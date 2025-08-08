import os
import json
from datetime import datetime, timedelta

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm
from arango.client import ArangoClient
import langid

import config
import chatbots as cb
import googledrive as gd

# config variables (see config.py for descriptions)
GOOGLE_CREDENTIALS_PATH = config.GOOGLE_CREDENTIALS_PATH
GOOGLE_TOKEN_PATH = config.GOOGLE_TOKEN_PATH
DATASET_FOLDER_ID = config.DATASET_FOLDER_ID
MASTER_SHEET_ID = config.MASTER_SHEET_ID
OUT_FOLDER = config.OUT_FOLDER
JSON_FOLDER_ID = config.JSON_FOLDER_ID
CHATBOTS = config.CHATBOTS
ARANGO_HOST = config.ARANGO_HOST
ARANGO_USERNAME = config.ARANGO_USERNAME
ARANGO_PASSWORD = config.ARANGO_PASSWORD
ARANGO_DATABASE = config.ARANGO_DATABASE
ARANGO_COLLECTION = config.ARANGO_COLLECTION
MAX_FT_CLAIMS = config.MAX_FT_CLAIMS
FT_DAYS_AGO = config.FT_DAYS_AGO
FT_LANG = config.FT_LANG

def load_claims(arango_host, arango_username, arango_password, database, collection, lang = "en", days_ago = 7, claim_limit = None):
    """
    Loads a set of claims from Open Claims Project through ArangoDB into a dataframe.

    Args:
        arango_host (str): URL to the ArangoDB database.
        arango_username (str): Username for the ArangoDB database.
        arango_password (str): Password for the ArangoDB database.
        database (str): Name of database to select from ArangoDB.
        collection (str): Name of collection within database to select.
        lang (str): Language code to filter claims.
        days_ago (int): How many days ago to look for claims (e.g. look for claims up to 7 days ago).
        claim_limit (int): Maximum number of claims to fetch.
    
    Returns:
        pandas.DataFrame: Dataframe of claims and their metadata.
    """
    # initialize client and connect to database
    client = ArangoClient(hosts = arango_host)
    sys_db = client.db("_system", username = arango_username, password = arango_password)
    db = client.db(database, username = arango_username, password = arango_password)

    # calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    # build query to check for claim and filter by date
    aql_query = """
    FOR doc IN @@collection
      FILTER HAS(doc, "raw") 
        AND HAS(doc.raw, "datePublished")
        AND HAS(doc.raw, "claimReviewed")
        AND doc.raw.datePublished >= @cutoff_date
      RETURN doc
    """
    bind_vars = {
        "@collection": collection,
        "cutoff_date": cutoff_date
    }

    # execute query
    cursor = db.aql.execute(aql_query, bind_vars = bind_vars)

    # filter results by language
    filtered_results = []
    for doc in cursor:
        claim = doc.get("raw").get("claimReviewed")
        predicted_lang, _ = langid.classify(claim)
        if predicted_lang == lang:
            filtered_results.append(doc)

    # shorten list of claims if specified
    if claim_limit:
        filtered_results = filtered_results[:claim_limit]
    print(f"Successfully fetched {len(filtered_results)} claims!")
    
    # build the rows with relevant metadata
    rows = []
    for doc in filtered_results:
        source = doc.get("sd_publisher")
        claim = doc.get("raw").get("claimReviewed")
        date_published = doc.get("raw").get("datePublished")
        appearance_url = doc.get("appearance_url")
        context_url = doc.get("context_url")
        rows.append({"source": source,
                     "claim": claim.strip(),
                     "lang": lang,
                     "date published": date_published,
                     "appearance url": appearance_url,
                     "context url": context_url})
    
    # turn rows into pandas df and return
    return pd.DataFrame(rows)

def add_questions(df, factcheck_prompt = "Is this statement true: "):
    """
    Creates a new dataframe with a question about each claim.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with claims under "claim" column.
        factcheck_prompt (str): A string to append to the beginning of each claim to check its
        validity (default "Is this statement true: ").

    Returns:
        pandas.DataFrame: A new dataframe with claim questions added on.
    """
    # copy dataframe
    dfq = df.copy()

    # append a new column with questions based on claims and return
    dfq["question"] = factcheck_prompt + dfq["claim"]
    return dfq

def ask_questions(df, chatbots, save_folder, creds, gdrive_save_id, max_workers = 10):
    """
    Asks a set of questions in a dataframe to a series of chatbots, saves their answers as
    JSON files, and returns a dataframe containing all previous data and the filepaths.

    Args:
        df (pandas.DataFrame): A dataframe of questions to ask (in column "question") along
        with any other data to be passed through.
        chatbots (str[]): List of chatbot names to query (corresponding to a chatbot name in
        cb_functions).
        save_folder (str): Path to folder to save JSON responses.
        creds (google.oauth2.credentials.Credentials): Authenticated Google API credentials.
        gdrive_save_id (str): ID for Google Drive folder to save to (i.e.
        https://drive.google.com/drive/u/0/folders/[FOLDER_ID]).
        max_workers (int): Maximum number of workers for threading.
    
    Returns:
        pandas.DataFrame: A new dataframe with questions answered in saved JSON files linked
        in "response path" column.
    """
    print(f"Answering questions about headlines (clients: {chatbots}).")

    # map of ai chatbot names to their function calls
    cb_functions = cb.CB_FUNCTIONS

    # make sure all chatbots specified are listed in cb_functions
    for chatbot in chatbots:
        if not chatbot in cb_functions.keys():
            raise ValueError("Invalid chatbot specified in ask_questions().")

    # make save file path
    os.makedirs(save_folder, exist_ok = True)

    # start a counter to make simple file names (AMT-FactCheck-2025-07-30-00000.json, etc.)
    counter = 0

    # initialize empty task list
    tasks = []

    # create threading locks for counter and chatbots (to avoid rate limiting)
    counter_lock = threading.Lock()
    locks = {bot: threading.Lock() for bot in chatbots}

    # get timestamp
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d")

    # define a helper function for threading tasks
    def ask_and_save(row_dict, chatbot):
        # access parent scope for counter
        nonlocal counter
        # ask chatbot question and save response as JSON
        try:
            question = row_dict["question"]
            ask_fn = cb_functions[chatbot]
            # query each chatbot one at a time
            with locks[chatbot]:
                response = ask_fn(question)
            # safely increment counter and make path name
            with counter_lock:
                count = counter
                counter += 1
            # save response as JSON
            out_path = os.path.join(save_folder, f"AMT-FactCheck-{timestamp}-{count:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            save_url = gd.upload_file(creds, gdrive_save_id, out_path)
            # record path in a row (duplicated from original) and return
            result_dict = row_dict.copy()
            result_dict["ai client"] = response["model"]
            # error message for url if missing
            if save_url == "":
                save_url = "error creating url"
            result_dict["response url"] = save_url
            return result_dict
        except Exception as e:
            print(f"Error in ask_questions: {e}")
            result_dict = row_dict.copy()
            result_dict["ai client"] = f"ERROR w/ {chatbot}"
            result_dict["response url"] = "an error occurred"
            return result_dict

    # build task list
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        for chatbot in chatbots:
            tasks.append((row_dict, chatbot))

    # execute tasks in multiple threads
    with ThreadPoolExecutor(max_workers = max_workers) as executor:
        results = list(tqdm(
            executor.map(lambda task: ask_and_save(*task), tasks),
            total = len(tasks),
            desc = "questions"
        ))
    
    # convert rows to dataframe and return
    return pd.DataFrame(results)

if __name__ == "__main__":
    # authenticate Google API
    creds = gd.authenticate(GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH)

    # get current date object
    now = datetime.now()

    # fetch claims from ArangoDB
    df = load_claims(ARANGO_HOST, ARANGO_USERNAME, ARANGO_PASSWORD, ARANGO_DATABASE, ARANGO_COLLECTION,
                    lang = FT_LANG, days_ago = FT_DAYS_AGO, claim_limit = MAX_FT_CLAIMS)

    # create new child sheet
    timestamp = now.strftime("%Y-%m-%d")
    child_sheet_name = f"AMT Fact Check {timestamp}"
    child_sheet_id = gd.create_spreadsheet(creds, child_sheet_name, DATASET_FOLDER_ID, public_access = True, tab_name = "claims")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"

    # append new row to master
    gd.append_row(creds, MASTER_SHEET_ID, "master", [timestamp, "fact check", child_sheet_url])
    gd.format_tab(creds, MASTER_SHEET_ID, tab_name = "master", format_name = "master")

    # import data into "claims" tab and format nicely
    gd.pd_to_sheet(creds, child_sheet_id, df, "claims")
    gd.format_tab(creds, child_sheet_id, tab_name = "claims", format_name = "claims")

    # create local and Google Drive output folders, if necessary
    save_folder = os.path.join(OUT_FOLDER, now.strftime("%Y-%m-%d"))
    gdrive_save_id = gd.create_folder(creds, JSON_FOLDER_ID, timestamp)

    # generate questions dataframe, then answers dataframe
    dfq = add_questions(df)
    dfqa = ask_questions(dfq, CHATBOTS, save_folder, creds, gdrive_save_id)

    # import data into "news questions" tab and nicely format
    gd.pd_to_sheet(creds, child_sheet_id, dfqa, "claim questions")
    gd.format_tab(creds, child_sheet_id, tab_name = "claim questions", format_name = "claim questions")

    # save backup CSV of data
    backup_folder = os.path.join(save_folder, "datasets")
    gd.save_backup_csv(df, backup_folder, f"{timestamp}-factcheck-claims.csv")
    gd.save_backup_csv(dfqa, backup_folder, f"{timestamp}-factcheck-questions.csv")

    print("AMT Fact Check Questions workflow finished!")