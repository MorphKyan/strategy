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

import csv
from datetime import date
from pathlib import Path
from typing import Any

from src.platform_core.models import PortfolioState, parse_date


def load_splits(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """读取拆分表。默认 ``platform/data/platform_splits.csv``，
    可用 config["data"]["splits_csv"] 覆盖（主要供测试注入）。"""
    override = ((config or {}).get("data") or {}).get("splits_csv")
    if override:
        path = Path(override)
    else:
        platform_dir = Path(__file__).resolve().parent.parent.parent
        path = platform_dir / "data" / "platform_splits.csv"
    if not path.exists():
        return []
    splits: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            splits.append(
                {
                    "code": row["code"].strip(),
                    "split_date": parse_date(row["split_date"].strip()),
                    "split_ratio": float(row["split_ratio"].strip()),
                }
            )
    return splits


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
