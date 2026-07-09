from __future__ import annotations

from datetime import date

import pytest

from src.platform_core.models import Asset, Bar, PortfolioState, Position
from src.platform_core.strategy import StrategyContext, get_strategy_class
from src.platform_core.strategies.fixed_weight import FixedWeightThresholdStrategy


def _context(positions: dict[str, tuple[float, float]], cash: float, params: dict) -> StrategyContext:
    """positions: asset_id -> (quantity, price)"""
    assets = {
        asset_id: Asset(asset_id=asset_id, code=asset_id, name=asset_id, lot_size=100)
        for asset_id in ("A", "B", "C", "D")
    }
    bars = {
        asset_id: Bar(date=date(2024, 6, 3), asset_id=asset_id, open=price, high=price, low=price, close=price)
        for asset_id, (_, price) in positions.items()
    }
    state = PortfolioState(
        cash=cash,
        positions={
            asset_id: Position(asset_id=asset_id, quantity=quantity, cost_basis=price)
            for asset_id, (quantity, price) in positions.items()
            if quantity > 0
        },
        last_date=date(2024, 5, 31),
    )
    return StrategyContext(
        date=date(2024, 6, 3),
        assets=assets,
        bars=bars,
        state=state,
        data=None,
        params={"universe": ["A", "B", "C", "D"], **params},
        runtime={},
    )


def test_fixed_weight_threshold_registered():
    assert get_strategy_class("fixed_weight_threshold") is FixedWeightThresholdStrategy


def test_opens_full_target_when_flat():
    # 全现金空仓 → 建仓到等权目标
    ctx = _context({a: (0.0, 10.0) for a in "ABCD"}, cash=100000.0, params={})
    target = FixedWeightThresholdStrategy().generate_targets(ctx)
    assert target is not None
    assert target.weights == pytest.approx({a: 0.25 for a in "ABCD"})


def test_holds_inside_band():
    # 每个资产 25,000 元、总值 100,000 → 全部正中目标，无偏离 → 不动
    ctx = _context({a: (2500.0, 10.0) for a in "ABCD"}, cash=0.0, params={})
    assert FixedWeightThresholdStrategy().generate_targets(ctx) is None

    # 偏离 4pp（29%/21%...）在 5pp 绝对带与 25% 相对带内 → 仍不动
    ctx = _context(
        {"A": (2900.0, 10.0), "B": (2100.0, 10.0), "C": (2500.0, 10.0), "D": (2500.0, 10.0)},
        cash=0.0,
        params={},
    )
    assert FixedWeightThresholdStrategy().generate_targets(ctx) is None


def test_triggers_on_absolute_band_breach():
    # A 涨到 31%（偏离 6pp > 5pp 绝对带）→ 全组合归位
    ctx = _context(
        {"A": (3100.0, 10.0), "B": (2300.0, 10.0), "C": (2300.0, 10.0), "D": (2300.0, 10.0)},
        cash=0.0,
        params={},
    )
    target = FixedWeightThresholdStrategy().generate_targets(ctx)
    assert target is not None
    assert target.weights == pytest.approx({a: 0.25 for a in "ABCD"})


def test_triggers_on_relative_band_breach_for_small_weight():
    # 显式小权重资产：D 目标 10%，涨到 13%（偏离 3pp < 5pp 绝对带，
    # 但 3pp > 10% × 25% = 2.5pp 相对带）→ 触发
    params = {"target_weights": {"A": 0.30, "B": 0.30, "C": 0.30, "D": 0.10}}
    ctx = _context(
        {"A": (2900.0, 10.0), "B": (2900.0, 10.0), "C": (2900.0, 10.0), "D": (1300.0, 10.0)},
        cash=0.0,
        params=params,
    )
    target = FixedWeightThresholdStrategy().generate_targets(ctx)
    assert target is not None
    assert target.weights == pytest.approx({"A": 0.30, "B": 0.30, "C": 0.30, "D": 0.10})


def test_explicit_target_weights_are_normalized():
    ctx = _context({a: (0.0, 10.0) for a in "ABCD"}, cash=100000.0, params={"target_weights": {"A": 2, "B": 1, "C": 1, "D": 1}})
    target = FixedWeightThresholdStrategy().generate_targets(ctx)
    assert target is not None
    assert sum(target.weights.values()) == pytest.approx(1.0)
    assert target.weights["A"] == pytest.approx(0.4)
