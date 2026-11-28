"""Read-only API and static site for the Platform dashboard."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Annotated, Literal

import pandas as pd
import plotly.graph_objects as go
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import FiniteFloat

from . import artifacts as data
from .charts import DOWN, UP, chart, compare_charts, decomposition, line, performance

app = FastAPI(title="Platform 策略看板")
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=4)
ROOT = data.platform_root()
DIST = ROOT / "dashboard_web" / "dist"
Kind = Literal["live", "sim"]
Period = Literal["全部", "近1月", "近3月", "近6月", "今年", "近1年", "近2年", "近3年"]
Mode = Literal["nav", "return"]


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def rows(frame: pd.DataFrame):
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=14))


def matrix(frame: pd.DataFrame):
    return {"labels": list(frame.columns), "values": json.loads(frame.to_json(orient="values", double_precision=14))}


def lookup(records, predicate, message):
    record = next((item for item in records if predicate(item)), None)
    if record is None:
        raise HTTPException(404, message)
    return record


def get_run(run_id, include_temporary):
    return lookup(data.discover_runs(ROOT, include_temporary), lambda item: item.run_id == run_id, "未找到该回测。")


def get_portfolio(kind, portfolio_id):
    return lookup(data.discover_portfolios(ROOT), lambda item: (item.kind, item.portfolio_id) == (kind, portfolio_id),
                  "未找到该组合。")


def portfolio_summary(record, nav):
    latest = None if nav.empty else nav.iloc[-1]
    returns = data.trailing_returns(nav)
    return {
        "id": record.portfolio_id,
        "kind": record.kind,
        "asOf": None if latest is None else latest["date"].date().isoformat(),
        "businessDaysBehind": None if latest is None else data.business_days_behind(latest["date"]),
        "totalValue": None if latest is None else number(latest["total_value"]),
        "returnSinceStart": returns["成立以来"],
        "returns": returns,
        "maxDrawdown": data.max_drawdown(nav),
        "pendingCount": len(record.state.get("pending_intents") or {}),
    }


def portfolio_rows():
    return [portfolio_summary(record, data.read_portfolio_nav(record.path, record.kind))
            for record in data.discover_portfolios(ROOT)]


def run_choice(run):
    return {"id": run.run_id, "date": run.generated_at[:10], "start": run.start_date, "end": run.end_date,
            "scenario": data.infer_slippage_scenario(run.run_id, run.metrics)}


@app.get("/api/health")
def health():
    return {"ready": (DIST / "index.html").is_file()}


@app.get("/api/overview")
def overview(include_temporary: bool = False):
    strategies = Counter(config.strategy_name for config in data.discover_configs(ROOT))
    official = data.discover_runs(ROOT)
    runs = data.discover_runs(ROOT, True) if include_temporary else official
    recent = []
    for run in runs[:5]:
        metrics = data.read_run_metrics(run.path)
        recent.append({
            **run_choice(run),
            "annualizedReturn": number(metrics.get("annualized_return")),
            "maxDrawdown": number(metrics.get("max_drawdown")),
        })
    return {
        "portfolios": portfolio_rows(),
        "configCount": strategies.total(),
        "strategyCount": len(strategies),
        "runCount": len(official),
        "strategies": [{"name": name, "count": count} for name, count in strategies.most_common(5)],
        "recentRuns": recent,
    }


@app.get("/api/portfolios")
def portfolio_choices(summary: bool = False):
    if summary:
        return portfolio_rows()
    return [{"kind": record.kind, "id": record.portfolio_id} for record in data.discover_portfolios(ROOT)]


@app.get("/api/portfolio")
def portfolio_detail(kind: Kind, id: Annotated[str, Query(min_length=1)]):
    record = get_portfolio(kind, id)
    nav = data.read_portfolio_nav(record.path, kind)
    summary = data.nav_summary_metrics(nav)
    windows = {}
    series = []
    if not nav.empty:
        drawdown = nav["net_value"] / nav["net_value"].cummax() - 1
        series = [
            {"date": day.date().isoformat(), "value": number(value), "drawdown": number(loss)}
            for day, value, loss in zip(nav["date"], nav["net_value"], drawdown)
        ]
        for period in ("近1月", "近3月", "近1年"):
            windows[period] = data.window_start_date(nav["date"].iloc[-1], period).date().isoformat()

    prices, dates = {}, {}
    for asset_id in record.state.get("positions") or {}:
        code = data.asset_code(asset_id)
        if code.isdigit():
            history = data.read_market_history(ROOT, code)
            if not history.empty:
                price = number(history["close"].iloc[-1])
                if price is not None:
                    prices[asset_id] = price
                    dates[asset_id] = history["trade_date"].iloc[-1].date().isoformat()
    positions = data.position_weights(record.state, prices)

    pending = record.state.get("pending_intents") or {}
    ticket = data.latest_ticket(record.path)
    targets = {asset_id: number(intent.get("target_weight") or 0) for asset_id, intent in pending.items()}
    target_source = "待执行意图"
    if not targets and ticket is not None and {"asset_id", "weight_target"} <= set(ticket["orders"]):
        targets = dict(zip(ticket["orders"]["asset_id"].astype(str), map(number, ticket["orders"]["weight_target"])))
        target_source = f"下单票 {ticket['date']}"
    weights = []
    if not positions.empty or targets:
        traces = [go.Bar(x=positions["code"].tolist(), y=[number(weight) for weight in positions["weight"]], name="当前")] if not positions.empty else []
        if targets:
            traces.append(go.Bar(x=[data.asset_code(asset_id) for asset_id in targets], y=list(targets.values()),
                                 name=f"目标 · {target_source}"))
        weights.append(chart("当前权重与目标权重", traces, barmode="group", percent=True, xaxis_type="category", height=240))

    return {
        **portfolio_summary(record, nav),
        "cash": number(record.state.get("cash")),
        "maxDrawdown": summary["max_drawdown"],
        "metrics": summary,
        "qualityNote": nav.attrs.get("quality_note"),
        "windows": windows,
        "series": series,
        "weights": weights,
        "pending": rows(pd.DataFrame(list(pending.values()))),
        "ticket": None if ticket is None else {
            "date": str(ticket["date"]), "text": ticket["text"], "orders": rows(ticket["orders"]),
        },
        "positions": [
            {"id": row.asset_id, "code": row.code, "quantity": number(row.quantity),
             "marketValue": number(row.market_value), "weight": number(row.weight), "priceDate": dates.get(row.asset_id)}
            for row in positions.itertuples(index=False)
        ],
    }


@app.get("/api/portfolio/activity")
def portfolio_activity(kind: Kind, id: str):
    record = get_portfolio(kind, id)
    if kind == "live":
        try:
            executions = data.read_live_executions(record.path)
        except (OSError, ValueError) as error:
            raise HTTPException(422, "无法读取实盘成交流水，请检查 execution_ledger.csv。") from error
        if "event" in executions:
            executions["event"] = executions["event"].replace({"BUY": "买入", "SELL": "卖出"})
        return [{"title": "实盘成交", "rows": rows(executions.rename(columns={
            "date": "成交日期", "code": "标的代码", "event": "方向", "quantity": "成交数量",
            "price": "成交价（元）", "gross_amount": "成交金额（元）", "fee": "费用（元）",
        }))}]
    return [{"title": title, "rows": rows(data.read_sim_run_table(record.path, name))}
            for title, name in (("建议订单", "suggested_orders"), ("模拟成交", "trades"))]


@app.get("/api/portfolio/analysis")
def portfolio_analysis(
    kind: Kind, id: str, section: Literal["performance", "returns"], period: Period = "全部",
    mode: Mode = "nav", log: bool = False, benchmark_run: str = "", benchmark_kind: Kind | None = None,
    benchmark_id: str = "", include_temporary: bool = False,
):
    record = get_portfolio(kind, id)
    nav = data.read_portfolio_nav(record.path, kind)
    if section == "returns":
        return {"charts": decomposition(nav)}
    benchmark, label = pd.DataFrame(), ""
    if benchmark_run:
        benchmark = data.read_run_table(get_run(benchmark_run, include_temporary).path, "nav")
        label = f"回测 · {benchmark_run}"
    elif benchmark_kind and benchmark_id:
        other = get_portfolio(benchmark_kind, benchmark_id)
        benchmark = data.read_portfolio_nav(other.path, other.kind)
        label = f"{'实盘' if other.kind == 'live' else '模拟'} · {benchmark_id}"
    figures, note = performance(nav, period, mode, benchmark, label, log)
    return {"charts": figures, "note": note}


@app.get("/api/configs")
def configs():
    return [{"id": config.relative_path, "name": config.run_name, "strategy": config.strategy_name}
            for config in data.discover_configs(ROOT)]


@app.get("/api/config")
def config_detail(id: str):
    item = lookup(data.discover_configs(ROOT), lambda config: config.relative_path == id, "未找到该配置。")
    columns = ("code", "name", "asset_type", "exchange", "lot_size")
    return {
        "assets": [{key: asset[key] for key in columns if key in asset} for asset in item.assets],
        "params": [{"参数": str(key), "值": str(value)} for key, value in item.params.items()],
        "yaml": yaml.safe_dump(item.payload, allow_unicode=True, sort_keys=False),
    }


@app.get("/api/runs")
def runs(query: str = "", include_temporary: bool = False):
    all_runs = data.discover_runs(ROOT, include_temporary)
    return [run_choice(item) for item in data.filter_runs(all_runs, query)]


NUMERIC_METRICS = (
    "total_return", "annualized_return", "annualized_volatility", "max_drawdown", "sharpe_ratio",
    "annualized_turnover", "annualized_fee_drag", "execution_slippage", "trade_count", "order_count",
    "rejected_order_count", "average_cash_weight",
)


def metrics_for(run, source):
    return {**{key: number(source.get(key)) for key in NUMERIC_METRICS},
            "slippage_scenario": data.infer_slippage_scenario(run.run_id, source)}


@app.get("/api/run")
def run_detail(id: str, include_temporary: bool = False):
    run = get_run(id, include_temporary)
    source = data.read_run_metrics(run.path)
    snapshot = run.path / "config_snapshot.yaml"
    training = source.get("training_metrics") or {}
    oos = source.get("oos_metrics") or {}
    split = None
    if source.get("training_metrics_available") and source.get("oos_metrics_available"):
        split = {"training": {key: number(training.get(key)) for key in NUMERIC_METRICS},
                 "oos": {key: number(oos.get(key)) for key in NUMERIC_METRICS}}
    return {
        **run_choice(run), "metrics": metrics_for(run, source), "split": split,
        "manifest": json.dumps(run.manifest, ensure_ascii=False, indent=2),
        "config": snapshot.read_text(encoding="utf-8") if snapshot.is_file() else None,
    }


def rebalance(run, asset):
    orders = data.read_run_table(run.path, "orders")
    events = data.rebalance_events(orders)
    assets = sorted(orders["asset_id"].dropna().astype(str).unique()) if "asset_id" in orders else []
    selected = asset if asset in assets else next(iter(assets), None)
    output = {"assets": assets, "asset": selected, "tables": [{"title": "调仓日期", "rows": rows(events)}]}
    if events.empty or not selected:
        return {**output, "note": "该回测暂无已成交调仓记录。"}
    symbol = data.asset_code(selected)
    history = data.read_market_history(ROOT, symbol) if symbol.isdigit() else pd.DataFrame()
    price = data.market_history_for_window(history, run.start_date, run.end_date)
    if price.empty:
        return {**output, "note": f"{symbol} 在回测区间内暂无本地行情。"}
    traces = [line(price["trade_date"], price["close"], "收盘价")]
    selected_orders = orders.loc[orders["asset_id"].astype(str) == selected]
    if {"side", "price"} <= set(selected_orders):
        for side, label, color, marker in (("BUY", "买入", UP, "triangle-up"), ("SELL", "卖出", DOWN, "triangle-down")):
            trades = selected_orders.loc[selected_orders["side"].astype(str).str.upper() == side]
            if not trades.empty:
                traces.append(go.Scatter(x=trades["date"], y=trades["price"], mode="markers", name=label,
                                        marker={"color": color, "symbol": marker, "size": 10}))
    return {**output, "charts": [chart("调仓与行情", traces, height=420, slider=True)]}


@app.get("/api/run/analysis")
def run_analysis(
    id: str, section: Literal["performance", "returns", "positions", "rebalance", "execution"],
    include_temporary: bool = False, period: Period = "全部", mode: Mode = "nav",
    benchmark_id: str = "", log: bool = False, asset: str = "",
):
    run = get_run(id, include_temporary)
    if section == "rebalance":
        return rebalance(run, asset)
    if section == "execution":
        tables = []
        for title, name in (("订单", "orders"), ("交易", "trades"), ("跳过与拒单", "skipped_orders")):
            frame = data.read_run_table(run.path, name)
            if "date" in frame:
                frame = frame.sort_values("date", ascending=False)
            tables.append({"title": title, "rows": rows(frame)})
        return {"tables": tables}
    if section == "positions":
        positions = data.read_run_table(run.path, "positions")
        figures = []
        if {"date", "asset_id", "weight"} <= set(positions) and not positions.empty:
            grouped = positions.pivot_table(index="date", columns="asset_id", values="weight", aggfunc="sum").fillna(0)
            grouped["现金"] = (1 - grouped.sum(axis=1)).clip(lower=0)
            figures.append(chart("历史持仓权重", [
                line(grouped.index, grouped[column], str(column), stackgroup="weights") for column in grouped
            ], percent=True))
        return {"charts": figures, "tables": [{"title": "最新持仓", "rows": rows(data.latest_positions(positions))}]}

    nav = data.read_run_table(run.path, "nav")
    if section == "returns":
        return {"charts": decomposition(nav)}
    benchmark = data.read_run_table(get_run(benchmark_id, include_temporary).path, "nav") if benchmark_id else pd.DataFrame()
    figures, note = performance(nav, period, mode, benchmark, benchmark_id, log)
    if not nav.empty and run.start_date and pd.to_datetime(run.start_date, errors="coerce") < nav["date"].min():
        trimmed = f"有效净值基准日 {nav['date'].min().date()}，已隐藏首次投资前的纯现金区间。"
        note = f"{trimmed} {note}" if note else trimmed
    return {"charts": figures, "note": note}


@app.get("/api/compare")
def compare(
    id: Annotated[list[str], Query(min_length=2, max_length=8)], include_temporary: bool = False,
    period: Period = "全部", mode: Mode = "nav", overlap: bool = True,
):
    available = {item.run_id: item for item in data.discover_runs(ROOT, include_temporary)}
    ids = list(dict.fromkeys(id))
    if len(ids) < 2 or any(key not in available for key in ids):
        raise HTTPException(422, "请选择至少两个可用的回测。")
    selected = [available[key] for key in ids]
    nav_map = {run.run_id: data.read_run_table(run.path, "nav") for run in selected}
    aligned = data.align_navs(nav_map, overlap_only=overlap)
    if not aligned.empty:
        start = data.window_start_date(aligned["date"].max(), period)
        if start is not None:
            aligned = data.align_navs(nav_map, overlap_only=overlap, start_date=start)
    start_end = None if aligned.empty else [aligned["date"].min().date().isoformat(), aligned["date"].max().date().isoformat()]
    source = [{"id": run.run_id, **metrics_for(run, data.read_run_metrics(run.path))} for run in selected]
    missing = [scenario for scenario in data.SLIPPAGE_SCENARIOS
               if all(item["slippage_scenario"] != scenario for item in source)]
    return {
        "series": {"performance": [], "yearly": [], "risk": []} if aligned.empty else compare_charts(aligned, mode == "return"),
        "window": start_end, "metrics": source, "missingScenarios": missing,
    }


@app.get("/api/market/symbols")
def market_symbols():
    return data.discover_market_symbols(ROOT)


@app.get("/api/market/history")
def market_history(symbol: Annotated[str, Query(pattern=r"^[0-9]+$")]):
    history = data.read_market_history(ROOT, symbol)
    actions = data.read_corporate_actions(ROOT, symbol)
    if not history.empty:
        for name, date_col in (("dividends", "ex_date"), ("splits", "split_date")):
            frame = actions[name]
            if date_col in frame:
                valid = frame.dropna(subset=[date_col]).sort_values(date_col)
                actions[name] = pd.merge_asof(valid, history[["trade_date", "close"]], left_on=date_col,
                                              right_on="trade_date", direction="nearest").drop(columns="trade_date")
    return {"prices": rows(history[[col for col in ("trade_date", "open", "high", "low", "close") if col in history]]),
            **{key: rows(value) for key, value in actions.items()}}


@app.get("/api/market/basket")
def market_basket(
    symbol: Annotated[list[str], Query(min_length=1, max_length=10)],
    weight: Annotated[list[FiniteFloat], Query(min_length=1, max_length=10)],
    window: Literal["0", "60", "120", "252", "504", "1000"] = "252",
):
    if len(symbol) != len(weight) or len(set(symbol)) != len(symbol) or any(
        not value.isascii() or not value.isdigit() for value in symbol
    ) or any(value < 0 for value in weight) or not math.isfinite(sum(weight)):
        raise HTTPException(422, "请检查合约和非负权重。")
    weights = dict(zip(symbol, weight))
    histories = {key: data.read_market_history(ROOT, key) for key in weights}
    missing = [key for key in weights if weights[key] > 0 and histories[key].empty]
    if missing:
        raise HTTPException(422, "缺少行情：" + "、".join(missing))
    basket = data.build_weighted_portfolio(histories, weights)
    if basket.empty:
        return {"charts": [], "contribution": [], "note": "所选合约没有共同交易区间，或权重均为零。"}
    plotted = data.downsample_timeseries(basket, max_points=2500)
    lines = [line(plotted["date"], plotted["portfolio"], "模拟组合", line_width=2.5)]
    lines.extend(line(plotted["date"], plotted[key], key, line_dash="dot") for key in symbol if key in plotted)
    figures = [
        chart("归一化净值", lines, height=410, slider=True),
        chart("组合回撤", [line(plotted["date"], plotted["drawdown"], "回撤", fill="tozeroy")], percent=True, height=250),
    ]
    risks = data.portfolio_risk_analysis(histories, weights, int(window) or None)
    correlation, contribution = risks["correlation"], risks["contribution"]
    if not correlation.empty:
        serialized = matrix(correlation)
        figures.append(chart("收益相关性矩阵", [go.Heatmap(
            x=serialized["labels"], y=serialized["labels"], z=serialized["values"],
            zmin=-1, zmax=1, texttemplate="%{z:.2f}", colorscale="RdBu_r",
        )], height=360, xaxis_type="category", yaxis_type="category"))
    if not contribution.empty:
        figures.append(chart("年化波动风险贡献", [
            go.Bar(x=contribution["symbol"], y=contribution["risk_contribution_pct"]),
        ], percent=True, xaxis_type="category", height=360))
    return {"charts": figures, "contribution": rows(contribution)}


@app.get("/", include_in_schema=False)
@app.get("/portfolios", include_in_schema=False)
@app.get("/portfolio", include_in_schema=False)
@app.get("/market", include_in_schema=False)
@app.get("/backtests", include_in_schema=False)
@app.get("/compare", include_in_schema=False)
@app.get("/configs", include_in_schema=False)
def index():
    path = DIST / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=503, detail="请先构建 dashboard_web，或使用 Vite 开发服务器。")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


app.mount("/assets", StaticFiles(directory=DIST / "assets", check_dir=False), name="assets")
