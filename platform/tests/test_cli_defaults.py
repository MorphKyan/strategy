import ast
from pathlib import Path

import yaml

from src.platform_core.data_store import assets_from_config
from src.platform_core.engine import load_strategy_config
from src.platform_core.execution import ExecutionConfig
from src.platform_core.strategy import get_strategy_class
from src.platform_core.sync_universe import discover_fixed_configs


def test_all_fixed_configs_pass_shared_runtime_validation():
    root = Path(__file__).parents[1]
    for path in discover_fixed_configs(root / "configs"):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert assets_from_config(config["assets"]), path.name
        strategy = load_strategy_config(config["strategy"])
        get_strategy_class(strategy["strategy_name"])
        ExecutionConfig.from_config(config.get("execution", {}))


def test_public_cli_default_input_configs_exist():
    root = Path(__file__).parents[2]
    missing = []
    for subsystem in ("platform", "etf_selection"):
        for path in (root / subsystem / "scripts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
                    continue
                options = [arg.value for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
                if not any("config" in option and "output" not in option for option in options):
                    continue
                for keyword in node.keywords:
                    if keyword.arg != "default" or not isinstance(keyword.value, ast.Constant):
                        continue
                    value = keyword.value.value
                    if not isinstance(value, str) or not value.endswith((".yaml", ".yml")):
                        continue
                    base = root if value.startswith(("platform/", "etf_selection/")) else root / subsystem
                    if not (base / value).is_file():
                        missing.append(f"{path.name}: {value}")
    assert not missing, "Missing default input configs: " + "; ".join(missing)


def test_etf_universe_templates_reference_existing_platform_configs():
    root = Path(__file__).parents[2]
    for path in (root / "etf_selection" / "config").glob("*.yaml"):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert (root / config["paths"]["platform_base_config"]).is_file(), path.name
