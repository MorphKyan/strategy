# -*- coding: utf-8 -*-
import sys
import os
import shutil
import json
import yaml
import math
import copy
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.storage import SQLiteStore
from src.platform_core.strategy import BUILTIN_STRATEGIES

CONFIGS_DIR = ROOT / "configs"
GENERATED_DIR = CONFIGS_DIR / "generated"

def read_yaml(path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_yaml(path, data):
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

def get_asset_codes(config):
    return sorted([str(asset["code"]) for asset in config.get("assets", [])])

def get_strategy_name(config):
    try:
        return config["strategies"]["segments"][0]["strategy_name"]
    except Exception:
        return None

def calculate_metrics_for_subset(nav_df, trades_df, start_date_str, end_date_str):
    if nav_df.empty:
        return {"sharpe_ratio": 0.0, "annualized_return": 0.0, "max_drawdown": 0.0}
    
    nav_df = nav_df.copy()
    nav_df["date_parsed"] = nav_df["date"].astype(str)
    sub_nav = nav_df[(nav_df["date_parsed"] >= start_date_str) & (nav_df["date_parsed"] <= end_date_str)]
    
    if sub_nav.empty or len(sub_nav) < 2:
        return {"sharpe_ratio": 0.0, "annualized_return": 0.0, "max_drawdown": 0.0}

    net_value = sub_nav["net_value"].astype(float).values
    days = len(sub_nav)
    
    total_return = net_value[-1] / net_value[0] - 1.0 if net_value[0] else 0.0
    daily_returns = [net_value[i] / net_value[i-1] - 1.0 for i in range(1, len(net_value))]
    
    if len(daily_returns) > 0:
        mean_return = sum(daily_returns) / len(daily_returns)
        annualized_return = (net_value[-1] / net_value[0]) ** (252.0 / max(len(daily_returns), 1)) - 1.0
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)
        annualized_volatility = math.sqrt(variance * 252.0)
    else:
        annualized_return = 0.0
        annualized_volatility = 0.0

    peak = net_value[0]
    max_drawdown = 0.0
    for val in net_value:
        if val > peak:
            peak = val
        if peak:
            drawdown = val / peak - 1.0
            if drawdown < max_drawdown:
                max_drawdown = drawdown

    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
    return {
        "sharpe_ratio": sharpe_ratio,
        "annualized_return": annualized_return,
        "max_drawdown": max_drawdown
    }

def run_is_backtest_and_sensitivity(config_data, config_name):
    # Configure backtest to cap at 2025-06-30
    config_run = copy.deepcopy(config_data)
    config_run.setdefault("backtest", {})["end_date"] = "2025-06-30"
    config_run["backtest"]["enable_checkpoints"] = False
    
    # Cap segment end dates
    if "strategies" in config_run and "segments" in config_run["strategies"]:
        for seg in config_run["strategies"]["segments"]:
            if seg.get("end_date") is None or seg["end_date"] > "2025-06-30":
                seg["end_date"] = "2025-06-30"
            if seg["start_date"] > "2025-06-30":
                seg["start_date"] = "2025-06-30"

    # Run in-memory backtest
    store = SQLiteStore(":memory:")
    try:
        engine = PlatformBacktestEngine(config=config_run, store=store)
        result = engine.run()
        
        import pandas as pd
        def read_csv_safe(path):
            if not path.exists() or path.stat().st_size == 0:
                return pd.DataFrame()
            try:
                return pd.read_csv(path)
            except Exception:
                return pd.DataFrame()

        nav_df = read_csv_safe(result.output_dir / "nav.csv")
        trades_df = read_csv_safe(result.output_dir / "trades.csv")
        
        # Sort dates
        if not nav_df.empty:
            nav_df = nav_df.sort_values("date")
            dates = nav_df["date"].astype(str).tolist()
        else:
            dates = []
            
        if not dates:
            return None
            
        start_date = dates[0]
        end_date = dates[-1]
        
        is_metrics = calculate_metrics_for_subset(nav_df, trades_df, start_date, end_date)
        
        # Sensitivity
        calendar = [d.strftime("%Y-%m-%d") for d in engine.data.calendar if d.strftime("%Y-%m-%d") <= "2025-06-30"]
        step = 42
        start_indices = list(range(0, len(calendar), step))
        valid_start_indices = [idx for idx in start_indices if (len(calendar) - idx) >= 126]
        if len(valid_start_indices) < 3:
            valid_start_indices = [idx for idx in start_indices if (len(calendar) - idx) >= 60]
            
        sensitivity_sharpes = []
        temp_results_dir = ROOT / "results" / "temp_sensitivity_screen"
        temp_results_dir.mkdir(parents=True, exist_ok=True)
        
        for idx in valid_start_indices:
            temp_start_date = calendar[idx]
            config_temp = copy.deepcopy(config_run)
            config_temp["backtest"]["start_date"] = temp_start_date
            if "strategies" in config_temp and "segments" in config_temp["strategies"]:
                config_temp["strategies"]["segments"][0]["start_date"] = temp_start_date
                
            temp_store = SQLiteStore(":memory:")
            try:
                temp_engine = PlatformBacktestEngine(config=config_temp, store=temp_store, output_dir=temp_results_dir / f"sens_{temp_start_date}")
                temp_result = temp_engine.run()
                
                t_nav = read_csv_safe(temp_result.output_dir / "nav.csv")
                t_trades = read_csv_safe(temp_result.output_dir / "trades.csv")
                
                run_metrics = calculate_metrics_for_subset(t_nav, t_trades, temp_start_date, "2025-06-30")
                sensitivity_sharpes.append(run_metrics["sharpe_ratio"])
            except Exception as e:
                print(f"    Sensitivity run failed for {temp_start_date}: {e}")
                traceback.print_exc()
            finally:
                temp_store.close()
                run_dir = temp_results_dir / f"sens_{temp_start_date}"
                if run_dir.exists():
                    shutil.rmtree(run_dir, ignore_errors=True)
                    
        if sensitivity_sharpes:
            sens_mean = sum(sensitivity_sharpes) / len(sensitivity_sharpes)
            sens_std = pd.Series(sensitivity_sharpes).std() if len(sensitivity_sharpes) > 1 else 0.0
        else:
            sens_mean = 0.0
            sens_std = 0.0
            
        return {
            "sharpe_ratio": is_metrics["sharpe_ratio"],
            "annualized_return": is_metrics["annualized_return"],
            "max_drawdown": is_metrics["max_drawdown"],
            "sens_mean": sens_mean,
            "sens_std": sens_std
        }
    except Exception as e:
        print(f"Error running backtest/sensitivity for {config_name}: {e}")
        traceback.print_exc()
        return None
    finally:
        store.close()

def main():
    baselines = sorted([p for p in CONFIGS_DIR.glob("baseline_*.yaml") if p.is_file()])
    print(f"Found {len(baselines)} baseline configurations to evaluate.")
    
    all_candidates = sorted(list(GENERATED_DIR.glob("*.yaml")))
    print(f"Found {len(all_candidates)} generated configs in generated/.")
    
    # Store candidates in memory by asset codes
    candidate_pool = []
    for cp in all_candidates:
        try:
            cfg = read_yaml(cp)
            s_name = get_strategy_name(cfg)
            if not s_name:
                continue
            if s_name not in BUILTIN_STRATEGIES:
                # Skip unregistered strategies
                continue
            assets = get_asset_codes(cfg)
            candidate_pool.append({
                "path": cp,
                "config": cfg,
                "strategy_name": s_name,
                "assets": assets
            })
        except Exception:
            pass
            
    print(f"Active valid candidates (with registered strategies): {len(candidate_pool)}")
    
    screen_results = {}
    
    for bp in baselines:
        print(f"\n==================================================")
        print(f"Baseline: {bp.name}")
        print(f"==================================================")
        
        b_cfg = read_yaml(bp)
        b_assets = get_asset_codes(b_cfg)
        b_strategy = get_strategy_name(b_cfg)
        
        # 1. Backtest baseline on training sample
        print("Running baseline on training set...")
        b_metrics = run_is_backtest_and_sensitivity(b_cfg, bp.name)
        if not b_metrics:
            print("Failed to run baseline. Skipping.")
            continue
            
        print(f"Baseline IS Sharpe: {b_metrics['sharpe_ratio']:.3f} | Sens Mean: {b_metrics['sens_mean']:.3f} (Std: {b_metrics['sens_std']:.3f})")
        
        # 2. Find matching candidates
        matching = []
        for cand in candidate_pool:
            if cand["assets"] == b_assets:
                matching.append(cand)
                
        # Also include existing optimal config as a candidate if its assets match
        stem_suffix = bp.stem[len("baseline_"):] if bp.name.startswith("baseline_") else bp.stem
        existing_opt_files = list(CONFIGS_DIR.glob(f"baseline_opt_{stem_suffix}_*.yaml"))
        for opt_file in existing_opt_files:
            try:
                opt_cfg = read_yaml(opt_file)
                if get_asset_codes(opt_cfg) == b_assets and get_strategy_name(opt_cfg) in BUILTIN_STRATEGIES:
                    matching.append({
                        "path": opt_file,
                        "config": opt_cfg,
                        "strategy_name": get_strategy_name(opt_cfg),
                        "assets": b_assets,
                        "is_existing_optimal": True
                    })
            except Exception:
                pass
                
        if not matching:
            print("No valid candidates with the same asset universe found. Deleting optimal config if it exists.")
            for opt_file in existing_opt_files:
                opt_file.unlink()
                print(f"Deleted {opt_file.name}")
            continue
            
        print(f"Found {len(matching)} matching candidates. Evaluating...")
        
        best_candidate = None
        best_sharpe = b_metrics["sharpe_ratio"]
        best_metrics = b_metrics
        
        for cand in matching:
            c_name = cand["path"].name
            print(f"Evaluating candidate: {c_name} ({cand['strategy_name']})...")
            c_metrics = run_is_backtest_and_sensitivity(cand["config"], c_name)
            if not c_metrics:
                continue
                
            print(f"  IS Sharpe: {c_metrics['sharpe_ratio']:.3f} | Sens Mean: {c_metrics['sens_mean']:.3f} (Std: {c_metrics['sens_std']:.3f})")
            
            # Select candidate if:
            # 1. Sharpe ratio on training set is higher than current best.
            # 2. Sensitivity is stable (std < 0.6).
            if c_metrics["sharpe_ratio"] > best_sharpe + 0.02 and c_metrics["sens_std"] < 0.6:
                best_sharpe = c_metrics["sharpe_ratio"]
                best_candidate = cand
                best_metrics = c_metrics
                
        if best_candidate:
            c_name = best_candidate["path"].name
            new_strat = best_candidate["strategy_name"]
            new_opt_name = f"baseline_opt_{stem_suffix}_{new_strat}.yaml"
            new_opt_path = CONFIGS_DIR / new_opt_name
            print(f"Result: Candidate {c_name} outperforms baseline. Saving as {new_opt_name}")
            # Ensure output results dir is standard
            opt_cfg_to_save = copy.deepcopy(best_candidate["config"])
            opt_cfg_to_save["platform"]["run_name"] = f"baseline_opt_{stem_suffix}_{new_strat}"
            opt_cfg_to_save["output"]["results_dir"] = "results/backtests"
            # Ensure backtest dates match standard range (back to original range)
            opt_cfg_to_save["backtest"]["start_date"] = b_cfg["backtest"]["start_date"]
            opt_cfg_to_save["backtest"]["end_date"] = b_cfg["backtest"]["end_date"]
            if "strategies" in opt_cfg_to_save and "segments" in opt_cfg_to_save["strategies"]:
                opt_cfg_to_save["strategies"]["segments"][0]["start_date"] = b_cfg["strategies"]["segments"][0]["start_date"]
                opt_cfg_to_save["strategies"]["segments"][0]["end_date"] = b_cfg["strategies"]["segments"][0]["end_date"]
            
            # Delete any other existing optimal configs for this baseline to prevent duplicates
            for opt_file in existing_opt_files:
                if opt_file != new_opt_path:
                    opt_file.unlink()
                    print(f"Deleted outdated optimal config: {opt_file.name}")
            
            write_yaml(new_opt_path, opt_cfg_to_save)
            print(f"Saved {new_opt_path.name}")
        else:
            print("Result: No candidate outperforms the baseline in-sample. Deleting optimal config if it exists.")
            for opt_file in existing_opt_files:
                opt_file.unlink()
                print(f"Deleted {opt_file.name}")

if __name__ == "__main__":
    main()
