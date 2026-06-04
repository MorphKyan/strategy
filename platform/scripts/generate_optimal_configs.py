# -*- coding: utf-8 -*-
import json
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
configs_dir = ROOT / "configs"
mapping_path = ROOT / "results" / "optimal_strategy_mapping.json"

if not mapping_path.exists():
    print(f"Error: mapping file {mapping_path} not found.")
    sys.exit(1)

with open(mapping_path, "r", encoding="utf-8") as f:
    mapping = json.load(f)

# Standard optimal parameters
STRATEGY_PARAMS = {
    "risk_parity_ewma": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "ewma_lambda": 0.94,
        "rebalance_frequency": "monthly"
    },
    "risk_parity_cvar_dynamic_budget": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "confidence_level": 0.95,
        "cvar_sensitivity": 1.0,
        "volatility_target": 0.08,
        "cov_estimator": "ledoit_wolf",
        "rebalance_frequency": "monthly"
    }
}

for config_file, best_strat in mapping.items():
    source_path = configs_dir / config_file
    if not source_path.exists():
        continue
        
    with open(source_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    # Update run_name to specify it is the optimal runner
    if "platform" not in cfg:
        cfg["platform"] = {}
    cfg["platform"]["run_name"] = f"optimal_{config_file.replace('.yaml', '')}_{best_strat}"
    
    # Update backtest end date to align with latest available data
    if "backtest" in cfg:
        cfg["backtest"]["end_date"] = "2026-06-01"
        
    # Update strategy segments
    if "strategies" in cfg and "segments" in cfg["strategies"]:
        for segment in cfg["strategies"]["segments"]:
            segment["strategy_name"] = best_strat
            orig_params = segment.get("params", {})
            universe = orig_params.get("universe")
            
            # Inject optimal parameters
            segment["params"] = STRATEGY_PARAMS[best_strat].copy()
            if universe:
                segment["params"]["universe"] = universe
                
    # Save as optimal prefix config
    dest_file = f"optimal_{config_file}"
    dest_path = configs_dir / dest_file
    with open(dest_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True)
    print(f"Generated optimal config: {dest_file}")

print("\nSuccessfully updated all config files with optimal strategies!")
