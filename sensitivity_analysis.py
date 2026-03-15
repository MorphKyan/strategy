import pandas as pd
import matplotlib.pyplot as plt
from data_loader import load_etf_data
from backtest_engine import run_backtest
from metrics import calculate_metrics
import os

# 设置中文字体 (Windows 常用字体)
plt.rcParams['font.sans-serif'] = ['SimHei'] 
plt.rcParams['axes.unicode_minus'] = False

def run_sensitivity_analysis():
    codes = ['510300', '518880', '511260']
    df_all = load_etf_data(codes)
    
    dates = df_all.index.tolist()
    results = []
    
    print(f"开始敏感度分析，总交易日数: {len(dates)}")
    
    # 我们至少需要 1 年的数据来计算有意义的年化收益，
    # 且最后一天由于没有后续数据，run_backtest 可能会在 metrics 中报错
    # 限制分析范围：起始日最晚到最后半年之前
    cutoff_idx = len(dates) - 126 # 约半年
    
    for i in range(cutoff_idx):
        start_date = dates[i]
        df_subset = df_all.iloc[i:]
        
        # 运行回测
        res_df, trades_df = run_backtest(df_subset)
        
        # 计算指标
        metrics = calculate_metrics(res_df['net_value'])
        
        # 补充交易次数和手续费
        metrics['start_date'] = start_date
        metrics['rebalance_count'] = len(trades_df)
        metrics['total_fee'] = trades_df['fee'].sum() if not trades_df.empty else 0.0
        
        results.append(metrics)
        
        if (i + 1) % 100 == 0:
            print(f"已处理 {i+1}/{cutoff_idx} 个起始日...")

    analysis_df = pd.DataFrame(results).set_index('start_date')
    analysis_df.to_csv('sensitivity_analysis_results.csv')
    print("\n分析结果已保存至 sensitivity_analysis_results.csv")
    
    # 绘图
    fig, axes = plt.subplots(3, 2, figsize=(15, 12), constrained_layout=True)
    fig.suptitle('“三等分动态平衡策略”起始日敏感度分析', fontsize=16)
    
    # 1. 年化收益
    axes[0, 0].plot(analysis_df.index, analysis_df['annualized_return'] * 100, color='tab:blue')
    axes[0, 0].set_title('年化收益率 (%)')
    axes[0, 0].grid(True)
    
    # 2. 最大回撤
    axes[0, 1].plot(analysis_df.index, analysis_df['max_drawdown'] * 100, color='tab:red')
    axes[0, 1].set_title('最大回撤 (%)')
    axes[0, 1].grid(True)
    
    # 3. 夏普比率
    axes[1, 0].plot(analysis_df.index, analysis_df['sharpe_ratio'], color='tab:green')
    axes[1, 0].set_title('夏普比率 (rf=2.0%)')
    axes[1, 0].grid(True)
    
    # 4. 再平衡次数
    axes[1, 1].plot(analysis_df.index, analysis_df['rebalance_count'], color='tab:orange')
    axes[1, 1].set_title('总计触发再平衡次数')
    axes[1, 1].grid(True)
    
    # 5. 累计手续费
    axes[2, 0].plot(analysis_df.index, analysis_df['total_fee'], color='tab:purple')
    axes[2, 0].set_title('累计手续费损耗 (单位净值)')
    axes[2, 0].grid(True)
    
    # 6. 总收益 (辅助参考)
    axes[2, 1].plot(analysis_df.index, analysis_df['total_return'] * 100, color='tab:cyan')
    axes[2, 1].set_title('回测期总收益 (%)')
    axes[2, 1].grid(True)
    
    plt.savefig('sensitivity_analysis.png')
    print("图表已保存至 sensitivity_analysis.png")

if __name__ == "__main__":
    run_sensitivity_analysis()
