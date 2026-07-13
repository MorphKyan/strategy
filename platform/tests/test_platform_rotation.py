from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.platform_core.models import Asset, Bar, PortfolioState, Position
from src.platform_core.strategy import BUILTIN_STRATEGIES, StrategyContext
from src.platform_core.strategies.rotation import IndustryMomentumRotationStrategy

UNIVERSE = ["A", "B", "C", "D", "E", "F"]
# 日收益率恒定 → 动量排名 A > B > C > D > E > F
DAILY_RETURNS = {"A": 0.004, "B": 0.003, "C": 0.002, "D": 0.001, "E": 0.0, "F": -0.002}


class _FakeData:
    """最小行情桩：aligned 后复权价 + 可选交易日历（供月频节奏判断）。"""

    def __init__(self, frame: pd.DataFrame, calendar: list[date] | None = None):
        self._frame = frame
        if calendar is not None:
            self.calendar = calendar

    def get_price_frame(self, universe: list[str], end_date: date, use_nav: bool = False):
        df = self._frame.loc[self._frame.index <= pd.Timestamp(end_date), universe]
        return df.dropna()


def _price_frame(days: int = 80, overrides: dict[str, dict[int, float]] | None = None) -> pd.DataFrame:
    """overrides: asset -> {距末尾的偏移(0=最后一天): 当日收益率}，用于构造尾部崩盘等情形。"""
    index = pd.bdate_range(end="2024-06-03", periods=days)
    data = {}
    for asset_id, ret in DAILY_RETURNS.items():
        prices = [1.0]
        for i in range(1, days):
            r = ret
            if overrides and asset_id in overrides:
                offset = days - 1 - i
                r = overrides[asset_id].get(offset, ret)
            prices.append(prices[-1] * (1 + r))
        data[asset_id] = prices
    return pd.DataFrame(data, index=index)


def _context(
    positions: dict[str, float],
    frame: pd.DataFrame,
    params: dict | None = None,
    calendar: list[date] | None = None,
    current: date = date(2024, 6, 3),
) -> StrategyContext:
    assets = {a: Asset(asset_id=a, code=a, name=a, lot_size=100) for a in UNIVERSE}
    bars = {
        a: Bar(date=current, asset_id=a, open=1.0, high=1.0, low=1.0, close=float(frame[a].iloc[-1]))
        for a in UNIVERSE
    }
    state = PortfolioState(
        cash=100000.0,
        positions={
            a: Position(asset_id=a, quantity=q, cost_basis=1.0) for a, q in positions.items() if q > 0
        },
        last_date=current,
    )
    return StrategyContext(
        date=current,
        assets=assets,
        bars=bars,
        state=state,
        data=_FakeData(frame, calendar),
        params={"universe": UNIVERSE, **(params or {})},
        runtime={},
    )


def _targets(ctx: StrategyContext):
    strategy = IndustryMomentumRotationStrategy()
    strategy.initialize(ctx)
    return strategy.generate_targets(ctx)


def test_rotation_not_registered():
    # R039 v1 验收 Failed，按 Hard Rule 3 保持 research-only、不注册（防误用回归）
    assert "industry_momentum_rotation" not in BUILTIN_STRATEGIES


def test_flat_state_selects_top_n_equal_weight():
    target = _targets(_context({}, _price_frame()))
    assert target is not None
    assert target.weights == pytest.approx({"A": 1 / 3, "B": 1 / 3, "C": 1 / 3})
    assert all(w >= 0 for w in target.weights.values())
    assert sum(target.weights.values()) <= 1.0 + 1e-9


def test_rank_buffer_keeps_incumbent_within_band():
    # 现任 D 排名第 4，在 top_n(3)+buffer(2) 内 → 留任；空位按排名补 A、B
    target = _targets(_context({"D": 30000.0}, _price_frame()))
    assert target is not None
    assert set(target.weights) == {"D", "A", "B"}
    assert target.weights["D"] == pytest.approx(1 / 3)


def test_rank_buffer_evicts_incumbent_outside_band():
    # 现任 F 排名第 6，超出缓冲带 → 换出，选 A/B/C
    target = _targets(_context({"F": 30000.0}, _price_frame()))
    assert target is not None
    assert set(target.weights) == {"A", "B", "C"}


def test_momentum_floor_leaves_unfilled_slots_in_cash():
    # 只有 A 动量为正：仅持 A，权重 1/3，其余留现金
    frame = _price_frame()
    negative = frame.copy()
    for a in ("B", "C", "D", "E"):
        negative[a] = frame["F"].values  # 全部替换为负动量序列
    target = _targets(_context({}, negative))
    assert target is not None
    assert set(target.weights) == {"A"}
    assert target.weights["A"] == pytest.approx(1 / 3)


def test_all_negative_momentum_liquidates_to_cash():
    frame = _price_frame()
    bear = frame.copy()
    for a in UNIVERSE:
        bear[a] = frame["F"].values
    target = _targets(_context({"A": 30000.0}, bear))
    assert target is not None
    assert target.weights == {}


def test_skip_days_ignores_recent_crash():
    # A 在最近 5 个交易日每天 -5%，但信号锚点在 t-5，A 仍应入选
    crash = _price_frame(overrides={"A": {i: -0.05 for i in range(5)}})
    target = _targets(_context({}, crash))
    assert target is not None
    assert "A" in target.weights


def test_insufficient_history_returns_none():
    assert _targets(_context({}, _price_frame(days=40))) is None


def test_monthly_cadence_via_calendar():
    frame = _price_frame()
    # 月中：下一交易日同月 → 非调仓日
    mid_calendar = [date(2024, 6, 3), date(2024, 6, 4)]
    assert _targets(_context({}, frame, calendar=mid_calendar, current=date(2024, 6, 3))) is None
    # 月末：下一交易日跨月 → 调仓日
    eom_calendar = [date(2024, 5, 31), date(2024, 6, 3)]
    frame_eom = frame.loc[frame.index <= pd.Timestamp(date(2024, 5, 31))]
    target = _targets(_context({}, frame_eom, calendar=eom_calendar, current=date(2024, 5, 31)))
    assert target is not None


def test_threshold_band_suppresses_intra_band_drift():
    # 成员未变、漂移在阈值带内 → 当月不交易（None）
    frame = _price_frame()
    ctx = _context(
        {"A": 34000.0, "B": 33000.0, "C": 33000.0},
        frame,
        params={"rebalance_threshold": 0.05},
    )
    # 手工把现金清零，让三者权重都在 1/3 附近（带内）
    ctx.state.cash = 0.0
    assert _targets(ctx) is None
