# ETF Selection

This directory owns ETF screening and basket construction. It is intentionally separate from `platform/`; it only generates platform configs and optionally calls platform CLI commands.

## Workflow

1. Define ETF candidates by sleeve in `config/etf_universe.yaml`.
2. Run sleeve screening:
Use `.\env\Scripts\python.exe` for venv/uv layouts, or substitute `.\env\python.exe` when the local environment exposes Python there.

```powershell
.\env\Scripts\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml
```

3. Review reports under `etf_selection/reports/<timestamp>/`.
4. Generated platform configs are written under `etf_selection/generated_configs/<timestamp>/`.
5. Optional: run generated configs through the platform:

```powershell
.\env\Scripts\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml --run-experiments
```

筛选会检查已加载候选的最新有效行情是否在最近 7 个自然日内、末日是否一致。命令行遇到过期或不对齐时，会调用平台同步工具更新全部启用候选并复查；同步或复查失败时停止，不写筛选结果。

QDII 决策数据通过 `platform/scripts/read_etf_premium.py` 取得，统一剔除最近两个交易日尚未公布的净值观测。需先将净值同步至 `platform/data/etf_nav/<code>.csv`，并在候选中明确填写年费率 `ter`。缺数据时拒绝候选，不填入默认溢价或成本。报告分别列出同一可观测区间的复权市场价年化、累计净值年化及端点溢价；`expense_ratio` 仅表示披露年费率，不代表实际持有成本，评分权重使用同名字段。

## Design

- Sleeve screening is independent of platform internals.
- Backtests are delegated to `platform/scripts/run_platform_experiment.py`.
- `--run-experiments` 会运行候选/基线同窗口对比及两者的起点敏感性分析，默认 `default + stress`。命令、阶段及输出写入 `platform_validation_runs.json`，任一步失败即停止并返回非零状态。
- 商品优先选择宽基，缺少合格宽基时可组合多个单商品 ETF。单资产与篮子共有历史门槛分别由 `selection.min_history_years`、`selection.min_common_history_years` 决定。

## Outputs

- `sleeve_rankings.csv`
- `basket_scores.csv`
- `report.md`
- `summary.json`
- `correlations/<sleeve>.csv`
- `correlations/basket_<id>.csv`
- generated platform configs
