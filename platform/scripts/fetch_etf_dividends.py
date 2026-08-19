# -*- coding: utf-8 -*-
import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.platform_core.sync_universe import (
    discover_fixed_configs,
    etf_assets,
    load_assets_from_configs,
    merge_assets,
    parse_asset_spec,
)


def parse_dividend(text: Any) -> float:
    if not isinstance(text, str) or not text:
        return 0.0
    match = re.search(r"(?:分红|派息|派现金|派)([\d.]+)元", text)
    if not match:
        match = re.search(r"([\d.]+)", text)
    if not match:
        return 0.0

    value = float(match.group(1))
    if "每百份" in text or "每100份" in text:
        return value / 100.0
    if "每十份" in text or "每10份" in text:
        return value / 10.0
    return value


def parse_split_ratio(text: Any) -> float:
    if not isinstance(text, str) or not text:
        return 1.0
    if ":" in text:
        parts = text.split(":")
        try:
            return float(parts[1]) / float(parts[0])
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(text)
    except ValueError:
        return 1.0


def dividend_text(row: pd.Series) -> Any:
    """Read the payout field across EastMoney's per-share/per-10-share schemas."""
    for column in ("每份分红", "每10份分红", "分红方案"):
        value = row.get(column, "")
        if pd.notna(value) and str(value).strip():
            return value
    return ""


def sync_etf_corporate_actions(
    assets: Iterable[dict[str, Any]],
    data_dir: str | Path,
    client: Any | None = None,
) -> None:
    """Fetch and merge dividend/split histories for every supplied ETF asset."""
    etfs = etf_assets(assets)
    if not etfs:
        print("No ETF assets supplied; nothing to fetch.")
        return
    if client is None:
        import akshare as client

    dividend_records: list[dict[str, Any]] = []
    split_records: list[dict[str, Any]] = []
    failures: list[str] = []
    print("Start fetching ETF dividend and split histories from EastMoney via AKShare...")

    for etf in etfs:
        code = str(etf["code"])
        name = str(etf.get("name") or code)
        print(f"Fetching {code} ({name})...")
        try:
            frame = client.fund_open_fund_info_em(symbol=code, indicator="分红送配详情")
            if frame.empty:
                print("  - No dividend events found")
            else:
                for _, row in frame.iterrows():
                    raw_dividend = dividend_text(row)
                    dividend_per_share = parse_dividend(raw_dividend)
                    if dividend_per_share <= 0:
                        print(f"  - Skipped dividend row without a positive payout: {raw_dividend!r}")
                        continue
                    dividend_records.append(
                        {
                            "code": code,
                            "name": name,
                            "year": row.get("年份", ""),
                            "record_date": row.get("权益登记日", ""),
                            "ex_date": row.get("除息日", ""),
                            "raw_text": raw_dividend,
                            "dividend_per_share": dividend_per_share,
                            "payment_date": row.get("分红发放日", ""),
                        }
                    )
                print(f"  - Found {len(frame)} dividend events")
        except Exception as exc:
            print(f"  - Error fetching dividends: {exc}")
            failures.append(f"{code} dividends: {exc}")

        try:
            frame = client.fund_open_fund_info_em(symbol=code, indicator="拆分详情")
            if frame.empty:
                print("  - No split events found")
            else:
                for _, row in frame.iterrows():
                    raw_split = row.get("拆分折算比例", "")
                    split_records.append(
                        {
                            "code": code,
                            "name": name,
                            "year": row.get("年份", ""),
                            "split_date": row.get("拆分折算日", ""),
                            "split_type": row.get("拆分类型", ""),
                            "raw_text": raw_split,
                            "split_ratio": parse_split_ratio(raw_split),
                        }
                    )
                print(f"  - Found {len(frame)} split events")
        except Exception as exc:
            print(f"  - Error fetching splits: {exc}")
            failures.append(f"{code} splits: {exc}")

    _merge_event_records(dividend_records, split_records, Path(data_dir))
    from src.platform_core.hfq_factors import sync_corporate_action_hfq_factor

    for etf in etfs:
        print(f"  [hfq] {sync_corporate_action_hfq_factor(str(etf['code']), data_dir)}")
    if failures:
        detail = "; ".join(failures)
        raise RuntimeError(f"ETF corporate-action sync completed with {len(failures)} failed requests: {detail}")


def _merge_event_records(
    dividend_records: list[dict[str, Any]],
    split_records: list[dict[str, Any]],
    data_dir: Path,
) -> None:
    from src.platform_core.corporate_actions import merge_event_table, validate_split_against_prices
    from src.platform_core.data_store import write_csv_stable

    data_dir.mkdir(parents=True, exist_ok=True)

    dividend_frame = pd.DataFrame(dividend_records)
    if not dividend_frame.empty:
        output_path = data_dir / "platform_dividends.csv"
        existing = pd.read_csv(output_path, dtype=str).fillna("") if output_path.exists() else None
        if existing is None:
            merged = dividend_frame.iloc[0:0].copy()
            notes: list[str] = []
            additions = dividend_frame.astype(str).fillna("").to_dict("records")
        else:
            merged, notes, additions = _merge_scoped_events(
                existing, dividend_frame, ["code", "ex_date"], merge_event_table
            )
        for note in notes:
            print(f"  [dividends] {note}")
        if additions:
            merged = pd.concat([merged, pd.DataFrame(additions)], ignore_index=True)
        merged = merged.sort_values(by=["code", "ex_date"], ascending=[True, False])
        changed = write_csv_stable(output_path, merged)
        print(
            f"\nDividends: +{len(additions)} new events; "
            f"file {'updated' if changed else 'unchanged'} ({output_path})"
        )

    split_frame = pd.DataFrame(split_records)
    if not split_frame.empty:
        output_path = data_dir / "platform_splits.csv"
        existing = pd.read_csv(output_path, dtype=str).fillna("") if output_path.exists() else None
        if existing is None:
            merged = split_frame.iloc[0:0].copy()
            notes = []
            additions = split_frame.astype(str).fillna("").to_dict("records")
        else:
            merged, notes, additions = _merge_scoped_events(
                existing, split_frame, ["code", "split_date"], merge_event_table
            )
        for note in notes:
            print(f"  [splits] {note}")
        accepted = []
        for row in additions:
            ok, verdict = validate_split_against_prices(
                row["code"], row["split_date"], float(row["split_ratio"]), data_dir
            )
            print(f"  [splits] {'接受' if ok else '拒绝'}: {verdict}")
            if ok:
                accepted.append(row)
        if accepted:
            merged = pd.concat([merged, pd.DataFrame(accepted)], ignore_index=True)
        merged = merged.sort_values(by=["code", "split_date"], ascending=[True, False])
        changed = write_csv_stable(output_path, merged)
        print(
            f"Splits: +{len(accepted)} accepted / {len(additions) - len(accepted)} rejected; "
            f"file {'updated' if changed else 'unchanged'} ({output_path})"
        )


def _merge_scoped_events(
    existing: pd.DataFrame,
    fetched: pd.DataFrame,
    key_columns: list[str],
    merge_event_table: Any,
) -> tuple[pd.DataFrame, list[str], list[dict[str, Any]]]:
    """Compare only fetched symbols while retaining every unrelated ledger row."""
    fetched_codes = set(fetched["code"].astype(str))
    existing_codes = existing["code"].astype(str)
    untouched = existing[~existing_codes.isin(fetched_codes)]
    scoped = existing[existing_codes.isin(fetched_codes)]
    if scoped.empty:
        merged_scoped = existing.iloc[0:0].copy()
        notes: list[str] = []
        additions = fetched.astype(str).fillna("").to_dict("records")
    else:
        merged_scoped, notes, additions = merge_event_table(scoped, fetched, key_columns)
    merged = pd.concat([untouched, merged_scoped], ignore_index=True)
    return merged, notes, additions


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for candidate in (Path.cwd() / path, ROOT / path, ROOT.parent / path):
        if candidate.exists():
            return candidate
    return ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch dividend and split histories for ETFs from configs or command-line codes."
    )
    parser.add_argument("--config", action="append", default=[], help="Platform YAML config; repeatable.")
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        help="Asset as CODE[.EXCHANGE][:TYPE][=NAME]; only resolved ETFs are queried. Repeatable.",
    )
    parser.add_argument("--data-dir", default="data", help="Local platform data directory.")
    args = parser.parse_args(argv)

    if args.config:
        configured = load_assets_from_configs([_resolve_path(value) for value in args.config])
    elif args.asset:
        configured = []
    else:
        paths = discover_fixed_configs(ROOT / "configs")
        configured = load_assets_from_configs(paths)
        print(f"No --config supplied; discovered ETFs from {len(paths)} fixed platform configs.")
    direct = [parse_asset_spec(value) for value in args.asset]
    assets = etf_assets(merge_assets(configured, direct))
    if not assets:
        parser.error("no ETF assets were resolved")
    sync_etf_corporate_actions(assets, data_dir=_resolve_path(args.data_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
