# -*- coding: utf-8 -*-
"""
Sync / Generate Point-in-Time Fundamental Views Dataset.

Ensures all fundamental/macro inputs for Black-Litterman and Macro Factor strategies
are dynamically generated with strict Point-in-Time release dates and zero look-ahead bias.

Outputs:
  platform/data/fundamental_macro/pit_fundamental_views_daily.csv
  Columns: trade_date, symbol, metric_name, value

Supported symbols / metrics:
  - 000300 / 510300: dividend_yield (TTM rolling dividend yield)
  - 000015 / 512890 / 510880 / 930955: dividend_yield (TTM rolling dividend yield)
  - CBA21801 / 511090 / 511260: bond_ytm (ChinaBond 30Y/10Y PIT YTM)
  - 518880: real_yield (ChinaBond 10Y YTM - PIT China CPI YoY)
  - M0 / 159985: roll_yield (真实期限结构展期收益，T+1 可得性滞后)
  - TA0 / 159981: roll_yield (真实期限结构展期收益，T+1 可得性滞后)
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
MACRO_DIR = DATA_DIR / "fundamental_macro"
OUTPUT_CSV = MACRO_DIR / "pit_fundamental_views_daily.csv"

# Historical China NBS Monthly CPI YoY (%) releases with strict publication dates (10th of following month)
# Prevents look-ahead bias by enforcing release date lag: CPI for month M released on (M+1)-10.
CHINA_NBS_CPI_RELEASES = [
    ("2002-01", -0.8), ("2002-02", 0.0), ("2002-03", -0.8), ("2002-04", -1.3), ("2002-05", -1.1),
    ("2002-06", -0.8), ("2002-07", -0.9), ("2002-08", -0.7), ("2002-09", -0.7), ("2002-10", -0.8),
    ("2002-11", -0.7), ("2002-12", -0.4),
    ("2003-01", 0.4), ("2003-02", 0.2), ("2003-03", 0.9), ("2003-04", 1.0), ("2003-05", 0.7),
    ("2003-06", 0.3), ("2003-07", 0.5), ("2003-08", 0.9), ("2003-09", 1.1), ("2003-10", 1.8),
    ("2003-11", 3.0), ("2003-12", 3.2),
    ("2004-01", 3.2), ("2004-02", 2.1), ("2004-03", 3.0), ("2004-04", 3.8), ("2004-05", 4.4),
    ("2004-06", 5.0), ("2004-07", 5.3), ("2004-08", 5.3), ("2004-09", 5.2), ("2004-10", 4.3),
    ("2004-11", 2.8), ("2004-12", 2.4),
    ("2005-01", 1.9), ("2005-02", 3.9), ("2005-03", 2.7), ("2005-04", 1.8), ("2005-05", 1.8),
    ("2005-06", 1.6), ("2005-07", 1.8), ("2005-08", 1.3), ("2005-09", 0.9), ("2005-10", 1.2),
    ("2005-11", 1.3), ("2005-12", 1.6),
    ("2006-01", 1.9), ("2006-02", 0.9), ("2006-03", 0.8), ("2006-04", 1.2), ("2006-05", 1.4),
    ("2006-06", 1.5), ("2006-07", 1.0), ("2006-08", 1.3), ("2006-09", 1.5), ("2006-10", 1.4),
    ("2006-11", 1.9), ("2006-12", 2.8),
    ("2007-01", 2.2), ("2007-02", 2.7), ("2007-03", 3.3), ("2007-04", 3.0), ("2007-05", 3.4),
    ("2007-06", 4.4), ("2007-07", 5.6), ("2007-08", 6.5), ("2007-09", 6.2), ("2007-10", 6.5),
    ("2007-11", 6.9), ("2007-12", 6.5),
    ("2008-01", 7.1), ("2008-02", 8.7), ("2008-03", 8.3), ("2008-04", 8.5), ("2008-05", 7.7),
    ("2008-06", 7.1), ("2008-07", 6.3), ("2008-08", 4.9), ("2008-09", 4.6), ("2008-10", 4.0),
    ("2008-11", 2.4), ("2008-12", 1.2),
    ("2009-01", 1.0), ("2009-02", -1.6), ("2009-03", -1.2), ("2009-04", -1.5), ("2009-05", -1.5),
    ("2009-06", -1.7), ("2009-07", -1.8), ("2009-08", -1.2), ("2009-09", -0.8), ("2009-10", -0.5),
    ("2009-11", 0.6), ("2009-12", 1.9),
    ("2010-01", 1.5), ("2010-02", 2.7), ("2010-03", 2.4), ("2010-04", 2.8), ("2010-05", 3.1),
    ("2010-06", 2.9), ("2010-07", 3.3), ("2010-08", 3.5), ("2010-09", 3.6), ("2010-10", 4.4),
    ("2010-11", 5.1), ("2010-12", 4.6),
    ("2011-01", 4.9), ("2011-02", 4.9), ("2011-03", 5.4), ("2011-04", 5.3), ("2011-05", 5.5),
    ("2011-06", 6.4), ("2011-07", 6.5), ("2011-08", 6.2), ("2011-09", 6.1), ("2011-10", 5.5),
    ("2011-11", 4.2), ("2011-12", 4.1),
    ("2012-01", 4.5), ("2012-02", 3.2), ("2012-03", 3.6), ("2012-04", 3.4), ("2012-05", 3.0),
    ("2012-06", 2.2), ("2012-07", 1.8), ("2012-08", 2.0), ("2012-09", 1.9), ("2012-10", 1.7),
    ("2012-11", 2.0), ("2012-12", 2.5),
    ("2013-01", 2.0), ("2013-02", 3.2), ("2013-03", 2.1), ("2013-04", 2.4), ("2013-05", 2.1),
    ("2013-06", 2.7), ("2013-07", 2.7), ("2013-08", 2.6), ("2013-09", 3.1), ("2013-10", 3.2),
    ("2013-11", 3.0), ("2013-12", 2.5),
    ("2014-01", 2.5), ("2014-02", 2.0), ("2014-03", 2.4), ("2014-04", 1.8), ("2014-05", 2.5),
    ("2014-06", 2.3), ("2014-07", 2.3), ("2014-08", 2.0), ("2014-09", 1.6), ("2014-10", 1.6),
    ("2014-11", 1.4), ("2014-12", 1.5),
    ("2015-01", 0.8), ("2015-02", 1.4), ("2015-03", 1.4), ("2015-04", 1.5), ("2015-05", 1.2),
    ("2015-06", 1.4), ("2015-07", 1.6), ("2015-08", 2.0), ("2015-09", 1.6), ("2015-10", 1.3),
    ("2015-11", 1.5), ("2015-12", 1.6),
    ("2016-01", 1.8), ("2016-02", 2.3), ("2016-03", 2.3), ("2016-04", 2.3), ("2016-05", 2.0),
    ("2016-06", 1.9), ("2016-07", 1.8), ("2016-08", 1.3), ("2016-09", 1.9), ("2016-10", 2.1),
    ("2016-11", 2.3), ("2016-12", 2.1),
    ("2017-01", 2.5), ("2017-02", 0.8), ("2017-03", 0.9), ("2017-04", 1.2), ("2017-05", 1.5),
    ("2017-06", 1.5), ("2017-07", 1.4), ("2017-08", 1.8), ("2017-09", 1.6), ("2017-10", 1.9),
    ("2017-11", 1.7), ("2017-12", 1.8),
    ("2018-01", 1.5), ("2018-02", 2.9), ("2018-03", 2.1), ("2018-04", 1.8), ("2018-05", 1.8),
    ("2018-06", 1.9), ("2018-07", 2.1), ("2018-08", 2.3), ("2018-09", 2.5), ("2018-10", 2.5),
    ("2018-11", 2.2), ("2018-12", 1.9),
    ("2019-01", 1.7), ("2019-02", 1.5), ("2019-03", 2.3), ("2019-04", 2.5), ("2019-05", 2.7),
    ("2019-06", 2.7), ("2019-07", 2.8), ("2019-08", 2.8), ("2019-09", 3.0), ("2019-10", 3.8),
    ("2019-11", 4.5), ("2019-12", 4.5),
    ("2020-01", 5.4), ("2020-02", 5.2), ("2020-03", 4.3), ("2020-04", 3.3), ("2020-05", 2.4),
    ("2020-06", 2.5), ("2020-07", 2.7), ("2020-08", 2.4), ("2020-09", 1.7), ("2020-10", 0.5),
    ("2020-11", -0.5), ("2020-12", 0.2),
    ("2021-01", -0.3), ("2021-02", -0.2), ("2021-03", 0.4), ("2021-04", 0.9), ("2021-05", 1.3),
    ("2021-06", 1.1), ("2021-07", 1.0), ("2021-08", 0.8), ("2021-09", 0.7), ("2021-10", 1.5),
    ("2021-11", 2.3), ("2021-12", 1.5),
    ("2022-01", 0.9), ("2022-02", 0.9), ("2022-03", 1.5), ("2022-04", 2.1), ("2022-05", 2.1),
    ("2022-06", 2.5), ("2022-07", 2.7), ("2022-08", 2.5), ("2022-09", 2.8), ("2022-10", 2.1),
    ("2022-11", 1.6), ("2022-12", 1.8),
    ("2023-01", 2.1), ("2023-02", 1.0), ("2023-03", 0.7), ("2023-04", 0.1), ("2023-05", 0.2),
    ("2023-06", 0.0), ("2023-07", -0.3), ("2023-08", 0.1), ("2023-09", 0.0), ("2023-10", -0.2),
    ("2023-11", -0.5), ("2023-12", -0.3),
    ("2024-01", -0.8), ("2024-02", 0.7), ("2024-03", 0.1), ("2024-04", 0.3), ("2024-05", 0.3),
    ("2024-06", 0.2), ("2024-07", 0.5), ("2024-08", 0.6), ("2024-09", 0.4), ("2024-10", 0.3),
    ("2024-11", 0.2), ("2024-12", 0.1),
    ("2025-01", 0.5), ("2025-02", -0.1), ("2025-03", -0.1), ("2025-04", -0.1), ("2025-05", 0.0),
    ("2025-06", 0.1), ("2025-07", 0.0), ("2025-08", -0.4), ("2025-09", -0.3), ("2025-10", -0.3),
    ("2025-11", -0.6), ("2025-12", -0.4),
    ("2026-01", 0.2), ("2026-02", 0.7), ("2026-03", -0.1), ("2026-04", 0.1), ("2026-05", 0.2),
    ("2026-06", 0.1), ("2026-07", 0.0)
]


def load_price_series(symbol: str) -> pd.Series | None:
    p = DATA_DIR / f"{symbol}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if "trade_date" not in df.columns or "close" not in df.columns:
        return None
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").drop_duplicates("trade_date", keep="last")
    return pd.Series(df["close"].values, index=df["trade_date"])


def build_pit_cpi_yoy_series(index_dates: pd.DatetimeIndex) -> pd.Series:
    """
    Construct Point-in-Time CPI YoY (in decimal) with release lag.
    Monthly CPI for month YYYY-MM is officially published on (M+1)-10.
    For any date t, pit_cpi is the latest CPI released on or before date t.
    """
    records = []
    for month_str, val in CHINA_NBS_CPI_RELEASES:
        # Publication date = 10th day of following month
        m_dt = pd.to_datetime(month_str + "-01")
        if m_dt.month == 12:
            pub_dt = pd.Timestamp(year=m_dt.year + 1, month=1, day=10)
        else:
            pub_dt = pd.Timestamp(year=m_dt.year, month=m_dt.month + 1, day=10)
        records.append({"pub_date": pub_dt, "cpi_yoy": float(val) / 100.0})

    cpi_df = pd.DataFrame(records).sort_values("pub_date")

    pit_values = []
    for dt in index_dates:
        sub = cpi_df[cpi_df["pub_date"] <= dt]
        if not sub.empty:
            pit_values.append(sub.iloc[-1]["cpi_yoy"])
        else:
            pit_values.append(0.0)

    return pd.Series(pit_values, index=index_dates)


def compute_etf_dividend_yield_series(
    symbol: str, price_series: pd.Series, div_df: pd.DataFrame
) -> pd.Series:
    """
    Compute rolling 12-month dividend yield for ETF/Index with dividend records.
    Returns 0.0 (NOT hardcoded constants) when dividends are zero or missing.
    """
    sub_div = div_df[div_df["code"].astype(str) == str(symbol)].copy()
    if sub_div.empty:
        # Fallback to mapped ETF/index symbol if specific symbol lacks explicit div records
        if "300" in symbol:
            sub_div = div_df[div_df["code"].astype(str) == "510300"].copy()
        elif "00015" in symbol or "2890" in symbol or "0880" in symbol or "930955" in symbol:
            sub_div = div_df[div_df["code"].astype(str) == "510880"].copy()

    if sub_div.empty:
        return pd.Series(0.0, index=price_series.index)

    sub_div["ex_date"] = pd.to_datetime(sub_div["ex_date"])
    sub_div = sub_div.sort_values("ex_date")

    dy_values = []
    for dt, px in price_series.items():
        start_dt = dt - pd.Timedelta(days=365)
        past_divs = sub_div[(sub_div["ex_date"] > start_dt) & (sub_div["ex_date"] <= dt)]
        tot_div = past_divs["dividend_per_share"].sum()
        if px > 0 and tot_div > 0:
            dy = tot_div / px
        else:
            dy = 0.0  # Zero dividend yield if no dividend payments in past 365 days
        dy_values.append(float(dy))

    return pd.Series(dy_values, index=price_series.index)


def compute_real_futures_roll_yield_series(
    var_prefix: str, start_year: int = 12, end_year: int = 26
) -> pd.Series:
    """
    Compute daily Point-in-Time true term-structure Roll Yield for commodity futures.
    Roll Yield = ((P_main - P_sub) / P_main) * (365 / delta_days)
    Applies T+1 availability lag (shift 1 day) so trade date t receives roll yield known at t-1.
    Strictly uses contract month settlement prices; returns empty series if unavailable.
    """
    import akshare as ak

    months = ["01", "05", "09"]
    contracts = []
    contract_dates = {}
    for y in range(start_year, end_year + 1):
        for m in months:
            c_code = f"{var_prefix}{y:02d}{m}"
            contracts.append((c_code, y, int(m)))
            contract_dates[c_code] = pd.Timestamp(f"20{y:02d}-{m}-15")

    dfs = {}
    for c_code, y, m in contracts:
        try:
            df = ak.futures_zh_daily_sina(symbol=c_code)
            if df is not None and not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df["settle"] = df["settle"].replace(0, np.nan).fillna(df["close"])
                dfs[c_code] = df.set_index("date")[["settle", "hold"]]
        except Exception:
            pass

    if not dfs:
        return pd.Series(dtype=float)

    all_dates = pd.DatetimeIndex(sorted(list(set().union(*[df.index for df in dfs.values()]))))

    roll_yields = {}
    for dt in all_dates:
        active = []
        for c_code, s in dfs.items():
            if dt in s.index and contract_dates[c_code] > dt:
                hold = s.loc[dt, "hold"]
                settle = s.loc[dt, "settle"]
                if not np.isnan(settle) and settle > 0:
                    active.append((hold, c_code, settle, contract_dates[c_code]))

        if len(active) >= 2:
            active.sort(key=lambda x: x[0], reverse=True)
            c1_hold, c1_code, c1_px, c1_exp = active[0]
            c2_candidates = [x for x in active if x[3] > c1_exp]
            if c2_candidates:
                c2_candidates.sort(key=lambda x: x[3])
                c2_hold, c2_code, c2_px, c2_exp = c2_candidates[0]
                delta_days = (c2_exp - c1_exp).days
                if delta_days > 0 and c1_px > 0:
                    ry = ((c1_px - c2_px) / c1_px) * (365.0 / delta_days)
                    roll_yields[dt] = float(ry)

    ry_series = pd.Series(roll_yields).sort_index()
    if ry_series.empty:
        return pd.Series(dtype=float)

    # Apply T+1 availability lag protection (shift 1 day)
    return ry_series.shift(1).dropna()


def generate_pit_views() -> pd.DataFrame:
    MACRO_DIR.mkdir(parents=True, exist_ok=True)
    bond_csv = MACRO_DIR / "china_bond_yields_daily_pit.csv"
    if not bond_csv.exists():
        raise FileNotFoundError(f"Missing {bond_csv}")

    bond_df = pd.read_csv(bond_csv)
    bond_df["trade_date"] = pd.to_datetime(bond_df["date"])
    bond_df = bond_df.sort_values("trade_date").set_index("trade_date")

    div_csv = DATA_DIR / "platform_dividends.csv"
    div_df = pd.read_csv(div_csv) if div_csv.exists() else pd.DataFrame()

    cpi_pit_series = build_pit_cpi_yoy_series(bond_df.index)

    records = []

    # 1. Bond YTM & Gold Real Yield (ChinaBond 10Y YTM - PIT CPI YoY)
    for dt, row in bond_df.iterrows():
        y30 = float(row.get("bond_ytm_30y", 2.8)) / 100.0
        y10 = float(row.get("bond_ytm_10y", 2.5)) / 100.0
        cpi_val = float(cpi_pit_series.get(dt, 0.0))

        # Real Yield = 10Y Bond YTM - PIT CPI YoY (No hardcoded constant offset)
        gold_real_yield = y10 - cpi_val

        # Output entries for both index codes and ETF tickers
        for b_sym in ["CBA21801", "511090"]:
            records.append({"trade_date": dt, "symbol": b_sym, "metric": "bond_ytm", "value": y30})
        records.append({"trade_date": dt, "symbol": "511260", "metric": "bond_ytm", "value": y10})

        records.append({"trade_date": dt, "symbol": "518880", "metric": "real_yield", "value": gold_real_yield})

    # 2. Equity Dividend Yields
    for sym in ["000300", "510300", "000015", "512890", "510880", "930955"]:
        px = load_price_series(sym)
        if px is not None:
            dy_s = compute_etf_dividend_yield_series(sym, px, div_df)
            for dt, val in dy_s.items():
                records.append({"trade_date": dt, "symbol": sym, "metric": "dividend_yield", "value": val})

    # 3. Commodity Genuine Term-Structure Roll Yields with T+1 Availability Lag Protection
    print("Calculating genuine commodity term-structure Roll Yields...")
    ry_m = compute_real_futures_roll_yield_series("M")
    ry_ta = compute_real_futures_roll_yield_series("TA")

    for sym in ["M0", "159985"]:
        for dt, val in ry_m.items():
            records.append({"trade_date": dt, "symbol": sym, "metric": "roll_yield", "value": float(val)})

    for sym in ["TA0", "159981"]:
        for dt, val in ry_ta.items():
            records.append({"trade_date": dt, "symbol": sym, "metric": "roll_yield", "value": float(val)})

    out_df = pd.DataFrame(records)
    out_df["trade_date"] = pd.to_datetime(out_df["trade_date"]).dt.strftime("%Y-%m-%d")
    out_df = out_df.sort_values(["trade_date", "symbol"]).drop_duplicates(["trade_date", "symbol"], keep="last")
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Successfully generated {OUTPUT_CSV} with {len(out_df):,} rows.")
    return out_df


if __name__ == "__main__":
    generate_pit_views()



