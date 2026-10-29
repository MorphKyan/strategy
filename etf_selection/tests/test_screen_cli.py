import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


@pytest.mark.parametrize("failure", [None, "sync", "recheck"])
def test_stale_screening_syncs_all_candidates_and_stops_on_failure(tmp_path, monkeypatch, failure):
    spec = importlib.util.spec_from_file_location("screen_cli", Path(__file__).parents[1] / "scripts/screen_etf_sleeves.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({
        "paths": {"data_dir": str(tmp_path / "data")},
        "candidates": [{"code": "510300", "exchange": "SH"}, {"code": "159985", "exchange": "SZ"},
                       {"code": "518880", "include": False}],
    }))
    monkeypatch.setattr(sys, "argv", ["screen", "--config", str(path)])
    calls, syncs, reports = [], [], []

    def screen(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1 or failure == "recheck":
            raise RuntimeError("行情过期")
        return pd.DataFrame(), {}, {}

    def sync(command, **kwargs):
        syncs.append((command, kwargs))
        if failure == "sync":
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(module, "screen_sleeves", screen)
    monkeypatch.setattr(module.subprocess, "run", sync)
    monkeypatch.setattr(module, "write_report", lambda *args, **kwargs: reports.append(1))
    if failure:
        with pytest.raises(subprocess.CalledProcessError if failure == "sync" else RuntimeError):
            module.main()
        assert not reports
    else:
        assert module.main() == 0
        assert reports == [1]
    assert len(calls) == (1 if failure == "sync" else 2)
    assert len(syncs) == 1
    command, options = syncs[0]
    assert options["check"] is True
    assert "510300.SH:etf" in command and "159985.SZ:etf" in command
    assert not any("518880" in argument for argument in command)
