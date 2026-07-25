"""R049 行业估值分位轮动：加载层（含前视防护）与策略选择规则。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.platform_core.index_valuation import IndexValuationStore, reset_store_cache
from src.platform_core.models import PortfolioState, Position
from src.platform_core.strategies.value_rotation import IndustryValueRotationStrategy
from src.platform_core.strategy import BUILTIN_STRATEGIES, StrategyContext


def _build_store(tmp_path: Path, series: dict[str, list[float]], start: str = "2020-01-01") -> Path:
    """series: ETF代码 -> pb 序列（按交易日递增）。写出映射表与逐指数估值文件。"""
    valuation_dir = tmp_path / "index_valuation"
    valuation_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for code, values in series.items():
        index_code = f"IDX{code}.CSI"
        dates = pd.bdate_range(start, periods=len(values))
        pd.DataFrame({
            "trade_date": dates.strftime("%Y-%m-%d"),
            "pe_ttm": [v * 10 for v in values],
            "pb_lf": values,
            "dividend_yield": [1.0] * len(values),
            "turnover": [1.0] * len(values),
            "mv_total": [1e9] * len(values),
            "con_num": [30] * len(values),
        }).to_csv(valuation_dir / f"{index_code}.csv", index=False)
        rows.append({"etf_code": code, "name": code, "industry": code,
                     "index_code": index_code, "index_name": code, "verified_by": "test"})
    pd.DataFrame(rows).to_csv(tmp_path / "etf_index_map.csv", index=False)
    return tmp_path


def test_percentile_uses_only_history_up_to_asof(tmp_path: Path) -> None:
    """前视防护：分位只能用 <= asof 的观测，未来的极端值不得影响当日结论。"""
    # 前 10 天 PB 从 1.0 升到 1.9，第 11 天起暴涨到 5.0
    values = [1.0 + 0.1 * i for i in range(10)] + [5.0] * 10
    _build_store(tmp_path, {"512800": values})
    store = IndexValuationStore(tmp_path)
    dates = pd.bdate_range("2020-01-01", periods=len(values)).date

    # 在第 10 天(索引9,PB=1.9)看：它是当时的历史最高 → 分位 1.0
    at_day10 = store.percentile_at("CN_ETF:512800.SH", dates[9], window=1250)
    assert at_day10 is not None
    assert at_day10.value == pytest.approx(1.9)
    assert at_day10.percentile == pytest.approx(1.0)
    assert at_day10.observations == 10

    # 在最后一天看，1.9 只是历史中位偏低——若加载层泄露未来，第 10 天就不会是 1.0
    at_end = store.percentile_at("CN_ETF:512800.SH", dates[-1], window=1250)
    assert at_end.value == pytest.approx(5.0)
    assert at_end.observations == 20


def test_percentile_window_and_missing_mapping(tmp_path: Path) -> None:
    values = [float(i) for i in range(1, 21)]  # 1..20 递增
    _build_store(tmp_path, {"512800": values})
    store = IndexValuationStore(tmp_path)
    asof = pd.bdate_range("2020-01-01", periods=20).date[-1]

    # 全窗口：当前是最大值 → 分位 1.0
    assert store.percentile_at("CN_ETF:512800.SH", asof, window=1250).percentile == pytest.approx(1.0)
    # 窗口截断到最近 5 个观测，观测数随之下降
    windowed = store.percentile_at("CN_ETF:512800.SH", asof, window=5)
    assert windowed.observations == 5
    # 数据开始前的日期没有任何历史 → None（不向未来借值）
    assert store.percentile_at("CN_ETF:512800.SH", date(2019, 1, 1)) is None
    # 不在映射表里的资产 → None，而不是抛异常
    assert store.percentile_at("CN_ETF:999999.SH", asof) is None


def test_percentiles_at_filters_short_history(tmp_path: Path) -> None:
    """历史不足 min_observations 的行业被排除，不用'发布以来分位'充数。"""
    _build_store(tmp_path, {"512800": [1.0] * 100, "512010": [1.0] * 10})
    store = IndexValuationStore(tmp_path)
    asof = pd.bdate_range("2020-01-01", periods=100).date[-1]

    results = store.percentiles_at(
        ["CN_ETF:512800.SH", "CN_ETF:512010.SH"], asof, min_observations=50
    )
    assert set(results) == {"CN_ETF:512800.SH"}


class _StubData:
    """最小行情桩：策略只用到 data_dir（估值路径）与 calendar（基类节奏判断）。"""

    def __init__(self, data_dir: Path, calendar: list | None = None):
        self.data_dir = data_dir
        self.calendar = calendar


def _context(tmp_path: Path, asof, positions: dict[str, float], params: dict, calendar=None, last_date=None):
    asset_ids = params["universe"]
    state = PortfolioState(cash=100000.0)
    state.last_date = last_date  # None 表示组合尚未起跑（首日建仓语义）
    for asset_id, quantity in positions.items():
        state.positions[asset_id] = Position(asset_id=asset_id, quantity=quantity, cost_basis=1.0)
    return StrategyContext(
        date=asof,
        assets={asset_id: object() for asset_id in asset_ids},
        bars={asset_id: object() for asset_id in asset_ids},
        state=state,
        data=_StubData(tmp_path, calendar),
        params=params,
        runtime={},
    )


def _make_universe(tmp_path: Path, cheap_to_rich: list[str], length: int = 800) -> dict:
    """构造分位严格递增的资产池：cheap_to_rich[0] 最便宜。"""
    series = {}
    for rank, code in enumerate(cheap_to_rich):
        # 历史都是 [0,1] 均匀分布，当前值按名次给不同水平 → 分位随名次上升
        base = [i / length for i in range(length - 1)]
        series[code] = base + [rank / len(cheap_to_rich)]
    _build_store(tmp_path, series)
    return {"universe": [f"CN_ETF:{code}.SH" for code in cheap_to_rich]}


def test_strategy_selects_cheapest_and_leaves_cash_when_short(tmp_path: Path) -> None:
    reset_store_cache()
    codes = ["A1", "A2", "A3", "A4", "A5", "A6"]
    params = _make_universe(tmp_path, codes)
    params.update({"top_n": 3, "rank_buffer": 2, "min_history": 100, "percentile_window": 1250})
    asof = pd.bdate_range("2020-01-01", periods=800).date[-1]

    strategy = IndustryValueRotationStrategy()
    target = strategy.generate_theoretical_targets(_context(tmp_path, asof, {}, params))

    assert target is not None
    assert set(target.weights) == {"CN_ETF:A1.SH", "CN_ETF:A2.SH", "CN_ETF:A3.SH"}
    assert all(w == pytest.approx(1 / 3) for w in target.weights.values())
    assert sum(target.weights.values()) <= 1.0 + 1e-9
    assert all(w >= 0 for w in target.weights.values())

    # 合格集不足 top_n 时缺额留现金（权重和 < 1）
    params_short = dict(params, min_history=100, top_n=10)
    short_target = strategy.generate_theoretical_targets(_context(tmp_path, asof, {}, params_short))
    assert sum(short_target.weights.values()) == pytest.approx(0.6)  # 6 只 × 1/10


def test_rank_buffer_keeps_incumbent_and_excludes_short_history(tmp_path: Path) -> None:
    reset_store_cache()
    codes = ["A1", "A2", "A3", "A4", "A5", "A6"]
    params = _make_universe(tmp_path, codes)
    params.update({"top_n": 3, "rank_buffer": 2, "min_history": 100, "percentile_window": 1250})
    asof = pd.bdate_range("2020-01-01", periods=800).date[-1]
    strategy = IndustryValueRotationStrategy()

    # A5 排名第 5，在 top_n(3)+buffer(2)=5 内 → 现任留任，挤掉本该入选的 A3
    target = strategy.generate_theoretical_targets(
        _context(tmp_path, asof, {"CN_ETF:A5.SH": 100.0}, params)
    )
    assert "CN_ETF:A5.SH" in target.weights
    assert set(target.weights) == {"CN_ETF:A1.SH", "CN_ETF:A2.SH", "CN_ETF:A5.SH"}

    # A6 排名第 6，超出缓冲带 → 被换出
    target = strategy.generate_theoretical_targets(
        _context(tmp_path, asof, {"CN_ETF:A6.SH": 100.0}, params)
    )
    assert "CN_ETF:A6.SH" not in target.weights

    # 全池历史都不足 → 无信号，返回 None（而非空目标清仓）
    params_strict = dict(params, min_history=10_000)
    assert strategy.generate_theoretical_targets(_context(tmp_path, asof, {}, params_strict)) is None


def test_monthly_cadence_and_registration(tmp_path: Path) -> None:
    """月频节奏：只有当日是当月最后一个交易日才出目标（基类判断，T+1 执行）。"""
    reset_store_cache()
    codes = ["A1", "A2", "A3", "A4"]
    params = _make_universe(tmp_path, codes)
    params.update({"top_n": 2, "min_history": 100})
    calendar = list(pd.bdate_range("2020-01-01", periods=800).date)
    # 取一个真实的月末与其前一日（同月，非月末）
    month_end = next(
        day for index, day in enumerate(calendar[:-1])
        if calendar[index + 1].month != day.month and index > 700
    )
    mid_month = calendar[calendar.index(month_end) - 1]

    strategy = IndustryValueRotationStrategy()

    # 组合已起跑（last_date 非空）：非月末不出目标
    ctx_mid = _context(tmp_path, mid_month, {}, params, calendar=calendar, last_date=calendar[0])
    strategy.initialize(ctx_mid)
    assert strategy.generate_targets(ctx_mid) is None

    # 月末：出目标
    ctx_end = _context(tmp_path, month_end, {}, params, calendar=calendar, last_date=calendar[0])
    strategy.initialize(ctx_end)
    target = strategy.generate_targets(ctx_end)
    assert target is not None and len(target.weights) == 2

    # R049 验收 Failed 后按 Hard Rule 3 撤销注册；策略代码保留为 research-only。
    # 复研时在 strategy.py 尾部重新注册，本断言随之改回 is IndustryValueRotationStrategy。
    assert "industry_value_rotation" not in BUILTIN_STRATEGIES


def test_rebalance_on_start_matches_baseline_entry_convention(tmp_path: Path) -> None:
    """首日建仓语义须与基线 monthly_equal_weight 一致，否则敏感性测的是入场运气。

    实测：候选若空仓等到首个月末，2024-09-18 起点会因错过政策行情产生 -49.6pp 伪劣势。
    """
    reset_store_cache()
    codes = ["A1", "A2", "A3", "A4"]
    params = _make_universe(tmp_path, codes)
    params.update({"top_n": 2, "min_history": 100})
    calendar = list(pd.bdate_range("2020-01-01", periods=800).date)
    mid_month = calendar[750]  # 非月末
    strategy = IndustryValueRotationStrategy()

    # last_date is None（组合未起跑）+ 默认 rebalance_on_start=True → 首日即建仓
    ctx_start = _context(tmp_path, mid_month, {}, params, calendar=calendar, last_date=None)
    strategy.initialize(ctx_start)
    assert strategy.generate_targets(ctx_start) is not None

    # 显式关闭时退回"等月末"语义
    params_off = dict(params, rebalance_on_start=False)
    ctx_off = _context(tmp_path, mid_month, {}, params_off, calendar=calendar, last_date=None)
    strategy.initialize(ctx_off)
    assert strategy.generate_targets(ctx_off) is None
