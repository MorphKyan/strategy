import pytest
import pandas as pd

from src.platform_core.data_store import assets_from_config
from src.platform_core.engine import PlatformBacktestEngine, load_strategy_config
from src.platform_core.execution import ExecutionConfig, FeeProfile
from src.platform_core.storage import InMemoryStore


@pytest.mark.parametrize("field,value", [("asset_id", "A"), ("code", "AAA")])
def test_duplicate_assets_cannot_be_silently_replaced_by_dict_construction(field, value):
    items = [{"asset_id": "A", "code": "AAA"}, {"asset_id": "B", "code": "BBB"}]
    items[1][field] = value
    with pytest.raises(ValueError, match="Duplicate"):
        assets_from_config(items)


@pytest.mark.parametrize("lot", [0, -1, 1.5, float("nan")])
def test_invalid_lot_size_is_not_silently_rounded_or_replaced(lot):
    with pytest.raises(ValueError, match="lot_size"):
        assets_from_config([{"asset_id": "A", "code": "AAA", "lot_size": lot}])


@pytest.mark.parametrize("kwargs", [
    {"slippage_bps": 20000}, {"slippage_by_code": {"AAA": float("nan")}},
    {"cash_buffer_pct": float("nan")}, {"weight_tolerance": float("nan")},
    {"price_field": "volume"}, {"round_mode": "nearest"},
])
def test_invalid_execution_settings_fail_before_they_change_cash_or_fill_prices(kwargs):
    with pytest.raises(ValueError):
        ExecutionConfig(fee_profile=FeeProfile(), **kwargs)


@pytest.mark.parametrize("params", [None, ["A"], {"universe": ["A", "A"]}, {"universe": "A"}])
def test_strategy_parameters_reject_ambiguous_universe_or_non_mapping(params):
    with pytest.raises(ValueError):
        load_strategy_config({"strategy_name": "monthly_equal_weight", "params": params})


def test_index_defaults_are_not_etf_lot_and_limit_defaults():
    assets = assets_from_config([{"asset_id": "INDEX", "code": "000300", "asset_type": "index"},
                                 {"asset_id": "ETF", "code": "510300", "asset_type": "etf"}])
    assert assets[0].lot_size == 1 and assets[0].price_limit_pct is None
    assert assets[1].lot_size == 100 and assets[1].price_limit_pct == 0.1


@pytest.mark.parametrize("positions", [
    [{"asset_id": "A", "quantity": -1}], [{"asset_id": "A", "quantity": float("nan")}],
    [{"asset_id": "A", "cost_basis": -1}], [{"asset_id": "A", "cost_basis": float("inf")}],
    [{"asset_id": "A", "quantity": 1}, {"asset_id": "A", "quantity": 2}],
])
def test_bad_initial_positions_fail_before_backtest_artifacts_are_written(tmp_path, positions):
    pd.DataFrame({"trade_date": ["2024-01-01"], "close": [10]}).to_csv(tmp_path / "A.csv", index=False)
    config = {"data": {"data_dir": str(tmp_path)}, "assets": [{"asset_id": "A", "code": "A"}],
              "strategy": {"strategy_name": "monthly_equal_weight"},
              "portfolio": {"initial_cash": 1000, "initial_positions": positions},
              "output": {"results_dir": str(tmp_path / "runs")}}
    with pytest.raises(ValueError):
        PlatformBacktestEngine(config, InMemoryStore()).run()
    assert not (tmp_path / "runs").exists()
