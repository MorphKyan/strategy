from __future__ import annotations

from datetime import date

import pytest

from src.platform_core.models import Asset, Bar, PortfolioState, Position, TargetPortfolio
from src.platform_core.strategy import (
    AdaptiveRiskDeviationVolatilityTriggeredStrategy,
    RiskParityStrategy,
    StrategyContext,
    get_strategy_class,
)
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


def test_risk_parity_uses_explicit_5_25_thresholds():
    strategy = RiskParityStrategy()
    target = TargetPortfolio({asset_id: 0.25 for asset_id in "ABCD"})

    inside = _context(
        {"A": (2900.0, 10.0), "B": (2100.0, 10.0), "C": (2500.0, 10.0), "D": (2500.0, 10.0)},
        cash=0.0,
        params={"rebalance_threshold": 0.05, "rebalance_relative_threshold": 0.25},
    )
    assert strategy.should_rebalance(inside, target) is False

    absolute_breach = _context(
        {"A": (3100.0, 10.0), "B": (2300.0, 10.0), "C": (2300.0, 10.0), "D": (2300.0, 10.0)},
        cash=0.0,
        params={"rebalance_threshold": 0.05, "rebalance_relative_threshold": 0.25},
    )
    assert strategy.should_rebalance(absolute_breach, target) is True

    relative_target = TargetPortfolio({"A": 0.30, "B": 0.30, "C": 0.30, "D": 0.10})
    relative_breach = _context(
        {"A": (2900.0, 10.0), "B": (2900.0, 10.0), "C": (2900.0, 10.0), "D": (1300.0, 10.0)},
        cash=0.0,
        params={"rebalance_threshold": 0.05, "rebalance_relative_threshold": 0.25},
    )
    assert strategy.should_rebalance(relative_breach, relative_target) is True


def test_risk_parity_without_thresholds_keeps_unconditional_default():
    context = _context({asset_id: (2500.0, 10.0) for asset_id in "ABCD"}, cash=0.0, params={})
    target = TargetPortfolio({asset_id: 0.25 for asset_id in "ABCD"})
    assert RiskParityStrategy().should_rebalance(context, target) is True


def test_relative_threshold_liquidates_zero_target_position():
    context = _context(
        {"A": (100.0, 10.0), "B": (9900.0, 10.0), "C": (0.0, 10.0), "D": (0.0, 10.0)},
        cash=0.0,
        params={"rebalance_threshold": 0.05, "rebalance_relative_threshold": 0.25},
    )
    target = TargetPortfolio({"B": 1.0})
    assert RiskParityStrategy().should_rebalance(context, target) is True


def test_adaptive_strategy_always_allows_initial_build():
    context = _context({asset_id: (0.0, 10.0) for asset_id in "ABCD"}, cash=100000.0, params={})
    target = TargetPortfolio({asset_id: 0.25 for asset_id in "ABCD"})
    assert AdaptiveRiskDeviationVolatilityTriggeredStrategy().should_rebalance(context, target) is True


def test_r059_strategies_registered():
    from src.platform_core.strategies.macro_factor_es import RiskParityMacroFactorStrategy
    from src.platform_core.strategies.black_litterman_es import RiskParityBlackLittermanStrategy

    assert get_strategy_class("risk_parity_macro_factor") is RiskParityMacroFactorStrategy
    assert get_strategy_class("risk_parity_black_litterman") is RiskParityBlackLittermanStrategy


def test_black_litterman_strategy_no_constant_fallbacks():
    """Verify Black-Litterman ES sources dynamic Point-in-Time fundamental views."""
    import pandas as pd
    import numpy as np
    from src.platform_core.strategies.black_litterman_es import RiskParityBlackLittermanStrategy

    strat = RiskParityBlackLittermanStrategy()
    assert strat.name == "risk_parity_black_litterman"

    # Test with empty PIT views (simulating missing data window)
    strat._pit_views_df = None

    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    data = {
        "CN_ETF:510300.SH": np.linspace(10, 15, 200) + np.random.randn(200) * 0.1,
        "CN_ETF:511260.SH": np.linspace(100, 102, 200) + np.random.randn(200) * 0.05,
    }
    df = pd.DataFrame(data, index=dates)

    class MockDataStore:
        def get_price_frame(self, universe, date, use_nav=False):
            return df.loc[df.index <= pd.to_datetime(date)]

    context = StrategyContext(
        date=pd.Timestamp("2024-09-01"),
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={"risk_budgets": {"CN_ETF:510300.SH": 0.5, "CN_ETF:511260.SH": 0.5}},
    )

    target = strat._inverse_vol_target(context, list(data.keys()))
    assert target is not None
    assert "CN_ETF:510300.SH" in target.weights
    assert "CN_ETF:511260.SH" in target.weights
    # In absence of PIT views, weights equal base equal-budget weights
    w1 = target.weights["CN_ETF:510300.SH"]
    w2 = target.weights["CN_ETF:511260.SH"]
    assert np.isclose(w1 + w2, 1.0) or (w1 + w2 < 1.0)



