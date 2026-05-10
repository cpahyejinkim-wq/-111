from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.common import clean_code, to_number, year_month

MONTH_RE = re.compile(r"(1[0-2]|[1-9])\s*월")


def _extract_year(sheet: str) -> int | None:
    found = re.findall(r"(20\d{2}|\d{2})", sheet)
    if not found:
        return None
    value = int(found[-1])
    return value if value > 100 else 2000 + value


def _month(value) -> int | None:
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


def _find_header(raw: pd.DataFrame) -> int:
    for idx in range(min(10, len(raw))):
        text = raw.iloc[idx].astype(str).str.cat(sep="|")
        if "계정" in text and any(_month(v) for v in raw.iloc[idx]):
            return idx
    return 0


def parse_bs_workbook(path: str | Path) -> tuple[pd.DataFrame, list[str]]:
    xls = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []
    parsed_sheets: list[str] = []
    for sheet in xls.sheet_names:
        if "BS" not in sheet.upper() and "평잔" not in sheet:
            continue
        year = _extract_year(sheet)
        if year is None:
            continue
        raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        header = _find_header(raw)
        month_cols = {c: _month(raw.iat[header, c]) for c in range(raw.shape[1])}
        month_cols = {c: m for c, m in month_cols.items() if m}
        rows = []
        for r in range(header + 1, len(raw)):
            category = str(raw.iat[r, 0]).strip() if raw.shape[1] > 0 and not pd.isna(raw.iat[r, 0]) else ""
            code = clean_code(raw.iat[r, 1] if raw.shape[1] > 1 else "")
            level = clean_code(raw.iat[r, 2] if raw.shape[1] > 2 else "")
            name = str(raw.iat[r, 3]).strip() if raw.shape[1] > 3 and not pd.isna(raw.iat[r, 3]) else ""
            if not code and not name:
                continue
            for c, month in month_cols.items():
                value = to_number(raw.iat[r, c])
                if value == 0 and (pd.isna(raw.iat[r, c]) or str(raw.iat[r, c]).strip() == ""):
                    continue
                rows.append({
                    "source_file": Path(path).name,
                    "source_sheet": sheet,
                    "year": year,
                    "year_month": year_month(year, month),
                    "month": month,
                    "bs_category": category,
                    "account_code": code,
                    "account_level": level,
                    "account_name": name,
                    "avg_balance": value,
                })
        if rows:
            frames.append(pd.DataFrame(rows))
            parsed_sheets.append(sheet)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), parsed_sheets)
