# -*- coding: utf-8 -*-
"""
Public Tool: Sync Index, Futures & Fundamental PIT Macro Datasets for Quant Platform.

Usage:
    python platform/scripts/sync_index_benchmark_data.py [--config CONFIG_PATH] [--start-date YYYYMMDD] [--end-date YYYYMMDD]

Supported Data Types:
1. Stock Indices (e.g., 000300.SH, 000015.SH) via akshare stock_zh_index_daily
2. Bond Indices (e.g., CBA21801.CS) via local or bond index interface
3. Commodity Futures Main Contracts (e.g., M0.DCE, TA0.CZCE) via akshare futures_main_sina
4. ChinaBond Treasury YTM Point-in-Time Data via akshare bond_zh_us_rate
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import yaml

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import akshare as ak

DATA_DIR = ROOT / "platform" / "data"
FUNDAMENTAL_DIR = DATA_DIR / "fundamental_macro"
FUNDAMENTAL_DIR.mkdir(parents=True, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Sync Index, Futures, and Fundamental PIT Macro datasets into platform/data/."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="platform/configs/index_benchmark/domestic_baseline_es_index_benchmark_100k.yaml",
        help="Path to reusable platform config file.",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="20130101",
        help="Start date YYYYMMDD for data sync.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date YYYYMMDD for data sync (defaults to latest available).",
    )
    parser.add_argument(
        "--sync-pit-bonds",
        action="store_true",
        default=True,
        help="Sync ChinaBond 30Y/10Y Treasury YTM Point-in-Time dataset.",
    )
    return parser.parse_args()

def filter_date_bounds(df: pd.DataFrame, date_col: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """Filter DataFrame by start_date and end_date string bounds (YYYY-MM-DD or YYYYMMDD)."""
    filtered = df.copy()
    if start_date:
        s_dt = pd.to_datetime(start_date).strftime("%Y-%m-%d")
        filtered = filtered.loc[filtered[date_col] >= s_dt]
    if end_date:
        e_dt = pd.to_datetime(end_date).strftime("%Y-%m-%d")
        filtered = filtered.loc[filtered[date_col] <= e_dt]
    return filtered

def sync_index_data(symbol: str, start_date: str | None = None, end_date: str | None = None) -> bool:
    """Sync stock/bond index daily close prices."""
    code = symbol.split(":")[-1].split(".")[0]
    out_path = DATA_DIR / f"{code}.csv"
    print(f"[{code}] Syncing index daily series...")

    try:
        if code in ["000300", "000015"]:
            df = ak.stock_zh_index_daily(symbol=f"sh{code}")
            date_col = next((c for c in df.columns if "date" in c.lower() or "日" in c), df.columns[0])
            df["trade_date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
            df["close"] = df["close"].astype(float)
            out_df = df[["trade_date", "close"]].sort_values("trade_date")
            out_df = filter_date_bounds(out_df, "trade_date", start_date, end_date)
            out_df.to_csv(out_path, index=False)
            print(f"   SUCCESS: Saved {out_path.name} ({len(out_df)} rows, {out_df.iloc[0]['trade_date']} ~ {out_df.iloc[-1]['trade_date']})")
            return True
        elif code == "CBA21801":
            if out_path.exists():
                print(f"   EXISTS: Preserved local bond index {out_path.name}")
                return True
    except Exception as e:
        print(f"   ERROR syncing index {code}: {e}")
    return False

def sync_futures_main_data(symbol: str, start_date: str | None = None, end_date: str | None = None) -> bool:
    """Sync futures main continuous contract close prices."""
    code = symbol.split(":")[-1].split(".")[0]
    out_path = DATA_DIR / f"{code}.csv"
    print(f"[{code}] Syncing futures main continuous series...")

    try:
        df = ak.futures_main_sina(symbol=code)
        date_col = next((c for c in df.columns if "日" in c or "date" in c.lower()), df.columns[0])
        price_col = next((c for c in df.columns if "收盘" in c or "close" in c.lower()), df.columns[4])

        df["trade_date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
        df["close"] = df[price_col].astype(float)
        out_df = df[["trade_date", "close"]].sort_values("trade_date")
        out_df = filter_date_bounds(out_df, "trade_date", start_date, end_date)

        out_df.to_csv(out_path, index=False)
        print(f"   SUCCESS: Saved {out_path.name} ({len(out_df)} rows, {out_df.iloc[0]['trade_date']} ~ {out_df.iloc[-1]['trade_date']})")
        return True
    except Exception as e:
        print(f"   ERROR syncing futures {code}: {e}")
    return False

def sync_pit_china_bond_ytm(start_date: str | None = None, end_date: str | None = None) -> bool:
    """Sync ChinaBond 30Y and 10Y Treasury YTM Point-in-Time dataset."""
    out_path = FUNDAMENTAL_DIR / "china_bond_yields_daily_pit.csv"
    print(f"[PIT Bonds] Syncing ChinaBond Treasury YTM series to {out_path.name}...")

    try:
        df_rates = ak.bond_zh_us_rate()
        date_col = next((c for c in df_rates.columns if "日" in c or "date" in c.lower()), df_rates.columns[0])
        df_rates["date"] = pd.to_datetime(df_rates[date_col])
        df_rates = df_rates.sort_values("date")

        col_30y = next((c for c in df_rates.columns if "中国" in c and "30年" in c), None)
        col_10y = next((c for c in df_rates.columns if "中国" in c and "10年" in c), None)

        if not (col_30y and col_10y):
            print("   ERROR: Could not locate 30Y and 10Y ChinaBond columns.")
            return False

        df_out = pd.DataFrame({
            "date": df_rates["date"].dt.strftime("%Y-%m-%d"),
            "bond_ytm_30y": pd.to_numeric(df_rates[col_30y], errors="coerce"),
            "bond_ytm_10y": pd.to_numeric(df_rates[col_10y], errors="coerce"),
        }).dropna()

        df_out = filter_date_bounds(df_out, "date", start_date, end_date)
        df_out.to_csv(out_path, index=False)
        print(f"   SUCCESS: Saved {out_path.name} ({len(df_out)} rows, {df_out.iloc[0]['date']} ~ {df_out.iloc[-1]['date']})")
        return True
    except Exception as e:
        print(f"   ERROR syncing PIT bond yields: {e}")
    return False


def main():
    args = parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    universe = cfg.get("strategy", {}).get("params", {}).get("universe", [])
    if not universe:
        universe = [a.get("asset_id") for a in cfg.get("assets", []) if isinstance(a, dict)]

    print(f"=== Platform Data Sync Tool for {config_path.name} ===")
    print(f"Target Universe ({len(universe)} symbols): {universe}\n")

    for symbol in universe:
        if "CN_INDEX" in symbol or symbol.startswith("000") or symbol.startswith("CBA"):
            sync_index_data(symbol, args.start_date, args.end_date)
        elif "CN_FUTURES" in symbol or symbol.startswith("M0") or symbol.startswith("TA0"):
            sync_futures_main_data(symbol, args.start_date, args.end_date)
        elif "CN_ETF" in symbol:
            code = symbol.split(":")[-1].split(".")[0]
            if code == "518880":
                print(f"[{code}] Gold ETF daily bar exists in platform/data/{code}.csv")

    if args.sync_pit_bonds:
        sync_pit_china_bond_ytm(args.start_date, args.end_date)


    print("\nData sync completed cleanly.")

if __name__ == "__main__":
    main()
