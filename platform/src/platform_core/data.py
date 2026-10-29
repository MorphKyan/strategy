from __future__ import annotations

from datetime import date, timedelta
from math import isfinite
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.platform_core.data_store import DataQualityReport, validate_market_dates
from src.platform_core.models import Asset, Bar, parse_date


PRICE_COLUMNS = {
    "open": ["open", "open_price", "open_price_adjusted"],
    "high": ["high", "high_price", "high_price_adjusted"],
    "low": ["low", "low_price", "low_price_adjusted"],
    "close": ["close", "close_price", "close_price_adjusted", "nav", "acc_nav"],
    "volume": ["volume", "vol"],
    "amount": ["amount", "turnover"],
}


def _first_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


class LocalCsvBarData:
    def __init__(self, data_dir: str | Path, assets: Iterable[Asset], start_date: str | None = None, end_date: str | None = None):
        self.data_dir = Path(data_dir)
        self.assets = {asset.asset_id: asset for asset in assets}
        self.start_date = parse_date(start_date) if start_date else None
        self.end_date = parse_date(end_date) if end_date else None
        self.quality = DataQualityReport()
        self.real_bar_dates: dict[str, list[date]] = {}
        self.frames = self._load_frames()
        self.calendar = self._build_calendar()
        self._aligned_adj_close = pd.DataFrame({
            asset_id: frame["adj_close"] for asset_id, frame in self.frames.items()
        })
        self._aligned_acc_nav = pd.DataFrame({
            asset_id: (frame["acc_nav"] if "acc_nav" in frame.columns else frame["adj_close"])
            for asset_id, frame in self.frames.items()
        })

    def get_price_frame(self, universe: list[str], end_date: date, use_nav: bool = False) -> pd.DataFrame | None:
        if not all(asset_id in self.frames for asset_id in universe):
            return None
        df = self._aligned_acc_nav if use_nav else self._aligned_adj_close
        valid_cols = [c for c in universe if c in df.columns]
        if not valid_cols:
            return pd.DataFrame()
        return df.loc[df.index <= end_date, valid_cols].dropna()

    def extend_calendar(self) -> None:
        """用已知后续交易日或下一工作日补齐边界，避免每日运行都被判成月末。"""
        if not self.calendar:
            return
        last = self.calendar[-1]
        following = min((day for dates in self.real_bar_dates.values() for day in dates if day > last), default=None)
        if following is None:
            following = last + timedelta(days=1)
            while following.weekday() >= 5:
                following += timedelta(days=1)
        self.calendar.append(following)

    def _load_frames(self) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for asset in self.assets.values():
            path = self.data_dir / f"{asset.code}.csv"
            if not path.exists():
                raise FileNotFoundError(f"Market data file not found for {asset.asset_id}: {path}")
            raw = pd.read_csv(path)
            if "trade_date" not in raw.columns:
                raise ValueError(f"`trade_date` column is required in {path}")

            raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.date
            raw = raw.sort_values("trade_date").reset_index(drop=True)
            if raw["trade_date"].duplicated().any():
                raise ValueError(f"Duplicate trade_date rows in {path}")
            factor_col = _first_column(raw, ["hfq_factor", "adjust_factor", "qfq_factor"])
            sidecar_factor = self._sidecar_hfq_factor(asset, raw["trade_date"])
            if not isinstance(sidecar_factor, float):
                factor = sidecar_factor
                self.quality.notes.append(f"{asset.asset_id}: using sidecar HFQ factor.")
            elif factor_col:
                factor = raw[factor_col].fillna(1.0)
            else:
                factor = 1.0
                self.quality.notes.append(f"{asset.asset_id}: no adjustment factor column or sidecar; using raw prices.")
            factor = pd.to_numeric(factor, errors="raise")
            factor_values = factor if isinstance(factor, pd.Series) else pd.Series([factor])
            if (factor_values <= 0).any() or not factor_values.map(isfinite).all():
                raise ValueError(f"Invalid adjustment factors in {path}; factors must be finite and positive.")

            normalized = pd.DataFrame({"date": raw["trade_date"]})
            close_col = _first_column(raw, PRICE_COLUMNS["close"])
            if close_col is None:
                raise ValueError(f"No close price column found in {path}")

            close = pd.to_numeric(raw[close_col], errors="coerce")
            if (close <= 0).any() or not close.dropna().map(isfinite).all():
                raise ValueError(f"Invalid close prices in {path}; prices must be finite and positive.")
            for field_name in ["open", "high", "low"]:
                source = _first_column(raw, PRICE_COLUMNS[field_name])
                if source is None:
                    normalized[field_name] = close
                    self.quality.notes.append(f"{asset.asset_id}: missing {field_name}; filled with close.")
                else:
                    normalized[field_name] = pd.to_numeric(raw[source], errors="coerce")
            normalized["close"] = close
            normalized["adj_close"] = close * factor
            if "nav" in raw.columns:
                normalized["nav"] = pd.to_numeric(raw["nav"], errors="coerce")
            if "acc_nav" in raw.columns:
                normalized["acc_nav"] = pd.to_numeric(raw["acc_nav"], errors="coerce")


            for field_name in ["volume", "amount"]:
                source = _first_column(raw, PRICE_COLUMNS[field_name])
                if source is None:
                    normalized[field_name] = 0.0
                    self.quality.notes.append(f"{asset.asset_id}: missing {field_name}; filled with 0.")
                else:
                    normalized[field_name] = pd.to_numeric(raw[source], errors="coerce").fillna(0.0)

            normalized = normalized.sort_values("date").dropna(subset=["close"])
            self.real_bar_dates[asset.asset_id] = normalized["date"].tolist()

            previous_close = normalized["close"].shift(1)
            if asset.price_limit_pct is None:
                normalized["limit_up"] = None
                normalized["limit_down"] = None
            else:
                normalized["limit_up"] = (previous_close * (1 + asset.price_limit_pct)).round(2)
                normalized["limit_down"] = (previous_close * (1 - asset.price_limit_pct)).round(2)
            if asset.asset_type in {"index", "futures"}:
                normalized["is_suspended"] = False
            else:
                normalized["is_suspended"] = normalized["volume"].fillna(0.0) <= 0
            if self.start_date:
                normalized = normalized[normalized["date"] >= self.start_date]
            if self.end_date:
                normalized = normalized[normalized["date"] <= self.end_date]
            frames[asset.asset_id] = normalized.set_index("date", drop=False)
        validate_market_dates({asset_id: dates[-1] if dates else None
                               for asset_id, dates in self.real_bar_dates.items()}, date.today())
        return frames

    def _sidecar_hfq_factor(self, asset: Asset, trade_dates: pd.Series) -> pd.Series | float:
        path = self.data_dir / f"{asset.code}_hfq_factor.csv"
        if not path.exists():
            return 1.0
        factor_frame = pd.read_csv(path)
        if "trade_date" not in factor_frame.columns or "hfq_factor" not in factor_frame.columns:
            raise ValueError(f"Invalid sidecar HFQ factor file: {path}")
        factor_frame["trade_date"] = pd.to_datetime(factor_frame["trade_date"]).dt.date
        if factor_frame["trade_date"].isna().any() or factor_frame["trade_date"].duplicated().any():
            raise ValueError(f"Missing or duplicate HFQ factor dates: {path}")
        factor_by_date = factor_frame.set_index("trade_date")["hfq_factor"].sort_index().ffill()
        return factor_by_date.reindex(trade_dates, method="ffill").reset_index(drop=True).fillna(1.0)

    def _build_calendar(self) -> list[date]:
        dates = set()
        for frame in self.frames.values():
            dates.update(frame.index.tolist())
        return sorted(dates)

    def bars_on(self, current_date: date) -> dict[str, Bar]:
        bars: dict[str, Bar] = {}
        for asset_id, frame in self.frames.items():
            if current_date in frame.index:
                row = frame.loc[current_date]
                bars[asset_id] = Bar(
                    date=current_date,
                    asset_id=asset_id,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    amount=float(row["amount"]),
                    limit_up=float(row["limit_up"]) if pd.notna(row["limit_up"]) else None,
                    limit_down=float(row["limit_down"]) if pd.notna(row["limit_down"]) else None,
                    is_suspended=bool(row["is_suspended"]),
                    adj_close=float(row["adj_close"]),
                )
                continue

            prior = frame[frame.index < current_date]
            if not prior.empty:
                last = prior.iloc[-1]
                close = float(last["close"])
                adj_close = float(last["adj_close"])
                bars[asset_id] = Bar(
                    date=current_date,
                    asset_id=asset_id,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=0.0,
                    amount=0.0,
                    is_suspended=True,
                    adj_close=adj_close,
                )
        return bars

    def first_bar_date_after(self, asset_id: str, after_date: date) -> date | None:
        """该资产在 after_date 之后第一个有真实行情行的日期。

        bars_on() 对缺失日会用前收合成停牌 bar，那种日期不算；只认 CSV 里真实存在的行。
        用于份额拆分生效日解析：价格要到拆分基准日后的首个真实交易日才反映除权。
        """
        dates = self.real_bar_dates.get(asset_id)
        if not dates:
            return None
        later = [d for d in dates if d > after_date]
        return min(later) if later else None

    def is_month_end(self, current_date: date) -> bool:
        try:
            idx = self.calendar.index(current_date)
        except ValueError:
            return False
        if idx == len(self.calendar) - 1:
            return True
        return self.calendar[idx + 1].month != current_date.month
