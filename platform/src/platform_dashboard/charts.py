"""Plotly figures shared by the read-only dashboard views."""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from .artifacts import downsample_timeseries, nav_analytics, rebase_benchmark, window_start_date

UP = "#c62828"
DOWN = "#167147"
COLORS = ["#212121", "#365c78", "#856b38", "#6e5484", "#43736a", "#93545c", "#60708c", "#555555"]
RETURNS = [[0, DOWN], [0.5, "#f9f9f9"], [1, UP]]


def chart(title, traces, *, height=320, percent=False, slider=False, **layout):
    fig = go.Figure(traces)
    fig.update_layout(
        template="none", height=height, colorway=COLORS, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font={"color": "#5d5d5d", "size": 11},
        margin={"l": 52, "r": 22, "t": 16, "b": 40}, hovermode="closest",
        legend={"orientation": "h", "y": -0.22}, **layout,
    )
    fig.update_xaxes(gridcolor="#ededed", automargin=True, rangeslider_visible=slider)
    fig.update_yaxes(gridcolor="#ededed", zerolinecolor="#dfdfdf", automargin=True,
                     tickformat=".1%" if percent else None)
    return {"title": title, **json.loads(pio.to_json(fig))}


def line(x, y, name, **kwargs):
    return go.Scatter(x=x, y=y, name=name, mode="lines", **kwargs)


def window_nav(nav, period):
    if nav.empty or not {"date", "net_value"} <= set(nav.columns):
        return pd.DataFrame()
    start = window_start_date(nav["date"].max(), period)
    return nav if start is None else nav.loc[nav["date"] >= start]


def performance(nav, period, mode, benchmark, benchmark_label, log_scale):
    window = window_nav(nav, period)
    if len(window) < 2:
        return [], "所选区间内的净值数据不足两天。"
    base = float(window["net_value"].iloc[0])
    if not base:
        return [], "区间首日净值为 0。"
    as_return = mode == "return"
    label = "区间收益" if as_return else "净值"

    def display(values):
        return values / base - 1 if as_return else values

    traces = [line(window["date"], display(window["net_value"]), label)]
    comparison = rebase_benchmark(window, benchmark) if not benchmark.empty else pd.DataFrame()
    if not comparison.empty:
        traces.append(line(comparison["date"], display(comparison["net_value"]), benchmark_label,
                           line={"dash": "dash", "color": "#767676"}))
    result = [chart(label, traces, height=420, percent=as_return, slider=True,
                    yaxis_type="log" if log_scale and not as_return else "linear")]
    if not comparison.empty:
        merged = window.merge(comparison.rename(columns={"net_value": "benchmark"}), on="date")
        result.append(chart("相对基准超额", [line(merged["date"], merged["net_value"] / merged["benchmark"] - 1,
                                               "超额收益")], height=240, percent=True))
    values = window["net_value"]
    result.append(chart("区间回撤", [line(window["date"], values / values.cummax() - 1,
                                           "回撤", fill="tozeroy")], height=250, percent=True))
    return result, ("与所选基准在该区间内无可比净值。" if benchmark_label and comparison.empty else None)


def decomposition(nav):
    data = nav_analytics(nav)
    months = data["monthly_pivot"]
    if months.empty:
        return []
    result = [chart("月度收益热力图", [go.Heatmap(
        x=[f"{month}月" for month in range(1, 13)], y=[str(year) for year in months.index],
        z=months.to_numpy(), texttemplate="%{z:.1%}", colorscale=RETURNS, zmid=0,
        colorbar={"tickformat": ".0%"}, hovertemplate="%{y}年%{x} · %{z:.2%}<extra></extra>",
    )], height=max(190, 80 + 36 * len(months)), yaxis={"type": "category", "autorange": "reversed"})]

    for key, x, title in (("yearly", "year", "年度收益"), ("monthly", "date", "月度收益序列")):
        frame = data[key]
        if not frame.empty:
            result.append(chart(title, [go.Bar(x=frame[x], y=frame["ret"], name=title,
                                               marker_color=[UP if value >= 0 else DOWN for value in frame["ret"]])],
                                percent=True, height=270, xaxis_type="category" if key == "yearly" else "date"))
    if not data["daily"].empty:
        result.insert(2, chart("日收益分布", [go.Histogram(x=data["daily"]["ret"], nbinsx=60)],
                               xaxis_tickformat=".1%", yaxis_title="天数", height=270))
    rolling = data["rolling"]
    for key, label, percent in (("vol_60d", "滚动 60 日年化波动", True),
                                ("sharpe_252d", "滚动 252 日 Sharpe", False)):
        if key in rolling:
            result.append(chart(label, [line(rolling["date"], rolling[key], label)], percent=percent, height=270))
    return result


def compare_charts(aligned, as_return):
    nav, drawdown, yearly, rolling = [], [], [], []
    for index, (run, group) in enumerate(aligned.groupby("run_id", sort=False)):
        color = COLORS[index]
        plotted = downsample_timeseries(group, max_points=1500)
        nav.append(line(plotted["date"], plotted["net_value"] - int(as_return), run, line_color=color))
        drawdown.append(line(plotted["date"], plotted["drawdown"], run, line_color=color))
        analytics = nav_analytics(group)
        year, risk = analytics["yearly"], analytics["rolling"]
        if not year.empty:
            yearly.append(go.Bar(x=year["year"], y=year["ret"], name=run, marker_color=color))
        if "vol_60d" in risk:
            rolling.append(line(risk["date"], risk["vol_60d"], run, line_color=color))
    return {
        "performance": [
            chart("区间收益" if as_return else "归一净值", nav, percent=as_return, height=430, slider=True),
            chart("区间回撤", drawdown, height=300, percent=True),
        ],
        "yearly": [chart("年度收益", yearly, percent=True, barmode="group", xaxis_type="category")] if yearly else [],
        "risk": [chart("滚动 60 日年化波动", rolling, percent=True)] if rolling else [],
    }
