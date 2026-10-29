from datetime import date

import pytest

from src.platform_core.data_store import validate_market_dates


def test_exactly_seven_days_old_aligned_snapshot_is_accepted():
    validate_market_dates({"A": date(2026, 10, 22), "B": date(2026, 10, 22)}, date(2026, 10, 29))


@pytest.mark.parametrize("latest,message", [
    ({}, "Missing"), ({"A": None}, "Missing"),
    ({"A": date(2026, 10, 28), "B": date(2026, 10, 29)}, "not aligned"),
    ({"A": date(2026, 10, 21)}, "Stale"), ({"A": date(2026, 10, 30)}, "Future"),
])
def test_invalid_market_snapshot_fails(latest, message):
    with pytest.raises(RuntimeError, match=message):
        validate_market_dates(latest, date(2026, 10, 29))
