"""ETF 场内折溢价数据加载层（R056 溢价闸门的信号数据源）。

数据由 `scripts/fetch_etf_nav.py` 从东财 F10 入库：
  data/etf_nav/<code>.csv   列 trade_date,unit_nav,cum_nav,source,updated_at

溢价率定义：`premium_d = 场内收盘价_d / 单位净值_d - 1`
场内收盘价取 `data/<code>.csv` 的 `close` 列（**未复权原价**——复权价与净值不同基准，
配对会得到无意义的数字）。

**前视防护是本模块唯一的硬责任，且与 R049 的估值模块不同**：

  行业指数估值当日发布（当日收盘价 + 已披露财报算出），T 日信号 → T+1 执行即可。
  **QDII 基金净值不是**：净值需等标的市场收盘与汇率结算，境内 QDII 普遍 T+1~T+2 才披露。
  若按 `premium_T` 决策，等于用了当天尚未公布的净值——一个典型的、且相当隐蔽的前视。

因此 `premium_at(asof)` 返回的是 **asof 之前第 `publication_lag_days` 个交易日**的溢价观测，
默认 lag=2（取披露区间上界，最保守）。同时刻意**用同一天的价格与净值配对**：
若用 `价格_T / 净值_{T-2}`，会把 2 天的价格波动混进溢价读数，制造出并不存在的溢价波动。

调用方无法绕过滞后——这是本模块存在的理由。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

NAV_DIRNAME = "etf_nav"
DEFAULT_PUBLICATION_LAG_DAYS = 2


@dataclass(frozen=True)
class PremiumResult:
    """某 ETF 在 asof 日**可观测**的最新溢价读数。"""

    asset_code: str
    observed_date: date  # 该溢价读数对应的交易日（严格早于 asof）
    close: float
    unit_nav: float
    premium: float  # 0.0342 表示溢价 3.42%
    observations: int


class EtfPremiumStore:
    """按需加载 + 进程内缓存的 ETF 溢价仓库。

    一个回测会对同一标的反复取溢价（每月一次 × 数年），故按代码缓存整条配对好的
    序列，切片在内存里做。数据量很小（单只 ~3200 行）。
    """

    def __init__(self, data_dir: str | Path, nav_dirname: str = NAV_DIRNAME):
        self.data_dir = Path(data_dir)
        self.nav_dir = self.data_dir / nav_dirname
        self._series_cache: dict[str, pd.DataFrame] = {}

    @staticmethod
    def asset_code(asset_id: str) -> str:
        """CN_ETF:513100.SH -> 513100，与行情 CSV / 净值 CSV 的文件名对应。"""
        return asset_id.split(":")[-1].split(".")[0]

    def has_data(self, asset_id: str) -> bool:
        return (self.nav_dir / f"{self.asset_code(asset_id)}.csv").exists()

    def load_premium_series(self, asset_code: str) -> pd.DataFrame:
        """返回按日期升序、索引为 trade_date 的 DataFrame（close/unit_nav/premium）。

        价格与净值按**同一交易日** inner join；任一侧缺失的日期直接丢弃，不做
        前值填充——填充会把停牌/净值缺口伪装成有效观测。
        """
        if asset_code in self._series_cache:
            return self._series_cache[asset_code]

        nav_path = self.nav_dir / f"{asset_code}.csv"
        if not nav_path.exists():
            raise FileNotFoundError(
                f"ETF 净值数据不存在: {nav_path}（先跑 scripts/fetch_etf_nav.py --codes {asset_code}）"
            )
        price_path = self.data_dir / f"{asset_code}.csv"
        if not price_path.exists():
            raise FileNotFoundError(f"ETF 行情数据不存在: {price_path}")

        nav = pd.read_csv(nav_path, usecols=["trade_date", "unit_nav"])
        nav["trade_date"] = pd.to_datetime(nav["trade_date"], errors="coerce").dt.date
        nav["unit_nav"] = pd.to_numeric(nav["unit_nav"], errors="coerce")
        nav = nav.dropna().drop_duplicates("trade_date", keep="last")

        price = pd.read_csv(price_path)
        close_column = "close" if "close" in price.columns else "close_price"
        price = price[["trade_date", close_column]].rename(columns={close_column: "close"})
        price["trade_date"] = pd.to_datetime(price["trade_date"], errors="coerce").dt.date
        price["close"] = pd.to_numeric(price["close"], errors="coerce")
        price = price.dropna().drop_duplicates("trade_date", keep="last")

        merged = price.merge(nav, on="trade_date", how="inner").sort_values("trade_date")
        merged = merged[merged["unit_nav"] > 0]
        merged["premium"] = merged["close"] / merged["unit_nav"] - 1.0
        merged = merged.set_index("trade_date")
        self._series_cache[asset_code] = merged
        return merged

    def premium_at(
        self,
        asset_id: str,
        asof: date,
        publication_lag_days: int = DEFAULT_PUBLICATION_LAG_DAYS,
    ) -> PremiumResult | None:
        """asof 日**可观测**的最新溢价读数，已扣除净值发布滞后。

        取满足 `trade_date <= asof` 的观测后，再向前丢弃 `publication_lag_days` 条
        （按观测序列的交易日计数，不按自然日——自然日会在长假后放松滞后）。
        历史不足时返回 None，由调用方决定如何处置（本课题的约定是"没有信号就不下注"）。
        """
        code = self.asset_code(asset_id)
        series = self.load_premium_series(code)
        history = series[series.index <= asof]
        lag = max(0, int(publication_lag_days))
        if len(history) <= lag:
            return None
        row = history.iloc[-(lag + 1)]
        observed_date = history.index[-(lag + 1)]
        return PremiumResult(
            asset_code=code,
            observed_date=observed_date,
            close=float(row["close"]),
            unit_nav=float(row["unit_nav"]),
            premium=float(row["premium"]),
            observations=int(len(history)),
        )


_STORE_CACHE: dict[str, EtfPremiumStore] = {}


def get_store(data_dir: str | Path) -> EtfPremiumStore:
    """按 data_dir 复用 store 实例，避免每个回测日重复读盘。"""
    key = str(Path(data_dir).resolve())
    if key not in _STORE_CACHE:
        _STORE_CACHE[key] = EtfPremiumStore(key)
    return _STORE_CACHE[key]


def reset_store_cache() -> None:
    """测试用：清空进程内缓存。"""
    _STORE_CACHE.clear()
