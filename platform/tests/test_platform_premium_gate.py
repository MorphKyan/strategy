"""R056 溢价闸门：加载层前视防护 + 策略行为。

本文件的核心是**前视防护**测试。QDII 净值 T+1~T+2 才披露，若策略用 T 日净值决策，
回测会拿到当天尚不存在的信息——这是本课题最容易犯且最难察觉的错误，
故对滞后语义做逐条断言。
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.platform_core.etf_premium import EtfPremiumStore, reset_store_cache
from src.platform_core.models import Asset, Bar, PortfolioState, Position
from src.platform_core.strategies.premium_gated_satellite import PremiumGatedSatelliteStrategy
from src.platform_core.strategy import BUILTIN_STRATEGIES, StrategyContext

SAT = "CN_ETF:513100.SH"
CORE = ["CN_ETF:510300.SH", "CN_ETF:511260.SH", "CN_ETF:518880.SH", "CN_ETF:512890.SH"]
CORE_WEIGHTS = {asset_id: 0.25 for asset_id in CORE}


# --------------------------------------------------------------------- 数据夹具


@pytest.fixture
def premium_data(tmp_path):
    """造一段价格/净值：前 5 日溢价 0%，后 5 日溢价 10%。"""
    dates = pd.bdate_range("2024-06-03", periods=10).date
    nav = [1.0] * 10
    close = [1.0] * 5 + [1.10] * 5  # D5 起溢价 10%
    (tmp_path / "etf_nav").mkdir(exist_ok=True)
    pd.DataFrame({"trade_date": dates, "unit_nav": nav, "cum_nav": nav}).to_csv(
        tmp_path / "etf_nav" / "513100.csv", index=False
    )
    pd.DataFrame({"trade_date": dates, "close": close}).to_csv(tmp_path / "513100.csv", index=False)
    reset_store_cache()
    return tmp_path, list(dates)


# --------------------------------------------------------------------- 加载层


def test_premium_pairs_same_day_price_and_nav(premium_data):
    data_dir, dates = premium_data
    store = EtfPremiumStore(data_dir)
    # lag=0 时 asof=D5(索引5) 应读到当日 10% 溢价
    result = store.premium_at(SAT, dates[5], publication_lag_days=0)
    assert result.observed_date == dates[5]
    assert result.premium == pytest.approx(0.10)


def test_publication_lag_blocks_lookahead(premium_data):
    """溢价 D5 跳到 10%，lag=2 时 D5/D6 仍只能看到 0%，D7 才看到 10%。"""
    data_dir, dates = premium_data
    store = EtfPremiumStore(data_dir)

    for asof in (dates[5], dates[6]):
        result = store.premium_at(SAT, asof, publication_lag_days=2)
        assert result.premium == pytest.approx(0.0), f"{asof} 提前看到了尚未披露的净值"

    result = store.premium_at(SAT, dates[7], publication_lag_days=2)
    assert result.observed_date == dates[5]
    assert result.premium == pytest.approx(0.10)


def test_lag_counts_trading_days_not_calendar_days(premium_data):
    """滞后按观测序列计数——跨周末不得因自然日流逝而变松。"""
    data_dir, dates = premium_data
    store = EtfPremiumStore(data_dir)
    result = store.premium_at(SAT, dates[6], publication_lag_days=2)
    assert result.observed_date == dates[4]  # 恰好回退 2 个观测，与自然日间隔无关


def test_returns_none_when_history_shorter_than_lag(premium_data):
    data_dir, dates = premium_data
    store = EtfPremiumStore(data_dir)
    assert store.premium_at(SAT, dates[1], publication_lag_days=5) is None


def test_missing_nav_file_raises(tmp_path):
    reset_store_cache()
    store = EtfPremiumStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.premium_at(SAT, date(2024, 6, 3))


# --------------------------------------------------------------------- 策略


def _context(data_dir, asof, positions, cash, params_override=None):
    assets = {
        asset_id: Asset(asset_id=asset_id, code=asset_id.split(":")[-1].split(".")[0], name=asset_id, lot_size=100)
        for asset_id in CORE + [SAT]
    }
    bars = {
        asset_id: Bar(date=asof, asset_id=asset_id, open=1.0, high=1.0, low=1.0, close=1.0)
        for asset_id in CORE + [SAT]
    }
    state = PortfolioState(
        cash=cash,
        positions={
            asset_id: Position(asset_id=asset_id, quantity=quantity, cost_basis=1.0)
            for asset_id, quantity in positions.items()
            if quantity > 0
        },
        last_date=asof,
    )

    class _Data:
        def __init__(self, d):
            self.data_dir = d

        def is_month_end(self, _):
            return True  # 闸门每次都重估，隔离掉频率因素

    params = {
        "satellite": SAT,
        "satellite_weight": 0.30,
        "premium_cap": 0.02,
        "publication_lag_days": 2,
        "gate_eval": "month_end",
        "core_weights": CORE_WEIGHTS,
        "abs_band": 0.05,
        "rel_band": 0.25,
    }
    params.update(params_override or {})
    return StrategyContext(
        date=asof, assets=assets, bars=bars, state=state, data=_Data(data_dir), params=params, runtime={}
    )


def test_strategy_not_registered():
    """R056 验收 Failed（换手 9.34%→135.41%），按 Hard Rule 3 撤销注册。

    策略文件与本测试保留为 research-only：加载层的前视防护是通用能力，
    复研时重新 import 并注册即可。
    """
    assert "premium_gated_satellite" not in BUILTIN_STRATEGIES


def test_gate_open_holds_satellite(premium_data):
    """溢价 0% ≤ 2% → 闸门开，卫星 30%、核心各 17.5%。"""
    data_dir, dates = premium_data
    ctx = _context(data_dir, dates[4], {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0)
    target = PremiumGatedSatelliteStrategy().generate_targets(ctx)
    assert target.weights[SAT] == pytest.approx(0.30)
    for asset_id in CORE:
        assert target.weights[asset_id] == pytest.approx(0.175)


def test_gate_closed_routes_weight_back_to_core(premium_data):
    """溢价 10% > 2% → 闸门关，卫星权重为 0，核心各 25%（组内比例不变）。"""
    data_dir, dates = premium_data
    ctx = _context(data_dir, dates[7], {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0)
    target = PremiumGatedSatelliteStrategy().generate_targets(ctx)
    assert SAT not in target.weights
    for asset_id in CORE:
        assert target.weights[asset_id] == pytest.approx(0.25)
    assert sum(target.weights.values()) == pytest.approx(1.0)


def test_gate_closure_triggers_liquidation_of_held_satellite(premium_data):
    """已持有卫星时闸门关闭必须触发交易——目标里消失的资产也要参与偏离判定。"""
    data_dir, dates = premium_data
    positions = {asset_id: 175_000.0 for asset_id in CORE}
    positions[SAT] = 300_000.0
    ctx = _context(data_dir, dates[7], positions, cash=0.0)
    target = PremiumGatedSatelliteStrategy().generate_targets(ctx)
    assert target is not None, "闸门关闭却未触发再平衡，卫星会一直留在仓里"
    assert SAT not in target.weights


def test_missing_nav_closes_gate(tmp_path):
    """没有净值数据时闸门默认关闭——没有信号就不下注。"""
    reset_store_cache()
    ctx = _context(tmp_path, date(2024, 6, 10), {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0)
    target = PremiumGatedSatelliteStrategy().generate_targets(ctx)
    assert SAT not in target.weights


def test_gate_state_is_remembered_between_evaluations(premium_data):
    """非重估日沿用记忆状态，不因当日溢价波动翻转。"""
    data_dir, dates = premium_data

    class _DataNoMonthEnd:
        def __init__(self, d):
            self.data_dir = d

        def is_month_end(self, _):
            return False

    strategy = PremiumGatedSatelliteStrategy()
    runtime: dict = {}
    # 第一次（无记忆）→ 强制重估，溢价 0% → 开
    ctx = _context(data_dir, dates[4], {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0)
    ctx.runtime = runtime
    ctx.data = _DataNoMonthEnd(data_dir)
    assert strategy.generate_targets(ctx).weights[SAT] == pytest.approx(0.30)

    # 第二次：溢价已跳到 10%，但非重估日 → 沿用"开"
    ctx2 = _context(data_dir, dates[7], {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0)
    ctx2.runtime = runtime
    ctx2.data = _DataNoMonthEnd(data_dir)
    assert ctx2.runtime.get("r056_premium_gate_open") is True
    assert strategy.generate_targets(ctx2).weights[SAT] == pytest.approx(0.30)


def test_daily_gate_eval_reacts_immediately(premium_data):
    data_dir, dates = premium_data
    ctx = _context(
        data_dir, dates[7], {a: 0.0 for a in CORE + [SAT]}, cash=1_000_000.0,
        params_override={"gate_eval": "daily"},
    )
    target = PremiumGatedSatelliteStrategy().generate_targets(ctx)
    assert SAT not in target.weights
