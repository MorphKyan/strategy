# 实验报告： risk_parity

## 目标
运行 `risk_parity` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选： `D:\strategy\env\python.exe main.py --config D:\strategy\configs\risk_parity.yaml --strategy risk_parity`

## 候选篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## 候选指标
- 累计收益率： 62.39%
- 年化收益率： 5.95%
- 年化波动率： 3.53%
- 最大回撤： -4.41%
- 夏普比率： 1.6851
- 年化换手： 0.4657
- 成交笔数： 48
- 是否有样本外指标：否

## Baseline 对比
- 未写入 baseline 对比，因为 baseline 指标不可用。

## 建议
- 复核

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
