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


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or advance a simulated portfolio from a platform checkpoint.")
    parser.add_argument("--config", default="configs/baseline_r1_domestic_rolling.yaml", help="Platform YAML config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--checkpoint", required=True, help="Checkpoint JSON to derive the simulated portfolio from.")
    parser.add_argument("--asof-date", required=True, help="Advance through this date, YYYY-MM-DD.")
    parser.add_argument("--portfolio-id", help="Stable simulated portfolio id.")
    parser.add_argument("--output-dir", help="Override simulated portfolio output root.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    checkpoint_path = (ROOT / args.checkpoint).resolve() if not Path(args.checkpoint).is_absolute() else Path(args.checkpoint)
    output_dir = None
    if args.output_dir:
        output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    config = load_config(config_path)
    store = SQLiteStore(db_path)
    try:
        portfolio = SimPortfolio.create_from_checkpoint(
            checkpoint_path=checkpoint_path,
            config=config,
            store=store,
            portfolio_id=args.portfolio_id,
            output_root=output_dir,
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
