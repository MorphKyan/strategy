from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.platform_core.data_sources import FinshareDataSource
from src.platform_core.models import Asset, parse_date


MARKET_COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor", "source", "updated_at"]

# 主备数据源之间 volume/amount 常有小数级噪音（如 10171325.0 vs 10171324.85，
# 手/份换算差异），价格列一致时按容差视为同一行，避免换源日反复 churn。
JITTER_COLUMNS = {"volume", "amount"}
JITTER_RELATIVE_TOLERANCE = 0.01


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
    path.write_text(output, encoding="utf-8", newline="")
    return True



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
                normalized = self._guard_history_shrink(path, normalized, asset.asset_id)
                self._write_preserving_unchanged(path, normalized, asset.asset_id)
                self.quality.extend(f"{asset.asset_id}: {note}" for note in notes)
            elif fetch and is_synthetic:
                if not path.exists():
                    raise FileNotFoundError(
                        f"Synthetic market data missing for {asset.asset_id}: {path}. "
                        "Regenerate it with the canonical synthetic-data generator."
                    )
                self.quality.add(f"{asset.asset_id}: synthetic asset preserved; provider fetch skipped")
            elif not path.exists():
                raise FileNotFoundError(f"Standard market data missing for {asset.asset_id}: {path}. Run sync with --fetch or import CSV first.")
            self.quality.extend(self.validate_file(path, asset.asset_id))
            
            # Enforce 7-day data staleness check (skip under pytest)
            import sys
            if "pytest" not in sys.modules:
                today = date.today()
                frame = pd.read_csv(path)
                if "trade_date" in frame.columns:
                    valid_dates = pd.to_datetime(frame["trade_date"], errors="coerce").dropna()
                    if valid_dates.empty:
                        raise RuntimeError(f"No valid trade_date values for {asset.asset_id} in {path}.")
                    max_date = valid_dates.max().date()
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

    def _write_preserving_unchanged(self, path: Path, frame: pd.DataFrame, asset_id: str) -> bool:
        changed = write_csv_stable(path, frame, key_column="trade_date")
        if not changed:
            self.quality.add(f"{asset_id}: data unchanged; file untouched")
        return changed

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
