import os

from datetime import datetime

import config
import googlesheets as gs
import googlenews as gn
import newsquestions as nq
import longtermquestions as ltq

# paths to Google API keys
CREDENTIALS_PATH = config.CREDENTIALS_PATH
TOKEN_PATH = config.TOKEN_PATH

# ID pointing to master Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit)
MASTER_SHEET_ID = config.MASTER_SHEET_ID

# ID pointing to Google Drive folder for storing daily datasets (i.e. drive.google.com/drive/u/1/folders/[FOLDER_ID])
DATA_FOLDER_ID = config.DATA_FOLDER_ID

# local folder to save JSON outputs
JSON_FOLDER = config.JSON_FOLDER

# chatbots to query (options: "perplexity" "openai" and "gemini")
CHATBOTS = ["perplexity", "gemini", "openai"]

# list of tasks to complete
#    "news": daily news questions
#    "longterm": long term questions (not yet implemented)
#    "factcheck": fact checking questions (not yet implemented)
TASKS = ["longterm"]

# max number of articles to fetch from google news (set low for testing)
MAX_ARTICLES = 5

# path to list of longterm questions
LT_QUESTIONS_PATH = "longterm/lt-questions.txt"

# max number of longterm questions (set low for testing)
MAX_LT_QUESTIONS = 5

def main():
    # authenticate Google API
    creds = gs.authenticate_gsheets(CREDENTIALS_PATH, TOKEN_PATH)

    # news questions workflow
    if "news" in TASKS:
        # create new sheet for child dataset, append row to master sheet, and nicely format
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d")
        child_sheet_name = f"AMT News {timestamp}"
        child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "headlines")
        child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"
        gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, "news", child_sheet_url])
        gs.format_tab(MASTER_SHEET_ID, creds, "master")

        # import data into "headlines" tab and format nicely
        df = gn.fetch_articles('en-US', 'US', 'US:en', separate_titles = True, article_limit = MAX_ARTICLES)
        gs.pd_to_sheet(child_sheet_id, creds, df, "headlines")
        gs.format_tab(child_sheet_id, creds, "headlines")

        # generate questions dataframe, then answers dataframe
        dfq = nq.add_questions(df, use_ai_questions = True)
        save_folder = os.path.join(JSON_FOLDER, now.strftime("%Y-%m-%d"))
        dfqa = nq.ask_questions(dfq, CHATBOTS, save_folder)

        # import data into "questions" tab and nicely format
        gs.pd_to_sheet(child_sheet_id, creds, dfqa, "news questions")
        gs.format_tab(child_sheet_id, creds, "news questions")
    
    # long term questions workflow
    if "longterm" in TASKS:
        # create new sheet for child dataset, append row to master sheet, and nicely format
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d")
        child_sheet_name = f"AMT Long Term Questions {timestamp}"
        child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "longterm questions")
        child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"
        gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, "longterm", child_sheet_url])
        gs.format_tab(MASTER_SHEET_ID, creds, "master")

        # fetch longterm questions, ask, and put into pandas df
        questions = ltq.load_questions(LT_QUESTIONS_PATH)
        if MAX_LT_QUESTIONS:
            questions = questions[:MAX_LT_QUESTIONS]
        save_folder = os.path.join(JSON_FOLDER, now.strftime("%Y-%m-%d"))
        dfqa = ltq.answer_questions(questions, CHATBOTS, save_folder)

        # import data into "questions" tab and nicely format
        gs.pd_to_sheet(child_sheet_id, creds, dfqa, "longterm questions")
        gs.format_tab(child_sheet_id, creds, "longterm questions")


        

if __name__ == "__main__":
    main()