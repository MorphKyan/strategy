"""指数估值入库脚本：非交易日剔除、代码规范化、去重、列裁剪。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "ingest_index_valuation",
    Path(__file__).resolve().parents[1] / "scripts" / "ingest_index_valuation.py",
)
ingest_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ingest_module)


def _write_raw(source_dir: Path, code: str, rows: list[dict]) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.insert(0, "OBJECT_ID", [f"{{GUID-{i}}}" for i in range(len(frame))])
    frame.insert(1, "S_INFO_WINDCODE", code)
    frame["OPDATE"] = "2022-08-04 19:30:57.000"
    frame["OPMODE"] = 1
    frame.to_csv(source_dir / f"AINDEXVALUATION_{code}.csv", index=False)


def test_ingest_drops_non_trading_days_and_normalizes_code(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # 交易日历基准：只有 01-02 与 01-06 是交易日（01-04/01-05 为周末）
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03", "2024-01-06"]}).to_csv(
        data_dir / f"{ingest_module.CALENDAR_REFERENCE}.csv", index=False
    )
    source = tmp_path / "raw"
    # Wind 按自然日导出：非交易日用前值填充且 TURNOVER 为空
    _write_raw(source, "h30184.CSI", [
        {"TRADE_DT": 20240102, "CON_NUM": 30, "PE_TTM": 10.0, "PB_LF": 2.0,
         "DIVIDEND_YIELD": 1.0, "TURNOVER": 0.5, "MV_TOTAL": 1e9},
        {"TRADE_DT": 20240103, "CON_NUM": 30, "PE_TTM": 11.0, "PB_LF": 2.1,
         "DIVIDEND_YIELD": 1.0, "TURNOVER": 0.6, "MV_TOTAL": 1e9},
        {"TRADE_DT": 20240104, "CON_NUM": 30, "PE_TTM": 11.0, "PB_LF": 2.1,
         "DIVIDEND_YIELD": 1.0, "TURNOVER": None, "MV_TOTAL": 1e9},
        {"TRADE_DT": 20240105, "CON_NUM": 30, "PE_TTM": 11.0, "PB_LF": 2.1,
         "DIVIDEND_YIELD": 1.0, "TURNOVER": None, "MV_TOTAL": 1e9},
        {"TRADE_DT": 20240106, "CON_NUM": 30, "PE_TTM": 12.0, "PB_LF": 2.2,
         "DIVIDEND_YIELD": 1.0, "TURNOVER": 0.7, "MV_TOTAL": 1e9},
    ])

    summary = ingest_module.ingest(source, data_dir, data_dir / "index_valuation")

    # 代码规范化为大写；输出文件按规范化后的代码命名
    assert summary["index_code"].tolist() == ["H30184.CSI"]
    out = pd.read_csv(data_dir / "index_valuation" / "H30184.CSI.csv")
    assert list(out.columns) == ingest_module.OUTPUT_COLUMNS
    # 周末两行被剔除，只剩三个交易日
    assert out["trade_date"].tolist() == ["2024-01-02", "2024-01-03", "2024-01-06"]
    assert summary["dropped"].iloc[0] == 2
    # 交叉校验计数：被丢的都无成交、保留的都有成交
    assert summary["warn_dropped_tradable"].iloc[0] == 0
    assert summary["warn_kept_no_turnover"].iloc[0] == 0
    # Wind 元数据列不得残留
    assert not {"OBJECT_ID", "OPDATE", "OPMODE", "S_INFO_WINDCODE"} & set(out.columns)


@pytest.mark.parametrize("duplicates", [2, 32])
def test_ingest_dedupes_same_day_rows(tmp_path: Path, duplicates: int) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03"]}).to_csv(
        data_dir / f"{ingest_module.CALENDAR_REFERENCE}.csv", index=False
    )
    source = tmp_path / "raw"
    rows = [{"TRADE_DT": 20240102 + i % 2, "CON_NUM": 30, "PE_TTM": 10.0, "PB_LF": float(i + 1),
             "DIVIDEND_YIELD": 1.0, "TURNOVER": 0.5, "MV_TOTAL": 1e9}
            for i in range(duplicates * 2)]
    _write_raw(source, "000913.SH", rows)

    ingest_module.ingest(source, data_dir, data_dir / "index_valuation")

    out = pd.read_csv(data_dir / "index_valuation" / "000913.SH.csv")
    assert len(out) == 2
    assert out["pb_lf"].tolist() == pytest.approx([duplicates * 2 - 1, duplicates * 2])


def test_ingest_merges_short_exports_and_leaves_identical_file_untouched(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03", "2024-01-04"]}).to_csv(
        data_dir / f"{ingest_module.CALENDAR_REFERENCE}.csv", index=False
    )
    source = tmp_path / "raw"
    rows = [{"TRADE_DT": day, "CON_NUM": 30, "PE_TTM": 10.0, "PB_LF": pb,
             "DIVIDEND_YIELD": 1.0, "TURNOVER": 0.5, "MV_TOTAL": 1e9}
            for day, pb in [(20240102, 2.0), (20240103, 2.1), (20240104, 2.2)]]
    output_dir = data_dir / "index_valuation"
    _write_raw(source, "000913.SH", rows[:2])
    ingest_module.ingest(source, data_dir, output_dir)

    rows[1]["PB_LF"] = 2.5
    _write_raw(source, "000913.SH", rows[1:])
    ingest_module.ingest(source, data_dir, output_dir)
    output = output_dir / "000913.SH.csv"
    stored = pd.read_csv(output)
    assert stored["trade_date"].tolist() == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert stored["pb_lf"].tolist() == pytest.approx([2.0, 2.5, 2.2])

    before, modified = output.read_bytes(), output.stat().st_mtime_ns
    ingest_module.ingest(source, data_dir, output_dir)
    assert output.read_bytes() == before
    assert output.stat().st_mtime_ns == modified

    _write_raw(source, "000913.SH", [{**rows[0], "TRADE_DT": 20240107}])
    with pytest.raises(ValueError, match="No fetched observations"):
        ingest_module.ingest(source, data_dir, output_dir)
    assert output.read_bytes() == before
