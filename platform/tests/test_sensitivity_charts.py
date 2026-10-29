import pandas as pd
import pytest

from src.platform_core.visualization import render_sensitivity_charts


@pytest.mark.parametrize("multiple_scenarios", [False, True])
def test_sensitivity_charts_align_dates_with_each_valid_metric(tmp_path, multiple_scenarios):
    rows = [
        {"start_date": "2024-01-02", "annualized_return": .1, "sharpe_ratio": None, "max_drawdown": -.1},
        {"start_date": "2024-03-04", "annualized_return": None, "sharpe_ratio": .5, "max_drawdown": -.2},
        {"start_date": "2024-05-06", "annualized_return": .2, "sharpe_ratio": .8, "max_drawdown": None},
    ]
    if multiple_scenarios:
        rows = [dict(row, slippage_scenario=scenario) for scenario in ("default", "stress") for row in rows]
    path = tmp_path / "sensitivity_summary.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    chart = render_sensitivity_charts(path)
    assert chart is not None and chart.stat().st_size > 0
