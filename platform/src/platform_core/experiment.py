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
from src.platform_core.metrics import OOS_START_DATE, TRAINING_END_DATE, build_platform_metrics, comparison_metrics
from src.platform_core.runtime_config import apply_runtime_dates
from src.platform_core.slippage import apply_slippage_scenario
from src.platform_core.storage import SQLiteStore, InMemoryStore
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
    strategy = config.get("strategy")
    if isinstance(strategy, dict):
        return str(strategy.get("strategy_name", "platform_strategy"))
    return str(config.get("platform", {}).get("run_name", "platform_strategy"))


def run_name(config: dict[str, Any], label: str) -> str:
    base = config.get("platform", {}).get("run_name") or strategy_name(config)
    return f"{base}_{label}"


def run_backtest(
    config: dict[str, Any],
    label: str,
    store: SQLiteStore | InMemoryStore,
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
    if not candidate.get("training_metrics_available"):
        return "继续改进：缺少训练样本指标"
    if not candidate.get("oos_metrics_available"):
        return "继续改进：缺少样本外指标"
    if not baseline.get("training_metrics_available") or not baseline.get("oos_metrics_available"):
        return "继续改进：baseline 缺少训练或样本外指标"

    candidate_oos = candidate.get("oos_metrics") or {}
    baseline_oos = baseline.get("oos_metrics") or {}
    sharpe_up = (candidate_oos.get("sharpe_ratio") or 0) > (baseline_oos.get("sharpe_ratio") or 0)
    drawdown_ok = (candidate_oos.get("max_drawdown") or 0) >= (baseline_oos.get("max_drawdown") or 0)
    candidate_turnover = candidate_oos.get("annualized_turnover_amount", candidate_oos.get("annualized_turnover")) or 0
    baseline_turnover = baseline_oos.get("annualized_turnover_amount", baseline_oos.get("annualized_turnover")) or 0
    turnover_ok = candidate_turnover <= baseline_turnover * 1.2
    execution_ok = (candidate_oos.get("rejected_order_count") or 0) <= (baseline_oos.get("rejected_order_count") or 0)
    return "接受" if sharpe_up and drawdown_ok and turnover_ok and execution_ok else "继续改进"


def metric_lines(title: str, metrics: dict[str, Any]) -> list[str]:
    return [
        "",
        f"## {title}",
        f"- 开始日期：{metrics.get('start_date')}",
        f"- 结束日期：{metrics.get('end_date')}",
        f"- 观测数：{metrics.get('observations')}",
        f"- 累计收益率：{pct_or_na(metrics.get('total_return'))}",
        f"- 年化收益率：{pct_or_na(metrics.get('annualized_return'))}",
        f"- 年化波动率：{pct_or_na(metrics.get('annualized_volatility'))}",
        f"- 最大回撤：{pct_or_na(metrics.get('max_drawdown'))}",
        f"- Sharpe：{num_or_na(metrics.get('sharpe_ratio'))}",
        f"- 年化金额换手率：{pct_or_na(metrics.get('annualized_turnover_amount', metrics.get('annualized_turnover')))}",
        f"- 成交笔数：{metrics.get('trade_count')}",
        f"- 订单数：{metrics.get('order_count')}",
        f"- 拒单数：{metrics.get('rejected_order_count')}",
        f"- 最大待执行意图数：{metrics.get('max_pending_intent_count')}",
        f"- 平均现金权重：{pct_or_na(metrics.get('average_cash_weight'))}",
    ]


def build_report(
    experiment_name: str,
    candidate: ExperimentRun,
    baseline: ExperimentRun | None,
    candidate_config_path: Path,
    baseline_config_path: Path | None,
    comparison: dict[str, Any],
    training_comparison: dict[str, Any] | None = None,
    oos_comparison: dict[str, Any] | None = None,
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
            "## 样本切分",
            f"- 训练样本截至：`{TRAINING_END_DATE}`",
            f"- 样本外起始：`{OOS_START_DATE}`",
            f"- 候选是否有训练指标：{bool_zh(c.get('training_metrics_available'))}",
            f"- 候选是否有样本外指标：{bool_zh(c.get('oos_metrics_available'))}",
        ]
    )
    if baseline is not None:
        b = baseline.metrics
        lines.extend(
            [
                f"- Baseline 是否有训练指标：{bool_zh(b.get('training_metrics_available'))}",
                f"- Baseline 是否有样本外指标：{bool_zh(b.get('oos_metrics_available'))}",
            ]
        )

    lines.extend(metric_lines("候选全样本指标", c.get("full_metrics") or c))
    lines.extend(metric_lines("候选训练样本指标", c.get("training_metrics") or {}))
    lines.extend(metric_lines("候选样本外指标", c.get("oos_metrics") or {}))

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
            "skipped_order_count_delta": "跳过订单数差值",
            "skipped_below_lot_or_cash_count_delta": "低于一手或现金不足跳过数差值",
            "max_pending_intent_count_delta": "最大待执行意图数差值",
            "average_cash_weight_delta": "平均现金权重差值",
        }
        for key, value in comparison.items():
            lines.append(f"- {comparison_labels.get(key, key)}：{num_or_na(value)}")
        if training_comparison:
            lines.extend(["", "## 训练样本对比"])
            for key, value in training_comparison.items():
                lines.append(f"- {comparison_labels.get(key, key)}：{num_or_na(value)}")
        if oos_comparison:
            lines.extend(["", "## 样本外对比"])
            for key, value in oos_comparison.items():
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
    start_date: str | None = None,
    end_date: str | None = None,
    slippage_scenario: str | None = None,
) -> ExperimentResult:
    candidate_config_path = Path(candidate_config_path)
    baseline_config_path = Path(baseline_config_path) if baseline_config_path else candidate_config_path
    candidate_config = apply_runtime_dates(load_yaml(candidate_config_path), start_date=start_date, end_date=end_date)
    baseline_config = None if skip_baseline else apply_runtime_dates(load_yaml(baseline_config_path), start_date=start_date, end_date=end_date)
    if slippage_scenario is not None:
        candidate_config = apply_slippage_scenario(candidate_config, slippage_scenario)
        if baseline_config is not None:
            baseline_config = apply_slippage_scenario(baseline_config, slippage_scenario)

    resolved_name = experiment_name or strategy_name(candidate_config)
    if slippage_scenario is not None:
        resolved_name = f"{resolved_name}_{slippage_scenario}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(report_root) / resolved_name / timestamp
    raw_dir = Path(raw_root) / resolved_name / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    enable_db = (candidate_config.get("backtest") or {}).get("enable_database", False)
    if enable_db:
        store = SQLiteStore(db_path)
    else:
        store = InMemoryStore()
    try:
        candidate = run_backtest(candidate_config, "candidate", store, raw_dir, render_charts=render_charts)
        baseline = None
        if baseline_config is not None:
            baseline = run_backtest(baseline_config, "baseline", store, raw_dir, render_charts=render_charts)
    finally:
        store.close()

    comparison = comparison_metrics(candidate.metrics, baseline.metrics if baseline else None)
    training_comparison = comparison_metrics(
        candidate.metrics.get("training_metrics") or {},
        (baseline.metrics.get("training_metrics") if baseline else None),
    )
    oos_comparison = comparison_metrics(
        candidate.metrics.get("oos_metrics") or {},
        (baseline.metrics.get("oos_metrics") if baseline else None),
    )
    recommendation_text = recommendation(candidate.metrics, baseline.metrics if baseline else None)
    payload = {
        "experiment_name": resolved_name,
        "candidate_config": str(candidate_config_path),
        "baseline_config": None if baseline is None else str(baseline_config_path),
        "slippage_scenario": slippage_scenario,
        "candidate": candidate.metrics,
        "baseline": None if baseline is None else baseline.metrics,
        "comparison": comparison,
        "training_comparison": training_comparison,
        "oos_comparison": oos_comparison,
        "recommendation": recommendation_text,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    metrics_path = report_dir / "metrics.json"
    report_path = report_dir / "report.md"
    write_json(metrics_path, payload)
    write_text(
        report_path,
        build_report(
            resolved_name,
            candidate,
            baseline,
            candidate_config_path,
            baseline_config_path if baseline else None,
            comparison,
            training_comparison,
            oos_comparison,
        ),
    )
    shutil.copy2(candidate_config_path, report_dir / "candidate_config.yaml")
    if baseline is not None and baseline_config_path:
        shutil.copy2(baseline_config_path, report_dir / "baseline_config.yaml")
    write_text(report_dir / "latest_candidate_raw_results_path.txt", str(candidate.output_dir))
    if baseline is not None:
        write_text(report_dir / "latest_baseline_raw_results_path.txt", str(baseline.output_dir))

    return ExperimentResult(report_dir=report_dir, candidate=candidate, baseline=baseline, metrics_path=metrics_path, report_path=report_path)
