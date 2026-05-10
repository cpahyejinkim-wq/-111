from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.common import clean_code, to_number, year_month

MONTH_RE = re.compile(r"(1[0-2]|[1-9])\s*월")


def _extract_year(sheet: str, default_century: int = 2000) -> int | None:
    found = re.findall(r"(20\d{2}|\d{2})", sheet)
    if not found:
        return None
    value = int(found[-1])
    return value if value > 100 else default_century + value


def _month_from_cell(value) -> int | None:
    if pd.isna(value):
        return None
    text = str(value)
    m = MONTH_RE.search(text)
    if m:
        return int(m.group(1))
    try:
        n = int(float(text))
        return n if 1 <= n <= 12 else None
    except ValueError:
        return None


def _find_header(raw: pd.DataFrame) -> tuple[int, int] | None:
    for idx in range(min(10, len(raw) - 1)):
        row = raw.iloc[idx].astype(str).str.cat(sep="|")
        next_row = raw.iloc[idx + 1].astype(str).str.cat(sep="|")
        if "계정" in row and ("잔액" in next_row or "증감" in next_row):
            return idx, idx + 1
    return (0, 1) if len(raw) > 1 else None


def parse_pl_workbook(path: str | Path) -> tuple[pd.DataFrame, list[str]]:
    xls = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []
    parsed_sheets: list[str] = []
    for sheet in xls.sheet_names:
        if "PL" not in sheet.upper() and "손익" not in sheet and "월별PL" not in sheet:
            continue
        year = _extract_year(sheet)
        if year is None:
            continue
        raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        header = _find_header(raw)
        if header is None:
            continue
        h1, h2 = header
        month_by_col: dict[int, int] = {}
        current_month = None
        for col in range(raw.shape[1]):
            month = _month_from_cell(raw.iat[h1, col])
            if month:
                current_month = month
            if current_month:
                month_by_col[col] = current_month
        rows = []
        for r in range(h2 + 1, len(raw)):
            code = clean_code(raw.iat[r, 0] if raw.shape[1] > 0 else "")
            name = str(raw.iat[r, 2]).strip() if raw.shape[1] > 2 and not pd.isna(raw.iat[r, 2]) else ""
            if not code and not name:
                continue
            level = clean_code(raw.iat[r, 1] if raw.shape[1] > 1 else "")
            for c, month in month_by_col.items():
                sub = str(raw.iat[h2, c]).strip() if not pd.isna(raw.iat[h2, c]) else ""
                if month == 1 and ("증감" not in sub):
                    amount_type = "monthly"
                elif "증감" in sub:
                    amount_type = "monthly"
                elif "잔액" in sub or sub == "":
                    amount_type = "cumulative"
                else:
                    continue
                amount = to_number(raw.iat[r, c])
                rows.append({
                    "source_file": Path(path).name,
                    "source_sheet": sheet,
                    "year": year,
                    "year_month": year_month(year, month),
                    "month": month,
                    "account_code": code,
                    "account_level": level,
                    "account_name": name,
                    "amount_type": amount_type,
                    "amount": amount,
                })
        if rows:
            frames.append(pd.DataFrame(rows))
            parsed_sheets.append(sheet)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), parsed_sheets)
