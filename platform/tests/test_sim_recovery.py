import json
from datetime import date

import pandas as pd
import pytest

from src.platform_core.attribution import load_shadow_nav
from src.platform_core.models import PendingIntent, PortfolioState
from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import InMemoryStore, SQLiteStore
from src.platform_core.strategy import MonthlyEqualWeightStrategy


def _portfolio(tmp_path, store):
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"trade_date": pd.bdate_range("2024-01-02", periods=3), "close": [10.] * 3,
                  "volume": [1000.] * 3}).to_csv(data / "A.csv", index=False)
    config = {"data": {"data_dir": str(data)},
              "assets": [{"asset_id": "A", "code": "A", "lot_size": 1, "price_limit_pct": None}],
              "strategy": {"strategy_name": "monthly_equal_weight", "params": {"universe": ["A"]}},
              "execution": {"slippage_bps": 0, "fee": {"rate": 0., "min_fee": 0.}},
              "output": {"sim_dir": str(tmp_path / "sims")}}
    checkpoint = tmp_path / "checkpoint.json"
    state = PortfolioState(cash=1000., last_date=date(2024, 1, 2),
                           pending_intents={"A": PendingIntent("A", 1., date(2024, 1, 2))})
    checkpoint.write_text(json.dumps(state.to_dict()))
    return SimPortfolio.create_from_checkpoint(checkpoint, config, store, portfolio_id="test"), checkpoint


@pytest.mark.parametrize("failure", ["strategy", "persist"])
@pytest.mark.parametrize("persisted", [True, False])
def test_failed_advance_preserves_memory_and_checkpoint_and_can_retry(tmp_path, monkeypatch, failure, persisted):
    from src.platform_core import sim

    store = SQLiteStore(tmp_path / "registry.sqlite") if persisted else InMemoryStore()
    try:
        portfolio, _ = _portfolio(tmp_path, store)
        state_object = portfolio.state
        before = portfolio.state.to_dict()
        saved = portfolio.state_path.read_bytes()
        with monkeypatch.context() as patch:
            if failure == "strategy":
                def fail(*args):
                    raise RuntimeError("strategy failure after pending fill")
                patch.setattr(MonthlyEqualWeightStrategy, "generate_targets", fail)
                error = RuntimeError
            else:
                original_write = sim.write_json

                def fail(path, payload):
                    if path == portfolio.state_path:
                        raise OSError("checkpoint unavailable")
                    return original_write(path, payload)

                patch.setattr(sim, "write_json", fail)
                error = OSError
            with pytest.raises(error):
                portfolio.advance("2024-01-04")
        assert portfolio.state is state_object
        assert portfolio.state.to_dict() == before
        assert portfolio.state_path.read_bytes() == saved
        assert load_shadow_nav(portfolio.portfolio_dir) == []
        retried = portfolio.advance("2024-01-04")
        assert retried.metrics["trade_count"] == 1
        assert portfolio.state is state_object
        assert portfolio.state.positions["A"].quantity == 100.
        assert portfolio.state.cash == 0.
        assert [row["date"] for row in load_shadow_nav(portfolio.portfolio_dir)] == ["2024-01-03", "2024-01-04"]
    finally:
        store.close()


def test_reload_keeps_the_original_checkpoint_in_run_provenance(tmp_path):
    portfolio, checkpoint = _portfolio(tmp_path, InMemoryStore())
    portfolio.advance("2024-01-03")
    loaded = SimPortfolio.load("test", portfolio.config, InMemoryStore())
    assert loaded.source_checkpoint == checkpoint
    result = loaded.advance("2024-01-04")
    assert json.loads((result.output_dir / "manifest.json").read_text())["source_checkpoint"] == str(checkpoint)


def test_calendar_extension_is_for_signals_and_cannot_create_a_fake_trading_day(tmp_path):
    portfolio, _ = _portfolio(tmp_path, InMemoryStore())
    result = portfolio.advance("2024-01-05")
    assert result.metrics["processed_days"] == 2
    assert portfolio.state.last_date == date(2024, 1, 4)
    assert pd.read_csv(result.output_dir / "nav.csv")["date"].tolist() == ["2024-01-03", "2024-01-04"]


def test_failed_run_stays_excluded_after_a_later_different_window_commits(tmp_path, monkeypatch):
    from src.platform_core import sim

    portfolio, _ = _portfolio(tmp_path, InMemoryStore())
    original_write = sim.write_json
    with monkeypatch.context() as patch:
        def fail(path, payload):
            if path == portfolio.state_path:
                raise OSError("checkpoint unavailable")
            return original_write(path, payload)

        patch.setattr(sim, "write_json", fail)
        with pytest.raises(OSError):
            portfolio.advance("2024-01-04")
    portfolio.config["backtest"] = {"start_date": "2024-01-04"}
    portfolio.advance("2024-01-04")
    assert [row["date"] for row in load_shadow_nav(portfolio.portfolio_dir)] == ["2024-01-04"]
    loaded = SimPortfolio.load("test", portfolio.config, InMemoryStore())
    loaded.advance("2024-01-04")
    assert [row["date"] for row in load_shadow_nav(portfolio.portfolio_dir)] == ["2024-01-04"]
