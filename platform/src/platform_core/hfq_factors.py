from __future__ import annotations

from datetime import datetime
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
        try:
            raw_existing = pd.read_csv(factor_path)
            if "trade_date" in raw_existing.columns and "hfq_factor" in raw_existing.columns:
                raw_existing["trade_date_dt"] = pd.to_datetime(raw_existing["trade_date"], errors="coerce")
                raw_existing = (
                    raw_existing.dropna(subset=["trade_date_dt"])
                    .drop_duplicates("trade_date_dt", keep="last")
                    .sort_values("trade_date_dt")
                    .reset_index(drop=True)
                )
                if not raw_existing.empty:
                    existing_df = raw_existing
        except Exception:
            existing_df = None

    dividend_records: list[dict] = []
    dividend_path = root / "platform_dividends.csv"
    if dividend_path.exists():
        dividends = pd.read_csv(dividend_path, dtype={"code": str})
        dividends = dividends[dividends["code"].astype(str).str.zfill(6) == str(code).zfill(6)].copy()
        dividends["event_date"] = pd.to_datetime(dividends["ex_date"], errors="coerce")
        dividends["amount"] = pd.to_numeric(dividends["dividend_per_share"], errors="coerce")
        for row in dividends.dropna(subset=["event_date", "amount"]).sort_values("event_date").itertuples():
            if row.amount > 0:
                dividend_records.append({"event_date": row.event_date, "amount": float(row.amount)})

    split_records: list[dict] = []
    split_path = root / "platform_splits.csv"
    if split_path.exists():
        splits = pd.read_csv(split_path, dtype={"code": str})
        splits = splits[splits["code"].astype(str).str.zfill(6) == str(code).zfill(6)].copy()
        splits["event_date"] = pd.to_datetime(splits["split_date"], errors="coerce")
        splits["ratio"] = pd.to_numeric(splits["split_ratio"], errors="coerce")
        for row in splits.dropna(subset=["event_date", "ratio"]).sort_values("event_date").itertuples():
            if row.ratio > 0:
                split_records.append({"event_date": row.event_date, "ratio": float(row.ratio)})

    stamp = datetime.now().isoformat(timespec="seconds")

    # Scenario A: An existing factor file exists
    if existing_df is not None:
        last_factor_date = existing_df["trade_date_dt"].max()
        # If the existing factor already covers all available market dates, leave untouched
        if last_factor_date >= market_max_date:
            return f"{code}: existing provider/research HFQ factor preserved"

        # Market has newer dates: seamlessly append extension segment
        last_factor_val = float(
            existing_df.loc[existing_df["trade_date_dt"] == last_factor_date, "hfq_factor"].iloc[-1]
        )
        new_market = market[market["trade_date"] > last_factor_date].copy().reset_index(drop=True)
        new_factors = pd.Series(last_factor_val, index=new_market.index, dtype=float)
        applied_new = 0

        # Apply new dividends occurring after last_factor_date
        for div in dividend_records:
            if div["event_date"] > last_factor_date:
                eligible = new_market.index[new_market["trade_date"] >= div["event_date"]]
                if not eligible.empty:
                    event_idx = eligible[0]
                    ex_close = float(new_market.at[event_idx, "close"])
                    if ex_close > 0:
                        new_factors.loc[event_idx:] *= (ex_close + div["amount"]) / ex_close
                        applied_new += 1

        # Apply new splits taking effect after last_factor_date
        for spl in split_records:
            if spl["event_date"] >= last_factor_date:
                eligible = new_market.index[new_market["trade_date"] > spl["event_date"]]
                if not eligible.empty:
                    event_idx = eligible[0]
                    new_factors.loc[event_idx:] *= spl["ratio"]
                    applied_new += 1

        # Format historical segment
        existing_df["trade_date"] = existing_df["trade_date_dt"].dt.strftime("%Y-%m-%d")
        existing_df["hfq_factor"] = pd.to_numeric(existing_df["hfq_factor"], errors="coerce")
        if "source" not in existing_df.columns:
            existing_df["source"] = LEGACY_FACTOR_SOURCE
        else:
            existing_df["source"] = existing_df["source"].fillna(LEGACY_FACTOR_SOURCE)
        if "updated_at" not in existing_df.columns:
            existing_df["updated_at"] = ""
        existing_part = existing_df[["trade_date", "hfq_factor", "source", "updated_at"]]

        # Format new extension segment
        new_part = pd.DataFrame(
            {
                "trade_date": new_market["trade_date"].dt.strftime("%Y-%m-%d"),
                "hfq_factor": new_factors,
                "source": GENERATED_FACTOR_SOURCE,
                "updated_at": stamp,
            }
        )

        merged_output = pd.concat([existing_part, new_part], ignore_index=True)
        changed = write_csv_stable(factor_path, merged_output, key_column="trade_date")
        action = "extended" if changed else "unchanged"
        return (
            f"{code}: {action} HFQ factor from {last_factor_date.strftime('%Y-%m-%d')} "
            f"to {market_max_date.strftime('%Y-%m-%d')} ({applied_new} new events)"
        )

    # Scenario B: No existing factor file exists -> generate from scratch
    factor = pd.Series(1.0, index=market.index, dtype=float)
    applied = 0
    start_market_date = market.iloc[0]["trade_date"]

    for div in dividend_records:
        if div["event_date"] >= start_market_date:
            eligible = market.index[market["trade_date"] >= div["event_date"]]
            if not eligible.empty:
                event_idx = eligible[0]
                ex_close = float(market.at[event_idx, "close"])
                if ex_close > 0:
                    factor.loc[event_idx:] *= (ex_close + div["amount"]) / ex_close
                    applied += 1

    for spl in split_records:
        if spl["event_date"] >= start_market_date:
            eligible = market.index[market["trade_date"] > spl["event_date"]]
            if not eligible.empty:
                event_idx = eligible[0]
                factor.loc[event_idx:] *= spl["ratio"]
                applied += 1

    if applied == 0:
        return f"{code}: no applicable local corporate actions; HFQ factor skipped"

    output = pd.DataFrame(
        {
            "trade_date": market["trade_date"].dt.strftime("%Y-%m-%d"),
            "hfq_factor": factor,
            "source": GENERATED_FACTOR_SOURCE,
            "updated_at": stamp,
        }
    )
    changed = write_csv_stable(factor_path, output, key_column="trade_date")
    return f"{code}: corporate-action HFQ factor {'updated' if changed else 'unchanged'} ({applied} events)"
