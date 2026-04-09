import pandas as pd
import importlib
import sys
from tqdm import tqdm

class SensitivityAnalyzer:
    def __init__(self, strategy_name: str, config: dict):
        self.strategy_name = strategy_name
        self.config = config
        try:
            self.strategy_module = importlib.import_module(f"src.strategies.{strategy_name}")
        except ImportError:
            raise ImportError(f"找不到策略模块: {strategy_name}")

    def run_analysis(self, df: pd.DataFrame, step_size: int = 20, min_backtest_days: int = 252):
        """
        运行敏感度分析：变动起始日期并记录回测指标。
        
        :param df: 全量数据 DataFrame
        :param step_size: 起始点步长 (默认为每 20 个交易日测试一次)
        :param min_backtest_days: 最短回测天数 (默认 1 年)
        """
        dates = df.index.tolist()
        results = []
        
        # 限制分析范围：起始日最晚到离结束还有 min_backtest_days 之前
        cutoff_idx = len(dates) - min_backtest_days
        if cutoff_idx <= 0:
            print("数据量不足以进行敏感度分析。")
            return pd.DataFrame()

        print(f"开始敏感度分析: 策略={self.strategy_name}, 总测试起始点数: {(cutoff_idx // step_size) + 1}")
        
        # 进度条
        pbar = tqdm(range(0, cutoff_idx, step_size))
        for i in pbar:
            start_date = dates[i]
            pbar.set_description(f"正在分析起始日期: {start_date.date()}")
            
            # 数据切片
            df_subset = df.iloc[i:]
            
            try:
                # 运行策略
                _, _, metrics = self.strategy_module.run_strategy(df_subset, self.config)
                
                # 补充基本信息
                metrics['start_date'] = start_date
                results.append(metrics)
            except Exception as e:
                print(f"起始日 {start_date} 回测失败: {e}")
                continue

        analysis_df = pd.DataFrame(results).set_index('start_date')
        return analysis_df
