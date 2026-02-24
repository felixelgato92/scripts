# Copilot Instructions

## Project Overview

This is a Python scripting project for processing financial statements (PDF → CSV) and uploading them to Google Sheets. It uses `tabula-py` and `pdfplumber` for PDF extraction, `pandas` for data manipulation, and `gspread` for Google Sheets integration.

## Python Best Practices

- **Type hints**: Use type hints on all function signatures. Use `Optional`, `List`, `Dict`, etc. from `typing` for compatibility.
- **Docstrings**: Every function must have a concise docstring explaining what it does and what it returns.
- **Small, focused functions**: Keep functions short and single-purpose. Extract helpers rather than writing long procedural blocks.
- **Constants at the top**: Configuration values (file paths, sheet names, column sets) go at the module level as named constants.
- **Explicit over implicit**: Avoid relying on pandas silently inferring types or dates. Always specify `format` or expected columns explicitly when possible.
- **Error handling**: Use specific exception types. Print actionable error messages. Avoid bare `except:` — at minimum use `except Exception`.
- **Data integrity**: When converting DataFrames for upload, preserve numeric types. Only apply `fillna('')` to string/object columns, never to numeric columns.
- **Google Sheets uploads**: Always pass `value_input_option='USER_ENTERED'` to `append_row()` and `append_rows()` so values are interpreted correctly.
- **File I/O**: Use `os.makedirs(..., exist_ok=True)` before writing to subdirectories. Use pathlib or `os.path` for path construction.
- **CSV output**: Place generated CSV files in the `statements/` folder.

## Debugging

- **Never remove `pdb` imports or `set_trace()` calls.** These are intentionally placed by the developer for debugging. Do not delete, comment out, or refactor away any `import pdb`, `from pdb import set_trace`, `pdb.set_trace()`, or `breakpoint()` calls.

## Code Style

- Follow PEP 8 conventions.
- Use `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for constants.
- Prefix private/internal helper functions with `_` (e.g., `_clean_cell`, `_parse_amount`).
- Keep imports organized: stdlib → third-party → local, separated by blank lines.
- Prefer f-strings for string formatting.
