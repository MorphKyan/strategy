"""按真实可用日期构造基本面信号；缺输入或同步失败时停止，不填造数值。

CPI 输入：available_date,cpi_yoy_pct，可附 observation_date。
指数股息率输入：symbol,available_date,dividend_yield_pct。
期货到期日输入：contract,expiry_date；不再假设每月 15 日到期。
债券输入沿用 china_bond_yields_daily_pit.csv；没有 available_date 时保守滞后一条报价。
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import assets_from_config, write_csv_stable

BOND_COLUMNS = {"CBA21801": "bond_ytm_30y", "511090": "bond_ytm_30y", "511260": "bond_ytm_10y"}
INDEX_CODES = {"000300", "000015", "930955"}
ETF_CODES = {"510300", "512890", "510880"}
FUTURES_PREFIXES = {"M0": "M", "159985": "M", "TA0": "TA", "159981": "TA"}
SUPPORTED_SYMBOLS = sorted(set(BOND_COLUMNS) | INDEX_CODES | ETF_CODES | set(FUTURES_PREFIXES) | {"518880"})


def observable_series(index_dates: pd.DatetimeIndex, releases: pd.DataFrame, value_column: str) -> pd.Series:
    """只前填已披露观测；首次披露前保留缺失值，不用零代替。"""
    required = {"available_date", value_column}
    if not required.issubset(releases.columns):
        raise ValueError(f"Release data requires columns: {sorted(required)}")
    available = pd.to_datetime(releases["available_date"], errors="raise")
    values = pd.to_numeric(releases[value_column], errors="raise")
    if available.isna().any() or available.duplicated().any() or not np.isfinite(values).all():
        raise ValueError(f"Invalid release dates or values: {value_column}")
    if "observation_date" in releases:
        observed = pd.to_datetime(releases["observation_date"], errors="raise")
        if observed.isna().any() or (available < observed).any():
            raise ValueError("Release date cannot precede the observation date.")
    series = pd.Series(values.to_numpy(dtype=float), index=available).sort_index()
    return series.reindex(pd.DatetimeIndex(index_dates), method="ffill")


def compute_etf_dividend_yield_series(symbol: str, price_series: pd.Series, div_df: pd.DataFrame,
                                      splits: pd.DataFrame | None = None) -> pd.Series:
    if symbol in INDEX_CODES:
        raise ValueError("Index points cannot be paired with ETF per-share cash distributions.")
    events = div_df[div_df["code"].astype(str) == symbol].copy()
    events["ex_date"] = pd.to_datetime(events["ex_date"], errors="raise")
    events["dividend_per_share"] = pd.to_numeric(events["dividend_per_share"], errors="raise")
    if (events["ex_date"].isna().any() or events["ex_date"].duplicated().any()
            or not np.isfinite(events["dividend_per_share"]).all() or (events["dividend_per_share"] < 0).any()):
        raise ValueError(f"Invalid dividend history: {symbol}")
    effective_splits = []
    if splits is not None:
        selected = splits[splits["code"].astype(str) == symbol].copy()
        selected["split_date"] = pd.to_datetime(selected["split_date"], errors="raise")
        selected["split_ratio"] = pd.to_numeric(selected["split_ratio"], errors="raise")
        if (selected["split_date"].isna().any() or selected["split_date"].duplicated().any()
                or not np.isfinite(selected["split_ratio"]).all() or (selected["split_ratio"] <= 0).any()):
            raise ValueError(f"Invalid split history: {symbol}")
        for row in selected.itertuples():
            position = price_series.index.searchsorted(row.split_date, side="right")
            if position < len(price_series):
                effective_splits.append((price_series.index[position], row.split_ratio))
    values = []
    for day, price in price_series.items():
        total = 0.
        trailing = events[(events["ex_date"] > day - pd.Timedelta(days=365)) & (events["ex_date"] <= day)]
        for event in trailing.itertuples():
            ratio = np.prod([ratio for effective, ratio in effective_splits if event.ex_date < effective <= day])
            total += event.dividend_per_share / ratio
        values.append(total / price)
    return pd.Series(values, index=price_series.index)


def compute_real_futures_roll_yield_series(var_prefix: str, calendar: pd.DatetimeIndex,
                                          contracts: pd.DataFrame, fetcher=None) -> pd.Series:
    selected = contracts[contracts["contract"].astype(str).str.fullmatch(var_prefix + r"\d+")].copy()
    selected["expiry_date"] = pd.to_datetime(selected["expiry_date"], errors="raise")
    if len(selected) < 2 or selected["contract"].duplicated().any() or selected["expiry_date"].isna().any():
        raise ValueError(f"At least two distinct contracts with actual expiries are required: {var_prefix}")
    if fetcher is None:
        import akshare as ak
        fetcher = ak.futures_zh_daily_sina
    histories = {}
    expiries = {}
    for contract in selected.itertuples():
        try:
            frame = fetcher(symbol=contract.contract)
            if frame is None or frame.empty:
                raise ValueError("empty contract history")
            frame = frame.copy()
            frame["date"] = pd.to_datetime(frame["date"], errors="raise")
            for column in ("settle", "hold"):
                frame[column] = pd.to_numeric(frame[column], errors="raise")
            if (frame["date"].isna().any() or frame["date"].duplicated().any()
                    or not np.isfinite(frame[["settle", "hold"]]).all().all()
                    or (frame["settle"] <= 0).any() or (frame["hold"] < 0).any()):
                raise ValueError("invalid contract observations")
            histories[contract.contract] = frame.set_index("date").sort_index()
            expiries[contract.contract] = contract.expiry_date
        except (OSError, ValueError, KeyError) as exc:
            raise RuntimeError(f"Contract history failed: {contract.contract}") from exc
    raw = {}
    for day in sorted(set().union(*(frame.index for frame in histories.values()))):
        active = [(float(frame.at[day, "hold"]), code, float(frame.at[day, "settle"]), expiries[code])
                  for code, frame in histories.items() if day in frame.index and expiries[code] >= day
                  and frame.at[day, "hold"] > 0]
        if len(active) < 2:
            continue
        front = min(active, key=lambda item: (-item[0], item[3], item[1]))
        later = [item for item in active if item[3] > front[3]]
        if later:
            deferred = min(later, key=lambda item: item[3])
            raw[day] = (front[2] - deferred[2]) / front[2] * 365 / (deferred[3] - front[3]).days
    values = pd.Series(raw, dtype=float).sort_index()
    calendar = pd.DatetimeIndex(calendar).sort_values()
    positions = calendar.searchsorted(values.index, side="right")
    keep = positions < len(calendar)
    result = pd.Series(values.to_numpy()[keep], index=calendar.take(positions[keep]))
    result = result.groupby(level=0).last()
    if result.empty:
        raise ValueError(f"No observable two-contract roll-yield history: {var_prefix}")
    return result


def generate_pit_views(data_dir: Path, symbols: list[str], cpi_releases: Path | None = None,
                       index_yields: Path | None = None, futures_contracts: Path | None = None) -> pd.DataFrame:
    symbols = list(dict.fromkeys(symbols))
    unknown = set(symbols) - set(SUPPORTED_SYMBOLS)
    if unknown or not symbols:
        raise ValueError(f"Unsupported or empty fundamental universe: {sorted(unknown)}")
    data_dir = Path(data_dir)
    macro = data_dir / "fundamental_macro"
    assets = assets_from_config([{"asset_id": code, "code": code,
                                 "asset_type": "index" if code in INDEX_CODES or code == "CBA21801" else
                                 "futures" if code in {"M0", "TA0"} else "etf"} for code in symbols])
    data = LocalCsvBarData(data_dir, assets)
    prices = {code: frame["close"].set_axis(pd.to_datetime(frame.index)) for code, frame in data.frames.items()}
    views = {}
    if set(symbols) & (set(BOND_COLUMNS) | {"518880"}):
        rates = pd.read_csv(macro / "china_bond_yields_daily_pit.csv")
        rates["date"] = pd.to_datetime(rates["date"], errors="raise")
        rates = rates.sort_values("date").reset_index(drop=True)
        if rates["date"].isna().any() or rates["date"].duplicated().any():
            raise ValueError("Invalid bond quote dates.")
        if (pd.Timestamp(max(data.calendar)) - rates["date"].max()).days > 7:
            raise ValueError("Bond yields are stale relative to the required market snapshot.")
        rates = rates.rename(columns={"date": "observation_date"})
        if "available_date" not in rates:
            rates["available_date"] = rates["observation_date"].shift(-1)
            rates = rates.iloc[:-1].copy()
        for code in set(symbols) & set(BOND_COLUMNS):
            views[code] = ("bond_ytm", observable_series(prices[code].index, rates, BOND_COLUMNS[code]) / 100)
        if "518880" in symbols:
            cpi = pd.read_csv(cpi_releases or macro / "china_cpi_releases.csv")
            days = prices["518880"].index
            views["518880"] = ("real_yield", observable_series(days, rates, "bond_ytm_10y") / 100
                               - observable_series(days, cpi, "cpi_yoy_pct") / 100)
    if set(symbols) & INDEX_CODES:
        releases = pd.read_csv(index_yields or macro / "index_dividend_yield_releases.csv", dtype={"symbol": str})
        for code in set(symbols) & INDEX_CODES:
            selected = releases[releases["symbol"] == code]
            views[code] = ("dividend_yield", observable_series(prices[code].index, selected, "dividend_yield_pct") / 100)
    if set(symbols) & ETF_CODES:
        dividends = pd.read_csv(data_dir / "platform_dividends.csv", dtype={"code": str})
        split_path = data_dir / "platform_splits.csv"
        splits = pd.read_csv(split_path, dtype={"code": str}) if split_path.exists() else None
        for code in set(symbols) & ETF_CODES:
            views[code] = ("dividend_yield", compute_etf_dividend_yield_series(code, prices[code], dividends, splits))
    selected_futures = set(symbols) & set(FUTURES_PREFIXES)
    if selected_futures:
        contracts = pd.read_csv(futures_contracts or macro / "futures_contract_expiries.csv", dtype={"contract": str})
        for prefix in {FUTURES_PREFIXES[code] for code in selected_futures}:
            codes = [code for code in selected_futures if FUTURES_PREFIXES[code] == prefix]
            calendar = pd.DatetimeIndex(sorted(set().union(*(prices[code].index for code in codes))))
            series = compute_real_futures_roll_yield_series(prefix, calendar, contracts)
            for code in codes:
                views[code] = ("roll_yield", series.loc[series.index.isin(prices[code].index)])
    records = []
    for code in symbols:
        metric, series = views[code]
        series = series.dropna()
        if series.empty or not np.isfinite(series).all():
            raise ValueError(f"No finite observable fundamental history: {code}")
        records.extend({"trade_date": day.strftime("%Y-%m-%d"), "symbol": code, "metric": metric, "value": float(value)}
                       for day, value in series.items())
    return pd.DataFrame(records).sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--symbols", nargs="+", choices=SUPPORTED_SYMBOLS, default=SUPPORTED_SYMBOLS)
    parser.add_argument("--cpi-releases", type=Path)
    parser.add_argument("--index-yields", type=Path)
    parser.add_argument("--futures-contracts", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.data_dir / "fundamental_macro/pit_fundamental_views_daily.csv"
    generated = generate_pit_views(args.data_dir, args.symbols, args.cpi_releases, args.index_yields, args.futures_contracts)
    if output.exists():
        previous = pd.read_csv(output, dtype={"symbol": str})
        previous = previous[~previous["symbol"].isin(args.symbols)]
        generated = pd.concat([previous, generated], ignore_index=True).sort_values(["trade_date", "symbol"])
    output.parent.mkdir(parents=True, exist_ok=True)
    written = write_csv_stable(output, generated)
    print(f"PIT views: {output}; selected symbols={len(args.symbols)}; {'updated' if written else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
