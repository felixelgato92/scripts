import os
import sys
from typing import List

from pdf_to_csv import OUTPUT_DIR, extract_transactions, save_csv
from import_credit_chase import upload_to_gsheets


def main(argv: List[str]) -> int:
    """Convert a bank statement PDF to CSV (or accept CSV) and upload it to Google Sheets.

    If a PDF is supplied the script converts it to CSV first. If a CSV is supplied,
    the conversion step is skipped and the CSV is uploaded directly.
    """
    if len(argv) < 2:
        print(f"Usage: python {os.path.basename(argv[0])} <statement.pdf|statement.csv>")
        return 1

    input_path = argv[1]

    # --- Validate file exists ---
    if not os.path.isfile(input_path):
        print(f"Error: file not found: {input_path}")
        return 1

    _, ext = os.path.splitext(input_path)
    ext = ext.lower()

    if ext == ".pdf":
        # --- Step 1: PDF → CSV ---
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")

        try:
            print(f"Reading PDF: {input_path}")
            df = extract_transactions(input_path)
        except Exception as exc:
            print(f"Error: PDF to CSV conversion failed: {exc}")
            return 1

        if df.empty:
            print("Error: PDF to CSV conversion failed: no transactions found. "
                  "The PDF layout may need manual tuning.")
            return 1

        try:
            save_csv(df, csv_path)
        except Exception as exc:
            print(f"Error: PDF to CSV conversion failed (writing CSV): {exc}")
            return 1

        print(f"Wrote {len(df)} transactions to {csv_path}")

    elif ext == ".csv":
        # CSV supplied — skip conversion and use the provided CSV directly
        csv_path = input_path
        print(f"Using existing CSV: {csv_path}")

    else:
        print("Error: this script only accepts .pdf or .csv files.")
        return 1

    # --- Step 2: CSV → Google Sheets ---
    try:
        upload_to_gsheets(csv_path)
    except Exception as exc:
        print(f"Error: Google Sheets upload failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
