# R049 椭球稳健自适应在线组合选择（RELP-Adap）失败报告

## 结论

`Failed`。候选在训练样本的全部三个滑点场景均显著落后于主基线，并且交易频率远超预冻结上限；未运行起点敏感性和最终测试，未读取 `2025-07-01` 之后的绩效。

## 假设与冻结

候选按 Tsang、Sit、Wong 的 RELP Theorem 5 映射为 SOCP：预测收益减去 `lambda * L1` 换手惩罚及 `kappa * ||U b||_2` 稳健项，受 `1'b + gamma * ||b_hat_prev-b||_1 <= 1` 约束。唯一冻结版本为 25 个 `(kappa, lambda)` 专家、SB 选择、`z=1.96`、`delta=0`、`W=5`、每 5 个共同交易日决策、`gamma=0.0002`、`CLARABEL` 与 `1e-8` 容差。平台费用和滑点仅由执行层扣除，未将模型成本二次计入 NAV。

论文来源：[Adaptive Robust Online Portfolio Selection](https://arxiv.org/abs/2206.01064)；其公开稿将鲁棒模型写为椭球最坏情形收益并给出 Theorem 5 的 SOCP 重述。

## 数据与命令

- 四标的：`510300`、`511260`、`518880`、`512890`；共同区间 `2019-01-18` 至 `2026-07-10`，训练期 1,560 个共同交易日，最新日期距运行日 2 天。
- 主基线：`platform/configs/r8_permanent_real_fixed_weight_threshold.yaml`；机制基线未运行，因为主训练硬门槛已失败。
- 命令：

```powershell
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r049_robust_ellipsoidal_online_portfolio_adaptive.yaml --baseline-config configs\r8_permanent_real_fixed_weight_threshold.yaml --experiment-name r049_training_vs_fixed_weight --start-date 2019-01-18 --end-date 2025-06-30 --no-charts --slippage-scenario all
```

## 训练结果

| 场景 | 候选 Sharpe | 基线 Sharpe | 候选/基线年化收益 | 候选/基线 MaxDD | 候选/基线年化换手 | 候选/基线 trade_count | 拒单 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 0.087 | 1.171 | 1.24% / 10.91% | -31.80% / -9.52% | 1974.65% / 10.24% | 410 / 24 | 0 / 0 |
| stress | -0.230 | 1.168 | -3.31% / 10.88% | -37.90% / -9.53% | 1977.50% / 10.25% | 420 / 24 | 0 / 0 |
| dynamic_participation | -0.238 | 1.164 | -3.44% / 10.89% | -40.33% / -9.52% | 1954.61% / 9.97% | 418 / 24 | 0 / 0 |

候选相对主基线的 Sharpe 差为 `-1.085`、`-1.398`、`-1.402`，年化收益分别低 `9.67`、`14.19`、`14.32` 个百分点，最大回撤分别恶化 `22.28`、`28.37`、`30.81` 个百分点。年化换手为主基线约 191、193、196 倍，交易与订单数约 17 倍，违反预冻结的 30% 换手上限及交易风险门槛。

## 产物与后续

- 标准化报告：`platform/reports/experiments/r049_training_vs_fixed_weight_{default,stress,dynamic_participation}/20260712_01*/metrics.json`。
- 原始 artifacts 保留于 `platform/results/backtests/r049_training_vs_fixed_weight_*/`。
- 首次运行发现 checkpoint 状态含非 JSON `date`，已改为 ISO 日期并通过 SOCP/no-trade/序列化测试；该工程修复不改变冻结模型。
- 由于训练硬失败，已删除候选源码、注册、候选配置和专用测试；不得据此版本再进行参数调优或最终测试。
