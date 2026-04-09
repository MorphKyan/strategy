import pandas as pd
import pathlib
from typing import List
# import finshare as fs  # Moved to local import in fetch_codes_data
from datetime import datetime

class DataHandler:
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = pathlib.Path(__file__).parent.parent / data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_codes_data(self, codes: List[str], start_date: str = '1990-01-01', end_date: str = None):
        """从 Finshare 获取数据并保存到本地"""
        try:
            import finshare as fs
        except ImportError:
            print("错误：未安装 finshare 库，无法获取在线数据。请使用 pip install finshare 安装。")
            return

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        for code in codes:
            print(f"正在从 Finshare 获取 {code} 的数据...")
            try:
                fs_code = f"{code}.SH" if not code.endswith(('.SH', '.SZ')) else code
                simple_code = code.split('.')[0]
                
                # 获取原始数据和复权因子
                df_unadj = fs.get_historical_data(fs_code, start=start_date, end=end_date, adjust=None)
                df_hfq = fs.get_historical_data(fs_code, start=start_date, end=end_date, adjust='hfq')
                
                if df_unadj is not None and not df_unadj.empty:
                    df_unadj.to_csv(self.data_dir / f"{simple_code}.csv", index=False)
                    
                    if df_hfq is not None and not df_hfq.empty:
                        # 计算复权因子并保存
                        hfq_merged = pd.merge(df_unadj[['trade_date', 'close_price']], 
                                            df_hfq[['trade_date', 'close_price']], 
                                            on='trade_date', suffixes=('_unadj', '_hfq'))
                        hfq_merged['hfq_factor'] = hfq_merged['close_price_hfq'] / hfq_merged['close_price_unadj']
                        hfq_df = hfq_merged[['trade_date', 'hfq_factor']]
                        hfq_df.to_csv(self.data_dir / f"{simple_code}_hfq_factor.csv", index=False)
                        print(f"[{code}] 数据获取并保存成功。")
                else:
                    print(f"[{code}] 警告：未能获取数据。")
            except Exception as e:
                print(f"[{code}] 获取数据时发生错误: {e}")

    def load_etf_data(self, codes: List[str], auto_fetch: bool = True) -> pd.DataFrame:
        """加载数据，如果缺失则自动获取"""
        merged_df = pd.DataFrame()

        for code in codes:
            price_file = self.data_dir / f"{code}.csv"
            factor_file = self.data_dir / f"{code}_hfq_factor.csv"
            
            if not price_file.exists() or not factor_file.exists():
                if auto_fetch:
                    print(f"数据文件缺失: {code}，尝试自动获取...")
                    self.fetch_codes_data([code])
                else:
                    raise FileNotFoundError(f"数据文件缺失且未开启自动获取: {code}")
            
            # 再次检查文件是否存在（获取后）
            if not price_file.exists() or not factor_file.exists():
                 raise FileNotFoundError(f"数据加载失败，文件仍不存在: {code}")

            df_price = pd.read_csv(price_file, parse_dates=['trade_date'])
            df_factor = pd.read_csv(factor_file, parse_dates=['trade_date'])
            
            df_price = df_price[['trade_date', 'close_price']].rename(columns={'close_price': f'{code}_unadj'})
            df_factor = df_factor[['trade_date', 'hfq_factor']].rename(columns={'hfq_factor': f'{code}_factor'})
            
            df_item = pd.merge(df_price, df_factor, on='trade_date', how='left')
            df_item[f'{code}_factor'] = df_item[f'{code}_factor'].ffill().fillna(1.0)
            df_item[code] = df_item[f'{code}_unadj'] * df_item[f'{code}_factor']
            
            df_final = df_item[['trade_date', code]].set_index('trade_date')
            
            if merged_df.empty:
                merged_df = df_final
            else:
                merged_df = pd.merge(merged_df, df_final, left_index=True, right_index=True, how='outer')

        merged_df = merged_df.sort_index().ffill().dropna()
        return merged_df
