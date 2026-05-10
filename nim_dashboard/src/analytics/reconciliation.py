from __future__ import annotations

import pandas as pd


def _keyword_accounts(df: pd.DataFrame, keywords: list[str], value_col: str) -> pd.DataFrame:
    if df.empty:
        return df
    pat = "|".join(keywords)
    return df[df["account_name"].astype(str).str.contains(pat, case=False, na=False)][["year_month", "account_code", "account_name", value_col]]


def reconcile(pl: pd.DataFrame, bs: pd.DataFrame, product_map: pd.DataFrame, funding_map: pd.DataFrame, product_monthly: pd.DataFrame, funding_monthly: pd.DataFrame, settings: dict) -> tuple[pd.DataFrame, dict]:
    tol = settings.get("anomaly_thresholds", {}).get("reconciliation_tolerance", 1000)
    det = settings.get("account_detection", {})
    pl_m = pl[pl["amount_type"].eq("monthly")] if not pl.empty else pd.DataFrame()
    income_src = _keyword_accounts(pl_m, det.get("interest_income_keywords", ["이자수익"]), "amount")
    expense_src = _keyword_accounts(pl_m, det.get("interest_expense_keywords", ["이자비용"]), "amount")
    asset_src = _keyword_accounts(bs, det.get("asset_keywords", ["대출", "리스"]), "avg_balance")
    liability_src = _keyword_accounts(bs, det.get("liability_keywords", ["차입", "사채"]), "avg_balance")
    months = sorted(set(pl.get("year_month", pd.Series(dtype=str))).union(set(bs.get("year_month", pd.Series(dtype=str)))))
    rows = []
    def add(ym, ctype, source, mapped, desc):
        diff = float(source - mapped)
        rows.append({"year_month": ym, "check_type": ctype, "source_total": float(source), "mapped_total": float(mapped), "difference": diff, "tolerance": tol, "status": "OK" if abs(diff) <= tol else "Error", "description": desc})
    for ym in months:
        add(ym, "PL_INTEREST_INCOME", income_src[income_src.year_month.eq(ym)]["amount"].sum() if not income_src.empty else 0, product_monthly[product_monthly.year_month.eq(ym)]["interest_income"].sum() if not product_monthly.empty else 0, "PL 이자수익 키워드 계정 합계와 상품 맵핑 합계 비교")
        add(ym, "PL_INTEREST_EXPENSE", expense_src[expense_src.year_month.eq(ym)]["amount"].sum() if not expense_src.empty else 0, funding_monthly[funding_monthly.year_month.eq(ym)]["interest_expense"].sum() if not funding_monthly.empty else 0, "PL 이자비용 키워드 계정 합계와 차입 맵핑 합계 비교")
        add(ym, "BS_EARNING_ASSETS", asset_src[asset_src.year_month.eq(ym)]["avg_balance"].sum() if not asset_src.empty else 0, product_monthly[product_monthly.year_month.eq(ym)]["avg_balance"].sum() if not product_monthly.empty else 0, "BS 여신성자산 키워드 계정 합계와 상품 맵핑 합계 비교")
        add(ym, "BS_FUNDING_LIABILITIES", liability_src[liability_src.year_month.eq(ym)]["avg_balance"].sum() if not liability_src.empty else 0, funding_monthly[funding_monthly.year_month.eq(ym)]["liability_avg_balance"].sum() if not funding_monthly.empty else 0, "BS 차입부채 키워드 계정 합계와 차입 맵핑 합계 비교")
    mapped_income = set(product_map["income_account_code"].astype(str)) if not product_map.empty else set()
    mapped_expense = set(funding_map["expense_account_code"].astype(str)) if not funding_map.empty else set()
    mapped_assets = set(product_map["asset_account_code"].astype(str)) if not product_map.empty else set()
    mapped_liabilities = set(funding_map["liability_account_code"].astype(str)).union(set(funding_map.get("contra_account_code", pd.Series(dtype=str)).astype(str))) if not funding_map.empty else set()
    unmapped = {
        "interest_income_accounts": income_src[~income_src.account_code.astype(str).isin(mapped_income)].drop_duplicates(["account_code", "account_name"]).to_dict("records") if not income_src.empty else [],
        "interest_expense_accounts": expense_src[~expense_src.account_code.astype(str).isin(mapped_expense)].drop_duplicates(["account_code", "account_name"]).to_dict("records") if not expense_src.empty else [],
        "asset_accounts": asset_src[~asset_src.account_code.astype(str).isin(mapped_assets)].drop_duplicates(["account_code", "account_name"]).to_dict("records") if not asset_src.empty else [],
        "liability_accounts": liability_src[~liability_src.account_code.astype(str).isin(mapped_liabilities)].drop_duplicates(["account_code", "account_name"]).to_dict("records") if not liability_src.empty else [],
    }
    return pd.DataFrame(rows), unmapped
