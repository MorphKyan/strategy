from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.metrics import build_platform_metrics, comparison_metrics
from src.platform_core.storage import SQLiteStore
from src.platform_core.visualization import render_platform_charts


@dataclass
class ExperimentRun:
    label: str
    run_id: str
    output_dir: Path
    metrics: dict[str, Any]


@dataclass
class ExperimentResult:
    report_dir: Path
    candidate: ExperimentRun
    baseline: ExperimentRun | None
    metrics_path: Path
    report_path: Path


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_text(path: str | Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def strategy_name(config: dict[str, Any]) -> str:
    segments = config.get("strategies", {}).get("segments", [])
    if segments:
        return str(segments[0].get("strategy_name", "platform_strategy"))
    return str(config.get("platform", {}).get("run_name", "platform_strategy"))


def run_name(config: dict[str, Any], label: str) -> str:
    base = config.get("platform", {}).get("run_name") or strategy_name(config)
    return f"{base}_{label}"


def run_backtest(
    config: dict[str, Any],
    label: str,
    store: SQLiteStore,
    raw_root: str | Path,
    render_charts: bool = True,
) -> ExperimentRun:
    runtime_config = copy.deepcopy(config)
    runtime_config.setdefault("platform", {})["run_name"] = run_name(runtime_config, label)
    output_root = Path(raw_root) / strategy_name(runtime_config)
    result = PlatformBacktestEngine(config=runtime_config, store=store, output_dir=output_root).run()
    metrics = build_platform_metrics(result.output_dir)
    if render_charts:
        chart_paths = render_platform_charts(result.output_dir)
        metrics["chart_paths"] = [str(path) for path in chart_paths]
    return ExperimentRun(label=label, run_id=result.run_id, output_dir=result.output_dir, metrics=metrics)


def pct_or_na(value: Any) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.2f}%"


def num_or_na(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.4f}"


def recommendation(candidate: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    if baseline is None:
        return "Review"
    sharpe_up = (candidate.get("sharpe_ratio") or 0) > (baseline.get("sharpe_ratio") or 0)
    drawdown_ok = (candidate.get("max_drawdown") or 0) >= (baseline.get("max_drawdown") or 0)
    turnover_ok = (candidate.get("annualized_turnover") or 0) <= (baseline.get("annualized_turnover") or 0) * 1.2
    execution_ok = (candidate.get("rejected_order_count") or 0) <= (baseline.get("rejected_order_count") or 0)
    return "Accept" if sharpe_up and drawdown_ok and turnover_ok and execution_ok else "Refine"


def build_report(
    experiment_name: str,
    candidate: ExperimentRun,
    baseline: ExperimentRun | None,
    candidate_config_path: Path,
    baseline_config_path: Path | None,
    comparison: dict[str, Any],
) -> str:
    lines = [
        f"# Platform Experiment Report: {experiment_name}",
        "",
        "## Goal",
        "Run a standardized platform experiment and compare it with a platform baseline when available.",
        "",
        "## Artifacts",
        f"- Candidate raw path: `{candidate.output_dir}`",
        f"- Candidate config: `{candidate_config_path}`",
    ]
    if baseline is not None:
        lines.extend([f"- Baseline raw path: `{baseline.output_dir}`", f"- Baseline config: `{baseline_config_path}`"])

    c = candidate.metrics
    lines.extend(
        [
            "",
            "## Candidate Metrics",
            f"- Total return: {pct_or_na(c.get('total_return'))}",
            f"- Annualized return: {pct_or_na(c.get('annualized_return'))}",
            f"- Annualized volatility: {pct_or_na(c.get('annualized_volatility'))}",
            f"- Max drawdown: {pct_or_na(c.get('max_drawdown'))}",
            f"- Sharpe ratio: {num_or_na(c.get('sharpe_ratio'))}",
            f"- Annualized turnover: {num_or_na(c.get('annualized_turnover'))}",
            f"- Trade count: {c.get('trade_count')}",
            f"- Order count: {c.get('order_count')}",
            f"- Rejected order count: {c.get('rejected_order_count')}",
            f"- Max pending intents: {c.get('max_pending_intent_count')}",
            f"- Average cash weight: {pct_or_na(c.get('average_cash_weight'))}",
            f"- Out-of-sample metrics available: {c.get('oos_metrics_available')}",
        ]
    )

    if c.get("rejection_reason_counts"):
        lines.extend(["", "## Candidate Execution Rejections"])
        for reason, count in c["rejection_reason_counts"].items():
            lines.append(f"- `{reason}`: {count}")

    if baseline is not None:
        lines.extend(["", "## Baseline Comparison"])
        for key, value in comparison.items():
            lines.append(f"- {key}: {num_or_na(value)}")
    else:
        lines.extend(["", "## Baseline Comparison", "- No baseline comparison was requested."])

    lines.extend(
        [
            "",
            "## Recommendation",
            f"- {recommendation(c, baseline.metrics if baseline else None)}",
            "",
            "## Notes",
            "- Metrics are computed from generated platform CSV artifacts.",
            "- Execution constraints are summarized from `orders.csv`, `trades.csv`, and pending-intent state in `nav.csv`.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_platform_experiment(
    candidate_config_path: str | Path,
    db_path: str | Path,
    baseline_config_path: str | Path | None = None,
    experiment_name: str | None = None,
    raw_root: str | Path = "results/backtests",
    report_root: str | Path = "reports/experiments",
    skip_baseline: bool = False,
    render_charts: bool = True,
) -> ExperimentResult:
    candidate_config_path = Path(candidate_config_path)
    baseline_config_path = Path(baseline_config_path) if baseline_config_path else candidate_config_path
    candidate_config = load_yaml(candidate_config_path)
    baseline_config = None if skip_baseline else load_yaml(baseline_config_path)

    resolved_name = experiment_name or strategy_name(candidate_config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(report_root) / resolved_name / timestamp
    raw_dir = Path(raw_root) / resolved_name / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore(db_path)
    try:
        candidate = run_backtest(candidate_config, "candidate", store, raw_dir, render_charts=render_charts)
        baseline = None
        if baseline_config is not None:
            baseline = run_backtest(baseline_config, "baseline", store, raw_dir, render_charts=render_charts)
    finally:
        store.close()

    comparison = comparison_metrics(candidate.metrics, baseline.metrics if baseline else None)
    payload = {
        "experiment_name": resolved_name,
        "candidate_config": str(candidate_config_path),
        "baseline_config": None if baseline is None else str(baseline_config_path),
        "candidate": candidate.metrics,
        "baseline": None if baseline is None else baseline.metrics,
        "comparison": comparison,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    metrics_path = report_dir / "metrics.json"
    report_path = report_dir / "report.md"
    write_json(metrics_path, payload)
    write_text(
        report_path,
        build_report(resolved_name, candidate, baseline, candidate_config_path, baseline_config_path if baseline else None, comparison),
    )
    shutil.copy2(candidate_config_path, report_dir / "candidate_config.yaml")
    if baseline is not None and baseline_config_path:
        shutil.copy2(baseline_config_path, report_dir / "baseline_config.yaml")
    write_text(report_dir / "latest_candidate_raw_results_path.txt", str(candidate.output_dir))
    if baseline is not None:
        write_text(report_dir / "latest_baseline_raw_results_path.txt", str(baseline.output_dir))

    return ExperimentResult(report_dir=report_dir, candidate=candidate, baseline=baseline, metrics_path=metrics_path, report_path=report_path)
