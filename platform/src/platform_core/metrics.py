from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

TRAINING_END_DATE = "2025-06-30"
OOS_START_DATE = "2025-07-01"
MIN_SAMPLE_OBSERVATIONS = 2


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def read_csv_or_empty(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _filter_by_date(frame: pd.DataFrame, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    if frame.empty or "date" not in frame.columns:
        return frame.copy()
    out = frame.copy()
    dates = pd.to_datetime(out["date"], errors="coerce")
    mask = dates.notna()
    if start_date is not None:
        mask &= dates >= pd.Timestamp(start_date)
    if end_date is not None:
        mask &= dates <= pd.Timestamp(end_date)
    return out.loc[mask].copy()


def _empty_metrics(
    trades: pd.DataFrame,
    orders: pd.DataFrame,
    skipped_orders: pd.DataFrame,
) -> dict[str, Any]:
    skipped_reason_counts = (
        skipped_orders.get("reason", pd.Series(dtype=str)).fillna("unknown").value_counts().to_dict()
        if not skipped_orders.empty
        else {}
    )
    return {
        "start_date": None,
        "end_date": None,
        "observations": 0,
        "total_return": None,
        "annualized_return": None,
        "annualized_volatility": None,
        "max_drawdown": None,
        "sharpe_ratio": None,
        "turnover_total": 0.0,
        "annualized_turnover": 0.0,
        "turnover_amount_total": 0.0,
        "turnover_amount_ratio": 0.0,
        "annualized_turnover_amount": 0.0,
        "turnover_quantity_total": 0.0,
        "annualized_turnover_quantity": 0.0,
        "trade_count": int(len(trades)),
        "order_count": int(len(orders)),
        "skipped_order_count": int(len(skipped_orders)),
        "skipped_below_lot_or_cash_count": int(skipped_reason_counts.get("below_lot_or_cash", 0)),
        "filled_order_count": 0,
        "rejected_order_count": 0,
        "skipped_reason_counts": {str(key): int(value) for key, value in skipped_reason_counts.items()},
        "pending_intent_count": 0,
        "max_pending_intent_count": 0,
        "average_cash_weight": None,
        "max_position_count": 0,
        "execution_slippage": 0.0,
        "fee_total": 0.0,
        "fee_drag_ratio": 0.0,
        "annualized_fee_drag": 0.0,
    }


def _compute_period_metrics(
    nav: pd.DataFrame,
    trades: pd.DataFrame,
    orders: pd.DataFrame,
    skipped_orders: pd.DataFrame,
    positions: pd.DataFrame,
) -> dict[str, Any]:
    if nav.empty or "net_value" not in nav.columns:
        return _empty_metrics(trades, orders, skipped_orders)

    nav = nav.copy()
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date"]).sort_values("date")
    net_value = pd.to_numeric(nav["net_value"], errors="coerce").dropna()
    if net_value.empty:
        return _empty_metrics(trades, orders, skipped_orders)

    daily_returns = net_value.pct_change().dropna()
    days = len(net_value)
    years = days / 252 if days else 0
    total_return = net_value.iloc[-1] / net_value.iloc[0] - 1 if days and net_value.iloc[0] else None
    annualized_return = (
        (net_value.iloc[-1] / net_value.iloc[0]) ** (252 / max(len(net_value), 1)) - 1
        if len(net_value) > 0 and net_value.iloc[0]
        else 0.0
    )
    annualized_volatility = daily_returns.std() * math.sqrt(252) if len(daily_returns) > 1 else 0.0
    rolling_peak = net_value.cummax()
    drawdown = net_value / rolling_peak - 1
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility else 0.0

    average_total_value = None
    if "total_value" in nav.columns:
        total_value_series = pd.to_numeric(nav["total_value"], errors="coerce").dropna()
        if not total_value_series.empty:
            average_total_value = safe_float(total_value_series.mean())

    turnover_amount_total = (
        pd.to_numeric(trades.get("trade_value", pd.Series(dtype=float)), errors="coerce").abs().sum()
        if not trades.empty
        else 0.0
    )
    turnover_quantity_total = (
        pd.to_numeric(trades.get("quantity", pd.Series(dtype=float)), errors="coerce").abs().sum()
        if not trades.empty
        else 0.0
    )
    turnover_amount_ratio = (
        turnover_amount_total / (2 * average_total_value)
        if average_total_value and average_total_value > 0
        else 0.0
    )
    annualized_turnover_amount = turnover_amount_ratio / years if years else turnover_amount_ratio
    annualized_turnover_quantity = (turnover_quantity_total / 2) / years if years else (turnover_quantity_total / 2)

    status_counts = {}
    rejection_reason_counts = {}
    if not orders.empty:
        status_counts = orders.get("status", pd.Series(dtype=str)).fillna("").value_counts().to_dict()
        rejected = orders[orders["status"] == "REJECTED"] if "status" in orders.columns else pd.DataFrame()
        if not rejected.empty:
            rejection_reason_counts = rejected.get("reason", pd.Series(dtype=str)).fillna("unknown").value_counts().to_dict()
    skipped_reason_counts = {}
    if not skipped_orders.empty:
        skipped_reason_counts = skipped_orders.get("reason", pd.Series(dtype=str)).fillna("unknown").value_counts().to_dict()

    pending_series = pd.to_numeric(nav.get("pending_intent_count", pd.Series(dtype=float)), errors="coerce").fillna(0)
    average_cash_weight = None
    if "cash" in nav.columns and "total_value" in nav.columns:
        total_value = pd.to_numeric(nav["total_value"], errors="coerce").replace(0, pd.NA)
        cash = pd.to_numeric(nav["cash"], errors="coerce")
        average_cash_weight = safe_float((cash / total_value).dropna().mean())

    max_position_count = 0
    if not positions.empty and {"date", "quantity"}.issubset(positions.columns):
        active_positions = positions[pd.to_numeric(positions["quantity"], errors="coerce").fillna(0) > 0]
        if not active_positions.empty:
            max_position_count = int(active_positions.groupby("date")["asset_id"].count().max())

    execution_slippage = 0.0
    if not trades.empty and "valuation_price" in trades.columns:
        trade_prices = pd.to_numeric(trades["price"], errors="coerce")
        trade_val_prices = pd.to_numeric(trades["valuation_price"], errors="coerce")
        trade_qty = pd.to_numeric(trades["quantity"], errors="coerce")
        slippage_amt = (trade_prices - trade_val_prices).abs() * trade_qty
        valuation_amt = trade_val_prices * trade_qty
        sum_slippage_amt = slippage_amt.sum()
        sum_valuation_amt = valuation_amt.sum()
        if sum_valuation_amt > 0:
            execution_slippage = sum_slippage_amt / sum_valuation_amt

    fee_total = 0.0
    fee_drag_ratio = 0.0
    annualized_fee_drag = 0.0
    if not trades.empty and "fee" in trades.columns:
        fee_total = pd.to_numeric(trades["fee"], errors="coerce").fillna(0.0).sum()
        if average_total_value and average_total_value > 0:
            fee_drag_ratio = fee_total / average_total_value
            annualized_fee_drag = fee_drag_ratio / years if years else fee_drag_ratio

    return {
        "start_date": nav["date"].min().strftime("%Y-%m-%d"),
        "end_date": nav["date"].max().strftime("%Y-%m-%d"),
        "observations": int(days),
        "total_return": safe_float(total_return),
        "annualized_return": safe_float(annualized_return),
        "annualized_volatility": safe_float(annualized_volatility),
        "max_drawdown": safe_float(max_drawdown),
        "sharpe_ratio": safe_float(sharpe_ratio),
        "turnover_total": safe_float(turnover_amount_total),
        "annualized_turnover": safe_float(annualized_turnover_amount),
        "turnover_amount_total": safe_float(turnover_amount_total),
        "turnover_amount_ratio": safe_float(turnover_amount_ratio),
        "annualized_turnover_amount": safe_float(annualized_turnover_amount),
        "turnover_quantity_total": safe_float(turnover_quantity_total),
        "annualized_turnover_quantity": safe_float(annualized_turnover_quantity),
        "trade_count": int(len(trades)),
        "order_count": int(len(orders)),
        "skipped_order_count": int(len(skipped_orders)),
        "skipped_below_lot_or_cash_count": int(skipped_reason_counts.get("below_lot_or_cash", 0)),
        "filled_order_count": int(status_counts.get("FILLED", 0)),
        "rejected_order_count": int(status_counts.get("REJECTED", 0)),
        "order_status_counts": {str(key): int(value) for key, value in status_counts.items()},
        "rejection_reason_counts": {str(key): int(value) for key, value in rejection_reason_counts.items()},
        "skipped_reason_counts": {str(key): int(value) for key, value in skipped_reason_counts.items()},
        "pending_intent_count": int(pending_series.iloc[-1]) if len(pending_series) else 0,
        "max_pending_intent_count": int(pending_series.max()) if len(pending_series) else 0,
        "average_cash_weight": average_cash_weight,
        "max_position_count": max_position_count,
        "execution_slippage": safe_float(execution_slippage),
        "fee_total": safe_float(fee_total),
        "fee_drag_ratio": safe_float(fee_drag_ratio),
        "annualized_fee_drag": safe_float(annualized_fee_drag),
    }


def build_platform_metrics(result_dir: str | Path) -> dict[str, Any]:
    result_dir = Path(result_dir)
    nav = read_csv_or_empty(result_dir / "nav.csv")
    trades = read_csv_or_empty(result_dir / "trades.csv")
    orders = read_csv_or_empty(result_dir / "orders.csv")
    skipped_orders = read_csv_or_empty(result_dir / "skipped_orders.csv")
    positions = read_csv_or_empty(result_dir / "positions.csv")

    metrics: dict[str, Any] = {
        "results_dir": str(result_dir),
        "nav_csv": str(result_dir / "nav.csv"),
        "positions_csv": str(result_dir / "positions.csv"),
        "orders_csv": str(result_dir / "orders.csv"),
        "skipped_orders_csv": str(result_dir / "skipped_orders.csv"),
        "trades_csv": str(result_dir / "trades.csv"),
        "training_end_date": TRAINING_END_DATE,
        "oos_start_date": OOS_START_DATE,
    }

    full_metrics = _compute_period_metrics(nav, trades, orders, skipped_orders, positions)
    training_metrics = _compute_period_metrics(
        _filter_by_date(nav, end_date=TRAINING_END_DATE),
        _filter_by_date(trades, end_date=TRAINING_END_DATE),
        _filter_by_date(orders, end_date=TRAINING_END_DATE),
        _filter_by_date(skipped_orders, end_date=TRAINING_END_DATE),
        _filter_by_date(positions, end_date=TRAINING_END_DATE),
    )
    oos_metrics = _compute_period_metrics(
        _filter_by_date(nav, start_date=OOS_START_DATE),
        _filter_by_date(trades, start_date=OOS_START_DATE),
        _filter_by_date(orders, start_date=OOS_START_DATE),
        _filter_by_date(skipped_orders, start_date=OOS_START_DATE),
        _filter_by_date(positions, start_date=OOS_START_DATE),
    )

    metrics.update(full_metrics)
    metrics["full_metrics"] = dict(full_metrics)
    metrics["training_metrics"] = training_metrics
    metrics["oos_metrics"] = oos_metrics
    metrics["training_metrics_available"] = training_metrics.get("observations", 0) >= MIN_SAMPLE_OBSERVATIONS
    metrics["oos_metrics_available"] = oos_metrics.get("observations", 0) >= MIN_SAMPLE_OBSERVATIONS
    return metrics


def delta(candidate: dict[str, Any], baseline: dict[str, Any] | None, key: str) -> float | None:
    if baseline is None:
        return None
    left = candidate.get(key)
    right = baseline.get(key)
    if left is None or right is None:
        return None
    return safe_float(float(left) - float(right))


def comparison_metrics(candidate: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    keys = [
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "sharpe_ratio",
        "turnover_amount_total",
        "turnover_amount_ratio",
        "annualized_turnover_amount",
        "turnover_quantity_total",
        "annualized_turnover_quantity",
        "trade_count",
        "order_count",
        "rejected_order_count",
        "skipped_order_count",
        "skipped_below_lot_or_cash_count",
        "max_pending_intent_count",
        "average_cash_weight",
        "execution_slippage",
        "annualized_fee_drag",
    ]
    return {f"{key}_delta": delta(candidate, baseline, key) for key in keys}


def write_metrics_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
