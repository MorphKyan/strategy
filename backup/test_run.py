import finshare as fs
from datetime import datetime

def main():
    code = '510310.SH'
    start = '1990-01-01'
    end = datetime.now().strftime('%Y-%m-%d')
    
    with open('test_output.txt', 'w') as f:
        f.write("--- get_historical_data (no adjust) ---\n")
        try:
            df = fs.get_historical_data(code, start=start, end=end, adjust=None)
            if df is not None:
                f.write(f"Shape: {df.shape}\n")
                f.write(f"Min Date: {df['trade_date'].min()}\n")
                f.write(f"Max Date: {df['trade_date'].max()}\n")
            else:
                f.write("Returned None\n")
        except Exception as e:
            f.write(f"Error: {e}\n")
            
        f.write("\n--- get_historical_data (qfq) ---\n")
        try:
            df_qfq = fs.get_historical_data(code, start=start, end=end, adjust='qfq')
            if df_qfq is not None:
                f.write(f"Shape: {df_qfq.shape}\n")
                f.write(f"Min Date: {df_qfq['trade_date'].min()}\n")
                f.write(f"Max Date: {df_qfq['trade_date'].max()}\n")
            else:
                f.write("Returned None\n")
        except Exception as e:
            f.write(f"Error: {e}\n")
            
        f.write("\n--- get_dividend ---\n")
        try:
            div = fs.get_dividend(code)
            if div is not None:
                f.write(f"Shape: {div.shape}\n")
                f.write(f"Head:\n{div.head()}\n")
            else:
                f.write("Returned None\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
