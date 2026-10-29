"""份额拆分（企业行为）的加载、生效日解析与应用。

数据源（finshare）的 ``split_date`` 是份额折算/分拆的基准日，而行情价格一律在
其后第一个真实交易日才反映拆分：拆分日通常停牌（512890 2021-10-22、513100
2022-01-13、513500 2022-03-29），510500 2022-08-26 当日甚至有成交但价格仍未除权。
若在 ``split_date`` 当天就调整持仓数量，会与停牌前向填充的旧价相乘，产生单日
净值假尖峰（如 baseline_r1 在 2021-10-22 的 +11%/-10%）。

因此拆分统一在 ``split_date`` 之后、该资产第一个有真实行情 bar 的交易日生效。
engine 与 sim 共用本模块，避免两处逻辑漂移。
"""

from __future__ import annotations

from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any

import pandas as pd

from src.platform_core.models import PortfolioState, parse_date


def load_corporate_actions(config: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    """从行情所属目录加载并验证事件；显式覆盖路径不存在时拒绝静默跳过。"""
    if kind not in {"dividends", "splits"}:
        raise ValueError(f"Unknown corporate-action kind: {kind}")
    data = config.get("data") or {}
    directory = data.get("market_store_dir") or data.get("data_dir") or Path(__file__).resolve().parents[2] / "data"
    override = data.get(f"{kind}_csv")
    path = Path(override) if override else Path(directory) / f"platform_{kind}.csv"
    if not path.exists() and not override:
        return []
    frame = pd.read_csv(path, dtype={"code": str})
    event_date, value_column = (("ex_date", "dividend_per_share") if kind == "dividends"
                                else ("split_date", "split_ratio"))
    date_columns = [event_date, "payment_date"] if kind == "dividends" else [event_date]
    missing = {"code", value_column, *date_columns} - set(frame.columns)
    if missing:
        raise ValueError(f"Corporate-action columns missing: {sorted(missing)} ({path})")
    frame["code"] = frame["code"].str.strip()
    for column in date_columns:
        frame[column] = frame[column].map(lambda value: parse_date(str(value).strip()))
    values = pd.to_numeric(frame[value_column], errors="raise")
    if (frame["code"].isna().any() or frame["code"].eq("").any()
            or frame.duplicated(["code", event_date]).any() or not values.map(isfinite).all()
            or (values < 0).any() or (kind == "splits" and (values == 0).any())):
        raise ValueError(f"Invalid or duplicate corporate actions: {path}")
    if kind == "dividends" and (frame["payment_date"] < frame["ex_date"]).any():
        raise ValueError(f"Dividend payment precedes its ex-date: {path}")
    frame[value_column] = values
    return frame.sort_values(["code", event_date]).to_dict("records")


def apply_due_dividends(dividends: list[dict[str, Any]], state: PortfolioState,
                        code_to_asset_id: dict[str, str], current_date: date) -> None:
    """回测和模拟在执行当日订单前确认除息权益，并结转到期应收。"""
    for dividend in dividends:
        if dividend["ex_date"] != current_date:
            continue
        asset_id = code_to_asset_id.get(dividend["code"])
        position = state.positions.get(asset_id)
        if position is not None and position.quantity > 0:
            state.dividend_receivables.append({"asset_id": asset_id,
                "payment_date": dividend["payment_date"],
                "amount": position.quantity * dividend["dividend_per_share"]})
    remaining = []
    for item in state.dividend_receivables:
        if item["payment_date"] <= current_date:
            state.cash += item["amount"]
        else:
            remaining.append(item)
    state.dividend_receivables = remaining


def resolve_split_effective_dates(
    splits: list[dict[str, Any]],
    code_to_asset_id: dict[str, str],
    data: Any,
) -> None:
    """就地为每条拆分记录计算 ``effective_date``。

    生效日 = ``split_date`` 之后该资产第一个真实行情日（data.first_bar_date_after）。
    资产不在本组合或数据窗口内没有后续行情时为 None（永不应用）。
    """
    for split in splits:
        asset_id = code_to_asset_id.get(split["code"])
        split["effective_date"] = (
            data.first_bar_date_after(asset_id, split["split_date"]) if asset_id else None
        )


def merge_event_table(
    existing: "pd.DataFrame | None",
    fetched: "pd.DataFrame",
    key_columns: list[str],
) -> tuple["pd.DataFrame", list[str], list[dict[str, Any]]]:
    """企业行为事件表的**只增不删**合并。

    背景：分红/拆分抓取器曾把上游返回的整表直接覆盖本地文件，一次上游数据
    异常就静默删掉了已验证的历史事件（510500 的 2022/2015 两条拆分被替换成
    一条错误的 1:0.01）。规则：
    - 本地已有事件行原样保留（含人工校正）；
    - 抓取结果中键不存在于本地的行作为"候选新增"返回（由调用方决定是否采纳，
      拆分类需先过价格交叉验证）；
    - 键相同但内容不同的抓取行**不覆盖**，记入 notes 留人工裁决。

    返回 (合并后的表, notes, 候选新增行列表)。
    """
    notes: list[str] = []
    fetched_str = fetched.fillna("").astype(str)
    if not fetched_str.empty and fetched_str.duplicated(key_columns).any():
        raise ValueError("上游企业行为事件键重复，拒绝合并。")
    if existing is None or existing.empty:
        return fetched_str.iloc[:0].copy(), notes, fetched_str.to_dict("records")

    existing_str = existing.fillna("").astype(str)
    key_of = lambda row: tuple(row.get(c, "") for c in key_columns)  # noqa: E731
    existing_by_key = {key_of(row): row for row in existing_str.to_dict("records")}
    compare_columns = set(existing_str.columns) & set(fetched_str.columns) - set(key_columns)

    additions: list[dict[str, Any]] = []
    fetched_keys = set()
    for row in fetched_str.to_dict("records"):
        key = key_of(row)
        fetched_keys.add(key)
        old = existing_by_key.get(key)
        if old is None:
            additions.append(row)
        elif any(old[column] != row[column] for column in compare_columns):
            notes.append(f"上游与本地事件内容冲突 {key}（已保留本地，需人工核对）")
    missing = existing_by_key.keys() - fetched_keys
    if missing:
        notes.append(f"上游缺失本地已有事件 {sorted(missing)}（已保留，不删除）")
    return existing_str, notes, additions


def validate_split_against_prices(
    code: str,
    split_date: str,
    split_ratio: float,
    data_dir: str | Path,
    tolerance: float = 0.15,
) -> tuple[bool, str]:
    """用本地价格交叉验证一条拆分事件：拆分后首个交易日价格应≈拆前价 ÷ split_ratio。

    数据不足（事件早于本地历史等）时保守拒绝——错误拆分入表会让回测持仓
    凭空放大/缩小，宁可留人工添加。
    """
    path = Path(data_dir) / f"{code}.csv"
    if not path.exists():
        return False, f"{code} 无本地价格数据，无法验证"
    frame = pd.read_csv(path)
    close_column = "close" if "close" in frame else "close_price"
    frame = frame.rename(columns={close_column: "close"}).sort_values("trade_date")
    prev = frame[frame["trade_date"] <= str(split_date)]
    nxt = frame[frame["trade_date"] > str(split_date)]
    if prev.empty or nxt.empty:
        return False, f"{code} {split_date} 前后价格数据不足，无法验证"
    prev_close = float(prev.iloc[-1]["close"])
    next_close = float(nxt.iloc[0]["close"])
    if any(not isfinite(value) or value <= 0 for value in (split_ratio, prev_close, next_close)):
        return False, f"{code} {split_date} 比例或价格非法"
    expected = prev_close / float(split_ratio)
    deviation = abs(next_close / expected - 1.0)
    if deviation <= tolerance:
        return True, f"{code} {split_date} 验证通过（偏差 {deviation:.1%}）"
    return False, (
        f"{code} {split_date} 比例 1:{split_ratio} 与价格不符："
        f"拆前收 {prev_close}，拆后首日收 {next_close}，期望≈{expected:.4f}（偏差 {deviation:.1%}）"
    )


def apply_due_splits(
    splits: list[dict[str, Any]],
    state: PortfolioState,
    code_to_asset_id: dict[str, str],
    current_date: date,
) -> None:
    """在生效日当天调整持仓数量与成本。必须先调用 resolve_split_effective_dates。"""
    for split in splits:
        if split.get("effective_date") != current_date:
            continue
        asset_id = code_to_asset_id.get(split["code"])
        if asset_id and asset_id in state.positions:
            position = state.positions[asset_id]
            if position.quantity > 0:
                position.quantity *= split["split_ratio"]
                position.cost_basis /= split["split_ratio"]
