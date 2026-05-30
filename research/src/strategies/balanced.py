import pandas as pd
from src.engine import BacktestEngine
from src.metrics import calculate_metrics

def run_strategy(df: pd.DataFrame, config: dict):
    """
    运行均衡再平衡策略
    """
    params = config['strategy']['params']
    
    # 提取回测参数
    initial_weights = params['initial_weights']
    rebalance_threshold = params['rebalance_threshold']
    commission = params['commission']
    
    # 1. 运行核心回测
    res_df, trades_df = BacktestEngine.run_standard_rebalance(
        df, 
        initial_weights, 
        rebalance_threshold, 
        commission
    )
    
    # 2. 计算指标
    metrics = calculate_metrics(res_df['net_value'])
    
    return res_df, trades_df, metrics
