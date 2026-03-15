import pandas as pd
import pathlib
from typing import List, Dict

def load_etf_data(codes: List[str], data_dir: str = './data') -> pd.DataFrame:
    """
    加载 ETF 数据并计算后复权收盘价，合并到一个 DataFrame 中。
    
    Args:
        codes: ETF 代码列表，例如 ['510300', '518880', '511260']
        data_dir: 数据存储目录
        
    Returns:
        pd.DataFrame: 包含各 ETF 后复权收盘价的 DataFrame，索引为 trade_date
    """
    base_path = pathlib.Path(data_dir)
    merged_df = pd.DataFrame()

    for code in codes:
        # 加载原始 K 线数据
        price_file = base_path / f"{code}.csv"
        factor_file = base_path / f"{code}_hfq_factor.csv"
        
        if not price_file.exists() or not factor_file.exists():
            raise FileNotFoundError(f"数据文件缺失: {code}")
            
        df_price = pd.read_csv(price_file, parse_dates=['trade_date'])
        df_factor = pd.read_csv(factor_file, parse_dates=['trade_date'])
        
        # 提取收盘价和复权因子
        df_price = df_price[['trade_date', 'close_price']].rename(columns={'close_price': f'{code}_unadj'})
        df_factor = df_factor[['trade_date', 'hfq_factor']].rename(columns={'hfq_factor': f'{code}_factor'})
        
        # 合并并计算后复权价
        df_item = pd.merge(df_price, df_factor, on='trade_date', how='left')
        # 如果因子缺失，默认用 1.0 (理论上不应该缺失)
        df_item[f'{code}_factor'] = df_item[f'{code}_factor'].ffill().fillna(1.0)
        df_item[code] = df_item[f'{code}_unadj'] * df_item[f'{code}_factor']
        
        df_final = df_item[['trade_date', code]].set_index('trade_date')
        
        if merged_df.empty:
            merged_df = df_final
        else:
            merged_df = pd.merge(merged_df, df_final, left_index=True, right_index=True, how='outer')

    # 处理缺失值：前向填充
    merged_df = merged_df.sort_index().ffill()
    
    # 剔除初始阶段（只要有一个资产还没上市就剔除，确保从三者都有数据的那天开始回测）
    merged_df = merged_df.dropna()
    
    return merged_df

if __name__ == "__main__":
    # 测试加载
    codes = ['510300', '518880', '511260']
    df = load_etf_data(codes)
    print("数据对齐后的前 5 行：")
    print(df.head())
    print(f"\n数据范围: {df.index.min()} 到 {df.index.max()}")
    print(f"总交易日数: {len(df)}")
