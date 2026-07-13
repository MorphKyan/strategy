# -*- coding: utf-8 -*-
"""
Generate a synthetic 3x leveraged ETF for the 10-year Treasury ETF (511260)
to simulate 30-year Treasury futures in risk parity backtesting.
The leverage is applied to the fully adjusted (HFQ) price returns to properly
account for dividends/splits.
"""
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def generate_3x_etf():
    data_dir = ROOT / "data"
    input_price_path = data_dir / "511260.csv"
    input_factor_path = data_dir / "511260_hfq_factor.csv"
    
    output_price_path = data_dir / "511260_3X.csv"
    output_factor_path = data_dir / "511260_3X_hfq_factor.csv"
    
    if not input_price_path.exists() or not input_factor_path.exists():
        print(f"Error: Input files not found in {data_dir}")
        return 1
        
    prices_df = pd.read_csv(input_price_path)
    factors_df = pd.read_csv(input_factor_path)
    
    # Sort by trade_date
    prices_df = prices_df.sort_values("trade_date").reset_index(drop=True)
    factors_df = factors_df.sort_values("trade_date").reset_index(drop=True)
    
    # Merge on trade_date and ffill factor
    df = pd.merge(prices_df, factors_df, on="trade_date", how="left")
    df["hfq_factor"] = df["hfq_factor"].ffill().fillna(1.0)
    
    # Calculate fully adjusted (HFQ) price columns
    df["adj_close"] = df["close"] * df["hfq_factor"]
    df["adj_open"] = df["open"] * df["hfq_factor"]
    df["adj_high"] = df["high"] * df["hfq_factor"]
    df["adj_low"] = df["low"] * df["hfq_factor"]
    
    # Prepare lists for 3x leveraged prices
    sim_close = []
    sim_open = []
    sim_high = []
    sim_low = []
    
    # Day 0 initialization: Use the first day's adjusted prices directly
    first_row = df.iloc[0]
    sim_close.append(first_row["adj_close"])
    sim_open.append(first_row["adj_open"])
    sim_high.append(first_row["adj_high"])
    sim_low.append(first_row["adj_low"])
    
    for i in range(1, len(df)):
        prev_adj_close = df.loc[i-1, "adj_close"]
        curr_adj_close = df.loc[i, "adj_close"]
        curr_adj_open = df.loc[i, "adj_open"]
        curr_adj_high = df.loc[i, "adj_high"]
        curr_adj_low = df.loc[i, "adj_low"]
        
        prev_sim_close = sim_close[-1]
        
        # 1. Close price return (overnight + intraday)
        r_close = curr_adj_close / prev_adj_close - 1.0
        r_close_3x = 3.0 * r_close
        curr_sim_close = prev_sim_close * (1.0 + r_close_3x)
        
        # 2. Open price return (overnight gap relative to previous close)
        r_open = curr_adj_open / prev_adj_close - 1.0
        r_open_3x = 3.0 * r_open
        curr_sim_open = prev_sim_close * (1.0 + r_open_3x)
        
        # 3. High price return relative to open
        r_high = curr_adj_high / curr_adj_open - 1.0
        r_high_3x = 3.0 * r_high
        curr_sim_high = curr_sim_open * (1.0 + r_high_3x)
        
        # 4. Low price return relative to open
        r_low = curr_adj_low / curr_adj_open - 1.0
        r_low_3x = 3.0 * r_low
        curr_sim_low = curr_sim_open * (1.0 + r_low_3x)
        
        sim_close.append(curr_sim_close)
        sim_open.append(curr_sim_open)
        sim_high.append(curr_sim_high)
        sim_low.append(curr_sim_low)
        
    df["close"] = sim_close
    df["open"] = sim_open
    df["high"] = sim_high
    df["low"] = sim_low
    
    # Clean up df to match original CSV structure
    df["adjust_factor"] = 1.0
    df["source"] = "simulated"
    df["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    
    output_cols = ["trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor", "source", "updated_at"]
    # 稳定写盘：派生数据未变的行保留原 updated_at，内容一致时不动文件，
    # 避免每次同步都全文件重写（数千行假 diff）
    from src.platform_core.data_store import write_csv_stable

    write_csv_stable(output_price_path, df[output_cols], key_column="trade_date")

    # Save adjust factor file (always 1.0 since prices are pre-adjusted)
    factors_out = pd.DataFrame({
        "trade_date": df["trade_date"],
        "hfq_factor": 1.0
    })
    write_csv_stable(output_factor_path, factors_out, key_column="trade_date")
    
    print(f"Successfully generated synthetic 3x ETF:")
    print(f"- Prices saved to: {output_price_path}")
    print(f"- HFQ factor saved to: {output_factor_path}")
    print(f"- Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
    print(f"- Total rows: {len(df)}")
    return 0

if __name__ == "__main__":
    sys.exit(generate_3x_etf())
