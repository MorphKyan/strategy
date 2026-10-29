from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from io import StringIO
from math import isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pandas as pd

from src.platform_core.data_sources import FinshareDataSource
from src.platform_core.models import Asset
from src.platform_core.storage import write_json


MARKET_COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor", "source", "updated_at"]

# 主备数据源之间 volume/amount 常有小数级噪音（如 10171325.0 vs 10171324.85，
# 手/份换算差异），价格列一致时按容差视为同一行，避免换源日反复 churn。
JITTER_COLUMNS = {"volume", "amount"}
JITTER_RELATIVE_TOLERANCE = 0.01


def validate_market_dates(latest: dict[str, date | None], today: date) -> None:
    """检查整批标的的有效末日；历史样本窗口不改变当前行情前置条件。"""
    detail = ", ".join(f"{asset_id}={day}" for asset_id, day in latest.items())
    if not latest or any(day is None for day in latest.values()):
        raise RuntimeError(f"Missing valid market dates: {detail}")
    if len(set(latest.values())) != 1:
        raise RuntimeError(f"Market dates are not aligned; sync every required asset: {detail}")
    day = next(iter(latest.values()))
    if day > today:
        raise RuntimeError(f"Future market date after today ({today}): {detail}")
    if (today - day).days > 7:
        raise RuntimeError(f"Stale market data; latest date is older than 7 days from today ({today}): {detail}")


def _stringify_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """按 to_csv 的实际序列化结果把 frame 转成字符串表，保证比较与落盘同构。"""
    buffer = StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n")
    buffer.seek(0)
    return pd.read_csv(buffer, dtype=str, keep_default_na=False)


def _rows_equivalent(new_row: dict, old_row: dict, columns: list[str]) -> bool:
    for column in columns:
        new_value = new_row.get(column, "")
        old_value = old_row.get(column, "")
        if new_value == old_value:
            continue
        if column in JITTER_COLUMNS:
            try:
                new_num, old_num = float(new_value), float(old_value)
            except (TypeError, ValueError):
                return False
            base = max(abs(old_num), 1e-12)
            if abs(new_num - old_num) / base <= JITTER_RELATIVE_TOLERANCE:
                continue
        return False
    return True


def write_csv_stable(path: Path, frame: pd.DataFrame, key_column: str | None = None) -> bool:
    """内容感知 CSV 写盘：diff 只反映真实数据变化。返回是否写盘。

    - key_column 给定且新旧行等价（价格列严格相等、volume/amount 在容差内）时，
      **保留旧行原样**（含 updated_at 时间戳与噪音前的数值）；
    - 全文件内容与磁盘一致时完全不写（mtime 都不动）；
    - 写盘时保留文件原有行尾（仓库快照历史上是 CRLF——pandas 在 Windows 直写
      文件的默认行为——改行尾会制造一次性全文件假 diff）。

    行情快照随 git 版本管理后，每日同步给所有行重打 updated_at 曾制造数万行
    假 diff、天天弄脏工作区；本函数是该问题的根治点，事件表与合成数据生成器
    也复用它。
    """
    candidate = _stringify_frame(frame)
    existing: pd.DataFrame | None = None
    if path.exists():
        try:
            existing = pd.read_csv(path, dtype=str, keep_default_na=False)
        except Exception:
            existing = None
    if (
        key_column
        and existing is not None
        and key_column in existing.columns
        and key_column in candidate.columns
    ):
        compare_columns = [c for c in candidate.columns if c != "updated_at" and c in existing.columns]
        old_by_key = {row[key_column]: row for row in existing.to_dict("records")}
        restored = []
        for row in candidate.to_dict("records"):
            old = old_by_key.get(row[key_column])
            if old is not None and _rows_equivalent(row, old, compare_columns):
                row = {column: old.get(column, row.get(column, "")) for column in candidate.columns}
            restored.append(row)
        candidate = pd.DataFrame(restored, columns=list(candidate.columns))

    buffer = StringIO()
    candidate.to_csv(buffer, index=False, lineterminator="\n")
    text = buffer.getvalue()  # 统一 LF 的规范形

    newline_style = os.linesep
    if path.exists():
        try:
            raw = path.read_bytes()
            if raw:
                newline_style = "\r\n" if b"\r\n" in raw else "\n"
            if raw.decode("utf-8").replace("\r\n", "\n") == text:
                return False
        except (OSError, UnicodeDecodeError):
            pass
    output = text if newline_style == "\n" else text.replace("\n", "\r\n")
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(output)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def merge_observations(path: Path, fetched: pd.DataFrame, date_column: str = "trade_date") -> pd.DataFrame:
    """仅更新响应实际包含的日期，保留短窗和临时缺行之外的本地历史。"""
    if fetched.empty:
        raise ValueError("No fetched observations; existing history was preserved.")
    frames = [pd.read_csv(path), fetched.copy()] if path.exists() else [fetched.copy()]
    for frame in frames:
        dates = pd.to_datetime(frame[date_column], errors="raise")
        if dates.isna().any() or dates.duplicated().any():
            raise ValueError(f"Missing or duplicate {date_column}; existing history was preserved.")
        frame[date_column] = dates.dt.strftime("%Y-%m-%d")
    return (pd.concat(frames, ignore_index=True)
            .drop_duplicates(date_column, keep="last")
            .sort_values(date_column).reset_index(drop=True))



@dataclass
class DataQualityReport:
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"notes": self.notes, "generated_at": datetime.now().isoformat(timespec="seconds")}


def assets_from_config(items: list[dict[str, Any]]) -> list[Asset]:
    assets = [
        Asset(
            asset_id=item["asset_id"],
            code=str(item["code"]),
            name=item.get("name", item["code"]),
            asset_type=item.get("asset_type", "etf"),
            exchange=item.get("exchange", "CN"),
            currency=item.get("currency", "CNY"),
            lot_size=item.get("lot_size", 100 if item.get("asset_type", "etf") == "etf" else 1),
            price_limit_pct=item.get("price_limit_pct", 0.10 if item.get("asset_type", "etf") == "etf" else None),
        )
        for item in items
    ]
    for field_name in ("asset_id", "code"):
        values = [getattr(asset, field_name) for asset in assets]
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate asset {field_name} in config.")
    return assets


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

    trade_date_col = _first_column(raw, ["trade_date", "date", "datetime", "日期"])
    close_col = _first_column(raw, ["close", "close_price", "nav", "acc_nav", "收盘价", "收盘"])
    if trade_date_col is None or close_col is None:
        raise ValueError("Market data requires trade_date/date and close/close_price columns.")

    factor_col = _first_column(raw, ["adjust_factor", "hfq_factor", "qfq_factor"])
    factor = pd.to_numeric(raw[factor_col], errors="raise").fillna(1.0) if factor_col else 1.0
    if factor_col is None:
        notes.append("missing adjust_factor; using 1.0")

    out = pd.DataFrame()
    out["trade_date"] = pd.to_datetime(raw[trade_date_col]).dt.strftime("%Y-%m-%d")
    close = pd.to_numeric(raw[close_col], errors="coerce")
    for target, candidates in {
        "open": ["open", "open_price", "开盘价", "开盘"],
        "high": ["high", "high_price", "最高价", "最高"],
        "low": ["low", "low_price", "最低价", "最低"],
    }.items():
        source_col = _first_column(raw, candidates)
        if source_col is None:
            out[target] = close
            notes.append(f"missing {target}; filled with close")
        else:
            out[target] = pd.to_numeric(raw[source_col], errors="coerce")
    out["close"] = close
    for target, candidates in {"volume": ["volume", "vol", "成交量"], "amount": ["amount", "turnover", "成交额"]}.items():
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

    for column in ("close", "adjust_factor"):
        if (out[column] <= 0).any() or not out[column].map(isfinite).all():
            raise ValueError(f"Market {column} values must be finite and positive; existing history was preserved.")
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
        latest = {}
        for asset in assets:
            path = self.store_dir / f"{asset.code}.csv"
            is_synthetic = asset.code.endswith("_3X")
            if fetch and not is_synthetic:
                fetch_start = start or "1990-01-01"
                fetch_end = end or date.today().isoformat()
                raw = self.source.fetch_bars(self._finshare_code(asset), start=fetch_start, end=fetch_end, adjust=None)
                normalized, notes = normalize_market_frame(raw, "finshare")
                if normalized.empty:
                    raise RuntimeError(
                        f"Market data provider returned no valid rows for {asset.asset_id} "
                        f"between {fetch_start} and {fetch_end}; existing file was preserved."
                    )
                merged = merge_observations(path, normalized)
                preserved = len(merged) - len(normalized)
                if preserved:
                    self.quality.notes.append(
                        f"{asset.asset_id}: kept {preserved} local rows absent from fetched history (short-window source guard)"
                    )
                if not write_csv_stable(path, merged, key_column="trade_date"):
                    self.quality.notes.append(f"{asset.asset_id}: data unchanged; file untouched")
                self.quality.notes.extend(f"{asset.asset_id}: {note}" for note in notes)
            elif fetch and is_synthetic:
                if not path.exists():
                    raise FileNotFoundError(
                        f"Synthetic market data missing for {asset.asset_id}: {path}. "
                        "Regenerate it with the canonical synthetic-data generator."
                    )
                self.quality.notes.append(f"{asset.asset_id}: synthetic asset preserved; provider fetch skipped")
            elif not path.exists():
                raise FileNotFoundError(f"Standard market data missing for {asset.asset_id}: {path}. Run sync with --fetch or import CSV first.")
            frame = pd.read_csv(path)
            missing = [column for column in MARKET_COLUMNS if column not in frame.columns]
            if missing:
                self.quality.notes.append(f"{asset.asset_id}: missing market columns {missing}")
            if "trade_date" in frame.columns and frame["trade_date"].duplicated().any():
                raise ValueError(f"{asset.asset_id}: duplicate trade_date rows")
            if "close" in frame.columns:
                close = pd.to_numeric(frame["close"], errors="coerce")
                if (close <= 0).any() or not close.dropna().map(isfinite).all():
                    raise ValueError(f"{asset.asset_id}: close values must be finite and positive")
            valid_dates = pd.to_datetime(frame.get("trade_date", pd.Series(dtype=str)), errors="coerce").dropna()
            latest[asset.asset_id] = valid_dates.max().date() if not valid_dates.empty else None
        validate_market_dates(latest, date.today())
        write_json(self.store_dir / "data_manifest.json", self.quality.to_dict())
        return self.quality

    @staticmethod
    def _finshare_code(asset: Asset) -> str:
        if "." in asset.code:
            return asset.code
        return f"{asset.code}.{asset.exchange}" if asset.exchange in {"SH", "SZ"} else asset.code
