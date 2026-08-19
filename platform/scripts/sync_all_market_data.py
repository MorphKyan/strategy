# -*- coding: utf-8 -*-
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

ORIG_CWD = Path.cwd()
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.data_store import MarketDataStore, assets_from_config
from src.platform_core.sync_universe import (
    discover_fixed_configs,
    etf_assets,
    load_assets_from_configs,
    merge_assets,
    parse_asset_spec,
)


def resolve_path(path_str: str, root_dir: Path, orig_cwd: Path) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    if (orig_cwd / path).exists():
        return orig_cwd / path
    if (root_dir / path).exists():
        return root_dir / path
    if (root_dir.parent / path).exists():
        return root_dir.parent / path
    if path.parts and path.parts[0] == "platform":
        return root_dir.parent / path
    return root_dir / path


def resolve_asset_dicts(config_args: list[str], asset_args: list[str]) -> list[dict]:
    explicit_configs = [resolve_path(value, ROOT, ORIG_CWD) for value in config_args]
    if explicit_configs:
        configured = load_assets_from_configs(explicit_configs)
    elif asset_args:
        configured = []
    else:
        config_paths = discover_fixed_configs(ROOT / "configs")
        configured = etf_assets(load_assets_from_configs(config_paths))
        print(f"No --config supplied; discovered ETFs from {len(config_paths)} fixed platform configs.")
    direct = [parse_asset_spec(value) for value in asset_args]
    assets = merge_assets(configured, direct)
    if not assets:
        raise ValueError("No assets were resolved. Supply --config or --asset.")
    return assets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync market data for assets resolved from platform configs or command-line ETF codes."
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Platform YAML config whose assets should be synced. Repeat for multiple configs.",
    )
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        help="Additional asset as CODE[.EXCHANGE][:TYPE][=NAME]; TYPE defaults to etf. Repeatable.",
    )
    parser.add_argument("--start-date", default="2010-01-01", help="Sync start date.")
    parser.add_argument("--data-dir", default="data", help="Local data directory.")
    args = parser.parse_args(argv)

    asset_dicts = resolve_asset_dicts(args.config, args.asset)
    assets = assets_from_config(asset_dicts)
    data_dir = resolve_path(args.data_dir, ROOT, ORIG_CWD)

    print(f"Syncing market data for {len(assets)} resolved assets from Finshare...")
    market_report = MarketDataStore(data_dir).sync_assets(
        assets,
        start=args.start_date,
        end=datetime.now().strftime("%Y-%m-%d"),
        fetch=True,
    )
    print("Market data synced:")
    for note in market_report.notes:
        print(f"- {note}")

    etfs = etf_assets(asset_dicts)
    if etfs:
        print(f"\nFetching dividend and split histories for {len(etfs)} resolved ETFs...")
        from scripts.fetch_etf_dividends import sync_etf_corporate_actions

        sync_etf_corporate_actions(etfs, data_dir=data_dir)
        print("ETF dividend and split data synced successfully.")
    else:
        print("\nNo ETF assets resolved; skipped dividend and split sync.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
