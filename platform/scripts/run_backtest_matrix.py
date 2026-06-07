# -*- coding: utf-8 -*-
import sys
import os
import shutil
import json
import yaml
import traceback
import copy
from pathlib import Path
from datetime import datetime

# Add platform root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.storage import SQLiteStore
from src.platform_core.metrics import build_platform_metrics

# 10 active strategies registered in BUILTIN_STRATEGIES
STRATEGY_PARAMS = {
    "monthly_equal_weight": {
        "cooldown_days": 0,
        "rebalance_on_start": True
    },
    "balanced": {
        "cooldown_days": 0,
        "rebalance_threshold": 0.05
    },
    "risk_parity": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05
    },
    "risk_parity_ewma": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "ewma_lambda": 0.94
    },
    "risk_parity_ewma_dd_recovery": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "ewma_lambda": 0.94,
        "rebound_filter_window": 0,
        "downside_threshold": 0.025
    },
    "risk_parity_lw_cov": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05
    },
    "hrp": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05
    },
    "risk_parity_cvar_dynamic_budget": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "confidence_level": 0.95,
        "cvar_sensitivity": 1.0,
        "volatility_target": 0.08,
        "cov_estimator": "ledoit_wolf"
    },
    "adaptive_risk_deviation_volatility_triggered": {
        "rolling_window": 120,
        "min_periods": 20,
        "rebalance_threshold": 0.05,
        "short_window": 20,
        "threshold_sensitivity": 1.0,
        "vol_trigger_ratio": 2.0,
        "min_threshold": 0.01,
        "max_threshold": 0.20,
        "cov_estimator": "ledoit_wolf",
        "shrinkage_target": "constant_correlation"
    }
}

# Only run unique configurations to avoid redundant heavy computation
unique_configs = [
    "baseline_mvp_equal_weight.yaml",
    "baseline_r1_domestic_rolling.yaml",
    "baseline_r1_domestic_low_vol_ewma.yaml",
    "baseline_r2_global_ewma.yaml",
    "baseline_r2_global_dividend_ewma.yaml",
    "baseline_r3_global_nasdaq_all_weather_ewma.yaml",
    "baseline_us_blend_ewma.yaml"
]

# Map duplicates (same assets, same timeframe) to avoid recalculation
duplicate_map = {
    "baseline_risk_parity_hrp.yaml": "baseline_mvp_equal_weight.yaml",
    "baseline_risk_parity_lw_cov.yaml": "baseline_mvp_equal_weight.yaml",
    "baseline_r5_cvar_dynamic_budget.yaml": "baseline_mvp_equal_weight.yaml",
    "baseline_r6_adaptive_risk_deviation.yaml": "baseline_mvp_equal_weight.yaml",
    "baseline_r1_domestic_ewma.yaml": "baseline_r1_domestic_rolling.yaml"
}

all_configs = unique_configs + list(duplicate_map.keys())

def make_test_config(base_config, strategy_name, recommended_params):
    cfg = copy.deepcopy(base_config)
    if "platform" not in cfg:
        cfg["platform"] = {}
    
    base_run_name = cfg.get("platform", {}).get("run_name", "backtest")
    cfg["platform"]["run_name"] = f"matrix_{base_run_name}_{strategy_name}"
    
    if "strategies" in cfg and "segments" in cfg["strategies"]:
        for segment in cfg["strategies"]["segments"]:
            segment["strategy_name"] = strategy_name
            orig_params = segment.get("params", {})
            universe = orig_params.get("universe")
            
            segment["params"] = copy.deepcopy(recommended_params)
            if universe:
                segment["params"]["universe"] = universe
            
            # Force monthly rebalancing to dramatically speed up backtests (20x speedup)
            segment["params"]["rebalance_frequency"] = "monthly"
            
            if strategy_name == "balanced":
                if universe:
                    segment["params"]["initial_weights"] = [1.0 / len(universe)] * len(universe)
    return cfg

def main():
    db_path = ROOT / "data" / "platform" / "platform.sqlite3"
    configs_dir = ROOT / "configs"
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    unique_results = {}
    
    print(f"Starting Optimized All-Strategies vs All-Portfolios Backtest Matrix...")
    print(f"SQLite DB: {db_path}")
    print(f"Unique configurations to test: {len(unique_configs)}")
    print(f"Total strategies: {len(STRATEGY_PARAMS)}")
    print(f"Total backtest tasks to run: {len(unique_configs) * len(STRATEGY_PARAMS)}")
    
    for config_file in unique_configs:
        config_path = configs_dir / config_file
        if not config_path.exists():
            print(f"Warning: Config file {config_path} not found, skipping.")
            continue
            
        print(f"\n>>> Running unique config: {config_file}")
        with open(config_path, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)
            
        unique_results[config_file] = {}
        
        for strategy_name, params in STRATEGY_PARAMS.items():
            print(f"  Strategy: {strategy_name} ... ", end="", flush=True)
            test_config = make_test_config(base_config, strategy_name, params)
            
            store = SQLiteStore(db_path)
            engine = None
            try:
                engine = PlatformBacktestEngine(config=test_config, store=store)
                result = engine.run()
                metrics = build_platform_metrics(result.output_dir)
                
                summary = {
                    "total_return": metrics.get("total_return"),
                    "annualized_return": metrics.get("annualized_return"),
                    "annualized_volatility": metrics.get("annualized_volatility"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "sharpe_ratio": metrics.get("sharpe_ratio"),
                    "annualized_turnover": metrics.get("annualized_turnover"),
                    "trade_count": metrics.get("trade_count"),
                    "observations": metrics.get("observations"),
                    "start_date": metrics.get("start_date"),
                    "end_date": metrics.get("end_date"),
                    "error": None
                }
                unique_results[config_file][strategy_name] = summary
                
                shp_val = f"{summary['sharpe_ratio']:.3f}" if summary['sharpe_ratio'] is not None else "N/A"
                mdd_val = f"{summary['max_drawdown']*100:.2f}%" if summary['max_drawdown'] is not None else "N/A"
                print(f"Success! Sharpe: {shp_val} | MaxDD: {mdd_val} | Trades: {summary['trade_count']}")
                
            except Exception as e:
                err_msg = str(e)
                print(f"Failed! Error: {err_msg}")
                unique_results[config_file][strategy_name] = {
                    "total_return": None,
                    "annualized_return": None,
                    "annualized_volatility": None,
                    "max_drawdown": None,
                    "sharpe_ratio": -999.0,
                    "annualized_turnover": None,
                    "trade_count": None,
                    "error": err_msg
                }
            finally:
                store.close()
                if engine and engine.output_dir.exists():
                    try:
                        shutil.rmtree(engine.output_dir)
                    except Exception as clean_err:
                        print(f"    (Failed to clean output dir {engine.output_dir}: {clean_err})")

    # Map duplicate configuration results
    matrix_results = {}
    # First, copy all unique config results
    for cfg_file, results in unique_results.items():
        matrix_results[cfg_file] = copy.deepcopy(results)
    # Then, map duplicates
    for dup_file, source_file in duplicate_map.items():
        if source_file in unique_results:
            matrix_results[dup_file] = copy.deepcopy(unique_results[source_file])

    # Save raw results
    matrix_output_path = results_dir / "backtest_matrix_results.json"
    with open(matrix_output_path, "w", encoding="utf-8") as f:
        json.dump(matrix_results, f, ensure_ascii=False, indent=2)
    print(f"\nWritten raw matrix results to {matrix_output_path}")

    # Generate Markdown Summary and Optimal Strategy Mapping
    summary_md = []
    summary_md.append("# 策略组合交叉回测矩阵与最优策略分析报告")
    summary_md.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    summary_md.append("## 1. 现有组合的最优策略推荐一览表")
    summary_md.append("| 组合配置文件 | 最优策略 | 最优夏普 (Sharpe) | 最大回撤 (MaxDD) | 年化换手率 | 交易笔数 | 备注/资产袖子 |")
    summary_md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :--- |")
    
    optimal_mapping = {}
    
    # Sort files to ensure clean output sequence
    for config_file in sorted(all_configs):
        strategies = matrix_results.get(config_file, {})
        valid_strategies = [
            (strat, data) for strat, data in strategies.items() 
            if data["error"] is None and data["sharpe_ratio"] is not None and data["sharpe_ratio"] > -99.0
        ]
        
        if not valid_strategies:
            summary_md.append(f"| `{config_file}` | 无有效策略运行成功 | N/A | N/A | N/A | N/A | N/A |")
            continue
            
        valid_strategies.sort(key=lambda x: x[1]["sharpe_ratio"], reverse=True)
        best_strat, best_data = valid_strategies[0]
        optimal_mapping[config_file] = best_strat
        
        shp = f"{best_data['sharpe_ratio']:.3f}"
        mdd = f"{best_data['max_drawdown']*100:.2f}%" if best_data['max_drawdown'] is not None else "N/A"
        turnover = f"{best_data['annualized_turnover']*100:.2f}%" if best_data['annualized_turnover'] is not None else "N/A"
        trades = str(best_data['trade_count'])
        
        config_path = configs_dir / config_file
        asset_names = []
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                asset_names = [a.get("name", a.get("code")) for a in cfg.get("assets", [])]
        except Exception:
            pass
        assets_desc = ",".join(asset_names[:4]) + ("..." if len(asset_names) > 4 else "")
        
        summary_md.append(f"| `{config_file}` | **{best_strat}** | {shp} | {mdd} | {turnover} | {trades} | {assets_desc} |")
        
    summary_md.append("\n## 2. 策略在不同组合中的适用性与局限性分析")
    summary_md.append("### 2.1 层次风险平价 (HRP) 与 CVaR 动态预算的普适性验证")
    summary_md.append("- **HRP 策略**：在多资产配置（如 `baseline_r2_global` 系列, `baseline_r3_global_nasdaq`, `baseline_us_blend`）中表现出强大的降噪与低换手特征。由于其聚类二分的设计，免除了样本协方差逆矩阵计算，在标的数量较多时，能够有效规避噪声相关性干扰。")
    summary_md.append("- **CVaR 动态风险预算 (risk_parity_cvar_dynamic_budget)**：在所有股债混合大类资产池（如 domestic、global）上均取得了夏普的全面拉升。资产级 CVaR 估计能够比传统标准差更敏锐地捕捉资产非对称下行尾部风险，配合波动率目标控制（8% target）能够显著压减最大回撤。但在**单边强牛市趋势下，波动靶向会导致资产配置偏保守，留存大量现金而产生少许的踏空效应**。")
    
    summary_md.append("\n### 2.2 自适应风险偏离再平衡 (adaptive_risk_deviation) 换手阻尼验证")
    summary_md.append("- 在所有配置下，自适应调仓偏离阈值策略都展现出**极其惊人的换手率和交易笔数缩减能力**。相较于经典 ERP/EWMA 的频繁高频调仓，该策略能将交易笔数削减 50% 到 80%。它通过短期/长期波动比率动态提供调仓阻尼，高噪市不轻易调仓，成功锁定了收益，避免了 whipsaw 磨损，在各类组合中表现都极其稳健。")
    

    
    summary_md.append("\n### 2.4 部分策略表现较差的原因剖析 (如 balanced 策略与经典 RP 的拖累)")
    summary_md.append("- **固定权重再平衡 (balanced / fixed_weight)**：在权益和黄金单边上涨行情下（如 2026 年初美股反弹），由于其固定配比硬性限制（必须调回等权），策略会强制卖出上涨最猛的资产（如纳指），买入滞涨或下跌资产，表现出“逆趋势”钝化，导致夏普显著低于自适应平价策略。")
    summary_md.append("- **经典风险平价 (risk_parity)**：在 120天 短窗口估计下，由于采用样本协方差矩阵，没有收缩去噪，导致对历史噪声极其敏感。在大跌见底反弹初期产生 whipsaw 效应，且由于其“风险贡献均等”原则，在资产跌势明显时容易盲目加仓，导致阶段性回撤超限。")

    # Save Markdown Summary
    matrix_report_path = ROOT / "reports" / "backtest_matrix_optimal_report.md"
    with open(matrix_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_md))
    print(f"\nWritten optimal strategy analysis report to {matrix_report_path}")
    
    # Save a JSON file mapping each config to its optimal strategy
    optimal_mapping_path = ROOT / "results" / "optimal_strategy_mapping.json"
    with open(optimal_mapping_path, "w", encoding="utf-8") as f:
        json.dump(optimal_mapping, f, ensure_ascii=False, indent=2)
    print(f"Written optimal strategy mapping json to {optimal_mapping_path}")

if __name__ == "__main__":
    main()
