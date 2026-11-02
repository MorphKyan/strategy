# ETF 组合执行优化复跑报告

> **2026-11-02 复核更新**：当前原窗口最优候选排序变化，“暂不替换 baseline”结论保留；原文数字为历史发表值。 [查看复核与明细](../../../../platform/reports/refactor_conclusion_validation/20261102_02/report.md)。


生成时间：2026-05-31

## 优化内容

- `skip_below_lot=true`：目标差额不足一手、或扣除现金缓冲后的可用买入现金不足一手时，清除 pending intent，不再每天重试。
- `cash_buffer_pct=0.01`：执行时将目标权重缩放到 99%，保留约 1% 现金缓冲。
- `order_priority=target_gap_desc`：先处理卖单，再按目标缺口金额从大到小处理买单，避免小额买单先消耗关键资产现金。

## 验证

- 单元测试：`./env/python.exe -m pytest platform/tests`，结果 `17 passed`。
- 复跑对象：`etf_selection/reports/platform_execution_validation/20260531/configs/optimized_execution/` 下 8 个优化版候选配置。
- 对照：同样加入执行优化参数的 aligned baseline。
- 执行记录：`etf_selection/results/screening/20260531_000612/platform_experiment_runs_execopt_v2.json`。

## 核心结果

- 候选拒单从优化前 480-851 笔降到优化后 0-32 笔；总拒单下降 99.3%。
- 优化后最优候选：`518880,510300,159985,159981,511260`，年化收益=6.52%, 最大回撤=-2.97%, Sharpe=1.9049。
- 优化前最优候选：`518880,510310,159980,159985,511260`，年化收益=7.37%, 最大回撤=-3.38%, Sharpe=1.9076。
- 优化后最优候选相对优化版 baseline：年化收益差=-0.78%, Sharpe 差=-0.4751。
- 执行优化显著减少无意义拒单和每日重试，但没有改变本轮“暂不接受替换 baseline”的结论；商品候选相对同日期 baseline 的 Sharpe 仍为负 delta。

## 新旧对比

| rank | codes | old_rejected | new_rejected | old_cash | new_cash | old_sharpe | new_sharpe | old_ann_ret | new_ann_ret | new_sharpe_delta |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `518880,510300,159985,159981,511260` | 511 | 0 | 3.57% | 4.71% | 1.8540 | 1.9049 | 6.43% | 6.52% | -0.4751 |
| 2 | `518880,510300,159980,159985,511260` | 669 | 0 | 3.47% | 4.37% | 1.9039 | 1.8608 | 7.34% | 7.21% | -0.5192 |
| 3 | `518880,510310,159980,159985,511260` | 556 | 0 | 3.37% | 4.69% | 1.9076 | 1.8486 | 7.37% | 7.09% | -0.5314 |
| 4 | `518880,510310,159985,159981,511260` | 480 | 32 | 3.43% | 4.49% | 1.8207 | 1.8128 | 6.37% | 6.27% | -0.5672 |
| 5 | `518880,510300,159980,159985,159981,511260` | 629 | 0 | 3.36% | 4.52% | 1.6405 | 1.6264 | 6.82% | 6.65% | -0.7536 |
| 6 | `518880,510300,159980,159981,511260` | 738 | 0 | 3.44% | 4.68% | 1.5805 | 1.6108 | 6.63% | 6.58% | -0.7692 |
| 7 | `518880,510310,159980,159985,159981,511260` | 851 | 3 | 3.51% | 4.43% | 1.6090 | 1.6045 | 6.69% | 6.59% | -0.7755 |
| 8 | `518880,510310,159980,159981,511260` | 551 | 1 | 3.59% | 4.46% | 1.5656 | 1.5958 | 6.56% | 6.55% | -0.7842 |

## 解读

- 拒单大幅下降的主要原因是“零手残差”不再进入 pending retry。此前大量 `511260` 买入残差因为不足一手或现金不足，按日重复尝试。
- 少量剩余拒单主要来自真正的停牌/不可交易日或目标调整瞬间仍可形成一笔失败订单；期末 pending 已基本清理。
- 现金缓冲从机制上避免把账户现金压到一手都买不起的边缘，但也会增加平均现金权重，降低满仓暴露。
- 目标缺口优先级让高权重资产先成交，减少小 ETF 先用掉现金后高权重资产无法补足的路径依赖。
- 本轮收益和 Sharpe 的变化不大，说明此前拒单多数是尾部残差噪音，不是影响主仓位配置的核心错误。
- 加商品 ETF 的组合仍没有超过 baseline，核心原因仍是商品资产提高了波动，并替代了部分 2022-2026 样本内表现较强的债券暴露。

## 产物

- 优化版汇总 CSV：`D:\strategy\etf_selection\results\screening\20260531_000612\platform_backtest_summary_execopt_v2.csv`
- 优化版平台报告根目录：`D:\strategy\platform\results\temporary_backtests\experiments\summaries\etf_selection_20260531_000612_execopt_v2`
- 优化版配置目录：`D:\strategy\etf_selection\reports\platform_execution_validation\20260531\configs\optimized_execution`

> 2026-11-02 合并更新：16 份同参基线已按费用口径合并为两份，当前保留 18 份输入。合并后四个成本场景已实际重跑，最大指标差 `4.89e-15`；以下 32 份记录描述整理当日的历史范围。

## 配置保全与复现状态（2026-11-01 整理）

本次随报告保留 32 份历史 YAML 输入，仅更新其中 16 份对照配置的 `aligned_to_candidate_config` 路径引用，未修改策略参数、交易成本或检查点设置，也未重新运行历史研究。迁移前后先逐文件校验 SHA-256，再确认路径更新只涉及元数据引用；当前仅确认文件完整和 YAML 可解析；完整复现尚未验证。

这些输入使用旧版 `strategies.segments` 格式，当前平台要求单一 `strategy` 映射，因此不能直接传给当前回测入口。原运行代码、依赖版本与行情快照未核实；恢复复现时须先确认原版本语义，再显式迁移，不能把格式改写视为原结果复现。

保留的输入：

- [configs/aligned_baselines/baseline_aligned.yaml](configs/aligned_baselines/baseline_aligned.yaml)
- [configs/optimized_execution/aligned_baselines/baseline_aligned.yaml](configs/optimized_execution/aligned_baselines/baseline_aligned.yaml)
- [configs/optimized_execution/platform_basket_518880_510300_159980_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510300_159980_159981_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510300_159980_159985_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510300_159980_159985_159981_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510300_159980_159985_511260.yaml](configs/optimized_execution/platform_basket_518880_510300_159980_159985_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510300_159985_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510300_159985_159981_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510310_159980_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510310_159980_159981_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510310_159980_159985_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510310_159980_159985_159981_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510310_159980_159985_511260.yaml](configs/optimized_execution/platform_basket_518880_510310_159980_159985_511260.yaml)
- [configs/optimized_execution/platform_basket_518880_510310_159985_159981_511260.yaml](configs/optimized_execution/platform_basket_518880_510310_159985_159981_511260.yaml)
- [configs/platform_basket_518880_510300_159980_159981_511260.yaml](configs/platform_basket_518880_510300_159980_159981_511260.yaml)
- [configs/platform_basket_518880_510300_159980_159985_159981_511260.yaml](configs/platform_basket_518880_510300_159980_159985_159981_511260.yaml)
- [configs/platform_basket_518880_510300_159980_159985_511260.yaml](configs/platform_basket_518880_510300_159980_159985_511260.yaml)
- [configs/platform_basket_518880_510300_159985_159981_511260.yaml](configs/platform_basket_518880_510300_159985_159981_511260.yaml)
- [configs/platform_basket_518880_510310_159980_159981_511260.yaml](configs/platform_basket_518880_510310_159980_159981_511260.yaml)
- [configs/platform_basket_518880_510310_159980_159985_159981_511260.yaml](configs/platform_basket_518880_510310_159980_159985_159981_511260.yaml)
- [configs/platform_basket_518880_510310_159980_159985_511260.yaml](configs/platform_basket_518880_510310_159980_159985_511260.yaml)
- [configs/platform_basket_518880_510310_159985_159981_511260.yaml](configs/platform_basket_518880_510310_159985_159981_511260.yaml)
