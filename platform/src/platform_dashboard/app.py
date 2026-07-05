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
    discover_configs,
    discover_runs,
    latest_positions,
    nav_analytics,
    platform_root,
    read_run_tables,
    rebase_benchmark,
    window_start_date,
)


st.set_page_config(page_title="Platform 回测看板", page_icon="📈", layout="wide")

# A 股配色习惯：红涨绿跌
UP_COLOR = "#c62828"
DOWN_COLOR = "#1b8a3a"
RETURN_COLORSCALE = [[0.0, "#1b8a3a"], [0.5, "#f7f7f7"], [1.0, "#c62828"]]
MONTH_LABELS = [f"{month}月" for month in range(1, 13)]

RANGE_BUTTONS = [
    {"count": 1, "label": "1月", "step": "month", "stepmode": "backward"},
    {"count": 3, "label": "3月", "step": "month", "stepmode": "backward"},
    {"count": 6, "label": "6月", "step": "month", "stepmode": "backward"},
    {"count": 1, "label": "今年", "step": "year", "stepmode": "todate"},
    {"count": 1, "label": "1年", "step": "year", "stepmode": "backward"},
    {"count": 3, "label": "3年", "step": "year", "stepmode": "backward"},
    {"step": "all", "label": "全部"},
]


@st.cache_data(show_spinner=False)
def cached_configs(root: str) -> list[ConfigRecord]:
    return discover_configs(Path(root))


@st.cache_data(show_spinner=False)
def cached_runs(root: str) -> list[RunRecord]:
    return discover_runs(Path(root))


@st.cache_data(show_spinner=False)
def cached_tables(run_dir: str, modified_at: float) -> dict[str, pd.DataFrame]:
    del modified_at
    return read_run_tables(Path(run_dir))


def run_tables(run: RunRecord) -> dict[str, pd.DataFrame]:
    manifest_path = run.path / "manifest.json"
    return cached_tables(str(run.path), manifest_path.stat().st_mtime)


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


def apply_time_axis(fig: go.Figure, rangeslider: bool = True) -> None:
    fig.update_xaxes(
        rangeselector={"buttons": RANGE_BUTTONS},
        rangeslider={"visible": rangeslider, "thickness": 0.06},
    )


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
    metrics = run.metrics
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
        benchmark_window = rebase_benchmark(window, run_tables(benchmark_run)["nav"])
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
    tables = run_tables(run)
    st.caption(str(run.path))
    render_run_metrics(run)
    performance, decomposition, positions, execution, metadata = st.tabs(
        ["净值与回撤", "收益分解", "持仓", "订单与交易", "运行信息"]
    )
    with performance:
        render_performance(tables["nav"], run, runs)
    with decomposition:
        render_return_decomposition(tables["nav"])
    with positions:
        render_positions(tables["positions"])
    with execution:
        render_execution(tables)
    with metadata:
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
    selected_ids = st.multiselect(
        "选择 2–5 个回测",
        [item.run_id for item in runs],
        default=[item.run_id for item in runs[:2]],
        max_selections=5,
    )
    if len(selected_ids) < 2:
        st.caption("请至少选择两个回测。")
        return
    overlap_only = st.checkbox("仅对比共同重叠区间（各自归一到区间首日）", value=True)

    selected_runs = [item for item in runs if item.run_id in selected_ids]
    nav_map = {item.run_id: run_tables(item)["nav"] for item in selected_runs}
    aligned = align_navs(nav_map, overlap_only=overlap_only)
    if aligned.empty:
        st.warning("所选回测没有可对齐的净值数据。")
        return

    fig = go.Figure()
    for run_id, group in aligned.groupby("run_id"):
        fig.add_trace(go.Scatter(x=group["date"], y=group["net_value"], name=run_id, line={"width": 1.8}))
    apply_time_axis(fig)
    fig.update_layout(
        height=460,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        yaxis_title="归一净值",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    st.plotly_chart(fig, width="stretch")

    drawdown = go.Figure()
    for run_id, group in aligned.groupby("run_id"):
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
        table[run.run_id] = [metric_text(run.metrics.get(key), kind) for key, _, kind in COMPARE_METRICS]
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)


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
        params = pd.DataFrame(
            [{"参数": key, "值": value if not isinstance(value, (dict, list)) else str(value)} for key, value in record.params.items()]
        )
        st.dataframe(params, width="stretch", hide_index=True)

    with st.expander("查看完整 YAML"):
        st.code(yaml.safe_dump(record.payload, allow_unicode=True, sort_keys=False), language="yaml")


# ---------------------------------------------------------------- 入口


def main() -> None:
    root = str(platform_root())
    configs = cached_configs(root)
    runs = cached_runs(root)
    render_header()
    with st.sidebar:
        page = st.radio("导航", ["概览", "回测分析", "回测对比", "策略配置"])
        if st.button("刷新数据", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Platform: {root}")
    if page == "概览":
        render_overview(configs, runs)
    elif page == "回测分析":
        render_runs(runs)
    elif page == "回测对比":
        render_comparison(runs)
    else:
        render_configs(configs)


if __name__ == "__main__":
    main()
