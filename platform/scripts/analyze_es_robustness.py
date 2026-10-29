from __future__ import annotations

"""Analyze Expected Shortfall risk-budget robustness for ETF/index proxies.

The tool compares raw historical simulation with EWMA-filtered historical
simulation, rolling-window choices, moving-block bootstrap weight intervals,
single-worst-scenario deletion sensitivity, and ES risk-contribution budget
errors. It can also generate reusable matrix configs under configs/generated.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))
os.chdir(PLATFORM_ROOT)

from src.platform_core.data import LocalCsvBarData  # noqa: E402
from src.platform_core.data_store import assets_from_config, validate_market_dates  # noqa: E402
from src.platform_core.engine import load_strategy_config  # noqa: E402
from src.platform_core.strategy import RiskParityStrategy  # noqa: E402
from src.platform_core.strategies.expected_shortfall import (  # noqa: E402
    RiskParityExpectedShortfallFixedBudgetStrategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--etf-config",
        default="configs/capital_100k/es_120d_hist_100k.yaml",
    )
    parser.add_argument(
        "--index-config",
        default="configs/index_benchmark/index_es_120d_hist_100k.yaml",
    )
    parser.add_argument("--windows", default="120,252,500")
    parser.add_argument("--methods", default="historical,filtered")
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--fhs-decay", type=float, default=0.94)
    parser.add_argument("--bootstrap-reps", type=int, default=200)
    parser.add_argument("--bootstrap-block-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Defaults to results/temporary_backtests/es_robustness/<timestamp>.",
    )
    parser.add_argument(
        "--generated-config-dir",
        default="configs/generated/es_robustness",
    )
    return parser.parse_args()


def load_yaml(path_value: str) -> tuple[Path, dict]:
    path = Path(path_value)
    if not path.is_absolute():
        path = PLATFORM_ROOT / path
    with path.open("r", encoding="utf-8") as handle:
        return path, yaml.safe_load(handle)


def config_prices(config: dict) -> tuple[pd.DataFrame, list[str], np.ndarray]:
    params = load_strategy_config(config["strategy"])["params"]
    assets = assets_from_config(config["assets"])
    universe = params.get("universe") or [asset.asset_id for asset in assets]
    budgets = params.get("risk_budgets")
    if not isinstance(budgets, dict) or set(budgets) != set(universe):
        raise ValueError("risk_budgets must match the complete universe.")
    budgets = RiskParityStrategy._normalize_risk_budgets(budgets, universe)
    data = LocalCsvBarData(PLATFORM_ROOT / config.get("data", {}).get("data_dir", "data"), assets)
    prices = data.get_price_frame(universe, max(data.calendar))
    if prices is None or prices.empty:
        raise ValueError("No aligned price history for the configured universe.")
    prices.index = pd.to_datetime(prices.index)
    return prices, universe, budgets


def es_risk_contributions(
    scenarios: np.ndarray,
    weights: np.ndarray,
    confidence_level: float,
) -> np.ndarray:
    _, marginal = RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(
        scenarios,
        weights,
        confidence_level,
    )
    contributions = weights * marginal
    total = float(contributions.sum())
    if not np.isfinite(total) or abs(total) <= 1e-14:
        raise ValueError("ES risk-contribution shares are undefined for zero or nonfinite total risk.")
    return contributions / total


def moving_block_sample(values: np.ndarray, block_size: int, rng: np.random.Generator) -> np.ndarray:
    observations = len(values)
    if observations < 2 or block_size < 1:
        raise ValueError("Block sampling requires at least two observations and a positive block size.")
    size = min(block_size, observations)
    blocks = int(np.ceil(observations / size))
    starts = rng.integers(0, observations - size + 1, size=blocks)
    sampled = np.concatenate([values[start : start + size] for start in starts], axis=0)
    return sampled[:observations]


def solve_weights(
    raw_returns: np.ndarray,
    budgets: np.ndarray,
    method: str,
    confidence_level: float,
    fhs_decay: float,
) -> tuple[np.ndarray, np.ndarray]:
    scenarios = RiskParityExpectedShortfallFixedBudgetStrategy._expected_shortfall_scenarios(
        raw_returns,
        method=method,
        fhs_decay=fhs_decay,
    )
    weights = RiskParityExpectedShortfallFixedBudgetStrategy._solve_expected_shortfall_risk_budget(
        scenarios,
        budgets,
        confidence_level,
    )
    return weights, scenarios


def monthly_dates(returns: pd.DataFrame, window: int) -> list[pd.Timestamp]:
    eligible = returns.index[window - 1 :]
    if len(eligible) == 0:
        return []
    marker = pd.Series(eligible, index=eligible)
    return list(marker.groupby(eligible.to_period("M")).last())


def diagnostic_rows(
    proxy: str,
    prices: pd.DataFrame,
    universe: list[str],
    budgets: np.ndarray,
    windows: list[int],
    methods: list[str],
    confidence_level: float,
    fhs_decay: float,
) -> list[dict[str, object]]:
    returns = prices.pct_change().dropna()
    rows: list[dict[str, object]] = []
    for window in windows:
        for method in methods:
            for current_date in monthly_dates(returns, window):
                sample = returns.loc[:current_date].tail(window).to_numpy(dtype=float)
                weights, scenarios = solve_weights(
                    sample, budgets, method, confidence_level, fhs_decay
                )
                contributions = es_risk_contributions(scenarios, weights, confidence_level)
                worst_index = int(np.argmax(-(scenarios @ weights)))
                reduced_sample = np.delete(sample, worst_index, axis=0)
                deleted_weights, _ = solve_weights(
                    reduced_sample, budgets, method, confidence_level, fhs_decay
                )
                row: dict[str, object] = {
                    "proxy": proxy,
                    "window": window,
                    "method": method,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "tail_observations": int(
                        np.ceil((1 - confidence_level) * window - 1e-12)
                    ),
                    "risk_budget_l1_error": float(np.abs(contributions - budgets).sum()),
                    "risk_budget_max_abs_error": float(np.abs(contributions - budgets).max()),
                    "delete_worst_weight_l1_change": float(np.abs(deleted_weights - weights).sum()),
                    "delete_worst_weight_max_change": float(np.abs(deleted_weights - weights).max()),
                }
                for index, asset_id in enumerate(universe):
                    row[f"weight::{asset_id}"] = float(weights[index])
                    row[f"risk_contribution::{asset_id}"] = float(contributions[index])
                    row[f"budget::{asset_id}"] = float(budgets[index])
                    row[f"delete_worst_weight::{asset_id}"] = float(deleted_weights[index])
                rows.append(row)
    return rows


def bootstrap_rows(
    proxy: str,
    prices: pd.DataFrame,
    universe: list[str],
    budgets: np.ndarray,
    windows: list[int],
    methods: list[str],
    confidence_level: float,
    fhs_decay: float,
    repetitions: int,
    block_size: int,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    if repetitions < 2 or block_size < 1:
        raise ValueError("Bootstrap requires at least two repetitions and a positive block size.")
    returns = prices.pct_change().dropna()
    rows: list[dict[str, object]] = []
    for window in windows:
        if len(returns) < window:
            continue
        raw_sample = returns.tail(window).to_numpy(dtype=float)
        for method in methods:
            point, _ = solve_weights(raw_sample, budgets, method, confidence_level, fhs_decay)
            samples: list[np.ndarray] = []
            failures = 0
            for _ in range(repetitions):
                sampled = moving_block_sample(raw_sample, block_size, rng)
                try:
                    weight, _ = solve_weights(
                        sampled, budgets, method, confidence_level, fhs_decay
                    )
                    samples.append(weight)
                except (RuntimeError, ValueError):
                    failures += 1
            if len(samples) < 2:
                raise RuntimeError(f"Bootstrap has fewer than two successful repetitions: {proxy}/{window}/{method}; failed={failures}")
            matrix = np.asarray(samples)
            for index, asset_id in enumerate(universe):
                rows.append(
                    {
                        "proxy": proxy,
                        "window": window,
                        "method": method,
                        "date": returns.index[-1].strftime("%Y-%m-%d"),
                        "asset_id": asset_id,
                        "point_weight": float(point[index]),
                        "bootstrap_p05": float(np.quantile(matrix[:, index], 0.05)),
                        "bootstrap_p50": float(np.quantile(matrix[:, index], 0.50)),
                        "bootstrap_p95": float(np.quantile(matrix[:, index], 0.95)),
                        "bootstrap_std": float(np.std(matrix[:, index], ddof=1)),
                        "successful_reps": len(samples),
                        "failed_reps": failures,
                    }
                )
    return rows


def generate_configs(
    config: dict,
    proxy: str,
    windows: list[int],
    methods: list[str],
    confidence_level: float,
    fhs_decay: float,
    output_dir: Path,
) -> list[Path]:
    import copy

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for window in windows:
        for method in methods:
            generated = copy.deepcopy(config)
            run_name = f"es_robustness_{proxy}_w{window}_{method}"
            generated.setdefault("platform", {})["run_name"] = run_name
            generated.setdefault("output", {})["results_dir"] = "results/temporary_backtests/direct"
            params = generated["strategy"]["params"]
            params["rolling_window"] = window
            params["min_periods"] = window
            params["confidence_level"] = confidence_level
            params["es_method"] = method
            if method == "filtered":
                params["fhs_decay"] = fhs_decay
            else:
                params.pop("fhs_decay", None)
            path = output_dir / f"{run_name}.yaml"
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                yaml.safe_dump(generated, handle, allow_unicode=True, sort_keys=False)
            paths.append(path)
    return paths


def tracking_summary(etf_prices: pd.DataFrame, index_prices: pd.DataFrame) -> dict[str, float | str | int | None]:
    etf_asset = next(column for column in etf_prices if "511090" in column)
    index_asset = next(column for column in index_prices if "CBA21801" in column)
    pair = pd.concat(
        [etf_prices[etf_asset].rename("etf"), index_prices[index_asset].rename("index")],
        axis=1,
    ).dropna()
    returns = pair.pct_change().dropna()
    if len(returns) < 2 or (returns.std(ddof=1) <= 0).any():
        raise ValueError("Tracking statistics require at least two common returns and nonzero volatility.")
    difference = returns["etf"] - returns["index"]
    downside = returns.loc[returns["index"] < 0]
    return {
        "start_date": returns.index.min().strftime("%Y-%m-%d"),
        "end_date": returns.index.max().strftime("%Y-%m-%d"),
        "observations": int(len(returns)),
        "daily_return_correlation": float(returns.corr().iloc[0, 1]),
        "annualized_tracking_error": float(difference.std(ddof=1) * np.sqrt(252)),
        "annualized_mean_return_difference": float(difference.mean() * 252),
        "etf_to_index_beta": float(returns.cov().iloc[0, 1] / returns["index"].var(ddof=1)),
        "downside_correlation": (float(downside.corr().iloc[0, 1])
                                 if len(downside) >= 2 and (downside.std(ddof=1) > 0).all() else None),
        "etf_annualized_volatility": float(returns["etf"].std(ddof=1) * np.sqrt(252)),
        "index_annualized_volatility": float(returns["index"].std(ddof=1) * np.sqrt(252)),
    }


def main() -> int:
    args = parse_args()
    windows = [int(item) for item in args.windows.split(",")]
    methods = [item.strip().lower() for item in args.methods.split(",")]
    if (not windows or any(window < 3 for window in windows) or len(set(windows)) != len(windows)
            or not methods or set(methods) - {"historical", "filtered"} or len(set(methods)) != len(methods)
            or args.bootstrap_reps < 2 or args.bootstrap_block_size < 1
            or not 0 < args.confidence_level < 1 or not 0 < args.fhs_decay < 1):
        raise ValueError("Invalid windows, methods, confidence level, decay or bootstrap parameters.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = Path(args.output_dir) if args.output_dir else Path(
        f"results/temporary_backtests/es_robustness/{timestamp}"
    )
    if not output_dir.is_absolute():
        output_dir = PLATFORM_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=False)

    etf_path, etf_config = load_yaml(args.etf_config)
    index_path, index_config = load_yaml(args.index_config)
    etf_prices, etf_universe, etf_budgets = config_prices(etf_config)
    index_prices, index_universe, index_budgets = config_prices(index_config)
    validate_market_dates({"etf": etf_prices.index[-1].date(), "index": index_prices.index[-1].date()}, date.today())

    all_diagnostics: list[dict[str, object]] = []
    all_bootstrap: list[dict[str, object]] = []
    rng = np.random.default_rng(args.seed)
    for proxy, prices, universe, budgets in [
        ("etf_511090", etf_prices, etf_universe, etf_budgets),
        ("index_cba21801", index_prices, index_universe, index_budgets),
    ]:
        all_diagnostics.extend(
            diagnostic_rows(
                proxy,
                prices,
                universe,
                budgets,
                windows,
                methods,
                args.confidence_level,
                args.fhs_decay,
            )
        )
        all_bootstrap.extend(
            bootstrap_rows(
                proxy,
                prices,
                universe,
                budgets,
                windows,
                methods,
                args.confidence_level,
                args.fhs_decay,
                args.bootstrap_reps,
                args.bootstrap_block_size,
                rng,
            )
        )

    diagnostics = pd.DataFrame(all_diagnostics)
    bootstrap = pd.DataFrame(all_bootstrap)
    diagnostics.to_csv(output_dir / "rebalance_diagnostics.csv", index=False)
    bootstrap.to_csv(output_dir / "bootstrap_weight_intervals.csv", index=False)

    tracking = tracking_summary(etf_prices, index_prices)
    with (output_dir / "tracking_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(tracking, handle, ensure_ascii=False, indent=2, allow_nan=False)

    config_dir = Path(args.generated_config_dir)
    if not config_dir.is_absolute():
        config_dir = PLATFORM_ROOT / config_dir
    config_dir = config_dir / timestamp
    config_dir.mkdir(parents=True, exist_ok=False)
    generated = []
    generated.extend(
        generate_configs(etf_config, "etf_511090", windows, methods, args.confidence_level, args.fhs_decay, config_dir)
    )
    generated.extend(
        generate_configs(index_config, "index_cba21801", windows, methods, args.confidence_level, args.fhs_decay, config_dir)
    )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "etf_config": str(etf_path),
        "index_config": str(index_path),
        "windows": windows,
        "methods": methods,
        "confidence_level": args.confidence_level,
        "fhs_decay": args.fhs_decay,
        "bootstrap_reps": args.bootstrap_reps,
        "bootstrap_block_size": args.bootstrap_block_size,
        "seed": args.seed,
        "etf_common_range": [str(etf_prices.index.min().date()), str(etf_prices.index.max().date())],
        "index_common_range": [str(index_prices.index.min().date()), str(index_prices.index.max().date())],
        "generated_configs": [str(path) for path in generated],
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
