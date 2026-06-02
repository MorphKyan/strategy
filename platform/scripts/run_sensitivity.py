import argparse
import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import assets_from_config
from src.platform_core.experiment import run_backtest, strategy_name
from src.platform_core.storage import SQLiteStore
from src.platform_core.visualization import render_sensitivity_charts


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def set_start_date(config: dict, start_date: str) -> dict:
    runtime = copy.deepcopy(config)
    runtime.setdefault("backtest", {})["start_date"] = start_date
    segments = runtime.setdefault("strategies", {}).setdefault("segments", [])
    if segments:
        segments[0]["start_date"] = start_date
    runtime.setdefault("platform", {})["run_name"] = f"{runtime.get('platform', {}).get('run_name', strategy_name(runtime))}_start_{start_date.replace('-', '')}"
    return runtime


def calendar_for_config(config: dict) -> list[str]:
    data_config = config.get("data", {})
    backtest = config.get("backtest", {})
    market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")
    data = LocalCsvBarData(
        data_dir=market_dir,
        assets=assets_from_config(config.get("assets", [])),
        start_date=backtest.get("start_date"),
        end_date=backtest.get("end_date"),
    )
    return [item.isoformat() for item in data.calendar]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run platform start-date sensitivity analysis.")
    parser.add_argument("--config", default="configs/platform_risk_parity.yaml", help="Platform config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--step", type=int, default=3, help="Trading-day step between start dates. Default: 3.")
    parser.add_argument("--raw-root", default="results/sensitivity_raw", help="Root for raw sensitivity run artifacts.")
    parser.add_argument("--report-root", default="reports/sensitivity", help="Root for sensitivity summary reports.")
    parser.add_argument("--charts", action="store_true", help="Render per-run charts. Off by default because sensitivity can produce many runs.")
    args = parser.parse_args()

    if args.step <= 0:
        raise ValueError("--step must be positive.")

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    raw_root = (ROOT / args.raw_root).resolve() if not Path(args.raw_root).is_absolute() else Path(args.raw_root)
    report_root = (ROOT / args.report_root).resolve() if not Path(args.report_root).is_absolute() else Path(args.report_root)

    base_config = load_config(config_path)
    name = strategy_name(base_config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = report_root / name / timestamp
    raw_dir = raw_root / name / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    dates = calendar_for_config(base_config)[:: args.step]
    rows = []
    store = SQLiteStore(db_path)
    try:
        for start_date in dates:
            runtime_config = set_start_date(base_config, start_date)
            run = run_backtest(runtime_config, "sensitivity", store, raw_dir / start_date, render_charts=args.charts)
            row = {"start_date": start_date, "run_id": run.run_id, "raw_path": str(run.output_dir)}
            for key in [
                "total_return",
                "annualized_return",
                "annualized_volatility",
                "max_drawdown",
                "sharpe_ratio",
                "annualized_turnover",
                "trade_count",
                "rejected_order_count",
                "max_pending_intent_count",
                "average_cash_weight",
            ]:
                row[key] = run.metrics.get(key)
            rows.append(row)
    finally:
        store.close()

    frame = pd.DataFrame(rows)
    frame.to_csv(report_dir / "sensitivity_summary.csv", index=False)
    payload = {
        "config": str(config_path),
        "step": args.step,
        "sample_count": len(rows),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary_csv": str(report_dir / "sensitivity_summary.csv"),
        "runs": rows,
    }
    (report_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "report.md").write_text(
        "\n".join(
            [
                f"# 平台起始日敏感度分析：{name}",
                "",
                f"- 配置：`{config_path}`",
                f"- 步长：`{args.step}` 个交易日",
                f"- 样本数量：`{len(rows)}`",
                f"- 汇总 CSV：`{report_dir / 'sensitivity_summary.csv'}`",
                f"- 原始结果根目录：`{raw_dir}`",
                "",
                "本分析不限制样本数，会对配置回测日历中每隔 `step` 个交易日的起始日期逐一评估。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        render_sensitivity_charts(report_dir / "sensitivity_summary.csv", report_dir)
        print("Generated sensitivity summary charts.")
    except Exception as e:
        print(f"Failed to generate sensitivity charts: {e}")
    print(f"Sensitivity report written to: {report_dir}")
    print(f"Sample count: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
