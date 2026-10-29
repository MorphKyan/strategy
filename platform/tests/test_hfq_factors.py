from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.platform_core.hfq_factors import sync_corporate_action_hfq_factor


def test_generates_total_return_factor_from_dividend_ledger(tmp_path: Path):
    pd.DataFrame(
        {
            "trade_date": ["2025-11-28", "2025-12-01", "2025-12-02"],
            "close": [118.142, 116.641, 115.981],
        }
    ).to_csv(tmp_path / "511090.csv", index=False)
    pd.DataFrame(
        {
            "code": ["511090"],
            "ex_date": ["2025-12-01"],
            "dividend_per_share": [1.5],
        }
    ).to_csv(tmp_path / "platform_dividends.csv", index=False)

    note = sync_corporate_action_hfq_factor("511090", tmp_path)

    factor = pd.read_csv(tmp_path / "511090_hfq_factor.csv")
    expected = (116.641 + 1.5) / 116.641
    assert factor["hfq_factor"].tolist() == pytest.approx([1.0, expected, expected])
    assert set(factor["source"]) == {"corporate_actions"}
    assert "updated" in note


def test_preserves_existing_unmarked_provider_factor(tmp_path: Path):
    pd.DataFrame({"trade_date": ["2025-12-01"], "close": [116.641]}).to_csv(
        tmp_path / "511090.csv", index=False
    )
    original = "trade_date,hfq_factor\n2025-12-01,9.9\n"
    path = tmp_path / "511090_hfq_factor.csv"
    path.write_text(original, encoding="utf-8")

    note = sync_corporate_action_hfq_factor("511090", tmp_path)

    assert path.read_text(encoding="utf-8") == original
    assert "preserved" in note


def test_ignores_actions_before_local_market_history(tmp_path: Path):
    pd.DataFrame({"trade_date": ["2025-12-01"], "close": [116.641]}).to_csv(
        tmp_path / "511090.csv", index=False
    )
    pd.DataFrame(
        {"code": ["511090"], "ex_date": ["2024-01-01"], "dividend_per_share": [1.5]}
    ).to_csv(tmp_path / "platform_dividends.csv", index=False)

    note = sync_corporate_action_hfq_factor("511090", tmp_path)

    assert not (tmp_path / "511090_hfq_factor.csv").exists()
    assert "no applicable" in note


def test_extends_existing_unmarked_factor_with_new_market_dates(tmp_path: Path):
    pd.DataFrame(
        {
            "trade_date": ["2025-12-01", "2025-12-02"],
            "close": [116.641, 117.000],
        }
    ).to_csv(tmp_path / "511090.csv", index=False)
    original = "trade_date,hfq_factor\n2025-12-01,9.9\n"
    path = tmp_path / "511090_hfq_factor.csv"
    path.write_text(original, encoding="utf-8")

    note = sync_corporate_action_hfq_factor("511090", tmp_path)

    factor = pd.read_csv(path)
    assert len(factor) == 2
    assert factor["trade_date"].tolist() == ["2025-12-01", "2025-12-02"]
    assert factor["hfq_factor"].tolist() == pytest.approx([9.9, 9.9])
    assert factor["source"].tolist() == ["legacy_research", "corporate_actions"]
    assert "extended" in note


def test_extends_existing_factor_compounding_new_dividend(tmp_path: Path):
    pd.DataFrame(
        {
            "trade_date": ["2025-12-01", "2025-12-02", "2025-12-03"],
            "close": [10.0, 9.0, 9.5],
        }
    ).to_csv(tmp_path / "510300.csv", index=False)
    # Existing factor ends at 2025-12-01 with value 2.0
    pd.DataFrame(
        {
            "trade_date": ["2025-12-01"],
            "hfq_factor": [2.0],
            "source": ["legacy_research"],
            "updated_at": ["2025-12-01T00:00:00"],
        }
    ).to_csv(tmp_path / "510300_hfq_factor.csv", index=False)
    # New dividend occurs on 2025-12-02 (1.0 yuan/share)
    pd.DataFrame(
        {
            "code": ["510300"],
            "ex_date": ["2025-12-02"],
            "dividend_per_share": [1.0],
        }
    ).to_csv(tmp_path / "platform_dividends.csv", index=False)

    note = sync_corporate_action_hfq_factor("510300", tmp_path)

    factor = pd.read_csv(tmp_path / "510300_hfq_factor.csv")
    assert len(factor) == 3
    # 2.0 * (9.0 + 1.0) / 9.0 = 2.222222...
    expected_new = 2.0 * (9.0 + 1.0) / 9.0
    assert factor["hfq_factor"].tolist() == pytest.approx([2.0, expected_new, expected_new])
    assert factor["source"].tolist() == ["legacy_research", "corporate_actions", "corporate_actions"]
    assert "extended" in note
    assert "1 new events" in note


def test_extension_keeps_cutoff_dividend_and_defers_cutoff_split(tmp_path):
    days = ["2025-12-01", "2025-12-02", "2025-12-03"]
    pd.DataFrame({"trade_date": days, "close": [10, 5, 4.5]}).to_csv(tmp_path / "A.csv", index=False)
    pd.DataFrame({"code": ["A", "A"], "ex_date": [days[0], days[2]],
                  "dividend_per_share": [3, .5]}).to_csv(tmp_path / "platform_dividends.csv", index=False)
    pd.DataFrame({"code": ["A"], "split_date": [days[0]], "split_ratio": [2]}).to_csv(
        tmp_path / "platform_splits.csv", index=False)
    path = tmp_path / "A_hfq_factor.csv"
    original = "trade_date,hfq_factor,source,updated_at\n2025-12-01,2.0,legacy_research,original\n"
    path.write_text(original, encoding="utf-8")
    sync_corporate_action_hfq_factor("A", tmp_path)
    frame = pd.read_csv(path)
    assert frame["hfq_factor"].tolist() == pytest.approx([2, 4, 4 * 5 / 4.5])
    assert path.read_text(encoding="utf-8").splitlines()[1] == original.splitlines()[1]
    before = path.read_bytes()
    sync_corporate_action_hfq_factor("A", tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("original", [
    "trade_date,legacy_factor\n2025-12-01,9.9\n",
    "trade_date,hfq_factor\nnot-a-date,9.9\n",
    "trade_date,hfq_factor\n2025-12-01,9.9\n2025-12-01,2\n",
    "trade_date,hfq_factor\n2025-12-01,inf\n",
    "trade_date,hfq_factor\n2025-12-01,0\n",
])
def test_invalid_existing_factor_is_never_rebuilt_over_historical_file(tmp_path, original):
    pd.DataFrame({"trade_date": ["2025-12-01", "2025-12-02"], "close": [10, 9]}).to_csv(
        tmp_path / "A.csv", index=False)
    pd.DataFrame({"code": ["A"], "ex_date": ["2025-12-02"], "dividend_per_share": [1]}).to_csv(
        tmp_path / "platform_dividends.csv", index=False)
    path = tmp_path / "A_hfq_factor.csv"
    path.write_text(original)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        sync_corporate_action_hfq_factor("A", tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind,date_column,value_column", [
    ("dividends", "ex_date", "dividend_per_share"),
    ("splits", "split_date", "split_ratio"),
])
@pytest.mark.parametrize("invalid", ["nonfinite", "negative", "missing_date", "duplicate"])
def test_invalid_action_preserves_existing_hfq_history(tmp_path, kind, date_column, value_column, invalid):
    pd.DataFrame({"trade_date": ["2025-12-01", "2025-12-02"], "close": [10, 9]}).to_csv(
        tmp_path / "A.csv", index=False)
    frame = pd.DataFrame({"code": ["A"], date_column: ["2025-12-02"], value_column: [1.]})
    if invalid == "nonfinite":
        frame[value_column] = float("inf")
    elif invalid == "negative":
        frame[value_column] = -1.
    elif invalid == "missing_date":
        frame[date_column] = None
    else:
        frame = pd.concat([frame, frame], ignore_index=True)
    frame.to_csv(tmp_path / f"platform_{kind}.csv", index=False)
    path = tmp_path / "A_hfq_factor.csv"
    path.write_text("trade_date,hfq_factor\n2025-12-01,2.0\n", encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        sync_corporate_action_hfq_factor("A", tmp_path)
    assert path.read_bytes() == before
