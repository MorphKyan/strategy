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
