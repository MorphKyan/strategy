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
from src.platform_core.slippage import REQUIRED_SLIPPAGE_SCENARIOS, apply_slippage_scenario
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
    parser.add_argument(
        "--slippage-scenario",
        choices=[*REQUIRED_SLIPPAGE_SCENARIOS, "all"],
        default="all",
        help="Slippage scenario to run. Default `all` runs default, stress, and dynamic_participation.",
    )
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    output_dir = None
    if args.output_dir:
        output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    base_config = apply_runtime_dates(load_config(config_path), start_date=args.start_date, end_date=args.end_date)
    enable_db = (base_config.get("backtest") or {}).get("enable_database", False)
    if enable_db:
        store = SQLiteStore(db_path)
    else:
        from src.platform_core.storage import InMemoryStore
        store = InMemoryStore()
    try:
        scenario_names = REQUIRED_SLIPPAGE_SCENARIOS if args.slippage_scenario == "all" else (args.slippage_scenario,)
        results = []
        for scenario in scenario_names:
            config = apply_slippage_scenario(base_config, scenario)
            result = PlatformBacktestEngine(config=config, store=store, output_dir=output_dir).run()
            results.append((scenario, result))
    finally:
        store.close()

    print("Platform backtest completed.")
    for scenario, result in results:
        print(f"[{scenario}] output: {result.output_dir}")
        print(f"[{scenario}] run id: {result.run_id}")
        print(f"[{scenario}] total return: {result.metrics.get('total_return', 0.0) * 100:.2f}%")
        print(f"[{scenario}] trade count: {result.metrics.get('trade_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
