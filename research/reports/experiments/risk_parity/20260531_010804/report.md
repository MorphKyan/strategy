# 实验报告：risk_parity

## 目标
运行 `risk_parity` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选：`C:\ProgramData\miniconda3\python.exe main.py --config C:\Users\morph\.codex\worktrees\b6cc\strategy\research\configs\generated\risk_parity_no_bond_cyclical_commodity.yaml --strategy risk_parity`
- Baseline：`C:\ProgramData\miniconda3\python.exe main.py --config C:\Users\morph\.codex\worktrees\b6cc\strategy\research\configs\risk_parity.yaml --strategy risk_parity`

## 候选篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `159980` 有色期货ETF
- `159981` 能源化工ETF

## Baseline 篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## 候选指标
- 累计收益率：58.21%
- 年化收益率：12.37%
- 年化波动率：11.41%
- 最大回撤：-12.33%
- 夏普比率：1.0840
- 年化换手：1.0068
- 交易笔数：56
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值：-0.6012
- 年化收益率差值：+0.0642
- 年化波动率差值：+0.0788
- 最大回撤差值：-0.0793
- 年化换手差值：+0.5410

## 建议
- 继续改进

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
