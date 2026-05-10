from __future__ import annotations

import pandas as pd

from src.common import add_period_changes, annualize, safe_divide


def calculate_funding_cost(pl: pd.DataFrame, bs: pd.DataFrame, funding_map: pd.DataFrame) -> pd.DataFrame:
    cols = ["year", "month", "year_month", "funding_id", "funding_name", "funding_group", "liability_avg_balance", "interest_expense", "funding_rate_monthly", "funding_rate_annualized", "mapping_status", "include_in_funding_rate"]
    if funding_map.empty:
        return pd.DataFrame(columns=cols)
    months = sorted(set(pl.get("year_month", pd.Series(dtype=str))).union(set(bs.get("year_month", pd.Series(dtype=str)))))
    pl_monthly = pl[pl["amount_type"].eq("monthly")].copy() if not pl.empty else pd.DataFrame()
    rows = []
    for ym in months:
        year, month = map(int, ym.split("-"))
        for fid, g in funding_map.groupby("funding_id", dropna=False):
            first = g.iloc[0]
            liability_codes = set(g["liability_account_code"].dropna().astype(str).str.strip()) - {""}
            contra_codes = set(g.get("contra_account_code", pd.Series(dtype=str)).dropna().astype(str).str.strip()) - {""}
            all_bal_codes = liability_codes.union(contra_codes)
            bal = bs[(bs["year_month"].eq(ym)) & (bs["account_code"].isin(all_bal_codes))]["avg_balance"].sum() if not bs.empty and all_bal_codes else 0.0
            expense = 0.0
            for _, mrow in g.iterrows():
                code = str(mrow["expense_account_code"]).strip()
                sign = -1 if str(mrow.get("sign_policy", "original")).lower() == "reverse" else 1
                if code and not pl_monthly.empty:
                    expense += pl_monthly[(pl_monthly["year_month"].eq(ym)) & (pl_monthly["account_code"].eq(code))]["amount"].sum() * sign
            monthly = safe_divide(expense, bal)
            rows.append({
                "year": year, "month": month, "year_month": ym,
                "funding_id": fid, "funding_name": first.get("funding_name", fid), "funding_group": first.get("funding_group", ""),
                "liability_avg_balance": float(bal), "interest_expense": float(expense),
                "funding_rate_monthly": monthly, "funding_rate_annualized": annualize(monthly, year, month),
                "mapping_status": "mapped" if all_bal_codes or str(first.get("expense_account_code", "")).strip() else "missing_mapping",
                "include_in_funding_rate": first.get("include_in_funding_rate", "Y") or "Y",
            })
    out = pd.DataFrame(rows, columns=cols)
    out = add_period_changes(out, ["funding_id"], ["liability_avg_balance", "interest_expense"], ["funding_rate_annualized"])
    out = out.rename(columns={
        "mom_liability_avg_balance_change": "mom_balance_change",
        "mom_interest_expense_change": "mom_expense_change",
        "mom_funding_rate_annualized_change_bp": "mom_rate_change_bp",
        "yoy_interest_expense_change": "yoy_expense_change",
        "yoy_funding_rate_annualized_change_bp": "yoy_rate_change_bp",
    })
    return out
