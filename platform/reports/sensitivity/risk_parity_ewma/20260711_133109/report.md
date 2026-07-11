# 平台起始日敏感度分析：risk_parity_ewma

- 配置：`D:\strategy\platform\configs\r0_domestic_equal_weight_risk_parity_ewma.yaml`
- 步长：`3` 个交易日
- 样本数量：`144`
- 汇总 CSV：`D:\strategy\platform\reports\sensitivity\risk_parity_ewma\20260711_133109\sensitivity_summary.csv`
- 原始结果根目录：`D:\strategy\platform\results\sensitivity_raw\risk_parity_ewma\20260711_133109`

本分析不限制样本数，会对配置回测日历中每隔 `step` 个交易日的起始日期逐一评估。
