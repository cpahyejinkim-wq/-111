from __future__ import annotations

import pandas as pd

from src.common import add_period_changes, annualize, safe_divide


def calculate_total_metrics(product_monthly: pd.DataFrame, funding_monthly: pd.DataFrame) -> pd.DataFrame:
    months = sorted(set(product_monthly.get("year_month", pd.Series(dtype=str))).union(set(funding_monthly.get("year_month", pd.Series(dtype=str)))))
    rows = []
    for ym in months:
        year, month = map(int, ym.split("-"))
        p = product_monthly[(product_monthly["year_month"].eq(ym)) & (product_monthly["include_in_nim"].fillna("Y").eq("Y"))] if not product_monthly.empty else pd.DataFrame()
        f = funding_monthly[(funding_monthly["year_month"].eq(ym)) & (funding_monthly["include_in_funding_rate"].fillna("Y").eq("Y"))] if not funding_monthly.empty else pd.DataFrame()
        asset = p["avg_balance"].sum() if not p.empty else 0.0
        income = p["interest_income"].sum() if not p.empty else 0.0
        liability = f["liability_avg_balance"].sum() if not f.empty else 0.0
        expense = f["interest_expense"].sum() if not f.empty else 0.0
        net = income - expense
        asset_yield = safe_divide(income, asset)
        funding_rate = safe_divide(expense, liability)
        nim = safe_divide(net, asset)
        rows.append({
            "year": year, "month": month, "year_month": ym,
            "total_earning_assets_avg_balance": float(asset),
            "total_interest_income": float(income),
            "total_interest_expense": float(expense),
            "total_funding_liability_avg_balance": float(liability),
            "total_asset_yield_monthly": asset_yield,
            "total_asset_yield_annualized": annualize(asset_yield, year, month),
            "total_funding_rate_monthly": funding_rate,
            "total_funding_rate_annualized": annualize(funding_rate, year, month),
            "net_interest_income": float(net),
            "nim_monthly": nim,
            "nim_annualized": annualize(nim, year, month),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = add_period_changes(out, [], ["net_interest_income"], ["nim_annualized"])
    return out.rename(columns={"mom_nim_annualized_change_bp": "mom_nim_change_bp", "yoy_nim_annualized_change_bp": "yoy_nim_change_bp"})


def build_nim_decomposition(allocated_products: pd.DataFrame, total_monthly: pd.DataFrame) -> pd.DataFrame:
    if allocated_products.empty:
        return pd.DataFrame()
    totals = total_monthly[["year_month", "net_interest_income"]].rename(columns={"net_interest_income": "total_net_interest_income"})
    out = allocated_products.merge(totals, on="year_month", how="left")
    out["nim_contribution"] = out.apply(lambda r: None if not r.get("total_net_interest_income") else r["net_interest_income"] / r["total_net_interest_income"], axis=1)
    out["spread_annualized"] = out["nim_annualized"]
    return out[["year_month", "product_id", "product_name", "product_group", "avg_balance", "interest_income", "gross_yield_annualized", "allocated_interest_expense", "net_interest_income", "nim_annualized", "nim_contribution", "allocation_method"]]
