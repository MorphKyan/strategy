# 实验报告：risk_parity

## 目标
运行 `risk_parity` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选：`D:\strategy\env\python.exe main.py --config D:\strategy\research\configs\generated\risk_parity_etfsel_all_commodities_20260531.yaml --strategy risk_parity`
- Baseline：`D:\strategy\env\python.exe main.py --config D:\strategy\research\configs\risk_parity.yaml --strategy risk_parity`

## 候选篮子
- `518880` 黄金ETF
- `510300` 沪深300ETF
- `159980` 有色期货ETF
- `159985` 豆粕ETF
- `159981` 能源化工ETF
- `511260` 十年国债ETF

## Baseline 篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## 候选指标
- 累计收益率：62.72%
- 年化收益率：8.35%
- 年化波动率：4.73%
- 最大回撤：-5.34%
- 夏普比率：1.7637
- 年化换手：0.6493
- 交易笔数：78
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值：+0.0786
- 年化收益率差值：+0.0240
- 年化波动率差值：+0.0120
- 最大回撤差值：-0.0094
- 年化换手差值：+0.1836

## 建议
- 继续改进

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
