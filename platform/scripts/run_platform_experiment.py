import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.experiment import run_platform_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a standardized platform experiment with optional baseline comparison.")
    parser.add_argument("--config", default="configs/baseline_r1_domestic_rolling.yaml", help="Candidate platform config path.")
    parser.add_argument("--baseline-config", help="Baseline platform config path. Defaults to --config.")
    parser.add_argument("--experiment-name", help="Report grouping name. Defaults to the first strategy name.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--raw-root", default="results/backtests", help="Root for raw platform backtest artifacts.")
    parser.add_argument("--report-root", default="reports/experiments", help="Root for standardized experiment reports.")
    parser.add_argument("--skip-baseline", action="store_true", help="Run candidate only.")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart rendering.")
    parser.add_argument("--start-date", help="Runtime backtest start date for candidate and baseline, YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Runtime backtest end date for candidate and baseline, YYYY-MM-DD.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    baseline_config_path = None
    if args.baseline_config:
        baseline_config_path = (ROOT / args.baseline_config).resolve() if not Path(args.baseline_config).is_absolute() else Path(args.baseline_config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    raw_root = (ROOT / args.raw_root).resolve() if not Path(args.raw_root).is_absolute() else Path(args.raw_root)
    report_root = (ROOT / args.report_root).resolve() if not Path(args.report_root).is_absolute() else Path(args.report_root)

    result = run_platform_experiment(
        candidate_config_path=config_path,
        baseline_config_path=baseline_config_path,
        experiment_name=args.experiment_name,
        db_path=db_path,
        raw_root=raw_root,
        report_root=report_root,
        skip_baseline=args.skip_baseline,
        render_charts=not args.no_charts,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"Standardized platform report written to: {result.report_dir}")
    print(f"Candidate raw artifacts: {result.candidate.output_dir}")
    if result.baseline:
        print(f"Baseline raw artifacts: {result.baseline.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
