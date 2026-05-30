import argparse
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT / "results"
REPORTS_ROOT = ROOT / "reports" / "experiments"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def choose_python() -> str:
    env_python = ROOT / "env" / "python.exe"
    if env_python.exists():
        return str(env_python)
    repo_env_python = ROOT.parent / "env" / "python.exe"
    if repo_env_python.exists():
        return str(repo_env_python)
    return sys.executable


def run_backtest(config_path: Path, strategy: str) -> subprocess.CompletedProcess:
    command = [
        choose_python(),
        "main.py",
        "--config",
        str(config_path),
        "--strategy",
        strategy,
    ]
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def latest_result_dir(strategy: str) -> Path:
    strategy_root = RESULTS_ROOT / strategy
    if not strategy_root.exists():
        raise FileNotFoundError(f"No results directory exists for strategy '{strategy}'.")

    candidates = [path for path in strategy_root.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No timestamped result directories found for '{strategy}'.")

    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_net_value_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    if "net_value" not in frame.columns:
        raise ValueError(f"'net_value' column not found in {path}")
    return frame


def load_trade_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def safe_float(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(value)


def build_metrics(results_dir: Path) -> dict:
    backtest_csv = results_dir / "backtest_results.csv"
    trades_csv = results_dir / "trade_history.csv"

    frame = load_net_value_frame(backtest_csv)
    trades = load_trade_frame(trades_csv)
    net_value = frame["net_value"].dropna()
    daily_returns = net_value.pct_change().dropna()

    days = len(net_value)
    years = days / 252 if days else 0
    total_return = net_value.iloc[-1] / net_value.iloc[0] - 1 if days else None
    annualized_return = (
        (net_value.iloc[-1] / net_value.iloc[0]) ** (252 / max(len(daily_returns), 1)) - 1
        if len(daily_returns) > 0
        else 0.0
    )
    annualized_volatility = daily_returns.std() * math.sqrt(252) if len(daily_returns) > 1 else 0.0
    rolling_peak = net_value.cummax()
    drawdown = (net_value / rolling_peak) - 1
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0
    sharpe_ratio = (
        annualized_return / annualized_volatility
        if annualized_volatility not in (0, None) and annualized_volatility != 0
        else 0.0
    )

    turnover_total = safe_float(trades["trade_value"].abs().sum()) if "trade_value" in trades.columns else 0.0
    annualized_turnover = turnover_total / years if years else turnover_total

    return {
        "results_dir": str(results_dir),
        "backtest_results_csv": str(backtest_csv),
        "trade_history_csv": str(trades_csv),
        "start_date": net_value.index.min().strftime("%Y-%m-%d") if days else None,
        "end_date": net_value.index.max().strftime("%Y-%m-%d") if days else None,
        "observations": int(days),
        "total_return": safe_float(total_return),
        "annualized_return": safe_float(annualized_return),
        "annualized_volatility": safe_float(annualized_volatility),
        "max_drawdown": safe_float(max_drawdown),
        "sharpe_ratio": safe_float(sharpe_ratio),
        "turnover_total": safe_float(turnover_total),
        "annualized_turnover": safe_float(annualized_turnover),
        "trade_count": int(len(trades)),
        "oos_metrics_available": False,
    }


def pct_or_na(value) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def num_or_na(value) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def delta(candidate, baseline) -> str:
    if candidate is None or baseline is None:
        return "N/A"
    return f"{candidate - baseline:+.4f}"


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def write_text(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copy2(src, dst)


def build_report(
    strategy: str,
    baseline_strategy: str,
    command: list[str],
    baseline_command: list[str] | None,
    candidate_assets: list[dict],
    baseline_assets: list[dict] | None,
    strategy_metrics: dict,
    baseline_metrics: dict | None,
) -> str:
    recommendation = "Refine"
    if baseline_metrics is None:
        recommendation = "Review"
    else:
        sharpe_up = (strategy_metrics["sharpe_ratio"] or 0) > (baseline_metrics["sharpe_ratio"] or 0)
        drawdown_ok = (strategy_metrics["max_drawdown"] or 0) >= (baseline_metrics["max_drawdown"] or 0)
        turnover_ok = (strategy_metrics["annualized_turnover"] or 0) <= (baseline_metrics["annualized_turnover"] or 0) * 1.2
        recommendation = "Accept" if sharpe_up and drawdown_ok and turnover_ok else "Refine"

    lines = [
        f"# Experiment Report: {strategy}",
        "",
        "## Goal",
        f"Run a standardized experiment for `{strategy}` and compare it against `{baseline_strategy}` when baseline metrics are available.",
        "",
        "## Hypothesis",
        "This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.",
        "",
        "## Commands",
        f"- Candidate: `{' '.join(command)}`",
    ]

    if baseline_command is not None:
        lines.append(f"- Baseline: `{' '.join(baseline_command)}`")

    lines.extend(["", "## Candidate Basket"])
    for asset in candidate_assets:
        lines.append(f"- `{asset['code']}` {asset.get('name', '')}".rstrip())

    if baseline_assets is not None:
        lines.extend(["", "## Baseline Basket"])
        for asset in baseline_assets:
            lines.append(f"- `{asset['code']}` {asset.get('name', '')}".rstrip())

    lines.extend(
        [
            "",
            "## Candidate Metrics",
            f"- Total return: {pct_or_na(strategy_metrics['total_return'])}",
            f"- Annualized return: {pct_or_na(strategy_metrics['annualized_return'])}",
            f"- Annualized volatility: {pct_or_na(strategy_metrics['annualized_volatility'])}",
            f"- Max drawdown: {pct_or_na(strategy_metrics['max_drawdown'])}",
            f"- Sharpe ratio: {num_or_na(strategy_metrics['sharpe_ratio'])}",
            f"- Annualized turnover: {num_or_na(strategy_metrics['annualized_turnover'])}",
            f"- Trade count: {strategy_metrics['trade_count']}",
            f"- Out-of-sample metrics available: {strategy_metrics['oos_metrics_available']}",
        ]
    )

    if baseline_metrics is not None:
        lines.extend(
            [
                "",
                "## Baseline Comparison",
                f"- Sharpe delta: {delta(strategy_metrics['sharpe_ratio'], baseline_metrics['sharpe_ratio'])}",
                f"- Annualized return delta: {delta(strategy_metrics['annualized_return'], baseline_metrics['annualized_return'])}",
                f"- Annualized volatility delta: {delta(strategy_metrics['annualized_volatility'], baseline_metrics['annualized_volatility'])}",
                f"- Max drawdown delta: {delta(strategy_metrics['max_drawdown'], baseline_metrics['max_drawdown'])}",
                f"- Annualized turnover delta: {delta(strategy_metrics['annualized_turnover'], baseline_metrics['annualized_turnover'])}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Baseline Comparison",
                "- No baseline comparison was written because baseline metrics were not available.",
            ]
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            f"- {recommendation}",
            "",
            "## Notes",
            "- Metrics are computed from generated CSV artifacts, not inferred from memory.",
            "- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.",
        ]
    )

    return "\n".join(lines) + "\n"


def create_report_dir(strategy: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = REPORTS_ROOT / strategy / timestamp
    target.mkdir(parents=True, exist_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a standardized backtest experiment and write stable report artifacts.")
    parser.add_argument("--strategy", required=True, help="Strategy module name under research/src/strategies.")
    parser.add_argument("--config", default="configs/risk_parity.yaml", help="Config file path.")
    parser.add_argument("--baseline-strategy", default="risk_parity", help="Baseline strategy name for comparison.")
    parser.add_argument("--baseline-config", help="Optional baseline config path. Defaults to --config.")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip running the baseline during this invocation.")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    runtime_config = load_config(config_path)
    candidate_assets = runtime_config.get("backtest", {}).get("assets", [])

    baseline_config_path = (ROOT / args.baseline_config).resolve() if args.baseline_config else config_path
    if not baseline_config_path.exists():
        raise FileNotFoundError(f"Baseline config file not found: {baseline_config_path}")
    baseline_config = load_config(baseline_config_path)
    baseline_assets = baseline_config.get("backtest", {}).get("assets", [])

    report_dir = create_report_dir(args.strategy)
    candidate_command = [choose_python(), "main.py", "--config", str(config_path), "--strategy", args.strategy]
    candidate_run = run_backtest(config_path, args.strategy)
    write_text(report_dir / "candidate_stdout.txt", candidate_run.stdout)
    write_text(report_dir / "candidate_stderr.txt", candidate_run.stderr)

    if candidate_run.returncode != 0:
        failure_payload = {
            "strategy": args.strategy,
            "command": candidate_command,
            "returncode": candidate_run.returncode,
            "report_dir": str(report_dir),
        }
        write_json(report_dir / "failure.json", failure_payload)
        raise RuntimeError(f"Candidate backtest failed for '{args.strategy}'. See {report_dir}.")

    candidate_results_dir = latest_result_dir(args.strategy)
    candidate_metrics = build_metrics(candidate_results_dir)

    baseline_metrics = None
    baseline_command = None
    if not args.skip_baseline:
        baseline_command = [choose_python(), "main.py", "--config", str(baseline_config_path), "--strategy", args.baseline_strategy]
        baseline_run = run_backtest(baseline_config_path, args.baseline_strategy)
        write_text(report_dir / "baseline_stdout.txt", baseline_run.stdout)
        write_text(report_dir / "baseline_stderr.txt", baseline_run.stderr)
        if baseline_run.returncode == 0:
            baseline_metrics = build_metrics(latest_result_dir(args.baseline_strategy))

    report = build_report(
        strategy=args.strategy,
        baseline_strategy=args.baseline_strategy,
        command=candidate_command,
        baseline_command=baseline_command,
        candidate_assets=candidate_assets,
        baseline_assets=baseline_assets if not args.skip_baseline else None,
        strategy_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )

    payload = {
        "strategy": args.strategy,
        "config": str(config_path),
        "assets": candidate_assets,
        "baseline_config": None if args.skip_baseline else str(baseline_config_path),
        "baseline_assets": None if args.skip_baseline else baseline_assets,
        "candidate": candidate_metrics,
        "baseline": baseline_metrics,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    write_json(report_dir / "metrics.json", payload)
    write_text(report_dir / "report.md", report)
    copy_if_exists(candidate_results_dir / "config_snapshot.yaml", report_dir / "candidate_config_snapshot.yaml")
    write_text(report_dir / "latest_raw_results_path.txt", str(candidate_results_dir))

    print(f"Standardized report written to: {report_dir}")
    print(f"Raw candidate artifacts: {candidate_results_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
