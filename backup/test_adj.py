import finshare as fs
import pandas as pd

def main():
    code = '510310.SH'
    print("--- Testing get_historical_data with start=1990-01-01 ---")
    df_none = fs.get_historical_data(code, start='1990-01-01', adjust=None)
    
    if df_none is not None:
        print(f"Unadjusted data shape: {df_none.shape}")
        print(f"Min date: {df_none['trade_date'].min()}, Max date: {df_none['trade_date'].max()}")
        print(f"Columns: {df_none.columns.tolist()}")

    df_qfq = fs.get_historical_data(code, start='1990-01-01', adjust='qfq')
    if df_qfq is not None:
        print(f"QFQ data shape: {df_qfq.shape}")
        
    print("\n--- Testing get_dividend ---")
    try:
        div = fs.get_dividend(code)
        if div is not None:
            print(f"Dividend data shape: {div.shape}")
            print(div.head())
        else:
            print("Dividend returned None")
    except Exception as e:
        print(f"Error calling get_dividend: {e}")

if __name__ == "__main__":
    main()
