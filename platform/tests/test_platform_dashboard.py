from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.platform_dashboard.artifacts import discover_configs, discover_runs, latest_positions, read_run_tables


def test_discover_configs_reads_strategy_and_assets(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "sample.yaml").write_text(
        """
platform:
  run_name: sample_run
assets:
  - asset_id: CN_ETF:510300.SH
    code: "510300"
strategy:
  strategy_name: risk_parity
  params:
    rolling_window: 120
""",
        encoding="utf-8",
    )
    records = discover_configs(tmp_path)
    assert len(records) == 1
    assert records[0].run_name == "sample_run"
    assert records[0].strategy_name == "risk_parity"
    assert records[0].params["rolling_window"] == 120


def test_discover_runs_and_read_tables(tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "backtests" / "sample_run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "sample_run",
                "generated_at": "2026-07-05T10:00:00",
                "metrics": {"total_return": 0.1},
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {"date": "2025-01-01", "net_value": 1.0, "cash": 100.0},
            {"date": "2025-01-02", "net_value": 0.9, "cash": 90.0},
        ]
    ).to_csv(run_dir / "nav.csv", index=False)
    pd.DataFrame(
        [
            {"date": "2025-01-02", "asset_id": "A", "weight": 0.4},
            {"date": "2025-01-02", "asset_id": "B", "weight": 0.6},
        ]
    ).to_csv(run_dir / "positions.csv", index=False)

    runs = discover_runs(tmp_path)
    assert [run.run_id for run in runs] == ["sample_run"]
    tables = read_run_tables(run_dir)
    assert tables["nav"]["drawdown"].tolist() == pytest.approx([0.0, -0.1])
    assert latest_positions(tables["positions"])["asset_id"].tolist() == ["B", "A"]


def test_discover_runs_ignores_non_backtest_manifests(tmp_path: Path) -> None:
    report_dir = tmp_path / "results" / "metadata"
    report_dir.mkdir(parents=True)
    (report_dir / "manifest.json").write_text("{}", encoding="utf-8")
    assert discover_runs(tmp_path) == []
