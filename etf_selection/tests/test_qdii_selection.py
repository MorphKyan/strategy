from types import SimpleNamespace

import pandas as pd
import pytest

from src import selection


@pytest.fixture
def qdii_data(tmp_path, monkeypatch):
    days = pd.bdate_range("2024-06-03", periods=10)
    pd.DataFrame({"trade_date": days, "close_price": [1] * 5 + [1.1] * 5,
                  "nav": 0.1, "acc_nav": 0.1, "volume": 1000, "amount": 1000}).to_csv(
        tmp_path / "513100.csv", index=False)
    pd.DataFrame({"trade_date": days, "hfq_factor": 1}).to_csv(tmp_path / "513100_hfq_factor.csv", index=False)
    (tmp_path / "etf_nav").mkdir()
    pd.DataFrame({"trade_date": days, "unit_nav": 1, "cum_nav": [1] * 8 + [100] * 2}).to_csv(
        tmp_path / "etf_nav/513100.csv", index=False)
    monkeypatch.setattr(selection, "date", SimpleNamespace(today=lambda: days[-1].date()))
    config = {"paths": {"data_dir": str(tmp_path)},
              "selection": {"train_end_date": str(days[-1].date()), "test_start_date": "2024-07-01",
                            "min_history_years": 0.01},
              "candidates": [{"code": "513100", "asset_id": "CN_ETF:513100.SH", "sleeve": "qdii", "ter": 0.006}]}
    return tmp_path, days, config


def test_qdii_selection_uses_guarded_platform_cli_and_reports_both_return_bases(qdii_data):
    data_dir, days, config = qdii_data
    ranking, correlations, _ = selection.screen_sleeves(config)
    row = ranking.iloc[0]
    assert row["eligible"]
    assert row["premium_observed_date"] == str(days[-3].date())
    assert row["premium_start"] == 0
    assert row["premium_end"] == pytest.approx(0.1)
    assert row["nav_annualized_return"] == 0
    assert row["market_annualized_return"] == pytest.approx(1.1 ** (252 / 7) - 1)
    assert row["expense_ratio"] == 0.006
    assert "holding_cost" not in ranking
    selection.write_report(data_dir / "report", ranking, correlations, pd.DataFrame(), {}, [], config)
    report = (data_dir / "report/report.md").read_text(encoding="utf-8")
    assert "市场价年化" in report and "净值年化=0.00%" in report
    assert str(days[-3].date()) in report


@pytest.mark.parametrize("missing", ["nav_file", "cum_nav", "ter"])
def test_missing_qdii_inputs_reject_instead_of_fabricating_scores(qdii_data, missing):
    data_dir, _, config = qdii_data
    path = data_dir / "etf_nav/513100.csv"
    if missing == "nav_file":
        path.unlink()
    elif missing == "cum_nav":
        frame = pd.read_csv(path).drop(columns="cum_nav")
        frame.to_csv(path, index=False)
    else:
        config["candidates"][0].pop("ter")
    ranking, _, candidates = selection.screen_sleeves(config)
    assert not ranking.iloc[0]["eligible"]
    assert "QDII" in ranking.iloc[0]["reject_reason"]
    assert not candidates


def test_unsorted_etf_quotes_do_not_fill_factors_from_future(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-03", "2024-01-02", "2024-01-01"],
                  "close": 10, "volume": 100}).to_csv(tmp_path / "A.csv", index=False)
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-03"], "hfq_factor": [1, 2]}).to_csv(
        tmp_path / "A_hfq_factor.csv", index=False)
    result = selection.load_adjusted_price(tmp_path, {"code": "A"})
    assert result.price.tolist() == [10, 10, 20]


def test_etf_factor_before_first_quote_is_retained(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03"], "close": 10}).to_csv(tmp_path / "A.csv", index=False)
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-04"], "hfq_factor": [2, 3]}).to_csv(
        tmp_path / "A_hfq_factor.csv", index=False)
    assert selection.load_adjusted_price(tmp_path, {"code": "A"}).price.tolist() == [20, 20]
