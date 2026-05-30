# 实验报告： risk_parity

## 目标
运行 `risk_parity` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_3_510300_510880_511260_518880.yaml --strategy risk_parity`
- Baseline： `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## 候选篮子
- `510300` 沪深300ETF
- `510880` 红利ETF
- `511260` 十年国债ETF
- `518880` 黄金ETF

## Baseline 篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## 候选指标
- 累计收益率： 59.68%
- 年化收益率： 5.81%
- 年化波动率： 3.91%
- 最大回撤： -6.79%
- 夏普比率： 1.4861
- 年化换手： 0.4442
- 成交笔数： 56
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值： -0.2402
- 年化收益率差值： -0.0024
- 年化波动率差值： +0.0041
- 最大回撤差值： -0.0239
- 年化换手差值： -0.0307

## 建议
- 继续改进

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
