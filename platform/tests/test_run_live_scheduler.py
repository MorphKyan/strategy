from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from scripts.run_live_scheduler import (
    build_cycle_command,
    execute_with_retries,
    next_run_datetime,
    parse_run_time,
)

TZ = ZoneInfo("Asia/Shanghai")


def test_parse_run_time_valid_and_invalid() -> None:
    assert parse_run_time("18:15") == (18, 15)
    assert parse_run_time("09:05") == (9, 5)
    with pytest.raises(ValueError):
        parse_run_time("25:00")
    with pytest.raises(ValueError):
        parse_run_time("1815")


def test_next_run_datetime_weekdays_and_weekend() -> None:
    # Friday before trigger -> same day
    fri_morning = datetime(2026, 11, 27, 10, 0, tzinfo=TZ)
    assert next_run_datetime(fri_morning, 18, 15) == datetime(2026, 11, 27, 18, 15, tzinfo=TZ)

    # Friday after trigger -> next Monday
    fri_evening = datetime(2026, 11, 27, 18, 15, tzinfo=TZ)
    assert next_run_datetime(fri_evening, 18, 15) == datetime(2026, 11, 30, 18, 15, tzinfo=TZ)

    # Saturday -> Monday
    sat = datetime(2026, 11, 28, 12, 0, tzinfo=TZ)
    assert next_run_datetime(sat, 18, 15) == datetime(2026, 11, 30, 18, 15, tzinfo=TZ)


def test_build_cycle_command() -> None:
    cmd = build_cycle_command(
        "configs/demo.yaml",
        "live_demo",
        sync=True,
        notify=True,
        shadow="sim_demo",
        asof_date="2026-11-27",
    )
    assert "cycle" in cmd
    assert "--config" in cmd and "configs/demo.yaml" in cmd
    assert "--portfolio" in cmd and "live_demo" in cmd
    assert "--sync" in cmd
    assert "--notify" in cmd
    assert "--shadow" in cmd and "sim_demo" in cmd
    assert "--asof-date" in cmd and "2026-11-27" in cmd


def test_execute_with_retries_recovers() -> None:
    calls: list[list[str]] = []

    def fake_runner(cmd: list[str], cwd=None):
        calls.append(cmd)
        return SimpleNamespace(returncode=0 if len(calls) == 2 else 1)

    code = execute_with_retries(["echo", "ok"], max_retries=2, retry_delay_seconds=0.01, runner=fake_runner)
    assert code == 0
    assert len(calls) == 2
