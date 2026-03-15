import finshare as fs
import pandas as pd
import pathlib
from datetime import datetime

# Target ETF codes
# 510310: 易方达沪深300发起式ETF
# 518880: 华安黄金ETF
# 511130: 博时上证30年期国债ETF
# 511260: 十年国债ETF
CODES = ['510300', '510310', '518880', '511130', '511260']

def main():
    # Use an early start date to fetch maximum history
    start_str = '1990-01-01'
    end_str = datetime.now().strftime('%Y-%m-%d')

    # Ensure data directory exists
    data_dir = pathlib.Path('./data')
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching max history data from {start_str} to {end_str}")

    for code in CODES:
        print(f"\nProcessing {code}...")
        try:
            fs_code = f"{code}.SH"
            
            # Fetch Unadjusted, QFQ, and HFQ data
            df_unadj = fs.get_historical_data(fs_code, start=start_str, end=end_str, adjust=None)
            df_qfq = fs.get_historical_data(fs_code, start=start_str, end=end_str, adjust='qfq')
            df_hfq = fs.get_historical_data(fs_code, start=start_str, end=end_str, adjust='hfq')
            
            if df_unadj is not None and not df_unadj.empty:
                # Save maximum unadjusted data
                data_dir.mkdir(parents=True, exist_ok=True)
                df_unadj.to_csv(data_dir / f"{code}.csv", index=False)
                df_unadj.to_parquet(data_dir / f"{code}.parquet", index=False)
                print(f"[{code}] Saved max unadjusted data. Shape: {df_unadj.shape}")

                # Calculate and save QFQ factors
                if df_qfq is not None and not df_qfq.empty:
                    qfq_merged = pd.merge(df_unadj[['trade_date', 'close_price']], 
                                          df_qfq[['trade_date', 'close_price']], 
                                          on='trade_date', suffixes=('_unadj', '_qfq'))
                    qfq_merged['qfq_factor'] = qfq_merged['close_price_qfq'] / qfq_merged['close_price_unadj']
                    qfq_df = qfq_merged[['trade_date', 'qfq_factor']]
                    qfq_df.to_csv(data_dir / f"{code}_qfq_factor.csv", index=False)
                    qfq_df.to_parquet(data_dir / f"{code}_qfq_factor.parquet", index=False)
                    print(f"[{code}] Saved forward adjustment factors (QFQ).")

                # Calculate and save HFQ factors
                if df_hfq is not None and not df_hfq.empty:
                    hfq_merged = pd.merge(df_unadj[['trade_date', 'close_price']], 
                                          df_hfq[['trade_date', 'close_price']], 
                                          on='trade_date', suffixes=('_unadj', '_hfq'))
                    hfq_merged['hfq_factor'] = hfq_merged['close_price_hfq'] / hfq_merged['close_price_unadj']
                    hfq_df = hfq_merged[['trade_date', 'hfq_factor']]
                    hfq_df.to_csv(data_dir / f"{code}_hfq_factor.csv", index=False)
                    hfq_df.to_parquet(data_dir / f"{code}_hfq_factor.parquet", index=False)
                    print(f"[{code}] Saved backward adjustment factors (HFQ).")
            else:
                print(f"[{code}] Warning: Failed to fetch unadjusted data.")
        except Exception as e:
            print(f"[{code}] Error fetching data: {e}")

if __name__ == "__main__":
    main()
