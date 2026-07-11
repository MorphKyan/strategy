from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.platform_dashboard.artifacts import (
    ConfigRecord,
    RunRecord,
    align_navs,
    build_weighted_portfolio,
    discover_configs,
    discover_market_symbols,
    discover_runs,
    downsample_timeseries,
    infer_slippage_scenario,
    latest_positions,
    nav_analytics,
    platform_root,
    read_run_metrics,
    read_run_table,
    read_corporate_actions,
    read_market_history,
    rebalance_events,
    portfolio_risk_analysis,
    SLIPPAGE_SCENARIOS,
    rebase_benchmark,
    window_start_date,
)


st.set_page_config(page_title="Platform 回测看板", page_icon="📈", layout="wide")

# A 股配色习惯：红涨绿跌
UP_COLOR = "#c62828"
DOWN_COLOR = "#1b8a3a"
RETURN_COLORSCALE = [[0.0, "#1b8a3a"], [0.5, "#f7f7f7"], [1.0, "#c62828"]]
MONTH_LABELS = [f"{month}月" for month in range(1, 13)]

@st.cache_data(show_spinner=False, ttl=30)
def cached_configs(root: str) -> list[ConfigRecord]:
    return discover_configs(Path(root))


@st.cache_data(show_spinner=False, ttl=30)
def cached_runs(root: str) -> list[RunRecord]:
    return discover_runs(Path(root))


@st.cache_data(show_spinner=False, max_entries=128, ttl=600)
def cached_table(run_dir: str, name: str, modified_at: float) -> pd.DataFrame:
    del modified_at
    return read_run_table(Path(run_dir), name)


def run_table(run: RunRecord, name: str) -> pd.DataFrame:
    path = run.path / f"{name}.csv"
    modified_at = path.stat().st_mtime if path.exists() else 0.0
    return cached_table(str(run.path), name, modified_at)


@st.cache_data(show_spinner=False, max_entries=128, ttl=600)
def cached_metrics(run_dir: str, modified_at: float) -> dict[str, Any]:
    del modified_at
    return read_run_metrics(Path(run_dir))


def run_metrics(run: RunRecord) -> dict[str, Any]:
    manifest = run.path / "manifest.json"
    metrics = run.path / "metrics.json"
    modified_at = max(manifest.stat().st_mtime, metrics.stat().st_mtime if metrics.exists() else 0.0)
    return cached_metrics(str(run.path), modified_at)


@st.cache_data(show_spinner=False, max_entries=64, ttl=600)
def cached_market_history(root: str, symbol: str, modified_at: float) -> pd.DataFrame:
    del modified_at
    return read_market_history(Path(root), symbol)


def market_history(root: Path, symbol: str) -> pd.DataFrame:
    path = root / "data" / f"{symbol}.csv"
    return cached_market_history(str(root), symbol, path.stat().st_mtime if path.exists() else 0.0)


@st.cache_data(show_spinner=False, max_entries=64, ttl=600)
def cached_actions(root: str, symbol: str, signature: tuple[float, float]) -> dict[str, pd.DataFrame]:
    del signature
    return read_corporate_actions(Path(root), symbol)


def corporate_actions(root: Path, symbol: str) -> dict[str, pd.DataFrame]:
    paths = [root / "data" / "platform_dividends.csv", root / "data" / "platform_splits.csv"]
    signature = tuple(path.stat().st_mtime if path.exists() else 0.0 for path in paths)
    return cached_actions(str(root), symbol, signature)


def metric_text(value: Any, kind: str = "number") -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return "—"
    if kind == "text":
        return str(value)
    if kind == "percent":
        return f"{float(value):.2%}"
    if kind == "integer":
        return f"{int(value):,}"
    return f"{float(value):.3f}"


def signed_colors(values: pd.Series) -> list[str]:
    return [UP_COLOR if value >= 0 else DOWN_COLOR for value in values]


def render_header() -> None:
    st.title("Platform 回测看板")
    st.caption("本地只读视图 · 数据来自 platform 配置与回测 artifact")


# ---------------------------------------------------------------- 概览


def render_overview(configs: list[ConfigRecord], runs: list[RunRecord]) -> None:
    st.subheader("概览")
    cols = st.columns(4)
    cols[0].metric("策略配置", len(configs))
    cols[1].metric("已发现回测", len(runs))
    cols[2].metric("内置策略类型", len({item.strategy_name for item in configs}))
    latest = runs[0].generated_at[:10] if runs and runs[0].generated_at else "—"
    cols[3].metric("最近回测", latest)

    st.markdown("#### 最近回测")
    if not runs:
        st.info("尚未发现包含 nav.csv 和 manifest.json 的回测结果。")
        return
    rows = []
    for run in runs[:10]:
        rows.append(
            {
                "run_id": run.run_id,
                "区间": f"{run.start_date} → {run.end_date}",
                "累计收益": metric_text(run.metrics.get("total_return"), "percent"),
                "年化收益": metric_text(run.metrics.get("annualized_return"), "percent"),
                "年化波动": metric_text(run.metrics.get("annualized_volatility"), "percent"),
                "最大回撤": metric_text(run.metrics.get("max_drawdown"), "percent"),
                "Sharpe": metric_text(run.metrics.get("sharpe_ratio")),
                "滑点场景": metric_text(run.metrics.get("slippage_scenario"), "text"),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ---------------------------------------------------------------- 回测分析


def render_run_metrics(run: RunRecord) -> None:
    metrics = run_metrics(run)
    first = st.columns(5)
    first[0].metric("累计收益", metric_text(metrics.get("total_return"), "percent"))
    first[1].metric("年化收益", metric_text(metrics.get("annualized_return"), "percent"))
    first[2].metric("年化波动", metric_text(metrics.get("annualized_volatility"), "percent"))
    first[3].metric("最大回撤", metric_text(metrics.get("max_drawdown"), "percent"))
    first[4].metric("Sharpe", metric_text(metrics.get("sharpe_ratio")))
    second = st.columns(5)
    second[0].metric("年化换手", metric_text(metrics.get("annualized_turnover"), "percent"))
    second[1].metric("年化费用拖累", metric_text(metrics.get("annualized_fee_drag"), "percent"))
    second[2].metric("交易数", metric_text(metrics.get("trade_count"), "integer"))
    second[3].metric("拒单数", metric_text(metrics.get("rejected_order_count"), "integer"))
    second[4].metric("平均现金", metric_text(metrics.get("average_cash_weight"), "percent"))

    training = metrics.get("training_metrics") or {}
    oos = metrics.get("oos_metrics") or {}
    if metrics.get("training_metrics_available") and metrics.get("oos_metrics_available"):
        with st.expander("训练样本 vs 冻结测试样本（2025-07-01 起）"):
            keys = [
                ("annualized_return", "年化收益", "percent"),
                ("annualized_volatility", "年化波动", "percent"),
                ("max_drawdown", "最大回撤", "percent"),
                ("sharpe_ratio", "Sharpe", "number"),
            ]
            frame = pd.DataFrame(
                {
                    "指标": [label for _, label, _ in keys],
                    "训练样本": [metric_text(training.get(key), kind) for key, _, kind in keys],
                    "冻结样本": [metric_text(oos.get(key), kind) for key, _, kind in keys],
                }
            )
            st.dataframe(frame, width="stretch", hide_index=True)


PERFORMANCE_PERIODS = ["近1月", "近3月", "近6月", "今年", "近1年", "近2年", "近3年", "全部"]


def render_performance(nav: pd.DataFrame, run: RunRecord, runs: list[RunRecord]) -> None:
    if nav.empty or "net_value" not in nav:
        st.info("该运行没有可展示的净值数据。")
        return

    controls = st.columns([1.1, 3.2, 1.6, 0.7])
    others = [item for item in runs if item.run_id != run.run_id]
    with controls[0]:
        mode = st.radio("显示", ["净值", "收益率"], horizontal=True)
    with controls[1]:
        period = st.radio("区间", PERFORMANCE_PERIODS, index=len(PERFORMANCE_PERIODS) - 1, horizontal=True)
    with controls[2]:
        benchmark_id = st.selectbox("基准对比", ["无", *[item.run_id for item in others]])
    with controls[3]:
        log_scale = st.toggle("对数", value=False, disabled=mode == "收益率", help="长区间复利曲线建议开启")

    start = window_start_date(nav["date"].max(), period)
    window = nav if start is None else nav[nav["date"] >= start]
    if len(window) < 2:
        st.info("所选区间内的净值数据不足两天。")
        return
    window = window[["date", "net_value"]].copy()
    base = float(window["net_value"].iloc[0])
    if base == 0:
        st.info("区间首日净值为 0，无法计算。")
        return

    benchmark_window = pd.DataFrame()
    if benchmark_id != "无":
        benchmark_run = next(item for item in others if item.run_id == benchmark_id)
        benchmark_window = rebase_benchmark(window, run_table(benchmark_run, "nav"))
        if benchmark_window.empty:
            st.warning("与所选基准在该区间内无重叠，无法对比。")

    as_return = mode == "收益率"

    def display_series(values: pd.Series) -> pd.Series:
        return values / base - 1.0 if as_return else values

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=window["date"], y=display_series(window["net_value"]), name="本策略", line={"width": 2})
    )
    if not benchmark_window.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_window["date"],
                y=display_series(benchmark_window["net_value"]),
                name=f"基准 · {benchmark_id}",
                line={"width": 1.5, "dash": "dash", "color": "#888888"},
            )
        )
    if as_return:
        fig.add_hline(y=0, line_dash="dot", line_color="#999999")
    fig.update_xaxes(rangeslider={"visible": True, "thickness": 0.06})
    fig.update_layout(
        height=460,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        yaxis_title="区间收益" if as_return else "净值",
        yaxis_tickformat=".1%" if as_return else None,
        yaxis_type="log" if log_scale and not as_return else "linear",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    st.plotly_chart(fig, width="stretch")

    if not benchmark_window.empty:
        merged = pd.merge(
            window,
            benchmark_window.rename(columns={"net_value": "benchmark"}),
            on="date",
            how="inner",
        )
        if not merged.empty:
            merged["excess"] = merged["net_value"] / merged["benchmark"] - 1.0
            excess = go.Figure()
            excess.add_trace(
                go.Scatter(x=merged["date"], y=merged["excess"], name="超额收益", line={"width": 1.5, "color": UP_COLOR})
            )
            excess.add_hline(y=0, line_dash="dot", line_color="#999999")
            excess.update_layout(
                height=220,
                margin={"l": 10, "r": 10, "t": 30, "b": 10},
                yaxis_title="相对基准超额",
                yaxis_tickformat=".1%",
            )
            st.plotly_chart(excess, width="stretch")

    drawdown_series = window["net_value"] / window["net_value"].cummax() - 1.0
    drawdown_frame = pd.DataFrame({"date": window["date"], "drawdown": drawdown_series})
    drawdown = px.area(drawdown_frame, x="date", y="drawdown", labels={"date": "日期", "drawdown": "回撤"})
    drawdown.update_traces(line_color="#d9534f", fillcolor="rgba(217,83,79,0.25)")
    drawdown.update_layout(height=260, margin={"l": 10, "r": 10, "t": 20, "b": 10}, yaxis_tickformat=".1%")
    st.plotly_chart(drawdown, width="stretch")
    if start is not None:
        st.caption(f"区间：{window['date'].iloc[0].date()} → {window['date'].iloc[-1].date()}，回撤按区间内高点计算。")


def render_return_decomposition(nav: pd.DataFrame) -> None:
    analytics = nav_analytics(nav)
    monthly_pivot = analytics["monthly_pivot"]
    if monthly_pivot.empty:
        st.info("样本不足一个月，暂无收益分解。")
        return

    st.markdown("#### 月度收益热力图")
    text = monthly_pivot.map(lambda value: "" if pd.isna(value) else f"{value:.1%}")
    heatmap = go.Figure(
        go.Heatmap(
            z=monthly_pivot.values,
            x=MONTH_LABELS,
            y=[str(year) for year in monthly_pivot.index],
            text=text.values,
            texttemplate="%{text}",
            colorscale=RETURN_COLORSCALE,
            zmid=0,
            colorbar={"tickformat": ".0%"},
            hovertemplate="%{y}年%{x}: %{z:.2%}<extra></extra>",
        )
    )
    heatmap.update_yaxes(autorange="reversed")
    heatmap.update_layout(height=90 + 42 * len(monthly_pivot), margin={"l": 10, "r": 10, "t": 10, "b": 10})
    st.plotly_chart(heatmap, width="stretch")

    left, right = st.columns(2)
    yearly = analytics["yearly"]
    with left:
        st.markdown("#### 年度收益")
        if yearly.empty:
            st.caption("样本不足。")
        else:
            bars = go.Figure(
                go.Bar(
                    x=yearly["year"],
                    y=yearly["ret"],
                    marker_color=signed_colors(yearly["ret"]),
                    text=[f"{value:.1%}" for value in yearly["ret"]],
                    textposition="outside",
                )
            )
            bars.update_layout(height=320, margin={"l": 10, "r": 10, "t": 20, "b": 10}, yaxis_tickformat=".0%")
            st.plotly_chart(bars, width="stretch")
    daily = analytics["daily"]
    with right:
        st.markdown("#### 日收益分布")
        if daily.empty:
            st.caption("样本不足。")
        else:
            hist = px.histogram(daily, x="ret", nbins=60, labels={"ret": "日收益"})
            hist.update_traces(marker_color="#4a6fa5")
            hist.update_layout(
                height=320,
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
                xaxis_tickformat=".1%",
                yaxis_title="天数",
            )
            st.plotly_chart(hist, width="stretch")

    monthly = analytics["monthly"]
    if not monthly.empty:
        st.markdown("#### 月度收益序列")
        bars = go.Figure(
            go.Bar(x=monthly["date"], y=monthly["ret"], marker_color=signed_colors(monthly["ret"]))
        )
        bars.update_layout(height=260, margin={"l": 10, "r": 10, "t": 20, "b": 10}, yaxis_tickformat=".0%")
        st.plotly_chart(bars, width="stretch")

    rolling = analytics["rolling"]
    if not rolling.empty:
        left, right = st.columns(2)
        with left:
            if "vol_60d" in rolling:
                st.markdown("#### 滚动 60 日年化波动")
                vol = go.Figure(
                    go.Scatter(x=rolling["date"], y=rolling["vol_60d"], line={"width": 1.5, "color": "#e08e0b"})
                )
                vol.update_layout(height=260, margin={"l": 10, "r": 10, "t": 20, "b": 10}, yaxis_tickformat=".0%")
                st.plotly_chart(vol, width="stretch")
        with right:
            if "sharpe_252d" in rolling:
                st.markdown("#### 滚动 252 日 Sharpe")
                sharpe = go.Figure(
                    go.Scatter(x=rolling["date"], y=rolling["sharpe_252d"], line={"width": 1.5, "color": "#4a6fa5"})
                )
                sharpe.add_hline(y=0, line_dash="dot", line_color="#999999")
                sharpe.update_layout(height=260, margin={"l": 10, "r": 10, "t": 20, "b": 10})
                st.plotly_chart(sharpe, width="stretch")


def render_positions(positions: pd.DataFrame) -> None:
    if positions.empty:
        st.info("该运行没有持仓记录。")
        return
    latest = latest_positions(positions)
    latest_display = latest.copy()
    if "weight" in latest_display:
        latest_display["weight"] = latest_display["weight"].map(lambda value: metric_text(value, "percent"))
    left, right = st.columns([1, 1.4])
    with left:
        st.markdown("#### 最新持仓")
        st.dataframe(latest_display, width="stretch", hide_index=True)
    with right:
        if {"date", "asset_id", "weight"}.issubset(positions.columns):
            weights = positions[["date", "asset_id", "weight"]].copy()
            cash = 1.0 - weights.groupby("date")["weight"].sum()
            cash_frame = cash.clip(lower=0).rename("weight").reset_index()
            cash_frame["asset_id"] = "现金"
            weights = pd.concat([weights, cash_frame], ignore_index=True)
            chart = px.area(weights, x="date", y="weight", color="asset_id", labels={"date": "日期", "weight": "权重"})
            chart.update_layout(height=400, margin={"l": 10, "r": 10, "t": 30, "b": 10}, yaxis_tickformat=".0%")
            st.plotly_chart(chart, width="stretch")


def render_execution(tables: dict[str, pd.DataFrame]) -> None:
    for title, name in (("订单", "orders"), ("交易", "trades"), ("跳过/拒绝订单", "skipped_orders")):
        st.markdown(f"#### {title}")
        frame = tables[name]
        if frame.empty:
            st.caption("无记录")
        else:
            st.dataframe(frame.sort_values("date", ascending=False), width="stretch", hide_index=True)


def render_rebalance_overlay(run: RunRecord, root: Path) -> None:
    orders = run_table(run, "orders")
    events = rebalance_events(orders)
    if events.empty:
        st.info("该运行没有已成交调仓记录。")
        return
    asset_ids = sorted(orders.get("asset_id", pd.Series(dtype=str)).dropna().astype(str).unique())
    selected = st.selectbox("叠加行情合约", asset_ids)
    symbol = selected.split(":")[-1].split(".")[0]
    history = market_history(root, symbol)
    if history.empty:
        st.warning(f"未找到 {symbol} 的本地行情。")
        return
    asset_orders = orders[orders["asset_id"].astype(str) == selected].copy()
    asset_orders["date"] = pd.to_datetime(asset_orders["date"], errors="coerce")
    start = min(history["trade_date"].max(), pd.Timestamp(run.start_date or history["trade_date"].min()))
    price = history[history["trade_date"] >= start]
    fig = go.Figure(go.Scatter(x=price["trade_date"], y=price["close"], name="收盘价", line={"width": 1.4}))
    for side, color, symbol_shape in (("BUY", UP_COLOR, "triangle-up"), ("SELL", DOWN_COLOR, "triangle-down")):
        points = asset_orders[asset_orders.get("side", "").astype(str).str.upper() == side]
        if not points.empty:
            fig.add_trace(go.Scatter(x=points["date"], y=points.get("price"), mode="markers", name=side,
                                     marker={"color": color, "symbol": symbol_shape, "size": 10},
                                     customdata=points[[column for column in ("quantity", "target_weight", "signal_date") if column in points]].to_numpy(),
                                     hovertemplate=f"{side}<br>%{{x|%Y-%m-%d}}<br>价格 %{{y:.3f}}<extra></extra>"))
    fig.update_layout(height=480, margin={"l": 10, "r": 10, "t": 20, "b": 10}, legend={"orientation": "h"})
    fig.update_xaxes(rangeslider={"visible": True, "thickness": 0.06})
    st.plotly_chart(fig, width="stretch")
    st.markdown("#### 调仓日期")
    shown = events.rename(columns={"signal_date": "信号日期", "date": "执行日期", "order_count": "订单数", "trade_value": "成交额"})
    st.dataframe(shown.sort_values("执行日期", ascending=False), width="stretch", hide_index=True)


def render_runs(runs: list[RunRecord]) -> None:
    st.subheader("回测分析")
    if not runs:
        st.warning("未发现可读取的回测结果。")
        return
    selected_id = st.selectbox(
        "选择回测",
        [item.run_id for item in runs],
        format_func=lambda run_id: next(
            f"{item.run_id} · {item.start_date} → {item.end_date}" for item in runs if item.run_id == run_id
        ),
    )
    run = next(item for item in runs if item.run_id == selected_id)
    st.caption(str(run.path))
    render_run_metrics(run)
    sections = ["净值与回撤", "收益分解", "持仓", "调仓与行情", "订单与交易", "运行信息"]
    section = st.segmented_control("分析视图", sections, default=sections[0], label_visibility="collapsed")
    if section == "净值与回撤":
        render_performance(run_table(run, "nav"), run, runs)
    elif section == "收益分解":
        render_return_decomposition(run_table(run, "nav"))
    elif section == "持仓":
        render_positions(run_table(run, "positions"))
    elif section == "调仓与行情":
        render_rebalance_overlay(run, platform_root())
    elif section == "订单与交易":
        render_execution({name: run_table(run, name) for name in ("orders", "trades", "skipped_orders")})
    else:
        st.json(run.manifest)
        snapshot = run.path / "config_snapshot.yaml"
        if snapshot.exists():
            st.markdown("#### 配置快照")
            st.code(snapshot.read_text(encoding="utf-8"), language="yaml")


# ---------------------------------------------------------------- 回测对比

COMPARE_METRICS = [
    ("total_return", "累计收益", "percent"),
    ("annualized_return", "年化收益", "percent"),
    ("annualized_volatility", "年化波动", "percent"),
    ("max_drawdown", "最大回撤", "percent"),
    ("sharpe_ratio", "Sharpe", "number"),
    ("annualized_turnover", "年化换手", "percent"),
    ("annualized_fee_drag", "年化费用拖累", "percent"),
    ("execution_slippage", "执行滑点", "percent"),
    ("trade_count", "交易数", "integer"),
    ("rejected_order_count", "拒单数", "integer"),
    ("average_cash_weight", "平均现金", "percent"),
    ("slippage_scenario", "滑点场景", "text"),
]


def render_comparison(runs: list[RunRecord]) -> None:
    st.subheader("回测对比")
    if len(runs) < 2:
        st.info("至少需要两个回测结果才能对比。")
        return
    query = st.text_input("筛选运行", placeholder="输入策略、运行名或场景关键字")
    choices = [item.run_id for item in runs if not query or query.lower() in item.run_id.lower()]
    selected_ids = st.multiselect(
        "选择 2–8 个回测",
        choices,
        default=choices[:2],
        max_selections=8,
    )
    if len(selected_ids) < 2:
        st.caption("请至少选择两个回测。")
        return

    controls = st.columns([1.1, 3.2, 2.3])
    with controls[0]:
        mode = st.radio("显示", ["净值", "收益率"], horizontal=True)
    with controls[1]:
        period = st.radio("区间", PERFORMANCE_PERIODS, index=len(PERFORMANCE_PERIODS) - 1, horizontal=True)
    with controls[2]:
        overlap_only = st.checkbox("仅对比共同重叠区间", value=True, help="各回测在区间首日对齐归一")

    selected_runs = [item for item in runs if item.run_id in selected_ids]
    nav_map = {item.run_id: run_table(item, "nav") for item in selected_runs}
    aligned = align_navs(nav_map, overlap_only=overlap_only)
    if aligned.empty:
        st.warning("所选回测没有可对齐的净值数据。")
        return
    start = window_start_date(aligned["date"].max(), period)
    if start is not None:
        aligned = align_navs(nav_map, overlap_only=overlap_only, start_date=start)
        if aligned.empty:
            st.info("所选区间内没有足够的重叠净值数据。")
            return

    as_return = mode == "收益率"
    plotted = pd.concat(
        [downsample_timeseries(group, max_points=1500) for _, group in aligned.groupby("run_id")],
        ignore_index=True,
    )
    fig = go.Figure()
    for run_id, group in plotted.groupby("run_id"):
        values = group["net_value"] - 1.0 if as_return else group["net_value"]
        fig.add_trace(go.Scatter(x=group["date"], y=values, name=run_id, line={"width": 1.8}))
    if as_return:
        fig.add_hline(y=0, line_dash="dot", line_color="#999999")
    fig.update_xaxes(rangeslider={"visible": True, "thickness": 0.06})
    fig.update_layout(
        height=460,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        yaxis_title="区间收益" if as_return else "归一净值",
        yaxis_tickformat=".1%" if as_return else None,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"区间：{aligned['date'].min().date()} → {aligned['date'].max().date()}，各回测在区间首日对齐归一，回撤按区间内高点计算。"
    )

    drawdown = go.Figure()
    for run_id, group in plotted.groupby("run_id"):
        drawdown.add_trace(go.Scatter(x=group["date"], y=group["drawdown"], name=run_id, line={"width": 1.2}))
    drawdown.update_layout(
        height=260,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        yaxis_title="回撤",
        yaxis_tickformat=".1%",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    st.plotly_chart(drawdown, width="stretch")

    st.markdown("#### 指标对照（全样本口径）")
    table = {"指标": [label for _, label, _ in COMPARE_METRICS]}
    for run in selected_runs:
        metrics = run_metrics(run)
        table[run.run_id] = [metric_text(metrics.get(key), kind) for key, _, kind in COMPARE_METRICS]
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)

    tab_year, tab_rolling, tab_slippage = st.tabs(["年度收益", "滚动风险", "三滑点场景"])
    with tab_year:
        yearly_parts = []
        for run_id, group in aligned.groupby("run_id"):
            analytics = nav_analytics(group.rename(columns={"net_value": "net_value"}))
            yearly = analytics["yearly"].copy()
            if not yearly.empty:
                yearly["run_id"] = run_id
                yearly_parts.append(yearly)
        if yearly_parts:
            yearly_all = pd.concat(yearly_parts, ignore_index=True)
            chart = px.bar(yearly_all, x="year", y="ret", color="run_id", barmode="group",
                           labels={"year": "年度", "ret": "收益", "run_id": "回测"})
            chart.update_layout(height=400, yaxis_tickformat=".1%", margin={"l": 10, "r": 10, "t": 20, "b": 10})
            st.plotly_chart(chart, width="stretch")
    with tab_rolling:
        rolling_fig = go.Figure()
        for run_id, group in aligned.groupby("run_id"):
            rolling = nav_analytics(group)["rolling"]
            if "vol_60d" in rolling:
                rolling_fig.add_trace(go.Scatter(x=rolling["date"], y=rolling["vol_60d"], name=run_id))
        rolling_fig.update_layout(height=380, yaxis_title="60日年化波动", yaxis_tickformat=".1%",
                                  margin={"l": 10, "r": 10, "t": 20, "b": 10})
        st.plotly_chart(rolling_fig, width="stretch")
    with tab_slippage:
        scenario_rows = []
        for run in selected_runs:
            metrics = run_metrics(run)
            scenario_rows.append({"run_id": run.run_id, "scenario": infer_slippage_scenario(run.run_id, metrics),
                                  **{key: metrics.get(key) for key in ("annualized_return", "sharpe_ratio", "max_drawdown", "annualized_turnover", "trade_count", "rejected_order_count")}})
        scenario_frame = pd.DataFrame(scenario_rows)
        found = set(scenario_frame["scenario"]) & set(SLIPPAGE_SCENARIOS)
        missing = [item for item in SLIPPAGE_SCENARIOS if item not in found]
        if missing:
            st.warning("所选回测缺少场景：" + "、".join(missing) + "。unknown 运行不会自动视为 default。")
        valid = scenario_frame[scenario_frame["scenario"].isin(SLIPPAGE_SCENARIOS)]
        if not valid.empty:
            metric = st.selectbox("场景指标", ["annualized_return", "sharpe_ratio", "max_drawdown", "annualized_turnover"])
            scenario_chart = px.bar(valid, x="scenario", y=metric, color="run_id", barmode="group",
                                    category_orders={"scenario": list(SLIPPAGE_SCENARIOS)})
            scenario_chart.update_layout(height=380, margin={"l": 10, "r": 10, "t": 20, "b": 10})
            st.plotly_chart(scenario_chart, width="stretch")
        st.dataframe(scenario_frame, width="stretch", hide_index=True)


# ---------------------------------------------------------------- 策略配置


def render_configs(configs: list[ConfigRecord]) -> None:
    st.subheader("策略配置")
    if not configs:
        st.warning("未发现 YAML 配置。")
        return
    strategies = sorted({item.strategy_name for item in configs})
    selected_strategy = st.selectbox("策略类型", ["全部", *strategies])
    filtered = [item for item in configs if selected_strategy == "全部" or item.strategy_name == selected_strategy]
    selected_path = st.selectbox(
        "配置文件",
        [item.relative_path for item in filtered],
        format_func=lambda value: next(item.run_name for item in filtered if item.relative_path == value),
    )
    record = next(item for item in filtered if item.relative_path == selected_path)

    cols = st.columns(3)
    cols[0].markdown(f"**策略**  \n`{record.strategy_name}`")
    cols[1].metric("资产数", len(record.assets))
    cols[2].markdown(f"**配置路径**  \n`{record.relative_path}`")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### 资产篮子")
        assets = pd.DataFrame(record.assets)
        wanted = [column for column in ("code", "name", "asset_type", "exchange", "lot_size") if column in assets]
        st.dataframe(assets[wanted] if wanted else assets, width="stretch", hide_index=True)
    with right:
        st.markdown("#### 策略参数")
        # 值列统一转字符串：参数值有数字也有字符串（如 init_mode: calculate），
        # 混合类型列无法序列化为 Arrow，会让 Streamlit 每次渲染都刷警告
        params = pd.DataFrame(
            [{"参数": str(key), "值": str(value)} for key, value in record.params.items()]
        )
        st.dataframe(params, width="stretch", hide_index=True)

    with st.expander("查看完整 YAML"):
        st.code(yaml.safe_dump(record.payload, allow_unicode=True, sort_keys=False), language="yaml")


def render_market_data(root: Path) -> None:
    st.subheader("市场数据与组合模拟")
    symbols = discover_market_symbols(root)
    if not symbols:
        st.warning("未发现本地行情数据。")
        return
    mode = st.radio("视图", ["单合约", "多合约组合"], horizontal=True)
    if mode == "单合约":
        symbol = st.selectbox("合约", symbols)
        history = market_history(root, symbol)
        if history.empty:
            st.info("该合约没有可展示行情。")
            return
        date_range = st.date_input("日期范围", value=(history["trade_date"].min().date(), history["trade_date"].max().date()))
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            history = history[history["trade_date"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]
        style = st.radio("行情类型", ["K线", "收盘价"], horizontal=True)
        fig = go.Figure()
        if style == "K线" and {"open", "high", "low", "close"}.issubset(history):
            fig.add_trace(go.Candlestick(x=history["trade_date"], open=history["open"], high=history["high"],
                                         low=history["low"], close=history["close"], name=symbol,
                                         increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR))
        else:
            fig.add_trace(go.Scatter(x=history["trade_date"], y=history["close"], name=symbol))
        actions = corporate_actions(root, symbol)
        for label, frame, date_col, value_col, color in (
            ("分红", actions["dividends"], "ex_date", "dividend_per_share", "#d99000"),
            ("转送/折算", actions["splits"], "split_date", "split_ratio", "#7b5ea7"),
        ):
            if not frame.empty:
                matched = pd.merge_asof(frame.sort_values(date_col), history[["trade_date", "close"]].sort_values("trade_date"),
                                        left_on=date_col, right_on="trade_date", direction="nearest")
                fig.add_trace(go.Scatter(x=matched[date_col], y=matched["close"], mode="markers", name=label,
                                         marker={"size": 11, "color": color, "symbol": "diamond"},
                                         text=matched[value_col].map(lambda x: f"{label}: {x}"), hovertemplate="%{x|%Y-%m-%d}<br>%{text}<extra></extra>"))
        fig.update_layout(height=520, xaxis_rangeslider_visible=True, margin={"l": 10, "r": 10, "t": 20, "b": 10})
        st.plotly_chart(fig, width="stretch")
        left, right = st.columns(2)
        with left:
            st.markdown("#### 历史分红")
            st.dataframe(actions["dividends"], width="stretch", hide_index=True)
        with right:
            st.markdown("#### 历史转送/份额折算")
            st.dataframe(actions["splits"], width="stretch", hide_index=True)
    else:
        selected = st.multiselect("选择合约", symbols, default=symbols[:min(3, len(symbols))], max_selections=10)
        if not selected:
            st.info("请至少选择一个合约。")
            return
        cols = st.columns(min(4, len(selected)))
        raw = {symbol: cols[index % len(cols)].number_input(f"{symbol} 权重", min_value=0.0, value=1.0 / len(selected), step=0.05)
               for index, symbol in enumerate(selected)}
        histories = {symbol: market_history(root, symbol) for symbol in selected}
        basket = build_weighted_portfolio(histories, raw)
        if basket.empty:
            st.warning("所选合约没有共同交易区间。")
            return
        fig = go.Figure()
        plotted_basket = downsample_timeseries(basket, max_points=2500)
        for symbol in selected:
            if symbol in plotted_basket:
                fig.add_trace(go.Scatter(x=plotted_basket["date"], y=plotted_basket[symbol], name=symbol, line={"width": 1, "dash": "dot"}))
        fig.add_trace(go.Scatter(x=plotted_basket["date"], y=plotted_basket["portfolio"], name="模拟组合", line={"width": 3, "color": "#1f5aa6"}))
        fig.update_layout(height=500, yaxis_title="归一化净值", margin={"l": 10, "r": 10, "t": 20, "b": 10})
        fig.update_xaxes(rangeslider={"visible": True, "thickness": 0.06})
        st.plotly_chart(fig, width="stretch")
        dd = px.area(basket, x="date", y="drawdown", labels={"date": "日期", "drawdown": "组合回撤"})
        dd.update_layout(height=240, yaxis_tickformat=".1%", margin={"l": 10, "r": 10, "t": 15, "b": 10})
        st.plotly_chart(dd, width="stretch")
        st.markdown("#### 组合风险分析")
        risk_window = st.select_slider("风险估计窗口", options=[60, 120, 252, 504, 1000, "全部"], value=252)
        risk = portfolio_risk_analysis(histories, raw, None if risk_window == "全部" else int(risk_window))
        left, right = st.columns(2)
        with left:
            correlation = risk["correlation"]
            if not correlation.empty:
                heat = px.imshow(correlation, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r",
                                 labels={"color": "相关系数"})
                heat.update_layout(height=430, title="收益相关性矩阵")
                st.plotly_chart(heat, width="stretch")
        with right:
            contribution = risk["contribution"]
            if not contribution.empty:
                bars = px.bar(contribution, x="symbol", y="risk_contribution_pct", color="symbol",
                              labels={"symbol": "合约", "risk_contribution_pct": "风险贡献"}, title="年化波动风险贡献")
                bars.update_layout(height=430, yaxis_tickformat=".1%", showlegend=False)
                st.plotly_chart(bars, width="stretch")
                st.dataframe(contribution, width="stretch", hide_index=True,
                             column_config={"weight": st.column_config.NumberColumn(format="%.1%%"),
                                            "risk_contribution_pct": st.column_config.NumberColumn(format="%.1%%")})


# ---------------------------------------------------------------- 入口


def main() -> None:
    root_path = platform_root()
    root = str(root_path)
    render_header()
    with st.sidebar:
        page = st.radio("导航", ["概览", "市场数据", "回测分析", "回测对比", "策略配置"])
        if st.button("刷新数据", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Platform: {root}")
    if page == "概览":
        render_overview(cached_configs(root), cached_runs(root))
    elif page == "市场数据":
        render_market_data(root_path)
    elif page == "回测分析":
        render_runs(cached_runs(root))
    elif page == "回测对比":
        render_comparison(cached_runs(root))
    else:
        render_configs(cached_configs(root))


if __name__ == "__main__":
    main()
