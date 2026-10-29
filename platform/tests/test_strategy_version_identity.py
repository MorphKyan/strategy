import json
from datetime import date

import pandas as pd
import pytest

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.models import PortfolioState
from src.platform_core.sim import SimPortfolio
from src.platform_core.storage import InMemoryStore
from src.platform_core.strategies.fixed_weight import FixedWeightThresholdStrategy
from src.platform_core.strategy import MonthlyEqualWeightStrategy


@pytest.mark.parametrize("mode", ["backtest", "sim"])
@pytest.mark.parametrize("mismatch", ["class", "parameters"])
def test_runtime_records_actual_strategy_instead_of_trusting_foreign_version_id(tmp_path, mode, mismatch):
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                  "close": 10, "volume": 1000}).to_csv(tmp_path / "A.csv", index=False)
    store = InMemoryStore()
    old_cls = FixedWeightThresholdStrategy if mismatch == "class" else MonthlyEqualWeightStrategy
    old_id = store.ensure_builtin_version(old_cls, {"universe": ["OLD"]})
    config = {"data": {"data_dir": str(tmp_path)}, "assets": [{"asset_id": "A", "code": "A"}],
              "strategy": {"strategy_name": "monthly_equal_weight", "strategy_version_id": old_id,
                           "params": {"universe": ["A"]}},
              "portfolio": {"initial_cash": 10000}, "output": {"results_dir": str(tmp_path / "out")}}
    if mode == "backtest":
        result = PlatformBacktestEngine(config, store).run()
    else:
        portfolio = SimPortfolio("test", config, store, PortfolioState(cash=10000, last_date=date(2024, 1, 1)),
                                 tmp_path / "checkpoint", output_root=tmp_path / "sims")
        result = portfolio.advance("2024-01-03")
    version_id = int(pd.read_csv(result.output_dir / "nav.csv")["strategy_version_id"].iloc[0])
    assert version_id != old_id
    record = store.get_strategy_version(version_id)
    assert record["name"] == "monthly_equal_weight"
    assert json.loads(record["params_json"]) == {"universe": ["A"]}


def test_sim_does_not_restore_runtime_without_matching_source_proof(tmp_path, monkeypatch):
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-02"], "close": 10}).to_csv(tmp_path / "A.csv", index=False)
    config = {"data": {"data_dir": str(tmp_path)}, "assets": [{"asset_id": "A", "code": "A"}],
              "strategy": {"strategy_name": "monthly_equal_weight", "params": {}}}
    state = PortfolioState(cash=1000, last_date=date(2024, 1, 1), strategy_state={
        "_strategy_runtime": {"identity": {"strategy_name": "monthly_equal_weight", "params": {}},
                              "runtime": {"stale": True}}
    })
    observed = []
    monkeypatch.setattr(MonthlyEqualWeightStrategy, "generate_targets", lambda self, context: observed.append(context.runtime.get("stale")))
    portfolio = SimPortfolio("test", config, InMemoryStore(), state, tmp_path / "checkpoint", output_root=tmp_path / "sims")
    portfolio.advance("2024-01-02")
    assert observed == [None]
    assert state.strategy_state["_strategy_runtime"]["identity"]["source_hash"]
