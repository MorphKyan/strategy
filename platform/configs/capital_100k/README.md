# 10 万元实盘配置

本目录保存 `platform/configs/` 顶层非 `generated` 国内资产策略的 10 万元等价配置，用于常态化小资金回测和模拟运行。

- `portfolio.initial_cash` 与 `portfolio.initial_equity` 固定为 `100000.0`。
- 交易费率保持 `rate: 0.0002`、`min_fee: 5.0`。
- 策略、资产池、调仓规则、滑点和整手约束与同名顶层配置一致。
- `platform.run_name` 统一增加 `_capital_100k` 后缀，避免覆盖原有 100 万元结果。
- 配置不保存固定 `start_date` 或 `end_date`；如需限定样本，应通过运行命令传入。

示例：

```powershell
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\capital_100k\domestic_cvar_dynamic_budget_bond_10y.yaml --slippage-scenario all
```
