import pandas as pd
import numpy as np
from typing import List, Tuple

def run_backtest(df: pd.DataFrame, 
                 initial_weights: List[float] = [1/3, 1/3, 1/3],
                 rebalance_threshold: float = 0.05,
                 commission: float = 0.0002) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    运行三等分动态平衡策略回测
    
    Args:
        df: 包含各资产后复权收盘价的 DataFrame
        initial_weights: 初始权重
        rebalance_threshold: 再平衡偏离阈值 (5%)
        commission: 手续费率 (0.02%)
        
    Returns:
        pd.DataFrame: 包含每日净值和权重的 DataFrame
        pd.DataFrame: 包含调仓记录的 DataFrame
    """
    # 计算日收益率
    returns = df.pct_change().fillna(0)
    
    # 初始化
    asset_names = df.columns.tolist()
    n_assets = len(asset_names)
    weights = np.array(initial_weights)
    
    portfolio_values = []
    daily_weights = []
    trades = []
    
    current_value = 1.0
    total_commission = 0.0
    
    # 获取季度末日期（每个季度的最后一个交易日）
    # 使用 resample('QE') 获取每个季度的最大索引日期
    quarter_ends = df.index.to_series().resample('QE').max().tolist()
    
    for date, row_rets in returns.iterrows():
        # 1. 计算当日资产价值变化 (当日收盘前)
        # 假设 weights 是今天开盘时的持仓权重
        # asset_values = 上日价值 * (1 + 今日收益)
        # 这里为了简化向量化思路中的逻辑，我们维护 current_value
        
        asset_values = current_value * weights * (1 + row_rets.values)
        current_value = asset_values.sum()
        
        # 计算当前实际权重
        actual_weights = asset_values / current_value
        
        # 检查是否是季度末，且是否触发阈值
        is_rebalance_day = date in quarter_ends
        triggered = False
        trade_fee = 0.0
        
        if is_rebalance_day:
            # 检查偏离
            deviation = np.abs(actual_weights - (1/n_assets))
            if np.any(deviation > rebalance_threshold):
                # 触发再平衡
                triggered = True
                target_weights = np.ones(n_assets) / n_assets
                # 计算换手量：目标价值与当前价值的差值的绝对值之和
                # 实际上卖出和买入都会产生手续费 (双边)
                trade_volume = np.sum(np.abs(target_weights * current_value - asset_values))
                trade_fee = trade_volume * commission
                
                # 扣除手续费
                current_value -= trade_fee
                total_commission += trade_fee
                
                # 更新权重为目标权重
                weights = target_weights
                
                trades.append({
                    'date': date,
                    'before_weights': actual_weights.tolist(),
                    'trade_volume': trade_volume,
                    'fee': trade_fee
                })
            else:
                # 未触发，继续持有当前实际分布
                weights = actual_weights
        else:
            # 非调仓日，权重自然飘移
            weights = actual_weights
            
        # 记录每日状态
        portfolio_values.append(current_value)
        daily_weights.append(weights.tolist())
        
    # 转换为 DataFrame
    result_df = pd.DataFrame({
        'net_value': portfolio_values
    }, index=df.index)
    
    weights_df = pd.DataFrame(daily_weights, columns=[f'w_{c}' for c in asset_names], index=df.index)
    result_df = pd.concat([result_df, weights_df], axis=1)
    
    trades_df = pd.DataFrame(trades)
    
    return result_df, trades_df

if __name__ == "__main__":
    from data_loader import load_etf_data
    codes = ['510300', '518880', '511260']
    df = load_etf_data(codes)
    res, trades = run_backtest(df)
    print("回测净值前 5 行：")
    print(res.head())
    print(f"\n总计调仓次数: {len(trades)}")
    print(f"累计手续费损耗: {trades['fee'].sum() if not trades.empty else 0:.6f}")
