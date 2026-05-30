# 实验报告： risk_parity_ewma_semiannual

## 目标
运行 `risk_parity_ewma_semiannual` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity_ewma_semiannual`
- Baseline： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## 候选指标
- 累计收益率： 68.76%
- 年化收益率： 6.57%
- 年化波动率： 3.59%
- 最大回撤： -3.39%
- 夏普比率： 1.8297
- 年化换手： 0.5335
- 成交笔数： 42
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值： +0.1033
- 年化收益率差值： +0.0052
- 年化波动率差值： +0.0009
- 最大回撤差值： +0.0101
- 年化换手差值： +0.0586

## 建议
- 接受

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
