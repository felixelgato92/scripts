import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- CONFIGURATION ---
JSON_FILE = 'credentials.json'  # The key you downloaded
SHEET_NAME = 'Tithing 2025'    # The name of your Google Sheet
TAB_NAME = 'All chase transactions'
CSV_FILE = 'chase_statement.csv'

def upload_to_gsheets():
    # 1. Authenticate
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)

    # 2. Open Sheet
    spreadsheet = client.open(SHEET_NAME)
    try:
        worksheet = spreadsheet.worksheet(TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=TAB_NAME, rows="100", cols="20")

    # 3. Process CSV
    df = pd.read_csv(CSV_FILE)
    date_col = 'Transaction Date' if 'Transaction Date' in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    month_label = df[date_col].iloc[0].strftime('%B %Y')
    df[date_col] = df[date_col].dt.strftime('%m/%d/%Y')
    
    # Convert dataframe to list of lists for GSheets
    data_to_upload = df.fillna('').values.tolist()
    headers = df.columns.tolist()

    # 4. Find the start row
    # We look for the first empty row
    existing_data = worksheet.get_all_values()
    start_row = len(existing_data) + 1

    # 5. Append Header and Data
    # Adding a summary row first
    summary_row = [month_label, "Statement Total:", df['Amount'].sum()]
    worksheet.append_row(summary_row)
    
    # Append the actual transactions
    worksheet.append_rows([headers] + data_to_upload)

    # 6. Create the Collapsible Group (The "Magic")
    # This groups the rows we just added under the summary row
    end_row = start_row + len(data_to_upload) + 1
    
    requests = [{
        "addDimensionGroup": {
            "range": {
                "sheetId": worksheet.id,
                "dimension": "ROWS",
                "startIndex": start_row, # Starts after the summary row
                "endIndex": end_row
            }
        }
    }]
    spreadsheet.batch_update({'requests': requests})

    print(f"Successfully uploaded {month_label} to Google Sheets!")

if __name__ == "__main__":
    upload_to_gsheets()