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
    discover_configs,
    discover_runs,
    latest_positions,
    platform_root,
    read_run_tables,
)


st.set_page_config(page_title="Platform 回测看板", page_icon="📈", layout="wide")


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


def metric_text(value: Any, kind: str = "number") -> str:
    if value is None or pd.isna(value):
        return "—"
    if kind == "percent":
        return f"{float(value):.2%}"
    if kind == "integer":
        return f"{int(value):,}"
    return f"{float(value):.3f}"


def render_header() -> None:
    st.title("Platform 回测看板")
    st.caption("本地只读视图 · 数据来自 platform 配置与回测 artifact")


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
                "最大回撤": metric_text(run.metrics.get("max_drawdown"), "percent"),
                "Sharpe": metric_text(run.metrics.get("sharpe_ratio")),
                "交易数": metric_text(run.metrics.get("trade_count"), "integer"),
            }
        )
    frame = pd.DataFrame(rows)
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
    )


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
    second[1].metric("交易数", metric_text(metrics.get("trade_count"), "integer"))
    second[2].metric("订单数", metric_text(metrics.get("order_count"), "integer"))
    second[3].metric("拒单数", metric_text(metrics.get("rejected_order_count"), "integer"))
    second[4].metric("平均现金", metric_text(metrics.get("average_cash_weight"), "percent"))


def render_performance(nav: pd.DataFrame) -> None:
    if nav.empty or "net_value" not in nav:
        st.info("该运行没有可展示的净值数据。")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=nav["date"], y=nav["net_value"], name="净值", line={"width": 2}))
    fig.update_layout(height=390, margin={"l": 10, "r": 10, "t": 30, "b": 10}, yaxis_title="净值")
    st.plotly_chart(fig, width="stretch")
    if "drawdown" in nav:
        drawdown = px.area(nav, x="date", y="drawdown", labels={"date": "日期", "drawdown": "回撤"})
        drawdown.update_traces(line_color="#d9534f", fillcolor="rgba(217,83,79,0.25)")
        drawdown.update_layout(height=270, margin={"l": 10, "r": 10, "t": 20, "b": 10}, yaxis_tickformat=".1%")
        st.plotly_chart(drawdown, width="stretch")


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
        st.dataframe(
            latest_display,
            width="stretch",
            hide_index=True,
        )
    with right:
        if {"date", "asset_id", "weight"}.issubset(positions.columns):
            chart = px.area(positions, x="date", y="weight", color="asset_id", labels={"date": "日期", "weight": "权重"})
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
    manifest_path = run.path / "manifest.json"
    tables = cached_tables(str(run.path), manifest_path.stat().st_mtime)
    st.caption(str(run.path))
    render_run_metrics(run)
    performance, positions, execution, metadata = st.tabs(["收益与回撤", "持仓", "订单与交易", "运行信息"])
    with performance:
        render_performance(tables["nav"])
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


def main() -> None:
    root = str(platform_root())
    configs = cached_configs(root)
    runs = cached_runs(root)
    render_header()
    with st.sidebar:
        page = st.radio("导航", ["概览", "策略配置", "回测分析"])
        if st.button("刷新数据", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Platform: {root}")
    if page == "概览":
        render_overview(configs, runs)
    elif page == "策略配置":
        render_configs(configs)
    else:
        render_runs(runs)


if __name__ == "__main__":
    main()
