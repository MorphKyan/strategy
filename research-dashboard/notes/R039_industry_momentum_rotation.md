# R039：行业 ETF 动量轮动（高波卫星仓）—— Failed（research-only）

- 日期：2026-07-12
- 蓝图：`platform/docs/r039_rotation_blueprint.md`（立项动机、文献依据、参数先验、验收标准、D1–D4 迭代路线）
- 详细报告：`platform/reports/r039_industry_rotation_report.md`
- 实验产物：`platform/reports/experiments/r039_industry_rotation_{default,stress,dynamic_participation}/20260712_*`；敏感性 `platform/reports/sensitivity/industry_momentum_rotation/20260712_031736`、`.../monthly_equal_weight/20260712_031853`

## 假设

行业层面动量（1M+3M 混合、跳过近 5 日）+ Top-3 等权 + 排名缓冲带 + 负动量持币，月频长多，可作为 R038 核心仓外的高波卫星仓，跑赢"持有全部行业等权"。参数全部先验冻结、零搜索。

## 结果（训练样本 2020-03-16 ~ 2025-06-30，default 场景）

- 候选年化 **−3.7%**（Sharpe −0.16，MaxDD −53%）vs 行业等权基线 **+6.8%**（0.33，−36%）：落后 10.5pp/年。
- 起始日敏感性（32 起点 × 3 滑点场景）：候选年化中位数 −8.2%、仅 1/32 为正；基线 +2.0%、75% 为正。
- 三滑点场景结论一致；费用+滑点合计 <0.5pp/年，非败因。
- 分年：6 个年度中 4 年大幅落后（2021 −18pp、2024 −17.7pp）；唯一占优 2023（+7.7pp）。

## 败因

2021–2022 行业急涨急跌的鞭打（年化 4.5× 换手全换在噪声上）+ V 型反转双重踩踏（2024-09-30 持币踏空、2024-10-08 顶点追入次日 −7%）+ 闸门 14.6% 平均现金拖累。与 Liu-Stambaugh-Yuan (2019) A 股反转结论一致；文献中显著的行业动量多为多空构造、样本偏 2017 前。

## 处置

- `industry_momentum_rotation` 撤销注册（Hard Rule 3），`strategies/rotation.py` 留 research-only + 10 例 pytest（含"确未注册"断言）。
- 候选配置删除（完整副本在实验报告目录）；基线 `baseline_r9_industry_equal_weight.yaml` 保留（Hard Rule 8）。
- 16 只行业 ETF 数据链（sina 全量行情 + 事件驱动 hfq 因子 + 分红/拆分事件表扩容）保留入库；`MarketDataStore` 新增历史收缩保护。
- 冻结样本未触碰。

## 对后续的建议

- D2（拥挤度否决）只能修追顶尾部（几个 pp），修不动鞭打主亏，不建议单独立项。
- 卫星仓更可行的下一个候选：**行业池等权 + Swedroe 阈值带**（= 本课题基线 + R038 纪律），训练样本年化 6.8%、起点稳健性 75% 为正，与核心仓相关性结构不同。如立项建议编号 R044+，复用本课题全部数据与基线。
