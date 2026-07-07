from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.platform_dashboard.artifacts import (
    align_navs,
    discover_configs,
    discover_runs,
    latest_positions,
    nav_analytics,
    read_run_tables,
    rebase_benchmark,
    window_start_date,
)


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


def _make_nav(start: str, periods: int, daily_ret: float, base: float = 1.0) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=periods)
    values = base * (1 + daily_ret) ** pd.RangeIndex(periods)
    return pd.DataFrame({"date": dates, "net_value": values})


def test_nav_analytics_derives_multi_scale_returns() -> None:
    nav = _make_nav("2024-07-01", 300, 0.001)
    analytics = nav_analytics(nav)

    assert analytics["daily"]["ret"].iloc[0] == pytest.approx(0.001)
    monthly_pivot = analytics["monthly_pivot"]
    assert set(monthly_pivot.index) == {2024, 2025}
    assert list(monthly_pivot.columns) == list(range(1, 13))
    # 2024 年度收益 = 2024 年内净值终点 / 起点 - 1
    year_2024 = analytics["yearly"].set_index("year").loc["2024", "ret"]
    nav_2024 = nav[nav["date"].dt.year == 2024]["net_value"]
    assert year_2024 == pytest.approx(nav_2024.iloc[-1] / nav["net_value"].iloc[0] - 1)
    assert "vol_60d" in analytics["rolling"].columns


def test_nav_analytics_handles_empty_and_short_input() -> None:
    for nav in (pd.DataFrame(), _make_nav("2025-01-01", 1, 0.0)):
        analytics = nav_analytics(nav)
        assert all(frame.empty for frame in analytics.values())


def test_rebase_benchmark_intersects_and_scales() -> None:
    candidate = _make_nav("2025-01-01", 10, 0.001)
    benchmark = _make_nav("2025-01-08", 10, 0.002, base=100.0)
    rebased = rebase_benchmark(candidate, benchmark)

    common_start = rebased["date"].min()
    candidate_at_start = candidate.loc[candidate["date"] == common_start, "net_value"].iloc[0]
    assert rebased["net_value"].iloc[0] == pytest.approx(candidate_at_start)
    assert rebased["date"].max() <= candidate["date"].max()


def test_rebase_benchmark_returns_empty_without_overlap() -> None:
    candidate = _make_nav("2025-01-01", 5, 0.001)
    benchmark = _make_nav("2025-03-01", 5, 0.001)
    assert rebase_benchmark(candidate, benchmark).empty


def test_window_start_date_maps_period_labels() -> None:
    last = pd.Timestamp("2026-07-03")
    assert window_start_date(last, "近1月") == pd.Timestamp("2026-06-03")
    assert window_start_date(last, "近2年") == pd.Timestamp("2024-07-03")
    assert window_start_date(last, "今年") == pd.Timestamp("2026-01-01")
    assert window_start_date(last, "全部") is None
    assert window_start_date(last, "未知标签") is None


def test_align_navs_rebases_to_common_window() -> None:
    navs = {
        "a": _make_nav("2025-01-01", 30, 0.001),
        "b": _make_nav("2025-01-15", 30, -0.001, base=2.0),
    }
    aligned = align_navs(navs, overlap_only=True)

    assert set(aligned["run_id"]) == {"a", "b"}
    firsts = aligned.groupby("run_id").first()
    assert firsts["net_value"].tolist() == pytest.approx([1.0, 1.0])
    assert aligned["date"].min() == pd.Timestamp("2025-01-15")
    assert (aligned["drawdown"] <= 1e-12).all()


def test_align_navs_rebases_at_start_date() -> None:
    navs = {
        "a": _make_nav("2025-01-01", 60, 0.001),
        "b": _make_nav("2025-01-01", 60, 0.002, base=2.0),
    }
    aligned = align_navs(navs, overlap_only=True, start_date=pd.Timestamp("2025-02-01"))

    assert aligned["date"].min() >= pd.Timestamp("2025-02-01")
    firsts = aligned.groupby("run_id")["net_value"].first()
    assert firsts.tolist() == pytest.approx([1.0, 1.0])


def test_align_navs_returns_empty_when_overlap_required_but_absent() -> None:
    navs = {
        "a": _make_nav("2025-01-01", 5, 0.001),
        "b": _make_nav("2025-03-01", 5, 0.002),
    }

    assert align_navs(navs, overlap_only=True).empty
