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
from src.platform_core.slippage import REQUIRED_SLIPPAGE_SCENARIOS, apply_slippage_scenario, resolve_slippage_scenarios
from src.platform_core.storage import SQLiteStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an M0-M2 daily platform backtest.")
    parser.add_argument("--config", default="configs/domestic_rolling_bond_10y.yaml", help="Platform YAML config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--output-dir", help="Override output root directory.")
    parser.add_argument("--start-date", help="Runtime backtest start date, YYYY-MM-DD. Defaults to earliest available data.")
    parser.add_argument("--end-date", help="Runtime backtest end date, YYYY-MM-DD. Defaults to latest available data.")
    parser.add_argument(
        "--slippage-scenario",
        choices=[*REQUIRED_SLIPPAGE_SCENARIOS, "standard", "all"],
        default="standard",
        help="默认 standard 运行 default + stress；all 额外运行 dynamic_participation。",
    )
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    output_dir = None
    if args.output_dir:
        output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    base_config = apply_runtime_dates(yaml.safe_load(config_path.read_text(encoding="utf-8")),
                                      start_date=args.start_date, end_date=args.end_date)
    enable_db = (base_config.get("backtest") or {}).get("enable_database", False)
    if enable_db:
        store = SQLiteStore(db_path)
    else:
        from src.platform_core.storage import InMemoryStore
        store = InMemoryStore()
    try:
        scenario_names = resolve_slippage_scenarios(args.slippage_scenario)
        results = []
        for scenario in scenario_names:
            config = apply_slippage_scenario(base_config, scenario)
            result = PlatformBacktestEngine(config=config, store=store, output_dir=output_dir,
                                           config_path=config_path).run()
            results.append((scenario, result))
    finally:
        store.close()

    print("Platform backtest completed.")
    for scenario, result in results:
        print(f"[{scenario}] output: {result.output_dir}")
        print(f"[{scenario}] run id: {result.run_id}")
        total_return = result.metrics.get("total_return")
        print(f"[{scenario}] total return: {format(total_return, '.2%') if total_return is not None else 'N/A'}")
        print(f"[{scenario}] trade count: {result.metrics.get('trade_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
