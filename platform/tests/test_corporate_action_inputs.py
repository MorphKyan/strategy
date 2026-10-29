from datetime import date

import pandas as pd
import pytest

from src.platform_core.corporate_actions import load_corporate_actions
from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.live import LivePortfolio
from src.platform_core.models import PortfolioState, Position
from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import InMemoryStore


def _config(tmp_path, closes):
    directory = tmp_path / "market"
    directory.mkdir()
    pd.DataFrame({"trade_date": pd.bdate_range("2024-01-02", periods=3), "close": closes,
                  "volume": [1000.] * 3}).to_csv(directory / "TEST.csv", index=False)
    return {"data": {"data_dir": str(directory)},
            "assets": [{"asset_id": "A", "code": "TEST", "lot_size": 1, "price_limit_pct": None}],
            "portfolio": {"initial_cash": 0., "initial_positions": [{"asset_id": "A", "quantity": 100., "cost_basis": 10.}]},
            "backtest": {"start_date": "2024-01-02", "end_date": "2024-01-04"},
            "strategy": {"strategy_name": "monthly_equal_weight", "params": {"universe": ["A"], "rebalance_on_start": False}},
            "output": {"results_dir": str(tmp_path / "results"), "sim_dir": str(tmp_path / "sims")}}


@pytest.mark.parametrize("mode", ["backtest", "sim"])
@pytest.mark.parametrize("kind", ["dividends", "splits"])
def test_runtime_uses_corporate_actions_from_its_own_market_directory(tmp_path, mode, kind):
    config = _config(tmp_path, [10., 9., 9.] if kind == "dividends" else [10., 5., 5.])
    directory = config["data"]["data_dir"]
    if kind == "dividends":
        pd.DataFrame({"code": ["TEST"], "ex_date": ["2024-01-03"], "payment_date": ["2024-01-04"],
                      "dividend_per_share": [1.]}).to_csv(f"{directory}/platform_dividends.csv", index=False)
    else:
        pd.DataFrame({"code": ["TEST"], "split_date": ["2024-01-02"], "split_ratio": [2.]}).to_csv(
            f"{directory}/platform_splits.csv", index=False)
    store = InMemoryStore()
    if mode == "backtest":
        result = PlatformBacktestEngine(config, store).run()
        rows = pd.read_csv(result.output_dir / "nav.csv")
    else:
        state = PortfolioState(cash=0., positions={"A": Position("A", 100., 10.)}, last_date=date(2024, 1, 2))
        portfolio = SimPortfolio("test", config, store, state, tmp_path / "checkpoint")
        result = portfolio.advance("2024-01-04")
        rows = pd.read_csv(result.output_dir / "nav.csv")
    assert rows["total_value"].tolist() == pytest.approx([1000.] * len(rows))
    assert rows["cash"].iloc[-1] == (100. if kind == "dividends" else 0.)


@pytest.mark.parametrize("kind,csv", [
    ("dividends", "code,ex_date,payment_date,dividend_per_share\nA,2024-01-02,2024-01-03,-1\n"),
    ("dividends", "code,ex_date,payment_date,dividend_per_share\nA,2024-01-02,2024-01-03,inf\n"),
    ("dividends", "code,ex_date,payment_date,dividend_per_share\nA,2024-01-02,2024-01-01,1\n"),
    ("dividends", "code,ex_date,payment_date,dividend_per_share\nA,,2024-01-03,1\n"),
    ("dividends", "code,ex_date,payment_date,dividend_per_share\nA,2024-01-02,2024-01-03,1\nA,2024-01-02,2024-01-03,1\n"),
    ("splits", "code,split_date,split_ratio\nA,2024-01-02,0\n"),
    ("splits", "code,split_date,split_ratio\nA,2024-01-02,nan\n"),
    ("splits", "code,split_date,split_ratio\nA,2024-01-02,2\nA,2024-01-02,2\n"),
])
def test_invalid_event_files_fail_before_cash_or_positions_are_changed(tmp_path, kind, csv):
    (tmp_path / f"platform_{kind}.csv").write_text(csv)
    with pytest.raises(ValueError):
        load_corporate_actions({"data": {"data_dir": str(tmp_path)}}, kind)


def test_explicit_missing_event_file_is_not_treated_as_no_events(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_corporate_actions({"data": {"splits_csv": str(tmp_path / "missing.csv")}}, "splits")


def test_live_dividends_use_the_configured_market_directory(tmp_path):
    config = _config(tmp_path, [10., 9., 9.])
    pd.DataFrame({"code": ["TEST"], "record_date": ["2024-01-02"], "ex_date": ["2024-01-03"],
                  "payment_date": ["2024-01-04"], "dividend_per_share": [1.]}).to_csv(
        f"{config['data']['data_dir']}/platform_dividends.csv", index=False)
    portfolio = LivePortfolio("test", config, output_root=tmp_path / "live")
    state = PortfolioState(cash=0., positions={"A": Position("A", 100., 10.)}, last_date=date(2024, 1, 2))
    portfolio._apply_dividends(state, date(2024, 1, 4))
    assert state.cash == 100.
