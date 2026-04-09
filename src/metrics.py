import numpy as np
import pandas as pd

def calculate_metrics(net_value: pd.Series, rf=0.02):
    """
    根据净值曲线计算核心绩效指标
    """
    # 1. 累计收益率
    total_return = net_value.iloc[-1] / net_value.iloc[0] - 1
    
    # 2. 年化收益率
    days = (net_value.index[-1] - net_value.index[0]).days
    annualized_return = (1 + total_return) ** (365 / days) - 1
    
    # 3. 最大回撤
    peak = net_value.expanding(min_periods=1).max()
    drawdown = (net_value - peak) / peak
    max_drawdown = drawdown.min()
    
    # 4. 夏普比率 (假设一年 252 个交易日)
    daily_returns = net_value.pct_change().dropna()
    excess_return = annualized_return - rf
    volatility = daily_returns.std() * np.sqrt(252)
    sharpe_ratio = excess_return / volatility if volatility != 0 else 0.0
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'volatility': volatility
    }
