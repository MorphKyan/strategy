from __future__ import annotations

"""Summarize ES robustness backtests, execution risk budgets, and sensitivities."""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))
os.chdir(PLATFORM_ROOT)

from scripts.analyze_es_robustness import (  # noqa: E402
    config_prices,
    es_risk_contributions,
    solve_weights,
)
from src.platform_core.metrics import build_platform_metrics  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtest-root", required=True)
    parser.add_argument("--sensitivity-report-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--minimum-active-observations", type=int, default=126)
    return parser.parse_args()


def run_identity(path: Path) -> tuple[str, int, str, str]:
    config = yaml.safe_load((path / "config_snapshot.yaml").read_text(encoding="utf-8"))
    params = config["strategy"]["params"]
    proxy = "index_cba21801" if any("CBA21801" in item for item in params["universe"]) else "etf_511090"
    return proxy, int(params["rolling_window"]), str(params.get("es_method", "historical")), str(
        json.loads((path / "manifest.json").read_text(encoding="utf-8"))["execution_model"]["slippage_scenario"]
    )


def execution_risk_rows(path: Path, data_dir: Path) -> list[dict[str, object]]:
    config = yaml.safe_load((path / "config_snapshot.yaml").read_text(encoding="utf-8"))
    prices, universe, budgets = config_prices(config, data_dir)
    params = config["strategy"]["params"]
    window = int(params["rolling_window"])
    method = str(params.get("es_method", "historical"))
    confidence = float(params.get("confidence_level", 0.95))
    decay = float(params.get("fhs_decay", 0.94))
    proxy, _, _, scenario = run_identity(path)
    returns = prices.pct_change().dropna()
    trades = pd.read_csv(path / "trades.csv")
    positions = pd.read_csv(path / "positions.csv")
    nav = pd.read_csv(path / "nav.csv").set_index("date")
    if trades.empty or positions.empty:
        return []
    trades["date"] = pd.to_datetime(trades["date"])
    trades["signal_date"] = pd.to_datetime(trades["signal_date"])
    positions["date"] = pd.to_datetime(positions["date"])
    rows: list[dict[str, object]] = []
    for trade_date in sorted(trades["date"].unique()):
        day_trades = trades.loc[trades["date"] == trade_date]
        signal_date = day_trades["signal_date"].max()
        sample_frame = returns.loc[:signal_date].tail(window)
        if len(sample_frame) < window:
            continue
        sample = sample_frame.to_numpy(dtype=float)
        theoretical, scenarios = solve_weights(sample, budgets, method, confidence, decay)
        day_positions = positions.loc[positions["date"] == trade_date].set_index("asset_id")
        actual = np.asarray(
            [float(day_positions.at[item, "weight"]) if item in day_positions.index else 0.0 for item in universe]
        )
        risky_sum = float(actual.sum())
        if risky_sum <= 0.0:
            continue
        actual_relative = actual / risky_sum
        contributions = es_risk_contributions(scenarios, actual_relative, confidence)
        theoretical_contributions = es_risk_contributions(scenarios, theoretical, confidence)
        date_key = pd.Timestamp(trade_date).strftime("%Y-%m-%d")
        nav_row = nav.loc[date_key]
        row: dict[str, object] = {
            "run_id": path.name,
            "proxy": proxy,
            "window": window,
            "method": method,
            "scenario": scenario,
            "trade_date": date_key,
            "signal_date": signal_date.strftime("%Y-%m-%d"),
            "cash_weight": float(nav_row["cash"] / nav_row["total_value"]),
            "actual_to_theoretical_weight_l1": float(np.abs(actual_relative - theoretical).sum()),
            "actual_budget_l1_error": float(np.nansum(np.abs(contributions - budgets))),
            "actual_budget_max_abs_error": float(np.nanmax(np.abs(contributions - budgets))),
            "theoretical_budget_l1_error": float(np.nansum(np.abs(theoretical_contributions - budgets))),
        }
        for index, asset_id in enumerate(universe):
            row[f"actual_weight::{asset_id}"] = float(actual_relative[index])
            row[f"theoretical_weight::{asset_id}"] = float(theoretical[index])
            row[f"actual_risk_contribution::{asset_id}"] = float(contributions[index])
        rows.append(row)
    return rows


def summarize_sensitivities(report_root: Path, minimum_active: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows: list[pd.DataFrame] = []
    for manifest_path in sorted(report_root.rglob("manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary_path = Path(manifest["summary_csv"])
        if not summary_path.exists():
            continue
        frame = pd.read_csv(summary_path)
        config_name = Path(manifest["config"]).stem
        frame["config_name"] = config_name
        frame["proxy"] = "index_cba21801" if "index_cba21801" in config_name else "etf_511090"
        frame["window"] = pd.to_numeric(config_name.split("_w", 1)[1].split("_", 1)[0])
        frame["method"] = "filtered" if config_name.endswith("filtered") else "historical"
        all_rows.append(frame)
    raw = pd.concat(all_rows, ignore_index=True)
    raw["start_date"] = pd.to_datetime(raw["start_date"])
    matched = raw.loc[
        (raw["start_date"] >= pd.Timestamp("2023-06-13"))
        & (pd.to_numeric(raw["active_observations"], errors="coerce") >= minimum_active)
    ].copy()
    groups = ["proxy", "window", "method", "slippage_scenario"]
    summary = matched.groupby(groups).agg(
        valid_start_count=("start_date", "count"),
        annualized_return_median=("annualized_return_active", "median"),
        annualized_return_min=("annualized_return_active", "min"),
        sharpe_median=("active_sharpe_ratio", "median"),
        sharpe_min=("active_sharpe_ratio", "min"),
        sharpe_std=("active_sharpe_ratio", "std"),
        max_drawdown_median=("max_drawdown", "median"),
        worst_max_drawdown=("max_drawdown", "min"),
        turnover_median=("annualized_turnover", "median"),
        trade_count_median=("trade_count", "median"),
        order_count_median=("order_count", "median"),
        rejected_order_count_max=("rejected_order_count", "max"),
        average_cash_weight_median=("average_cash_weight", "median"),
    ).reset_index()
    return raw, summary


def summarize_weight_comparisons(diagnostics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    weight_columns = [column for column in diagnostics.columns if column.startswith("weight::")]
    long = diagnostics.melt(
        id_vars=["proxy", "window", "method", "date"],
        value_vars=weight_columns,
        var_name="asset_id",
        value_name="weight",
    ).dropna(subset=["weight"])
    long["asset_id"] = long["asset_id"].str.removeprefix("weight::")
    long["canonical_asset"] = long["asset_id"].replace(
        {
            "CN_ETF:511090.SH": "BOND_30Y",
            "CN_INDEX:CBA21801.CS": "BOND_30Y",
        }
    )

    proxy_pivot = long.pivot_table(
        index=["window", "method", "date", "canonical_asset"],
        columns="proxy",
        values="weight",
    ).dropna()
    proxy_pivot["absolute_difference"] = (
        proxy_pivot["etf_511090"] - proxy_pivot["index_cba21801"]
    ).abs()
    proxy_by_date = proxy_pivot.groupby(["window", "method", "date"])[
        "absolute_difference"
    ].sum().rename("index_vs_etf_weight_l1").reset_index()

    method_pivot = long.pivot_table(
        index=["proxy", "window", "date", "canonical_asset"],
        columns="method",
        values="weight",
    ).dropna()
    method_pivot["absolute_difference"] = (
        method_pivot["filtered"] - method_pivot["historical"]
    ).abs()
    method_by_date = method_pivot.groupby(["proxy", "window", "date"])[
        "absolute_difference"
    ].sum().rename("filtered_vs_historical_weight_l1").reset_index()
    return proxy_by_date, method_by_date


def main() -> int:
    args = parse_args()
    backtest_root = Path(args.backtest_root)
    report_root = Path(args.sensitivity_report_root)
    output_dir = Path(args.output_dir)
    if not backtest_root.is_absolute():
        backtest_root = PLATFORM_ROOT / backtest_root
    if not report_root.is_absolute():
        report_root = PLATFORM_ROOT / report_root
    if not output_dir.is_absolute():
        output_dir = PLATFORM_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = PLATFORM_ROOT / "data"

    performance_rows: list[dict[str, object]] = []
    risk_rows: list[dict[str, object]] = []
    for path in sorted(backtest_root.iterdir()):
        if not path.is_dir() or not (path / "manifest.json").exists():
            continue
        proxy, window, method, scenario = run_identity(path)
        metrics = build_platform_metrics(path)
        performance_rows.append(
            {"run_id": path.name, "proxy": proxy, "window": window, "method": method, "scenario": scenario, **metrics}
        )
        risk_rows.extend(execution_risk_rows(path, data_dir))

    performance = pd.DataFrame(performance_rows)
    execution_risk = pd.DataFrame(risk_rows)
    performance.to_csv(output_dir / "backtest_performance.csv", index=False)
    execution_risk.to_csv(output_dir / "execution_risk_budget_diagnostics.csv", index=False)
    execution_summary = execution_risk.groupby(["proxy", "window", "method", "scenario"]).agg(
        rebalance_trade_dates=("trade_date", "count"),
        actual_budget_l1_error_median=("actual_budget_l1_error", "median"),
        actual_budget_l1_error_p95=("actual_budget_l1_error", lambda value: value.quantile(0.95)),
        actual_budget_max_abs_error_median=("actual_budget_max_abs_error", "median"),
        actual_to_theoretical_weight_l1_median=("actual_to_theoretical_weight_l1", "median"),
        cash_weight_median=("cash_weight", "median"),
        theoretical_budget_l1_error_max=("theoretical_budget_l1_error", "max"),
    ).reset_index()
    execution_summary.to_csv(output_dir / "execution_risk_budget_summary.csv", index=False)

    sensitivity_raw, sensitivity_summary = summarize_sensitivities(
        report_root, args.minimum_active_observations
    )
    sensitivity_raw.to_csv(output_dir / "sensitivity_all_starts.csv", index=False)
    sensitivity_summary.to_csv(output_dir / "sensitivity_matched_summary.csv", index=False)

    diagnostics_path = output_dir.parent / "rebalance_diagnostics.csv"
    if diagnostics_path.exists():
        diagnostics = pd.read_csv(diagnostics_path)
        proxy_weights, method_weights = summarize_weight_comparisons(diagnostics)
        proxy_weights.to_csv(output_dir / "index_vs_etf_weight_difference.csv", index=False)
        method_weights.to_csv(output_dir / "filtered_vs_historical_weight_difference.csv", index=False)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
