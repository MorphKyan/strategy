from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.platform_core.data_store import write_csv_stable


GENERATED_FACTOR_SOURCE = "corporate_actions"


def sync_corporate_action_hfq_factor(code: str, data_dir: str | Path) -> str:
    """Create/update an HFQ sidecar from the local dividend and split ledgers.

    Existing provider/research sidecars (without our source marker) are preserved.
    The factor is normalized to 1.0 at the first local bar, which is sufficient for
    continuous total-return signals even when earlier corporate actions exist.
    """
    root = Path(data_dir)
    market_path = root / f"{code}.csv"
    factor_path = root / f"{code}_hfq_factor.csv"
    if not market_path.exists():
        return f"{code}: market data missing; HFQ factor skipped"

    if factor_path.exists():
        existing_factor = pd.read_csv(factor_path)
        sources = set(existing_factor.get("source", pd.Series(dtype=str)).dropna().astype(str))
        if sources != {GENERATED_FACTOR_SOURCE}:
            return f"{code}: existing provider/research HFQ factor preserved"

    market = pd.read_csv(market_path, usecols=["trade_date", "close"])
    market["trade_date"] = pd.to_datetime(market["trade_date"], errors="coerce")
    market["close"] = pd.to_numeric(market["close"], errors="coerce")
    market = (
        market.dropna()
        .drop_duplicates("trade_date", keep="last")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    if market.empty:
        return f"{code}: no valid market rows; HFQ factor skipped"

    factor = pd.Series(1.0, index=market.index, dtype=float)
    applied = 0

    dividend_path = root / "platform_dividends.csv"
    if dividend_path.exists():
        dividends = pd.read_csv(dividend_path, dtype={"code": str})
        dividends = dividends[dividends["code"].astype(str).str.zfill(6) == str(code).zfill(6)].copy()
        dividends["event_date"] = pd.to_datetime(dividends["ex_date"], errors="coerce")
        dividends["amount"] = pd.to_numeric(dividends["dividend_per_share"], errors="coerce")
        for row in dividends.dropna(subset=["event_date", "amount"]).sort_values("event_date").itertuples():
            if row.amount <= 0 or row.event_date < market.iloc[0]["trade_date"]:
                continue
            eligible = market.index[market["trade_date"] >= row.event_date]
            if eligible.empty:
                continue
            event_index = eligible[0]
            ex_close = float(market.at[event_index, "close"])
            if ex_close <= 0:
                continue
            factor.loc[event_index:] *= (ex_close + float(row.amount)) / ex_close
            applied += 1

    split_path = root / "platform_splits.csv"
    if split_path.exists():
        splits = pd.read_csv(split_path, dtype={"code": str})
        splits = splits[splits["code"].astype(str).str.zfill(6) == str(code).zfill(6)].copy()
        splits["event_date"] = pd.to_datetime(splits["split_date"], errors="coerce")
        splits["ratio"] = pd.to_numeric(splits["split_ratio"], errors="coerce")
        for row in splits.dropna(subset=["event_date", "ratio"]).sort_values("event_date").itertuples():
            if row.ratio <= 0 or row.event_date < market.iloc[0]["trade_date"]:
                continue
            eligible = market.index[market["trade_date"] > row.event_date]
            if eligible.empty:
                continue
            event_index = eligible[0]
            factor.loc[event_index:] *= float(row.ratio)
            applied += 1

    if applied == 0:
        return f"{code}: no applicable local corporate actions; HFQ factor skipped"

    output = pd.DataFrame(
        {
            "trade_date": market["trade_date"].dt.strftime("%Y-%m-%d"),
            "hfq_factor": factor,
            "source": GENERATED_FACTOR_SOURCE,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    changed = write_csv_stable(factor_path, output, key_column="trade_date")
    return f"{code}: corporate-action HFQ factor {'updated' if changed else 'unchanged'} ({applied} events)"
