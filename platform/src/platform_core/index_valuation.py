"""行业指数估值数据加载层（R049 左侧价值轮动的信号数据源）。

数据由 `scripts/ingest_index_valuation.py` 从 Wind `AIndexValuation` 清洗入库：
  data/index_valuation/<INDEX_CODE>.csv   列 trade_date,pe_ttm,pb_lf,dividend_yield,turnover,mv_total,con_num
  data/etf_index_map.csv                  ETF 代码 ↔ 跟踪指数代码（ETF 本身无 PE/PB，其估值即跟踪指数估值）

**前视防护是本模块唯一的硬责任**：`percentile_at()` 只使用 `trade_date <= asof` 的观测，
调用方无需（也无法）绕过。估值是日频、当日发布（由当日收盘价与最近已披露财报算出），
因此"T 日估值 → T 日信号 → T+1 执行"与价格类信号同构，不需要额外滞后。
按报告期编码的财务表（AIndexFinancialderivative）有披露滞后，本模块一律不加载。

时序分位而非横截面比大小：行业间 PB 绝对水平天然不可比（银行 0.6 与半导体 5.0 是行业
属性，不是贵贱），只有"与自己的历史比"才有意义。分位同时对数据源口径的常数倍缩放免疫，
降低将来从 Wind 换到公开源的拼接风险（蓝图 §1.2）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

VALUATION_DIRNAME = "index_valuation"
MAP_FILENAME = "etf_index_map.csv"
SUPPORTED_METRICS = ("pb_lf", "pe_ttm", "dividend_yield", "turnover")


@dataclass(frozen=True)
class PercentileResult:
    """某资产在 asof 日的估值分位。observations 用于 min_history 门槛判断。"""

    asset_code: str
    index_code: str
    value: float
    percentile: float
    observations: int


class IndexValuationStore:
    """按需加载 + 进程内缓存的指数估值仓库。

    一个策略回测会对同一指数反复取分位（每月一次 × 数年），因此按指数代码缓存整条
    序列，切片在内存里做。数据量很小（16 指数 × ~3300 行）。
    """

    def __init__(self, data_dir: str | Path, valuation_dirname: str = VALUATION_DIRNAME):
        self.data_dir = Path(data_dir)
        self.valuation_dir = self.data_dir / valuation_dirname
        self._series_cache: dict[tuple[str, str], pd.Series] = {}
        self._map: dict[str, str] | None = None

    # ---------------------------------------------------------------- 映射

    @property
    def code_to_index(self) -> dict[str, str]:
        """ETF 代码 → 跟踪指数代码。映射表可入库（公开信息），带 verified_by 溯源列。"""
        if self._map is None:
            path = self.data_dir / MAP_FILENAME
            if not path.exists():
                raise FileNotFoundError(f"ETF↔指数映射表不存在: {path}")
            frame = pd.read_csv(path, dtype=str)
            missing = {"etf_code", "index_code"} - set(frame.columns)
            if missing:
                raise ValueError(f"{path} 缺少必需列: {sorted(missing)}")
            self._map = {
                str(row["etf_code"]).strip(): str(row["index_code"]).strip()
                for _, row in frame.iterrows()
            }
        return self._map

    @staticmethod
    def asset_code(asset_id: str) -> str:
        """CN_ETF:512480.SH -> 512480，与行情 CSV / 映射表的代码列对应。"""
        return asset_id.split(":")[-1].split(".")[0]

    def index_code_for(self, asset_id: str) -> str | None:
        return self.code_to_index.get(self.asset_code(asset_id))

    # ---------------------------------------------------------------- 序列

    def load_series(self, index_code: str, metric: str) -> pd.Series:
        """返回以 trade_date 为索引、按日期升序的估值序列（已剔除缺失值）。"""
        if metric not in SUPPORTED_METRICS:
            raise ValueError(f"不支持的估值指标: {metric}（可选 {SUPPORTED_METRICS}）")
        key = (index_code, metric)
        if key in self._series_cache:
            return self._series_cache[key]

        path = self.valuation_dir / f"{index_code}.csv"
        if not path.exists():
            raise FileNotFoundError(f"指数估值数据不存在: {path}（先跑 scripts/ingest_index_valuation.py）")
        frame = pd.read_csv(path, usecols=["trade_date", metric])
        frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
        values = pd.to_numeric(frame[metric], errors="coerce")
        series = pd.Series(values.values, index=frame["trade_date"].values).dropna().sort_index()
        # 同日重复（原始导出偶发）保留最后一条，与 ingest 的去重口径一致
        series = series[~series.index.duplicated(keep="last")]
        self._series_cache[key] = series
        return series

    # ---------------------------------------------------------------- 分位

    def percentile_at(
        self,
        asset_id: str,
        asof: date,
        metric: str = "pb_lf",
        window: int = 1250,
    ) -> PercentileResult | None:
        """asof 日的估值时序分位（0 = 窗口内史上最便宜，1 = 最贵）。

        **只使用 trade_date <= asof 的观测**（前视防护）。asof 当日无观测时（停牌、
        指数数据缺口）取最近一个历史观测，不向未来借值。窗口内观测不足或没有任何
        历史时返回 None，由调用方按 min_history 决定是否参与选择。
        """
        index_code = self.index_code_for(asset_id)
        if index_code is None:
            return None
        series = self.load_series(index_code, metric)
        history = series[series.index <= asof]
        if history.empty:
            return None
        if window > 0:
            history = history.iloc[-window:]
        current = float(history.iloc[-1])
        # 分位 = 窗口内不高于当前值的观测占比；越低越便宜
        percentile = float((history <= current).sum()) / float(len(history))
        return PercentileResult(
            asset_code=self.asset_code(asset_id),
            index_code=index_code,
            value=current,
            percentile=percentile,
            observations=int(len(history)),
        )

    def percentiles_at(
        self,
        asset_ids: list[str],
        asof: date,
        metric: str = "pb_lf",
        window: int = 1250,
        min_observations: int = 750,
    ) -> dict[str, PercentileResult]:
        """批量取分位，并按 min_observations 过滤。

        历史不足者被**排除**而不是降级用"发布以来分位"充数：样本极短时分位是噪声，
        用它下注等于赌噪声，没有信号就不下注更诚实（蓝图 §1.1 硬约束②）。
        """
        out: dict[str, PercentileResult] = {}
        for asset_id in asset_ids:
            result = self.percentile_at(asset_id, asof, metric=metric, window=window)
            if result is not None and result.observations >= min_observations:
                out[asset_id] = result
        return out


_STORE_CACHE: dict[str, IndexValuationStore] = {}


def get_store(data_dir: str | Path) -> IndexValuationStore:
    """按 data_dir 复用 store 实例，避免每个回测日重复读盘。"""
    key = str(Path(data_dir).resolve())
    if key not in _STORE_CACHE:
        _STORE_CACHE[key] = IndexValuationStore(key)
    return _STORE_CACHE[key]


def reset_store_cache() -> None:
    """测试用：清空进程内缓存。"""
    _STORE_CACHE.clear()
