# -*- coding: utf-8 -*-
import os
import sys
import json
import yaml
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

# Path configuration
WORKSPACE_ROOT = Path(r"C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5")
PLATFORM_DIR = WORKSPACE_ROOT / "platform"
CACHE_DIR = PLATFORM_DIR / "results" / "backtest_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Data was synchronized on 2026-06-04 14:46. Any cache older than this must expire.
SYNC_DATETIME = datetime(2026, 6, 4, 14, 46, 0)

# All 11 platform configurations to test
configs_to_test = [
    "baseline_mvp_equal_weight",
    "baseline_m3m4_fundamental",
    "baseline_r1_domestic_rolling",
    "baseline_r1_domestic_ewma",
    "baseline_r1_domestic_low_vol_ewma",
    "baseline_r2_global_ewma",
    "baseline_r2_global_dividend_ewma",
    "baseline_r3_global_nasdaq_all_weather_ewma",
    "baseline_us_blend_ewma",
    "baseline_risk_parity_hrp",
    "baseline_risk_parity_lw_cov"
]

def get_cache(config_name, strategy_type):
    suffix = "baseline" if strategy_type == "baseline" else "candidate_semi_cov"
    cache_file = CACHE_DIR / f"{config_name}_{suffix}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cache_time = datetime.fromisoformat(data["timestamp"])
            if cache_time > SYNC_DATETIME:
                return data["metrics"]
            else:
                print(f"Cache expired for {config_name} ({strategy_type})")
        except Exception as e:
            print(f"Error reading cache for {config_name} ({strategy_type}): {e}")
    return None

def set_cache(config_name, strategy_type, metrics):
    suffix = "baseline" if strategy_type == "baseline" else "candidate_semi_cov"
    cache_file = CACHE_DIR / f"{config_name}_{suffix}.json"
    data = {
        "timestamp": datetime.now().isoformat(),
        "config_name": config_name,
        "strategy_type": strategy_type,
        "metrics": metrics
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_candidate_config(config_name):
    baseline_path = PLATFORM_DIR / "configs" / f"{config_name}.yaml"
    candidate_path = PLATFORM_DIR / "configs" / "generated" / f"{config_name}_candidate_semi_cov.yaml"
    
    with open(baseline_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    for segment in config["strategies"]["segments"]:
        segment["strategy_name"] = "risk_parity_semi_cov"
        if "params" not in segment:
            segment["params"] = {}
        # Apply standard/robust default parameters for downside semi-covariance
        if "rolling_window" not in segment["params"]:
            segment["params"]["rolling_window"] = 120
        if "min_periods" not in segment["params"]:
            segment["params"]["min_periods"] = 20
        if "rebalance_threshold" not in segment["params"]:
            segment["params"]["rebalance_threshold"] = 0.05
        # Custom parameters for downside semi-covariance
        if "semi_cov_threshold" not in segment["params"]:
            segment["params"]["semi_cov_threshold"] = 0.0
        if "shrinkage_intensity" not in segment["params"]:
            segment["params"]["shrinkage_intensity"] = 0.15
        
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    with open(candidate_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)
        
    return candidate_path

def safe_pct(val):
    if val is None:
        return "N/A"
    try:
        return f"{float(val)*100:.2f}%"
    except Exception:
        return "N/A"

def safe_val(val, fmt="{:.3f}"):
    if val is None:
        return "N/A"
    try:
        return fmt.format(float(val))
    except Exception:
        return "N/A"

def main():
    results = {}
    python_exe = str(WORKSPACE_ROOT / "env" / "python.exe")
    
    for config_name in configs_to_test:
        print(f"\n==========================================")
        print(f"Processing config: {config_name}")
        print(f"==========================================")
        
        # 1. Check cache
        baseline_metrics = get_cache(config_name, "baseline")
        candidate_metrics = get_cache(config_name, "candidate")
        
        if baseline_metrics and candidate_metrics:
            print(f"Using valid cached results for {config_name}")
        else:
            print(f"No valid cache or expired. Generating candidate config and running experiment...")
            # 2. Generate candidate config
            candidate_path = generate_candidate_config(config_name)
            baseline_path = PLATFORM_DIR / "configs" / f"{config_name}.yaml"
            
            # 3. Run backtest experiment
            exp_name = f"{config_name}_exp_semi_cov"
            cmd = [
                python_exe,
                "scripts/run_platform_experiment.py",
                "--config", str(candidate_path),
                "--baseline-config", str(baseline_path),
                "--experiment-name", exp_name
            ]
            print(f"Running command: {' '.join(cmd)}")
            log_path = PLATFORM_DIR / "results" / f"{config_name}_exp.log"
            
            try:
                with open(log_path, "w", encoding="utf-8") as log_file:
                    res = subprocess.run(cmd, stdout=log_file, stderr=log_file, text=True, cwd=str(PLATFORM_DIR))
                
                if res.returncode != 0:
                    print(f"Experiment failed for {config_name} with return code {res.returncode}:")
                    if log_path.exists():
                        with open(log_path, "r", encoding="utf-8") as lf:
                            print(lf.read())
                    continue
            except Exception as e:
                print(f"Exception raised during subprocess execution for {config_name}: {e}")
                traceback.print_exc()
                continue
                
            # 4. Read metrics from the latest experiment directory
            try:
                exp_dir = PLATFORM_DIR / "reports" / "experiments" / exp_name
                if not exp_dir.exists():
                    print(f"Experiment directory {exp_dir} not found!")
                    continue
                subdirs = sorted([d for d in exp_dir.iterdir() if d.is_dir()])
                if not subdirs:
                    print(f"No output timestamp directory found in {exp_dir}!")
                    continue
                latest_dir = subdirs[-1]
                metrics_path = latest_dir / "metrics.json"
                
                with open(metrics_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    
                candidate_metrics = payload["candidate"]
                baseline_metrics = payload["baseline"]
                
                # 5. Save to cache
                set_cache(config_name, "baseline", baseline_metrics)
                set_cache(config_name, "candidate", candidate_metrics)
                print(f"Successfully ran and cached results for {config_name}")
            except Exception as e:
                print(f"Exception raised during parsing metrics for {config_name}: {e}")
                traceback.print_exc()
                continue
            
        results[config_name] = {
            "baseline": baseline_metrics,
            "candidate": candidate_metrics
        }
        
    # Output result summary comparison table
    print("\n\n" + "="*50)
    print(" EXPERIMENT RESULTS COMPARISON SUMMARY ")
    print("="*50)
    print(f"{'Config Name':<42} | {'Strategy':<12} | {'Return':<8} | {'MDD':<8} | {'Sharpe':<6} | {'Turnover':<8} | {'Trades':<6}")
    print("-"*105)
    for name, data in results.items():
        if not data.get("baseline") or not data.get("candidate"):
            continue
        base = data["baseline"]
        cand = data["candidate"]
        
        b_ret = safe_pct(base.get('total_return'))
        b_mdd = safe_pct(base.get('max_drawdown'))
        b_shp = safe_val(base.get('sharpe_ratio'))
        b_turn = safe_pct(base.get('annualized_turnover'))
        b_trades = safe_val(base.get('trade_count'), "{}")
        
        c_ret = safe_pct(cand.get('total_return'))
        c_mdd = safe_pct(cand.get('max_drawdown'))
        c_shp = safe_val(cand.get('sharpe_ratio'))
        c_turn = safe_pct(cand.get('annualized_turnover'))
        c_trades = safe_val(cand.get('trade_count'), "{}")
        
        print(f"{name:<42} | {'baseline':<12} | {b_ret:>8} | {b_mdd:>8} | {b_shp:>6} | {b_turn:>8} | {b_trades:>6}")
        print(f"{'':<42} | {'candidate':<12} | {c_ret:>8} | {c_mdd:>8} | {c_shp:>6} | {c_turn:>8} | {c_trades:>6}")
        print("-"*105)

    # Write the results dict to a temporary json file for easy report generation
    summary_path = PLATFORM_DIR / "results" / "r011_experiments_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nWritten experimental results summary to {summary_path}")

if __name__ == "__main__":
    main()
