from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.platform_core.data import LocalCsvBarData
from src.platform_core.models import Asset


def load_research_hfq_series(research_data_dir: str | Path, code: str) -> pd.Series:
    data_dir = Path(research_data_dir)
    price_path = data_dir / f"{code}.csv"
    factor_path = data_dir / f"{code}_hfq_factor.csv"
    if not price_path.exists():
        raise FileNotFoundError(f"Research price file not found: {price_path}")
    if not factor_path.exists():
        raise FileNotFoundError(f"Research HFQ factor file not found: {factor_path}")
    price = pd.read_csv(price_path, parse_dates=["trade_date"])
    factor = pd.read_csv(factor_path, parse_dates=["trade_date"])
    merged = pd.merge(
        price[["trade_date", "close_price"]],
        factor[["trade_date", "hfq_factor"]],
        on="trade_date",
        how="left",
    )
    merged["hfq_factor"] = merged["hfq_factor"].ffill().fillna(1.0)
    merged["research_hfq_close"] = pd.to_numeric(merged["close_price"], errors="coerce") * pd.to_numeric(
        merged["hfq_factor"], errors="coerce"
    )
    return merged.set_index("trade_date")["research_hfq_close"].dropna().sort_index()


def load_platform_close_series(platform_data_dir: str | Path, code: str, start: str | None = None, end: str | None = None) -> pd.Series:
    asset = Asset(asset_id=code, code=code, name=code, lot_size=1)
    data = LocalCsvBarData(platform_data_dir, [asset], start_date=start, end_date=end)
    frame = data.frames[code].copy()
    frame.index = pd.to_datetime(frame.index)
    return frame["adj_close"].dropna().sort_index()


def compare_hfq_data(
    codes: list[str],
    research_data_dir: str | Path,
    platform_data_dir: str | Path,
    start: str | None = None,
    end: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    detail_frames = []
    for code in codes:
        research = load_research_hfq_series(research_data_dir, code)
        platform = load_platform_close_series(platform_data_dir, code, start=start, end=end)
        if start:
            research = research[research.index >= pd.to_datetime(start)]
        if end:
            research = research[research.index <= pd.to_datetime(end)]
        joined = pd.concat([research, platform.rename("platform_close")], axis=1, join="inner")
        joined["code"] = code
        joined["abs_diff"] = (joined["research_hfq_close"] - joined["platform_close"]).abs()
        joined["rel_diff"] = joined["abs_diff"] / joined["research_hfq_close"].abs().replace(0, pd.NA)
        detail_frames.append(joined.reset_index(names="trade_date"))
        rows.append(
            {
                "code": code,
                "research_observations": int(len(research)),
                "platform_observations": int(len(platform)),
                "common_observations": int(len(joined)),
                "research_start": research.index.min().strftime("%Y-%m-%d") if len(research) else None,
                "research_end": research.index.max().strftime("%Y-%m-%d") if len(research) else None,
                "platform_start": platform.index.min().strftime("%Y-%m-%d") if len(platform) else None,
                "platform_end": platform.index.max().strftime("%Y-%m-%d") if len(platform) else None,
                "max_abs_diff": float(joined["abs_diff"].max()) if len(joined) else None,
                "mean_abs_diff": float(joined["abs_diff"].mean()) if len(joined) else None,
                "max_rel_diff": float(joined["rel_diff"].max()) if len(joined) else None,
                "mean_rel_diff": float(joined["rel_diff"].mean()) if len(joined) else None,
            }
        )
    detail = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    summary = {
        "codes": codes,
        "research_data_dir": str(research_data_dir),
        "platform_data_dir": str(platform_data_dir),
        "start": start,
        "end": end,
        "rows": rows,
    }
    return detail, summary


def write_hfq_validation(output_dir: str | Path, detail: pd.DataFrame, summary: dict[str, Any]) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "hfq_detail.csv", index=False)
    (output_dir / "hfq_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# HFQ 数据链路校验",
        "",
        f"- 旧研究系统数据目录：`{summary['research_data_dir']}`",
        f"- 新平台数据目录：`{summary['platform_data_dir']}`",
        f"- 开始日期：`{summary.get('start')}`",
        f"- 结束日期：`{summary.get('end')}`",
        "",
        "## 摘要",
    ]
    for row in summary["rows"]:
        lines.append(
            f"- `{row['code']}` 共同样本数={row['common_observations']} 最大绝对差={row['max_abs_diff']} 最大相对差={row['max_rel_diff']}"
        )
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
