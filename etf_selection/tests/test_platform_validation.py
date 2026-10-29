from types import SimpleNamespace

import pytest
import yaml

from src.selection import run_platform_validation


@pytest.mark.parametrize("failure_index", [None, 0, 1, 2])
def test_validation_matches_windows_runs_both_sensitivities_and_stops_on_failure(tmp_path, monkeypatch, failure_index):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"backtest": {"start_date": "2020-01-02", "end_date": "2025-06-30"}}))
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        failed = len(calls) - 1 == failure_index
        return SimpleNamespace(returncode=int(failed), stdout="result", stderr="failure" if failed else "")

    monkeypatch.setattr("src.selection.subprocess.run", run)
    results = run_platform_validation([path], "platform/scripts/run_platform_experiment.py", tmp_path)
    assert len(results) == (3 if failure_index is None else failure_index + 1)
    assert [row["phase"] for row in results] == ["experiment", "candidate_sensitivity", "baseline_sensitivity"][:len(results)]
    for command in calls:
        assert command[command.index("--start-date") + 1] == "2020-01-02"
        assert command[command.index("--end-date") + 1] == "2025-06-30"
        assert command[command.index("--slippage-scenario") + 1] == "standard"
        if "run_sensitivity.py" in command[1]:
            assert command[command.index("--calendar-month-step") + 1] == "2"
