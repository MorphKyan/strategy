from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.platform_core.data_store import MarketDataStore
from src.platform_core.models import Asset


class _FakeSource:
    """可编程的假数据源：每次 fetch 返回预设的行情帧。"""

    def __init__(self, frames: list[pd.DataFrame]):
        self.frames = list(frames)
        self.calls = 0

    def fetch_bars(self, code, start=None, end=None, adjust=None):
        frame = self.frames[min(self.calls, len(self.frames) - 1)]
        self.calls += 1
        return frame.copy()


def _bars(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [d for d, _ in rows],
            "open": [c for _, c in rows],
            "high": [c for _, c in rows],
            "low": [c for _, c in rows],
            "close": [c for _, c in rows],
            "volume": [1000.0] * len(rows),
            "amount": [10000.0] * len(rows),
            "adjust_factor": [1.0] * len(rows),
        }
    )


ASSET = Asset(asset_id="CN_ETF:510300.SH", code="510300", name="沪深300ETF", exchange="SH")


def test_resync_with_identical_data_leaves_file_untouched(tmp_path: Path):
    source = _FakeSource([_bars([("2026-07-10", 4.829), ("2026-07-13", 4.744)])])
    store = MarketDataStore(tmp_path, source=source)
    store.sync_assets([ASSET], start=None, end=None, fetch=True)
    path = tmp_path / "510300.csv"
    first_text = path.read_text(encoding="utf-8")

    # 第二次同步：同样的数据 → 文件内容必须逐字节不变（updated_at 不重打）
    MarketDataStore(tmp_path, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    assert path.read_text(encoding="utf-8") == first_text


def test_new_rows_get_fresh_timestamp_old_rows_keep_theirs(tmp_path: Path):
    day1 = _bars([("2026-07-10", 4.829)])
    day2 = _bars([("2026-07-10", 4.829), ("2026-07-13", 4.744)])
    source = _FakeSource([day1, day2])
    store_dir = tmp_path

    MarketDataStore(store_dir, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    first = pd.read_csv(store_dir / "510300.csv", dtype=str)
    stamp_0710 = first.loc[first["trade_date"] == "2026-07-10", "updated_at"].iloc[0]

    MarketDataStore(store_dir, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    second = pd.read_csv(store_dir / "510300.csv", dtype=str)

    assert second.loc[second["trade_date"] == "2026-07-10", "updated_at"].iloc[0] == stamp_0710
    assert len(second) == 2  # 新交易日已追加


def test_revised_value_refreshes_that_rows_timestamp_only(tmp_path: Path):
    original = _bars([("2026-07-10", 4.829), ("2026-07-13", 4.744)])
    revised = _bars([("2026-07-10", 4.829), ("2026-07-13", 4.750)])  # 07-13 数值修订
    source = _FakeSource([original, revised])

    MarketDataStore(tmp_path, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    first = pd.read_csv(tmp_path / "510300.csv", dtype=str)
    stamps = dict(zip(first["trade_date"], first["updated_at"]))

    import time

    time.sleep(1.1)  # 保证新时间戳可区分（秒级精度）
    MarketDataStore(tmp_path, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    second = pd.read_csv(tmp_path / "510300.csv", dtype=str)

    assert second.loc[second["trade_date"] == "2026-07-10", "updated_at"].iloc[0] == stamps["2026-07-10"]
    assert second.loc[second["trade_date"] == "2026-07-13", "updated_at"].iloc[0] != stamps["2026-07-13"]
    assert second.loc[second["trade_date"] == "2026-07-13", "close"].iloc[0] == "4.75"


# ---------------------------------------------------------------- 事件表保护


def test_merge_event_table_never_deletes_and_flags_conflicts():
    existing = pd.DataFrame(
        [
            {"code": "510500", "split_date": "2022-08-26", "split_ratio": "1.1454"},
            {"code": "510500", "split_date": "2015-04-14", "split_ratio": "0.2803"},
        ]
    )
    # 上游异常：丢了两条已有事件，塞进一条新键的可疑事件
    fetched = pd.DataFrame([{"code": "510500", "split_date": "2019-01-24", "split_ratio": "0.01"}])

    from src.platform_core.corporate_actions import merge_event_table

    merged, notes, additions = merge_event_table(existing, fetched, ["code", "split_date"])

    assert len(merged) == 2  # 已有事件一条不丢
    assert {row["split_date"] for row in merged.to_dict("records")} == {"2022-08-26", "2015-04-14"}
    assert len(additions) == 1 and additions[0]["split_date"] == "2019-01-24"
    assert any("上游缺失" in note for note in notes)


def test_merge_event_table_keeps_existing_on_same_key_conflict():
    existing = pd.DataFrame([{"code": "510500", "split_date": "2022-08-26", "split_ratio": "1.1454"}])
    fetched = pd.DataFrame([{"code": "510500", "split_date": "2022-08-26", "split_ratio": "9.9999"}])

    from src.platform_core.corporate_actions import merge_event_table

    merged, _, additions = merge_event_table(existing, fetched, ["code", "split_date"])
    assert additions == []
    assert merged.iloc[0]["split_ratio"] == "1.1454"


def test_validate_split_against_prices(tmp_path: Path):
    # 拆前收 2.0，1:2 拆分 → 拆后首日应≈1.0
    pd.DataFrame(
        {"trade_date": ["2024-01-30", "2024-01-31", "2024-02-01"], "close": [2.0, 2.0, 1.01]}
    ).to_csv(tmp_path / "TEST01.csv", index=False)

    from src.platform_core.corporate_actions import validate_split_against_prices

    ok, _ = validate_split_against_prices("TEST01", "2024-01-31", 2.0, tmp_path)
    assert ok
    # 错误比例 1:0.01（价格应暴涨百倍，实际没有）→ 拒绝
    ok, verdict = validate_split_against_prices("TEST01", "2024-01-31", 0.01, tmp_path)
    assert not ok and "不符" in verdict
    # 无价格数据 → 保守拒绝
    ok, _ = validate_split_against_prices("NODATA", "2024-01-31", 2.0, tmp_path)
    assert not ok


def test_unchanged_note_recorded(tmp_path: Path):
    source = _FakeSource([_bars([("2026-07-10", 4.829)])])
    MarketDataStore(tmp_path, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    report = MarketDataStore(tmp_path, source=source).sync_assets([ASSET], start=None, end=None, fetch=True)
    assert any("data unchanged" in note for note in report.notes)
