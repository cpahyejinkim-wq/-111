from __future__ import annotations

import pandas as pd

from src.common import annualize


def allocate_average_funding_rate(product_monthly: pd.DataFrame, total_monthly: pd.DataFrame) -> pd.DataFrame:
    if product_monthly.empty:
        return product_monthly.copy()
    rate = total_monthly[["year_month", "total_funding_rate_monthly"]].copy() if not total_monthly.empty else pd.DataFrame(columns=["year_month", "total_funding_rate_monthly"])
    out = product_monthly.merge(rate, on="year_month", how="left")
    out["allocation_method"] = "average_funding_rate"
    out["allocated_interest_expense"] = out["avg_balance"] * out["total_funding_rate_monthly"].fillna(0)
    out["net_interest_income"] = out["interest_income"] - out["allocated_interest_expense"]
    out["nim_monthly"] = out.apply(lambda r: None if abs(r["avg_balance"]) < 1e-12 else r["net_interest_income"] / r["avg_balance"], axis=1)
    out["nim_annualized"] = out.apply(lambda r: annualize(r["nim_monthly"], int(r["year"]), int(r["month"])), axis=1)
    return out
