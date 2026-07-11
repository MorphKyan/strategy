# R044 中国宏观冲击复制与因子风险均衡：阶段 A 数据可行性审计

## 结论

`Failed`（数据不可验证）。R044 的 point-in-time 数据硬门槛未通过，因此没有实现 `macro_shock_factor_parity`、没有创建或注册策略、没有输出候选配置、没有运行训练回测、起点敏感性或最终测试。

## 审计范围

本次审计仅检查截至训练样本上限 `2025-06-30` 所需的数据链是否可验证；未读取或汇总 `2025-07-01` 之后的市场表现。审计对象为仓库内 `platform/data/`、平台源码/配置和 R044 的冻结课题要求。

| 因子 | 审计用序列 | 结果 |
| --- | --- | --- |
| `growth_shock` | 中国季度 GDP 不变价同比 | 没有首次发布值、版本快照及决策日可用映射；不合格。 |
| `inflation_shock` | 中国月度 CPI 同比 | 没有首次发布值、版本快照及决策日可用映射；不合格。 |
| `domestic_monetary_liquidity_shock` | 中国月度 M2 同比 | 没有首次发布值、版本快照及决策日可用映射；不合格。 |
| `external_financial_shock` | 日度 VIX 收益/创新 | 没有原始市场数据、收盘可用时点或时区映射；不合格。 |

## 证据

- `platform/data/` 仅包含 ETF 行情、复权因子与公司行为文件；关键词检索未发现宏观序列、`vintage`、`revision`、`发布日期`、`release.date` 或数据适配器。
- 国家统计局明确 GDP 数据包含初步核算、最终核实和历史修订，因此当前版本不能被当作历史首次可见值使用。[GDP 数据为什么要修订](https://www.stats.gov.cn/zs/tjws/tjzb/202301/t20230101_1903737.html)；[GDP 核算和数据发布制度公告](https://www.stats.gov.cn/xw/tjxw/tzgg/202302/t20230202_1893851.html)。

## 执行命令

```powershell
rg --files platform/data
rg -n -i --glob '!**/.git/**' 'NBS|国家统计局|China.*CPI|CPI|PPI|PMI|M2|Shibor|宏观|macro|vintage|revision|发布日期|release.date' platform/data platform/src platform/configs research-dashboard
```

## 未执行项目

- 未运行 ETF 数据同步或回测：阶段 A 已在宏观 point-in-time 数据链处失败，且没有必要使用行情数据来形成研究结论。
- 未生成 `metrics.json` 或原始 backtest artifact；因此没有可报告的 `annualized_return`、`sharpe_ratio`、`max_drawdown`、`annualized_turnover`、`trade_count`、`order_count`、`rejected_order_count` 或滑点场景指标。
- 未运行最终测试，不存在候选冻结后修改。

## 建议

仅当未来提供四类序列的受版本控制原始 vintage 数据、逐期首次发布时间（含时区）以及可复现的下一交易日映射后，才应以新的研究编号重新启动阶段 A。不得用当前修订序列、统一假设滞后或价格代理替代本门槛。
