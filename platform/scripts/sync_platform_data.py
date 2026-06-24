import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.data_store import MarketDataStore, assets_from_config


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync platform market/fundamental data into the local standard store.")
    parser.add_argument("--config", default="configs/baseline_r1_domestic_rolling.yaml", help="Platform YAML config path.")
    parser.add_argument("--fetch", action="store_true", help="Call Finshare. Without this flag, only validate local standard data.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config = load_config(config_path)
    data_config = config.get("data", {})
    assets = assets_from_config(config.get("assets", []))
    backtest = config.get("backtest", {})

    market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")

    market_report = MarketDataStore(market_dir).sync_assets(
        assets,
        start=backtest.get("start_date"),
        end=backtest.get("end_date"),
        fetch=args.fetch,
    )
    print(f"Market data checked: {market_dir}")
    for note in market_report.notes:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
