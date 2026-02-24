import os
import sys
from typing import List

from pdf_to_csv import OUTPUT_DIR, extract_transactions, save_csv
from import_credit_chase import upload_to_gsheets


def main(argv: List[str]) -> int:
    """Convert a bank statement PDF to CSV and upload it to Google Sheets."""
    if len(argv) < 2:
        print(f"Usage: python {os.path.basename(argv[0])} <statement.pdf>")
        return 1

    pdf_path = argv[1]

    # --- Validate file extension ---
    _, ext = os.path.splitext(pdf_path)
    if ext.lower() != ".pdf":
        print("Error: this script only accepts .pdf files.")
        return 1

    # --- Validate file exists ---
    if not os.path.isfile(pdf_path):
        print(f"Error: file not found: {pdf_path}")
        return 1

    # --- Step 1: PDF → CSV ---
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")

    try:
        print(f"Reading PDF: {pdf_path}")
        df = extract_transactions(pdf_path)
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

    # --- Step 2: CSV → Google Sheets ---
    try:
        upload_to_gsheets(csv_path)
    except Exception as exc:
        print(f"Error: Google Sheets upload failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
