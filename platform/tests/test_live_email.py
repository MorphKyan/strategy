from __future__ import annotations

import copy
import json
from datetime import date
from email import policy
from email.parser import Parser
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from src.platform_core import live_email, notify
from src.platform_core.live import LivePortfolio
from src.platform_core.models import PortfolioState, Position, parse_date


@pytest.fixture
def account(tmp_path, monkeypatch):
    class Today(date):
        @classmethod
        def today(cls):
            return cls(2024, 2, 2)

    monkeypatch.setattr(live_email, "date", Today)
    market = tmp_path / "market"
    market.mkdir()
    days = pd.to_datetime(["2024-01-29", "2024-01-30", "2024-01-31", "2024-02-01", "2024-02-02"])
    pd.DataFrame({"trade_date": days, "close": [10, 10, 9.9, 11, 12]}).to_csv(market / "AAA.csv", index=False)
    config = {"data": {"data_dir": str(market)}, "assets": [{"asset_id": "A", "code": "AAA", "name": "资产A"}],
              "strategy": {"strategy_name": "monthly_equal_weight", "params": {"universe": ["A"]}}}
    folder = tmp_path / "account"
    folder.mkdir()
    rows = [{"date": str(day.date()), "cash": cash, "total_value": value, "external_flow": flow}
            for day, cash, value, flow in zip(days, [1000, 899, 899, 1942, 1943],
                                             [1000, 999, 999, 2009, 2015], [1000, 0, 0, 1000, 0])]
    LivePortfolio._recompute_unit_chain(rows)
    pd.DataFrame(rows).to_csv(folder / "real_nav.csv", index=False)
    ledger = [
        ("2024-01-29", "INITIAL_CAPITAL", "", 0, 0, 0, 1000, 1000),
        ("2024-01-30", "BUY", "AAA", 10, 100, 1, -101, 0),
        ("2024-01-31", "DIVIDEND_RECEIVABLE", "AAA", 10, 1, 0, 0, 0),
        ("2024-02-01", "DEPOSIT", "", 0, 0, 0, 1000, 1000),
        ("2024-02-01", "SELL", "AAA", 4, 44, 1, 43, 0),
        ("2024-02-02", "DIVIDEND_PAYMENT", "AAA", 0, 1, 0, 1, 0),
        # 未来订单、成交流水不能提前影响今日图。
        ("2024-02-05", "BUY", "AAA", 100, 1200, 0, -1200, 0),
    ]
    pd.DataFrame(ledger, columns=["date", "event", "code", "quantity", "gross_amount", "fee",
                                  "cash_delta", "external_flow"]).to_csv(folder / "execution_ledger.csv", index=False)
    state = {"live_accounting": {"dividends": {"AAA:2024-01-30:2024-01-31": {
        "asset_id": "A", "amount": 1, "ex_date": "2024-01-31", "payment_date": "2024-02-02"}}}}
    (folder / "portfolio_state.json").write_text(json.dumps(state), encoding="utf-8")
    return config, folder


@pytest.mark.parametrize("automatic", [False, True])
def test_contribution_accounts_for_deposit_sale_fees_and_dividend_once(account, automatic):
    config, folder = account
    if automatic:
        ledger = pd.read_csv(folder / "execution_ledger.csv")
        ledger = ledger[~ledger.event.str.startswith("DIVIDEND_")]
        ledger.to_csv(folder / "execution_ledger.csv", index=False)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    _nav, adjusted, weights, linked, chain = live_email.load_daily_history(config, folder, "2024-02-02")
    assert weights.AAA.iloc[-1] == pytest.approx(72 / 2015)
    assert weights.receivables.iloc[2] == pytest.approx(1 / 999)
    assert weights.receivables.iloc[-1] == 0
    assert np.allclose(chain.diff().fillna(0), linked.sum(axis=1))
    assert chain.iloc[-1] == pytest.approx(1.009 * (2015 / 2009))
    assert adjusted.AAA.iloc[-1] == 12
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


@pytest.mark.parametrize("corruption", ["ledger", "market", "cash", "nav_chain", "stale", "unknown_event"])
def test_inconsistent_history_is_not_presented_as_contribution(account, corruption):
    config, folder = account
    if corruption in {"ledger", "unknown_event"}:
        frame = pd.read_csv(folder / "execution_ledger.csv")
        if corruption == "ledger":
            frame.loc[frame.event == "BUY", "quantity"] = 9
        else:
            frame.loc[0, "event"] = "UNEXPLAINED"
        frame.to_csv(folder / "execution_ledger.csv", index=False)
    elif corruption in {"market", "stale"}:
        path = config["data"]["data_dir"] + "/AAA.csv"
        frame = pd.read_csv(path)
        if corruption == "market":
            frame = frame.drop(2)
        else:
            frame.trade_date = pd.to_datetime(frame.trade_date) - pd.Timedelta(days=30)
        frame.to_csv(path, index=False)
    else:
        frame = pd.read_csv(folder / "real_nav.csv")
        frame.loc[2, "cash" if corruption == "cash" else "unit_nav"] += 1
        frame.to_csv(folder / "real_nav.csv", index=False)
    with pytest.raises(ValueError):
        live_email.load_daily_history(config, folder, "2024-02-02")


def test_six_charts_mime_and_annualization_are_dynamic(account, monkeypatch):
    config, folder = account
    order = []
    original = live_email._chart

    def capture(curves, total, kind, colors):
        order.append(kind)
        return original(curves, total, kind, colors)

    monkeypatch.setattr(live_email, "_chart", capture)
    text = "## 账户明细\n\n**策略目标监控**\n\n|资产|当前|目标|\n|---|---:|---:|\n|A|3.6%|5%|"
    body, images, annual = live_email.build_daily_email(config, folder, "2024-02-02", text)
    assert order == ["nav", "contribution", "weights"] * 2
    assert list(images) == [f"{window}_{kind}" for window in ["recent30", "full"]
                            for kind in ["nav", "contribution", "weights"]]
    assert all(content.startswith(b"\x89PNG") for content in images.values())
    assert "策略目标监控" in body and "<table" in body and 'width="320"' in body
    assert "样式测试" not in body and "首尾日期优化" not in body
    assert annual != "+5.15%"  # 不得复用示例的固定数据。
    sent = {}

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, *args):
            pass

        def sendmail(self, sender, recipients, raw):
            sent["message"] = Parser(policy=policy.default).parsestr(raw)

    monkeypatch.setenv("RQ_SMTP_PASSWORD", "synthetic")
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", SMTP)
    assert notify.send_notification("组合日报", text, {"channels": [
        {"type": "smtp", "host": "smtp.test", "username": "a@test", "to": ["b@test"]}]},
        html_body=body, inline_images=images)
    message = sent["message"]
    assert message.get_content_type() == "multipart/alternative"
    assert len([p for p in message.walk() if p.get_content_type() == "image/png"]) == 6
    assert message.get_body(preferencelist=("html",)).get_content() == body
    assert "策略目标监控" in message.get_body(preferencelist=("plain",)).get_content()


def test_new_account_single_day_has_no_invented_annual_return(account):
    config, folder = account
    body, images, annual = live_email.build_daily_email(config, folder, "2024-01-29", "尚未建仓")
    assert annual == "—" and len(images) == 6
    assert "0期收益观测" in body


def test_missing_valuation_day_is_reported_without_changing_account(account):
    config, folder = account
    path = folder / "real_nav.csv"
    frame = pd.read_csv(path)
    frame[frame.date != "2024-01-31"].to_csv(path, index=False)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(ValueError, match="缺少估值日：\\['2024-01-31'\\]；缺少行情日：\\[\\]"):
        live_email.load_daily_history(config, folder, "2024-02-02")
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


@pytest.mark.parametrize("automatic", [False, True])
def test_backfill_replays_trades_flows_and_dividends_preserving_known_rows(account, automatic):
    config, folder = account
    if automatic:
        ledger = pd.read_csv(folder / "execution_ledger.csv")
        ledger[~ledger.event.str.startswith("DIVIDEND_")].to_csv(folder / "execution_ledger.csv", index=False)
    path = folder / "real_nav.csv"
    original = pd.read_csv(path, dtype=str).set_index("date")
    missing = ["2024-01-30", "2024-01-31", "2024-02-01"]
    original.drop(missing).reset_index().to_csv(path, index=False)
    before_state = (folder / "portfolio_state.json").read_bytes()
    portfolio = LivePortfolio(folder.name, config, output_root=folder.parent)
    assert portfolio.backfill_missing_valuations("2024-02-02") == missing
    restored = pd.read_csv(path, dtype=str).set_index("date")
    pd.testing.assert_frame_equal(restored.loc[original.index.difference(missing), original.columns],
                                  original.loc[original.index.difference(missing)])
    for field in ["cash", "total_value", "external_flow", "units", "unit_nav"]:
        assert np.allclose(restored[field].astype(float), original[field].astype(float))
    assert (folder / "portfolio_state.json").read_bytes() == before_state
    before = path.read_bytes()
    assert portfolio.backfill_missing_valuations("2024-02-02") == []
    assert path.read_bytes() == before
    body, images, _ = live_email.build_daily_email(config, folder, "2024-02-02", "已回补")
    assert len(images) == 6


@pytest.mark.parametrize("corruption", ["cash", "market", "ledger"])
def test_backfill_does_not_write_when_history_cannot_be_verified(account, corruption):
    config, folder = account
    path = folder / "real_nav.csv"
    frame = pd.read_csv(path)
    frame = frame[frame.date != "2024-01-31"]
    if corruption == "cash":
        frame.loc[frame.date == "2024-02-02", "cash"] += 1
    elif corruption == "market":
        market_path = config["data"]["data_dir"] + "/AAA.csv"
        market = pd.read_csv(market_path)
        market[market.trade_date != "2024-01-30"].to_csv(market_path, index=False)
    else:
        ledger = pd.read_csv(folder / "execution_ledger.csv")
        ledger.loc[ledger.event == "BUY", "quantity"] = 9
        ledger.to_csv(folder / "execution_ledger.csv", index=False)
    frame.to_csv(path, index=False)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    portfolio = LivePortfolio(folder.name, config, output_root=folder.parent)
    with pytest.raises(ValueError):
        portfolio.backfill_missing_valuations("2024-02-02")
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


@pytest.mark.parametrize("invalid_ledger", [False, True])
def test_cycle_backfills_before_notifying_and_failure_keeps_notifications(account, invalid_ledger):
    config, folder = account
    path = folder / "real_nav.csv"
    frame = pd.read_csv(path)
    frame[frame.date != "2024-01-31"].to_csv(path, index=False)
    accounting = json.loads((folder / "portfolio_state.json").read_text())["live_accounting"]
    accounting["cash_asof"] = "2024-02-02"
    for event in accounting["dividends"].values():
        event["paid"] = True
    state = PortfolioState(cash=1943, positions={"A": Position("A", 6, 10.1)},
                           last_date=parse_date("2024-02-02"), live_accounting=accounting)
    (folder / "portfolio_state.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")
    if invalid_ledger:
        ledger = pd.read_csv(folder / "execution_ledger.csv")
        ledger.loc[ledger.event == "BUY", "quantity"] = 9
        ledger.to_csv(folder / "execution_ledger.csv", index=False)
    sent = []

    def notifier(title, text):
        assert ("2024-01-31" in pd.read_csv(path).date.tolist()) != invalid_ledger
        sent.append(title)
        return True

    portfolio = LivePortfolio(folder.name, config, output_root=folder.parent)
    result = portfolio.cycle("2024-02-02", notifier=notifier)
    assert result.notified and sent[0].startswith("组合日报")


def test_cli_uses_new_mail_only_for_enabled_daily_digest(account, monkeypatch, capsys):
    from scripts import run_live_cycle as cli
    config, folder = account
    config = copy.deepcopy(config)
    config["notify"] = {"daily_charts": True}
    sent = []
    monkeypatch.setattr(cli, "send_notification", lambda *args, **kwargs: sent.append((args, kwargs)) or True)
    monkeypatch.setattr(live_email, "build_daily_email", lambda *args: ("<html>日报</html>", {"chart": b"png"}, "+1.00%"))
    portfolio = SimpleNamespace(portfolio_dir=folder)
    assert cli.notify_and_report("组合日报 2024-02-02 · 2015元", "每日目标", config, portfolio)
    assert sent[-1][0][0] == "组合日报 2024-02-02"
    assert "年化收益 +1.00%" in sent[-1][0][1]
    assert sent[-1][1]["inline_images"] == {"chart": b"png"}
    cli.notify_and_report("调仓提醒 2024-02-02", "订单", config, portfolio)
    assert sent[-1][1] == {} and sent[-1][0][1] == "订单"

    def fail(*args):
        raise ValueError("坏账")

    monkeypatch.setattr(live_email, "build_daily_email", fail)
    assert cli.notify_and_report("组合日报 2024-02-02", "每日目标", config, portfolio)
    assert sent[-1][1] == {} and "图表暂不可用" in sent[-1][0][1]
    assert "ValueError: 坏账" in capsys.readouterr().out
