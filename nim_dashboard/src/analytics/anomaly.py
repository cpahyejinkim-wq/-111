from __future__ import annotations

import pandas as pd


def _add(rows, severity, year_month, area, item_type, item_id, item_name, metric, reason, suggested, value=None, previous_value=None, change=None, change_bp=None, account_code="", account_name=""):
    rows.append({
        "severity": severity, "year_month": year_month, "area": area, "item_type": item_type,
        "item_id": item_id, "item_name": item_name, "account_code": account_code, "account_name": account_name,
        "metric": metric, "value": value, "previous_value": previous_value, "change": change, "change_bp": change_bp,
        "reason": reason, "suggested_check": suggested,
    })


def detect_anomalies(product_monthly: pd.DataFrame, funding_monthly: pd.DataFrame, total_monthly: pd.DataFrame, reconciliation: pd.DataFrame, unmapped: dict, settings: dict) -> pd.DataFrame:
    t = settings.get("anomaly_thresholds", {})
    warn_bp = t.get("warn_bp", 50)
    alert_bp = t.get("alert_bp", 100)
    small = t.get("small_balance_threshold", 1_000_000)
    rows = []
    for kind, area, metric in [
        ("interest_income_accounts", "상품별 이자수익", "unmapped_interest_income"),
        ("interest_expense_accounts", "차입금별 이자비용", "unmapped_interest_expense"),
        ("asset_accounts", "상품별 이자수익", "unmapped_asset"),
        ("liability_accounts", "차입금별 이자비용", "unmapped_liability"),
    ]:
        for acc in unmapped.get(kind, []):
            _add(rows, "High", acc.get("year_month", ""), area, "account", acc.get("account_code", ""), acc.get("account_name", ""), metric, "맵핑 테이블에 없는 계정입니다.", "product_map.csv 또는 funding_map.csv 맵핑 추가 여부를 확인하세요.", value=acc.get("amount", acc.get("avg_balance")), account_code=acc.get("account_code", ""), account_name=acc.get("account_name", ""))
    if not product_monthly.empty:
        for _, r in product_monthly.iterrows():
            if abs(r["avg_balance"]) <= small and abs(r["interest_income"]) > 0:
                _add(rows, "High", r.year_month, "상품별 이자수익", "product", r.product_id, r.product_name, "interest_income", "평잔이 0 또는 극소액인데 이자수익이 발생했습니다.", "자산계정 맵핑 누락, 월별 평잔 원장, 이자계정 귀속을 확인하세요.", r.interest_income)
            if abs(r["avg_balance"]) > small and abs(r["interest_income"]) == 0:
                _add(rows, "Medium", r.year_month, "상품별 이자수익", "product", r.product_id, r.product_name, "interest_income", "평잔이 있으나 이자수익이 0입니다.", "이자수익 계정 맵핑 또는 해당월 수익 인식 여부를 확인하세요.", r.interest_income)
            bp = r.get("mom_yield_change_bp")
            if pd.notna(bp) and abs(bp) >= warn_bp:
                _add(rows, "High" if abs(bp) >= alert_bp else "Medium", r.year_month, "상품별 이자수익", "product", r.product_id, r.product_name, "gross_yield_annualized", "상품별 연환산 이자수익률이 전월 대비 임계값 이상 변동했습니다.", "상품별 금리, 연체이자, 이연손익, 평잔 급변 여부를 확인하세요.", r.gross_yield_annualized, change_bp=bp)
            nim = r.get("nim_annualized")
            if pd.notna(nim) and nim < 0:
                _add(rows, "Medium", r.year_month, "NIM 분해", "product", r.product_id, r.product_name, "nim_annualized", "상품별 NIM이 음수입니다.", "상품별 수익률, 배분 조달비용, 맵핑 오류를 확인하세요.", nim)
    if not funding_monthly.empty:
        for _, r in funding_monthly.iterrows():
            if abs(r["liability_avg_balance"]) <= small and abs(r["interest_expense"]) > 0:
                _add(rows, "High", r.year_month, "차입금별 이자비용", "funding", r.funding_id, r.funding_name, "interest_expense", "부채평잔이 0 또는 극소액인데 이자비용이 발생했습니다.", "부채계정 맵핑 누락, 할인차금 계정, 이자비용 귀속을 확인하세요.", r.interest_expense)
            if abs(r["liability_avg_balance"]) > small and abs(r["interest_expense"]) == 0:
                _add(rows, "Medium", r.year_month, "차입금별 이자비용", "funding", r.funding_id, r.funding_name, "interest_expense", "부채평잔이 있으나 이자비용이 0입니다.", "이자비용 계정 맵핑 또는 무이자/미인식 사유를 확인하세요.", r.interest_expense)
            bp = r.get("mom_rate_change_bp")
            if pd.notna(bp) and abs(bp) >= warn_bp:
                _add(rows, "High" if abs(bp) >= alert_bp else "Medium", r.year_month, "차입금별 이자비용", "funding", r.funding_id, r.funding_name, "funding_rate_annualized", "차입유형별 연환산 조달금리가 전월 대비 임계값 이상 변동했습니다.", "차입 조건 변경, 만기/신규 조달, 수수료/할인차금 계정을 확인하세요.", r.funding_rate_annualized, change_bp=bp)
    if not total_monthly.empty:
        for _, r in total_monthly.iterrows():
            bp = r.get("mom_nim_change_bp")
            if pd.notna(bp) and abs(bp) >= warn_bp:
                _add(rows, "High" if abs(bp) >= alert_bp else "Medium", r.year_month, "Executive", "total", "TOTAL", "총 NIM", "nim_annualized", "총 NIM이 전월 대비 임계값 이상 변동했습니다.", "총 이자수익, 총 이자비용, 자산평잔 변동 원인을 확인하세요.", r.nim_annualized, change_bp=bp)
    if not reconciliation.empty:
        for _, r in reconciliation[reconciliation.status.eq("Error")].iterrows():
            _add(rows, "High", r.year_month, "맵핑 / 검증", "reconciliation", r.check_type, r.check_type, "difference", "검증 합계가 허용오차를 초과했습니다.", r.description, r.difference, change=r.difference)
    return pd.DataFrame(rows)
