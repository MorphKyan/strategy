# -*- coding: utf-8 -*-
import argparse
import os
import sys
from pathlib import Path

ORIG_CWD = Path.cwd()
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

def resolve_path(path_str: str, root_dir: Path, orig_cwd: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    if (orig_cwd / p).exists():
        return orig_cwd / p
    if (root_dir / p).exists():
        return root_dir / p
    if (root_dir.parent / p).exists():
        return root_dir.parent / p
    parts = p.parts
    if parts and parts[0] == "platform":
        return root_dir.parent / p
    return root_dir / p

from src.platform_core.data_store import FundamentalStore, MarketDataStore, assets_from_config

ALL_ASSETS_DICT = [
    {"asset_id": "CN_ETF:510300.SH", "code": "510300", "name": "沪深300ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513500.SH", "code": "513500", "name": "标普500ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:518880.SH", "code": "518880", "name": "黄金ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:511260.SH", "code": "511260", "name": "十年国债ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159985.SZ", "code": "159985", "name": "豆粕ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159981.SZ", "code": "159981", "name": "能源化工ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512890.SH", "code": "512890", "name": "红利低波ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513100.SH", "code": "513100", "name": "纳指ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:510500.SH", "code": "510500", "name": "中证500ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159920.SZ", "code": "159920", "name": "恒生ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513030.SH", "code": "513030", "name": "德国ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:510880.SH", "code": "510880", "name": "红利ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
]

def main() -> int:
    parser = argparse.ArgumentParser(description="Sync all market data for all 12 assets in the universe.")
    parser.add_argument("--start-date", default="2010-01-01", help="Sync start date.")
    parser.add_argument("--data-dir", default="data", help="Local data directory.")
    parser.add_argument("--fundamentals-dir", default="data/platform_fundamentals", help="Local fundamentals directory.")
    parser.add_argument("--no-fundamentals", action="store_true", help="Skip fundamental data sync.")
    args = parser.parse_args()

    assets = assets_from_config(ALL_ASSETS_DICT)
    data_dir = resolve_path(args.data_dir, ROOT, ORIG_CWD)
    fundamentals_dir = resolve_path(args.fundamentals_dir, ROOT, ORIG_CWD)

    print("Syncing market data for all 12 universe assets from Finshare...")
    from datetime import datetime
    market_report = MarketDataStore(data_dir).sync_assets(
        assets,
        start=args.start_date,
        end=datetime.now().strftime("%Y-%m-%d"),
        fetch=True
    )
    print("Market data synced:")
    for note in market_report.notes:
        print(f"- {note}")

    if not args.no_fundamentals:
        print("\nSyncing fundamental data indicator fields...")
        fields = ["pe", "pb", "roe", "debt_to_asset", "dividend_yield"]
        fundamental_report = FundamentalStore(fundamentals_dir, fields=fields).sync_financial_indicators(
            assets,
            fetch=True
        )
        print("Fundamental data synced:")
        for note in fundamental_report.notes:
            print(f"- {note}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
