import numpy as np
import pandas as pd

from src.metrics import calculate_metrics


def run_strategy(df: pd.DataFrame, config: dict):
    """
    Risk parity variant that uses exponentially weighted volatility
    instead of a simple rolling standard deviation.
    """
    params = config["strategy"]["params"]
    ewma_span = params.get("ewma_span", 60)
    ewma_min_periods = params.get("ewma_min_periods", 20)
    rebalance_threshold = params.get("rebalance_threshold", 0.05)
    commission = params.get("commission", 0.0002)
    initial_weights = params.get("initial_weights", [0.15, 0.25, 0.60])
    init_mode = params.get("init_mode", "manual")
    init_calc_days = params.get("init_calc_days", 30)

    returns = df.pct_change()

    # Use exponentially weighted volatility so recent risk shifts have
    # more influence than distant history while keeping the interface stable.
    ewma_vol = returns.ewm(span=ewma_span, min_periods=ewma_min_periods, adjust=False).std() * np.sqrt(252)

    asset_names = df.columns.tolist()
    inv_vol = 1.0 / ewma_vol.replace(0, np.nan)
    target_weights_df = inv_vol.div(inv_vol.sum(axis=1), axis=0)

    if init_mode == "manual":
        for i, col in enumerate(target_weights_df.columns):
            target_weights_df[col] = target_weights_df[col].fillna(initial_weights[i])

    portfolio_values = []
    actual_weights_list = []
    trades = []

    current_value = 1.0
    is_opened = False
    if init_mode == "manual":
        weights = np.array(initial_weights)
        is_opened = True
    else:
        weights = np.zeros(len(asset_names))

    quarter_ends = df.index.to_series().resample("QE").max().tolist()
    returns_filled = returns.fillna(0)

    for i, (date, row_rets) in enumerate(returns_filled.iterrows()):
        if not is_opened and i >= init_calc_days:
            target_w = target_weights_df.loc[date].values
            if not np.any(np.isnan(target_w)):
                total_trade_vol = current_value
                trade_fee = total_trade_vol * commission

                for idx, asset in enumerate(asset_names):
                    target_val = target_w[idx] * current_value
                    if target_val > 1e-6:
                        price = df.loc[date, asset]
                        asset_fee = target_val * commission
                        trades.append(
                            {
                                "date": date,
                                "asset": asset,
                                "side": "BUY",
                                "price": price,
                                "trade_value": target_val,
                                "trade_volume": target_val / price if price > 0 else 0,
                                "fee": asset_fee,
                                "weight_before": 0.0,
                                "weight_after": target_w[idx],
                            }
                        )

                current_value -= trade_fee
                weights = target_w
                is_opened = True

        asset_values = current_value * weights * (1 + row_rets.values)
        current_value = asset_values.sum()

        if is_opened:
            actual_weights = asset_values / current_value if current_value > 0 else weights
            is_rebalance_day = date in quarter_ends

            if is_rebalance_day:
                target_w = target_weights_df.loc[date].values
                if not np.any(np.isnan(target_w)):
                    deviation = np.abs(actual_weights - target_w)
                    if np.any(deviation > rebalance_threshold):
                        for idx, asset in enumerate(asset_names):
                            prev_w = actual_weights[idx]
                            new_w = target_w[idx]
                            prev_val = asset_values[idx]
                            target_val = new_w * current_value
                            diff_val = target_val - prev_val

                            if abs(diff_val) > 1e-6:
                                side = "BUY" if diff_val > 0 else "SELL"
                                asset_fee = abs(diff_val) * commission
                                price = df.loc[date, asset]
                                trades.append(
                                    {
                                        "date": date,
                                        "asset": asset,
                                        "side": side,
                                        "price": price,
                                        "trade_value": abs(diff_val),
                                        "trade_volume": abs(diff_val) / price if price > 0 else 0,
                                        "fee": asset_fee,
                                        "weight_before": prev_w,
                                        "weight_after": new_w,
                                    }
                                )

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
            current_value = 1.0
            weights = np.zeros(len(asset_names))

        portfolio_values.append(current_value)
        actual_weights_list.append(weights.tolist())

    result_df = pd.DataFrame({"net_value": portfolio_values}, index=df.index)
    weights_cols = [f"w_{code}" for code in asset_names]
    weights_df = pd.DataFrame(actual_weights_list, columns=weights_cols, index=df.index)
    result_df = pd.concat([result_df, weights_df], axis=1)

    trades_df = pd.DataFrame(trades)
    metrics = calculate_metrics(result_df["net_value"])

    return result_df, trades_df, metrics
