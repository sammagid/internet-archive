import os.path
from datetime import datetime

import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# note: if modifying scopes, delete the token.json file first
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets", # Google Sheets API
    "https://www.googleapis.com/auth/drive" # Google Drive API
]

# paths to Google API keys
CREDENTIALS_PATH = "auth/google-credentials.json"
TOKEN_PATH = "auth/google-token.json"

def authenticate_gsheets(credentials_path, token_path):
    """
    Loads credentials for Google Sheets API. Tries to load from token_path if
    exists, otherwise generates new token using credential_path.

    Args:
        credential_path (str): Path to a Google Sheets API credentials JSON file.
        token_path (str): Path to a Google Sheets API token JSON file, or the location
        where it will be saved.
    
    Returns:
        google.oauth2.credentials.Credentials: The authenticated Google Sheets credentials object.
    """
    creds = None

    # load credentials from token if it exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # if there are no valid credentials, log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port = 0)

        # save credentials for future runs
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    
    return creds

def create_spreadsheet(creds, sheet_name, folder_id, public_access = False, tab_name = None):
    """
    Creates a new Google Spreadsheet and returns its ID and URL.

    Args:
        creds (google.oauth2.credentials.Credentials): Authenticated Google Sheets API credentials.
        sheet_name (str): The name of the spreadsheet.
        folder_id (str): Folder ID for the target folder to create new sheet.
        public_access (bool): Whether the new sheet should be publicly accessible.
        tab_name (str): If set, replaces default "Sheet1" tab with a custom name.

    Returns:
        str: Spreadsheet ID for newly created spreadsheet.
    """
    try:
        drive_service = build("drive", "v3", credentials = creds)

        # build request for new sheet within folder
        file_metadata = {
            "name": sheet_name,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id]
        }

        # create sheet
        file = drive_service.files().create(body = file_metadata, fields = "id, webViewLink").execute()
        sheet_id = file.get("id")
        print(f"Created spreadsheet '{sheet_name}' at https://docs.google.com/spreadsheets/d/{sheet_id}.")
    
        if public_access:
            # make the sheet public
            drive_service.permissions().create(
                fileId = sheet_id,
                body= {"type": "anyone", "role": "reader"},
            ).execute()
            print("Made spreadsheet public.")
        
        # if tab name specified, create it and delete the default "Sheet1" tab
        if tab_name:
            create_tab(sheet_id, creds, tab_name)
            delete_tab(sheet_id, creds, "Sheet1")

        # return the ID
        return sheet_id

    except HttpError as err:
        print(f"ERROR: {err}")

def pd_to_sheet(sheet_id, creds, df, tab_name):
    """
    Writes a Pandas Dataframe of data to a tab within a Google Sheet, creating tab if nonexistent.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        df (Pandas.DataFrame): Data to write.
        tab_name (str): Name of tab to write to (creates new tab if doesn't exist).
    
    Returns:
        None.
    """
    try:
        service = build("sheets", "v4", credentials = creds)
        sheet = service.spreadsheets()

        # convert df to list of lists
        values = [df.columns.tolist()] + df.values.tolist()

        # add new sheet
        add_sheet_request = {
            "requests": [{
                "addSheet": {"properties": {"title": tab_name}}
            }]
        }
        try:
            sheet.batchUpdate(spreadsheetId = sheet_id, body = add_sheet_request).execute()
            print(f"Created new tab '{tab_name}'.")
        except HttpError as e:
            if "already exists" in str(e):
                print(f"Tab '{tab_name}' exists, skipping creation.")
            else:
                raise

        # write dataframe values to sheet
        body = {"values": values}
        service.spreadsheets().values().update(
            spreadsheetId = sheet_id,
            range = f"{tab_name}!A1",
            valueInputOption = "RAW",
            body = body
        ).execute()

        print(f"DataFrame written to '{tab_name}'.")

    except HttpError as err:
        print(f"ERROR: {err}")

def append_row(sheet_id, creds, tab_name, row_values):
    """
    Appends a row to an already existing tab within a sheet.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        tab_name (str): The name of the target tab to append data to.
        row_values (list): List of values to append.
    
    Returns:
        None.
    """
    try:
        service = build("sheets", "v4", credentials = creds)

        # append values
        service.spreadsheets().values().append(
            spreadsheetId = sheet_id,
            range = f"{tab_name}!A1",
            valueInputOption = "RAW",
            insertDataOption = "INSERT_ROWS",
            body = {"values": [row_values]}
        ).execute()

        print(f"Appended row to {tab_name}.")

    except HttpError as err:
        print(f"ERROR: {err}")
    

def get_tab_id(sheet_id, creds, tab_name):
    """
    Returns the numeric tab ID of a given tab name in a sheet.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        tab_name (str): The name of the target tab to identify.
    
    Returns:
        int: The numeric ID for the given tab, or None if it does not exist.
    """
    try:
        service = build("sheets", "v4", credentials = creds)
        sheet = service.spreadsheets()
        spreadsheet = sheet.get(spreadsheetId = sheet_id).execute()

        # search for the tab
        for s in spreadsheet["sheets"]:
            if s["properties"]["title"] == tab_name:
                return s["properties"]["sheetId"]
        return None
    
    except HttpError as err:
        print(f"ERROR: {err}")

def delete_tab(sheet_id, creds, tab_name):
    """
    Deletes a given tab within a Google Sheet.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        tab_name (str): The name of the target tab to delete.
    
    Returns:
        None.
    """
    try:
        service = build("sheets", "v4", credentials = creds)
        sheet = service.spreadsheets()
        spreadsheet = sheet.get(spreadsheetId = sheet_id).execute()

        # get tab ID
        tab_id = get_tab_id(sheet_id, creds, tab_name)

        # if tab does not exist, skip
        if tab_id is None:
            print(f"Tab '{tab_name}' does not exist, skipping delete.")
            return
        
        # build delete request
        delete_request = {
            "requests": [
                {
                    "deleteSheet": {"sheetId": tab_id}
                }
            ]
        }

        # execute delete
        sheet.batchUpdate(spreadsheetId = sheet_id, body = delete_request).execute()
        print(f"Successfully deleted tab '{tab_name}'")

    except HttpError as err:
        print(f"ERROR: {err}")

def create_tab(sheet_id, creds, tab_name):
    """
    Creates a named tab within a given Google Sheet.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        tab_name (str): The name of the tab to create.
    
    Returns:
        None.
    """
    empty_df = pd.DataFrame()
    pd_to_sheet(sheet_id, creds, empty_df, tab_name)

def apply_formatting(sheet_id, creds, format_requests):
    """
    Applies a list of formatting requests to a given tab in a sheet.

    Args:
        sheet_id (str): The ID for the target Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        format_requests (dict[]): A list of formatting requests to be applied to the target tab (specified in request).
    
    Returns:
        None.
    """
    try:
        service = build("sheets", "v4", credentials = creds)
        sheet = service.spreadsheets()
        sheet.batchUpdate(spreadsheetId = sheet_id, body = {"requests": format_requests}).execute()

        # apply formatting
        print("Formatting requests successfully applied.")

    except HttpError as err:
        print(f"ERROR: {err}")

def format_tab(sheet_id, creds, tab_name, format_name):
    """
    Applies specific formatting for a given tab of a child (daily) dataset, including
    bold headers, text wrapping, and columns spaced for the given tab.

    Args:
        sheet_id (str): The ID for the child Google Sheet (i.e. docs.google.com/spreadsheets/d/[SHEET_ID]/edit).
        creds (google.oauth2.credentials.Credentials): The authenticated Google Sheets credentials object.
        tab_name (str): Name of tab to format.
        format_name (str): Name of formatting type to apply (currently "master", "headlines", "news questions",
        or "longterm questions").
    
    Returns:
        None.
    """
    # get numeric tab ID (needed for formatting request)
    tab_id = get_tab_id(sheet_id, creds, tab_name)

    # formatting request for master sheet column widths
    master_columns = [
        { # set "date" width to 120px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        { # set "dataset type" width to 100px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2
                },
                "properties": {
                    "pixelSize": 100
                },
                "fields": "pixelSize"
            }
        },
        { # set "link to AMT dataset" width to 650
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,
                    "endIndex": 3
                },
                "properties": {
                    "pixelSize": 650
                },
                "fields": "pixelSize"
            }
        }
    ]

    # formatting request for headlines tab (child sheet) column widths
    headlines_columns = [
        { # set "source" width to 100px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 100
                },
                "fields": "pixelSize"
            }
        },
        { # set "title" width to 400px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2
                },
                "properties": {
                    "pixelSize": 400
                },
                "fields": "pixelSize"
            }
        },
        { # set "news outlet" width to 200px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,
                    "endIndex": 3
                },
                "properties": {
                    "pixelSize": 200
                },
                "fields": "pixelSize"
            }
        },
        { # set "url" width to 800px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 3,
                    "endIndex": 4
                },
                "properties": {
                    "pixelSize": 800
                },
                "fields": "pixelSize"
            }
        }
    ]

    # formatting request for news questions tab (child sheet) column widths
    news_questions_columns = headlines_columns + [
        { # set "question" width to 450px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 4,
                    "endIndex": 5
                },
                "properties": {
                    "pixelSize": 450
                },
                "fields": "pixelSize"
            }
        },
        { # set "ai client" width to 200px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,
                    "endIndex": 6
                },
                "properties": {
                    "pixelSize": 200
                },
                "fields": "pixelSize"
            }
        },
        { # set "response path" width to 300px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 6,
                    "endIndex": 7
                },
                "properties": {
                    "pixelSize": 300
                },
                "fields": "pixelSize"
            }
        }
    ]

    # formatting request for longterm questions tab (child sheet) column widths
    longterm_questions_columns = [
        { # set "question" width to 450px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 450
                },
                "fields": "pixelSize"
            }
        },
        { # set "ai client" width to 200px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2
                },
                "properties": {
                    "pixelSize": 200
                },
                "fields": "pixelSize"
            }
        },
        { # set "response path" width to 300px
            "updateDimensionProperties": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,
                    "endIndex": 3
                },
                "properties": {
                    "pixelSize": 300
                },
                "fields": "pixelSize"
            }
        }
    ]

    # formatting request for bold headers and non-bold body
    bold_format = [
        { # make headers bold
            "repeatCell": {
                "range": {
                    "sheetId": tab_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold"
            }
        },
        { # make body non-bold
            "repeatCell": {
                "range": {
                    "sheetId": tab_id,
                    "startRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": False}
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold"
            }
        }
    ]

    # formatting request for text wrapping
    text_wrapping = [
        { # wrap text for whole sheet
            "repeatCell": {
                "range": {
                    "sheetId": tab_id
                },
                "cell": {
                    "userEnteredFormat": {
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy"
            }
        }
    ]

    # pick formatting based on tab name
    if format_name == "master":
        format_requests = master_columns
    elif format_name == "headlines":
        format_requests = headlines_columns
    elif format_name == "news questions":
        format_requests = news_questions_columns
    elif format_name == "longterm questions":
        format_requests = longterm_questions_columns
    else:
        raise ValueError("Invalid format name given to format_tab().")

    # add bold and text wrapping requests
    format_requests += bold_format
    format_requests += text_wrapping

    # execute formatting request
    apply_formatting(sheet_id, creds, format_requests)