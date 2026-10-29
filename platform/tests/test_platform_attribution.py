from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from src.platform_core.attribution import (
    build_live_attribution,
    load_real_nav,
    load_shadow_nav,
    month_window,
    previous_month,
    render_attribution_md,
)
from src.platform_core.sim import SimPortfolio
from src.platform_core.models import PortfolioState, TargetPortfolio
from src.platform_core.storage import InMemoryStore
from src.platform_core.strategy import RiskParityStrategy


# ---------------------------------------------------------------- SimPortfolio.load


def _write_market_data(data_dir: Path, dates: list[str]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    header = "code,trade_date,open_price,high_price,low_price,close_price,volume,amount,adjust_factor"
    rows = [header] + [f"AAA,{d},10,10,10,10,1000,10000,1" for d in dates]
    (data_dir / "AAA.csv").write_text("\n".join(rows), encoding="utf-8")


def _sim_config(data_dir: Path, sim_root: Path) -> dict:
    return {
        "platform": {"run_name": "shadow_test"},
        "data": {"data_dir": str(data_dir)},
        "assets": [{"asset_id": "A", "code": "AAA", "name": "资产A", "lot_size": 100, "price_limit_pct": None}],
        "execution": {"fee": {"rate": 0.0, "min_fee": 0.0}, "weight_tolerance": 0.0001},
        "strategy": {
            "strategy_name": "fixed_weight_threshold",
            "strategy_version_id": None,
            "params": {"universe": ["A"]},
        },
        "output": {"sim_dir": str(sim_root)},
    }


def test_sim_portfolio_load_advances_incrementally(tmp_path: Path):
    data_dir = tmp_path / "data"
    _write_market_data(data_dir, ["2024-01-29", "2024-01-30", "2024-01-31"])
    sim_root = tmp_path / "sims"
    config = _sim_config(data_dir, sim_root)

    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps(
            {
                "cash": 1000.0,
                "positions": {"A": {"asset_id": "A", "quantity": 100.0, "cost_basis": 10.0}},
                "pending_intents": {},
                "cooldown_pool": {},
                "strategy_state": {},
                "last_date": "2024-01-29",
                "dividend_receivables": [],
            }
        ),
        encoding="utf-8",
    )

    store = InMemoryStore()
    created = SimPortfolio.create_from_checkpoint(checkpoint, config, store, portfolio_id="shadow_x")
    created.advance("2024-01-30")

    # load 从持久化状态恢复：只增量处理 01-31 一天
    loaded = SimPortfolio.load("shadow_x", config, store)
    assert loaded.state.last_date == date(2024, 1, 30)
    result = loaded.advance("2024-01-31")
    assert result.metrics["processed_days"] == 1

    nav_rows = load_shadow_nav(sim_root / "shadow_x")
    assert [row["date"] for row in nav_rows] == ["2024-01-30", "2024-01-31"]


def test_sim_portfolio_load_missing_state_raises(tmp_path: Path):
    config = _sim_config(tmp_path / "data", tmp_path / "sims")
    with pytest.raises(FileNotFoundError, match="portfolio_state"):
        SimPortfolio.load("nope", config, InMemoryStore())


def test_sim_runs_in_same_second_preserve_previous_artifacts(tmp_path: Path, monkeypatch):
    class Clock:
        tick = 0

        @classmethod
        def now(cls):
            cls.tick += 1
            return datetime(2024, 1, 31, 12, 0, 0, cls.tick)

    monkeypatch.setattr("src.platform_core.sim.datetime", Clock)
    data_dir = tmp_path / "data"
    _write_market_data(data_dir, ["2024-01-29", "2024-01-30"])
    config = _sim_config(data_dir, tmp_path / "sims")
    portfolio = SimPortfolio("sim", config, InMemoryStore(), PortfolioState(cash=1000), tmp_path / "checkpoint")
    first = portfolio.advance("2024-01-30")
    before = (first.output_dir / "nav.csv").read_bytes()
    second = portfolio.advance("2024-01-30")
    assert first.output_dir != second.output_dir
    assert (first.output_dir / "nav.csv").read_bytes() == before
    assert second.metrics["processed_days"] == 0


def test_daily_sim_restarts_match_batch_and_preserve_monthly_schedule(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_market_data(data_dir, ["2024-01-29", "2024-01-30", "2024-01-31"])
    config = _sim_config(data_dir, tmp_path / "sims")
    config["execution"]["slippage_bps"] = 0
    config["strategy"] = {
        "strategy_name": "risk_parity", "strategy_version_id": 999,
        "params": {"universe": ["A"], "init_calc_days": 0, "rebalance_frequency": "monthly"},
    }
    monkeypatch.setattr(RiskParityStrategy, "_inverse_vol_target",
                        lambda self, context, universe: TargetPortfolio({"A": .5}))
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps(PortfolioState(cash=10000).to_dict()))
    daily = SimPortfolio.create_from_checkpoint(checkpoint, config, InMemoryStore(), portfolio_id="daily")
    daily.advance("2024-01-29")
    daily = SimPortfolio.load("daily", config, InMemoryStore())
    daily.advance("2024-01-30")
    assert not daily.state.pending_intents
    daily = SimPortfolio.load("daily", config, InMemoryStore())
    daily.advance("2024-01-31")
    batch = SimPortfolio.create_from_checkpoint(checkpoint, config, InMemoryStore(), portfolio_id="batch")
    batch.advance("2024-01-31")
    assert daily.state.to_dict() == batch.state.to_dict()


# ---------------------------------------------------------------- 归因数学


def _rows(values: dict[str, tuple[float, float]]) -> list[dict]:
    # values: date -> (total_value, cash)
    return [{"date": d, "total_value": t, "cash": c} for d, (t, c) in sorted(values.items())]


def test_build_live_attribution_math():
    # 6 月：模型每天 +1%，真实每天 +0.9%（稳定 -10bp/日 落后）
    dates = [f"2024-06-{d:02d}" for d in (3, 4, 5, 6, 7, 10, 11)]
    real, shadow = {}, {}
    rv, sv = 100.0, 100.0
    for i, d in enumerate(dates):
        if i > 0:
            rv *= 1.009
            sv *= 1.010
        real[d] = (rv, rv * 0.02)   # 真实现金 2%
        shadow[d] = (sv, sv * 0.01)  # 模型现金 1%

    result = build_live_attribution(_rows(real), _rows(shadow), date(2024, 6, 1), date(2024, 6, 30))

    assert result["sufficient"]
    assert result["observations"] == 6
    assert result["real_cum_return"] == pytest.approx(1.009**6 - 1)
    assert result["shadow_cum_return"] == pytest.approx(1.010**6 - 1)
    assert result["diff_cum_return"] == pytest.approx((1.009**6 - 1) - (1.010**6 - 1))
    # 每日差恒定 → TE 接近 0
    assert result["tracking_error_annualized"] == pytest.approx(0.0, abs=1e-6)
    # 现金拖累差为负（真实现金更多、模型收益为正）
    assert result["cash_drag_component"] < 0
    report = render_attribution_md(result, "live_x", "shadow_x", "2024-06")
    assert "Tracking Error" in report and "现金拖累差" in report and "只记录" in report


def test_build_live_attribution_uses_anchor_before_window():
    # 窗口前有共同日 5-31 → 6 月首日收益计入
    real = _rows({"2024-05-31": (100.0, 2.0), "2024-06-03": (101.0, 2.0)})
    shadow = _rows({"2024-05-31": (100.0, 1.0), "2024-06-03": (100.5, 1.0)})
    result = build_live_attribution(real, shadow, date(2024, 6, 1), date(2024, 6, 30))
    assert result["observations"] == 1
    assert result["real_cum_return"] == pytest.approx(0.01)
    assert result["shadow_cum_return"] == pytest.approx(0.005)


def test_build_live_attribution_insufficient_sample():
    real = _rows({"2024-06-03": (100.0, 2.0), "2024-06-04": (101.0, 2.0)})
    shadow = _rows({"2024-06-03": (100.0, 1.0), "2024-06-04": (100.8, 1.0)})
    result = build_live_attribution(real, shadow, date(2024, 6, 1), date(2024, 6, 30))
    assert not result["sufficient"]
    report = render_attribution_md(result, "live_x", "shadow_x", "2024-06")
    assert "样本不足" in report


def test_attribution_uses_unit_nav_for_return_and_account_value_for_total_display(tmp_path):
    (tmp_path / "real_nav.csv").write_text(
        "date,total_value,cash,unit_nav\n2024-06-03,1000,100,1\n2024-06-04,2000,1100,1\n")
    rows = load_real_nav(tmp_path)
    shadow = _rows({"2024-06-03": (1000, 100), "2024-06-04": (1000, 100)})
    result = build_live_attribution(rows, shadow, date(2024, 6, 1), date(2024, 6, 30))
    assert result["real_cum_return"] == 0
    assert result["real_total_start"] == 1000 and result["real_total_end"] == 2000


def test_missing_unit_nav_never_falls_back_to_deposit_contaminated_account_value(tmp_path):
    (tmp_path / "real_nav.csv").write_text(
        "date,total_value,cash,unit_nav\n2024-06-03,1000,100,1\n2024-06-04,2000,1100,\n")
    with pytest.raises(ValueError):
        load_real_nav(tmp_path)


@pytest.mark.parametrize("value", [0, float("nan"), float("inf")])
def test_invalid_shadow_nav_does_not_generate_infinite_or_undefined_attribution(value):
    real = _rows({"2024-06-03": (1000, 100), "2024-06-04": (1000, 100)})
    shadow = _rows({"2024-06-03": (value, 100), "2024-06-04": (1000, 100)})
    with pytest.raises(ValueError, match="有限正净值"):
        build_live_attribution(real, shadow, date(2024, 6, 1), date(2024, 6, 30))


def test_month_helpers():
    assert month_window("2024-12") == (date(2024, 12, 1), date(2024, 12, 31))
    assert month_window("2024-02") == (date(2024, 2, 1), date(2024, 2, 29))
    assert previous_month(date(2026, 7, 11)) == "2026-06"
    assert previous_month(date(2026, 1, 5)) == "2025-12"


def test_load_shadow_nav_dedupes_overlapping_runs(tmp_path: Path):
    runs = tmp_path / "shadow" / "runs"
    for name, rows in (
        ("2024-01-30_100000", [("2024-01-29", "1000", "10"), ("2024-01-30", "1010", "10")]),
        ("2024-01-31_100000", [("2024-01-30", "1011", "11"), ("2024-01-31", "1020", "11")]),
    ):
        run_dir = runs / name
        run_dir.mkdir(parents=True)
        with (run_dir / "nav.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "total_value", "cash", "pending_intent_count", "strategy_version_id"])
            writer.writerows([(d, t, c, 0, 1) for d, t, c in rows])

    rows = load_shadow_nav(tmp_path / "shadow")
    assert [row["date"] for row in rows] == ["2024-01-29", "2024-01-30", "2024-01-31"]
    # 同日取更新 run 的值
    assert rows[1]["total_value"] == pytest.approx(1011.0)
