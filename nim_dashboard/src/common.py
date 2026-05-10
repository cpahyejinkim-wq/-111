from __future__ import annotations

import calendar
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def repo_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def clean_code(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def to_number(value: Any) -> float:
    if pd.isna(value) or value == "":
        return 0.0
    if isinstance(value, str):
        value = value.replace(",", "").replace(" ", "")
        if value in {"-", ""}:
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or abs(float(denominator)) < 1e-12:
        return None
    return float(numerator) / float(denominator)


def year_month(year: int, month: int) -> str:
    return f"{int(year):04d}-{int(month):02d}"


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(int(year), int(month))[1]


def days_in_year(year: int) -> int:
    return 366 if calendar.isleap(int(year)) else 365


def annualize(monthly_rate: float | None, year: int, month: int) -> float | None:
    if monthly_rate is None or pd.isna(monthly_rate):
        return None
    return float(monthly_rate) / days_in_month(year, month) * days_in_year(year)


def add_period_changes(df: pd.DataFrame, keys: list[str], value_cols: list[str], rate_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy().sort_values(keys + ["year_month"])
    for col in value_cols:
        out[f"mom_{col}_change"] = out.groupby(keys)[col].diff() if keys else out[col].diff()
        prev_year = out.copy()
        prev_year["year"] = prev_year["year"] + 1
        prev_year = prev_year[keys + ["year", "month", col]].rename(columns={col: f"prev_year_{col}"})
        out = out.merge(prev_year, on=keys + ["year", "month"], how="left")
        out[f"yoy_{col}_change"] = out[col] - out[f"prev_year_{col}"]
        out = out.drop(columns=[f"prev_year_{col}"])
    for col in rate_cols:
        out[f"mom_{col}_change_bp"] = (out.groupby(keys)[col].diff() if keys else out[col].diff()) * 10000
        prev_year = out.copy()
        prev_year["year"] = prev_year["year"] + 1
        prev_year = prev_year[keys + ["year", "month", col]].rename(columns={col: f"prev_year_{col}"})
        out = out.merge(prev_year, on=keys + ["year", "month"], how="left")
        out[f"yoy_{col}_change_bp"] = (out[col] - out[f"prev_year_{col}"]) * 10000
        out = out.drop(columns=[f"prev_year_{col}"])
    return out


def json_sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if pd.isna(obj) if not isinstance(obj, (str, bytes, bool, type(None))) else False:
        return None
    return obj
