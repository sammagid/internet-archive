import os
import json
from datetime import datetime

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

import config
import chatbots as cb
import googledrive as gd

# config variables (see config.py for descriptions)
GOOGLE_CREDENTIALS_PATH = config.GOOGLE_CREDENTIALS_PATH
GOOGLE_TOKEN_PATH = config.GOOGLE_TOKEN_PATH
DATASET_FOLDER_ID = config.DATASET_FOLDER_ID
MASTER_SHEET_ID = config.MASTER_SHEET_ID
LT_QUESTIONS_SHEET_ID = config.LT_QUESTIONS_SHEET_ID
MAX_LT_QUESTIONS = config.MAX_LT_QUESTIONS
OUT_FOLDER = config.OUT_FOLDER
JSON_FOLDER_ID = config.JSON_FOLDER_ID
CHATBOTS = config.CHATBOTS

def load_questions(creds, question_sheet_id, question_tab_name, question_limit = None):
    """
    Imports longterm questions from a Google Sheet.

    Args:
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        question_sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        question_tab_name (str): Name of the tab to read from (must include a "question" column).
        question_limit (int): Maximum number of questions to import.
    
    Returns:
        str[]: List of question strings.
    """
    # fetch data from Google Sheets API
    df = gd.sheet_to_pd(creds, question_sheet_id, question_tab_name)

    # get list of questions from "question" column
    questions = df["question"].tolist()

    # shorten if specified
    if question_limit:
        questions = questions[:question_limit]
    print(f"Successfully fetched {len(questions)} longterm questions from Longterm Question Set Google Sheet!")

    return questions

def answer_questions(questions, chatbots, save_folder, creds, gdrive_save_id, max_workers = 10):
    """
    Takes a list of questions and answers them with several chatbots.

    Args:
        questions (str[]): List of questions to ask chatbots.
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
    def ask_and_save(question, chatbot):
        # access parent scope for counter
        nonlocal counter
        # ask chatbot question and save response as JSON
        try:
            ask_fn = cb_functions[chatbot]
            # query each chatbot one at a time
            with locks[chatbot]:
                response = ask_fn(question)
            # safely increment counter
            with counter_lock:
                count = counter
                counter += 1
            # save response as JSON and upload to Google Drive folder
            out_path = os.path.join(save_folder, f"AMT-LongTerm-{timestamp}-{count:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            save_url = gd.upload_file(creds, gdrive_save_id, out_path)
            # error message for url if missing
            if save_url == "":
                save_url = "error creating url"
            # record path in a row and return
            row_dict = {"question": question, "ai client": response["model"], "response url": save_url}
            return row_dict
        except Exception as e:
            print(f"Error in answer_questions(): {e}")
            row_dict = {"question": question, "ai client": f"ERROR w/ {chatbot}", "response url": "an error ocurred"}
            return row_dict

    # build task list
    for question in questions:
        for chatbot in chatbots:
            tasks.append((question, chatbot))

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

    # create local and Google Drive output folders, if necessary
    timestamp = now.strftime("%Y-%m-%d")
    save_folder = os.path.join(OUT_FOLDER, now.strftime("%Y-%m-%d"))
    gdrive_save_id = gd.create_folder(creds, JSON_FOLDER_ID, timestamp)

    # fetch longterm questions, ask, and put into pandas df
    questions = load_questions(creds, LT_QUESTIONS_SHEET_ID, "questions", MAX_LT_QUESTIONS)
    dfqa = answer_questions(questions, CHATBOTS, save_folder, creds, gdrive_save_id)

    # create new sheet for child dataset
    child_sheet_name = f"AMT Long Term {timestamp}"
    child_sheet_id = gd.create_spreadsheet(creds, child_sheet_name, DATASET_FOLDER_ID, public_access = True, tab_name = "longterm questions")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"

    # append new row to master
    gd.append_row(creds, MASTER_SHEET_ID, "master", [timestamp, "longterm", child_sheet_url])
    gd.format_tab(creds, MASTER_SHEET_ID, tab_name = "master", format_name = "master")

    # import data into "questions" tab and nicely format
    gd.pd_to_sheet(creds, child_sheet_id, dfqa, "longterm questions")
    gd.format_tab(creds, child_sheet_id, tab_name = "longterm questions", format_name = "longterm questions")

    # save backup CSV of data
    backup_folder = os.path.join(save_folder, "datasets")
    gd.save_backup_csv(dfqa, backup_folder, f"{timestamp}-longterm-questions.csv")

    print("AMT Longterm Questions workflow finished!")