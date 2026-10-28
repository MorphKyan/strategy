"""Lagged annual-rate inputs for monthly momentum signals (not cash accrual)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RATE_SOURCES = ("treasury_3m", "shibor_1m")
DEFAULT_RATE_DIR = Path(__file__).resolve().parents[2] / "data" / "interest_rates"


def load_annual_rates(path: str | Path) -> pd.Series:
    """Read percentage quotes; reject ambiguous dates and invalid observations."""
    frame = pd.read_csv(path, usecols=["date", "annual_rate_pct"])
    dates = pd.to_datetime(frame["date"], errors="raise")
    values = pd.to_numeric(frame["annual_rate_pct"], errors="raise")
    if dates.isna().any() or dates.duplicated().any() or not np.isfinite(values).all() or frame.empty:
        raise ValueError(f"Invalid annual rate observations: {path}")
    return pd.Series(values.to_numpy(dtype=float) / 100, index=dates).sort_index()


class SignalInterestRate:
    """A fixed annual rate or strictly lagged local Shibor/treasury quotes."""

    def __init__(self, config: dict | None = None):
        config = {} if config is None else config
        if not isinstance(config, dict):
            raise ValueError("trend_filter_risk_free must be a mapping")
        self.source = config.get("source", "treasury_3m")
        self.rates = None
        self.annual_rate = None
        if self.source == "fixed":
            self.annual_rate = float(config.get("annual_rate", 0.02))
            if not np.isfinite(self.annual_rate) or self.annual_rate <= -1:
                raise ValueError("annual_rate must be finite and greater than -1")
        elif self.source in RATE_SOURCES:
            self.rates = load_annual_rates(config.get("path", DEFAULT_RATE_DIR / f"{self.source}.csv"))
        else:
            raise ValueError("risk-free source must be treasury_3m, shibor_1m or fixed")

    def deduction(self, begin, end) -> float:
        if self.rates is None:
            return float((1 + self.annual_rate) ** (1 / 12) - 1)
        begin, end = pd.Timestamp(begin), pd.Timestamp(end)
        visible = self.rates.loc[self.rates.index < begin]
        if visible.empty or (begin - visible.index[-1]).days > 14:
            raise ValueError(f"Missing lagged {self.source} rate before {begin.date()}")
        return float(visible.iloc[-1]) * (end - begin).days / 365


def monthly_fast_slow_signal(prices: pd.Series, decision, rate: SignalInterestRate, calendar=()):
    """12-month mean / last-month excess return; exclude unfinished months.

    A known next trading day in a new month confirms month-end. At a truncated
    calendar's final date, conservatively require the last weekday of the month.
    """
    decision = pd.Timestamp(decision)
    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index)
    prices = prices.loc[prices.index <= decision].dropna().sort_index()
    following = next((pd.Timestamp(d) for d in calendar if pd.Timestamp(d) > decision), None)
    complete = (following.to_period("M") != decision.to_period("M")) if following is not None else (
        decision.normalize() >= (decision + pd.offsets.BMonthEnd(0)).normalize()
    )
    last_month = decision.to_period("M") if complete else decision.to_period("M") - 1
    prices = prices.loc[prices.index.to_period("M") <= last_month]
    monthly = prices.groupby(prices.index.to_period("M")).last()
    if len(monthly) < 13:
        return None
    monthly = monthly.iloc[-13:]
    if not monthly.index.equals(pd.period_range(monthly.index[0], periods=13, freq="M")):
        raise ValueError("Fast/slow signal requires 13 consecutive monthly prices")
    endpoints = pd.Series(prices.index, index=prices.index).groupby(prices.index.to_period("M")).last()
    excess = monthly.pct_change().iloc[1:].copy()
    for month in excess.index:
        excess.loc[month] -= rate.deduction(endpoints.loc[month - 1], endpoints.loc[month])
    slow, fast = float(excess.mean()), float(excess.iloc[-1])
    state = ("bull" if fast >= 0 else "correction") if slow >= 0 else ("rebound" if fast >= 0 else "bear")
    return state, slow, fast
