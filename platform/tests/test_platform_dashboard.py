from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.platform_dashboard.artifacts import (
    RunRecord,
    align_navs,
    asset_code,
    build_weighted_portfolio,
    business_days_behind,
    discover_configs,
    discover_portfolios,
    downsample_timeseries,
    discover_runs,
    effective_nav_start_date,
    filter_runs,
    latest_positions,
    latest_ticket,
    list_tickets,
    market_history_for_window,
    infer_slippage_scenario,
    max_drawdown,
    nav_analytics,
    nav_summary_metrics,
    position_weights,
    read_portfolio_nav,
    read_run_metrics,
    read_sim_run_table,
    read_ticket_orders,
    read_run_table,
    read_run_tables,
    read_corporate_actions,
    read_market_history,
    portfolio_risk_analysis,
    rebalance_events,
    rebase_benchmark,
    trailing_returns,
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


def test_filter_runs_matches_multiple_metadata_terms(tmp_path: Path) -> None:
    runs = [
        RunRecord("risk_parity_training_default", tmp_path / "default", "", "2020-01-01", "2025-06-30", {},
                  {"strategy": {"strategy_name": "risk_parity"}, "slippage_scenario": "default"}),
        RunRecord("fixed_weight_stress", tmp_path / "stress", "", "2021-01-01", "2025-06-30", {},
                  {"strategy": {"strategy_name": "fixed_weight"}, "slippage_scenario": "stress"}),
    ]

    assert filter_runs(runs, "RISK default") == [runs[0]]
    assert filter_runs(runs, "2021 stress") == [runs[1]]
    assert filter_runs(runs, "missing") == []


def test_single_table_reader_is_lazy_and_validates_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    pd.DataFrame([{"date": "2025-01-01", "net_value": 1.0}]).to_csv(run_dir / "nav.csv", index=False)
    nav = read_run_table(run_dir, "nav")
    assert list(nav.columns) == ["date", "net_value", "drawdown"]
    assert read_run_table(run_dir, "positions").empty
    with pytest.raises(ValueError, match="Unsupported run table"):
        read_run_table(run_dir, "unknown")


def test_nav_reader_trims_cash_only_prefix_and_keeps_pretrade_baseline(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    pd.DataFrame(
        [
            {"date": "2020-01-01", "net_value": 1.0, "cash": 100.0},
            {"date": "2020-01-02", "net_value": 1.0, "cash": 100.0},
            {"date": "2020-01-03", "net_value": 1.0, "cash": 100.0},
            {"date": "2020-01-06", "net_value": 1.02, "cash": 2.0},
            {"date": "2020-01-07", "net_value": 1.01, "cash": 2.0},
        ]
    ).to_csv(run_dir / "nav.csv", index=False)
    pd.DataFrame([{"date": "2020-01-06", "trade_id": "T1"}]).to_csv(run_dir / "trades.csv", index=False)

    assert effective_nav_start_date(run_dir) == pd.Timestamp("2020-01-03")
    nav = read_run_table(run_dir, "nav")
    assert nav["date"].tolist() == list(pd.to_datetime(["2020-01-03", "2020-01-06", "2020-01-07"]))
    assert nav["drawdown"].tolist() == pytest.approx([0.0, 0.0, 1.01 / 1.02 - 1])


def test_dashboard_metrics_use_effective_nav_window(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(json.dumps({"execution_model": {}}), encoding="utf-8")
    pd.DataFrame(
        [
            {"date": "2020-01-01", "net_value": 1.0, "total_value": 100.0, "cash": 100.0},
            {"date": "2020-01-02", "net_value": 1.0, "total_value": 100.0, "cash": 100.0},
            {"date": "2020-01-03", "net_value": 1.0, "total_value": 100.0, "cash": 100.0},
            {"date": "2020-01-06", "net_value": 1.1, "total_value": 110.0, "cash": 1.0},
        ]
    ).to_csv(run_dir / "nav.csv", index=False)
    pd.DataFrame([{"date": "2020-01-06", "trade_id": "T1", "trade_value": 99.0}]).to_csv(
        run_dir / "trades.csv", index=False
    )

    metrics = read_run_metrics(run_dir)
    assert metrics["start_date"] == "2020-01-03"
    assert metrics["observations"] == 2
    assert metrics["total_return"] == pytest.approx(0.1)


def test_discovery_does_not_generate_missing_metrics(tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "backtests" / "lazy_run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": "lazy_run", "generated_at": "2026-07-05T10:00:00"}), encoding="utf-8"
    )
    pd.DataFrame([
        {"date": "2025-01-01", "net_value": 1.0},
        {"date": "2025-01-02", "net_value": 1.1},
    ]).to_csv(run_dir / "nav.csv", index=False)

    runs = discover_runs(tmp_path)
    assert runs[0].metrics == {}
    assert not (run_dir / "metrics.json").exists()
    assert read_run_metrics(run_dir)["total_return"] == pytest.approx(0.1)


def test_discover_runs_ignores_non_backtest_manifests(tmp_path: Path) -> None:
    report_dir = tmp_path / "results" / "metadata"
    report_dir.mkdir(parents=True)
    (report_dir / "manifest.json").write_text("{}", encoding="utf-8")
    assert discover_runs(tmp_path) == []


def test_discover_runs_skips_sensitivity_raw_and_cache(tmp_path: Path) -> None:
    # 敏感性/缓存原始目录数量巨大（38 起点 × 3 场景），不进看板；
    # sim/live 组合推进产物属于组合页（蓝图 B3/B4），混进回测列表会出现空行
    for excluded in ("sensitivity_raw", "backtest_cache", "sim_portfolios", "live_portfolios"):
        run_dir = tmp_path / "results" / excluded / "strategy_x" / "run_1"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text(json.dumps({"run_id": f"{excluded}_run"}), encoding="utf-8")
        pd.DataFrame([{"date": "2025-01-01", "net_value": 1.0}]).to_csv(run_dir / "nav.csv", index=False)
    assert discover_runs(tmp_path) == []


def test_discover_runs_loads_temporary_root_only_when_enabled(tmp_path: Path) -> None:
    fixed_dir = tmp_path / "results" / "backtests" / "fixed_run"
    temporary_dir = tmp_path / "results" / "temporary_backtests" / "direct" / "temporary_run"
    sensitivity_dir = tmp_path / "results" / "temporary_backtests" / "sensitivity" / "sensitivity_run"
    unrelated_dir = tmp_path / "results" / "other" / "unrelated_run"
    for run_dir, run_id in (
        (fixed_dir, "fixed_run"),
        (temporary_dir, "temporary_run"),
        (sensitivity_dir, "sensitivity_run"),
        (unrelated_dir, "unrelated_run"),
    ):
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text(
            json.dumps({"run_id": run_id, "generated_at": "2026-07-05T10:00:00"}),
            encoding="utf-8",
        )
        pd.DataFrame([{"date": "2025-01-01", "net_value": 1.0}]).to_csv(run_dir / "nav.csv", index=False)

    assert [run.run_id for run in discover_runs(tmp_path)] == ["fixed_run"]
    assert {run.run_id for run in discover_runs(tmp_path, include_temporary=True)} == {
        "fixed_run",
        "temporary_run",
    }


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


def test_market_history_actions_and_weighted_portfolio(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    for symbol, closes in (("510300", [10, 11, 12]), ("518880", [20, 19, 21])):
        pd.DataFrame({"trade_date": pd.date_range("2025-01-01", periods=3), "open": closes,
                      "high": closes, "low": closes, "close": closes, "volume": [1, 2, 3]}).to_csv(data / f"{symbol}.csv", index=False)
    pd.DataFrame([{"code": "510300", "ex_date": "2025-01-02", "dividend_per_share": 0.1}]).to_csv(data / "platform_dividends.csv", index=False)
    pd.DataFrame([{"code": "510300", "split_date": "2025-01-03", "split_ratio": 2.0}]).to_csv(data / "platform_splits.csv", index=False)

    first = read_market_history(tmp_path, "510300")
    second = read_market_history(tmp_path, "518880")
    actions = read_corporate_actions(tmp_path, "510300")
    basket = build_weighted_portfolio({"510300": first, "518880": second}, {"510300": 0.6, "518880": 0.4})
    assert actions["dividends"]["dividend_per_share"].iloc[0] == pytest.approx(0.1)
    assert actions["splits"]["split_ratio"].iloc[0] == pytest.approx(2.0)
    assert basket["portfolio"].iloc[0] == pytest.approx(1.0)
    assert basket["portfolio"].iloc[-1] == pytest.approx(0.6 * 1.2 + 0.4 * 1.05)
    assert "drawdown" in basket


def test_market_history_for_window_uses_inclusive_backtest_dates() -> None:
    history = pd.DataFrame({
        "trade_date": pd.date_range("2025-01-01", periods=6),
        "close": range(10, 16),
    })

    sliced = market_history_for_window(history, "2025-01-02", "2025-01-04")

    assert sliced["trade_date"].tolist() == list(pd.date_range("2025-01-02", "2025-01-04"))
    assert sliced["close"].tolist() == [11, 12, 13]


def test_rebalance_events_aggregates_filled_orders() -> None:
    orders = pd.DataFrame([
        {"date": "2025-01-03", "signal_date": "2025-01-02", "status": "FILLED", "trade_value": 100},
        {"date": "2025-01-03", "signal_date": "2025-01-02", "status": "FILLED", "trade_value": -50},
        {"date": "2025-01-04", "signal_date": "2025-01-03", "status": "REJECTED", "trade_value": 20},
    ])
    events = rebalance_events(orders)
    assert len(events) == 1
    assert events["order_count"].iloc[0] == 2
    assert events["trade_value"].iloc[0] == pytest.approx(150)


def test_portfolio_risk_analysis_and_downsampling() -> None:
    histories = {
        "A": pd.DataFrame({"trade_date": pd.date_range("2025-01-01", periods=300), "close": range(100, 400)}),
        "B": pd.DataFrame({"trade_date": pd.date_range("2025-01-01", periods=300), "close": range(200, 500)}),
    }
    risk = portfolio_risk_analysis(histories, {"A": 0.6, "B": 0.4}, window=120)
    assert risk["correlation"].shape == (2, 2)
    assert risk["contribution"]["risk_contribution_pct"].sum() == pytest.approx(1.0)
    sampled = downsample_timeseries(histories["A"], max_points=50)
    assert len(sampled) <= 50
    assert sampled.iloc[0]["trade_date"] == histories["A"].iloc[0]["trade_date"]
    assert sampled.iloc[-1]["trade_date"] == histories["A"].iloc[-1]["trade_date"]


def test_slippage_scenario_inference_is_explicit_and_safe() -> None:
    assert infer_slippage_scenario("run_x", {"slippage_scenario": "stress"}) == "stress"
    assert infer_slippage_scenario("strategy_dynamic_participation_123", {}) == "dynamic_participation"
    assert infer_slippage_scenario("legacy_run", {}) == "unknown"


# ---------------------------------------------------------------- 组合页（蓝图 B3/B4）


def _write_state(portfolio_dir: Path, cash: float = 1000.0, pending: dict | None = None) -> None:
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    (portfolio_dir / "portfolio_state.json").write_text(
        json.dumps(
            {
                "cash": cash,
                "positions": {
                    "CN_ETF:510300.SH": {"asset_id": "CN_ETF:510300.SH", "quantity": 1000.0, "cost_basis": 4.0},
                    "CN_ETF:518880.SH": {"asset_id": "CN_ETF:518880.SH", "quantity": 500.0, "cost_basis": 8.0},
                },
                "pending_intents": pending or {},
                "cooldown_pool": {},
                "strategy_state": {},
                "last_date": "2026-07-10",
                "dividend_receivables": [],
            }
        ),
        encoding="utf-8",
    )


def test_discover_portfolios_and_nav_readers(tmp_path: Path) -> None:
    live_dir = tmp_path / "results" / "live_portfolios" / "live_x"
    _write_state(live_dir)
    pd.DataFrame(
        [
            {"date": "2026-07-09", "cash": 100.0, "positions_value": 900.0, "total_value": 1000.0},
            {"date": "2026-07-10", "cash": 100.0, "positions_value": 950.0, "total_value": 1050.0},
        ]
    ).to_csv(live_dir / "real_nav.csv", index=False)

    # sim 全史 = runs 增量段拼接；同日重复保留更新一段（advance 重跑场景）
    sim_dir = tmp_path / "results" / "sim_portfolios" / "sim_y"
    _write_state(sim_dir)
    for run_name, rows in (
        ("2026-07-09_100000", [{"date": "2026-07-08", "total_value": 2.0}, {"date": "2026-07-09", "total_value": 2.1}]),
        ("2026-07-10_100000", [{"date": "2026-07-09", "total_value": 2.15}, {"date": "2026-07-10", "total_value": 2.2}]),
    ):
        run_dir = sim_dir / "runs" / run_name
        run_dir.mkdir(parents=True)
        pd.DataFrame(rows).to_csv(run_dir / "nav.csv", index=False)

    records = discover_portfolios(tmp_path)
    assert [(item.kind, item.portfolio_id) for item in records] == [("live", "live_x"), ("sim", "sim_y")]
    assert records[0].state["cash"] == pytest.approx(1000.0)

    live_nav = read_portfolio_nav(live_dir, "live")
    assert list(live_nav["net_value"]) == pytest.approx([1000.0, 1050.0])
    sim_nav = read_portfolio_nav(sim_dir, "sim")
    assert list(sim_nav["net_value"]) == pytest.approx([2.0, 2.15, 2.2])
    assert read_portfolio_nav(tmp_path / "missing", "live").empty


def test_read_portfolio_nav_prefers_unit_nav_and_keeps_total(tmp_path: Path) -> None:
    """份额化档案：收益口径用 unit_nav（申购日不算涨），总值列保留供展示。"""
    live_dir = tmp_path / "results" / "live_portfolios" / "live_flow"
    _write_state(live_dir)
    pd.DataFrame(
        [
            {"date": "2026-07-10", "cash": 100.0, "positions_value": 900.0, "total_value": 1000.0,
             "external_flow": 0.0, "units": 1000.0, "unit_nav": 1.0},
            {"date": "2026-07-13", "cash": 600.0, "positions_value": 900.0, "total_value": 1500.0,
             "external_flow": 500.0, "units": 1500.0, "unit_nav": 1.0},
        ]
    ).to_csv(live_dir / "real_nav.csv", index=False)

    nav = read_portfolio_nav(live_dir, "live")
    assert list(nav["net_value"]) == pytest.approx([1.0, 1.0])  # 申购 500 不产生假收益
    assert list(nav["total_value"]) == pytest.approx([1000.0, 1500.0])
    assert trailing_returns(nav)["成立以来"] == pytest.approx(0.0)


def test_latest_ticket_prefers_newest_and_tolerates_missing_csv(tmp_path: Path) -> None:
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "ticket_2026-07-09.txt").write_text("老票", encoding="utf-8")
    pd.DataFrame([{"asset_id": "CN_ETF:510300.SH", "code": "510300", "weight_target": 0.5}]).to_csv(
        tickets / "ticket_2026-07-09.csv", index=False
    )
    (tickets / "ticket_2026-07-10.txt").write_text("【无操作】2026-07-10", encoding="utf-8")

    ticket = latest_ticket(tmp_path)
    assert ticket is not None
    assert ticket["date"] == "2026-07-10"
    assert "无操作" in ticket["text"]
    assert ticket["orders"].empty  # 无操作日只有 txt
    assert latest_ticket(tmp_path / "nowhere") is None


def test_position_weights_includes_cash_and_missing_price(tmp_path: Path) -> None:
    _write_state(tmp_path, cash=500.0)
    state = json.loads((tmp_path / "portfolio_state.json").read_text(encoding="utf-8"))
    weights = position_weights(state, {"CN_ETF:510300.SH": 5.0})  # 518880 缺价

    assert asset_code("CN_ETF:510300.SH") == "510300"
    frame = weights.set_index("code")
    # 已知市值 = 1000*5 + 现金 500；缺价资产保留行但权重为空
    assert frame.loc["510300", "weight"] == pytest.approx(5000.0 / 5500.0)
    assert frame.loc["现金", "weight"] == pytest.approx(500.0 / 5500.0)
    assert pd.isna(frame.loc["518880", "weight"])


def test_trailing_returns_uses_window_start_and_guards_short_history() -> None:
    nav = _make_nav("2025-01-01", 300, 0.001)
    returns = trailing_returns(nav)
    last = nav["date"].iloc[-1]
    start = window_start_date(last, "近1月")
    window = nav[nav["date"] >= start]
    assert returns["近1月"] == pytest.approx(window["net_value"].iloc[-1] / window["net_value"].iloc[0] - 1)
    assert returns["成立以来"] == pytest.approx(nav["net_value"].iloc[-1] / nav["net_value"].iloc[0] - 1)
    assert window_start_date(last, "近1周") == last - pd.DateOffset(weeks=1)

    young = _make_nav("2026-07-08", 3, 0.001)  # 3 天历史撑不起任何"近N期"
    young_returns = trailing_returns(young)
    assert young_returns["近1周"] is None
    assert young_returns["近1月"] is None
    assert young_returns["成立以来"] == pytest.approx(young["net_value"].iloc[-1] / young["net_value"].iloc[0] - 1)

    assert trailing_returns(pd.DataFrame())["成立以来"] is None


def test_nav_summary_metrics_gates_annualized_on_small_sample() -> None:
    long_nav = _make_nav("2024-07-01", 300, 0.001)
    summary = nav_summary_metrics(long_nav)
    assert summary["observations"] == 300
    daily = long_nav["net_value"].pct_change().dropna()
    years = len(daily) / 252
    expected = (long_nav["net_value"].iloc[-1] / long_nav["net_value"].iloc[0]) ** (1 / years) - 1
    assert summary["annualized_return"] == pytest.approx(expected)
    assert summary["max_drawdown"] == pytest.approx(0.0)  # 恒正收益无回撤
    assert summary["current_drawdown"] == pytest.approx(0.0)

    # 5 天样本：回撤照算，年化类一律 None（几天数据年化是噪声）
    short = pd.DataFrame({"date": pd.bdate_range("2026-07-10", periods=5), "net_value": [1.0, 1.01, 0.99, 1.0, 1.02]})
    summary = nav_summary_metrics(short)
    assert summary["observations"] == 5
    assert summary["annualized_return"] is None and summary["sharpe_ratio"] is None
    assert summary["max_drawdown"] == pytest.approx(0.99 / 1.01 - 1)

    assert nav_summary_metrics(pd.DataFrame())["observations"] == 0


def test_ticket_history_and_sim_run_tables(tmp_path: Path) -> None:
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "ticket_2026-07-09.txt").write_text("【调仓单】基于 2026-07-09 收盘估算", encoding="utf-8")
    pd.DataFrame([{"asset_id": "A", "code": "510300", "side": "BUY", "date": "2026-07-09"}]).to_csv(
        tickets / "ticket_2026-07-09.csv", index=False
    )
    (tickets / "ticket_2026-07-10.txt").write_text("【无操作】2026-07-10 阈值带内", encoding="utf-8")

    frame = list_tickets(tmp_path)
    assert frame["date"].tolist() == ["2026-07-10", "2026-07-09"]  # 新在前
    assert frame["kind"].tolist() == ["无操作", "调仓"]
    assert frame["has_detail"].tolist() == [False, True]
    assert list_tickets(tmp_path / "nowhere").empty

    orders = read_ticket_orders(tmp_path)
    assert len(orders) == 1 and orders["code"].iloc[0] == "510300"

    # sim runs 增量段拼接 + 整行去重（同日重跑 advance 场景）
    for run_name, rows in (
        ("2026-07-09_100000", [{"date": "2026-07-09", "asset_id": "A", "quantity": 100}]),
        ("2026-07-10_100000", [{"date": "2026-07-09", "asset_id": "A", "quantity": 100},
                               {"date": "2026-07-10", "asset_id": "B", "quantity": 200}]),
    ):
        run_dir = tmp_path / "runs" / run_name
        run_dir.mkdir(parents=True)
        pd.DataFrame(rows).to_csv(run_dir / "trades.csv", index=False)
    trades = read_sim_run_table(tmp_path, "trades")
    assert len(trades) == 2  # 重复的 07-09 行被去重
    assert trades["date"].iloc[0] == "2026-07-10"  # 倒序
    with pytest.raises(ValueError, match="Unsupported sim run table"):
        read_sim_run_table(tmp_path, "nav")


def test_max_drawdown_and_staleness() -> None:
    nav = pd.DataFrame({"date": pd.bdate_range("2025-01-01", periods=3), "net_value": [1.0, 0.8, 0.9]})
    assert max_drawdown(nav) == pytest.approx(-0.2)
    assert max_drawdown(pd.DataFrame()) is None

    # 周五 → 下周三 = 滞后 3 个工作日；同日/未来不为负
    assert business_days_behind("2026-07-10", "2026-07-15") == 3
    assert business_days_behind("2026-07-14", "2026-07-15") == 1
    assert business_days_behind("2026-07-15", "2026-07-15") == 0
    assert business_days_behind("2026-07-10", "2026-07-11") == 0  # 周六视角，无新交易日
