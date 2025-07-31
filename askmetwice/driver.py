import os

from datetime import datetime

import config
import googlesheets as gs
import googlenews as gn
import questions as qt

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
CHATBOTS = ["perplexity", "gemini"]

# max number of articles to fetch from google news (set low for testing)
MAX_ARTICLES = 5

def main():
    # authenticate Google API
    creds = gs.authenticate_gsheets(CREDENTIALS_PATH, TOKEN_PATH)

    # create new sheet for child dataset, append row to master sheet, and nicely format
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d")
    child_sheet_name = f"AMT {timestamp}"
    child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "headlines")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"
    gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, child_sheet_url])
    gs.format_tab(MASTER_SHEET_ID, creds, "master")

    # import data into "headlines" tab and format nicely
    df = gn.fetch_articles('en-US', 'US', 'US:en', separate_titles = True, article_limit = MAX_ARTICLES)
    gs.pd_to_sheet(child_sheet_id, creds, df, "headlines")
    gs.format_tab(child_sheet_id, creds, "headlines")

    # generate questions dataframe, then answers dataframe
    dfq = qt.add_questions(df, use_ai_questions = True)
    save_folder = os.path.join(JSON_FOLDER, now.strftime("%Y-%m-%d"))
    dfqa = qt.ask_questions(dfq, CHATBOTS, save_folder)

    # import data into "questions" tab and nicely format
    gs.pd_to_sheet(child_sheet_id, creds, dfqa, "questions")
    gs.format_tab(child_sheet_id, creds, "questions")

if __name__ == "__main__":
    main()