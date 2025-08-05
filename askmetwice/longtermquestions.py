import os
import json
from datetime import datetime

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

import config
import chatbots as cb
import googlesheets as gs

# config variables (see config.py for descriptions)
CREDENTIALS_PATH = config.CREDENTIALS_PATH
TOKEN_PATH = config.TOKEN_PATH
DATA_FOLDER_ID = config.DATA_FOLDER_ID
MASTER_SHEET_ID = config.MASTER_SHEET_ID
LT_QUESTIONS_PATH = config.LT_QUESTIONS_PATH
MAX_LT_QUESTIONS = config.MAX_LT_QUESTIONS
OUT_FOLDER = config.OUT_FOLDER
CHATBOTS = config.CHATBOTS

def load_questions(questions_path, question_limit):
    """
    Imports a question file (currently .txt) and returns them as a Python list.

    Args:
        question_path (str): Path to question list file (plain text).
        question_limit (int): Maximum number of questions to import.
    
    Returns:
        str[]: List of question strings.
    """
    with open(questions_path, "r", encoding = "utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]
        if question_limit:
            questions = questions[:question_limit]
    return questions

def answer_questions(questions, chatbots, save_folder, max_workers = 10):
    """
    Takes a list of questions and answers them with several chatbots.

    Args:
        questions (str[]): List of questions to ask chatbots.
        chatbots (str[]): List of chatbot names to query (corresponding to a chatbot name in
        cb_functions).
        save_folder (str): Path to folder to save JSON responses.
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
            # save response as JSON
            out_path = os.path.join(save_folder, f"AMT-LongTerm-{timestamp}-{count:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            # record path in a row and return
            row_dict = {"question": question, "ai client": response["model"], "response path": out_path}
            return row_dict
        except Exception as e:
            print(f"Error in answer_questions(): {e}")
            row_dict = {"question": question, "ai client": f"ERROR w/ {chatbot}", "response path": "an error ocurred"}
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
    creds = gs.authenticate_gsheets(CREDENTIALS_PATH, TOKEN_PATH)

    # get current date object
    now = datetime.now()

    # fetch longterm questions, ask, and put into pandas df
    questions = load_questions(LT_QUESTIONS_PATH, MAX_LT_QUESTIONS)
    save_folder = os.path.join(OUT_FOLDER, now.strftime("%Y-%m-%d"))
    dfqa = answer_questions(questions, CHATBOTS, save_folder)

    # create new sheet for child dataset
    timestamp = now.strftime("%Y-%m-%d")
    child_sheet_name = f"AMT Long Term Questions {timestamp}"
    child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "longterm questions")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"

    # append new row to master
    gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, "longterm", child_sheet_url])
    gs.format_tab(MASTER_SHEET_ID, creds, tab_name = "master", format_name = "master")

    # import data into "questions" tab and nicely format
    gs.pd_to_sheet(child_sheet_id, creds, dfqa, "longterm questions")
    gs.format_tab(child_sheet_id, creds, tab_name = "longterm questions", format_name = "longterm questions")

    # save backup CSV of data
    backup_folder = os.path.join(save_folder, "datasets")
    gs.save_backup_csv(dfqa, backup_folder, f"{timestamp}-longterm-questions.csv")

    print("AMT Longterm Questions workflow finished!")