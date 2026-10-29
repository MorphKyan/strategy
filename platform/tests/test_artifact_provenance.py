import copy
import json

import pandas as pd
import pytest
import yaml

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.runtime_config import apply_runtime_dates
from src.platform_core.slippage import apply_slippage_scenario
from src.platform_core.storage import InMemoryStore


@pytest.mark.parametrize("case,formal", [
    ("fixed", True), ("scenario", True), ("bounded", False), ("generated", False),
    ("unproven", False), ("changed_params", False), ("dated_config", False), ("uneven_history", False),
])
def test_only_proven_fixed_full_history_runs_use_formal_root(tmp_path, monkeypatch, case, formal):
    monkeypatch.setattr("src.platform_core.engine.PLATFORM_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for code in "AB":
        days = ["2024-01-01", "2024-01-02", "2024-01-03"]
        if case == "uneven_history" and code == "B":
            days = days[1:]
        pd.DataFrame({"trade_date": days, "close": 10, "volume": 1000}).to_csv(data_dir / f"{code}.csv", index=False)
    original = {
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": code, "code": code} for code in "AB"],
        "strategy": {"strategy_name": "monthly_equal_weight"},
        "output": {"results_dir": "results/backtests"},
    }
    if case == "dated_config":
        original["backtest"] = {"start_date": "2024-01-01"}
    config_path = tmp_path / "configs" / ("generated/sample.yaml" if case == "generated" else "sample.yaml")
    config_path.parent.mkdir(parents=True)
    config_path.write_text(yaml.safe_dump(original))
    config = copy.deepcopy(original)
    if case == "scenario":
        config = apply_slippage_scenario(config, "stress")
    if case == "bounded":
        config = apply_runtime_dates(config, start_date="2024-01-02")
    if case == "changed_params":
        config["strategy"]["params"] = {"rebalance_threshold": 0.2}
    engine = PlatformBacktestEngine(config, InMemoryStore(),
                                    config_path=None if case == "unproven" else config_path)
    expected = tmp_path / ("results/backtests" if formal else "results/temporary_backtests/direct")
    assert engine.output_dir.parent == expected
    assert engine.artifact_provenance["classification"] == ("fixed_full_history" if formal else "temporary")
    if case == "fixed":
        result = engine.run()
        manifest = json.loads((result.output_dir / "manifest.json").read_text())
        assert manifest["artifact_provenance"]["common_start_date"] == "2024-01-01"
        assert manifest["artifact_provenance"]["end_date"] == "2024-01-03"


def test_explicit_temporary_output_remains_temporary(tmp_path, monkeypatch):
    monkeypatch.setattr("src.platform_core.engine.PLATFORM_ROOT", tmp_path)
    pd.DataFrame({"trade_date": ["2024-01-01"], "close": [10]}).to_csv(tmp_path / "A.csv", index=False)
    config = {"data": {"data_dir": str(tmp_path)}, "assets": [{"asset_id": "A", "code": "A"}],
              "strategy": {"strategy_name": "monthly_equal_weight"}}
    output = tmp_path / "results/temporary_backtests/experiments"
    engine = PlatformBacktestEngine(config, InMemoryStore(), output_dir=output)
    assert engine.output_dir.parent == output


def test_published_index_virtual_fills_are_marked_as_research_simulation(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-02"], "close": [10000, 12000]}).to_csv(
        tmp_path / "000300.csv", index=False)
    config = {"data": {"data_dir": str(tmp_path)},
              "assets": [{"asset_id": "INDEX", "code": "000300", "asset_type": "index"}],
              "strategy": {"strategy_name": "monthly_equal_weight"}, "portfolio": {"initial_cash": 100000},
              "execution": {"fee": {"rate": 0, "min_fee": 0}, "slippage_bps": 0},
              "output": {"results_dir": str(tmp_path / "runs")}}
    result = PlatformBacktestEngine(config, InMemoryStore()).run()
    assert result.metrics["trade_count"] == 1
    manifest = json.loads((result.output_dir / "manifest.json").read_text())
    assert manifest["instrument_semantics"] == {"research_simulation": True, "non_tradable_indices": ["INDEX"]}
    assert "研究模拟" in (result.output_dir / "report.md").read_text()
