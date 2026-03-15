import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data_loader import load_etf_data
from metrics import calculate_metrics

def run_iv_risk_parity_backtest(
    df: pd.DataFrame,
    rolling_window: int = 120,
    rebalance_threshold: float = 0.05,
    commission: float = 0.0002
):
    """
    运行倒数波动率风险平价策略回测
    """
    # 1. 计算日收益率
    returns = df.pct_change()
    
    # 2. 计算滚动波动率 (年化)
    # 设定 min_periods=20，使得在 20 个交易日后就开始有动态权重
    rolling_vol = returns.rolling(window=rolling_window, min_periods=20).std() * np.sqrt(252)
    
    # 3. 计算动态目标权重
    asset_names = df.columns.tolist()
    # 目标权重 = (1/vol) / sum(1/vol)
    inv_vol = 1.0 / rolling_vol
    target_weights_df = inv_vol.div(inv_vol.sum(axis=1), axis=0)
    
    # 初始权重配置: [沪深300, 黄金, 长债] = [0.15, 0.25, 0.60]
    initial_weights = [0.15, 0.25, 0.60]
    
    # 波动率为 NaN 的期间使用初始权重过渡
    for i, col in enumerate(target_weights_df.columns):
        target_weights_df[col] = target_weights_df[col].fillna(initial_weights[i])
    
    # 4. 模拟交易逻辑
    portfolio_values = []
    actual_weights_list = []
    trades = []
    
    current_value = 1.0
    # 初始权重设为配置的初始权重
    weights = np.array(initial_weights)
    
    # 获取季度末日期
    quarter_ends = df.index.to_series().resample('QE').max().tolist()
    
    # 填充收益率为 0 防止计算错误
    returns_filled = returns.fillna(0)
    
    for date, row_rets in returns_filled.iterrows():
        # 计算当日收盘前的资产价值变化
        # asset_values = 上日价值 * (1 + 今日收益)
        asset_values = current_value * weights * (1 + row_rets.values)
        current_value = asset_values.sum()
        
        # 计算当前实际权重 (自然飘移后)
        actual_weights = asset_values / current_value
        
        # 检查是否是季度末，且是否触发阈值
        is_rebalance_day = date in quarter_ends
        
        if is_rebalance_day:
            # 获取当天的目标权重
            target_w = target_weights_df.loc[date].values
            
            # 检查偏离
            deviation = np.abs(actual_weights - target_w)
            if np.any(deviation > rebalance_threshold):
                # 触发再平衡
                # 计算换手量 (双边)
                trade_volume = np.sum(np.abs(target_w * current_value - asset_values))
                trade_fee = trade_volume * commission
                
                # 扣除手续费
                current_value -= trade_fee
                
                # 更新权重为目标权重
                weights = target_w
                
                trades.append({
                    'date': date,
                    'trade_volume': trade_volume,
                    'fee': trade_fee
                })
            else:
                # 未触发，保持当前实际权重
                weights = actual_weights
        else:
            # 非调仓日，权重天然飘移
            weights = actual_weights
            
        # 记录每日状态
        portfolio_values.append(current_value)
        actual_weights_list.append(weights.tolist())
        
    # 5. 结果整理
    result_df = pd.DataFrame({'net_value': portfolio_values}, index=df.index)
    weights_cols = [f'w_{c}' for c in asset_names]
    weights_df = pd.DataFrame(actual_weights_list, columns=weights_cols, index=df.index)
    result_df = pd.concat([result_df, weights_df], axis=1)
    
    trades_df = pd.DataFrame(trades)
    
    return result_df, trades_df, target_weights_df

def plot_results(result_df, target_weights_df, asset_names):
    """
    绘制净值曲线和目标权重面积图
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
    plt.rcParams['font.sans-serif'] = ['SimHei'] # 支持中文
    plt.rcParams['axes.unicode_minus'] = False
    
    # 子图1: 净值曲线
    ax1.plot(result_df.index, result_df['net_value'], label='策略净值', color='#1f77b4', linewidth=2)
    ax1.set_title('倒数波动率风险平价策略 - 净值曲线', fontsize=14)
    ax1.set_ylabel('净值')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 子图2: 目标权重面积图
    # 这里的 target_weights_df 是每日计算出来的目标权重
    # 我们用 stacked area chart 展示
    ax2.stackplot(target_weights_df.index, 
                 [target_weights_df[col] for col in asset_names],
                 labels=asset_names,
                 alpha=0.7)
    ax2.set_title('动态目标权重分配 (120日滚动波动率倒数)', fontsize=12)
    ax2.set_ylabel('权重占比')
    ax2.set_ylim(0, 1.0)
    ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('iv_risk_parity_results.png', dpi=300)
    print("图表已保存至 iv_risk_parity_results.png")
    plt.show()

if __name__ == "__main__":
    # 配置
    codes = ['510300', '518880', '511260']
    names = ['沪深300', '黄金ETF', '十年国债ETF'] # 用于展示
    
    # 1. 加载数据
    df = load_etf_data(codes)
    # 重命名列方便理解
    df.columns = names
    
    # 2. 运行回测
    res, trades, target_w = run_iv_risk_parity_backtest(df)
    
    # 3. 计算指标
    metrics = calculate_metrics(res['net_value'])
    
    print("\n--- 策略表现 (Inverse Volatility Risk Parity) ---")
    print(f"年化收益率: {metrics['annualized_return']:.2%}")
    print(f"最大回撤: {metrics['max_drawdown']:.2%}")
    print(f"夏普比率 (RF=2.0%): {metrics['sharpe_ratio']:.2f}")
    print(f"总手续费损耗: {trades['fee'].sum() if not trades.empty else 0:.6f}")
    print(f"调仓次数: {len(trades)}")
    
    # 4. 绘图
    plot_results(res, target_w, names)
