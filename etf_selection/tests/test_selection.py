from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml
import pandas as pd
import pytest

from src.selection import build_baskets, generate_platform_configs, screen_sleeves
from src import selection


def write_market_data(data_dir: Path, code: str, closes: list[float]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = ["trade_date,close_price,volume,amount"]
    factors = ["trade_date,hfq_factor"]
    dates = pd.bdate_range("2020-01-01", periods=len(closes))
    for date_value, close in zip(dates, closes):
        date_text = date_value.strftime("%Y-%m-%d")
        rows.append(f"{date_text},{close},1000,{close * 1000}")
        factors.append(f"{date_text},1")
    (data_dir / f"{code}.csv").write_text("\n".join(rows), encoding="utf-8")
    (data_dir / f"{code}_hfq_factor.csv").write_text("\n".join(factors), encoding="utf-8")


def config_for(data_dir: Path, base_config: Path, generated_dir: Path) -> dict:
    return {
        "selection": {
            "min_history_years": 3,
            "top_k_per_sleeve": 2,
            "max_baskets": 5,
            "required_sleeves": ["gold", "hs300", "commodity", "bond"],
            "commodity": {"prefer_broad": True, "min_single_commodity_count": 2, "max_single_commodity_count": 2},
        },
        "paths": {
            "data_dir": str(data_dir),
            "platform_base_config": str(base_config),
            "generated_config_dir": str(generated_dir),
        },
        "candidates": [
            {"asset_id": "G", "code": "G", "name": "Gold", "exchange": "SH", "sleeve": "gold", "subtype": "gold", "include": True},
            {"asset_id": "E", "code": "E", "name": "HS300", "exchange": "SH", "sleeve": "hs300", "subtype": "hs300", "include": True},
            {"asset_id": "B", "code": "B", "name": "Bond", "exchange": "SH", "sleeve": "bond", "subtype": "government_bond", "include": True},
            {
                "asset_id": "C1",
                "code": "C1",
                "name": "Commodity 1",
                "exchange": "SH",
                "sleeve": "commodity",
                "subtype": "single_energy",
                "include": True,
            },
            {
                "asset_id": "C2",
                "code": "C2",
                "name": "Commodity 2",
                "exchange": "SH",
                "sleeve": "commodity",
                "subtype": "single_metals",
                "include": True,
            },
        ],
    }


def test_sleeve_screening_and_platform_config_generation(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    n = 252 * 3 + 5
    monkeypatch.setattr(selection, "date", SimpleNamespace(today=lambda: pd.bdate_range("2020-01-01", periods=n)[-1].date()))
    write_market_data(data_dir, "G", [10 + i * 0.01 for i in range(n)])
    write_market_data(data_dir, "E", [20 + i * 0.02 for i in range(n)])
    write_market_data(data_dir, "B", [30 + i * 0.005 for i in range(n)])
    write_market_data(data_dir, "C1", [40 + i * 0.015 for i in range(n)])
    write_market_data(data_dir, "C2", [50 + i * 0.012 for i in range(n)])

    base_config = tmp_path / "platform_base.yaml"
    base_config.write_text(
        yaml.safe_dump(
            {
                "platform": {"run_name": "base"},
                "data": {"data_dir": "data"},
                "assets": [],
                "portfolio": {"initial_cash": 1000, "initial_equity": 1000, "initial_positions": []},
                "backtest": {"start_date": "2020-01-01", "end_date": "2022-01-28"},
                "execution": {"fee": {"rate": 0, "min_fee": 0}},
                "strategy": {"strategy_name": "risk_parity", "params": {"universe": ["OLD"]}},
            }
        ),
        encoding="utf-8",
    )
    config = config_for(data_dir, base_config, tmp_path / "generated")
    config["candidates"][2]["asset_type"] = "index"
    ranking, sleeve_corrs, candidates = screen_sleeves(config)
    baskets, basket_corrs, basket_codes = build_baskets(config, ranking, candidates)
    paths = generate_platform_configs(base_config, tmp_path / "generated", baskets, candidates)

    assert set(ranking["sleeve"]) == {"gold", "hs300", "bond", "commodity"}
    assert ranking["eligible"].all()
    assert "commodity" in sleeve_corrs
    assert not baskets.empty
    assert basket_codes
    assert basket_corrs
    assert paths
    generated = yaml.safe_load(paths[0].read_text(encoding="utf-8"))
    assert len(generated["assets"]) == 5
    assert generated["selection_metadata"]["codes"]
    assert generated["strategy"]["params"]["universe"] == [asset["asset_id"] for asset in generated["assets"]]
    assert "strategies" not in generated
    assert baskets["research_simulation"].all()
    index_asset = next(asset for asset in generated["assets"] if asset["asset_type"] == "index")
    assert index_asset["lot_size"] == 1 and index_asset["price_limit_pct"] is None
    assert generated["selection_metadata"]["non_tradable_indices"] == ["B"]
    selection.write_report(tmp_path / "report", ranking, sleeve_corrs, baskets, basket_corrs, paths, config)
    assert "研究模拟（含不可交易指数）" in (tmp_path / "report/report.md").read_text()


def test_screening_reports_missing_candidates_without_crashing(tmp_path: Path):
    config = config_for(tmp_path, tmp_path / "base.yaml", tmp_path / "generated")
    ranking, correlations, candidates = screen_sleeves(config)
    assert not ranking["eligible"].any()
    assert (ranking["sleeve_score"] == 0).all()
    assert not correlations and not candidates


def test_generated_yaml_and_reports_do_not_overwrite_existing_artifacts(tmp_path):
    path = tmp_path / "generated.yaml"
    selection.write_yaml(path, {"old": True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        selection.write_yaml(path, {"old": False})
    assert path.read_bytes() == before

    report_dir = tmp_path / "report"
    selection.write_report(report_dir, pd.DataFrame(), {}, pd.DataFrame(), {}, [])
    before = (report_dir / "summary.json").read_bytes()
    with pytest.raises(FileExistsError):
        selection.write_report(report_dir, pd.DataFrame(), {}, pd.DataFrame(), {}, [])
    assert (report_dir / "summary.json").read_bytes() == before


@pytest.mark.parametrize("explicit_null", [False, True])
def test_generated_index_defaults_and_explicit_null_limit_are_preserved(explicit_null):
    meta = {"asset_id": "INDEX", "code": "000300", "asset_type": "index"}
    if explicit_null:
        meta["price_limit_pct"] = None
    result = selection.platform_asset(meta)
    assert result["lot_size"] == 1
    assert result["price_limit_pct"] is None


@pytest.mark.parametrize("empty_ranking", [False, True])
def test_no_valid_baskets_returns_empty_results(tmp_path: Path, empty_ranking: bool, monkeypatch):
    data_dir = tmp_path / "data"
    config = config_for(data_dir, tmp_path / "base.yaml", tmp_path / "generated")
    monkeypatch.setattr(selection, "date", SimpleNamespace(today=lambda: pd.Timestamp("2020-01-03").date()))
    for item in config["candidates"]:
        write_market_data(data_dir, item["code"], [10.0, 10.1, 10.2])
    config["selection"]["min_history_years"] = 0
    ranking, _, candidates = screen_sleeves(config)
    if empty_ranking:
        ranking = pd.DataFrame()
    baskets, correlations, codes = build_baskets(config, ranking, candidates)
    assert baskets.empty
    assert not correlations and not codes


def test_stale_candidate_stops_screening(tmp_path):
    write_market_data(tmp_path, "G", [10, 11, 12])
    config = config_for(tmp_path, tmp_path / "base.yaml", tmp_path / "generated")
    with pytest.raises(RuntimeError, match="行情过期"):
        screen_sleeves(config)


def test_unaligned_candidate_dates_stop_screening(tmp_path, monkeypatch):
    write_market_data(tmp_path, "G", [10, 11, 12])
    write_market_data(tmp_path, "E", [10, 11])
    monkeypatch.setattr(selection, "date", SimpleNamespace(today=lambda: pd.Timestamp("2020-01-06").date()))
    with pytest.raises(RuntimeError, match="未对齐"):
        screen_sleeves(config_for(tmp_path, tmp_path / "base.yaml", tmp_path / "generated"))
