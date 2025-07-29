from datetime import datetime

import googlesheets as gs
import googlenews as gn

# paths to Google API keys
CREDENTIALS_PATH = 'auth/google-credentials.json'
TOKEN_PATH = 'auth/google-token.json'

# ID pointing to master Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit)
MASTER_SHEET_ID = "1RfhB1Cxwkrd5dKGSPDPuMjNuK1KgbOBNdr_oghT24Zc"

# ID pointing to folder for daily datasets
DATA_FOLDER_ID = "1BhZ09JGMMRk71q_jhD9FAmqv0uL-Kfx1"

def main():
    # authenticate Google API
    creds = gs.authenticate_gsheets(CREDENTIALS_PATH, TOKEN_PATH)

    # create new sheet for child dataset and append row to master
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    child_sheet_name = f"AMT {timestamp}"
    child_sheet_id = gs.create_spreadsheet(creds, child_sheet_name, DATA_FOLDER_ID, public_access = True, tab_name = "main")
    child_sheet_url = f"https://docs.google.com/spreadsheets/d/{child_sheet_id}/"
    gs.append_row(MASTER_SHEET_ID, creds, "master", [timestamp, child_sheet_url])

    # import data and change main tab name
    child_tab_name = "main"
    df = gn.fetch_articles('en-US', 'US', 'US:en')
    gs.pd_to_sheet(child_sheet_id, creds, df, child_tab_name)

    # nicely format sheet
    gs.format_child_dataset(child_sheet_id, creds, child_tab_name)

if __name__ == "__main__":
    main()