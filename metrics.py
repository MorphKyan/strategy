import pandas as pd
import numpy as np

def calculate_metrics(net_value_series: pd.Series, risk_free_rate: float = 0.02) -> dict:
    """
    计算量化评价指标
    
    Args:
        net_value_series: 净值曲线 Series
        risk_free_rate: 年化无风险利率 (默认 2.0%)
        
    Returns:
        dict: 包含各项指标的字典
    """
    # 1. 计算日收益率
    daily_returns = net_value_series.pct_change().dropna()
    
    # 2. 累计受益
    total_return = net_value_series.iloc[-1] / net_value_series.iloc[0] - 1
    
    # 3. 年化收益率
    # 假设一年 252 个交易日
    total_days = len(net_value_series)
    annualized_return = (1 + total_return) ** (252 / total_days) - 1
    
    # 4. 最大回撤
    cumulative_max = net_value_series.cummax()
    drawdown = (net_value_series - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    
    # 5. 夏普比率
    # 每日无风险利率
    daily_rf = risk_free_rate / 252
    excess_returns = daily_returns - daily_rf
    if daily_returns.std() != 0:
        sharpe_ratio = (excess_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0
        
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio
    }

if __name__ == "__main__":
    # 模拟数据测试
    dates = pd.date_range('2020-01-01', periods=500)
    # 模拟一个稍微向上走的曲线
    mock_nv = pd.Series(np.cumprod(1 + np.random.normal(0.0005, 0.01, 500)), index=dates)
    metrics = calculate_metrics(mock_nv)
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")
