import os
import json
from datetime import datetime

import pandas as pd
from tqdm import tqdm

import chatbots as cb

def load_questions(questions_path):
    """
    Imports a question file (currently .txt) and returns them as a Python list.

    Args:
        question_path (str): Path to question list file (plain text).
    
    Returns:
        str[]: List of question strings.
    """
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = [line.strip() for line in f if line.strip()]
    return questions

def answer_questions(questions, chatbots, save_folder):
    """
    Takes a list of questions and answers them with several chatbots.

    Args:
        questions (str[]): List of questions to ask chatbots.
        chatbots (str[]): List of chatbot names to query (corresponding to a chatbot name in
        cb_functions).
        save_folder (str): Path to folder to save JSON responses.
    
    Returns:
        pandas.DataFrame: A new dataframe with questions answered in saved JSON files linked
        in 'response path' column.
    """
    # map of ai chatbot names to their function calls
    cb_functions = cb.CB_FUNCTIONS

    # make sure all chatbots specified are listed in cb_functions
    for chatbot in chatbots:
        if not chatbot in cb_functions.keys():
            raise ValueError("Invalid chatbot specified in ask_questions().")
        
    # make save file path
    os.makedirs(save_folder, exist_ok=True)
        
    # start a counter to make simple file names (AMT-News-2025-07-30-00000.json, etc.)
    counter = 0

    # initialize result as empty list of rows
    result_rows = []

    for question in tqdm(questions):
        for chatbot in chatbots:
            ask_chatbot_function = cb_functions[chatbot]
            # ask chatbot question and save response as JSON
            response = ask_chatbot_function(question)
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d")
            out_path = os.path.join(save_folder, f"AMT-LongTerm-{timestamp}-{counter:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            # record path in resulting dataframe
            row_dict = {'question': question, 'ai client': chatbot, 'response path': out_path}
            result_rows.append(row_dict)
            # increment counter
            counter += 1

    # convert rows to dataframe and return
    return pd.DataFrame(result_rows)