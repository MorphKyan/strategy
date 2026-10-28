"""实盘股息权益与自动到账；真实现金快照之前的到账不再补加。"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.platform_core.models import PortfolioState, date_str, parse_date


def remember_holdings(state: PortfolioState, asof: date) -> None:
    book = state.live_accounting
    snapshots = book.setdefault("holdings", {})
    snapshots[date_str(asof)] = {a: p.quantity for a, p in state.positions.items()}


def apply_dividends(state: PortfolioState, asof: date, path: Path,
                    code_to_asset_id: dict[str, str], ledger_path: Path) -> None:
    book = state.live_accounting
    if "cash_asof" not in book:
        book["cash_asof"] = date_str(state.last_date or asof)
        remember_holdings(state, state.last_date or asof)
    # 冻结历史估值，不允许拿已经自动到账后的状态倒推旧日。
    if date_str(asof) < book.get("processed_through", book["cash_asof"]):
        return
    events = book.setdefault("dividends", {})
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ledger = None
    if ledger_path.exists():
        with ledger_path.open(encoding="utf-8-sig", newline="") as handle:
            ledger = list(csv.DictReader(handle))
    for row in sorted(rows, key=lambda r: r["ex_date"]):
        code = row["code"].strip()
        asset_id = code_to_asset_id.get(code)
        if asset_id is None:
            continue
        record = row["record_date"].strip()
        ex = row["ex_date"].strip()
        payment = row["payment_date"].strip()
        if not record or not ex or not payment:
            raise ValueError(f"分红日期缺失: {code}")
        if not record <= ex <= payment:
            raise ValueError(f"分红日期顺序错误: {code}")
        key = f"{code}:{record}:{ex}"
        # 已由真实现金快照覆盖的到账（包括历史重建）不得重复记账。
        if payment <= book["cash_asof"] or ex > date_str(asof):
            continue
        if key not in events:
            snapshots = book["holdings"]
            dates = [d for d in snapshots if d <= record]
            if dates:
                quantity = snapshots[max(dates)].get(asset_id, 0.0)
            elif ledger is not None:
                quantity = sum(float(r["quantity"]) * (-1 if r["event"] == "SELL" else 1)
                               for r in ledger if r["code"] == code and r["date"] <= record
                               and r["event"] in ("BUY", "SELL", "INTERNAL_TRANSFER_IN"))
            else:
                # 新接入账户无法推断现金快照之前的登记日持仓。
                continue
            amount = round(quantity * float(row["dividend_per_share"]), 2)
            events[key] = {"asset_id": asset_id, "record_date": record,
                           "ex_date": ex, "payment_date": payment,
                           "quantity": quantity, "amount": amount, "paid": False}
            if amount and not any(r["asset_id"] == asset_id
                                  and date_str(r["payment_date"]) == payment
                                  and r["amount"] == amount
                                  for r in state.dividend_receivables):
                state.dividend_receivables.append({"asset_id": asset_id,
                    "payment_date": parse_date(payment), "amount": amount})
        event = events[key]
        if not event["paid"] and event["payment_date"] <= date_str(asof):
            state.cash = round(state.cash + event["amount"], 8)
            if event["amount"]:
                item = next(r for r in state.dividend_receivables
                            if r["asset_id"] == asset_id
                            and date_str(r["payment_date"]) == event["payment_date"]
                            and r["amount"] == event["amount"])
                state.dividend_receivables.remove(item)
            event["paid"] = True
    book["processed_through"] = date_str(asof)


def expected_income(state: PortfolioState, ledger_path: Path, asof: date) -> float:
    """按流水成本结转核对已实现收益，并加入尚未写入流水的自动股息。"""
    result = 0.0
    ledger_dividends: set[tuple[str, str]] = set()
    if ledger_path.exists():
        quantities: dict[str, float] = {}
        costs: dict[str, float] = {}
        with ledger_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in sorted(csv.DictReader(handle), key=lambda r: r["date"]):
                if row["date"] > date_str(asof):
                    continue
                code, event = row["code"], row["event"]
                quantity, gross, fee = (float(row[k]) for k in ("quantity", "gross_amount", "fee"))
                if event in ("BUY", "INTERNAL_TRANSFER_IN"):
                    quantities[code] = quantities.get(code, 0) + quantity
                    costs[code] = costs.get(code, 0) + gross + fee
                elif event == "SELL":
                    basis = costs[code] / quantities[code] * quantity
                    result += gross - fee - basis
                    quantities[code] -= quantity
                    costs[code] -= basis
                elif event == "DIVIDEND_RECEIVABLE":
                    result += gross
                    ledger_dividends.add((code, row["date"]))
    for key, event in state.live_accounting.get("dividends", {}).items():
        if event["ex_date"] <= date_str(asof) and (key.split(":")[0], event["ex_date"]) not in ledger_dividends:
            result += event["amount"]
    return result
