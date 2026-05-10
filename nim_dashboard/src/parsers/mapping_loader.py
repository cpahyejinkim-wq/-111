from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PRODUCT_REQUIRED = [
    "product_id", "product_name", "segment", "product_group", "asset_account_code",
    "asset_account_name", "income_account_code", "income_account_name", "income_type",
    "sign_policy", "include_in_nim", "memo",
]
FUNDING_REQUIRED = [
    "funding_id", "funding_name", "funding_group", "liability_account_code",
    "liability_account_name", "expense_account_code", "expense_account_name", "expense_type",
    "contra_account_code", "sign_policy", "include_in_funding_rate", "memo",
]
OPTIONAL_FLAGS = [
    "exclude_from_yield_analysis", "exclude_from_nim", "exclude_from_funding_rate", "exclude_from_alert",
]


def _read_csv(path: Path, required: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("") if path.exists() else pd.DataFrame(columns=required)
    for col in required + OPTIONAL_FLAGS:
        if col not in df.columns:
            df[col] = ""
    code_cols = [c for c in df.columns if c.endswith("_account_code")]
    for col in code_cols:
        df[col] = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    for col in ["sign_policy", "include_in_nim", "include_in_funding_rate"]:
        if col in df.columns:
            df[col] = df[col].replace("", "original" if col == "sign_policy" else "Y")
    return df


def load_mappings(mapping_dir: str | Path) -> dict:
    base = Path(mapping_dir)
    excluded_path = base / "excluded_items.json"
    excluded = json.loads(excluded_path.read_text(encoding="utf-8")) if excluded_path.exists() else {}
    product = _read_csv(base / "product_map.csv", PRODUCT_REQUIRED)
    funding = _read_csv(base / "funding_map.csv", FUNDING_REQUIRED)
    return {
        "product_map": product,
        "funding_map": funding,
        "excluded_items": excluded,
        "mapping_status": {
            "product_rows": int(len(product)),
            "funding_rows": int(len(funding)),
            "product_required_missing": [c for c in PRODUCT_REQUIRED if c not in product.columns],
            "funding_required_missing": [c for c in FUNDING_REQUIRED if c not in funding.columns],
        },
    }
