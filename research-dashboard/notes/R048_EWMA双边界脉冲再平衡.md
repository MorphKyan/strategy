# R048 EWMA 风险平价外带触发、内带复位的双边界脉冲再平衡

## 基本信息

- 研究 ID：R048
- Owner：`/root`
- 创建时间：2026-07-11 Asia/Shanghai
- 状态：`Failed`
- 关联看板项：`research-dashboard/research_backlog.md`

## 假设与来源

- 假设：保持 `risk_parity_ewma` 的月度 5%/25% 外带触发；触发后沿实际权重至理论权重的连线进入半宽内带，能减少连续月重复触发和订单数，同时较 R045 的外边界落点改善目标跟踪。
- 来源：Holden 与 Holden（2011）及 Dybvig 与 Pezzo（2019）关于固定成本与比例成本共存时回到无交易区内部的结论；半宽 `0.5` 是预注册的工程近似，不视为理论最优。
- 主要风险：整手和最低费用可能使实际落点仍在外带之外；内带复位也可能仍导致低波三资产 Sharpe 起点敏感性退化。
- 不应合入条件：任一预冻结硬门槛失败，或训练/敏感性证据不能完整覆盖三个配置和三种滑点。

## 冻结条件（首次训练运行前）

- 训练样本截止：`2025-06-30`；最终测试起点：`2025-07-01`，最终测试结果在冻结前不得读取。
- 候选：`risk_parity_ewma_dual_band_reset`，继承 `RiskParityEWMAStrategy`；月频、`ewma_span=60`、`ewma_min_periods=20`、外带 `rebalance_threshold=0.05`、`rebalance_relative_threshold=0.25` 均与基线不变。
- 公式：`b_outer_i=min(0.05, 0.25*w_i*)`；`b_inner_i=0.5*b_outer_i`；触发时 `alpha=max_i max(0,1-b_inner_i/abs(w_i-w_i*))` 并截断到 `[0,1]`；初始建仓完整到 `w*`，零目标完整退出。
- 禁止事后修改：内带比例、外带、投影公式、资产池、EWMA 参数、检查频率、成本、容差与验收门槛。
- 验收门槛：完全遵循 R048 看板定义，包括三个配置、`default`/`stress`/`dynamic_participation`，及每 2 个自然月一个起点的训练样本敏感性。

## 数据审计

- `baseline_r1_domestic_ewma.yaml`：共同区间 `2019-01-18` 至 `2026-07-10`，1810 个交易日。
- `baseline_r1_domestic_low_vol_ewma.yaml`：共同区间 `2019-01-18` 至 `2026-07-10`，1810 个交易日。
- `r0_domestic_equal_weight_risk_parity_ewma.yaml`：共同区间 `2017-08-24` 至 `2026-07-10`，2152 个交易日。
- 运行日为 2026-07-11，最新数据滞后 1 个自然日，满足 7 日新鲜度；三个训练共同历史均严格超过 3 年。`validate_hfq_data.py` 因缺少不属于 platform 的 `research/data/510300.csv` 无法运行，不影响已从 platform 本地 CSV 取得的共同日期审计；后续将直接审计本地 CSV 的日期、重复项与价格字段。

## 验证命令

```powershell
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_ewma.yaml
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_low_vol_ewma.yaml
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\r0_domestic_equal_weight_risk_parity_ewma.yaml
```

## 结果与结论

- 主训练区间 `2019-01-18` 至 `2025-06-30` 已对主配置运行 `default`、`stress`、`dynamic_participation`。
- 候选的 `annualized_turnover` 为 `49.223%`、`49.868%`、`49.191%`，低于基线 `60.931%`、`60.789%`、`60.263%`；但候选的 `trade_count`/`order_count` 为 `171/171`、`175/175`、`170/170`，高于基线 `164/164`、`164/164`、`162/162`。
- 这违反 R048 预冻结硬门槛（交易数和订单数均不得高于基线），因此立即判定 `Failed`。未运行低波与等权稳健性配置、起点敏感性和最终测试，未读取 `2025-07-01` 之后指标。
- 已清理候选源码、注册、单元测试和临时配置；保留原始产物与中文报告 `platform/reports/r048_ewma_dual_band_reset_failed_report.md`。
