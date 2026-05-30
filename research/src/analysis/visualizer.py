import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

class BacktestVisualizer:
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        # 调用 utils 中的样式设置（虽然通常在 main 中调用一次即可）
        from src.utils import set_plot_style
        set_plot_style()

    def plot_performance_summary(self, res_df: pd.DataFrame, strategy_name: str):
        """
        绘制策略表现概览：净值曲线与回撤
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                        gridspec_kw={'height_ratios': [3, 1]})
        
        # 1. 净值曲线
        ax1.plot(res_df.index, res_df['net_value'], label='策略净值', color='#1f77b4', linewidth=2)
        ax1.set_title(f'策略性能概览 - {strategy_name}', fontsize=14)
        ax1.set_ylabel('累计净值')
        ax1.legend(loc='upper left')
        ax1.grid(True, linestyle='--', alpha=0.7)

        # 2. 回撤曲线
        # 计算回撤
        rolling_max = res_df['net_value'].cummax()
        drawdown = (res_df['net_value'] / rolling_max - 1.0)
        
        ax2.fill_between(drawdown.index, drawdown, 0, color='#d62728', alpha=0.3, label='回撤')
        ax2.plot(drawdown.index, drawdown, color='#d62728', linewidth=1)
        ax2.set_ylabel('回撤')
        ax2.set_xlabel('日期')
        ax2.set_ylim(-0.3, 0.05) # 默认设置一个较合理的回撤范围
        ax2.legend(loc='lower left')
        ax2.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()
        save_path = self.results_dir / "performance_summary.png"
        plt.savefig(save_path)
        plt.close()
        return save_path

    def plot_asset_allocation(self, res_df: pd.DataFrame):
        """
        绘制资产权重随时间变化的堆叠面积图
        """
        # 提取所有以 'w_' 开头的列
        weight_cols = [c for c in res_df.columns if c.startswith('w_')]
        if not weight_cols:
            print("未找到权重数据，跳过权重分布图绘制。")
            return None
        
        weights = res_df[weight_cols]
        # 去掉 'w_' 前缀以便在图例中显示
        clean_labels = [c.replace('w_', '') for c in weight_cols]
        
        plt.figure(figsize=(12, 7))
        plt.stackplot(weights.index, weights.values.T, labels=clean_labels, alpha=0.8)
        
        plt.title('投资组合资产权重分布', fontsize=14)
        plt.ylabel('权重')
        plt.xlabel('日期')
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        plt.ylim(0, 1.05)
        plt.grid(True, linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        save_path = self.results_dir / "asset_allocation.png"
        plt.savefig(save_path)
        plt.close()
        return save_path

    def plot_sensitivity_results(self, sensitivity_df: pd.DataFrame):
        """
        绘制敏感度分析汇总图：包含指标分布与随时间变化的趋势
        """
        fig, axes = plt.subplots(3, 2, figsize=(16, 18))
        
        # --- 第一行: 年化收益率 ---
        # 分布
        sns.histplot(sensitivity_df['annualized_return'] * 100, kde=True, ax=axes[0, 0], color='skyblue')
        axes[0, 0].set_title('年化收益率分布 (%)', fontsize=12)
        axes[0, 0].set_xlabel('收益率 (%)')
        # 随时间变化
        axes[0, 1].plot(sensitivity_df.index, sensitivity_df['annualized_return'] * 100, marker='o', markersize=4, linestyle='-', alpha=0.7, color='steelblue')
        axes[0, 1].set_title('年化收益率随起始日变化 (%)', fontsize=12)
        axes[0, 1].set_ylabel('收益率 (%)')
        axes[0, 1].grid(True, linestyle='--', alpha=0.6)

        # --- 第二行: 夏普比率 ---
        # 分布
        sns.histplot(sensitivity_df['sharpe_ratio'], kde=True, ax=axes[1, 0], color='salmon')
        axes[1, 0].set_title('夏普比率分布', fontsize=12)
        axes[1, 0].set_xlabel('夏普比率')
        # 随时间变化
        axes[1, 1].plot(sensitivity_df.index, sensitivity_df['sharpe_ratio'], marker='o', markersize=4, linestyle='-', alpha=0.7, color='indianred')
        axes[1, 1].set_title('夏普比率随起始日变化', fontsize=12)
        axes[1, 1].set_ylabel('夏普比率')
        axes[1, 1].grid(True, linestyle='--', alpha=0.6)

        # --- 第三行: 最大回撤 ---
        # 分布
        sns.histplot(sensitivity_df['max_drawdown'] * 100, kde=True, ax=axes[2, 0], color='lightgreen')
        axes[2, 0].set_title('最大回撤分布 (%)', fontsize=12)
        axes[2, 0].set_xlabel('最大回撤 (%)')
        # 随时间变化
        axes[2, 1].plot(sensitivity_df.index, sensitivity_df['max_drawdown'] * 100, marker='o', markersize=4, linestyle='-', alpha=0.7, color='seagreen')
        axes[2, 1].set_title('最大回撤随起始日变化 (%)', fontsize=12)
        axes[2, 1].set_ylabel('最大回撤 (%)')
        axes[2, 1].grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        save_path = self.results_dir / "sensitivity_analysis.png"
        plt.savefig(save_path)
        plt.close()
        return save_path
