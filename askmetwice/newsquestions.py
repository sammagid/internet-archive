import ast
import os
import json
from datetime import datetime

import threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from tqdm import tqdm

import config
import chatbots as cb
import googlesheets as gs
import googlenews as gn

# config variables (see config.py for descriptions)
GOOGLE_CREDENTIALS_PATH = config.GOOGLE_CREDENTIALS_PATH
GOOGLE_TOKEN_PATH = config.GOOGLE_TOKEN_PATH
DATA_FOLDER_ID = config.DATA_FOLDER_ID
MASTER_SHEET_ID = config.MASTER_SHEET_ID
OUT_FOLDER = config.OUT_FOLDER
CHATBOTS = config.CHATBOTS
MAX_ARTICLES = config.MAX_ARTICLES

def generate_questions(headline, use_ai_questions):
    """
    Generates a list of questions to ask about a news headline. If use_ai_questions is true, the
    function will use an AI client (currently gpt-4o) to generate questions. Otherwise, a basic,
    non-generated question will be used (right now "Tell me about this headline").
    
    Args:
        headline (str): Any news headline.
        use_AI_questions (boolean): Whether to include AI-generated questions in the question set.
    
    Returns:
        str[]: A list of questions to ask about the input headline.
    """
    # initialize empty list to populate
    question_list = []

    # add basic question
    basic_question = "Tell me about this headline:"
    question_list.append(f"{basic_question} {headline}")

    # add ai generated questions if specified
    if use_ai_questions:
        # build question-getting prompt for chatbot
        prompt = "Come up with a list of 5-10 questions people might ask about this headline. "
        prompt += "Make sure to generate some factual questions, some subjective, and some speculative. "
        prompt += "Each of the questions should include all necessary information so that no additional context is needed to understand what events, people, or topics the question is referring to. "
        prompt += "Provide them as a valid Python list of strings, with no extra text or ``` formatting headers/footers."
        prompt += "\n\n"
        prompt += f"Headline: {headline}"

        # query AI chatbot for a list of natural questions
        response = cb.ask_openai(prompt)

        # get just message out of response
        message = response["response"]["choices"][0]["message"]["content"]

        # just in case, remove headers from message if exist
        message = message.replace("```python", "")
        message = message.replace("```", "")

        # attempt to evaluate as a python list and add to question_list
        try:
            list_representation = ast.literal_eval(message)
            question_list += list_representation
        except Exception as err:
            # if failure, just use the basic question
            print(f"Error evaluating question list in generate_questions(): {err}")

    return question_list

def add_questions(df, use_ai_questions):
    """
    Adds a set of questions for each headline in a dataset. If use_ai_questions is true, AI
    generated questions will be included. Otherwise, a basic, non-generated question will be used
    (right now "Tell me about this headline").

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under "title" column.
        use_ai_questions (boolean): Whether to include AI-generated questions in the question set.

    Returns:
        pandas.DataFrame: A new dataframe with each row holding a different question-headline pair.
    """
    print("Generating questions about headlines.")

    # initialize empty list of rows to hold result
    result_rows = []
    
    # iterate through each title (with progress bar) and generate questions
    for i, row in tqdm(df.iterrows(), total = len(df), desc = "headlines"):
        title = df.at[i, "title"]
        questions = generate_questions(title, use_ai_questions)
        # add a new row to resulting dataframe for each question
        for question in questions:
            row_dict = row.to_dict()
            row_dict["question"] = question
            result_rows.append(row_dict)
    
    # convert rows to dataframe and return
    return pd.DataFrame(result_rows)

def ask_questions(df, chatbots, save_folder, max_workers = 10):
    """
    Asks a set of questions in a dataframe to a series of chatbots, saves their answers as
    JSON files, and returns a dataframe containing all previous data and the filepaths.

    Args:
        df (pandas.DataFrame): A dataframe of questions to ask (in column "question") along
        with any other data to be passed through.
        chatbots (str[]): List of chatbot names to query (corresponding to a chatbot name in
        cb_functions).
        save_folder (str): Path to folder to save JSON responses.
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

    # start a counter to make simple file names (AMT-News-2025-07-30-00000.json, etc.)
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
            out_path = os.path.join(save_folder, f"AMT-News-{timestamp}-{count:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            # record path in a row (duplicated from original) and return
            result_dict = row_dict.copy()
            result_dict["ai client"] = response["model"]
            result_dict["response path"] = out_path
            return result_dict
        except Exception as e:
            print(f"Error in ask_questions: {e}")
            result_dict = row_dict.copy()
            result_dict["ai client"] = f"ERROR w/ {chatbot}"
            result_dict["response path"] = "an error occurred"
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
    creds = gs.authenticate_gsheets(GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH)

    # get current date object
    now = datetime.now()

    # fetch news articles from Google News
    df = gn.fetch_articles("en-US", "US", "US:en", separate_titles = True, article_limit = MAX_ARTICLES)

    # create new child sheet
    timestamp = now.strftime("%Y-%m-%d")
    child_sheet_name = f"AMT News {timestamp}"
    child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "headlines")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"

    # append new row to master
    gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, "news", child_sheet_url])
    gs.format_tab(MASTER_SHEET_ID, creds, tab_name = "master", format_name = "master")

    # import data into "headlines" tab and format nicely
    gs.pd_to_sheet(child_sheet_id, creds, df, "headlines")
    gs.format_tab(child_sheet_id, creds, tab_name = "headlines", format_name = "headlines")

    # generate questions dataframe, then answers dataframe
    dfq = add_questions(df, use_ai_questions = True)
    save_folder = os.path.join(OUT_FOLDER, now.strftime("%Y-%m-%d"))
    dfqa = ask_questions(dfq, CHATBOTS, save_folder)

    # import data into "news questions" tab and nicely format
    gs.pd_to_sheet(child_sheet_id, creds, dfqa, "news questions")
    gs.format_tab(child_sheet_id, creds, tab_name = "news questions", format_name = "news questions")

    # save backup CSV of data
    backup_folder = os.path.join(save_folder, "datasets")
    gs.save_backup_csv(df, backup_folder, f"{timestamp}-news-headlines.csv")
    gs.save_backup_csv(dfqa, backup_folder, f"{timestamp}-news-questions.csv")

    print("AMT News Questions workflow finished!")