import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.platform_core.data_store import validate_market_dates


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.chdir(Path.cwd())
    return (importlib.import_module("scripts.analyze_es_robustness"),
            importlib.import_module("scripts.summarize_es_robustness"))


def _config(data_dir):
    data_dir.mkdir(exist_ok=True)
    for code in ("111111", "222222"):
        pd.DataFrame({"trade_date": pd.date_range("2024-01-03", periods=3),
                      "close": [10., 11., 12.]}).to_csv(data_dir / f"{code}.csv", index=False)
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-04"], "hfq_factor": [2., 3.]}).to_csv(
        data_dir / "111111_hfq_factor.csv", index=False)
    return {"assets": [{"asset_id": a, "code": c, "asset_type": "index"} for a, c in zip("AB", ("111111", "222222"))],
            "data": {"data_dir": str(data_dir)},
            "strategy": {"strategy_name": "risk_parity_expected_shortfall_fixed_budget",
                         "params": {"universe": ["A", "B"], "risk_budgets": {"A": 1e308, "B": 1e308}}}}


def test_diagnostics_use_configured_data_dir_and_shared_asof_adjustment(tmp_path, modules):
    analyze, _ = modules
    prices, universe, budgets = analyze.config_prices(_config(tmp_path))
    assert prices["A"].tolist() == [20., 33., 36.]
    assert universe == ["A", "B"]
    assert budgets == pytest.approx([.5, .5])


def test_diagnostics_do_not_bypass_current_market_freshness(tmp_path, modules, monkeypatch):
    analyze, _ = modules
    config = _config(tmp_path)
    monkeypatch.setattr("src.platform_core.data.validate_market_dates", validate_market_dates)
    with pytest.raises(RuntimeError, match="Stale"):
        analyze.config_prices(config)


def test_zero_risk_diagnostics_cannot_be_reported_as_zero_budget_error(modules):
    analyze, _ = modules
    with pytest.raises(ValueError, match="undefined"):
        analyze.es_risk_contributions(np.zeros((10, 2)), np.array([.5, .5]), .95)


def test_failed_bootstrap_reports_counts_instead_of_indexing_empty_matrix(modules, monkeypatch):
    analyze, _ = modules
    calls = []

    def solve(*args):
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("solver failure")
        return np.array([.5, .5]), None

    monkeypatch.setattr(analyze, "solve_weights", solve)
    prices = pd.DataFrame({"A": np.arange(10.) + 10, "B": np.arange(10.) + 20},
                          index=pd.bdate_range("2024-01-01", periods=10))
    with pytest.raises(RuntimeError, match="successful.*failed=3"):
        analyze.bootstrap_rows("test", prices, ["A", "B"], np.array([.5, .5]), [5], ["historical"],
                               .95, .94, 3, 2, np.random.default_rng(1))


def test_generated_configs_refuse_to_overwrite_previous_run(tmp_path, modules):
    analyze, _ = modules
    config = _config(tmp_path / "data")
    arguments = (config, "test", [5], ["historical"], .9, .94, tmp_path / "generated")
    path, = analyze.generate_configs(*arguments)
    before = path.read_bytes()
    assert yaml.safe_load(before)["strategy"]["params"]["confidence_level"] == .9
    with pytest.raises(FileExistsError):
        analyze.generate_configs(*arguments)
    assert path.read_bytes() == before


def test_analysis_refuses_existing_output_before_loading_inputs(tmp_path, modules, monkeypatch):
    analyze, _ = modules
    path = tmp_path / "old.csv"
    path.write_text("saved")
    monkeypatch.setattr(sys, "argv", ["analyze", "--output-dir", str(tmp_path)])
    with pytest.raises(FileExistsError):
        analyze.main()
    assert path.read_text() == "saved"


def _sensitivities(root):
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({
        "config": r"Z:\old\es_robustness_etf_511090_w120_historical.yaml",
        "summary_csv": r"Z:\old\sensitivity_summary.csv",
    }))
    frame = pd.DataFrame({"start_date": ["2020-01-01", "2024-01-01"], "active_observations": [130, 140],
                          "slippage_scenario": ["default", "default"]})
    for column in ["annualized_return_active", "active_sharpe_ratio", "max_drawdown", "annualized_turnover",
                   "trade_count", "order_count", "rejected_order_count", "average_cash_weight"]:
        frame[column] = .1
    frame.to_csv(root / "sensitivity_summary.csv", index=False)
    return root


def test_sensitivity_summary_has_no_hidden_date_cutoff_and_handles_moved_windows_artifacts(tmp_path, modules):
    _, summary = modules
    root = _sensitivities(tmp_path / "sensitivity")
    raw, all_starts = summary.summarize_sensitivities(root, 126)
    assert len(raw) == 2
    assert all_starts["valid_start_count"].tolist() == [2]
    _, bounded = summary.summarize_sensitivities(root, 126, "2023-01-01")
    assert bounded["valid_start_count"].tolist() == [1]


def test_weight_comparison_accepts_single_method_or_proxy(modules):
    _, summary = modules
    frame = pd.DataFrame({"proxy": ["etf_511090"], "window": [120], "method": ["historical"],
                          "date": ["2024-01-01"], "weight::CN_ETF:511090.SH": [1.]})
    proxy, method = summary.summarize_weight_comparisons(frame)
    assert proxy.empty and method.empty


def test_summary_reads_saved_metrics_and_allows_runs_without_trades(tmp_path, modules, monkeypatch):
    _, summary = modules
    run = tmp_path / "backtests/run"
    run.mkdir(parents=True)
    (run / "config_snapshot.yaml").write_text(yaml.safe_dump({"strategy": {"params": {
        "universe": ["CN_ETF:511090.SH"], "rolling_window": 120,
    }}}))
    (run / "manifest.json").write_text(json.dumps({"execution_model": {"slippage_scenario": "default"},
                                                   "metrics": {"annualized_return": .321}}))
    (run / "metrics.json").write_text(json.dumps({"annualized_return": .123, "trade_count": 0}))
    (run / "trades.csv").write_text("\n")
    (run / "positions.csv").write_text("\n")
    reports = _sensitivities(tmp_path / "sensitivity")
    output = tmp_path / "summary"
    monkeypatch.setattr(sys, "argv", ["summary", "--backtest-root", str(run.parent),
                                      "--sensitivity-report-root", str(reports), "--output-dir", str(output)])
    assert summary.main() == 0
    performance = pd.read_csv(output / "backtest_performance.csv")
    assert performance["annualized_return"].tolist() == [.123]
    assert pd.read_csv(output / "execution_risk_budget_summary.csv").empty
    before = (output / "backtest_performance.csv").read_bytes()
    with pytest.raises(FileExistsError):
        summary.main()
    assert (output / "backtest_performance.csv").read_bytes() == before


def test_tracking_summary_requires_actual_variation_and_common_observations(modules):
    analyze, _ = modules
    etf = pd.DataFrame({"CN_ETF:511090.SH": [100., 101., 103.]}, index=pd.bdate_range("2024-01-01", periods=3))
    index = pd.DataFrame({"CN_INDEX:CBA21801.CS": [100., 100., 100.]}, index=etf.index)
    with pytest.raises(ValueError, match="nonzero volatility"):
        analyze.tracking_summary(etf, index)
    index.iloc[:, 0] = [100., 101., 103.]
    assert analyze.tracking_summary(etf, index)["downside_correlation"] is None
