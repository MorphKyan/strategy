from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.platform_core.models import Asset, Bar, parse_date


PRICE_COLUMNS = {
    "open": ["open", "open_price", "open_price_adjusted"],
    "high": ["high", "high_price", "high_price_adjusted"],
    "low": ["low", "low_price", "low_price_adjusted"],
    "close": ["close", "close_price", "close_price_adjusted", "nav", "acc_nav"],
    "volume": ["volume", "vol"],
    "amount": ["amount", "turnover"],
}


@dataclass
class DataQualityReport:
    notes: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.notes.append(message)


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
        self.frames = self._load_frames()
        self.calendar = self._build_calendar()

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
            factor_col = _first_column(raw, ["adjust_factor", "hfq_factor", "qfq_factor"])
            factor = raw[factor_col].fillna(1.0) if factor_col else 1.0
            if factor_col is None:
                self.quality.add(f"{asset.asset_id}: no adjustment factor column; using raw prices.")

            normalized = pd.DataFrame({"date": raw["trade_date"]})
            close_col = _first_column(raw, PRICE_COLUMNS["close"])
            if close_col is None:
                raise ValueError(f"No close price column found in {path}")

            close = pd.to_numeric(raw[close_col], errors="coerce") * factor
            for field_name in ["open", "high", "low"]:
                source = _first_column(raw, PRICE_COLUMNS[field_name])
                if source is None:
                    normalized[field_name] = close
                    self.quality.add(f"{asset.asset_id}: missing {field_name}; filled with close.")
                else:
                    normalized[field_name] = pd.to_numeric(raw[source], errors="coerce") * factor
            normalized["close"] = close

            for field_name in ["volume", "amount"]:
                source = _first_column(raw, PRICE_COLUMNS[field_name])
                if source is None:
                    normalized[field_name] = 0.0
                    self.quality.add(f"{asset.asset_id}: missing {field_name}; filled with 0.")
                else:
                    normalized[field_name] = pd.to_numeric(raw[source], errors="coerce").fillna(0.0)

            normalized = normalized.sort_values("date").dropna(subset=["close"])
            if self.start_date:
                normalized = normalized[normalized["date"] >= self.start_date]
            if self.end_date:
                normalized = normalized[normalized["date"] <= self.end_date]

            previous_close = normalized["close"].shift(1)
            if asset.price_limit_pct is None:
                normalized["limit_up"] = None
                normalized["limit_down"] = None
            else:
                normalized["limit_up"] = previous_close * (1 + asset.price_limit_pct)
                normalized["limit_down"] = previous_close * (1 - asset.price_limit_pct)
            normalized["is_suspended"] = normalized["volume"].fillna(0.0) <= 0
            frames[asset.asset_id] = normalized.set_index("date", drop=False)
        return frames

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
                )
                continue

            prior = frame[frame.index < current_date]
            if not prior.empty:
                last = prior.iloc[-1]
                close = float(last["close"])
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
                )
        return bars

    def prices_on(self, current_date: date) -> dict[str, float]:
        return {asset_id: bar.close for asset_id, bar in self.bars_on(current_date).items()}

    def is_month_end(self, current_date: date) -> bool:
        try:
            idx = self.calendar.index(current_date)
        except ValueError:
            return False
        if idx == len(self.calendar) - 1:
            return True
        return self.calendar[idx + 1].month != current_date.month
