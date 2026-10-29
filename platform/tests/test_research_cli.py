import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


def _script(name, monkeypatch):
    monkeypatch.chdir(Path.cwd())
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("explicit,expected", [(None, ["default", "stress"]), ("all", ["default", "stress", "dynamic_participation"])])
def test_backtest_cli_defaults_to_user_directed_scenarios(tmp_path, monkeypatch, explicit, expected):
    module = _script("run_platform_backtest", monkeypatch)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"platform": {}, "execution": {}}))
    calls = []

    class Engine:
        def __init__(self, config, **kwargs):
            calls.append(config["execution"]["slippage_scenario"])

        def run(self):
            return SimpleNamespace(output_dir=tmp_path, run_id="test", metrics={})

    monkeypatch.setattr(module, "PlatformBacktestEngine", Engine)
    arguments = ["run", "--config", str(path)]
    if explicit:
        arguments += ["--slippage-scenario", explicit]
    monkeypatch.setattr(sys, "argv", arguments)
    assert module.main() == 0
    assert calls == expected


def test_experiment_cli_defaults_to_two_scenarios(tmp_path, monkeypatch):
    module = _script("run_platform_experiment", monkeypatch)
    calls = []

    def run(**kwargs):
        calls.append(kwargs["slippage_scenario"])
        return SimpleNamespace(report_dir=tmp_path, candidate=SimpleNamespace(output_dir=tmp_path), baseline=None)

    monkeypatch.setattr(module, "run_platform_experiment", run)
    monkeypatch.setattr(sys, "argv", ["run", "--config", str(tmp_path / "config.yaml")])
    assert module.main() == 0
    assert calls == ["default", "stress"]


@pytest.mark.parametrize("step,expected_days", [
    (None, ("2024-01-02", "2024-03-04", "2024-05-06")),
    (3, ("2024-01-02", "2024-05-06")),
])
def test_sensitivity_defaults_to_two_calendar_months_and_two_scenarios(tmp_path, monkeypatch, step, expected_days):
    module = _script("run_sensitivity", monkeypatch)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"platform": {}, "strategy": {"strategy_name": "monthly_equal_weight"}}))
    dates = ["2024-01-02", "2024-01-03", "2024-03-04", "2024-05-06", "2024-06-28"]
    calls = []
    def calendar(config):
        assert config["backtest"] == {"start_date": "2024-01-02", "end_date": "2024-06-28"}
        return dates

    monkeypatch.setattr(module, "calendar_for_config", calendar)
    monkeypatch.setattr(module, "render_sensitivity_charts", lambda *args: None)

    def run(config, *args, **kwargs):
        calls.append((config["execution"]["slippage_scenario"], config["backtest"]["start_date"]))
        return SimpleNamespace(run_id="test", output_dir=tmp_path, metrics={})

    monkeypatch.setattr(module, "run_backtest", run)
    arguments = ["run", "--config", str(path), "--raw-root", str(tmp_path / "raw"),
                 "--report-root", str(tmp_path / "reports"), "--start-date", "2024-01-02", "--end-date", "2024-06-28"]
    if step is not None:
        arguments += ["--step", str(step)]
    monkeypatch.setattr(sys, "argv", arguments)
    assert module.main() == 0
    assert calls == [(scenario, day) for scenario in ("default", "stress") for day in expected_days]


def test_sim_cli_resumes_existing_portfolio_without_resetting_checkpoint(tmp_path, monkeypatch):
    module = _script("run_sim_portfolio", monkeypatch)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"output": {"sim_dir": str(tmp_path / "sims")}}))
    state_path = tmp_path / "sims" / "existing" / "portfolio_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{}")
    calls = []

    def load(*args, **kwargs):
        calls.append("load")
        return SimpleNamespace(advance=lambda asof: SimpleNamespace(
            output_dir=tmp_path, portfolio_id="existing", metrics={"processed_days": 1}))

    monkeypatch.setattr(module.SimPortfolio, "load", load)
    monkeypatch.setattr(module.SimPortfolio, "create_from_checkpoint",
                        lambda *args, **kwargs: pytest.fail("已有组合不应从旧 checkpoint 重新创建"))
    monkeypatch.setattr(sys, "argv", ["run", "--config", str(path), "--portfolio-id", "existing",
                                      "--asof-date", "2024-01-31"])
    assert module.main() == 0
    assert calls == ["load"]
