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

from src.platform_core.data_store import MarketDataStore, assets_from_config

ALL_ASSETS_DICT = [
    {"asset_id": "CN_ETF:510300.SH", "code": "510300", "name": "沪深300ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513500.SH", "code": "513500", "name": "标普500ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:518880.SH", "code": "518880", "name": "黄金ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:511260.SH", "code": "511260", "name": "十年国债ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:511090.SH", "code": "511090", "name": "30年国债ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159985.SZ", "code": "159985", "name": "豆粕ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159981.SZ", "code": "159981", "name": "能源化工ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512890.SH", "code": "512890", "name": "红利低波ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513100.SH", "code": "513100", "name": "纳指ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:510500.SH", "code": "510500", "name": "中证500ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159920.SZ", "code": "159920", "name": "恒生ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:513030.SH", "code": "513030", "name": "德国ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:510880.SH", "code": "510880", "name": "红利ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    # --- R039 行业轮动候选池（docs/r039_rotation_blueprint.md §3）---
    {"asset_id": "CN_ETF:512880.SH", "code": "512880", "name": "证券ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512800.SH", "code": "512800", "name": "银行ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512010.SH", "code": "512010", "name": "医药ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159928.SZ", "code": "159928", "name": "消费ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512690.SH", "code": "512690", "name": "酒ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512660.SH", "code": "512660", "name": "军工ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512400.SH", "code": "512400", "name": "有色金属ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512980.SH", "code": "512980", "name": "传媒ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:515000.SH", "code": "515000", "name": "科技ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512480.SH", "code": "512480", "name": "半导体ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:515050.SH", "code": "515050", "name": "5G通信ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:512200.SH", "code": "512200", "name": "房地产ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:515220.SH", "code": "515220", "name": "煤炭ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:515700.SH", "code": "515700", "name": "新能车ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:515210.SH", "code": "515210", "name": "钢铁ETF", "asset_type": "etf", "exchange": "SH", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
    {"asset_id": "CN_ETF:159996.SZ", "code": "159996", "name": "家电ETF", "asset_type": "etf", "exchange": "SZ", "currency": "CNY", "lot_size": 100, "price_limit_pct": 0.1},
]

def main() -> int:
    parser = argparse.ArgumentParser(description="Sync all market data for all 12 assets in the universe.")
    parser.add_argument("--start-date", default="2010-01-01", help="Sync start date.")
    parser.add_argument("--data-dir", default="data", help="Local data directory.")
    args = parser.parse_args()

    assets = assets_from_config(ALL_ASSETS_DICT)
    data_dir = resolve_path(args.data_dir, ROOT, ORIG_CWD)

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

    print("\nFetching and syncing ETF dividend and split histories...")
    try:
        from scripts.fetch_etf_dividends import main as sync_dividends
        sync_dividends()
        print("ETF dividend and split data synced successfully.")
    except Exception as e:
        print(f"Warning: Failed to fetch ETF dividend/split data: {e}")

    print("\nGenerating simulated 30-year bond futures (3x leveraged 10-year Treasury ETF)...")
    try:
        from scripts.generate_leveraged_etf import generate_3x_etf
        generate_3x_etf()
        print("Simulated 30-year bond futures generated successfully.")
    except Exception as e:
        print(f"Warning: Failed to generate simulated 30-year bond futures: {e}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
