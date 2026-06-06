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


def bool_zh(value: Any) -> str:
    return "是" if bool(value) else "否"


def recommendation(candidate: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    if baseline is None:
        return "复核"
    sharpe_up = (candidate.get("sharpe_ratio") or 0) > (baseline.get("sharpe_ratio") or 0)
    drawdown_ok = (candidate.get("max_drawdown") or 0) >= (baseline.get("max_drawdown") or 0)
    candidate_turnover = candidate.get("annualized_turnover_amount", candidate.get("annualized_turnover")) or 0
    baseline_turnover = baseline.get("annualized_turnover_amount", baseline.get("annualized_turnover")) or 0
    turnover_ok = candidate_turnover <= baseline_turnover * 1.2
    execution_ok = (candidate.get("rejected_order_count") or 0) <= (baseline.get("rejected_order_count") or 0)
    return "接受" if sharpe_up and drawdown_ok and turnover_ok and execution_ok else "继续改进"


def build_report(
    experiment_name: str,
    candidate: ExperimentRun,
    baseline: ExperimentRun | None,
    candidate_config_path: Path,
    baseline_config_path: Path | None,
    comparison: dict[str, Any],
) -> str:
    lines = [
        f"# 平台实验报告：{experiment_name}",
        "",
        "## 目标",
        "运行标准化平台实验，并在 baseline 可用时进行对比。",
        "",
        "## 产物",
        f"- 候选原始结果路径：`{candidate.output_dir}`",
        f"- 候选配置：`{candidate_config_path}`",
    ]
    if baseline is not None:
        lines.extend([f"- Baseline 原始结果路径：`{baseline.output_dir}`", f"- Baseline 配置：`{baseline_config_path}`"])

    c = candidate.metrics
    lines.extend(
        [
            "",
            "## 候选指标",
            f"- 累计收益率：{pct_or_na(c.get('total_return'))}",
            f"- 年化收益率：{pct_or_na(c.get('annualized_return'))}",
            f"- 年化波动率：{pct_or_na(c.get('annualized_volatility'))}",
            f"- 最大回撤：{pct_or_na(c.get('max_drawdown'))}",
            f"- 夏普比率：{num_or_na(c.get('sharpe_ratio'))}",
            f"- 成交金额合计：{num_or_na(c.get('turnover_amount_total'))}",
            f"- 金额换手率：{pct_or_na(c.get('turnover_amount_ratio'))}",
            f"- 年化金额换手率：{pct_or_na(c.get('annualized_turnover_amount', c.get('annualized_turnover')))}",
            f"- 成交数量合计：{num_or_na(c.get('turnover_quantity_total'))}",
            f"- 年化数量换手：{num_or_na(c.get('annualized_turnover_quantity'))}",
            f"- 成交笔数：{c.get('trade_count')}",
            f"- 订单数：{c.get('order_count')}",
            f"- 拒单数：{c.get('rejected_order_count')}",
            f"- 最大待执行意图数：{c.get('max_pending_intent_count')}",
            f"- 平均现金权重：{pct_or_na(c.get('average_cash_weight'))}",
            f"- 是否有样本外指标：{bool_zh(c.get('oos_metrics_available'))}",
        ]
    )

    if c.get("rejection_reason_counts"):
        lines.extend(["", "## 候选执行拒单"])
        for reason, count in c["rejection_reason_counts"].items():
            lines.append(f"- `{reason}`: {count}")

    if baseline is not None:
        lines.extend(["", "## Baseline 对比"])
        comparison_labels = {
            "total_return_delta": "累计收益率差值",
            "annualized_return_delta": "年化收益率差值",
            "annualized_volatility_delta": "年化波动率差值",
            "max_drawdown_delta": "最大回撤差值",
            "sharpe_ratio_delta": "夏普比率差值",
            "turnover_amount_total_delta": "成交金额合计差值",
            "turnover_amount_ratio_delta": "金额换手率差值",
            "annualized_turnover_amount_delta": "年化金额换手率差值",
            "turnover_quantity_total_delta": "成交数量合计差值",
            "annualized_turnover_quantity_delta": "年化数量换手差值",
            "trade_count_delta": "成交笔数差值",
            "order_count_delta": "订单数差值",
            "rejected_order_count_delta": "拒单数差值",
            "max_pending_intent_count_delta": "最大待执行意图数差值",
            "average_cash_weight_delta": "平均现金权重差值",
        }
        for key, value in comparison.items():
            lines.append(f"- {comparison_labels.get(key, key)}：{num_or_na(value)}")
    else:
        lines.extend(["", "## Baseline 对比", "- 本次未请求 baseline 对比。"])

    lines.extend(
        [
            "",
            "## 建议",
            f"- {recommendation(c, baseline.metrics if baseline else None)}",
            "",
            "## 说明",
            "- 指标根据平台生成的 CSV 产物计算。",
            "- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。",
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
