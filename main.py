import argparse
import os
import sys
import pandas as pd
from src.utils import load_config, setup_results_dir, save_config_snapshot, set_plot_style
from src.data_handler import DataHandler
from src.analysis.visualizer import BacktestVisualizer
from src.analysis.sensitivity import SensitivityAnalyzer
import importlib

def main():
    parser = argparse.ArgumentParser(description="回测系统启动入口")
    parser.add_argument("--config", type=str, default="configs/default.yaml", help="配置文件路径")
    parser.add_argument("--strategy", type=str, help="覆盖配置文件中的策略名称（可选）")
    parser.add_argument("--plot", "-p", action="store_true", help="是否生成可视化图表")
    parser.add_argument("--sensitivity", "-s", action="store_true", help="是否运行起始日敏感度分析")
    args = parser.parse_args()

    # 1. 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        sys.exit(1)

    if args.strategy:
        config['strategy']['name'] = args.strategy

    strategy_name = config['strategy']['name']
    print(f"=== 正在运行策略: {strategy_name} ===")

    # 2. 加载数据
    assets = config['backtest']['assets']
    codes = [asset['code'] for asset in assets]
    handler = DataHandler()
    
    try:
        df = handler.load_etf_data(codes, auto_fetch=True)
        print(f"数据加载成功，交易日范围: {df.index.min().date()} 至 {df.index.max().date()}")
        print(f"有效回测天数: {len(df)}\n")
    except Exception as e:
        print(f"数据加载失败: {e}")
        sys.exit(1)

    # 3. 动态加载并运行策略
    try:
        strategy_module = importlib.import_module(f"src.strategies.{strategy_name}")
        res_df, trades_df, metrics = strategy_module.run_strategy(df, config)
    except ImportError:
        print(f"找不到策略模块: {strategy_name}，请检查 src/strategies/{strategy_name}.py 是否存在。")
        sys.exit(1)
    except Exception as e:
        print(f"运行策略时发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 4. 输出指标
    print("--- 策略表现指标 ---")
    print(f"累计收益率: {metrics['total_return'] * 100:.2f}%")
    print(f"年化收益率: {metrics['annualized_return'] * 100:.2f}%")
    print(f"最大回撤: {metrics['max_drawdown'] * 100:.2f}%")
    print(f"夏普比率: {metrics['sharpe_ratio']:.4f}")
    print(f"总计资产交易笔数: {len(trades_df)}\n")

    # 5. 保存结果
    results_dir = setup_results_dir(strategy_name, config['output'].get('results_dir', 'results'))
    save_config_snapshot(config, results_dir)
    res_df.to_csv(results_dir / "backtest_results.csv")
    trades_df.to_csv(results_dir / "trade_history.csv")
    
    # 6. 可视化 (可选)
    if args.plot or config['output'].get('save_plots', False):
        print("正在生成可视化图表...")
        visualizer = BacktestVisualizer(results_dir)
        visualizer.plot_performance_summary(res_df, strategy_name)
        visualizer.plot_asset_allocation(res_df)
    
    # 7. 敏感度分析 (可选)
    if args.sensitivity:
        print("\n--- 正在运行敏感度分析 ---")
        analyzer = SensitivityAnalyzer(strategy_name, config)
        sensitivity_df = analyzer.run_analysis(df, step_size=20) # 默认步长 20
        if not sensitivity_df.empty:
            sensitivity_df.to_csv(results_dir / "sensitivity_summary.csv")
            if args.plot or config['output'].get('save_plots', False):
                visualizer = BacktestVisualizer(results_dir)
                visualizer.plot_sensitivity_results(sensitivity_df)
            print(f"敏感度分析完成，保存至: {results_dir / 'sensitivity_summary.csv'}")

    print(f"\n回测任务全部完成。结果已保存至: {results_dir}")

if __name__ == "__main__":
    # 确保当前路径在系统路径中以方便加载 src
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.append(current_dir)
        
    main()
