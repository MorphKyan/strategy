from __future__ import annotations

import json
import csv
from datetime import date
from pathlib import Path

import pytest

from src.platform_core.data_store import MarketDataStore
from src.platform_core.data_validation import compare_hfq_data
from src.platform_core.engine import PlatformBacktestEngine, load_checkpoint
from src.platform_core.execution import ExecutionConfig, ExecutionEngine, FeeProfile
from src.platform_core.experiment import run_platform_experiment
from src.platform_core.metrics import build_platform_metrics
from src.platform_core.models import Asset, Bar, PendingIntent, PortfolioState, TargetPortfolio
from src.platform_core.sim import SimPortfolio
from src.platform_core.slippage import REQUIRED_SLIPPAGE_SCENARIOS, apply_slippage_scenario
from src.platform_core.storage import SQLiteStore, InMemoryStore
from src.platform_core.strategy import MonthlyEqualWeightStrategy
from src.platform_core.strategy import RiskParityStrategy
from src.platform_core.strategy import get_strategy_class
from src.platform_core.visualization import render_platform_charts


def test_target_portfolio_rejects_invalid_weights():
    with pytest.raises(ValueError):
        TargetPortfolio({"A": -0.1})
    with pytest.raises(ValueError):
        TargetPortfolio({"A": 0.7, "B": 0.4})


def test_market_sync_normalizes_open_ended_dates_and_preserves_existing_file_on_empty_fetch(tmp_path):
    import pandas as pd

    asset = Asset(asset_id="CN_ETF:515080.SH", code="515080", name="ETF", exchange="SH")
    existing = tmp_path / "515080.csv"
    existing.write_text("trade_date,close\n2026-06-24,1.0\n", encoding="utf-8")

    class EmptySource:
        def fetch_bars(self, code, start=None, end=None, adjust=None):
            assert code == "515080.SH"
            assert start == "1990-01-01"
            assert end == date.today().isoformat()
            return pd.DataFrame()

    with pytest.raises(RuntimeError, match="existing file was preserved"):
        MarketDataStore(tmp_path, source=EmptySource()).sync_assets([asset], start=None, end=None, fetch=True)
    assert existing.read_text(encoding="utf-8") == "trade_date,close\n2026-06-24,1.0\n"


def test_market_sync_skips_provider_fetch_for_synthetic_asset(tmp_path, monkeypatch):
    import pandas as pd

    monkeypatch.setattr("src.platform_core.data_store.date", type("D", (), {"today": staticmethod(lambda: date(2026, 7, 12))}))
    asset = Asset(asset_id="CN_ETF:511260_3X.SH", code="511260_3X", name="模拟30Y", exchange="SH")
    pd.DataFrame({
        "trade_date": ["2026-07-10"], "open": [1], "high": [1], "low": [1], "close": [1],
        "volume": [1], "amount": [1], "adjust_factor": [1], "source": ["simulated"], "updated_at": ["x"],
    }).to_csv(tmp_path / "511260_3X.csv", index=False)

    class NoFetch:
        def fetch_bars(self, *args, **kwargs):
            raise AssertionError("synthetic asset must not be fetched from provider")

    report = MarketDataStore(tmp_path, source=NoFetch()).sync_assets([asset], start=None, end=None, fetch=True)
    assert any("provider fetch skipped" in note for note in report.notes)


def test_risk_parity_daily_rebalance_frequency_checks_every_trading_day():
    class Data:
        calendar = [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
        ]

    class Context:
        date = date(2024, 1, 3)
        data = Data()
        runtime = {"rebalance_frequency": "daily"}

    assert RiskParityStrategy._is_rebalance_day(Context())
    Context.runtime = {"rebalance_frequency": "quarterly"}
    assert not RiskParityStrategy._is_rebalance_day(Context())


def test_fee_profile_applies_minimum_fee():
    fee = FeeProfile(rate=0.001, min_fee=5)
    assert fee.calculate(1000) == 5
    assert fee.calculate(10000) == 10


def test_execution_applies_default_and_qdii_commodity_slippage():
    bar = Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10)
    engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile(rate=0.0)))

    normal_asset = Asset(asset_id="A", code="510300", name="沪深300ETF", lot_size=1)
    state = PortfolioState(cash=1000)
    _, trades = engine.apply_target(date(2024, 1, 1), state, {"A": normal_asset}, {"A": bar}, TargetPortfolio({"A": 0.5}))
    assert trades[0].price == pytest.approx(10.002)

    qdii_asset = Asset(asset_id="A", code="513100", name="纳指ETF", lot_size=1)
    state = PortfolioState(cash=1000)
    _, trades = engine.apply_target(date(2024, 1, 1), state, {"A": qdii_asset}, {"A": bar}, TargetPortfolio({"A": 0.5}))
    assert trades[0].price == pytest.approx(10.006)

    commodity_asset = Asset(asset_id="A", code="159985", name="豆粕ETF", lot_size=1)
    state = PortfolioState(cash=1000)
    _, trades = engine.apply_target(date(2024, 1, 1), state, {"A": commodity_asset}, {"A": bar}, TargetPortfolio({"A": 0.5}))
    assert trades[0].price == pytest.approx(10.006)


def test_execution_applies_dynamic_participation_slippage():
    bar = Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10, amount=1000)
    asset = Asset(asset_id="A", code="510300", name="沪深300ETF", lot_size=1)
    state = PortfolioState(cash=1000)
    engine = ExecutionEngine(
        ExecutionConfig(
            fee_profile=FeeProfile(rate=0.0),
            slippage_bps=2.0,
            participation_impact={
                "enabled": True,
                "free_participation_rate": 0.0,
                "impact_bps_per_1pct": 5.0,
                "max_impact_bps": 100.0,
            },
        )
    )

    _, trades = engine.apply_target(date(2024, 1, 1), state, {"A": asset}, {"A": bar}, TargetPortfolio({"A": 0.5}))

    assert trades[0].price > 10.002


def test_slippage_scenarios_apply_required_execution_configs():
    base = {"platform": {"run_name": "x"}, "execution": {"fee": {"rate": 0.0}}}

    for scenario in REQUIRED_SLIPPAGE_SCENARIOS:
        cfg = apply_slippage_scenario(base, scenario)
        assert cfg["execution"]["slippage_scenario"] == scenario
        assert "default_bps" in cfg["execution"]["slippage"]
        assert cfg["platform"]["run_name"].endswith(f"_{scenario}")


def test_execution_rejects_price_limits_and_suspension():
    asset = Asset(asset_id="A", code="A", name="A", lot_size=1)
    state = PortfolioState(cash=1000)
    engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile(rate=0.0)))

    suspended = Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10, is_suspended=True)
    orders, trades = engine.apply_target(date(2024, 1, 1), state, {"A": asset}, {"A": suspended}, TargetPortfolio({"A": 1.0}))
    assert orders[0].status == "REJECTED"
    assert orders[0].reason == "suspended"
    assert not trades

    limit_up = Bar(date=date(2024, 1, 2), asset_id="A", open=11, high=11, low=11, close=11, limit_up=11, is_suspended=False)
    orders, trades = engine.apply_target(date(2024, 1, 2), state, {"A": asset}, {"A": limit_up}, TargetPortfolio({"A": 1.0}))
    assert orders[-1].reason == "limit_up"
    assert not trades

    state.position("A").quantity = 10
    state.cash = 0
    limit_down = Bar(date=date(2024, 1, 3), asset_id="A", open=9, high=9, low=9, close=9, limit_down=9, is_suspended=False)
    orders, trades = engine.apply_target(date(2024, 1, 3), state, {"A": asset}, {"A": limit_down}, TargetPortfolio({"A": 0.0}))
    assert orders[-1].reason == "limit_down"
    assert not trades


def test_pending_retry_does_not_liquidate_filled_positions():
    assets = {
        "A": Asset(asset_id="A", code="A", name="A", lot_size=1),
        "B": Asset(asset_id="B", code="B", name="B", lot_size=1),
    }
    state = PortfolioState(cash=1000)
    engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile(rate=0.0), weight_tolerance=0.0001, slippage_bps=0.0))

    day1_bars = {
        "A": Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10),
        "B": Bar(date=date(2024, 1, 1), asset_id="B", open=10, high=10, low=10, close=10, is_suspended=True),
    }
    orders, trades = engine.apply_target(
        date(2024, 1, 1),
        state,
        assets,
        day1_bars,
        TargetPortfolio({"A": 0.5, "B": 0.5}),
    )
    assert [(order.asset_id, order.status) for order in orders] == [("A", "FILLED"), ("B", "REJECTED")]
    assert len(trades) == 1
    assert state.position("A").quantity == 50
    assert state.pending_intents["B"].target_weight == 0.5

    pending_target = TargetPortfolio({asset_id: intent.target_weight for asset_id, intent in state.pending_intents.items()})
    day2_bars = {
        "A": Bar(date=date(2024, 1, 2), asset_id="A", open=10, high=10, low=10, close=10),
        "B": Bar(date=date(2024, 1, 2), asset_id="B", open=10, high=10, low=10, close=10),
    }
    orders, trades = engine.apply_target(
        date(2024, 1, 2),
        state,
        assets,
        day2_bars,
        pending_target,
        close_absent_positions=False,
    )

    assert [(order.asset_id, order.side, order.status) for order in orders] == [("B", "BUY", "FILLED")]
    assert len(trades) == 1
    assert state.position("A").quantity == 50
    assert state.position("B").quantity == 50
    assert state.pending_intents == {}


def test_unfilled_policy_cancel_and_mark_failed():
    asset = Asset(asset_id="A", code="A", name="A", lot_size=1)
    suspended = Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10, is_suspended=True)

    cancel_state = PortfolioState(cash=1000)
    cancel_engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile(rate=0.0), unfilled_policy="cancel", slippage_bps=0.0))
    orders, trades = cancel_engine.apply_target(date(2024, 1, 1), cancel_state, {"A": asset}, {"A": suspended}, TargetPortfolio({"A": 1.0}))
    assert orders[0].status == "REJECTED"
    assert not trades
    assert cancel_state.pending_intents == {}
    assert "_execution_failed_intents" not in cancel_state.strategy_state

    failed_state = PortfolioState(cash=1000)
    failed_engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile(rate=0.0), unfilled_policy="mark_failed", slippage_bps=0.0))
    orders, trades = failed_engine.apply_target(date(2024, 1, 1), failed_state, {"A": asset}, {"A": suspended}, TargetPortfolio({"A": 1.0}))
    assert orders[0].status == "REJECTED"
    assert not trades
    assert failed_state.pending_intents == {}
    assert failed_state.strategy_state["_execution_failed_intents"] == [
        {"asset_id": "A", "target_weight": 1.0, "date": "2024-01-01", "reason": "suspended"}
    ]


def test_execution_skips_below_lot_residual_without_pending():
    asset = Asset(asset_id="A", code="A", name="A", lot_size=100)
    state = PortfolioState(cash=50)
    state.position("A").quantity = 100
    bar = Bar(date=date(2024, 1, 1), asset_id="A", open=10, high=10, low=10, close=10)
    engine = ExecutionEngine(
        ExecutionConfig(
            fee_profile=FeeProfile(rate=0.0),
            weight_tolerance=0.0001,
            skip_below_lot=True,
            slippage_bps=0.0,
        )
    )

    orders, trades = engine.apply_target(
        date(2024, 1, 1),
        state,
        {"A": asset},
        {"A": bar},
        TargetPortfolio({"A": 1.0}),
    )

    assert orders == []
    assert trades == []
    assert state.pending_intents == {}


def test_execution_skips_buy_when_cash_cannot_cover_one_lot_without_pending():
    asset = Asset(asset_id="A", code="A", name="A", lot_size=100)
    held_asset = Asset(asset_id="B", code="B", name="B", lot_size=100)
    state = PortfolioState(cash=50)
    state.position("B").quantity = 1000
    state.pending_intents["A"] = PendingIntent(
        asset_id="A",
        target_weight=0.5,
        created_date=date(2024, 1, 1),
        signal_date=date(2024, 1, 1),
    )
    bars = {
        "A": Bar(date=date(2024, 1, 2), asset_id="A", open=10, high=10, low=10, close=10),
        "B": Bar(date=date(2024, 1, 2), asset_id="B", open=10, high=10, low=10, close=10),
    }
    engine = ExecutionEngine(
        ExecutionConfig(
            fee_profile=FeeProfile(rate=0.0),
            weight_tolerance=0.0001,
            skip_below_lot=True,
            slippage_bps=0.0,
        )
    )
    skipped_orders = []

    orders, trades = engine.apply_target(
        date(2024, 1, 2),
        state,
        {"A": asset, "B": held_asset},
        bars,
        TargetPortfolio({"A": 0.5}),
        close_absent_positions=False,
        skipped_orders=skipped_orders,
    )

    assert orders == []
    assert trades == []
    assert state.pending_intents == {}
    assert len(skipped_orders) == 1
    assert skipped_orders[0].status == "SKIPPED"
    assert skipped_orders[0].reason == "below_lot_or_cash"


def test_execution_cash_buffer_and_gap_priority():
    assets = {
        "BOND": Asset(asset_id="BOND", code="BOND", name="Bond", lot_size=100),
        "ETF": Asset(asset_id="ETF", code="ETF", name="ETF", lot_size=100),
    }
    bars = {
        "BOND": Bar(date=date(2024, 1, 1), asset_id="BOND", open=100, high=100, low=100, close=100),
        "ETF": Bar(date=date(2024, 1, 1), asset_id="ETF", open=10, high=10, low=10, close=10),
    }
    state = PortfolioState(cash=100000)
    engine = ExecutionEngine(
        ExecutionConfig(
            fee_profile=FeeProfile(rate=0.0),
            cash_buffer_pct=0.01,
            order_priority="target_gap_desc",
            slippage_bps=0.0,
        )
    )

    orders, trades = engine.apply_target(
        date(2024, 1, 1),
        state,
        assets,
        bars,
        TargetPortfolio({"ETF": 0.1, "BOND": 0.9}),
    )

    assert [order.asset_id for order in orders] == ["BOND", "ETF"]
    assert all(order.status == "FILLED" for order in orders)
    assert state.cash >= 1000
    assert sum(trade.trade_value for trade in trades) <= 99000


def test_strategy_version_delete_is_blocked_when_referenced(tmp_path: Path):
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        version_id = store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"x": 1})
        store.record_backtest("run_1", {"x": 1}, tmp_path / "out")
        store.add_strategy_reference(version_id, "backtest", "1")
        with pytest.raises(ValueError):
            store.delete_strategy_version(version_id)
    finally:
        store.close()


def test_in_memory_store_operations():
    store = InMemoryStore()
    version_id = store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"x": 1})
    assert version_id == 1
    
    # Check idempotency
    version_id_2 = store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"x": 1})
    assert version_id_2 == 1
    
    backtest_id = store.record_backtest("run_1", {"x": 1}, "out_dir")
    assert backtest_id == 1
    
    store.add_strategy_reference(version_id, "backtest", str(backtest_id))
    
    version_data = store.get_strategy_version(version_id)
    assert version_data["name"] == "monthly_equal_weight"
    
    with pytest.raises(ValueError):
        store.delete_strategy_version(version_id)


def test_platform_backtest_outputs_and_checkpoint_resume(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "AAA,2024-01-29,10,10,10,10,1000,10000,1",
                "AAA,2024-01-30,10,10,10,10,1000,10000,1",
                "AAA,2024-01-31,10,10,10,10,1000,10000,1",
                "AAA,2024-02-01,10,10,10,10,1000,10000,1",
            ]
        ),
        encoding="utf-8",
    )
    config = {
        "platform": {"run_name": "test"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": 0.1}],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {"start_date": "2024-01-29", "end_date": "2024-02-01", "enable_checkpoints": True},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
                    "strategy_version_id": None,
                    "params": {"universe": ["A"], "rebalance_on_start": True},
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
        reference_count = store.conn.execute("SELECT COUNT(*) AS count FROM strategy_references").fetchone()["count"]
    finally:
        store.close()

    expected_files = [
        "manifest.json",
        "config_snapshot.yaml",
        "nav.csv",
        "positions.csv",
        "orders.csv",
        "skipped_orders.csv",
        "trades.csv",
        "report.md",
    ]
    for name in expected_files:
        assert (result.output_dir / name).exists()
    checkpoint_path = result.output_dir / "checkpoints" / "2024-01-31.json"
    assert checkpoint_path.exists()
    checkpoint = load_checkpoint(checkpoint_path)
    assert checkpoint.last_date == date(2024, 1, 31)
    assert checkpoint.position("A").quantity > 0

    manifest = json.loads((result.output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["engine"] == "platform_core.daily_event"
    assert reference_count == 1


def test_platform_backtest_executes_signal_next_day_at_open(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "AAA,2024-01-02,10,10,10,10,1000,10000,1",
                "AAA,2024-01-03,10,14,10,14,1000,12000,1",
                "AAA,2024-01-04,20,20,20,20,1000,20000,1",
            ]
        ),
        encoding="utf-8",
    )
    config = {
        "platform": {"run_name": "next_day_open"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {"start_date": "2024-01-02", "end_date": "2024-01-04"},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001, "execution_price_field": "open"},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
                    "strategy_version_id": None,
                    "params": {"universe": ["A"], "rebalance_on_start": True},
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    with (result.output_dir / "orders.csv").open(newline="", encoding="utf-8") as handle:
        orders = list(csv.DictReader(handle))
    with (result.output_dir / "trades.csv").open(newline="", encoding="utf-8") as handle:
        trades = list(csv.DictReader(handle))

    assert len(orders) == 1
    assert len(trades) == 1
    assert orders[0]["date"] == "2024-01-03"
    assert orders[0]["signal_date"] == "2024-01-02"
    assert trades[0]["date"] == "2024-01-03"
    assert trades[0]["signal_date"] == "2024-01-02"
    assert float(trades[0]["price"]) == pytest.approx(10.002)
    assert float(trades[0]["quantity"]) == pytest.approx(99.0)


def _split_config(tmp_path: Path, data_dir: Path, splits_csv: Path, universe: list[str], assets: list[dict], end_date: str) -> dict:
    return {
        "platform": {"run_name": "split_test"},
        "data": {"data_dir": str(data_dir), "splits_csv": str(splits_csv)},
        "assets": assets,
        "portfolio": {"initial_cash": 10000.0, "initial_equity": 10000.0, "initial_positions": []},
        "backtest": {"start_date": "2024-01-02", "end_date": end_date},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
            "strategy_version_id": None,
            "params": {"universe": universe, "rebalance_on_start": True},
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }


def _read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_split_on_suspended_date_applies_on_resumption_without_nav_spike(tmp_path: Path):
    """512890 型：拆分基准日停牌（无行情行），复牌日价格减半。

    旧逻辑在基准日把份额翻倍、却用停牌前向填充的旧价估值，产生单日净值假尖峰；
    现在拆分应在复牌日（首个真实 bar）生效，净值全程连续。
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # AAA 在 2024-01-04（拆分基准日）停牌缺行，2024-01-05 复牌价减半
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "AAA,2024-01-02,10,10,10,10,1000,10000,1",
                "AAA,2024-01-03,10,10,10,10,1000,10000,1",
                "AAA,2024-01-05,5,5,5,5,2000,10000,1",
                "AAA,2024-01-08,5,5,5,5,2000,10000,1",
            ]
        ),
        encoding="utf-8",
    )
    # BBB 每天都有行情，保证 2024-01-04 在交易日历里（复现真实组合场景）
    (data_dir / "BBB.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "BBB,2024-01-02,10,10,10,10,1000,10000,1",
                "BBB,2024-01-03,10,10,10,10,1000,10000,1",
                "BBB,2024-01-04,10,10,10,10,1000,10000,1",
                "BBB,2024-01-05,10,10,10,10,1000,10000,1",
                "BBB,2024-01-08,10,10,10,10,1000,10000,1",
            ]
        ),
        encoding="utf-8",
    )
    splits_csv = tmp_path / "splits.csv"
    splits_csv.write_text(
        "code,split_date,split_ratio\nAAA,2024-01-04,2.0\n",
        encoding="utf-8",
    )
    assets = [
        {"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None},
        {"asset_id": "B", "code": "BBB", "name": "BBB", "lot_size": 1, "price_limit_pct": None},
    ]
    config = _split_config(tmp_path, data_dir, splits_csv, ["A", "B"], assets, "2024-01-08")
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    nav_rows = _read_rows(result.output_dir / "nav.csv")
    values = [float(row["net_value"]) for row in nav_rows]
    daily_moves = [abs(b / a - 1.0) for a, b in zip(values, values[1:])]
    assert max(daily_moves) < 0.01, f"净值出现拆分假尖峰: {values}"

    position_rows = _read_rows(result.output_dir / "positions.csv")
    qty_by_date = {row["date"]: float(row["quantity"]) for row in position_rows if row["asset_id"] == "A"}
    # 基准日（停牌）数量不变，复牌日翻倍
    assert qty_by_date["2024-01-04"] == pytest.approx(qty_by_date["2024-01-03"])
    assert qty_by_date["2024-01-05"] == pytest.approx(qty_by_date["2024-01-03"] * 2.0)


def test_split_on_traded_but_unadjusted_date_applies_next_bar(tmp_path: Path):
    """510500 型：拆分基准日有成交但价格仍未除权，次日才除权。

    拆分应在基准日之后的首个真实 bar（次日）生效，而不是基准日当天。
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "AAA,2024-01-02,10,10,10,10,1000,10000,1",
                "AAA,2024-01-03,10,10,10,10,1000,10000,1",
                "AAA,2024-01-04,10,10,10,10,1000,10000,1",
                "AAA,2024-01-05,5,5,5,5,2000,10000,1",
                "AAA,2024-01-08,5,5,5,5,2000,10000,1",
            ]
        ),
        encoding="utf-8",
    )
    splits_csv = tmp_path / "splits.csv"
    splits_csv.write_text(
        "code,split_date,split_ratio\nAAA,2024-01-04,2.0\n",
        encoding="utf-8",
    )
    assets = [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}]
    config = _split_config(tmp_path, data_dir, splits_csv, ["A"], assets, "2024-01-08")
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    nav_rows = _read_rows(result.output_dir / "nav.csv")
    values = [float(row["net_value"]) for row in nav_rows]
    daily_moves = [abs(b / a - 1.0) for a, b in zip(values, values[1:])]
    assert max(daily_moves) < 0.01, f"净值出现拆分假尖峰: {values}"

    position_rows = _read_rows(result.output_dir / "positions.csv")
    qty_by_date = {row["date"]: float(row["quantity"]) for row in position_rows if row["asset_id"] == "A"}
    assert qty_by_date["2024-01-04"] == pytest.approx(qty_by_date["2024-01-03"])
    assert qty_by_date["2024-01-05"] == pytest.approx(qty_by_date["2024-01-03"] * 2.0)


def test_historical_split_before_backtest_window_is_not_reapplied(tmp_path: Path):
    """拆分真实生效日早于回测窗口时，不应漂移到窗口首日重复应用。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor",
                "AAA,2024-01-03,10,10,10,10,1000,10000,1",
                "AAA,2024-01-05,5,5,5,5,2000,10000,1",
                "AAA,2024-01-08,5,5,5,5,2000,10000,1",
                "AAA,2024-01-09,5,5,5,5,2000,10000,1",
            ]
        ),
        encoding="utf-8",
    )
    splits_csv = tmp_path / "splits.csv"
    splits_csv.write_text(
        "code,split_date,split_ratio\nAAA,2024-01-04,2.0\n",
        encoding="utf-8",
    )
    assets = [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}]
    config = _split_config(tmp_path, data_dir, splits_csv, ["A"], assets, "2024-01-09")
    config["backtest"]["start_date"] = "2024-01-08"
    config["portfolio"]["initial_cash"] = 0.0
    config["portfolio"]["initial_equity"] = 500.0
    config["portfolio"]["initial_positions"] = [{"asset_id": "A", "quantity": 100.0, "cost_basis": 5.0}]

    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    position_rows = _read_rows(result.output_dir / "positions.csv")
    qty_by_date = {row["date"]: float(row["quantity"]) for row in position_rows if row["asset_id"] == "A"}
    assert qty_by_date["2024-01-08"] == pytest.approx(100.0)
    assert qty_by_date["2024-01-09"] == pytest.approx(100.0)


def test_platform_backtest_uses_full_data_when_dates_are_omitted(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "trade_date,open,high,low,close,volume,amount,adjust_factor,source,updated_at",
                "2024-01-02,10,10,10,10,1000,10000,1,csv,now",
                "2024-01-03,10,10,10,10,1000,10000,1,csv,now",
                "2024-01-04,10,10,10,10,1000,10000,1,csv,now",
            ]
        ),
        encoding="utf-8",
    )
    config = {
        "platform": {"run_name": "no_dates"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
                    "strategy_version_id": None,
                    "params": {"universe": ["A"], "rebalance_on_start": True},
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    assert result.metrics["start_date"] == "2024-01-02"
    assert result.metrics["end_date"] == "2024-01-04"
    assert result.metrics["trade_count"] > 0


def test_platform_backtest_rejects_legacy_strategy_segments(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "trade_date,open,high,low,close,volume,amount,adjust_factor,source,updated_at",
                "2024-01-02,10,10,10,10,1000,10000,1,csv,now",
            ]
        ),
        encoding="utf-8",
    )
    config = {
        "platform": {"run_name": "legacy_segments"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategies": {
            "segments": [
                {
                    "strategy_name": "monthly_equal_weight",
                    "params": {"universe": ["A"], "rebalance_on_start": True},
                }
            ]
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        with pytest.raises(ValueError, match="single `strategy` mapping"):
            PlatformBacktestEngine(config, store)
    finally:
        store.close()


class DummySource:
    def fetch_bars(self, code, start=None, end=None, adjust=None):
        return __import__("pandas").DataFrame(
            [
                {
                    "trade_date": "2024-01-01",
                    "open_price": 10,
                    "high_price": 11,
                    "low_price": 9,
                    "close_price": 10,
                    "volume": 100,
                    "amount": 1000,
                    "adjust_factor": 1,
                }
            ]
        )


def test_platform_risk_parity_strategy_runs(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = {
        "AAA": [10, 10.1, 10.2, 10.4, 10.3],
        "BBB": [20, 19.9, 20.1, 20.0, 20.2],
        "CCC": [30, 30.3, 30.2, 30.1, 30.4],
    }
    dates = ["2024-03-27", "2024-03-28", "2024-03-29", "2024-04-01", "2024-04-02"]
    for code, closes in rows.items():
        lines = ["trade_date,open,high,low,close,volume,amount,adjust_factor,source,updated_at"]
        for date_value, close in zip(dates, closes):
            lines.append(f"{date_value},{close},{close},{close},{close},1000,{close * 1000},1,csv,now")
        (data_dir / f"{code}.csv").write_text("\n".join(lines), encoding="utf-8")

    config = {
        "platform": {"run_name": "risk_parity"},
        "data": {"data_dir": str(data_dir)},
        "assets": [
            {"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": 0.1},
            {"asset_id": "B", "code": "BBB", "name": "BBB", "lot_size": 1, "price_limit_pct": 0.1},
            {"asset_id": "C", "code": "CCC", "name": "CCC", "lot_size": 1, "price_limit_pct": 0.1},
        ],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {"start_date": "2024-03-27", "end_date": "2024-04-02"},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "risk_parity",
                    "strategy_version_id": None,
                    "params": {
                        "universe": ["A", "B", "C"],
                        "rolling_window": 3,
                        "min_periods": 2,
                        "init_mode": "calculate",
                        "init_calc_days": 2,
                        "rebalance_threshold": 0.05,
                    },
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    trades = (result.output_dir / "trades.csv").read_text(encoding="utf-8")
    assert "trade_id" in trades
    assert result.metrics["trade_count"] > 0


def test_platform_risk_parity_ewma_strategy_runs(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = {
        "AAA": [10, 10.1, 10.2, 10.4, 10.3],
        "BBB": [20, 19.9, 20.1, 20.0, 20.2],
        "CCC": [30, 30.3, 30.2, 30.1, 30.4],
    }
    dates = ["2024-03-27", "2024-03-28", "2024-03-29", "2024-04-01", "2024-04-02"]
    for code, closes in rows.items():
        lines = ["trade_date,open,high,low,close,volume,amount,adjust_factor,source,updated_at"]
        for date_value, close in zip(dates, closes):
            lines.append(f"{date_value},{close},{close},{close},{close},1000,{close * 1000},1,csv,now")
        (data_dir / f"{code}.csv").write_text("\n".join(lines), encoding="utf-8")

    config = {
        "platform": {"run_name": "risk_parity_ewma"},
        "data": {"data_dir": str(data_dir)},
        "assets": [
            {"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": 0.1},
            {"asset_id": "B", "code": "BBB", "name": "BBB", "lot_size": 1, "price_limit_pct": 0.1},
            {"asset_id": "C", "code": "CCC", "name": "CCC", "lot_size": 1, "price_limit_pct": 0.1},
        ],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {"start_date": "2024-03-27", "end_date": "2024-04-02"},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "risk_parity_ewma",
                    "strategy_version_id": None,
                    "params": {
                        "universe": ["A", "B", "C"],
                        "ewma_span": 3,
                        "ewma_min_periods": 2,
                        "init_mode": "calculate",
                        "init_calc_days": 2,
                        "rebalance_threshold": 0.05,
                    },
        },
        "output": {"results_dir": str(tmp_path / "results")},
    }
    store = SQLiteStore(tmp_path / "platform.sqlite3")
    try:
        result = PlatformBacktestEngine(config, store).run()
    finally:
        store.close()

    assert get_strategy_class("risk_parity_ewma").name == "risk_parity_ewma"
    assert result.metrics["trade_count"] > 0


def test_platform_metrics_and_visualization_from_artifacts(tmp_path: Path):
    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "nav.csv").write_text(
        "\n".join(
            [
                "date,net_value,total_value,cash,pending_intent_count,strategy_version_id",
                "2024-01-01,1.0,1000,100,0,1",
                "2024-01-02,1.1,1100,50,1,1",
                "2024-01-03,1.05,1050,75,0,1",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "positions.csv").write_text(
        "\n".join(
            [
                "date,asset_id,quantity,price,market_value,weight,cost_basis",
                "2024-01-01,A,90,10,900,0.9,10",
                "2024-01-02,A,105,10,1050,0.9545,10",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "orders.csv").write_text(
        "\n".join(
            [
                "order_id,date,asset_id,side,quantity,price,trade_value,status,reason,target_weight",
                "O1,2024-01-01,A,BUY,90,10,900,FILLED,,1",
                "O2,2024-01-02,B,BUY,10,10,100,REJECTED,limit_up,0.1",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "skipped_orders.csv").write_text(
        "\n".join(
            [
                "order_id,date,asset_id,side,quantity,price,trade_value,status,reason,target_weight",
                "S1,2024-01-02,C,BUY,0,10,0,SKIPPED,below_lot_or_cash,0.1",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "trades.csv").write_text(
        "trade_id,order_id,date,asset_id,side,quantity,price,trade_value,fee,cash_after\n"
        "T1,O1,2024-01-01,A,BUY,90,10,900,0,100\n",
        encoding="utf-8",
    )

    metrics = build_platform_metrics(result_dir)
    assert metrics["trade_count"] == 1
    assert metrics["rejected_order_count"] == 1
    assert metrics["skipped_order_count"] == 1
    assert metrics["skipped_below_lot_or_cash_count"] == 1
    assert metrics["rejection_reason_counts"]["limit_up"] == 1
    assert metrics["skipped_reason_counts"]["below_lot_or_cash"] == 1
    paths = render_platform_charts(result_dir)
    assert paths
    assert all(path.exists() for path in paths)


def test_platform_metrics_reports_training_and_oos_slices(tmp_path: Path):
    result_dir = tmp_path / "result_oos"
    result_dir.mkdir()
    (result_dir / "nav.csv").write_text(
        "\n".join(
            [
                "date,net_value,total_value,cash,pending_intent_count,strategy_version_id",
                "2025-06-30,1.0,1000,100,0,1",
                "2025-07-01,1.1,1100,50,1,1",
                "2025-07-02,1.2,1200,60,0,1",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "positions.csv").write_text(
        "\n".join(
            [
                "date,asset_id,quantity,price,market_value,weight,cost_basis",
                "2025-06-30,A,90,10,900,0.9,10",
                "2025-07-01,A,105,10,1050,0.9545,10",
                "2025-07-02,A,114,10,1140,0.95,10",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "orders.csv").write_text(
        "\n".join(
            [
                "order_id,date,asset_id,side,quantity,price,trade_value,status,reason,target_weight",
                "O1,2025-07-01,A,BUY,10,10,100,FILLED,,1",
            ]
        ),
        encoding="utf-8",
    )
    (result_dir / "skipped_orders.csv").write_text("", encoding="utf-8")
    (result_dir / "trades.csv").write_text(
        "trade_id,order_id,date,asset_id,side,quantity,price,trade_value,fee,cash_after,valuation_price\n"
        "T1,O1,2025-07-01,A,BUY,10,10,100,0,50,10\n",
        encoding="utf-8",
    )

    metrics = build_platform_metrics(result_dir)

    assert not metrics["training_metrics_available"]
    assert metrics["oos_metrics_available"]
    assert metrics["training_metrics"]["observations"] == 1
    assert metrics["oos_metrics"]["observations"] == 2
    assert metrics["oos_metrics"]["trade_count"] == 1


def test_hfq_validation_matches_research_chain(tmp_path: Path):
    research_dir = tmp_path / "research_data"
    platform_dir = tmp_path / "platform_data"
    research_dir.mkdir()
    platform_dir.mkdir()
    price_csv = "\n".join(
        [
            "trade_date,close_price",
            "2024-01-01,10",
            "2024-01-02,11",
        ]
    )
    factor_csv = "\n".join(
        [
            "trade_date,hfq_factor",
            "2024-01-01,2",
            "2024-01-02,2",
        ]
    )
    (research_dir / "AAA.csv").write_text(price_csv, encoding="utf-8")
    (research_dir / "AAA_hfq_factor.csv").write_text(factor_csv, encoding="utf-8")
    (platform_dir / "AAA.csv").write_text(price_csv, encoding="utf-8")
    (platform_dir / "AAA_hfq_factor.csv").write_text(factor_csv, encoding="utf-8")

    detail, summary = compare_hfq_data(["AAA"], research_dir, platform_dir)
    assert summary["rows"][0]["common_observations"] == 2
    assert summary["rows"][0]["max_abs_diff"] == 0.0
    assert detail["platform_close"].tolist() == [20, 22]


def test_platform_experiment_runner_writes_standard_report(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "AAA.csv").write_text(
        "\n".join(
            [
                "trade_date,open,high,low,close,volume,amount,adjust_factor,source,updated_at",
                "2024-01-29,10,10,10,10,1000,10000,1,csv,now",
                "2024-01-30,10,10,10,10,1000,10000,1,csv,now",
                "2024-01-31,11,11,11,11,1000,11000,1,csv,now",
            ]
        ),
        encoding="utf-8",
    )
    config = {
        "platform": {"run_name": "experiment_test"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "AAA", "lot_size": 1, "price_limit_pct": None}],
        "portfolio": {"initial_cash": 1000.0, "initial_equity": 1000.0, "initial_positions": []},
        "backtest": {},
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
                    "strategy_version_id": None,
                    "params": {"universe": ["A"], "rebalance_on_start": True},
        },
        "output": {"results_dir": str(tmp_path / "unused")},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(__import__("yaml").safe_dump(config), encoding="utf-8")

    result = run_platform_experiment(
        candidate_config_path=config_path,
        baseline_config_path=config_path,
        db_path=tmp_path / "platform.sqlite3",
        raw_root=tmp_path / "raw",
        report_root=tmp_path / "reports",
        render_charts=False,
        start_date="2024-01-30",
        end_date="2024-01-31",
    )

    assert result.metrics_path.exists()
    assert result.report_path.exists()
    payload = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert payload["candidate"]["start_date"] == "2024-01-30"
    assert payload["candidate"]["end_date"] == "2024-01-31"
    assert payload["baseline"]["start_date"] == "2024-01-30"
    assert payload["baseline"]["end_date"] == "2024-01-31"
    assert payload["candidate"]["trade_count"] > 0
    assert payload["baseline"]["trade_count"] > 0
    assert "sharpe_ratio_delta" in payload["comparison"]
