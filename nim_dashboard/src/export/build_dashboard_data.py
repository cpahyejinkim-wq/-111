from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.analytics.anomaly import detect_anomalies
from src.analytics.funding_allocation import allocate_average_funding_rate
from src.analytics.funding_cost import calculate_funding_cost
from src.analytics.interest_income import calculate_product_income
from src.analytics.nim_metrics import build_nim_decomposition, calculate_total_metrics
from src.analytics.reconciliation import reconcile
from src.common import json_sanitize
from src.export.export_json import write_json
from src.parsers.bs_parser import parse_bs_workbook
from src.parsers.mapping_loader import load_mappings
from src.parsers.pl_parser import parse_pl_workbook

ROOT = Path(__file__).resolve().parents[2]


def _read_settings(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _find_excel_files(raw_dir: Path) -> list[Path]:
    return sorted([p for p in raw_dir.glob("**/*") if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"} and not p.name.startswith("~$")])


def _sample_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    months = ["2025-01", "2025-02", "2025-03"]
    pl_rows = []
    bs_rows = []
    accounts = [
        ("410101", "오토론 이자수익", [480000000, 500000000, 530000000]),
        ("410201", "리스 이자수익", [300000000, 310000000, 315000000]),
        ("410301", "담보대출 이자수익", [220000000, 230000000, 250000000]),
        ("510101", "단기차입금 이자비용", [180000000, 185000000, 190000000]),
        ("510201", "회사채 이자비용", [260000000, 265000000, 270000000]),
        ("510301", "기업어음 이자비용", [90000000, 92000000, 96000000]),
    ]
    balances = [
        ("자산", "110101", "오토론채권", [95000000000, 97000000000, 100000000000]),
        ("자산", "110201", "리스채권", [72000000000, 73000000000, 73500000000]),
        ("자산", "110301", "담보대출채권", [54000000000, 54500000000, 55000000000]),
        ("부채", "210101", "단기차입금", [62000000000, 63000000000, 64000000000]),
        ("부채", "220101", "회사채", [101000000000, 101500000000, 102000000000]),
        ("부채", "210201", "기업어음", [31000000000, 31500000000, 32000000000]),
    ]
    for ym_idx, ym in enumerate(months):
        year, month = map(int, ym.split("-"))
        for code, name, vals in accounts:
            pl_rows.append({"source_file": "sample", "source_sheet": "월별PL_25", "year": year, "year_month": ym, "month": month, "account_code": code, "account_level": "L4", "account_name": name, "amount_type": "monthly", "amount": vals[ym_idx]})
        for cat, code, name, vals in balances:
            bs_rows.append({"source_file": "sample", "source_sheet": "평잔BS_25", "year": year, "year_month": ym, "month": month, "bs_category": cat, "account_code": code, "account_level": "L4", "account_name": name, "avg_balance": vals[ym_idx]})
    return pd.DataFrame(pl_rows), pd.DataFrame(bs_rows), ["월별PL_25(sample)"], ["평잔BS_25(sample)"]


def build_dashboard_data(root: Path = ROOT, use_sample_if_empty: bool = True) -> dict:
    settings = _read_settings(root / "config" / "settings.json")
    mappings = load_mappings(root / "mapping")
    pl_frames, bs_frames, pl_sheets, bs_sheets = [], [], [], []
    for file in _find_excel_files(root / settings.get("raw_data_dir", "data/raw")):
        pl, sheets = parse_pl_workbook(file)
        bs, bss = parse_bs_workbook(file)
        if not pl.empty:
            pl_frames.append(pl)
            pl_sheets.extend(sheets)
        if not bs.empty:
            bs_frames.append(bs)
            bs_sheets.extend(bss)
    if pl_frames or bs_frames:
        pl = pd.concat(pl_frames, ignore_index=True) if pl_frames else pd.DataFrame()
        bs = pd.concat(bs_frames, ignore_index=True) if bs_frames else pd.DataFrame()
    elif use_sample_if_empty:
        pl, bs, pl_sheets, bs_sheets = _sample_data()
    else:
        pl, bs = pd.DataFrame(), pd.DataFrame()
    product = calculate_product_income(pl, bs, mappings["product_map"])
    funding = calculate_funding_cost(pl, bs, mappings["funding_map"])
    total = calculate_total_metrics(product, funding)
    product_alloc = allocate_average_funding_rate(product, total)
    total = calculate_total_metrics(product_alloc, funding)
    reconciliation, unmapped = reconcile(pl, bs, mappings["product_map"], mappings["funding_map"], product_alloc, funding, settings)
    anomalies = detect_anomalies(product_alloc, funding, total, reconciliation, unmapped, settings)
    nim_decomp = build_nim_decomposition(product_alloc, total)
    latest = total.sort_values("year_month").tail(1).to_dict("records")
    executive = latest[0] if latest else {}
    executive.update({
        "anomaly_count": int(len(anomalies)),
        "high_anomaly_count": int((anomalies["severity"].eq("High")).sum()) if not anomalies.empty else 0,
        "reconciliation_error_count": int((reconciliation["status"].eq("Error")).sum()) if not reconciliation.empty else 0,
    })
    data = {
        "meta": {"app": settings.get("app_name", "Financial Closing Analytics Dashboard"), "version": settings.get("version", "v1.0-nim-mvp"), "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        "status": {"available_months": sorted(set(total.get("year_month", pd.Series(dtype=str)))), "pl_sheets": pl_sheets, "bs_sheets": bs_sheets, "mapping_status": mappings["mapping_status"], "sample_data_used": not bool(pl_frames or bs_frames)},
        "modules": {"nim": {"settings": settings, "executive_kpis": executive, "total_monthly": total.to_dict("records"), "product_monthly": product_alloc.to_dict("records"), "funding_monthly": funding.to_dict("records"), "allocation_summary": product_alloc[["year_month", "product_id", "product_name", "allocation_method", "allocated_interest_expense"]].to_dict("records") if not product_alloc.empty else [], "nim_decomposition": nim_decomp.to_dict("records") if not nim_decomp.empty else [], "anomalies": anomalies.to_dict("records") if not anomalies.empty else [], "reconciliation": reconciliation.to_dict("records"), "mapping_status": {**mappings["mapping_status"], "unmapped": unmapped}}},
        "future_modules": {"rate_sensitivity": {"enabled": False}, "funding_forecast": {"enabled": False}, "asset_forecast": {"enabled": False}, "nim_forecast": {"enabled": False}},
    }
    out_dir = root / settings.get("output_dir", "output")
    write_json(data, out_dir / "dashboard_data.json")
    write_json(product_alloc.to_dict("records"), out_dir / "product_monthly.json")
    write_json(funding.to_dict("records"), out_dir / "funding_monthly.json")
    write_json(total.to_dict("records"), out_dir / "total_monthly.json")
    write_json(anomalies.to_dict("records") if not anomalies.empty else [], out_dir / "anomalies.json")
    write_json(reconciliation.to_dict("records"), out_dir / "reconciliation.json")
    return json_sanitize(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-sample", action="store_true", help="raw 파일이 없어도 샘플 데이터를 생성하지 않습니다.")
    args = parser.parse_args()
    data = build_dashboard_data(use_sample_if_empty=not args.no_sample)
    print(f"dashboard_data.json generated: {len(data['status']['available_months'])} months")

if __name__ == "__main__":
    main()
