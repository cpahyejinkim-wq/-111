from __future__ import annotations

import pandas as pd

from src.common import add_period_changes, annualize, safe_divide


def calculate_product_income(pl: pd.DataFrame, bs: pd.DataFrame, product_map: pd.DataFrame) -> pd.DataFrame:
    cols = ["year", "month", "year_month", "product_id", "product_name", "segment", "product_group", "avg_balance", "interest_income", "gross_yield_monthly", "gross_yield_annualized", "mapping_status", "include_in_nim"]
    if product_map.empty:
        return pd.DataFrame(columns=cols)
    months = sorted(set(pl.get("year_month", pd.Series(dtype=str))).union(set(bs.get("year_month", pd.Series(dtype=str)))))
    rows = []
    pl_monthly = pl[pl["amount_type"].eq("monthly")].copy() if not pl.empty else pd.DataFrame()
    for ym in months:
        year, month = map(int, ym.split("-"))
        for pid, g in product_map.groupby("product_id", dropna=False):
            first = g.iloc[0]
            asset_codes = set(g["asset_account_code"].dropna().astype(str).str.strip()) - {""}
            income_codes = set(g["income_account_code"].dropna().astype(str).str.strip()) - {""}
            bal = bs[(bs["year_month"].eq(ym)) & (bs["account_code"].isin(asset_codes))]["avg_balance"].sum() if not bs.empty and asset_codes else 0.0
            inc_df = pl_monthly[(pl_monthly["year_month"].eq(ym)) & (pl_monthly["account_code"].isin(income_codes))] if not pl_monthly.empty and income_codes else pd.DataFrame()
            income = 0.0
            if not inc_df.empty:
                for _, mrow in g.iterrows():
                    code = str(mrow["income_account_code"]).strip()
                    sign = -1 if str(mrow.get("sign_policy", "original")).lower() == "reverse" else 1
                    income += inc_df[inc_df["account_code"].eq(code)]["amount"].sum() * sign
            monthly = safe_divide(income, bal)
            rows.append({
                "year": year, "month": month, "year_month": ym,
                "product_id": pid, "product_name": first.get("product_name", pid),
                "segment": first.get("segment", ""), "product_group": first.get("product_group", ""),
                "avg_balance": float(bal), "interest_income": float(income),
                "gross_yield_monthly": monthly,
                "gross_yield_annualized": annualize(monthly, year, month),
                "mapping_status": "mapped" if asset_codes or income_codes else "missing_mapping",
                "include_in_nim": first.get("include_in_nim", "Y") or "Y",
            })
    out = pd.DataFrame(rows, columns=cols)
    out = add_period_changes(out, ["product_id"], ["avg_balance", "interest_income"], ["gross_yield_annualized"])
    out = out.rename(columns={
        "mom_avg_balance_change": "mom_balance_change",
        "mom_interest_income_change": "mom_income_change",
        "mom_gross_yield_annualized_change_bp": "mom_yield_change_bp",
        "yoy_interest_income_change": "yoy_income_change",
        "yoy_gross_yield_annualized_change_bp": "yoy_yield_change_bp",
    })
    return out
