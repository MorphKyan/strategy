import pandas as pd
import pytest

from src.platform_core.metrics import build_platform_metrics


def test_annualization_uses_return_intervals_instead_of_nav_row_count(tmp_path):
    pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=253),
                  "net_value": [1.001**i for i in range(253)]}).to_csv(tmp_path / "nav.csv", index=False)
    metrics = build_platform_metrics(tmp_path)
    assert metrics["annualized_return"] == pytest.approx(1.001**252 - 1)


def test_single_nav_observation_cannot_be_annualized(tmp_path):
    pd.DataFrame({"date": ["2024-01-01"], "net_value": [1.0]}).to_csv(tmp_path / "nav.csv", index=False)
    assert build_platform_metrics(tmp_path)["annualized_return"] is None


def test_active_metrics_include_first_invested_days_cost(tmp_path):
    pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                  "net_value": [1.0, .99, .99]}).to_csv(tmp_path / "nav.csv", index=False)
    pd.DataFrame({"date": ["2024-01-02"], "trade_value": [100], "quantity": [10]}).to_csv(
        tmp_path / "trades.csv", index=False)
    metrics = build_platform_metrics(tmp_path)
    assert metrics["active_observations"] == 2
    assert metrics["annualized_return_active"] == pytest.approx(.99**126 - 1)


def test_initial_holdings_start_active_window_before_later_trade(tmp_path):
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    pd.DataFrame({"date": dates, "net_value": [1, 1.01, 1.02]}).to_csv(tmp_path / "nav.csv", index=False)
    pd.DataFrame({"date": dates, "asset_id": "A", "quantity": 10}).to_csv(tmp_path / "positions.csv", index=False)
    pd.DataFrame({"date": [dates[-1]], "trade_value": [10], "quantity": [1]}).to_csv(tmp_path / "trades.csv", index=False)
    metrics = build_platform_metrics(tmp_path)
    assert metrics["active_observations"] == 3
    assert metrics["annualized_return_active"] == pytest.approx(1.02**126 - 1)
