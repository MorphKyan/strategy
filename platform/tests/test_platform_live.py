from __future__ import annotations

import csv
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.platform_core import notify as notify_module
from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.live import LivePortfolio, PlanResult
from src.platform_core.models import PortfolioState, TargetPortfolio, parse_date
from src.platform_core.notify import resolve_channels, send_notification
from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import InMemoryStore
from src.platform_core.strategies.expected_shortfall import RiskParityExpectedShortfallFixedBudgetStrategy
from src.platform_core.strategy import StrategyContext


def _write_market_data(
    data_dir: Path,
    closes: dict[str, dict[str, float]] | None = None,
    opens: dict[str, dict[str, float]] | None = None,
) -> None:
    """closes / opens: code -> {date: price}，缺省 OHLC 同价为 10。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    header = "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor"
    dates = ["2024-01-29", "2024-01-30", "2024-01-31"]
    for code in ("AAA", "BBB"):
        rows = [header]
        for d in dates:
            close = (closes or {}).get(code, {}).get(d, 10)
            open_price = (opens or {}).get(code, {}).get(d, close)
            rows.append(f"{code},{d},{open_price},{close},{open_price},{close},1000,10000,1")
        (data_dir / f"{code}.csv").write_text("\n".join(rows), encoding="utf-8")


def _live_config(data_dir: Path) -> dict:
    return {
        "platform": {"run_name": "live_test"},
        "data": {"data_dir": str(data_dir)},
        "assets": [
            {"asset_id": "A", "code": "AAA", "name": "资产A", "lot_size": 100, "price_limit_pct": None},
            {"asset_id": "B", "code": "BBB", "name": "资产B", "lot_size": 100, "price_limit_pct": None},
        ],
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "monthly_equal_weight",
            "strategy_version_id": None,
            "params": {"universe": ["A", "B"], "rebalance_on_start": True},
        },
    }


def _write_holdings(path: Path, rows: list[str]) -> Path:
    path.write_text("\n".join(["code,quantity,cost_basis", *rows]), encoding="utf-8")
    return path


def _make_portfolio(tmp_path: Path) -> LivePortfolio:
    data_dir = tmp_path / "data"
    _write_market_data(data_dir)
    return LivePortfolio("live_test", _live_config(data_dir), output_root=tmp_path / "live")


def _with_dividend(portfolio: LivePortfolio, tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    path.write_text("code,record_date,ex_date,payment_date,dividend_per_share\n"
                    "AAA,2024-01-29,2024-01-30,2024-01-31,0.1\n", encoding="utf-8")
    portfolio.config["live"] = {"dividends_path": str(path)}


def test_live_dividend_accrual_payment_and_repeat(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    _write_market_data(tmp_path / "data", closes={"AAA": {"2024-01-30": 9.9, "2024-01-31": 9.9}})
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-29")
    ex = portfolio.mark_to_market("2024-01-30")
    assert ex["cash"] == 7000
    assert ex["total_value"] == pytest.approx(10000)
    assert ex["realized_pnl"] == pytest.approx(30)
    assert not ex["realized_residual_alert"]
    # 重启后到账，重跑不重复加现金。
    portfolio = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live")
    for _ in range(2):
        payment = portfolio.mark_to_market("2024-01-31")
        assert payment["cash"] == 7030
        assert payment["total_value"] == pytest.approx(10000)
        assert not portfolio._load_state().dividend_receivables


def test_live_dividend_catches_up_and_plan_uses_cash(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-29")
    portfolio.plan("2024-01-31")
    assert portfolio._load_state().cash == 7030
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 7030


def test_live_dividend_record_holdings_survive_sale_and_reconcile(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-29")
    # 登记后卖光仍有权益；真实现金对账不抹掉应收。
    empty = _write_holdings(tmp_path / "empty.csv", [])
    portfolio.reconcile(empty, cash=9970, asof_date="2024-01-30")
    assert portfolio.mark_to_market("2024-01-30")["total_value"] == pytest.approx(10000)
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 10000
    portfolio.reconcile(empty, cash=10000, asof_date="2024-01-31")
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 10000


def test_live_dividend_existing_cash_snapshot_not_credited_again(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7030, asof_date="2024-01-31")
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 7030


def test_live_dividend_buyer_after_record_has_no_entitlement(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    empty = _write_holdings(tmp_path / "empty.csv", [])
    portfolio.reconcile(empty, cash=10000, asof_date="2024-01-29")
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-30")
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 7000


def test_live_dividend_same_day_record_uses_reconciled_holdings(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    _with_dividend(portfolio, tmp_path)
    path = Path(portfolio.config["live"]["dividends_path"])
    path.write_text(path.read_text().replace("2024-01-29,2024-01-30", "2024-01-30,2024-01-30"))
    empty = _write_holdings(tmp_path / "empty.csv", [])
    portfolio.reconcile(empty, cash=10000, asof_date="2024-01-29")
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-30")
    assert portfolio.mark_to_market("2024-01-31")["cash"] == 7030


def test_reconcile_overwrites_state_and_appends_real_nav(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,9.5"])

    result = portfolio.reconcile(holdings, cash=7000.0, asof_date="2024-01-30")

    assert result.positions_value == pytest.approx(3000.0)
    assert result.total_value == pytest.approx(10000.0)
    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert state["cash"] == pytest.approx(7000.0)
    assert state["positions"]["A"]["quantity"] == pytest.approx(300.0)
    assert state["positions"]["A"]["cost_basis"] == pytest.approx(9.5)
    assert state["pending_intents"] == {}
    assert state["last_date"] == "2024-01-30"

    # 同日重复 reconcile 应替换 real_nav 行而不是追加重复行
    portfolio.reconcile(holdings, cash=6000.0, asof_date="2024-01-30")
    with portfolio.real_nav_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert float(rows[0]["total_value"]) == pytest.approx(9000.0)


def test_reconcile_rejects_unknown_code(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["CCC,100,"])
    with pytest.raises(ValueError, match="CCC"):
        portfolio.reconcile(holdings, cash=1000.0, asof_date="2024-01-30")


@pytest.mark.parametrize("holdings,cash,flow", [
    (["AAA,nan,10"], 1000, 0),
    (["AAA,100,inf"], 1000, 0),
    (["AAA,100,10"], float("nan"), 0),
    (["AAA,100,10"], 1000, float("inf")),
    (["AAA,-100,10"], 1000, 0),
    (["AAA,100,-10"], 1000, 0),
    (["AAA,100,10", "AAA,200,10"], 1000, 0),
])
def test_invalid_reconcile_input_does_not_overwrite_account(tmp_path: Path, holdings, cash, flow):
    portfolio = _make_portfolio(tmp_path)
    path = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(path, cash=7000, asof_date="2024-01-29")
    state_before = portfolio.state_path.read_bytes()
    nav_before = portfolio.real_nav_path.read_bytes()
    _write_holdings(path, holdings)
    with pytest.raises(ValueError):
        portfolio.reconcile(path, cash=cash, asof_date="2024-01-30", external_flow=flow)
    assert portfolio.state_path.read_bytes() == state_before
    assert portfolio.real_nav_path.read_bytes() == nav_before


def test_historical_plan_does_not_rewind_latest_runtime_or_tickets(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,300,10"]), cash=7000, asof_date="2024-01-29")
    portfolio.plan("2024-01-31")
    before = portfolio.state_path.read_bytes()
    with pytest.raises(ValueError, match="历史"):
        portfolio.plan("2024-01-30")
    assert portfolio.state_path.read_bytes() == before
    assert not (portfolio.tickets_dir / "ticket_2024-01-30.txt").exists()


def test_same_day_no_op_removes_previous_order_csv(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    portfolio.strategy_config = {"strategy_name": "fixed_weight_threshold", "params": {"universe": ["A", "B"]}}
    holdings = _write_holdings(tmp_path / "h.csv", [])
    portfolio.reconcile(holdings, cash=10000, asof_date="2024-01-30")
    first = portfolio.plan("2024-01-31")
    assert first.ticket_csv.exists()
    _write_holdings(holdings, ["AAA,500,10", "BBB,500,10"])
    portfolio.reconcile(holdings, cash=0, asof_date="2024-01-31")
    repeated = portfolio.plan("2024-01-31")
    assert not repeated.has_target
    assert not first.ticket_csv.exists()


def test_amend_flow_rejects_nonfinite_value_without_writing(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", []), cash=10000, asof_date="2024-01-29")
    portfolio.mark_to_market("2024-01-30")
    before = portfolio.real_nav_path.read_bytes()
    with pytest.raises(ValueError, match="有限数"):
        portfolio.amend_flow("2024-01-30", float("nan"))
    assert portfolio.real_nav_path.read_bytes() == before


def test_plan_renders_lot_rounded_ticket_without_touching_real_state(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-30")

    # 2024-01-31 是真实月末（补出的下一工作日在 2 月）→ monthly_equal_weight 产出 A/B 各 50%
    result = portfolio.plan(asof_date="2024-01-31")

    assert result.has_target
    assert result.order_count == 2
    with result.ticket_csv.open(newline="", encoding="utf-8") as handle:
        rows = {row["asset_id"]: row for row in csv.DictReader(handle)}
    # 总值 10100：A 3000 → 5050 元，买 200 股；B 0 → 5050 元，买 500 股；均为整手（lot 100）
    assert float(rows["A"]["quantity"]) == pytest.approx(200.0)
    assert float(rows["B"]["quantity"]) == pytest.approx(500.0)
    assert all(float(row["quantity"]) % 100 == 0 for row in rows.values())
    assert rows["A"]["side"] == "BUY" and rows["B"]["side"] == "BUY"
    assert float(rows["B"]["weight_target"]) == pytest.approx(0.5)
    assert "买入" in result.text and "调仓单" in result.text

    # plan 是 dry-run：真实持仓与现金不得改变，只允许记录 pending_intents
    state = json.loads(portfolio.state_path.read_text(encoding="utf-8"))
    assert state["cash"] == pytest.approx(7100.0)
    assert state["positions"]["A"]["quantity"] == pytest.approx(300.0)
    assert "B" not in state["positions"]
    assert state["pending_intents"]["B"]["target_weight"] == pytest.approx(0.5)


def test_plan_uses_close_even_when_backtest_uses_open(tmp_path: Path):
    data_dir = tmp_path / "data"
    _write_market_data(
        data_dir,
        closes={"AAA": {"2024-01-31": 10}, "BBB": {"2024-01-31": 10}},
        opens={"AAA": {"2024-01-31": 8}, "BBB": {"2024-01-31": 9}},
    )
    config = _live_config(data_dir)
    config["execution"].update({"execution_price_field": "open", "slippage_bps": 0.0})
    portfolio = LivePortfolio("live_test", config, output_root=tmp_path / "live")
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-30")

    result = portfolio.plan(asof_date="2024-01-31")

    with result.ticket_csv.open(newline="", encoding="utf-8") as handle:
        rows = {row["asset_id"]: row for row in csv.DictReader(handle)}
    assert float(rows["A"]["est_price"]) == pytest.approx(10.0)
    assert float(rows["B"]["est_price"]) == pytest.approx(10.0)
    assert float(rows["A"]["quantity"]) == 200
    assert float(rows["B"]["quantity"]) == 500
    assert "基于 2024-01-31 收盘估算" in result.text
    assert config["execution"]["execution_price_field"] == "open"


def test_execution_config_shared_by_backtest_sim_and_live(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    config = portfolio.config
    config["execution"] = {
        "execution_price_field": "open", "fee": {"rate": 0.001, "min_fee": 5},
        "weight_tolerance": 0.02, "weight_tolerance_by_asset_id": {"A": 0.01},
        "cash_buffer_pct": 0.03, "skip_below_lot": False, "order_priority": "target_gap_desc",
        "unfilled_policy": "cancel", "round_mode": "floor", "slippage_bps": 99,
        "slippage": {
            "default_bps": 3, "qdii_commodity_bps": 8,
            "asset_bps": {"A": 4}, "code_bps": {"BBB": 7},
            "participation_impact": {"enabled": True, "impact_bps_per_1pct": 10},
        },
    }
    store = InMemoryStore()
    try:
        backtest = PlatformBacktestEngine(config, store, output_dir=tmp_path / "backtests")
        sim = SimPortfolio("sim", config, store, PortfolioState(cash=10000), tmp_path / "checkpoint",
                           output_root=tmp_path / "sim")
        live = LivePortfolio("live_test", config, output_root=tmp_path / "live")
        execution = backtest.execution.config
        assert sim.execution.config == execution
        assert live.execution.config == replace(execution, price_field="close")
        assert execution.price_field == "open"
        assert execution.slippage_bps == 3
        assert execution.participation_impact == config["execution"]["slippage"]["participation_impact"]
        assert execution.weight_tolerance_by_asset_id == {"A": 0.01}
        assert execution.fee_profile.calculate(100) == 5
    finally:
        store.close()


def _es_portfolio(tmp_path: Path, monkeypatch) -> LivePortfolio:
    portfolio = _make_portfolio(tmp_path)
    portfolio.config["strategy"] = {
        "strategy_name": RiskParityExpectedShortfallFixedBudgetStrategy.name,
        "params": {"universe": ["A", "B"], "init_calc_days": 0,
                   "rebalance_frequency": "monthly", "rebalance_threshold": 0.05},
    }
    # 隔离调度与状态恢复；ES 数值求解由 test_expected_shortfall_strategy.py 覆盖。
    monkeypatch.setattr(RiskParityExpectedShortfallFixedBudgetStrategy, "_inverse_vol_target",
                        lambda self, context, universe: TargetPortfolio({"A": 0.5, "B": 0.5}))
    return LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live")


def test_live_restarts_match_continuous_strategy_and_repeat_initial_ticket(tmp_path: Path, monkeypatch):
    portfolio = _es_portfolio(tmp_path, monkeypatch)
    portfolio.reconcile(_write_holdings(tmp_path / "empty.csv", []), cash=10000, asof_date="2024-01-29")
    data = portfolio._load_data(parse_date("2024-01-31"))
    data.calendar.append(parse_date("2024-02-01"))
    context = StrategyContext(
        date=parse_date("2024-01-29"), assets=portfolio.assets, bars={},
        state=copy.deepcopy(portfolio._load_state()), data=data,
        params=portfolio.strategy_config["params"],
    )
    strategy = RiskParityExpectedShortfallFixedBudgetStrategy()
    strategy.initialize(context)
    observed = []
    for day in ("2024-01-29", "2024-01-30", "2024-01-31"):
        context.date = parse_date(day)
        context.bars = data.bars_on(context.date)
        expected = strategy.generate_targets(context)
        portfolio = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live")
        result = portfolio.plan(day)
        observed.append(result.has_target)
        assert result.has_target == (expected is not None)
        if expected is not None:
            assert {key: intent.target_weight for key, intent in portfolio._load_state().pending_intents.items()} == expected.weights
        first_ticket = result.ticket_txt.read_bytes()
        repeated = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live").plan(day)
        assert repeated.has_target == result.has_target
        assert repeated.ticket_txt.read_bytes() == first_ticket
        assert portfolio._load_state().strategy_state["_live_strategy_runtime"]["runtime"]["opened"]
    assert observed == [True, False, True]


def test_live_legacy_holdings_bootstrap_and_reconcile_preserve_runtime(tmp_path: Path, monkeypatch):
    portfolio = _es_portfolio(tmp_path, monkeypatch)
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-29")
    assert not portfolio.plan("2024-01-29").has_target
    saved = portfolio._load_state().strategy_state["_live_strategy_runtime"]
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-30")
    assert portfolio._load_state().strategy_state["_live_strategy_runtime"] == saved
    assert not LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live").plan("2024-01-30").has_target


def test_live_config_change_does_not_restore_old_frequency(tmp_path: Path, monkeypatch):
    portfolio = _es_portfolio(tmp_path, monkeypatch)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,300,10"]), cash=7000, asof_date="2024-01-29")
    assert not portfolio.plan("2024-01-29").has_target
    portfolio.config["strategy"]["params"]["rebalance_frequency"] = "daily"
    restarted = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live")
    assert restarted.plan("2024-01-30").has_target


def test_daily_target_monitor_recomputes_below_threshold_and_uses_real_trades(tmp_path, monkeypatch):
    portfolio = _es_portfolio(tmp_path, monkeypatch)
    portfolio.config["strategy"]["params"]["rebalance_frequency"] = "daily"
    calls = []

    def calculate(self, context, universe):
        calls.append(context.date)
        weight = 0.5 if context.date.day == 29 else 0.52
        return TargetPortfolio({"A": weight, "B": 1 - weight})

    monkeypatch.setattr(RiskParityExpectedShortfallFixedBudgetStrategy, "_inverse_vol_target", calculate)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,500,10", "BBB,500,10"]),
                        cash=0, asof_date="2024-01-29")
    (portfolio.portfolio_dir / "execution_ledger.csv").write_text(
        "date,event,code,quantity\n2024-01-28,SELL,AAA,100\n2024-01-29,BUY,AAA,100\n"
        "2024-01-30,INTERNAL_TRANSFER_IN,AAA,100\n2024-01-30,DIVIDEND,AAA,0\n"
        "2024-01-30,BUY,AAA,0\n2024-01-31,BUY,AAA,100\n", encoding="utf-8")
    before = portfolio._load_state()
    for day, expected in (("2024-01-29", "50.00%"), ("2024-01-30", "52.00%")):
        restarted = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live")
        result = restarted.plan(day)
        assert not result.has_target and result.order_count == 0
        assert result.ticket_txt.exists() and result.ticket_csv is None
        assert expected in result.monitor_text and "现金" in result.monitor_text
        assert "上次调仓（有成交）：2024-01-29" in result.text
        assert "2024-01-31" not in result.text
        valuation = {"date": parse_date(day), "total_value": 10000, "cash": 0,
                     "weights": {"A": 0.5, "B": 0.5}}
        _, digest = restarted._render_daily_digest(valuation, result)
        assert result.monitor_text in digest
        after = restarted._load_state()
        assert after.cash == before.cash and after.positions == before.positions
    assert calls == [parse_date("2024-01-29"), parse_date("2024-01-30")]


def test_daily_target_ticket_and_digest_include_unknown_last_trade(tmp_path, monkeypatch):
    portfolio = _es_portfolio(tmp_path, monkeypatch)
    portfolio.config["strategy"]["params"]["rebalance_frequency"] = "daily"
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,300,10"]),
                        cash=7000, asof_date="2024-01-29")
    sent = []
    result = LivePortfolio("live_test", portfolio.config, output_root=tmp_path / "live").cycle(
        "2024-01-30", notifier=lambda title, text: sent.append(text) or True)
    assert result.plan.has_target and result.plan.order_count > 0
    assert result.plan.ticket_csv.exists()
    assert len(sent) == 2
    for message in sent:
        assert "上次调仓（有成交）：未知（无有效买卖流水）" in message
        assert "50.00%" in message
    assert portfolio._load_state().last_date == parse_date("2024-01-29")


@pytest.mark.parametrize("command", ["plan", "cycle", "reconcile", "mark_to_market"])
@pytest.mark.parametrize("empty", [False, True])
def test_live_rejects_unaligned_data_before_writing(tmp_path: Path, command: str, empty: bool):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "h.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7000, asof_date="2024-01-30")
    state_before, nav_before = portfolio.state_path.read_bytes(), portfolio.real_nav_path.read_bytes()
    path = tmp_path / "data" / "BBB.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:1] if empty else lines[:-1]), encoding="utf-8")
    with pytest.raises(RuntimeError, match="行情未对齐.*B="):
        if command == "reconcile":
            portfolio.reconcile(holdings, cash=123, asof_date="2024-01-31")
        else:
            getattr(portfolio, command)("2024-01-31")
    assert portfolio.state_path.read_bytes() == state_before
    assert portfolio.real_nav_path.read_bytes() == nav_before
    assert not portfolio.tickets_dir.exists()


def test_cycle_rechecks_alignment_after_sync(tmp_path: Path, monkeypatch):
    portfolio = _make_portfolio(tmp_path)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,300,10"]), cash=7000, asof_date="2024-01-30")
    synced = []

    def incomplete_sync(end):
        synced.append(end)
        path = tmp_path / "data" / "BBB.csv"
        path.write_text("\n".join(path.read_text().splitlines()[:-1]), encoding="utf-8")

    monkeypatch.setattr(portfolio, "_sync_data", incomplete_sync)
    with pytest.raises(RuntimeError, match="行情未对齐"):
        portfolio.cycle("2024-01-31", do_sync=True,
                        notifier=lambda *args: pytest.fail("行情未对齐时不得推送下单票"))
    assert synced == [parse_date("2024-01-31")]


def test_live_accepts_explicit_suspension_bar(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    path = tmp_path / "data" / "BBB.csv"
    path.write_text(path.read_text().replace("1000,10000", "0,0"), encoding="utf-8")
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", []), cash=10000, asof_date="2024-01-30")
    result = portfolio.plan("2024-01-31")
    with result.ticket_csv.open(newline="", encoding="utf-8") as handle:
        rows = {row["asset_id"]: row for row in csv.DictReader(handle)}
    assert "REJECTED" in rows["B"]["note"]


def test_plan_without_target_writes_no_op_ticket(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7000.0, asof_date="2024-01-29")

    # 2024-01-30 不是月末（日历下一日仍是 1 月）→ monthly_equal_weight 无目标
    result = portfolio.plan(asof_date="2024-01-30")

    assert not result.has_target
    assert result.order_count == 0
    assert result.ticket_csv is None
    assert "无操作" in result.text
    assert result.ticket_txt.exists()


def test_plan_requires_reconcile_first(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    with pytest.raises(FileNotFoundError, match="reconcile"):
        portfolio.plan(asof_date="2024-01-31")


def test_cycle_skips_non_trading_day(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-30")

    # 2024-02-01 不在行情日历里（数据止于 01-31）→ 跳过，不重复出票
    result = portfolio.cycle(asof_date="2024-02-01")

    assert result.skipped_non_trading
    assert result.plan is None and not result.reconciled and not result.notified


def test_cycle_reconciles_plans_and_notifies_two_messages(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    sent: list[tuple[str, str]] = []

    result = portfolio.cycle(
        asof_date="2024-01-31",
        holdings_csv=holdings,
        cash=7100.0,
        notifier=lambda title, text: sent.append((title, text)) or True,
    )

    assert result.reconciled and not result.skipped_non_trading
    assert result.plan is not None and result.plan.has_target
    assert result.notified
    # 两条推送：日报在前，调仓票独立第二条
    assert len(sent) == 2
    digest_title, digest_text = sent[0]
    assert "组合日报" in digest_title
    assert "总值" in digest_text and "触发调仓" in digest_text
    ticket_title, ticket_text = sent[1]
    assert "调仓提醒" in ticket_title
    assert "买入" in ticket_text


def test_cycle_digest_reports_asset_daily_change_and_inception_pnl(tmp_path: Path):
    """日报含各持仓当日涨跌幅/盈亏额与组合成立以来盈亏（2026-07-16 用户需求）。"""
    data_dir = tmp_path / "data"
    # AAA 收盘: 01-29 10 → 01-30 11（+10%）→ 01-31 12.1（+10%）
    _write_market_data(data_dir, closes={"AAA": {"2024-01-30": 11, "2024-01-31": 12.1}})
    portfolio = LivePortfolio("live_test", _live_config(data_dir), output_root=tmp_path / "live")
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")  # 起点总值 10100
    portfolio.mark_to_market("2024-01-30")
    sent: list[tuple[str, str]] = []

    portfolio.cycle(asof_date="2024-01-31", notifier=lambda title, text: sent.append((title, text)) or True)

    _, text = sent[0]
    # 当日涨跌：AAA +10%，盈亏 300 股 ×（12.1 − 11）= +330 元
    assert "+10.00%" in text and "+330.00 元" in text
    # 成立以来：总值 7100 + 300×12.1 = 10730，对起点 10100 为 +630 / +6.24%
    assert "成立以来" in text
    assert "+630.00 元 / +6.24%" in text and "起点 2024-01-29" in text

    # 成立首日（尚无早于当日的基准）不显示"成立以来"行
    valuation = portfolio.mark_to_market("2024-01-29")
    _, first_day_text = portfolio._render_daily_digest(
        valuation, PlanResult(portfolio.portfolio_id, parse_date("2024-01-29"), False, 0, None, Path("x"), "")
    )
    assert "成立以来" not in first_day_text


def _real_nav_rows(portfolio: LivePortfolio) -> list[dict]:
    with portfolio.real_nav_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_external_flow_issues_units_and_keeps_returns_clean(tmp_path: Path):
    """申购按当日单位净值增发份额：总值跳变不产生假收益（2026-07-18 需求）。"""
    portfolio = _make_portfolio(tmp_path)  # 价格恒为 10
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7000.0, asof_date="2024-01-29")  # 总值 10000

    # 01-30 申购 5000：现金 7000 → 12000，价格未动
    portfolio.reconcile(holdings, cash=12000.0, asof_date="2024-01-30", external_flow=5000.0)
    # 同日 mark_to_market 重估（cycle 的日常路径）必须继承申报过的申赎金额
    valuation = portfolio.mark_to_market("2024-01-30")

    rows = _real_nav_rows(portfolio)
    assert [float(row["units"]) for row in rows] == pytest.approx([10000.0, 15000.0])
    assert [float(row["unit_nav"]) for row in rows] == pytest.approx([1.0, 1.0])
    assert float(rows[1]["external_flow"]) == pytest.approx(5000.0)
    # 申购日收益率为 0（价格没动），金额变动剔除申赎后也是 0
    assert valuation["external_flow"] == pytest.approx(5000.0)
    assert valuation["unit_nav"] == pytest.approx(1.0)
    assert valuation["net_invested"] == pytest.approx(15000.0)
    _, text = portfolio._render_daily_digest(
        valuation, PlanResult(portfolio.portfolio_id, parse_date("2024-01-30"), False, 0, None, Path("x"), "")
    )
    assert "本日申购" in text and "+5,000.00 元" in text
    assert "+0.00%" in text  # 较上一估值日:份额口径,申购不算收益


def test_withdrawal_redeems_units_and_split_pnl_identity(tmp_path: Path):
    data_dir = tmp_path / "data"
    _write_market_data(data_dir, closes={"AAA": {"2024-01-31": 11}})
    portfolio = LivePortfolio("live_test", _live_config(data_dir), output_root=tmp_path / "live")
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7000.0, asof_date="2024-01-29")  # 总值 10000

    # 01-30 赎回 3000（价格未动）：份额 10000 → 7000，单位净值仍 1.0
    portfolio.reconcile(holdings, cash=4000.0, asof_date="2024-01-30", external_flow=-3000.0)
    rows = _real_nav_rows(portfolio)
    assert float(rows[1]["units"]) == pytest.approx(7000.0)
    assert float(rows[1]["unit_nav"]) == pytest.approx(1.0)

    # 01-31 AAA 10→11：总值 4000+3300=7300，单位净值 7300/7000
    valuation = portfolio.mark_to_market("2024-01-31")
    assert valuation["unit_nav"] == pytest.approx(7300.0 / 7000.0)
    # 净投入 10000−3000=7000,累计盈亏 300;浮动 =300×(11−10)=300(成本=建仓日收盘 10),已实现 0
    assert valuation["net_invested"] == pytest.approx(7000.0)
    assert valuation["total_pnl"] == pytest.approx(300.0)
    assert valuation["float_pnl"] == pytest.approx(300.0)
    assert valuation["realized_pnl"] == pytest.approx(0.0)
    _, text = portfolio._render_daily_digest(
        valuation, PlanResult(portfolio.portfolio_id, parse_date("2024-01-31"), False, 0, None, Path("x"), "")
    )
    assert "净投入 7,000.00 元" in text
    assert "已实现 +0.00 元 + 浮动 +300.00 元" in text
    assert "+4.29%" in text  # 7300/7000-1,份额口径


def test_full_withdrawal_and_redeposit_preserve_unit_nav():
    rows = [{"date": day, "total_value": str(total), "external_flow": str(flow)} for day, total, flow in [
        ("2024-01-25", 10000, 0), ("2024-01-26", 11000, 0),
        ("2024-01-29", 0, -11000), ("2024-01-30", 0, 0), ("2024-01-31", 5500, 5500),
    ]]
    LivePortfolio._recompute_unit_chain(rows)
    assert [float(row["unit_nav"]) for row in rows] == pytest.approx([1, 1.1, 1.1, 1.1, 1.1])
    assert [float(row["units"]) for row in rows] == pytest.approx([10000, 10000, 0, 0, 5000])


def test_amend_flow_write_failure_preserves_nav(tmp_path: Path, monkeypatch):
    portfolio = _make_portfolio(tmp_path)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", []), cash=10000, asof_date="2024-01-29")
    portfolio.mark_to_market("2024-01-30")
    before = portfolio.real_nav_path.read_bytes()

    def fail_replace(self, target):
        raise OSError("disk error")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="disk error"):
        portfolio.amend_flow("2024-01-30", 1000)
    assert portfolio.real_nav_path.read_bytes() == before


def test_legacy_real_nav_backfills_unit_chain(tmp_path: Path):
    """旧三列档案在下一次写盘时自动回填份额链，历史收益率不变（免迁移）。"""
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")
    # 手工降级为旧格式（date,cash,positions_value,total_value）
    portfolio.real_nav_path.write_text(
        "date,cash,positions_value,total_value\n2024-01-29,7100.00,3000.00,10100.00\n",
        encoding="utf-8",
    )

    portfolio.mark_to_market("2024-01-30")

    rows = _real_nav_rows(portfolio)
    assert [row["date"] for row in rows] == ["2024-01-29", "2024-01-30"]
    assert [float(row["unit_nav"]) for row in rows] == pytest.approx([1.0, 1.0])  # 价格恒定
    assert float(rows[0]["units"]) == pytest.approx(10100.0)
    assert float(rows[0]["external_flow"]) == pytest.approx(0.0)


def test_amend_flow_equals_timely_declaration(tmp_path: Path):
    """忘报申赎 → amend-flow 补报,份额链与当时就申报精确等价（回档重算）。"""
    data_dir = tmp_path / "data"
    _write_market_data(data_dir, closes={"AAA": {"2024-01-31": 11}})
    config = _live_config(data_dir)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])

    # 组合 A:01-30 申购 5000 当天就申报
    timely = LivePortfolio("live_test", config, output_root=tmp_path / "a")
    timely.reconcile(holdings, cash=7000.0, asof_date="2024-01-29")
    timely.reconcile(holdings, cash=12000.0, asof_date="2024-01-30", external_flow=5000.0)
    timely.mark_to_market("2024-01-31")

    # 组合 B:忘了申报（flow=0 → 当日出现 +50% 假收益），事后补报
    forgot = LivePortfolio("live_test", config, output_root=tmp_path / "b")
    forgot.reconcile(holdings, cash=7000.0, asof_date="2024-01-29")
    forgot.reconcile(holdings, cash=12000.0, asof_date="2024-01-30")  # 忘报
    forgot.mark_to_market("2024-01-31")
    fake = _real_nav_rows(forgot)
    assert float(fake[1]["unit_nav"]) == pytest.approx(1.5)  # 假收益证据

    result = forgot.amend_flow("2024-01-30", 5000.0)

    assert result["old_flow"] == pytest.approx(0.0)
    assert [item["date"] for item in result["changed"]] == ["2024-01-30", "2024-01-31"]
    # 补报后与组合 A 的台账逐字节一致（估值列本就相同,派生链确定性重放）
    assert forgot.real_nav_path.read_text(encoding="utf-8") == timely.real_nav_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="不存在"):
        forgot.amend_flow("2024-02-05", 100.0)


def test_cycle_rejects_flow_without_holdings(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")
    with pytest.raises(ValueError, match="external_flow"):
        portfolio.cycle(asof_date="2024-01-30", external_flow=5000.0)


def test_cycle_no_op_day_sends_single_digest(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")
    sent: list[tuple[str, str]] = []

    result = portfolio.cycle(asof_date="2024-01-30", notifier=lambda title, text: sent.append((title, text)) or True)

    assert result.plan is not None and not result.plan.has_target
    assert len(sent) == 1
    title, text = sent[0]
    assert "组合日报" in title
    assert "无需调仓" in text
    # 日变动基于前一估值日（reconcile 写入的 01-29 那行）
    assert "较上一估值日" in text


def test_mark_to_market_freezes_history_once_newer_row_exists(tmp_path: Path):
    """已有更新日期的估值后，旧日期不允许被重估值改写（数据中间状态防护）。"""
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")
    portfolio.mark_to_market("2024-01-30")
    portfolio.mark_to_market("2024-01-31")

    with portfolio.real_nav_path.open(newline="", encoding="utf-8") as handle:
        before = {row["date"]: row["total_value"] for row in csv.DictReader(handle)}

    # 回头重估 01-30（模拟数据处于异常中间状态时的 --force 重跑）→ 必须拒绝回写
    result = portfolio.mark_to_market("2024-01-30")
    assert result["written"] is False

    with portfolio.real_nav_path.open(newline="", encoding="utf-8") as handle:
        after = {row["date"]: row["total_value"] for row in csv.DictReader(handle)}
    assert after == before

    # 最新日期的同日重跑仍允许（当晚数据修正的正常场景）
    result = portfolio.mark_to_market("2024-01-31")
    assert result["written"] is True


def test_historical_valuation_uses_frozen_cash_and_excludes_future_deposits(tmp_path: Path, monkeypatch):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "h.csv", [])
    portfolio.reconcile(holdings, cash=10000, asof_date="2024-01-29")
    portfolio.mark_to_market("2024-01-30")
    _write_holdings(holdings, ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=17000, asof_date="2024-01-31", external_flow=10000)
    state_before, nav_before = portfolio.state_path.read_bytes(), portfolio.real_nav_path.read_bytes()
    monkeypatch.setattr(portfolio, "_load_data", lambda asof: pytest.fail("历史快照不需要重估行情"))
    historical = portfolio.mark_to_market("2024-01-30")
    assert historical["written"] is False
    assert historical["cash"] == 10000
    assert historical["total_value"] == 10000
    assert historical["net_invested"] == 10000
    assert historical["total_pnl"] == 0
    assert historical["float_pnl"] is None
    assert historical["realized_pnl"] is None
    assert portfolio.state_path.read_bytes() == state_before
    assert portfolio.real_nav_path.read_bytes() == nav_before


def test_mark_to_market_appends_daily_real_nav(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")

    valuation = portfolio.mark_to_market("2024-01-30")

    assert valuation["total_value"] == pytest.approx(7100.0 + 3000.0)
    assert valuation["previous_total"] == pytest.approx(10100.0)
    assert valuation["weights"]["A"] == pytest.approx(3000.0 / 10100.0)
    with portfolio.real_nav_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["date"] for row in rows] == ["2024-01-29", "2024-01-30"]


def test_residual_sentinel_silent_when_ledger_consistent(tmp_path: Path):
    """cost_basis 与建仓价一致时残差为 0，哨兵不报警。"""
    portfolio = _make_portfolio(tmp_path)
    # 10 元买 300 股 = 3000，现金 7100，净投入 10100；cost_basis 如实填 10
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,10"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")

    valuation = portfolio.mark_to_market("2024-01-30")

    assert valuation["realized_pnl"] == pytest.approx(0.0, abs=1e-6)
    assert valuation["realized_residual_alert"] is False


def test_partial_execution_ledger_warns_without_breaking_valuation(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,300,10"]), cash=7000, asof_date="2024-01-29")
    portfolio.reconcile(_write_holdings(tmp_path / "h.csv", ["AAA,200,10"]), cash=8099, asof_date="2024-01-30")
    (portfolio.portfolio_dir / "execution_ledger.csv").write_text(
        "date,code,event,quantity,gross_amount,fee\n2024-01-30,AAA,SELL,100,1100,1\n")
    valuation = portfolio.mark_to_market("2024-01-31")
    assert valuation["total_value"] == 10099
    assert valuation["expected_realized_pnl"] is None
    assert valuation["realized_residual_alert"]
    _, digest = portfolio._render_daily_digest(valuation, PlanResult(
        "live_test", parse_date("2024-01-31"), False, 0, None, tmp_path / "ticket.txt", ""))
    assert "缺少持仓成本" in digest


def test_residual_sentinel_fires_when_cost_basis_exceeds_inception_mark(tmp_path: Path):
    """R056 实盘踩过的故障：实付(含手续费/成交价高于收盘)高于建仓日收盘市值。

    首行基线按收盘 mark-to-market，而 cost_basis 是实付——两者的差被恒等式挤进
    「已实现」且符号为正（实际是损失）。这类"总值对、拆分错"的故障不会被任何
    总值类检查发现，哨兵是唯一的守门人。实盘 2026-07 潜伏了三周才被发现。
    """
    portfolio = _make_portfolio(tmp_path)
    # 收盘 10，实付 10.10/股（含费）→ 300 股多付 30 元，基线却按收盘记
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,10.10"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")

    valuation = portfolio.mark_to_market("2024-01-30")

    assert valuation["float_pnl"] == pytest.approx(-30.0, abs=1e-6)
    assert valuation["realized_pnl"] == pytest.approx(30.0, abs=1e-6)
    assert valuation["realized_residual_alert"] is True
    _, digest = portfolio._render_daily_digest(
        valuation,
        PlanResult(
            portfolio_id="live_test",
            plan_date=parse_date("2024-01-30"),
            has_target=False,
            order_count=0,
            ticket_csv=None,
            ticket_txt=tmp_path / "ticket.txt",
            text="",
        ),
    )
    assert "账本自检未通过" in digest


def test_residual_sentinel_tolerance_is_configurable(tmp_path: Path):
    """真实卖出后残差固定在累计已实现盈亏水平，调高容差即可止警。"""
    config = _live_config(tmp_path / "data")
    config["live"] = {"realized_residual_tolerance": 50.0}
    _write_market_data(tmp_path / "data")
    portfolio = LivePortfolio("live_test", config, output_root=tmp_path / "out")
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,10.10"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-29")

    valuation = portfolio.mark_to_market("2024-01-30")

    assert valuation["realized_pnl"] == pytest.approx(30.0, abs=1e-6)
    assert valuation["realized_residual_alert"] is False


def test_cycle_notifier_failure_does_not_break_cycle(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100.0, asof_date="2024-01-30")

    result = portfolio.cycle(asof_date="2024-01-31", notifier=lambda title, text: False)

    assert result.plan is not None
    assert not result.notified


def test_cycle_holdings_without_cash_raises(tmp_path: Path):
    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    with pytest.raises(ValueError, match="cash"):
        portfolio.cycle(asof_date="2024-01-31", holdings_csv=holdings)


# ---------------------------------------------------------------- notify


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _clear_notify_env(monkeypatch) -> None:
    for name in ("RQ_SERVERCHAN_KEY", "RQ_SMTP_HOST", "RQ_SMTP_USERNAME", "RQ_SMTP_PASSWORD", "RQ_SMTP_TO"):
        monkeypatch.delenv(name, raising=False)


def test_markdown_to_html_renders_repo_syntax_subset():
    """覆盖本仓库推送正文实际用到的全部语法：标题/引用/列表/有序/表格/行内。"""
    from src.platform_core.notify import markdown_to_html

    html = markdown_to_html(
        "# 标题\n"
        "\n"
        "> 引用第一行\n"
        "> 引用第二行\n"
        "\n"
        "## 小标题\n"
        "\n"
        "- **粗体项**：值\n"
        "- 普通项 `code`\n"
        "\n"
        "| 指标 | 值 |\n"
        "|---|---:|\n"
        "| 累计差异 | +0.3 bp |\n"
        "\n"
        "1. 买入 512890\n"
        "2. 卖出 510300\n"
        "\n"
        "普通段落。\n"
    )

    assert "<h1" in html and "<h2" in html
    assert "引用第一行<br>引用第二行" in html          # 连续引用合并为一块
    assert "<ul" in html and "<strong>粗体项</strong>" in html and "<code" in html
    assert "<table" in html and "<th" in html and "+0.3 bp" in html
    assert "<ol" in html and "买入 512890" in html
    assert "<p" in html and "普通段落。" in html
    assert "<style>" not in html                        # 必须内联，Gmail 会剥掉 style 块


def test_markdown_to_html_escapes_html():
    from src.platform_core.notify import markdown_to_html

    html = markdown_to_html("- 值 <b>x</b> & <script>alert(1)</script>\n")
    assert "&lt;script&gt;" in html and "&amp;" in html
    assert "<script>" not in html


def test_smtp_sends_multipart_with_html_alternative(monkeypatch):
    """Gmail 不渲染 markdown 纯文本，故必须同时带 HTML 分支。"""
    from src.platform_core import notify as notify_mod

    sent: dict = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, username, password):
            sent["user"] = username

        def sendmail(self, sender, recipients, raw):
            sent["raw"] = raw

    monkeypatch.setattr(notify_mod.smtplib, "SMTP_SSL", _FakeSMTP)
    monkeypatch.setenv("RQ_SMTP_PASSWORD", "pw")

    ok = notify_mod._send_smtp(
        {"host": "smtp.test", "port": 465, "username": "me@test", "to": ["you@test"]},
        "标题",
        "## 日报\n\n- **总值**: 105,029.64 元\n",
    )

    assert ok is True
    raw = sent["raw"]
    assert "multipart/alternative" in raw
    assert 'Content-Type: text/plain' in raw and 'Content-Type: text/html' in raw


def test_send_notification_without_channels_returns_false(monkeypatch):
    _clear_notify_env(monkeypatch)
    assert send_notification("t", "x", None) is False


def test_resolve_channels_auto_discovers_from_env(monkeypatch):
    _clear_notify_env(monkeypatch)
    monkeypatch.setenv("RQ_SERVERCHAN_KEY", "SCT_fake")
    assert resolve_channels(None) == [{"type": "serverchan"}]
    # 显式配置优先于自动发现
    explicit = {"channels": [{"type": "smtp", "host": "h", "username": "u", "to": ["a"]}]}
    assert resolve_channels(explicit) == explicit["channels"]


def test_send_serverchan_success(monkeypatch):
    _clear_notify_env(monkeypatch)
    monkeypatch.setenv("RQ_SERVERCHAN_KEY", "SCT_fake")
    monkeypatch.setattr(notify_module.urllib.request, "urlopen", lambda request, timeout: _FakeResponse())
    assert send_notification("调仓提醒", "正文", None) is True


def test_send_notification_swallows_channel_exceptions(monkeypatch):
    _clear_notify_env(monkeypatch)
    monkeypatch.setenv("RQ_SERVERCHAN_KEY", "SCT_fake")

    def boom(request, timeout):
        raise OSError("network down")

    monkeypatch.setattr(notify_module.urllib.request, "urlopen", boom)
    assert send_notification("调仓提醒", "正文", None) is False


def test_send_notification_unknown_channel_type(monkeypatch):
    _clear_notify_env(monkeypatch)
    assert send_notification("t", "x", {"channels": [{"type": "pigeon"}]}) is False


def test_live_does_not_reuse_runtime_without_matching_source_proof(tmp_path, monkeypatch):
    from src.platform_core.strategy import MonthlyEqualWeightStrategy

    portfolio = _make_portfolio(tmp_path)
    holdings = _write_holdings(tmp_path / "holdings.csv", ["AAA,300,"])
    portfolio.reconcile(holdings, cash=7100, asof_date="2024-01-30")
    payload = json.loads(portfolio.state_path.read_text())
    payload["strategy_state"]["_live_strategy_runtime"] = {
        "identity": {"strategy_name": "monthly_equal_weight", "params": portfolio.strategy_config["params"]},
        "plan_date": "2024-01-30", "runtime": {"stale": True}, "runtime_before": {"stale": True},
    }
    portfolio.state_path.write_text(json.dumps(payload))
    observed = []
    monkeypatch.setattr(MonthlyEqualWeightStrategy, "generate_targets", lambda self, context: observed.append(context.runtime.get("stale")))
    portfolio.plan("2024-01-31")
    assert observed == [None]
