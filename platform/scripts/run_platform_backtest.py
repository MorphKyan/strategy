import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.runtime_config import apply_runtime_dates
from src.platform_core.storage import SQLiteStore


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an M0-M2 daily platform backtest.")
    parser.add_argument("--config", default="configs/baseline_r1_domestic_rolling.yaml", help="Platform YAML config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--output-dir", help="Override output root directory.")
    parser.add_argument("--start-date", help="Runtime backtest start date, YYYY-MM-DD. Defaults to earliest available data.")
    parser.add_argument("--end-date", help="Runtime backtest end date, YYYY-MM-DD. Defaults to latest available data.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    output_dir = None
    if args.output_dir:
        output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    config = apply_runtime_dates(load_config(config_path), start_date=args.start_date, end_date=args.end_date)
    store = SQLiteStore(db_path)
    try:
        result = PlatformBacktestEngine(config=config, store=store, output_dir=output_dir).run()
    finally:
        store.close()

    print(f"Platform backtest completed: {result.output_dir}")
    print(f"Run id: {result.run_id}")
    print(f"Total return: {result.metrics.get('total_return', 0.0) * 100:.2f}%")
    print(f"Trade count: {result.metrics.get('trade_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
