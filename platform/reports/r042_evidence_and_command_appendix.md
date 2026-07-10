# R042 证据与命令附录

本附录只补充可追溯性，不改变候选、参数、验收阈值、指标或 `Research-Only` 结论，也没有重新运行任何回测。

## 一、正式与排除的敏感性产物

正式 936 runs 由下列 8 个 manifest 唯一构成；每份均为 39 个共同交易日起点 × 3 个滑点场景 = 117 runs：

1. `platform/reports/sensitivity/r042/fixed_weight_threshold/20260710_210304/manifest.json`
2. `platform/reports/sensitivity/r042/fixed_weight_threshold/20260710_210345/manifest.json`
3. `platform/reports/sensitivity/r042/monthly_equal_weight/20260710_210424/manifest.json`
4. `platform/reports/sensitivity/r042/monthly_equal_weight/20260710_210511/manifest.json`
5. `platform/reports/sensitivity/r042/risk_parity/20260710_210552/manifest.json`
6. `platform/reports/sensitivity/r042/risk_parity/20260710_210732/manifest.json`
7. `platform/reports/sensitivity/r042/risk_parity_ewma/20260710_210825/manifest.json`
8. `platform/reports/sensitivity/r042/risk_parity_ewma/20260710_210924/manifest.json`

明确排除：

- `platform/reports/sensitivity/r042/fixed_weight_threshold/20260710_210012/manifest.json`：237 runs，错误使用资产联合日历，含共同上市日前起点。
- `platform/reports/sensitivity/r042/fixed_weight_threshold/20260710_210026/manifest.json`：237 runs，同一错误联合日历批次的重复诊断。
- `platform/reports/sensitivity/r042/risk_parity/20260710_210644/manifest.json`：117 runs，虚拟30Y `risk_parity` 的先完成批次；因外层批处理随后超时后按既定恢复流程单独重跑，正式批次固定为 `20260710_210732`，本份标记为重复诊断。

选择标准是程序流程与时间戳：联合日历问题修正后，仅采用共同日历的完整批次；发生外层超时并恢复的配置采用恢复后明确完成并在汇总脚本中按最新时间戳选中的 `210732`。没有比较 `210644` 与 `210732` 的表现来择优。

## 二、实际命令

项目 Python 实际布局为 `.\env\python.exe`。下列命令按终端执行记录重建；批处理内部每个配置均由脚本的 `--slippage-scenario all` 展开为 `default`、`stress`、`dynamic_participation`，没有逐场景手工命令。

### 数据与代理检查

```powershell
.\env\python.exe platform\scripts\generate_leveraged_etf.py
```

随后使用 `.\env\python.exe -` 执行内联只读检查，读取 `platform/data/{510300,512890,518880,511260,511260_3X,511090}.csv` 与相关 HFQ sidecar，核验日期、重复值、共同训练区间、`511260_3X` 日收益误差以及真实30Y代理统计。内联脚本未持久化；终端证据值已写入主报告。除该事实外不声称存在一个无法验证的独立脚本文件。

实际内联命令主体如下（PowerShell here-string 通过 stdin 交给项目 Python）：

```powershell
@'
import pandas as pd, numpy as np
from pathlib import Path
D=Path('platform/data')
base=pd.read_csv(D/'511260.csv').merge(pd.read_csv(D/'511260_hfq_factor.csv'),on='trade_date',how='left').sort_values('trade_date')
base['hfq_factor']=base.hfq_factor.ffill().fillna(1); r=(base.close*base.hfq_factor).pct_change()
syn=pd.read_csv(D/'511260_3X.csv').sort_values('trade_date'); rs=syn.close.pct_change()
print('max_abs_return_error',np.nanmax(np.abs(rs.to_numpy()-3*r.to_numpy())))
for c in ['510300','512890','518880','511260','511260_3X']:
 x=pd.read_csv(D/f'{c}.csv'); print(c,x.trade_date.min(),x.trade_date.max(),len(x),x.trade_date.duplicated().sum())
common=set(pd.read_csv(D/'510300.csv').trade_date)
for c in ['512890','518880','511260','511260_3X']: common &= set(pd.read_csv(D/f'{c}.csv').trade_date)
train=sorted(d for d in common if d<='2025-06-30'); print('common_train',train[0],train[-1],len(train))
def adj(code):
 p=pd.read_csv(D/f'{code}.csv').sort_values('trade_date'); fp=D/f'{code}_hfq_factor.csv'
 if fp.exists():
  f=pd.read_csv(fp); p=p.merge(f,on='trade_date',how='left'); p['hfq_factor']=p.hfq_factor.ffill().fillna(1); px=p.close*p.hfq_factor
 else: px=p.close
 return pd.Series(px.values,index=pd.to_datetime(p.trade_date),name=code)
a=adj('511260_3X').pct_change(); b=adj('511090').pct_change(); z=pd.concat([a,b],axis=1).dropna(); z=z[z.index<='2025-06-30']
ann=np.sqrt(252); print('proxy_overlap',z.index.min().date(),z.index.max().date(),len(z)); print('corr',z.corr().iloc[0,1],'vol_ratio',z.iloc[:,0].std()/z.iloc[:,1].std(),'te',(z.iloc[:,0]-z.iloc[:,1]).std()*ann,'monthly_same',((1+z).resample('ME').prod().sub(1).prod(axis=1)>0).mean())
def mdd(ret):
 nav=(1+ret).cumprod(); return (nav/nav.cummax()-1).min()
print('mdd_syn',mdd(z.iloc[:,0]),'mdd_real',mdd(z.iloc[:,1]),'diff',mdd(z.iloc[:,0])-mdd(z.iloc[:,1]))
'@ | .\env\python.exe -
```

### 主训练 24 runs

```powershell
$configs = @('r8_permanent_real_fixed_weight_threshold.yaml','r42_permanent_virtual30_fixed_weight_threshold.yaml','r8_permanent_real_equal_weight_monthly.yaml','r42_permanent_virtual30_equal_weight_monthly.yaml','r42_permanent_10y_risk_parity.yaml','r42_permanent_virtual30_risk_parity.yaml','r42_permanent_10y_risk_parity_ewma.yaml','r42_permanent_virtual30_risk_parity_ewma.yaml')
foreach ($c in $configs) {
  .\env\python.exe platform\scripts\run_platform_backtest.py --config "configs\$c" --start-date 2019-01-18 --end-date 2025-06-30 --slippage-scenario all
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

### 正式敏感性 936 runs

实际执行过多次外层批处理恢复；每个正式配置的等价具体调用如下。manifest 的 `config`、`calendar_month_step=2`、`sample_count=117` 与三场景清单可逐项核对：

```powershell
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_virtual30_fixed_weight_threshold.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r8_permanent_real_equal_weight_monthly.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_virtual30_equal_weight_monthly.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_10y_risk_parity.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_virtual30_risk_parity.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_10y_risk_parity_ewma.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\r42_permanent_virtual30_risk_parity_ewma.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results/sensitivity_raw/r042 --report-root reports/sensitivity/r042
```

### 冻结后最终测试 24 runs

```powershell
$configs = @('r8_permanent_real_fixed_weight_threshold.yaml','r42_permanent_virtual30_fixed_weight_threshold.yaml','r8_permanent_real_equal_weight_monthly.yaml','r42_permanent_virtual30_equal_weight_monthly.yaml','r42_permanent_10y_risk_parity.yaml','r42_permanent_virtual30_risk_parity.yaml','r42_permanent_10y_risk_parity_ewma.yaml','r42_permanent_virtual30_risk_parity_ewma.yaml')
foreach ($c in $configs) {
  .\env\python.exe platform\scripts\run_platform_backtest.py --config "configs\$c" --start-date 2025-07-01 --end-date 2026-07-10 --slippage-scenario all
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

### 自动化验证

首次研究完成时执行：

```powershell
.\env\python.exe -m pytest platform\tests -q
```

输出为 `63 passed in 3.43s`。Reviewer 补证阶段于 `2026-07-10 21:19:53 +08:00` 再次执行同一命令，结束于 `21:19:57 +08:00`，完整关键输出为：

```text
...............................................................          [100%]
63 passed in 3.37s
```

这是代码验证，不是回测；没有改变冻结研究结果。

## 三、不可加载的冻结候选证据

以下为主候选研究配置的完整冻结内容；它只存在于 Markdown 代码块中，不位于 `platform/configs/`，不可被平台作为配置加载：

```yaml
platform: {run_name: r42_permanent_virtual30_fixed_weight_threshold}
data: {data_dir: data}
assets:
- {asset_id: 'CN_ETF:510300.SH', code: '510300', name: 沪深300ETF, asset_type: etf, exchange: SH, currency: CNY, lot_size: 100, price_limit_pct: 0.1}
- {asset_id: 'CN_ETF:512890.SH', code: '512890', name: 红利低波ETF, asset_type: etf, exchange: SH, currency: CNY, lot_size: 100, price_limit_pct: 0.1}
- {asset_id: 'CN_ETF:518880.SH', code: '518880', name: 黄金ETF, asset_type: etf, exchange: SH, currency: CNY, lot_size: 100, price_limit_pct: 0.1}
- {asset_id: 'CN_ETF:511260_3X.SH', code: '511260_3X', name: 虚拟30年国债, asset_type: etf, exchange: SH, currency: CNY, lot_size: 100, price_limit_pct: 0.1}
portfolio: {initial_cash: 1000000.0, initial_equity: 1000000.0, initial_positions: []}
backtest: {enable_checkpoints: false}
execution: {round_mode: round, price_field: close, weight_tolerance: 0.0005, unfilled_policy: retry_next_day, fee: {rate: 0.0002, min_fee: 5.0}}
output: {results_dir: results/backtests}
strategy:
  strategy_name: fixed_weight_threshold
  strategy_version_id: null
  cancel_pending_on_start: false
  params:
    rebalance_on_start: true
    abs_band: 0.05
    rel_band: 0.25
    cooldown_days: 0
    universe: ['CN_ETF:510300.SH', 'CN_ETF:512890.SH', 'CN_ETF:518880.SH', 'CN_ETF:511260_3X.SH']
```

原冻结文件 SHA256 为 `8A6D4F3676E79351F20612A3407F84E0891DDD8A316E4B91E9FDFED720B86FA7`。训练三份 runtime snapshot 及 SHA256：

- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_default_20260710_205941_317720/config_snapshot.yaml` → `7918565591630D223C4CCA5FF37C48062489219839EDF78DEE0A7E2DA3549788`
- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_stress_20260710_205941_791779/config_snapshot.yaml` → `43BF86378A254221F04A0E678F3B305583F22C85FFBAB0595418AC6901A950A7`
- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_dynamic_participation_20260710_205942_239186/config_snapshot.yaml` → `D91B27DAE7A0ACD9F0DC3DD7A07B4260D4C5DD169BFE80C35471515C847B06B4`

最终测试三份 runtime snapshot 及 SHA256：

- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_default_20260710_211221_074581/config_snapshot.yaml` → `823E26670661225DED50A67323B48E613A0946DC5E9BC665D56132DDEDA5C61E`
- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_stress_20260710_211221_197229/config_snapshot.yaml` → `A7AB2761C2269AF7892E450586E60C1B0ECEB1636CBAA48C5FBA97D7B256CB37`
- `platform/results/backtests/r42_permanent_virtual30_fixed_weight_threshold_dynamic_participation_20260710_211221_318617/config_snapshot.yaml` → `3A75CB8BCEB309115FE5CF3D7A742623131B937385E1CD55CB8BC72C7E0EED08`

runtime snapshots 与冻结 YAML 的候选资产、权重、策略和阈值一致；预期差异仅为运行器注入的 `backtest.start_date/end_date`、场景后缀 `platform.run_name`、`execution.slippage_scenario` 和对应滑点参数。中文名称在部分历史 snapshot 中因既有编码显示为乱码，不影响 `asset_id`、`code` 或参数解析。

审计配置的归一化冻结定义：月度候选仅将 `strategy_name` 改为 `monthly_equal_weight`；10Y/虚拟30Y `risk_parity` 配对固定 `rolling_window=120`、`min_periods=20`、`rebalance_frequency=monthly`、`rebalance_threshold=0.05`；EWMA 配对固定 `ewma_span=60`、`ewma_min_periods=20`、同样月频和阈值。所有审计篮子均为同四资产，仅债券 ID 在 `511260.SH` 与 `511260_3X.SH` 间配对替换。精确 runtime 内容永久保存在对应 raw 目录的 `config_snapshot.yaml`。

## 四、缓存与清理证据

- 所有命令均直接调用 `run_platform_backtest.py` 或 `run_sensitivity.py`，没有调用缓存接口或复制 cache metrics。
- Reviewer 补证检查 `platform/results/backtest_cache`，结果为 `CACHE_DIR_MISSING`。因此本仓库当前没有可被本研究复用的该目录条目；这只能证明目录不存在以及执行命令未指定缓存，不能证明外部系统从未存在缓存。
- `Get-ChildItem platform/configs -Filter 'r42*' -Recurse` 无输出；研究期六份 R042 配置已删除。
- 对 `platform/src/platform_core/strategy.py` 与 `platform/src/platform_core/strategies/*.py` 搜索 `r42_permanent|R042` 无输出；没有 R042 新策略或注册残留。
- 没有创建临时 `.py` 研究脚本；数据与代理诊断使用未持久化的 stdin 内联脚本。
- `git diff --check` 仅报告研究开始前已存在且明确不在本任务范围内的 `platform/src/platform_dashboard/app.py:553,556` 与 `artifacts.py:111` 尾随空格。本次未触碰这两个文件；R042 自有文件没有新增 diff-check 错误。

## 五、R042 文件清单

本研究创建或修改：

- 修改：`platform/data/511260_3X.csv`（从当前 `511260` 重建，固定 3 倍日收益链）。
- 修改：`platform/scripts/run_sensitivity.py`（共同日历、`--calendar-month-step`、`order_count`）。
- 创建：`platform/reports/r042_freeze_20260710_211100.md`。
- 创建：`platform/reports/r042_virtual_30y_permanent_portfolio_report.md`。
- 创建：`platform/reports/r042_evidence_and_command_appendix.md`。
- 创建：`platform/reports/sensitivity/r042/**` 与 `platform/results/sensitivity_raw/r042/**`。
- 创建：R042 训练与最终测试 raw 目录及其中补写的 `metrics.json`，位于 `platform/results/backtests/*_20260710_2059*/`、`*_20260710_2112*/`。
- 创建：`research-dashboard/notes/R042_虚拟30年国债中国永久组合.md`。
- 修改：`research-dashboard/research_backlog.md`、`research-dashboard/research_history_summary.md`、`platform/reports/non_baseline_research_history_summary.md`。
- 研究中创建后按 `Research-Only` 规则删除：六份 `platform/configs/r42_*.yaml`；它们不再是工作树文件，内容由 raw snapshot 与本附录保全。

研究开始前已有、与 R042 无关且未触碰：

- `platform/src/platform_dashboard/app.py`
- `platform/src/platform_dashboard/artifacts.py`
