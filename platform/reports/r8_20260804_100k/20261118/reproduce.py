from pathlib import Path
import json, os, subprocess, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import yaml

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import assets_from_config

HERE = Path(__file__).resolve().parent
OUT = ROOT / 'results/temporary_backtests/direct/r8_20260804_reproduce'
CONFIG = 'configs/capital_100k/r8_permanent_real_fixed_weight_threshold.yaml'
end = '2026-11-18'
cfg = yaml.safe_load((ROOT / CONFIG).read_text(encoding='utf-8'))
market = LocalCsvBarData('data', assets_from_config(cfg['assets']))
dates = [pd.Timestamp(frame.index[-1]) for frame in market.frames.values()]
if len(set(dates)) != 1 or (pd.Timestamp.now().normalize() - dates[0]).days > 7 or dates[0] < pd.Timestamp(end):
    raise RuntimeError('行情未对齐或已过期，请先同步四只 ETF')
starts = ['2026-08-04', '2026-09-01', '2026-10-01', '2026-11-01']
results = {}
for start in starts:
    root = OUT / start
    root.mkdir(parents=True, exist_ok=True)
    before = set(root.iterdir())
    subprocess.run([sys.executable, 'scripts/run_platform_backtest.py', '--config', CONFIG,
                    '--start-date', start, '--end-date', end, '--output-dir', str(root)], check=True)
    new = set(root.iterdir()) - before
    results[start] = {json.loads((p/'manifest.json').read_text(encoding='utf-8'))['metrics']['slippage_scenario']: p for p in new}
    assert set(results[start]) == {'default', 'stress'}

p = results[starts[0]]['default']
nav = pd.read_csv(p/'nav.csv', parse_dates=['date']).set_index('date')
pos = pd.read_csv(p/'positions.csv', parse_dates=['date'])
trades = pd.read_csv(p/'trades.csv', parse_dates=['date'])
codes = [a['code'] for a in cfg['assets']]
names = dict(zip(codes, ['沪深300', '十年国债', '黄金', '红利低波']))
pos['code'] = pos.asset_id.str.extract(r':(\d+)')
value = pos.pivot(index='date', columns='code', values='market_value').reindex(index=nav.index, columns=codes, fill_value=0).fillna(0)
qty = pos.pivot(index='date', columns='code', values='quantity').reindex(index=nav.index, columns=codes, fill_value=0).fillna(0)
cost = value * 0
for t in trades.itertuples():
    code = t.asset_id.split(':')[1].split('.')[0]
    cost.loc[t.date, code] += (1 if t.side == 'BUY' else -1) * t.trade_value + t.fee
income = value * 0
divs = pd.read_csv('data/platform_dividends.csv', dtype={'code': str})
for d in divs.itertuples():
    day = pd.Timestamp(d.ex_date)
    if d.code in codes and day in nav.index and day > nav.index[0]:
        income.loc[day, d.code] += qty.shift().loc[day, d.code] * d.dividend_per_share
pnl = value.diff().fillna(0) - cost + income
pnl.iloc[0] = 0
assert np.allclose(pnl.sum(axis=1).iloc[1:], nav.total_value.diff().iloc[1:], atol=.02), '损益归因与组合净值不一致'
adjusted = pd.DataFrame({a['code']: pd.Series(market.frames[a['asset_id']].adj_close.values, index=pd.to_datetime(market.frames[a['asset_id']].index)) for a in cfg['assets']}).reindex(nav.index)
weights = value.div(nav.total_value, axis=0)
weights['现金及应收'] = 1-weights.sum(axis=1)
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family': font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(), 'axes.unicode_minus': False})
colors = ['#56B4E9', '#009E73', '#E69F00', '#0072B2']
fig, axes = plt.subplots(2, 3, figsize=(17, 9), constrained_layout=True)
for row, (title, idx) in enumerate([('近30日', nav.index[nav.index >= nav.index[-1]-pd.Timedelta(days=29)]), ('全周期', nav.index)]):
    ax = axes[row, 0]
    for c, color in zip(codes, colors): ax.plot(idx, (adjusted.loc[idx,c]/adjusted.loc[idx[0],c]).values, color=color, label=names[c])
    ax.plot(idx, (nav.loc[idx,'net_value']/nav.loc[idx[0],'net_value']).values, color='black', lw=2.2, label='组合')
    ax.axhline(1, color='#bbbbbb', lw=.6)
    ax.set_title(title+' · 净值走势（起点 = 1）')
    ax.legend(fontsize=8, ncol=3)
    ax = axes[row, 1]
    # 无外部资金流，累计贡献等于逐日损益 / 区间期初资产。
    part = pnl.loc[idx].copy(); part.iloc[0] = 0
    contribution = part.cumsum().div(nav.loc[idx[0], 'total_value']).mul(100)
    for c, color in zip(codes, colors): ax.plot(idx, contribution[c], color=color, label=names[c])
    total = (nav.loc[idx,'total_value']/nav.loc[idx[0],'total_value']-1)*100
    assert np.allclose(contribution.sum(axis=1), total, atol=1e-6)
    ax.plot(idx, total, color='black', lw=2.2, label='组合')
    ax.axhline(0, color='#bbbbbb', lw=.6)
    ax.set_title(title+' · 累计收益贡献（百分点）')
    ax = axes[row, 2]
    ax.stackplot(idx, *[weights.loc[idx,c] * 100 for c in weights], colors=colors+['#d9d9d9'], labels=list(names.values())+['现金及应收'])
    ax.set_ylim(0,100); ax.set_title(title+' · 持仓占比（%）'); ax.legend(fontsize=8, ncol=3, loc='lower left')
    for ax in axes[row]:
        ax.grid(axis='y', alpha=.2); ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
fig.suptitle('R8 永久组合 · 2026-08-04 投入 10 万元 · 默认滑点', fontsize=17)
fig.savefig(HERE/'curves.png', dpi=150)
plt.close(fig)
def metrics(path): return json.loads((path/'manifest.json').read_text(encoding='utf-8'))['metrics']
data = {start: {scenario: metrics(path) for scenario,path in paths.items()} for start,paths in results.items()}
(HERE/'metrics.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('期末组合', nav.total_value.iloc[-1], '末期权重', weights.iloc[-1].to_dict())
print('累计贡献百分点', contribution.iloc[-1].to_dict())
