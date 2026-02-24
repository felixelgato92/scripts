import os
import re
import sys
from datetime import date as date_type
from typing import List, Optional
from category_map import CATEGORY_MAP

import pandas as pd
import pdfplumber
import tabula

# --- CONFIGURATION ---
OUTPUT_DIR = "statements_2026"

# PDF table columns (checking account statement)
PDF_COLUMNS = {"DATE", "DESCRIPTION", "AMOUNT", "BALANCE"}

# Section headers that appear in the PDF statement
SECTION_HEADERS = {
    "DEPOSITS AND ADDITIONS",
    "ELECTRONIC WITHDRAWALS",
    "FEES",
    "DAILY ENDING BALANCE",
    "SERVICE CHARGE SUMMARY",
    "TRANSACTION DETAIL",
}

# Header markers to skip (rows that are just column headers)
HEADER_MARKERS = {"DATE", "DESCRIPTION", "AMOUNT", "BALANCE"}

# Regex patterns for extracting due date from PDF header text
_DUE_DATE_PATTERNS = [
    re.compile(r'Payment\s+Due\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
    re.compile(r'Due\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
    re.compile(r'Statement\s+(?:Closing|End)\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
]

# Fallback: extract statement period end date (numeric format)
_PERIOD_END_RE = re.compile(
    r'(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:through|to|[-–])\s*(\d{1,2}/\d{1,2}/\d{2,4})',
    re.IGNORECASE,
)

# Statement period with spelled-out month names, e.g.
# "December 19, 2025 through January 22, 2026"
_MONTH_NAMES = (
    r'(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)'
)
_PERIOD_SPELLED_RE = re.compile(
    rf'({_MONTH_NAMES}\s+\d{{1,2}},?\s+\d{{4}})'
    rf'\s*(?:through|to|[-–])\s*'
    rf'({_MONTH_NAMES}\s+\d{{1,2}},?\s+\d{{4}})',
    re.IGNORECASE,
)


def _extract_due_date(pdf_path: str) -> Optional[date_type]:
    """Extract the Payment Due Date (or statement end date) from the PDF.

    Tries multiple strategies: full-page text, cropped top banner, and
    word-level extraction. Supports both numeric (01/22/2026) and
    spelled-out (January 22, 2026) date formats.

    Returns a datetime.date with the full year, or None if not found.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            # Gather text from multiple extraction strategies
            text_sources = []

            # Strategy 1: standard full-page text
            text_sources.append(page.extract_text() or "")

            # Strategy 2: cropped top banner (header area where period appears)
            for crop_height in (120, 200):
                cropped = page.crop((0, 0, page.width, crop_height))
                text_sources.append(cropped.extract_text() or "")

            # Strategy 3: word-level extraction (catches text that
            # extract_text() misses due to unusual positioning)
            words = page.extract_words(keep_blank_chars=True)
            text_sources.append(" ".join(w["text"] for w in words))
    except Exception:
        return None

    for text in text_sources:
        # Try each due-date pattern (numeric)
        for pattern in _DUE_DATE_PATTERNS:
            m = pattern.search(text)
            if m:
                return _parse_date_with_year(m.group(1))

        # Try spelled-out period: "December 19, 2025 through January 22, 2026"
        m = _PERIOD_SPELLED_RE.search(text)
        if m:
            return _parse_date_with_year(m.group(2))

        # Try numeric period: "12/19/2025 through 01/22/2026"
        m = _PERIOD_END_RE.search(text)
        if m:
            return _parse_date_with_year(m.group(2))

    return None


def _parse_date_with_year(date_str: str) -> Optional[date_type]:
    """Parse a date string like '01/20/2026' or '01/20/26' to a date object."""
    try:
        dt = pd.to_datetime(date_str)
        return dt.date()
    except Exception:
        return None


def _assign_year(date_mm_dd: str, due_date: date_type) -> str:
    """Convert a MM/DD date to MM/DD/YYYY using the due-date year.

    Rule: the due date's year applies to all transactions, UNLESS the
    transaction month is December and the due date is in January+ of the
    next year — then the transaction year is due_date.year - 1.
    """
    parts = date_mm_dd.split("/")
    if len(parts) >= 3 and len(parts[2]) >= 4:
        # Already has a year
        return date_mm_dd

    try:
        month = int(parts[0])
    except (ValueError, IndexError):
        return date_mm_dd

    if month == 12 and due_date.month != 12:
        year = due_date.year - 1
    else:
        year = due_date.year

    return f"{date_mm_dd}/{year}"


def _categorize(description: str, amount: float) -> str:
    """Return a category for the transaction based on description keywords."""
    desc_lower = description.lower()

    # Special rule: Airbnb + positive amount = Short-Term Income
    if "airbnb" in desc_lower and amount > 0:
        return "Short-Term Income"

    for keyword, category in CATEGORY_MAP:
        if keyword.lower() in desc_lower:
            return category

    return "Uncategorized"


def _read_tables(pdf_path: str) -> List[pd.DataFrame]:
    """Extract all tables from the PDF using tabula."""
    try:
        tables = tabula.read_pdf(
            pdf_path,
            pages="all",
            multiple_tables=True,
            guess=True,
            lattice=False,
        )
        if tables:
            return tables
        # Fallback: stream mode
        return tabula.read_pdf(
            pdf_path,
            pages="all",
            multiple_tables=True,
            guess=False,
            stream=True,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to read PDF. Ensure Java is installed and the PDF is readable."
        ) from exc


# Regex for a date at the start of a string, e.g. "01/15" or "01/15/2026"
_DATE_PREFIX_RE = re.compile(r"^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(.+)$")


def _normalize_table(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw PDF columns → (Date, Description, Amount). Drop Balance."""
    df = df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    df = df.dropna(axis=1, how="all")

    # Try exact column match first
    for date_col in ("DATE", "DATE OF TRANSACTION"):
        for desc_col in ("DESCRIPTION", "MERCHANT NAME OR TRANSACTION DESCRIPTION"):
            for amt_col in ("AMOUNT", "$ AMOUNT"):
                if {date_col, desc_col, amt_col}.issubset(set(df.columns)):
                    out = df[[date_col, desc_col, amt_col]].copy()
                    out.columns = ["Date", "Description", "Amount"]
                    return out

    # Handle 4-column table: skip the last column (Balance)
    if df.shape[1] >= 4:
        out = df.iloc[:, :3].copy()
        out.columns = ["Date", "Description", "Amount"]
        return out

    # Handle 3-column table where first column has merged Date+Description.
    # Detected when col 0 looks like "01/15 Some description" and col 1 looks
    # like a dollar amount. Split col 0 into Date and Description, treat col 1
    # as Amount, and ignore col 2 (Balance).
    if df.shape[1] == 3:
        sample_col0 = df.iloc[:, 0].dropna().astype(str)
        merged = sample_col0.apply(lambda x: bool(_DATE_PREFIX_RE.match(x.strip())))
        if merged.mean() > 0.3:  # >30% of rows look merged
            dates, descs = [], []
            for val in df.iloc[:, 0]:
                s = str(val).strip() if pd.notna(val) else ""
                m = _DATE_PREFIX_RE.match(s)
                if m:
                    dates.append(m.group(1))
                    descs.append(m.group(2))
                else:
                    dates.append("")
                    descs.append(s)
            out = pd.DataFrame({
                "Date": dates,
                "Description": descs,
                "Amount": df.iloc[:, 1].values,  # actual amount (not balance)
            })
            return out

        # Normal 3-column fallback
        out = df.iloc[:, :3].copy()
        out.columns = ["Date", "Description", "Amount"]
        return out

    return pd.DataFrame(columns=["Date", "Description", "Amount"])


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_amount(raw: str) -> Optional[float]:
    """Parse a dollar amount string to float. Returns None on failure."""
    raw = raw.replace(",", "").replace("$", "").strip()
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return float(raw)
    except ValueError:
        return None


def _is_section_header(text: str) -> bool:
    """Check if the row text is a section divider, not a transaction."""
    upper = text.upper()
    return any(header in upper for header in SECTION_HEADERS)


def _is_column_header(text: str) -> bool:
    upper = text.upper()
    matches = sum(1 for marker in HEADER_MARKERS if marker in upper)
    return matches >= 2


def extract_transactions(pdf_path: str) -> pd.DataFrame:
    """Parse the PDF and return a DataFrame matching the Chase CSV format."""
    due_date = _extract_due_date(pdf_path)
    if due_date:
        print(f"Detected statement due date: {due_date.strftime('%m/%d/%Y')}")
    else:
        print("Warning: Could not detect Payment Due Date from PDF. "
              "Dates will not have a year assigned.")

    tables = _read_tables(pdf_path)
    rows = []

    for table in tables:
        normalized = _normalize_table(table)
        if normalized.empty:
            continue

        for _, row in normalized.iterrows():
            date = _clean_cell(row.get("Date"))
            description = _clean_cell(row.get("Description"))
            amount_raw = _clean_cell(row.get("Amount"))

            # Fix merged date+description (common at PDF page breaks):
            # e.g. date="02/02 Pennymac Cash ..." → split into date + desc
            m = _DATE_PREFIX_RE.match(date)
            if m:
                extra_desc = m.group(2).strip()
                date = m.group(1)
                if description:
                    description = f"{extra_desc} {description}"
                else:
                    description = extra_desc

            row_text = f"{date} {description} {amount_raw}"

            # Skip section headers and column headers
            if _is_section_header(row_text) or _is_column_header(row_text):
                continue

            # Skip empty rows
            if not date and not description and not amount_raw:
                continue

            amount = _parse_amount(amount_raw)
            if amount is None:
                continue

            # Infer Type from sign
            tx_type = "Credit" if amount >= 0 else "Debit"

            # Assign year if we have a due date
            if due_date and date:
                date = _assign_year(date, due_date)

            # Categorize
            category = _categorize(description, amount)

            rows.append({
                "Transaction Date": date,
                "Post Date": date,          # checking stmts only have one date
                "Description": description,
                "Category": category,
                "Type": tx_type,
                "Amount": amount,
                "Memo": "",
            })

    return pd.DataFrame(rows)


def save_csv(df: pd.DataFrame, csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False)


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(f"Usage: python {os.path.basename(argv[0])} <input.pdf> [output.csv]")
        return 1

    pdf_path = argv[1]

    # Derive CSV path from the PDF filename
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")

    if len(argv) >= 3:
        csv_path = argv[2]

    print(f"Reading PDF: {pdf_path}")
    df = extract_transactions(pdf_path)

    if df.empty:
        print("No transactions found. The PDF layout may need manual tuning.")
        return 1

    save_csv(df, csv_path)
    print(f"Wrote {len(df)} transactions to {csv_path}")
    print(f"Columns: {', '.join(df.columns)}")
    print(f"\nCategory breakdown:")
    print(df["Category"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
