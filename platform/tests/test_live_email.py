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
    config = {"data": {"data_dir": str(market)}, "assets": [{"asset_id": "A", "code": "AAA", "name": "资产A"}]}
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


def test_cli_uses_new_mail_only_for_enabled_daily_digest(account, monkeypatch):
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
