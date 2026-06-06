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
FUNDAMENTAL_COLUMNS = ["asset_id", "report_period", "announcement_date", "asof_date", "field", "value", "source", "updated_at"]

FIELD_ALIASES = {
    "pe": ["pe", "pe_ttm", "市盈率", "市盈率ttm"],
    "pb": ["pb", "市净率"],
    "roe": ["roe", "净资产收益率", "roe_weighted", "roe加权"],
    "debt_to_asset": ["debt_to_asset", "资产负债率", "debt_asset_ratio"],
    "dividend_yield": ["dividend_yield", "股息率", "dividend_rate"],
}


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


def normalize_fundamental_frame(raw: pd.DataFrame, asset_id: str, source: str, fields: list[str]) -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    if raw.empty:
        return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS), [f"{asset_id}: empty fundamental frame"]

    ann_col = _first_column(raw, ["announcement_date", "ann_date", "annDate", "公告日期", "publish_date"])
    asof_col = _first_column(raw, ["asof_date", "effective_date"])
    period_col = _first_column(raw, ["report_period", "period", "报告期", "end_date", "报告日期"])
    if ann_col is None and asof_col is None:
        notes.append(f"{asset_id}: missing announcement_date/asof_date; rows skipped")
        return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS), notes

    rows: list[dict[str, Any]] = []
    for _, record in raw.iterrows():
        announcement_date = record.get(ann_col) if ann_col else record.get(asof_col)
        if pd.isna(announcement_date):
            notes.append(f"{asset_id}: missing announcement date row skipped")
            continue
        asof_date = record.get(asof_col) if asof_col else announcement_date
        report_period = record.get(period_col) if period_col else None
        for field in fields:
            source_col = _first_column(raw, FIELD_ALIASES.get(field, [field]))
            if source_col is None or pd.isna(record.get(source_col)):
                continue
            rows.append(
                {
                    "asset_id": asset_id,
                    "report_period": str(report_period) if report_period is not None and not pd.isna(report_period) else "",
                    "announcement_date": pd.to_datetime(announcement_date).strftime("%Y-%m-%d"),
                    "asof_date": pd.to_datetime(asof_date).strftime("%Y-%m-%d"),
                    "field": field,
                    "value": float(record[source_col]),
                    "source": source,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
    frame = pd.DataFrame(rows, columns=FUNDAMENTAL_COLUMNS)
    return frame, notes


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
                normalized.to_csv(path, index=False)
                self.quality.extend(f"{asset.asset_id}: {note}" for note in notes)
            elif not path.exists():
                raise FileNotFoundError(f"Standard market data missing for {asset.asset_id}: {path}. Run sync with --fetch or import CSV first.")
            self.quality.extend(self.validate_file(path, asset.asset_id))
        self._write_manifest()
        return self.quality

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


class FundamentalStore:
    def __init__(self, store_dir: str | Path, fields: list[str] | None = None, source=None):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.fields = fields or ["pe", "pb", "roe", "debt_to_asset", "dividend_yield"]
        self.source = source
        self.quality = DataQualityReport()

    def sync_financial_indicators(self, assets: list[Asset], fetch: bool = False) -> DataQualityReport:
        if fetch and self.source is None:
            self.source = FinshareDataSource(Path.cwd())
        for asset in assets:
            path = self.path_for(asset)
            if fetch:
                raw = self.source.fetch_financial_indicators(self._finshare_code(asset))
                normalized, notes = normalize_fundamental_frame(raw, asset.asset_id, "finshare", self.fields)
                normalized.to_csv(path, index=False)
                self.quality.extend(notes)
            elif not path.exists():
                self.quality.add(f"{asset.asset_id}: no local fundamental file at {path}")
                continue
            self.quality.extend(self.validate_file(path, asset.asset_id))
        self._write_manifest()
        return self.quality

    def import_csv(self, asset: Asset, raw_path: str | Path, source: str = "csv") -> Path:
        raw = pd.read_csv(raw_path)
        normalized, notes = normalize_fundamental_frame(raw, asset.asset_id, source, self.fields)
        path = self.path_for(asset)
        normalized.to_csv(path, index=False)
        self.quality.extend(notes)
        return path

    def path_for(self, asset: Asset) -> Path:
        return self.store_dir / f"{asset.code}.csv"

    def validate_file(self, path: str | Path, asset_id: str) -> list[str]:
        frame = pd.read_csv(path)
        notes: list[str] = []
        missing = [column for column in FUNDAMENTAL_COLUMNS if column not in frame.columns]
        if missing:
            notes.append(f"{asset_id}: missing fundamental columns {missing}")
        if "asof_date" in frame.columns and frame["asof_date"].isna().any():
            notes.append(f"{asset_id}: missing asof_date")
        if "announcement_date" in frame.columns and frame["announcement_date"].isna().any():
            notes.append(f"{asset_id}: missing announcement_date")
        return notes

    def _write_manifest(self) -> None:
        with (self.store_dir / "fundamental_manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(self.quality.to_dict(), handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _finshare_code(asset: Asset) -> str:
        if "." in asset.code:
            return asset.code
        return f"{asset.code}.{asset.exchange}" if asset.exchange in {"SH", "SZ"} else asset.code


class PointInTimeFundamentals:
    def __init__(self, fundamentals_dir: str | Path):
        self.fundamentals_dir = Path(fundamentals_dir)
        self.frame = self._load()

    def get(self, asset_id: str, asof_date: str | Any) -> dict[str, float]:
        if self.frame.empty:
            return {}
        current = parse_date(asof_date).isoformat()
        subset = self.frame[(self.frame["asset_id"] == asset_id) & (self.frame["asof_date"] <= current)]
        if subset.empty:
            return {}
        subset = subset.sort_values(["field", "asof_date", "announcement_date"]).groupby("field", as_index=False).tail(1)
        return {row["field"]: float(row["value"]) for _, row in subset.iterrows()}

    def filter(self, asset_ids: list[str], asof_date: str | Any, rules: dict[str, Any]) -> list[str]:
        selected: list[tuple[str, dict[str, float]]] = []
        for asset_id in asset_ids:
            values = self.get(asset_id, asof_date)
            if self._passes(values, rules):
                selected.append((asset_id, values))
        sort_by = rules.get("sort_by")
        if sort_by:
            reverse = bool(rules.get("descending", False))
            selected.sort(key=lambda item: item[1].get(sort_by, float("-inf") if reverse else float("inf")), reverse=reverse)
        limit = rules.get("limit")
        ids = [asset_id for asset_id, _ in selected]
        return ids[: int(limit)] if limit else ids

    def _load(self) -> pd.DataFrame:
        if not self.fundamentals_dir.exists():
            return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
        frames = []
        for path in self.fundamentals_dir.glob("*.csv"):
            if path.name.endswith("_raw.csv") or path.stat().st_size == 0:
                continue
            try:
                frame = pd.read_csv(path)
            except Exception:
                continue
            if all(column in frame.columns for column in FUNDAMENTAL_COLUMNS):
                frames.append(frame[FUNDAMENTAL_COLUMNS])
        if not frames:
            return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
        combined = pd.concat(frames, ignore_index=True)
        combined["asof_date"] = pd.to_datetime(combined["asof_date"]).dt.strftime("%Y-%m-%d")
        combined["announcement_date"] = pd.to_datetime(combined["announcement_date"]).dt.strftime("%Y-%m-%d")
        return combined.dropna(subset=["asset_id", "asof_date", "field", "value"])

    @staticmethod
    def _passes(values: dict[str, float], rules: dict[str, Any]) -> bool:
        for field, value in rules.get("min", {}).items():
            if values.get(field) is None or values[field] < float(value):
                return False
        for field, value in rules.get("max", {}).items():
            if values.get(field) is None or values[field] > float(value):
                return False
        for field in rules.get("required", []):
            if field not in values:
                return False
        return True
