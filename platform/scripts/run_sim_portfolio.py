import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import SQLiteStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or advance a simulated portfolio from a platform checkpoint.")
    parser.add_argument("--config", default="configs/domestic_rolling_bond_10y.yaml", help="Platform YAML config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--checkpoint", help="新组合的初始 checkpoint；已有 --portfolio-id 时从已保存状态续跑。")
    parser.add_argument("--asof-date", required=True, help="Advance through this date, YYYY-MM-DD.")
    parser.add_argument("--portfolio-id", help="Stable simulated portfolio id.")
    parser.add_argument("--output-dir", help="Override simulated portfolio output root.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    output_dir = None
    if args.output_dir:
        output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sim_root = Path(output_dir or config.get("output", {}).get("sim_dir", "results/sim_portfolios"))
    resume = bool(args.portfolio_id and (sim_root / args.portfolio_id / "portfolio_state.json").exists())
    if not resume and not args.checkpoint:
        parser.error("新建模拟组合需要 --checkpoint；续跑请指定已有的 --portfolio-id。")
    enable_db = (config.get("backtest") or {}).get("enable_database", False)
    if enable_db:
        store = SQLiteStore(db_path)
    else:
        from src.platform_core.storage import InMemoryStore
        store = InMemoryStore()
    try:
        if resume:
            portfolio = SimPortfolio.load(args.portfolio_id, config, store, output_root=output_dir)
        else:
            checkpoint_path = (ROOT / args.checkpoint).resolve() if not Path(args.checkpoint).is_absolute() else Path(args.checkpoint)
            portfolio = SimPortfolio.create_from_checkpoint(
                checkpoint_path=checkpoint_path, config=config, store=store,
                portfolio_id=args.portfolio_id, output_root=output_dir,
            )
        result = portfolio.advance(args.asof_date)
    finally:
        store.close()

    print(f"Sim portfolio advanced: {result.output_dir}")
    print(f"Portfolio id: {result.portfolio_id}")
    print(f"Processed days: {result.metrics.get('processed_days', 0)}")
    print(f"Trade count: {result.metrics.get('trade_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
