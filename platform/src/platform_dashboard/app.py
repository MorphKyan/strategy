from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.platform_dashboard.artifacts import (
    ConfigRecord,
    PortfolioRecord,
    RunRecord,
    align_navs,
    asset_code,
    build_weighted_portfolio,
    business_days_behind,
    discover_configs,
    discover_market_symbols,
    discover_portfolios,
    discover_runs,
    downsample_timeseries,
    filter_runs,
    infer_slippage_scenario,
    latest_positions,
    latest_ticket,
    list_tickets,
    market_history_for_window,
    max_drawdown,
    nav_analytics,
    nav_summary_metrics,
    platform_root,
    position_weights,
    read_portfolio_nav,
    read_run_metrics,
    read_sim_run_table,
    read_ticket_orders,
    read_run_table,
    read_corporate_actions,
    read_market_history,
    rebalance_events,
    portfolio_risk_analysis,
    SLIPPAGE_SCENARIOS,
    TRAILING_RETURN_PERIODS,
    rebase_benchmark,
    trailing_returns,
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
def cached_runs(root: str, include_temporary: bool = False) -> list[RunRecord]:
    return discover_runs(Path(root), include_temporary=include_temporary)


@st.cache_data(show_spinner=False, max_entries=128, ttl=600)
def cached_table(run_dir: str, name: str, modified_at: float) -> pd.DataFrame:
    del modified_at
    return read_run_table(Path(run_dir), name)


def run_table(run: RunRecord, name: str) -> pd.DataFrame:
    path = run.path / f"{name}.csv"
    modified_at = path.stat().st_mtime if path.exists() else 0.0
    if name == "nav":
        trades = run.path / "trades.csv"
        modified_at = max(modified_at, trades.stat().st_mtime if trades.exists() else 0.0)
    return cached_table(str(run.path), name, modified_at)


@st.cache_data(show_spinner=False, max_entries=128, ttl=600)
def cached_metrics(run_dir: str, modified_at: float) -> dict[str, Any]:
    del modified_at
    return read_run_metrics(Path(run_dir))


def run_metrics(run: RunRecord) -> dict[str, Any]:
    manifest = run.path / "manifest.json"
    metrics = run.path / "metrics.json"
    artifact_paths = [run.path / f"{name}.csv" for name in ("nav", "trades", "orders", "skipped_orders", "positions")]
    modified_at = max(
        manifest.stat().st_mtime,
        metrics.stat().st_mtime if metrics.exists() else 0.0,
        *(path.stat().st_mtime if path.exists() else 0.0 for path in artifact_paths),
    )
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


@st.cache_data(show_spinner=False, ttl=30)
def cached_portfolios(root: str) -> list[PortfolioRecord]:
    return discover_portfolios(Path(root))


@st.cache_data(show_spinner=False, max_entries=64, ttl=600)
def cached_portfolio_nav(portfolio_dir: str, kind: str, signature: tuple) -> pd.DataFrame:
    del signature
    return read_portfolio_nav(Path(portfolio_dir), kind)


def portfolio_nav(record: PortfolioRecord) -> pd.DataFrame:
    if record.kind == "live":
        paths = [record.path / "real_nav.csv"]
    else:
        paths = sorted(record.path.glob("runs/*/nav.csv"))
    signature = tuple((str(path), path.stat().st_mtime) for path in paths if path.exists())
    return cached_portfolio_nav(str(record.path), record.kind, signature)


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
        metrics = run_metrics(run)
        rows.append(
            {
                "run_id": run.run_id,
                "区间": f"{metrics.get('start_date', '—')} → {metrics.get('end_date', '—')}",
                "累计收益": metric_text(metrics.get("total_return"), "percent"),
                "年化收益": metric_text(metrics.get("annualized_return"), "percent"),
                "年化波动": metric_text(metrics.get("annualized_volatility"), "percent"),
                "最大回撤": metric_text(metrics.get("max_drawdown"), "percent"),
                "Sharpe": metric_text(metrics.get("sharpe_ratio")),
                "滑点场景": metric_text(metrics.get("slippage_scenario"), "text"),
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


def render_performance(nav: pd.DataFrame, benchmarks: dict[str, Callable[[], pd.DataFrame]] | None = None) -> None:
    """净值与回撤视图。benchmarks 为 {标签: 惰性净值加载器}，回测/组合详情页共用
    （基准净值经 rebase_benchmark 缩放到候选坐标系，规模不同的组合可直接对比）。"""
    if nav.empty or "net_value" not in nav:
        st.info("没有可展示的净值数据。")
        return
    benchmarks = benchmarks or {}

    controls = st.columns([1.1, 3.2, 1.6, 0.7])
    with controls[0]:
        mode = st.radio("显示", ["净值", "收益率"], horizontal=True)
    with controls[1]:
        period = st.radio("区间", PERFORMANCE_PERIODS, index=len(PERFORMANCE_PERIODS) - 1, horizontal=True)
    with controls[2]:
        benchmark_id = st.selectbox("基准对比", ["无", *benchmarks])
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
        benchmark_window = rebase_benchmark(window, benchmarks[benchmark_id]())
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
    price = market_history_for_window(history, run.start_date, run.end_date)
    if price.empty:
        st.warning("当前回测区间内没有可展示行情。")
        return
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
    if "backtest_run_query" not in st.session_state:
        st.session_state["backtest_run_query"] = ""
    if "backtest_run_query_draft" not in st.session_state:
        st.session_state["backtest_run_query_draft"] = st.session_state["backtest_run_query"]
    with st.form("backtest_run_search_form", border=False):
        search_col, button_col, clear_col = st.columns([6, 1, 1])
        with search_col:
            st.text_input(
                "搜索回测",
                placeholder="输入运行名、策略、日期或滑点场景；可用空格分隔多个关键词",
                key="backtest_run_query_draft",
            )
        with button_col:
            st.write("")
            st.form_submit_button(
                "搜索",
                width="stretch",
                on_click=lambda: st.session_state.update(
                    backtest_run_query=st.session_state.get("backtest_run_query_draft", "").strip()
                ),
            )
        with clear_col:
            st.write("")
            st.form_submit_button(
                "清除",
                width="stretch",
                on_click=lambda: st.session_state.update(
                    backtest_run_query="", backtest_run_query_draft=""
                ),
            )

    choices = filter_runs(runs, st.session_state["backtest_run_query"])
    if not choices:
        st.info("没有匹配的回测，请调整关键词或清除搜索条件。")
        return
    if st.session_state["backtest_run_query"]:
        st.caption(f"找到 {len(choices)} 个回测（共 {len(runs)} 个）")
    choice_by_id = {item.run_id: item for item in choices}
    selected_id = st.selectbox(
        "选择回测",
        list(choice_by_id),
        format_func=lambda run_id: (
            f"{run_id} · {choice_by_id[run_id].start_date} → {choice_by_id[run_id].end_date}"
        ),
    )
    run = choice_by_id[selected_id]
    st.caption(str(run.path))
    render_run_metrics(run)
    sections = ["净值与回撤", "收益分解", "持仓", "调仓与行情", "订单与交易", "运行信息"]
    section = st.segmented_control("分析视图", sections, default=sections[0], label_visibility="collapsed")
    if section == "净值与回撤":
        nav = run_table(run, "nav")
        if not nav.empty and run.start_date and pd.Timestamp(run.start_date) < nav["date"].min():
            st.caption(
                f"已隐藏首次投资前的纯现金区间：原始日历起点 {run.start_date}，"
                f"有效净值基准日 {nav['date'].min().date()}。"
            )
        benchmarks = {
            item.run_id: (lambda item=item: run_table(item, "nav"))
            for item in runs
            if item.run_id != run.run_id
        }
        render_performance(nav, benchmarks)
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


# ---------------------------------------------------------------- 组合（蓝图 B3/B4）

STALE_BUSINESS_DAYS = 3  # 净值落后 >=3 个工作日标黄：发现"定时任务挂了"的最廉价手段


def render_portfolio_overview(portfolios: list[PortfolioRecord]) -> None:
    st.subheader("组合总览")
    if not portfolios:
        st.info("尚未发现模拟/实盘组合（results/sim_portfolios、results/live_portfolios）。")
        return
    rows: list[dict[str, Any]] = []
    stale_flags: list[bool] = []
    for record in portfolios:
        nav = portfolio_nav(record)
        returns = trailing_returns(nav)
        if nav.empty:
            last_label, stale = "无净值", True
        else:
            last_date = nav["date"].iloc[-1]
            behind = business_days_behind(last_date)
            stale = behind >= STALE_BUSINESS_DAYS
            last_label = str(last_date.date()) + (f"（滞后 {behind} 个工作日）" if stale else "")
        rows.append(
            {
                "组合": record.portfolio_id,
                "类型": record.kind,
                "最新净值日期": last_label,
                "总值": f"{nav['net_value'].iloc[-1]:,.0f}" if not nav.empty else "—",
                **{period: metric_text(returns.get(period), "percent") for period in TRAILING_RETURN_PERIODS},
                "成立以来": metric_text(returns.get("成立以来"), "percent"),
                "最大回撤": metric_text(max_drawdown(nav), "percent"),
                "待执行意图": len(record.state.get("pending_intents") or {}),
            }
        )
        stale_flags.append(stale)
    frame = pd.DataFrame(rows)
    styled = frame.style.apply(
        lambda row: ["background-color: rgba(255, 193, 7, 0.3)" if stale_flags[row.name] else "" for _ in row],
        axis=1,
    )
    st.dataframe(styled, width="stretch", hide_index=True)
    st.caption(
        f"近 N 期收益 = 净值两点回看（区间口径与回测分析页一致），历史不足该区间时显示 —。"
        f"黄色行 = 净值落后当前日期 {STALE_BUSINESS_DAYS} 个工作日以上（未剔除节假日，长假会误报），"
        "请检查每日任务计划是否正常运行。sim 组合总值为模型口径，与真实账户金额无关。"
    )


def render_portfolio_detail(portfolios: list[PortfolioRecord], runs: list[RunRecord], root: Path) -> None:
    st.subheader("组合详情")
    if not portfolios:
        st.info("尚未发现模拟/实盘组合（results/sim_portfolios、results/live_portfolios）。")
        return
    options = {f"{record.kind} · {record.portfolio_id}": record for record in portfolios}
    record = options[st.selectbox("选择组合", list(options))]
    st.caption(str(record.path))

    nav = portfolio_nav(record)
    state = record.state
    pending = state.get("pending_intents") or {}
    returns = trailing_returns(nav)

    cols = st.columns(5)
    cols[0].metric("最新总值", f"{nav['net_value'].iloc[-1]:,.0f}" if not nav.empty else "—")
    cols[1].metric("现金", f"{float(state.get('cash') or 0):,.0f}")
    if nav.empty:
        cols[2].metric("最新净值日期", "—")
    else:
        behind = business_days_behind(nav["date"].iloc[-1])
        cols[2].metric(
            "最新净值日期",
            str(nav["date"].iloc[-1].date()),
            delta=f"-滞后 {behind} 个工作日" if behind >= STALE_BUSINESS_DAYS else None,
        )
    cols[3].metric("待执行意图", len(pending))
    cols[4].metric("成立以来", metric_text(returns.get("成立以来"), "percent"))

    # nav 派生指标行（复用回测口径；样本太短时年化类显示 —，见 nav_summary_metrics）
    summary = nav_summary_metrics(nav)
    second = st.columns(5)
    second[0].metric("年化收益", metric_text(summary.get("annualized_return"), "percent"))
    second[1].metric("年化波动", metric_text(summary.get("annualized_volatility"), "percent"))
    second[2].metric("Sharpe", metric_text(summary.get("sharpe_ratio")))
    second[3].metric("最大回撤", metric_text(summary.get("max_drawdown"), "percent"))
    second[4].metric("当前回撤", metric_text(summary.get("current_drawdown"), "percent"))
    if 0 < summary["observations"] < 20:
        st.caption(f"净值观测仅 {summary['observations']} 天，年化类指标暂不计算（样本不足，随净值累积自动出现）。")

    sections = ["概览", "净值与回撤", "收益分解", "票据与交易"]
    section = st.segmented_control("组合视图", sections, default=sections[0], label_visibility="collapsed")

    if section == "概览":
        _render_portfolio_snapshot(record, state, pending, root)
    elif section == "净值与回撤":
        # 基准可选其他组合（影子 sim 等）或任意回测 run —— 实盘 vs 回测预期一图看清
        benchmarks: dict[str, Callable[[], pd.DataFrame]] = {
            f"{item.kind} · {item.portfolio_id}": (lambda item=item: portfolio_nav(item))
            for item in portfolios
            if item.portfolio_id != record.portfolio_id
        }
        for run in runs:
            benchmarks[f"回测 · {run.run_id}"] = lambda run=run: run_table(run, "nav")
        render_performance(nav, benchmarks)
    elif section == "收益分解":
        render_return_decomposition(nav)
    else:
        _render_portfolio_activity(record)


def _render_portfolio_snapshot(record: PortfolioRecord, state: dict[str, Any], pending: dict[str, Any], root: Path) -> None:
    """概览节：当前权重 vs 目标权重、待执行意图、最新下单票。"""
    st.markdown("#### 当前权重 vs 目标权重")
    prices: dict[str, float] = {}
    for asset_id in (state.get("positions") or {}):
        code = asset_code(asset_id)
        if not code.isdigit():  # 演示/测试组合可能用非行情代码，缺价资产权重显示为空
            continue
        history = market_history(root, code)
        if not history.empty:
            prices[asset_id] = float(history["close"].iloc[-1])
    weights = position_weights(state, prices)
    ticket = latest_ticket(record.path)
    targets: dict[str, float] = {
        asset_id: float(intent.get("target_weight") or 0) for asset_id, intent in pending.items()
    }
    target_source = "待执行意图"
    if not targets and ticket is not None and not ticket["orders"].empty and "weight_target" in ticket["orders"]:
        targets = {
            str(row["asset_id"]): float(row["weight_target"])
            for _, row in ticket["orders"].iterrows()
        }
        target_source = f"下单票 {ticket['date']}"
    if weights.empty:
        st.info("状态中没有持仓。")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=weights["code"], y=weights["weight"], name="当前", marker_color="#4a6fa5"))
        if targets:
            fig.add_trace(
                go.Bar(
                    x=[asset_code(asset_id) for asset_id in targets],
                    y=list(targets.values()),
                    name=f"目标 · {target_source}",
                    marker_color="#e08e0b",
                )
            )
        fig.update_layout(barmode="group", height=340, yaxis_tickformat=".1%",
                          margin={"l": 10, "r": 10, "t": 20, "b": 10}, legend={"orientation": "h"})
        fig.update_xaxes(type="category")  # 代码是数字串，防被当成连续数值轴
        st.plotly_chart(fig, width="stretch")
        if not targets:
            st.caption("目标权重带仅在有待执行意图或下单票明细时显示（下单票只含需交易的资产）。")

    if pending:
        st.markdown("#### 待执行意图")
        st.dataframe(pd.DataFrame(list(pending.values())), width="stretch", hide_index=True)

    if ticket is not None:
        st.markdown(f"#### 最新下单票（{ticket['date']}）")
        st.code(ticket["text"], language=None)
        if not ticket["orders"].empty:
            st.dataframe(ticket["orders"], width="stretch", hide_index=True)


def _render_portfolio_activity(record: PortfolioRecord) -> None:
    """票据与交易节：live 组合列历史下单票，sim 组合列建议订单与模拟成交。"""
    if record.kind == "live":
        st.markdown("#### 下单票历史")
        tickets_frame = list_tickets(record.path)
        if tickets_frame.empty:
            st.caption("暂无下单票。")
        else:
            shown = tickets_frame.rename(
                columns={"date": "日期", "kind": "类型", "summary": "摘要", "has_detail": "有明细"}
            )
            st.dataframe(shown, width="stretch", hide_index=True)
        orders = read_ticket_orders(record.path)
        if not orders.empty:
            st.markdown("#### 调仓明细（全部票据）")
            st.dataframe(orders, width="stretch", hide_index=True)
    else:
        for title, name in (("建议订单", "suggested_orders"), ("模拟成交", "trades")):
            st.markdown(f"#### {title}")
            frame = read_sim_run_table(record.path, name)
            if frame.empty:
                st.caption("无记录")
            else:
                st.dataframe(frame, width="stretch", hide_index=True)


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
        page = st.radio("导航", ["概览", "组合总览", "组合详情", "市场数据", "回测分析", "回测对比", "策略配置"])
        include_temporary = st.checkbox(
            "加载临时回测",
            value=False,
            help="同时加载研究、训练集、测试集、敏感性和其他临时回测。",
        )
        if st.button("刷新数据", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Platform: {root}")
    if page == "概览":
        render_overview(cached_configs(root), cached_runs(root, include_temporary))
    elif page == "组合总览":
        render_portfolio_overview(cached_portfolios(root))
    elif page == "组合详情":
        render_portfolio_detail(cached_portfolios(root), cached_runs(root, include_temporary), root_path)
    elif page == "市场数据":
        render_market_data(root_path)
    elif page == "回测分析":
        render_runs(cached_runs(root, include_temporary))
    elif page == "回测对比":
        render_comparison(cached_runs(root, include_temporary))
    else:
        render_configs(cached_configs(root))


if __name__ == "__main__":
    main()
