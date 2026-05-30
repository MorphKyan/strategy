import pandas as pd
import numpy as np
from src.metrics import calculate_metrics

def run_strategy(df: pd.DataFrame, config: dict):
    """
    运行倒数波动率风险平价策略
    """
    params = config['strategy']['params']
    rolling_window = params.get('rolling_window', 120)
    rebalance_threshold = params.get('rebalance_threshold', 0.05)
    commission = params.get('commission', 0.0002)
    initial_weights = params.get('initial_weights', [0.15, 0.25, 0.60])
    init_mode = params.get('init_mode', 'manual')
    init_calc_days = params.get('init_calc_days', 30)
    
    # 1. 计算日收益率
    returns = df.pct_change()
    
    # 2. 计算滚动波动率 (年化)
    rolling_vol = returns.rolling(window=rolling_window, min_periods=20).std() * np.sqrt(252)
    
    # 3. 计算动态目标权重
    asset_names = df.columns.tolist()
    inv_vol = 1.0 / rolling_vol
    target_weights_df = inv_vol.div(inv_vol.sum(axis=1), axis=0)
    
    # 填充 NaN 为初始权重 (仅 manual 模式使用)
    if init_mode == 'manual':
        for i, col in enumerate(target_weights_df.columns):
            target_weights_df[col] = target_weights_df[col].fillna(initial_weights[i])
    
    # 4. 模拟交易逻辑 (风险平价逻辑较为特殊，暂时放在各策略内部)
    portfolio_values = []
    actual_weights_list = []
    trades = []
    
    current_value = 1.0
    is_opened = False
    if init_mode == 'manual':
        weights = np.array(initial_weights)
        is_opened = True
    else:
        weights = np.zeros(len(asset_names))
        
    quarter_ends = df.index.to_series().resample('QE').max().tolist()
    returns_filled = returns.fillna(0)
    
    for i, (date, row_rets) in enumerate(returns_filled.iterrows()):
        # 如果未建仓且达到观察期
        if not is_opened and i >= init_calc_days:
            target_w = target_weights_df.loc[date].values
            if not np.any(np.isnan(target_w)):
                # 执行首次建仓
                total_trade_vol = current_value # 初始全部买入
                trade_fee = total_trade_vol * commission
                
                for idx, asset in enumerate(asset_names):
                    target_val = target_w[idx] * current_value
                    if target_val > 1e-6:
                        price = df.loc[date, asset]
                        asset_fee = target_val * commission
                        trades.append({
                            'date': date,
                            'asset': asset,
                            'side': 'BUY',
                            'price': price,
                            'trade_value': target_val,
                            'trade_volume': target_val / price if price > 0 else 0,
                            'fee': asset_fee,
                            'weight_before': 0.0,
                            'weight_after': target_w[idx]
                        })
                
                current_value -= trade_fee
                weights = target_w
                is_opened = True
        
        # 计算当前净值
        asset_values = current_value * weights * (1 + row_rets.values)
        current_value = asset_values.sum()
        
        # 如果已建仓，则维持或调整权重
        if is_opened:
            actual_weights = asset_values / current_value if current_value > 0 else weights
            
            is_rebalance_day = date in quarter_ends
            if is_rebalance_day:
                target_w = target_weights_df.loc[date].values
                if not np.any(np.isnan(target_w)):
                    deviation = np.abs(actual_weights - target_w)
                    if np.any(deviation > rebalance_threshold):
                        # 记录明细交易
                        for idx, asset in enumerate(asset_names):
                            prev_w = actual_weights[idx]
                            t_w = target_w[idx]
                            
                            prev_val = asset_values[idx]
                            target_val = t_w * current_value
                            diff_val = target_val - prev_val
                            
                            if abs(diff_val) > 1e-6:
                                side = 'BUY' if diff_val > 0 else 'SELL'
                                asset_fee = abs(diff_val) * commission
                                price = df.loc[date, asset]
                                
                                trades.append({
                                    'date': date,
                                    'asset': asset,
                                    'side': side,
                                    'price': price,
                                    'trade_value': abs(diff_val),
                                    'trade_volume': abs(diff_val) / price if price > 0 else 0,
                                    'fee': asset_fee,
                                    'weight_before': prev_w,
                                    'weight_after': t_w
                                })

                        total_trade_vol = np.sum(np.abs(target_w * current_value - asset_values))
                        current_value -= total_trade_vol * commission
                        weights = target_w
                    else:
                        weights = actual_weights
                else:
                    weights = actual_weights
            else:
                weights = actual_weights
        else:
            # 未建仓期间，资产价值不变（全现金）
            current_value = 1.0
            weights = np.zeros(len(asset_names))
            
        portfolio_values.append(current_value)
        actual_weights_list.append(weights.tolist())
        
    result_df = pd.DataFrame({'net_value': portfolio_values}, index=df.index)
    weights_cols = [f'w_{c}' for c in asset_names]
    weights_df = pd.DataFrame(actual_weights_list, columns=weights_cols, index=df.index)
    result_df = pd.concat([result_df, weights_df], axis=1)
    
    trades_df = pd.DataFrame(trades)
    metrics = calculate_metrics(result_df['net_value'])
    
    return result_df, trades_df, metrics
