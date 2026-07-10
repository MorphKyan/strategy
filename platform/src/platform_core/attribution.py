"""实盘 vs 影子模型的净值归因（蓝图 A5）。

原则：**只记录，不据此改持仓或改参数**。mark-to-real 环路里误差每天从真值
重置、由阈值带自愈；本模块的职责只是把"真实账户与模型的差异"量化成
tracking error 并做粗拆，作为月度体检记录。

数据源：
- 真实侧：`results/live_portfolios/<id>/real_nav.csv`（cycle 每交易日 mark-to-market）
- 模型侧：影子模拟组合 `results/sim_portfolios/<id>/runs/*/nav.csv` 拼接
  （按 run 目录名时间序拼接、同日取最新，兼容从 checkpoint 重放产生的重叠）

归因粗拆口径（写进报告的假设）：
- 现金拖累差 ≈ (真实平均现金权重 − 模型平均现金权重) × 模型区间收益
  （用模型总收益近似"投资部分收益"，粗但方向正确）
- 其余差异归入"执行与结构差异"残差项（含手续费差、成交价差、整手取整
  造成的权重差），不再往下细拆——真实侧没有逐笔费用明细，细拆是伪精度。

个人财务数据落在 `reports/live/`（已 gitignore，不入库）。
"""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.platform_core.models import date_str, parse_date

MIN_OBSERVATIONS = 5  # 少于 5 个共同收益观测视为样本不足


def load_real_nav(live_dir: str | Path) -> list[dict[str, Any]]:
    """读取真实净值序列，返回按日期升序的 [{date, total_value, cash}, ...]。"""
    path = Path(live_dir) / "real_nav.csv"
    if not path.exists():
        raise FileNotFoundError(f"真实净值文件不存在: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [
            {"date": row["date"], "total_value": float(row["total_value"]), "cash": float(row["cash"])}
            for row in csv.DictReader(handle)
        ]
    return sorted(rows, key=lambda row: row["date"])


def load_shadow_nav(sim_dir: str | Path) -> list[dict[str, Any]]:
    """拼接影子模拟组合所有 run 的 nav.csv，同日取最新 run 的值。"""
    runs_dir = Path(sim_dir) / "runs"
    if not runs_dir.exists():
        raise FileNotFoundError(f"影子组合 runs 目录不存在: {runs_dir}")
    by_date: dict[str, dict[str, Any]] = {}
    for run_dir in sorted(runs_dir.iterdir()):
        nav_path = run_dir / "nav.csv"
        if not nav_path.exists() or nav_path.stat().st_size == 0:
            continue
        with nav_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                by_date[row["date"]] = {
                    "date": row["date"],
                    "total_value": float(row["total_value"]),
                    "cash": float(row["cash"]),
                }
    return [by_date[key] for key in sorted(by_date)]


def month_window(month: str) -> tuple[date, date]:
    """"YYYY-MM" → (当月首日, 当月末日)。"""
    start = parse_date(f"{month}-01")
    next_month = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    return start, next_month - timedelta(days=1)


def previous_month(today: date) -> str:
    first = date(today.year, today.month, 1)
    last_of_prev = first - timedelta(days=1)
    return f"{last_of_prev.year:04d}-{last_of_prev.month:02d}"


def build_live_attribution(
    real_rows: list[dict[str, Any]],
    shadow_rows: list[dict[str, Any]],
    start: date,
    end: date,
) -> dict[str, Any]:
    """在 [start, end] 窗口内对齐真实/模型净值，计算收益差与 tracking error。

    锚点规则：若窗口前存在共同日期，取最近一个作为收益基准（使窗口首日的
    涨跌也计入）；否则以窗口内第一个共同日期为基准。
    """
    real_by_date = {row["date"]: row for row in real_rows}
    shadow_by_date = {row["date"]: row for row in shadow_rows}
    common = sorted(set(real_by_date) & set(shadow_by_date))
    window_dates = [d for d in common if date_str(start) <= d <= date_str(end)]
    anchor_candidates = [d for d in common if d < date_str(start)]
    if anchor_candidates and window_dates:
        aligned_dates = [anchor_candidates[-1], *window_dates]
    else:
        aligned_dates = window_dates

    result: dict[str, Any] = {
        "start": date_str(start),
        "end": date_str(end),
        "common_dates": len(window_dates),
        "observations": max(0, len(aligned_dates) - 1),
        "sufficient": (len(aligned_dates) - 1) >= MIN_OBSERVATIONS,
    }
    if len(aligned_dates) < 2:
        return result

    real_series = [real_by_date[d]["total_value"] for d in aligned_dates]
    shadow_series = [shadow_by_date[d]["total_value"] for d in aligned_dates]
    real_returns = [b / a - 1.0 for a, b in zip(real_series, real_series[1:])]
    shadow_returns = [b / a - 1.0 for a, b in zip(shadow_series, shadow_series[1:])]
    diffs = [r - m for r, m in zip(real_returns, shadow_returns)]

    real_cum = real_series[-1] / real_series[0] - 1.0
    shadow_cum = shadow_series[-1] / shadow_series[0] - 1.0
    diff_cum = real_cum - shadow_cum

    if len(diffs) > 1:
        mean_diff = sum(diffs) / len(diffs)
        variance = sum((d - mean_diff) ** 2 for d in diffs) / (len(diffs) - 1)
        te_annualized = math.sqrt(variance) * math.sqrt(252)
    else:
        te_annualized = None

    real_cash_w = [real_by_date[d]["cash"] / real_by_date[d]["total_value"] for d in aligned_dates if real_by_date[d]["total_value"] > 0]
    shadow_cash_w = [shadow_by_date[d]["cash"] / shadow_by_date[d]["total_value"] for d in aligned_dates if shadow_by_date[d]["total_value"] > 0]
    mean_real_cash = sum(real_cash_w) / len(real_cash_w) if real_cash_w else 0.0
    mean_shadow_cash = sum(shadow_cash_w) / len(shadow_cash_w) if shadow_cash_w else 0.0
    cash_drag_component = -(mean_real_cash - mean_shadow_cash) * shadow_cum
    residual = diff_cum - cash_drag_component

    result.update(
        {
            "real_cum_return": real_cum,
            "shadow_cum_return": shadow_cum,
            "diff_cum_return": diff_cum,
            "tracking_error_annualized": te_annualized,
            "mean_real_cash_weight": mean_real_cash,
            "mean_shadow_cash_weight": mean_shadow_cash,
            "cash_drag_component": cash_drag_component,
            "execution_residual": residual,
            "real_total_start": real_series[0],
            "real_total_end": real_series[-1],
        }
    )
    return result


def render_attribution_md(result: dict[str, Any], live_id: str, shadow_id: str, month: str) -> str:
    """渲染中文月度归因报告（markdown）。"""
    lines = [
        f"# 实盘月度归因 · {month}",
        "",
        f"> 真实侧：`{live_id}`（real_nav.csv 日频估值） | 模型侧：影子组合 `{shadow_id}`",
        f"> 窗口：{result['start']} → {result['end']} | 共同交易日 {result['common_dates']} 个，收益观测 {result['observations']} 个",
        "> 纪律：本报告**只记录、不据此改持仓或改参数**；位置层面误差由阈值带自愈。",
        "",
    ]
    if not result.get("sufficient"):
        lines += [
            f"**样本不足**（收益观测 < {MIN_OBSERVATIONS}），本月不出具归因结论，仅存档。",
        ]
        if result.get("observations", 0) >= 1:
            lines += [
                "",
                f"- 真实区间收益：{result['real_cum_return']:+.4%}",
                f"- 模型区间收益：{result['shadow_cum_return']:+.4%}",
            ]
        return "\n".join(lines)

    te = result["tracking_error_annualized"]
    lines += [
        "## 核心指标",
        "",
        f"- **真实区间收益**：{result['real_cum_return']:+.4%}（总值 {result['real_total_start']:,.2f} → {result['real_total_end']:,.2f}）",
        f"- **模型区间收益**：{result['shadow_cum_return']:+.4%}",
        f"- **累计差异（真实 − 模型）**：{result['diff_cum_return'] * 10000:+.1f} bp",
        f"- **Tracking Error（年化）**：{te * 10000:,.1f} bp" if te is not None else "- Tracking Error：观测不足",
        "",
        "## 差异粗拆",
        "",
        f"- 现金拖累差：{result['cash_drag_component'] * 10000:+.1f} bp（真实平均现金 {result['mean_real_cash_weight']:.2%} vs 模型 {result['mean_shadow_cash_weight']:.2%}，按模型区间收益近似）",
        f"- 执行与结构差异（残差，含手续费差/成交价差/整手取整）：{result['execution_residual'] * 10000:+.1f} bp",
        "",
        "> 口径说明：现金拖累用模型总收益近似投资部分收益，方向正确、量级粗略；",
        "> 残差不再细拆——真实侧无逐笔费用明细，细拆是伪精度。",
    ]
    return "\n".join(lines)
