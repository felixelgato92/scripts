import sys
from typing import Optional

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import math
import pandas as pd

from category_map import CATEGORIES, CATEGORY_MAP

# --- CONFIGURATION ---
JSON_FILE = 'credentials.json'  # The key you downloaded
SHEET_NAME = 'Tithing 2025'    # The name of your Google Sheet
TAB_NAME = 'All chase transactions'

CATEGORY_TABLE_HEADER = ['Category', 'Total Amount', 'Total Items']
MIN_SEPARATOR_ROWS = 5
FILTER_VIEW_TITLE = 'By Total Amount'


def _categorize_description(description: str) -> str:
    """Return a category for the transaction description using CATEGORY_MAP."""
    desc_lower = description.lower()
    for keyword, category in CATEGORY_MAP:
        if keyword in desc_lower:
            return category
    return "Uncategorized"


def _build_category_table(categories: set) -> list:
    """Build the category summary table rows with SUMIF/COUNTIF formulas.

    Returns a list of rows starting with the header row.
    """
    sorted_cats = sorted(categories)
    rows = [CATEGORY_TABLE_HEADER]
    for i, cat in enumerate(sorted_cats):
        row_num = i + 2  # 1-based (row 1 is the header)
        rows.append([
            cat,
            f'=SUMIF(D:D,A{row_num},F:F)',
            f'=COUNTIF(D:D,A{row_num})',
        ])
    return rows


def _get_old_table_size(existing_data: list) -> int:
    """Count the number of rows in the existing category table (header + data).

    Counts consecutive non-empty rows in column A starting from row 1.
    Returns 0 if the sheet is empty.
    """
    if not existing_data:
        return 0
    count = 0
    for row in existing_data:
        if row and row[0] != '':
            count += 1
        else:
            break
    return count


def _find_filter_view_id(
    spreadsheet: gspread.Spreadsheet,
    sheet_id: int,
    title: str,
) -> Optional[int]:
    """Return the filterViewId of an existing filter view matching the title, or None."""
    metadata = spreadsheet.fetch_sheet_metadata()
    for sheet in metadata.get('sheets', []):
        if sheet.get('properties', {}).get('sheetId') == sheet_id:
            for fv in sheet.get('filterViews', []):
                if fv.get('title') == title:
                    return fv['filterViewId']
    return None


def _ensure_filter_view(
    spreadsheet: gspread.Spreadsheet,
    worksheet: gspread.Worksheet,
    category_table_size: int,
) -> None:
    """Create or update a filter view that sorts the category table by Total Amount descending."""
    sort_specs = [
        {'dimensionIndex': 1, 'sortOrder': 'DESCENDING'},   # Total Amount
        {'dimensionIndex': 0, 'sortOrder': 'ASCENDING'},    # Category name tiebreaker
    ]
    filter_range = {
        'sheetId': worksheet.id,
        'startRowIndex': 0,
        'endRowIndex': category_table_size,
        'startColumnIndex': 0,
        'endColumnIndex': 3,
    }

    existing_id = _find_filter_view_id(spreadsheet, worksheet.id, FILTER_VIEW_TITLE)

    if existing_id is not None:
        requests = [{
            'updateFilterView': {
                'filter': {
                    'filterViewId': existing_id,
                    'title': FILTER_VIEW_TITLE,
                    'range': filter_range,
                    'sortSpecs': sort_specs,
                },
                'fields': 'range,sortSpecs',
            }
        }]
    else:
        requests = [{
            'addFilterView': {
                'filter': {
                    'title': FILTER_VIEW_TITLE,
                    'range': filter_range,
                    'sortSpecs': sort_specs,
                }
            }
        }]

    spreadsheet.batch_update({'requests': requests})


def _write_category_table(
    spreadsheet: gspread.Spreadsheet,
    worksheet: gspread.Worksheet,
    category_table: list,
) -> None:
    """Write the category summary table at A1 and format Total Amount as currency."""
    required = len(category_table) + 50
    if worksheet.row_count < required:
        worksheet.resize(rows=required)

    worksheet.update(
        'A1',
        category_table,
        value_input_option='USER_ENTERED',
    )

    # Format column B (Total Amount) as currency
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId": worksheet.id,
                "startRowIndex": 1,                  # skip header row (0-based)
                "endRowIndex": len(category_table),   # exclusive
                "startColumnIndex": 1,                # column B
                "endColumnIndex": 2,
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {
                        "type": "CURRENCY",
                        "pattern": "$#,##0.00",
                    }
                }
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }]
    spreadsheet.batch_update({'requests': requests})


def upload_to_gsheets(csv_file: str) -> None:
    """Process the CSV and upload data with a category summary to Google Sheets."""
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
    df = pd.read_csv(csv_file)
    date_col = 'Transaction Date' if 'Transaction Date' in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    month_label = df[date_col].iloc[0].strftime('%B %Y')
    df[date_col] = df[date_col].dt.strftime('%m/%d/%Y')

    # Re-categorize transactions using our own CATEGORY_MAP
    desc_col = 'Description' if 'Description' in df.columns else df.columns[2]
    df['Category'] = df[desc_col].apply(_categorize_description)

    # Only fill NaN on string/object columns to preserve numeric types
    string_cols = df.select_dtypes(include=['object']).columns
    df[string_cols] = df[string_cols].fillna('')

    headers = df.columns.tolist()
    data_rows = df.values.tolist()

    # Sanitize any remaining NaN floats (not JSON-serializable)
    data_rows = [
        ['' if isinstance(v, float) and math.isnan(v) else v for v in row]
        for row in data_rows
    ]

    # 4. Write or update category summary table at the top
    existing_data = worksheet.get_all_values()
    category_table = _build_category_table(CATEGORIES)
    category_table_size = len(category_table)  # header + one row per category

    has_category_table = (
        len(existing_data) > 0
        and existing_data[0] == CATEGORY_TABLE_HEADER
    )

    # Detect whether the existing table is stale (categories added/removed)
    needs_update = False
    old_table_size = 0
    if has_category_table:
        old_table_size = _get_old_table_size(existing_data)
        needs_update = old_table_size != category_table_size

    if not has_category_table or needs_update:
        if needs_update:
            # Find where the first data section starts (1-based)
            first_data_row = None
            for i in range(old_table_size, len(existing_data)):
                if existing_data[i] and any(cell != '' for cell in existing_data[i]):
                    first_data_row = i + 1  # 1-based
                    break

            if category_table_size > old_table_size:
                # Table grew — insert rows so data & groups shift down
                min_data_start = category_table_size + MIN_SEPARATOR_ROWS + 1
                current_data_start = first_data_row or (old_table_size + 2)
                rows_to_insert = max(0, min_data_start - current_data_start)
                if rows_to_insert > 0:
                    spreadsheet.batch_update({'requests': [{
                        'insertDimension': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'ROWS',
                                'startIndex': old_table_size,  # 0-based
                                'endIndex': old_table_size + rows_to_insert,
                            },
                            'inheritFromBefore': False,
                        }
                    }]})
            else:
                # Table shrank — clear leftover rows
                worksheet.batch_clear([f'A1:C{old_table_size}'])

        _write_category_table(spreadsheet, worksheet, category_table)
        # Re-fetch so row count is accurate
        existing_data = worksheet.get_all_values()

    # Ensure the filter view for sorting categories by Total Amount exists
    _ensure_filter_view(spreadsheet, worksheet, category_table_size)

    # 5. Find the exact row to write at (bypasses table-detection issues
    #    with collapsed groups that append_rows / values.append can hit)
    start_row = len(existing_data) + 1          # 1-based, first empty row

    # Ensure at least MIN_SEPARATOR_ROWS blank rows after the category table
    if start_row <= category_table_size + MIN_SEPARATOR_ROWS:
        start_row = category_table_size + MIN_SEPARATOR_ROWS + 1

    summary_row_idx = start_row - 1             # 0-based index for the API

    # 6. Write all rows at the exact position
    summary_row = [month_label, "Statement Total:", df['Amount'].sum()]
    all_rows = [summary_row, headers] + data_rows

    # Ensure the worksheet has enough rows for the new data
    required_rows = start_row + len(all_rows) - 1
    if worksheet.row_count < required_rows:
        worksheet.resize(rows=required_rows)

    worksheet.update(
        f'A{start_row}',
        all_rows,
        value_input_option='USER_ENTERED',
    )

    # 7. Create the Collapsible Group
    # Group the header + data rows under the summary row
    group_start = summary_row_idx + 1          # row right after the summary (0-based)
    group_end = summary_row_idx + len(all_rows) # exclusive end (0-based)

    requests = [{
        "addDimensionGroup": {
            "range": {
                "sheetId": worksheet.id,
                "dimension": "ROWS",
                "startIndex": group_start,
                "endIndex": group_end,
            }
        }
    }]
    spreadsheet.batch_update({'requests': requests})

    print(f"Successfully uploaded {month_label} to Google Sheets!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <csv_file>")
        sys.exit(1)
    upload_to_gsheets(sys.argv[1])