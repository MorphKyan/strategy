from __future__ import annotations

from datetime import datetime
from math import isfinite
from pathlib import Path

import pandas as pd

from src.platform_core.data_store import write_csv_stable


GENERATED_FACTOR_SOURCE = "corporate_actions"
LEGACY_FACTOR_SOURCE = "legacy_research"


def sync_corporate_action_hfq_factor(code: str, data_dir: str | Path) -> str:
    """Create or incrementally extend an HFQ sidecar from market bars and corporate actions.

    Historical factor rows (including legacy research sidecars) are preserved to maintain
    continuity. When market bars extend beyond the existing factor cutoff, new dates are
    seamlessly appended, compounding any newly occurring dividends or splits with source
    and updated_at metadata.
    """
    root = Path(data_dir)
    market_path = root / f"{code}.csv"
    factor_path = root / f"{code}_hfq_factor.csv"
    if not market_path.exists():
        return f"{code}: market data missing; HFQ factor skipped"

    market = pd.read_csv(market_path, usecols=["trade_date", "close"])
    market["trade_date"] = pd.to_datetime(market["trade_date"], errors="coerce")
    market["close"] = pd.to_numeric(market["close"], errors="coerce")
    market = (
        market.dropna(subset=["trade_date", "close"])
        .drop_duplicates("trade_date", keep="last")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    if market.empty:
        return f"{code}: no valid market rows; HFQ factor skipped"

    market_max_date = market["trade_date"].max()

    existing_df: pd.DataFrame | None = None
    if factor_path.exists():
        raw_existing = pd.read_csv(factor_path)
        if not {"trade_date", "hfq_factor"}.issubset(raw_existing.columns) or raw_existing.empty:
            raise ValueError(f"Invalid existing HFQ factor file; original preserved: {factor_path}")
        raw_existing["trade_date_dt"] = pd.to_datetime(raw_existing["trade_date"], errors="raise")
        raw_existing["hfq_factor"] = pd.to_numeric(raw_existing["hfq_factor"], errors="raise")
        if (raw_existing["trade_date_dt"].isna().any() or raw_existing["trade_date_dt"].duplicated().any()
                or not raw_existing["hfq_factor"].map(lambda value: isfinite(value) and value > 0).all()):
            raise ValueError(f"Invalid existing HFQ factor observations; original preserved: {factor_path}")
        existing_df = raw_existing.sort_values("trade_date_dt").reset_index(drop=True)

    events: dict[str, list[dict]] = {}
    for kind, date_column, value_column in (
        ("dividends", "ex_date", "dividend_per_share"),
        ("splits", "split_date", "split_ratio"),
    ):
        events[kind] = []
        path = root / f"platform_{kind}.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path, dtype={"code": str})
        if not {"code", date_column, value_column}.issubset(frame.columns):
            raise ValueError(f"Invalid corporate-action columns; original HFQ factor preserved: {path}")
        frame = frame[frame["code"].str.zfill(6) == str(code).zfill(6)]
        dates = pd.to_datetime(frame[date_column], errors="raise")
        values = pd.to_numeric(frame[value_column], errors="raise")
        if (dates.isna().any() or dates.duplicated().any() or not values.map(isfinite).all()
                or (values < 0).any() or (kind == "splits" and (values == 0).any())):
            raise ValueError(f"Invalid or duplicate corporate actions; original HFQ factor preserved: {path}")
        events[kind] = pd.DataFrame({"event_date": dates, "value": values}).sort_values("event_date").to_dict("records")

    # 历史因子原样保留；首次生成与增量扩展共用事件计算。
    if existing_df is not None:
        last_factor_date = existing_df["trade_date_dt"].max()
        if last_factor_date >= market_max_date:
            return f"{code}: existing provider/research HFQ factor preserved"
        last_factor_val = float(
            existing_df.loc[existing_df["trade_date_dt"] == last_factor_date, "hfq_factor"].iloc[-1]
        )
        segment = market[market["trade_date"] > last_factor_date].reset_index(drop=True)
        event_start = last_factor_date
    else:
        segment = market
        last_factor_val = 1.0
        event_start = market.iloc[0]["trade_date"]

    factor = pd.Series(last_factor_val, index=segment.index, dtype=float)
    applied = 0
    for div in events["dividends"]:
        # 既有因子截止日的分红已入账；拆分则在基准日之后生效。
        due = div["event_date"] > event_start if existing_df is not None else div["event_date"] >= event_start
        if due and div["value"] > 0:
            eligible = segment.index[segment["trade_date"] >= div["event_date"]]
            if not eligible.empty:
                event_idx = eligible[0]
                ex_close = float(segment.at[event_idx, "close"])
                if ex_close > 0:
                    factor.loc[event_idx:] *= (ex_close + div["value"]) / ex_close
                    applied += 1

    for spl in events["splits"]:
        if spl["event_date"] >= event_start:
            eligible = segment.index[segment["trade_date"] > spl["event_date"]]
            if not eligible.empty:
                event_idx = eligible[0]
                factor.loc[event_idx:] *= spl["value"]
                applied += 1

    if existing_df is None and applied == 0:
        return f"{code}: no applicable local corporate actions; HFQ factor skipped"

    output = pd.DataFrame(
        {
            "trade_date": segment["trade_date"].dt.strftime("%Y-%m-%d"),
            "hfq_factor": factor,
            "source": GENERATED_FACTOR_SOURCE,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    if existing_df is not None:
        existing_df["trade_date"] = existing_df["trade_date_dt"].dt.strftime("%Y-%m-%d")
        if "source" not in existing_df.columns:
            existing_df["source"] = LEGACY_FACTOR_SOURCE
        else:
            existing_df["source"] = existing_df["source"].fillna(LEGACY_FACTOR_SOURCE)
        if "updated_at" not in existing_df.columns:
            existing_df["updated_at"] = ""
        output = pd.concat([existing_df[list(output.columns)], output], ignore_index=True)
    changed = write_csv_stable(factor_path, output, key_column="trade_date")
    if existing_df is not None:
        action = "extended" if changed else "unchanged"
        return (
            f"{code}: {action} HFQ factor from {last_factor_date.strftime('%Y-%m-%d')} "
            f"to {market_max_date.strftime('%Y-%m-%d')} ({applied} new events)"
        )
    return f"{code}: corporate-action HFQ factor {'updated' if changed else 'unchanged'} ({applied} events)"
