import json
from datetime import date

import pytest

from src.platform_core.live import LivePortfolio
from src.platform_core.models import PendingIntent, PortfolioState, Position
from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import InMemoryStore


def _config(tmp_path):
    return {"assets": [{"asset_id": "A", "code": "A"}],
            "strategy": {"strategy_name": "monthly_equal_weight"},
            "output": {"sim_dir": str(tmp_path / "sims"), "live_dir": str(tmp_path / "lives")}}


@pytest.mark.parametrize("kind", ["holding", "pending"])
def test_checkpoint_with_removed_asset_fails_before_creating_or_overwriting_portfolio(tmp_path, kind):
    state = PortfolioState(cash=1000)
    if kind == "holding":
        state.positions["REMOVED"] = Position("REMOVED", 100, 10)
    else:
        state.pending_intents["REMOVED"] = PendingIntent("REMOVED", 0, date(2024, 1, 1))
    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps(state.to_dict()))
    with pytest.raises(ValueError, match="REMOVED"):
        SimPortfolio.create_from_checkpoint(path, _config(tmp_path), InMemoryStore(), portfolio_id="test")
    assert not (tmp_path / "sims").exists()


def test_creating_existing_sim_id_preserves_previous_state(tmp_path):
    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps(PortfolioState(cash=1000).to_dict()))
    config = _config(tmp_path)
    portfolio = SimPortfolio.create_from_checkpoint(path, config, InMemoryStore(), portfolio_id="test")
    before = portfolio.state_path.read_bytes()
    path.write_text(json.dumps(PortfolioState(cash=500).to_dict()))
    with pytest.raises(FileExistsError):
        SimPortfolio.create_from_checkpoint(path, config, InMemoryStore(), portfolio_id="test")
    assert portfolio.state_path.read_bytes() == before


def test_live_config_change_cannot_hide_existing_holding(tmp_path):
    portfolio = LivePortfolio("test", _config(tmp_path))
    portfolio.portfolio_dir.mkdir(parents=True)
    state = PortfolioState(cash=1000, positions={"REMOVED": Position("REMOVED", 10, 10)})
    portfolio.state_path.write_text(json.dumps(state.to_dict()))
    before = portfolio.state_path.read_bytes()
    with pytest.raises(ValueError, match="REMOVED"):
        portfolio._load_state()
    assert portfolio.state_path.read_bytes() == before


@pytest.mark.parametrize("price", [None, 0, -1, float("nan"), float("inf")])
def test_held_asset_without_valid_price_is_never_valued_at_zero(price):
    state = PortfolioState(cash=1000, positions={"A": Position("A", 10, 10)})
    with pytest.raises(ValueError, match="A"):
        state.total_value({"A": price} if price is not None else {})


@pytest.mark.parametrize("field,value", [("cash", float("nan")), ("quantity", -1),
                                         ("cost_basis", float("inf")), ("target_weight", float("nan"))])
def test_corrupt_checkpoint_numbers_are_rejected_on_load(field, value):
    state = PortfolioState(cash=1000, positions={"A": Position("A", 10, 10)},
                           pending_intents={"A": PendingIntent("A", 0.5, date(2024, 1, 1))})
    payload = state.to_dict()
    if field == "cash":
        payload[field] = value
    elif field == "target_weight":
        payload["pending_intents"]["A"][field] = value
    else:
        payload["positions"]["A"][field] = value
    with pytest.raises(ValueError):
        PortfolioState.from_dict(payload)
