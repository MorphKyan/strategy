from __future__ import annotations

from pathlib import Path

import yaml
import pandas as pd

from src.selection import build_baskets, generate_platform_configs, screen_sleeves


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


def test_sleeve_screening_and_platform_config_generation(tmp_path: Path):
    data_dir = tmp_path / "data"
    n = 252 * 3 + 5
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
                "strategies": {
                    "segments": [
                        {
                            "start_date": "2020-01-01",
                            "end_date": None,
                            "strategy_name": "risk_parity",
                            "params": {},
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    config = config_for(data_dir, base_config, tmp_path / "generated")
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
