# 实验报告：risk_parity

## 目标
运行 `risk_parity` 的标准化实验，并在 baseline 指标可用时与 `risk_parity` 对比。

## 假设
本次运行评估候选策略是否在不显著增加换手的前提下改善风险调整后表现。

## 命令
- 候选：`C:\ProgramData\miniconda3\python.exe main.py --config C:\Users\morph\.codex\worktrees\b6cc\strategy\research\configs\generated\risk_parity_no_bond_agri_energy.yaml --strategy risk_parity`
- Baseline：`C:\ProgramData\miniconda3\python.exe main.py --config C:\Users\morph\.codex\worktrees\b6cc\strategy\research\configs\risk_parity.yaml --strategy risk_parity`

## 候选篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `159985` 豆粕ETF
- `159981` 能源化工ETF

## Baseline 篮子
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## 候选指标
- 累计收益率：56.59%
- 年化收益率：12.08%
- 年化波动率：9.95%
- 最大回撤：-11.82%
- 夏普比率：1.2140
- 年化换手：0.9222
- 交易笔数：48
- 是否有样本外指标：否

## Baseline 对比
- 夏普差值：-0.4711
- 年化收益率差值：+0.0613
- 年化波动率差值：+0.0642
- 最大回撤差值：-0.0742
- 年化换手差值：+0.4565

## 建议
- 继续改进

## 说明
- 指标根据生成的 CSV 产物计算，而不是凭记忆推断。
- 除非仓库明确生成样本外指标，否则样本外指标标记为不可用。
