import pandas as pd
import numpy as np

class BacktestEngine:
    @staticmethod
    def run_standard_rebalance(
        df: pd.DataFrame, 
        initial_weights: list, 
        rebalance_threshold: float = 0.05, 
        commission: float = 0.0002
    ):
        """
        运行标准再平衡策略（如三等分平衡）
        """
        returns = df.pct_change().fillna(0)
        portfolio_values = []
        actual_weights_list = []
        trades = []
        
        current_value = 1.0
        weights = np.array(initial_weights)
        asset_names = df.columns.tolist()
        
        for date, row_rets in returns.iterrows():
            # 计算当日资产价值变化
            asset_values = current_value * weights * (1 + row_rets.values)
            current_value = asset_values.sum()
            
            # 自然飘移后的实际权重
            actual_weights = asset_values / current_value
            
            # 检查偏离是否触发再平衡
            deviation = np.abs(actual_weights - np.array(initial_weights))
            if np.any(deviation > rebalance_threshold):
                # 触发调仓：回到初始配置
                target_weights = np.array(initial_weights)
                
                for idx, asset in enumerate(asset_names):
                    prev_w = actual_weights[idx]
                    target_w = target_weights[idx]
                    
                    prev_val = asset_values[idx]
                    target_val = target_w * current_value
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
                            'weight_after': target_w
                        })
                
                # 更新总净值（扣除总手续费）
                total_trade_vol = np.sum(np.abs(target_weights * current_value - asset_values))
                current_value -= total_trade_vol * commission
                weights = target_weights
            else:
                weights = actual_weights
                
            portfolio_values.append(current_value)
            actual_weights_list.append(weights.tolist())
            
        res_df = pd.DataFrame({'net_value': portfolio_values}, index=df.index)
        weights_cols = [f'w_{c}' for c in asset_names]
        weights_df = pd.DataFrame(actual_weights_list, columns=weights_cols, index=df.index)
        res_df = pd.concat([res_df, weights_df], axis=1)
        
        trades_df = pd.DataFrame(trades)
        return res_df, trades_df
