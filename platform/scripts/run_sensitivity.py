import argparse
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
from src.platform_core.runtime_config import apply_runtime_dates
from src.platform_core.slippage import REQUIRED_SLIPPAGE_SCENARIOS, apply_slippage_scenario
from src.platform_core.storage import SQLiteStore
from src.platform_core.visualization import render_sensitivity_charts


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def set_start_date(config: dict, start_date: str) -> dict:
    runtime = apply_runtime_dates(config, start_date=start_date)
    runtime.setdefault("platform", {})["run_name"] = f"{runtime.get('platform', {}).get('run_name', strategy_name(runtime))}_start_{start_date.replace('-', '')}"
    return runtime


def calendar_for_config(config: dict) -> list[str]:
    data_config = config.get("data", {})
    backtest = config.get("backtest") or {}
    market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")
    data = LocalCsvBarData(
        data_dir=market_dir,
        assets=assets_from_config(config.get("assets", [])),
        start_date=backtest.get("start_date"),
        end_date=backtest.get("end_date"),
    )
    if not data.calendar:
        return []
    universe = list(data.assets)
    aligned = data.get_price_frame(universe, data.calendar[-1])
    if aligned is None or aligned.empty:
        return []
    return [pd.Timestamp(item).date().isoformat() for item in aligned.index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run platform start-date sensitivity analysis.")
    parser.add_argument("--config", default="configs/baseline_r1_domestic_rolling.yaml", help="Platform config path.")
    parser.add_argument("--db", default="data/platform/platform.sqlite3", help="SQLite metadata database path.")
    parser.add_argument("--step", type=int, default=3, help="Trading-day step between start dates. Default: 3.")
    parser.add_argument(
        "--calendar-month-step",
        type=int,
        help="按自然月生成锚点，并取锚点当日或其后首个交易日；设置后优先于 --step。",
    )
    parser.add_argument(
        "--raw-root",
        default="results/sensitivity",
        help="Root for raw sensitivity run artifacts.",
    )
    parser.add_argument("--report-root", default="reports/sensitivity", help="Root for sensitivity summary reports.")
    parser.add_argument("--charts", action="store_true", help="Render per-run charts. Off by default because sensitivity can produce many runs.")
    parser.add_argument("--end-date", help="Runtime sensitivity end date, YYYY-MM-DD. Use 2025-06-30 for training-sample research.")
    parser.add_argument(
        "--slippage-scenario",
        choices=[*REQUIRED_SLIPPAGE_SCENARIOS, "all"],
        default="all",
        help="Slippage scenario to run. Default `all` runs default, stress, and dynamic_participation.",
    )
    args = parser.parse_args()

    if args.step <= 0:
        raise ValueError("--step must be positive.")
    if args.calendar_month_step is not None and args.calendar_month_step <= 0:
        raise ValueError("--calendar-month-step must be positive.")

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db)
    raw_root = (ROOT / args.raw_root).resolve() if not Path(args.raw_root).is_absolute() else Path(args.raw_root)
    report_root = (ROOT / args.report_root).resolve() if not Path(args.report_root).is_absolute() else Path(args.report_root)

    base_config = apply_runtime_dates(load_config(config_path), end_date=args.end_date)
    name = strategy_name(base_config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = report_root / name / timestamp
    raw_dir = raw_root / name / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    calendar = calendar_for_config(base_config)
    if args.calendar_month_step is None:
        dates = calendar[:: args.step]
    elif calendar:
        trading_dates = pd.DatetimeIndex(pd.to_datetime(calendar))
        anchors = pd.date_range(
            trading_dates[0], trading_dates[-1], freq=pd.DateOffset(months=args.calendar_month_step)
        )
        positions = trading_dates.searchsorted(anchors, side="left")
        dates = []
        for position in positions:
            if position < len(trading_dates):
                value = trading_dates[position].date().isoformat()
                if not dates or dates[-1] != value:
                    dates.append(value)
    else:
        dates = []
    rows = []
    enable_db = (base_config.get("backtest") or {}).get("enable_database", False)
    if enable_db:
        store = SQLiteStore(db_path)
    else:
        from src.platform_core.storage import InMemoryStore
        store = InMemoryStore()
    try:
        scenario_names = REQUIRED_SLIPPAGE_SCENARIOS if args.slippage_scenario == "all" else (args.slippage_scenario,)
        for scenario in scenario_names:
            scenario_config = apply_slippage_scenario(base_config, scenario)
            for start_date in dates:
                runtime_config = set_start_date(scenario_config, start_date)
                run = run_backtest(runtime_config, "sensitivity", store, raw_dir / scenario / start_date, render_charts=args.charts)
                row = {"slippage_scenario": scenario, "start_date": start_date, "run_id": run.run_id, "raw_path": str(run.output_dir)}
                for key in [
                    "total_return",
                    "annualized_return",
                    "annualized_volatility",
                    "max_drawdown",
                    "sharpe_ratio",
                    "annualized_turnover",
                    "trade_count",
                    "order_count",
                    "rejected_order_count",
                    "max_pending_intent_count",
                    "average_cash_weight",
                    "execution_slippage",
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
        "calendar_month_step": args.calendar_month_step,
        "slippage_scenario": args.slippage_scenario,
        "required_slippage_scenarios": list(REQUIRED_SLIPPAGE_SCENARIOS),
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
