# -*- coding: utf-8 -*-
import sys
import os
import json
import yaml
import math
import copy
import traceback
from pathlib import Path
from datetime import datetime, date

# Add platform root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.storage import SQLiteStore
from src.platform_core.metrics import build_platform_metrics

# Get all configuration files in platform/configs/ excluding 'generated' folder
CONFIGS_DIR = ROOT / "configs"

def get_platform_configs():
    yaml_files = []
    for file in CONFIGS_DIR.glob("*.yaml"):
        yaml_files.append(file)
    return sorted(yaml_files)

def calculate_metrics_for_subset(nav_df, trades_df, start_date_str, end_date_str):
    """
    Calculate portfolio metrics for a specific sub-period.
    """
    # Filter NAV
    nav_df = nav_df.copy()
    nav_df["date_parsed"] = nav_df["date"].astype(str)
    sub_nav = nav_df[(nav_df["date_parsed"] >= start_date_str) & (nav_df["date_parsed"] <= end_date_str)]
    
    # Filter trades
    trades_df = trades_df.copy()
    if not trades_df.empty:
        trades_df["date_parsed"] = trades_df["date"].astype(str)
        sub_trades = trades_df[(trades_df["date_parsed"] >= start_date_str) & (trades_df["date_parsed"] <= end_date_str)]
    else:
        sub_trades = trades_df

    if sub_nav.empty or len(sub_nav) < 2:
        return {
            "total_return": 0.0, "annualized_return": 0.0, "annualized_volatility": 0.0,
            "max_drawdown": 0.0, "sharpe_ratio": 0.0, "annualized_turnover_amount": 0.0,
            "annualized_turnover_quantity": 0.0, "trade_count": 0
        }

    net_value = sub_nav["net_value"].astype(float).values
    total_value = sub_nav["total_value"].astype(float).values if "total_value" in sub_nav.columns else net_value
    
    # Calculate returns
    days = len(sub_nav)
    years = days / 252.0 if days else 0.0
    
    total_return = net_value[-1] / net_value[0] - 1.0 if net_value[0] else 0.0
    
    daily_returns = [net_value[i] / net_value[i-1] - 1.0 for i in range(1, len(net_value))]
    
    if len(daily_returns) > 0:
        mean_return = sum(daily_returns) / len(daily_returns)
        # Annualized return
        annualized_return = (net_value[-1] / net_value[0]) ** (252.0 / max(len(daily_returns), 1)) - 1.0
        # Volatility
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)
        annualized_volatility = math.sqrt(variance * 252.0)
    else:
        annualized_return = 0.0
        annualized_volatility = 0.0

    # Max Drawdown
    peak = net_value[0]
    max_drawdown = 0.0
    for val in net_value:
        if val > peak:
            peak = val
        if peak:
            drawdown = val / peak - 1.0
            if drawdown < max_drawdown:
                max_drawdown = drawdown

    # Sharpe
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0

    # Turnover
    average_total_value = sum(total_value) / len(total_value) if len(total_value) else 1.0
    
    if not sub_trades.empty:
        turnover_amount_total = sub_trades["trade_value"].astype(float).abs().sum()
        turnover_quantity_total = sub_trades["quantity"].astype(float).abs().sum()
        trade_count = len(sub_trades)
    else:
        turnover_amount_total = 0.0
        turnover_quantity_total = 0.0
        trade_count = 0

    turnover_amount_ratio = turnover_amount_total / average_total_value if average_total_value > 0 else 0.0
    annualized_turnover_amount = turnover_amount_ratio / years if years else turnover_amount_ratio
    annualized_turnover_quantity = turnover_quantity_total / years if years else turnover_quantity_total

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "annualized_turnover_amount": annualized_turnover_amount,
        "annualized_turnover_quantity": annualized_turnover_quantity,
        "trade_count": trade_count
    }

def run_single_config(config_path):
    print(f"\n==================================================")
    print(f"Config: {config_path.name}")
    print(f"==================================================")
    
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 1. Run the Full Backtest using sqlite
    db_path = ROOT / "data" / "platform" / "platform.sqlite3"
    store = SQLiteStore(db_path)
    
    # Disable checkpoints for speed
    config_run = copy.deepcopy(config)
    config_run.setdefault("backtest", {})["enable_checkpoints"] = False
    
    # Run full backtest
    engine = PlatformBacktestEngine(config=config_run, store=store)
    result = engine.run()
    store.close()
    
    # Read outputs
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
    nav_df = nav_df.sort_values("date")
    dates = nav_df["date"].astype(str).tolist()
    
    if not dates:
        print(f"Error: No trading dates found for {config_path.name}")
        return None
        
    start_date = dates[0]
    end_date = dates[-1]
    
    # 2. In-sample (IS) subset (up to 2025-06-30)
    is_end_date = min("2025-06-30", end_date)
    is_metrics = calculate_metrics_for_subset(nav_df, trades_df, start_date, is_end_date)
    
    # 3. Out-of-sample (OOS) subset (from 2025-07-01 to end)
    oos_start_date = "2025-07-01"
    if end_date >= oos_start_date:
        oos_metrics = calculate_metrics_for_subset(nav_df, trades_df, oos_start_date, end_date)
    else:
        oos_metrics = {
            "total_return": 0.0, "annualized_return": 0.0, "annualized_volatility": 0.0,
            "max_drawdown": 0.0, "sharpe_ratio": 0.0, "annualized_turnover_amount": 0.0,
            "annualized_turnover_quantity": 0.0, "trade_count": 0
        }
        
    # 4. Start-date sensitivity test
    # Get the calendar of trading days up to 2025-06-30
    calendar = [d.strftime("%Y-%m-%d") for d in engine.data.calendar if d.strftime("%Y-%m-%d") <= "2025-06-30"]
    
    sensitivity_runs = []
    # Generate start dates every 42 trading days (approx. 2 months)
    step = 42
    start_indices = list(range(0, len(calendar), step))
    
    # Make sure we don't start too close to the end (need at least 126 trading days/6 months of data)
    valid_start_indices = [idx for idx in start_indices if (len(calendar) - idx) >= 126]
    
    if len(valid_start_indices) < 3:
        # If too short, use all start indices that leave at least 60 trading days
        valid_start_indices = [idx for idx in start_indices if (len(calendar) - idx) >= 60]
        
    print(f"Running start-date sensitivity tests ({len(valid_start_indices)} runs)...")
    
    temp_results_dir = ROOT / "results" / "temp_sensitivity"
    temp_results_dir.mkdir(parents=True, exist_ok=True)
    
    for idx in valid_start_indices:
        temp_start_date = calendar[idx]
        
        # Configure temp run
        config_temp = copy.deepcopy(config)
        config_temp["backtest"]["start_date"] = temp_start_date
        config_temp["backtest"]["end_date"] = "2025-06-30"
        config_temp["backtest"]["enable_checkpoints"] = False
        if "strategies" in config_temp and "segments" in config_temp["strategies"]:
            config_temp["strategies"]["segments"][0]["start_date"] = temp_start_date
            config_temp["strategies"]["segments"][0]["end_date"] = "2025-06-30"
            
        # Use in-memory SQLite store
        temp_store = SQLiteStore(":memory:")
        try:
            temp_engine = PlatformBacktestEngine(config=config_temp, store=temp_store, output_dir=temp_results_dir / f"sens_{config_path.stem}_{temp_start_date}")
            temp_result = temp_engine.run()
            
            temp_nav = read_csv_safe(temp_result.output_dir / "nav.csv")
            temp_trades = read_csv_safe(temp_result.output_dir / "trades.csv")
            
            # Calculate metrics for the training period
            run_metrics = calculate_metrics_for_subset(temp_nav, temp_trades, temp_start_date, "2025-06-30")
            
            sensitivity_runs.append({
                "start_date": temp_start_date,
                "sharpe_ratio": run_metrics["sharpe_ratio"],
                "annualized_return": run_metrics["annualized_return"],
                "max_drawdown": run_metrics["max_drawdown"],
                "annualized_turnover_amount": run_metrics["annualized_turnover_amount"],
                "trade_count": run_metrics["trade_count"]
            })
        except Exception as e:
            print(f"  Failed sensitivity run for start_date {temp_start_date}: {e}")
        finally:
            temp_store.close()
                
    # Calculate sensitivity statistics
    if sensitivity_runs:
        sharpes = [r["sharpe_ratio"] for r in sensitivity_runs]
        returns = [r["annualized_return"] for r in sensitivity_runs]
        drawdowns = [r["max_drawdown"] for r in sensitivity_runs]
        turnovers = [r["annualized_turnover_amount"] for r in sensitivity_runs]
        
        sensitivity_stats = {
            "count": len(sensitivity_runs),
            "sharpe_mean": sum(sharpes) / len(sharpes),
            "sharpe_std": pd.Series(sharpes).std() if len(sharpes) > 1 else 0.0,
            "sharpe_min": min(sharpes),
            "sharpe_max": max(sharpes),
            "return_mean": sum(returns) / len(returns),
            "return_std": pd.Series(returns).std() if len(returns) > 1 else 0.0,
            "drawdown_mean": sum(drawdowns) / len(drawdowns),
            "drawdown_std": pd.Series(drawdowns).std() if len(drawdowns) > 1 else 0.0,
            "turnover_mean": sum(turnovers) / len(turnovers)
        }
    else:
        sensitivity_stats = {
            "count": 0, "sharpe_mean": 0.0, "sharpe_std": 0.0, "sharpe_min": 0.0, "sharpe_max": 0.0,
            "return_mean": 0.0, "return_std": 0.0, "drawdown_mean": 0.0, "drawdown_std": 0.0, "turnover_mean": 0.0
        }
        
    full_metrics = calculate_metrics_for_subset(nav_df, trades_df, start_date, end_date)
    
    result_data = {
        "config_name": config_path.name,
        "is_baseline": config_path.name.startswith("baseline_"),
        "is_optimal": config_path.name.startswith("optimal_") or "_opt_" in config_path.name,
        "start_date": start_date,
        "end_date": end_date,
        "full_metrics": full_metrics,
        "is_metrics": is_metrics,
        "oos_metrics": oos_metrics,
        "sensitivity_stats": sensitivity_stats,
        "sensitivity_runs": sensitivity_runs
    }
    
    print(f"Full Sharpe: {full_metrics['sharpe_ratio']:.3f} | IS Sharpe: {is_metrics['sharpe_ratio']:.3f} | OOS Sharpe: {oos_metrics['sharpe_ratio']:.3f}")
    print(f"Sensitivity Sharpe Mean: {sensitivity_stats['sharpe_mean']:.3f} (Std: {sensitivity_stats['sharpe_std']:.3f})")
    
    return result_data

def main():
    configs = get_platform_configs()
    print(f"Found {len(configs)} platform configurations.")
    
    all_results = []
    
    for config_path in configs:
        try:
            res = run_single_config(config_path)
            if res:
                all_results.append(res)
        except Exception as e:
            print(f"Error running backtest for {config_path.name}: {e}")
            traceback.print_exc()
            
    # Save all results to a JSON file
    output_json_path = ROOT / "results" / "all_configs_evaluation_results.json"
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print(f"\nAll configuration evaluations completed. Saved to {output_json_path}")

if __name__ == "__main__":
    main()
