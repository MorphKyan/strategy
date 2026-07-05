from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.platform_core.live import LivePortfolio


def _write_market_data(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    header = "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor"
    dates = ["2024-01-29", "2024-01-30", "2024-01-31"]
    for code in ("AAA", "BBB"):
        rows = [header] + [f"{code},{d},10,10,10,10,1000,10000,1" for d in dates]
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
