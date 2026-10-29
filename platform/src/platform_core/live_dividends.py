"""实盘股息权益与自动到账；真实现金快照之前的到账不再补加。"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from math import isfinite
from pathlib import Path

from src.platform_core.models import PortfolioState, date_str, parse_date


def apply_dividends(state: PortfolioState, asof: date, path: Path,
                    code_to_asset_id: dict[str, str], ledger_path: Path) -> None:
    book = state.live_accounting
    today = date_str(asof)
    snapshots = book.setdefault("holdings", {})
    if "cash_asof" not in book:
        book["cash_asof"] = date_str(state.last_date or asof)
        snapshots.setdefault(book["cash_asof"], {a: p.quantity for a, p in state.positions.items()})
    # 冻结历史估值，不允许拿已经自动到账后的状态倒推旧日。
    if today < book.get("processed_through", book["cash_asof"]):
        return
    events = book.setdefault("dividends", {})
    rows, ledger = [], []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    if ledger_path.exists():
        with ledger_path.open(encoding="utf-8-sig", newline="") as handle:
            ledger = list(csv.DictReader(handle))
    # 旧账户的未关联应收可以认领一次；不同事件不能因金额相同而共用应收。
    unclaimed = Counter((r["asset_id"], date_str(r["payment_date"]), r["amount"])
                        for r in state.dividend_receivables)
    unclaimed.subtract((e["asset_id"], e["payment_date"], e["amount"])
                       for e in events.values() if not e["paid"] and e["amount"])
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
        record, ex, payment = (date_str(d) for d in (record, ex, payment))
        if not record <= ex <= payment:
            raise ValueError(f"分红日期顺序错误: {code}")
        key = f"{code}:{record}:{ex}"
        # 已由真实现金快照覆盖的到账（包括历史重建）不得重复记账。
        if key in events or payment <= book["cash_asof"] or ex > today:
            continue
        per_share = float(row["dividend_per_share"])
        if not isfinite(per_share) or per_share < 0:
            raise ValueError(f"每份股息必须为非负有限数: {code}")
        snapshot = max((d for d in snapshots if d <= record), default=None)
        trades = [r for r in ledger if r["code"] == code and r["date"] <= record
                  and (snapshot is None or r["date"] > snapshot)
                  and r["event"] in ("BUY", "SELL", "INTERNAL_TRANSFER_IN")]
        if snapshot is None and not trades:
            continue  # 缺少登记日持仓依据，不猜测权益。
        quantity = snapshots[snapshot].get(asset_id, 0.0) if snapshot else 0.0
        quantity += sum(float(r["quantity"]) * (-1 if r["event"] == "SELL" else 1) for r in trades)
        if not isfinite(quantity) or quantity < 0:
            raise ValueError(f"登记日持仓无效，请核对成交流水: {code}")
        amount = round(quantity * per_share, 2)
        events[key] = {"asset_id": asset_id, "record_date": record,
                       "ex_date": ex, "payment_date": payment,
                       "quantity": quantity, "amount": amount, "paid": False}
        if amount:
            signature = (asset_id, payment, amount)
            if unclaimed[signature] > 0:
                unclaimed[signature] -= 1
            else:
                state.dividend_receivables.append({"asset_id": asset_id,
                    "payment_date": parse_date(payment), "amount": amount})
    remaining = []
    for item in state.dividend_receivables:
        payment = date_str(item["payment_date"])
        if payment > today:
            remaining.append(item)
        elif payment > book["cash_asof"]:
            state.cash = round(state.cash + item["amount"], 8)
    state.dividend_receivables = remaining
    for event in events.values():
        if event["payment_date"] <= today:
            event["paid"] = True
    book["processed_through"] = today


def expected_income(state: PortfolioState, ledger_path: Path, asof: date) -> float | None:
    """按流水核对已实现收益；缺少卖出成本时返回未知，不猜测损益。"""
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
                if event not in ("BUY", "SELL", "INTERNAL_TRANSFER_IN", "DIVIDEND_RECEIVABLE"):
                    continue
                gross = float(row["gross_amount"])
                if not isfinite(gross) or gross < 0:
                    raise ValueError(f"流水金额必须为非负有限数: {code}")
                if event == "DIVIDEND_RECEIVABLE":
                    result += gross
                    ledger_dividends.add((code, row["date"]))
                    continue
                quantity = float(row["quantity"])
                fee = float(row.get("fee") or 0.0)
                if not isfinite(quantity) or quantity <= 0 or not isfinite(fee) or fee < 0:
                    raise ValueError(f"流水数量或费用无效: {code}")
                if event in ("BUY", "INTERNAL_TRANSFER_IN"):
                    quantities[code] = quantities.get(code, 0) + quantity
                    costs[code] = costs.get(code, 0) + gross + fee
                elif event == "SELL":
                    if quantities.get(code, 0.0) <= 0 or quantity > quantities[code] + 1e-9:
                        return None
                    basis = costs[code] / quantities[code] * quantity
                    result += gross - fee - basis
                    quantities[code] -= quantity
                    costs[code] -= basis
    for key, event in state.live_accounting.get("dividends", {}).items():
        if event["ex_date"] <= date_str(asof) and (key.split(":")[0], event["ex_date"]) not in ledger_dividends:
            result += event["amount"]
    return result
