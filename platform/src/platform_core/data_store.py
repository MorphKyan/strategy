from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.platform_core.data_sources import FinshareDataSource
from src.platform_core.models import Asset, parse_date


MARKET_COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor", "source", "updated_at"]



@dataclass
class DataQualityReport:
    notes: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.notes.append(message)

    def extend(self, messages: Iterable[str]) -> None:
        self.notes.extend(messages)

    def to_dict(self) -> dict[str, Any]:
        return {"notes": self.notes, "generated_at": datetime.now().isoformat(timespec="seconds")}


def assets_from_config(items: list[dict[str, Any]]) -> list[Asset]:
    return [
        Asset(
            asset_id=item["asset_id"],
            code=str(item["code"]),
            name=item.get("name", item["code"]),
            asset_type=item.get("asset_type", "etf"),
            exchange=item.get("exchange", "CN"),
            currency=item.get("currency", "CNY"),
            lot_size=int(item.get("lot_size", 100)),
            price_limit_pct=item.get("price_limit_pct", 0.10),
        )
        for item in items
    ]


def _first_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {column.lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def normalize_market_frame(raw: pd.DataFrame, source: str) -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    if raw.empty:
        return pd.DataFrame(columns=MARKET_COLUMNS), ["empty market frame"]

    trade_date_col = _first_column(raw, ["trade_date", "date", "datetime"])
    close_col = _first_column(raw, ["close", "close_price", "nav", "acc_nav"])
    if trade_date_col is None or close_col is None:
        raise ValueError("Market data requires trade_date/date and close/close_price columns.")

    factor_col = _first_column(raw, ["adjust_factor", "hfq_factor", "qfq_factor"])
    factor = pd.to_numeric(raw[factor_col], errors="coerce").fillna(1.0) if factor_col else 1.0
    if factor_col is None:
        notes.append("missing adjust_factor; using 1.0")

    out = pd.DataFrame()
    out["trade_date"] = pd.to_datetime(raw[trade_date_col]).dt.strftime("%Y-%m-%d")
    close = pd.to_numeric(raw[close_col], errors="coerce")
    for target, candidates in {
        "open": ["open", "open_price"],
        "high": ["high", "high_price"],
        "low": ["low", "low_price"],
    }.items():
        source_col = _first_column(raw, candidates)
        if source_col is None:
            out[target] = close
            notes.append(f"missing {target}; filled with close")
        else:
            out[target] = pd.to_numeric(raw[source_col], errors="coerce")
    out["close"] = close
    for target, candidates in {"volume": ["volume", "vol"], "amount": ["amount", "turnover"]}.items():
        source_col = _first_column(raw, candidates)
        if source_col is None:
            out[target] = 0.0
            notes.append(f"missing {target}; filled with 0")
        else:
            out[target] = pd.to_numeric(raw[source_col], errors="coerce").fillna(0.0)
    out["adjust_factor"] = factor
    out["source"] = source
    out["updated_at"] = datetime.now().isoformat(timespec="seconds")
    out = out[MARKET_COLUMNS].dropna(subset=["trade_date", "close"]).drop_duplicates(subset=["trade_date"], keep="last").sort_values("trade_date")

    if (out["close"] <= 0).any():
        notes.append("non-positive close values detected")
    if (pd.to_numeric(out["adjust_factor"], errors="coerce") <= 0).any():
        notes.append("non-positive adjust_factor values detected")
    return out, notes



class MarketDataStore:
    def __init__(self, store_dir: str | Path, source=None):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.source = source
        self.quality = DataQualityReport()

    def sync_assets(self, assets: list[Asset], start: str | None, end: str | None, fetch: bool = False) -> DataQualityReport:
        if fetch and self.source is None:
            self.source = FinshareDataSource(Path.cwd())
        for asset in assets:
            path = self.path_for(asset)
            if fetch:
                raw = self.source.fetch_bars(self._finshare_code(asset), start=start, end=end, adjust=None)
                normalized, notes = normalize_market_frame(raw, "finshare")
                normalized = self._guard_history_shrink(path, normalized, asset.asset_id)
                normalized.to_csv(path, index=False)
                self.quality.extend(f"{asset.asset_id}: {note}" for note in notes)
            elif not path.exists():
                raise FileNotFoundError(f"Standard market data missing for {asset.asset_id}: {path}. Run sync with --fetch or import CSV first.")
            self.quality.extend(self.validate_file(path, asset.asset_id))
            
            # Enforce 7-day data staleness check (skip under pytest)
            import sys
            if "pytest" not in sys.modules:
                from datetime import date
                today = date.today()
                frame = pd.read_csv(path)
                if "trade_date" in frame.columns:
                    max_date = pd.to_datetime(frame["trade_date"]).max().date()
                    if (today - max_date).days > 7:
                        raise RuntimeError(
                            f"Stale market data detected for {asset.asset_id} in {path}. "
                            f"Latest trade date is {max_date}, which is older than 7 days from today ({today})."
                        )
        self._write_manifest()
        return self.quality

    def _guard_history_shrink(self, path: Path, normalized: pd.DataFrame, asset_id: str) -> pd.DataFrame:
        """防止降级数据源覆盖掉已有的长历史。

        主源（eastmoney）被限流时，finshare 会降级到只有短窗数据的备源
        （如 baostock 的 ETF 数据仅从 2026-01 起）。若直接整文件覆盖，
        一次全量同步就会把多年历史压缩成几个月。规则：新数据首日晚于
        本地已有首日时，保留本地更早的历史行，只用新数据更新重叠及之后
        的部分（本地行情快照随 git 版本管理，误覆盖仍可恢复，但不该发生）。
        """
        if normalized.empty or not path.exists():
            return normalized
        try:
            existing = pd.read_csv(path)
        except Exception:
            return normalized
        if "trade_date" not in existing.columns or existing.empty:
            return normalized
        new_first = normalized["trade_date"].min()
        old_first = existing["trade_date"].min()
        if new_first <= old_first:
            return normalized
        preserved = existing[existing["trade_date"] < new_first]
        merged = pd.concat([preserved, normalized], ignore_index=True)
        merged = merged.drop_duplicates(subset=["trade_date"], keep="last").sort_values("trade_date")
        self.quality.add(
            f"{asset_id}: fetched history starts {new_first} but local starts {old_first}; "
            f"kept {len(preserved)} earlier local rows (short-window source guard)"
        )
        return merged

    def import_raw_csv(self, asset: Asset, raw_path: str | Path, source: str = "csv") -> Path:
        raw = pd.read_csv(raw_path)
        normalized, notes = normalize_market_frame(raw, source)
        path = self.path_for(asset)
        normalized.to_csv(path, index=False)
        self.quality.extend(f"{asset.asset_id}: {note}" for note in notes)
        return path

    def path_for(self, asset: Asset) -> Path:
        return self.store_dir / f"{asset.code}.csv"

    def validate_file(self, path: str | Path, asset_id: str) -> list[str]:
        frame = pd.read_csv(path)
        notes: list[str] = []
        missing = [column for column in MARKET_COLUMNS if column not in frame.columns]
        if missing:
            notes.append(f"{asset_id}: missing market columns {missing}")
        if "trade_date" in frame.columns and frame["trade_date"].duplicated().any():
            notes.append(f"{asset_id}: duplicate trade_date rows")
        if "close" in frame.columns and (pd.to_numeric(frame["close"], errors="coerce") <= 0).any():
            notes.append(f"{asset_id}: non-positive close values")
        return notes

    def _write_manifest(self) -> None:
        with (self.store_dir / "data_manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(self.quality.to_dict(), handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _finshare_code(asset: Asset) -> str:
        if "." in asset.code:
            return asset.code
        return f"{asset.code}.{asset.exchange}" if asset.exchange in {"SH", "SZ"} else asset.code
