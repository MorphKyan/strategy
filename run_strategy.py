import pandas as pd
from data_loader import load_etf_data
from backtest_engine import run_backtest
from metrics import calculate_metrics

def main():
    # 1. 设置参数
    # 510300.SH - 沪深 300 ETF (权益资产)
    # 518880.SH - 黄金 ETF (避险资产)
    # 511260.SH - 国泰 10 年期国债 ETF (防御资产)
    codes = ['510300', '518880', '511260']
    initial_weights = [1/3, 1/3, 1/3]
    rebalance_threshold = 0.05  # 5% 阈值
    commission = 0.0002         # 双边手续费
    
    print("=== 三等分动态平衡策略回测系统 ===")
    print(f"标的池: {codes}")
    print(f"初始权重: {initial_weights}")
    print(f"再平衡阈值: {rebalance_threshold * 100}%")
    print(f"手续费率: {commission * 100}%\n")

    # 2. 加载数据
    try:
        df = load_etf_data(codes)
        print(f"数据加载成功，交易日范围: {df.index.min().date()} 至 {df.index.max().date()}")
        print(f"有效回测天数: {len(df)}\n")
    except Exception as e:
        print(f"数据加载失败: {e}")
        return

    # 3. 运行回测
    res_df, trades_df = run_backtest(df, initial_weights, rebalance_threshold, commission)
    
    # 4. 计算指标
    metrics = calculate_metrics(res_df['net_value'])
    
    # 5. 输出结果
    print("--- 策略表现指标 ---")
    print(f"年化收益率 (Annualized Return): {metrics['annualized_return'] * 100:.2f}%")
    print(f"最大回撤 (Maximum Drawdown): {metrics['max_drawdown'] * 100:.2f}%")
    print(f"夏普比率 (Sharpe Ratio, rf=2.0%): {metrics['sharpe_ratio']:.4f}")
    
    total_trades = len(trades_df)
    total_fee = trades_df['fee'].sum() if not trades_df.empty else 0.0
    print(f"\n总计触发再平衡次数: {total_trades}")
    print(f"累计手续费损耗: {total_fee:.6f}")
    
    # 保存结果
    res_df.to_csv('backtest_results.csv')
    trades_df.to_csv('trade_history.csv')
    print(f"\n回测明细已保存至 backtest_results.csv 和 trade_history.csv")

if __name__ == "__main__":
    main()
