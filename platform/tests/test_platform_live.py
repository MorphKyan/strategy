from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.platform_core import notify as notify_module
from src.platform_core.live import LivePortfolio, PlanResult
from src.platform_core.models import parse_date
from src.platform_core.notify import resolve_channels, send_notification


def _write_market_data(data_dir: Path, closes: dict[str, dict[str, float]] | None = None) -> None:
    """closes: code -> {date: close}，缺省恒为 10（OHLC 同价）。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    header = "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor"
    dates = ["2024-01-29", "2024-01-30", "2024-01-31"]
    for code in ("AAA", "BBB"):
        rows = [header]
        for d in dates:
            price = (closes or {}).get(code, {}).get(d, 10)
            rows.append(f"{code},{d},{price},{price},{price},{price},1000,10000,1")
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
