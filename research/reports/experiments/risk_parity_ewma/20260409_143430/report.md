# 实验报告： risk_parity_ewma

## 目标
运行 `risk_parity_ewma` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity_ewma`
- Baseline： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## 候选指标
- 累计收益率： 64.02%
- 年化收益率： 6.20%
- 年化波动率： 3.50%
- 最大回撤： -3.80%
- 夏普比率： 1.7727
- 年化换手： 0.7159
- 成交笔数： 66
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值： +0.0463
- 年化收益率差值： +0.0015
- 年化波动率差值： -0.0001
- 最大回撤差值： +0.0061
- 年化换手差值： +0.2410

## 建议
- 继续改进

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
