# R037 研究笔记：基于波动率半衰期衰减动态阈值触发的自适应再平衡风险平价策略

## 基本信息

- 研究 ID：`R037`
- 课题：基于波动率半衰期衰减动态阈值触发的自适应再平衡风险平价策略
- Owner：`9e2d3532-a776-4676-9504-09797bcb48ed`
- 创建时间：`2026-06-24 23:49`
- 状态：`Failed`
- 关联看板项：`research-dashboard/research_backlog.md`
- 标准实验报告：`platform/reports/r037_half_life_adaptive_rebalance_report.md`

## 假设与来源

- 假设：用 realized volatility 的 AR(1) 半衰期动态调整 R016 偏离阈值，可在短半衰期冲击中加快避险，并在长半衰期震荡中减少 whipsaw。
- 来源或内部理由：R016 已证明动态阈值有效；R026/R028 证明过强阻尼会产生权重锁死。本研究只做 R016 邻近改造。
- 预期改善：相比 R016 Sharpe 不退化，年化双边换手率和交易笔数下降，最大回撤不恶化。
- 主要风险：半衰期估计路径依赖高；局部降低换手可能增加小额交易次数；阈值过窄会提高交易频率。
- 不应合入的条件：Sharpe 退化、最大回撤恶化、起点敏感性升高、交易笔数上升且无明确收益补偿。

## 冻结条件

- 训练样本截止：`2025-06-30`
- 最终测试起点：`2025-07-01`
- 冻结内容：候选逻辑、`half_life_window=120`、`half_life_vol_window=20`、`half_life_gamma=5.0`、`rebalance_fraction=0.8`、R016 验收门槛
- 冻结时间：`2026-06-24 23:52`
- 冻结前不得使用的内容：最终测试样本表现、最终测试指标、最终测试排序

## 实现范围

- 修改文件：临时修改 `platform/src/platform_core/strategy.py` 后已还原
- 新增配置：临时 `platform/configs/research_r037_*_train.yaml` 后已删除
- 新增或修改策略注册：临时注册 `half_life_adaptive_risk_parity` 后已删除
- 临时脚本：无持久化脚本；敏感性使用内联 Python
- 清理动作：未通过候选的策略代码、注册和研究配置均已物理移除

## 验证命令

```powershell
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml platform\configs\baseline_r2_global_dividend_ewma.yaml
.\env\python.exe -m compileall platform\src\platform_core\strategy.py
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\research_r037_r1_halflife_train.yaml --baseline-config configs\research_r037_r1_r016_train.yaml --experiment-name r037_r1_halflife_vs_r016_train --no-charts
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\research_r037_r2_halflife_train.yaml --baseline-config configs\research_r037_r2_r016_train.yaml --experiment-name r037_r2_halflife_vs_r016_train --no-charts
```

## 指标摘要

| 阶段 | 配置 | 策略 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 训练 | r1 | R016 基线 | 0.1388 | 1.2926 | -0.1422 | 0.3467 | 115 | 116 | 1 |
| 训练 | r1 | R037 候选 | 0.1408 | 1.2557 | -0.1528 | 0.3229 | 179 | 179 | 0 |
| 训练 | r2 | R016 基线 | 0.1531 | 1.0953 | -0.1591 | 0.3358 | 159 | 161 | 2 |
| 训练 | r2 | R037 候选 | 0.1498 | 1.0196 | -0.1834 | 0.3143 | 210 | 211 | 1 |

## 起点敏感性

- 采样规则：每 2 个自然月一个 `start_date`，所有 run 截止 `2025-06-30`
- 排名是否稳定：否。`r1` 候选仅 14/39 起点优于基线，`r2` 为 21/39，优势不稳定。
- Sharpe 是否稳定：否。候选 `r1` Sharpe Std `0.9583` 高于基线 `0.9479`；候选 `r2` Sharpe Std `1.0116` 高于基线 `0.9705`。
- 年化收益是否稳定：否。候选均值没有形成清晰优势。
- 最大回撤是否稳定：否。候选 `r1` 和 `r2` 的 MaxDD 均值与波动均劣于 R016。
- 换手、交易数、订单数、拒单数是否稳定：年化换手均值下降，但交易笔数和订单数明显上升，执行摩擦结构不佳。

## 最终测试

- 是否已冻结后运行：否
- 最终测试结论：未运行，因为训练样本已失败
- 是否看到结果后修改候选：否

## 结论

- 推荐：`Failed`
- 理由：训练样本 Sharpe 和最大回撤均未通过，起点敏感性不降反升，交易笔数显著增加；年化换手小幅下降不足以补偿收益和回撤退化。
- 后续动作：不合入、不保留候选策略注册、不新增平台 baseline 配置。
- 已更新文件：`research-dashboard/research_backlog.md`、`research-dashboard/research_history_summary.md`、`platform/reports/r037_half_life_adaptive_rebalance_report.md`
