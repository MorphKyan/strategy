# R052 固定 3× 十年国债虚拟 30 年代理审计报告

## 结论

本课题判定为 `Research-Only`，且当前 `511260_3X.SH` **不得作为实盘可交易 ETF**。真实 30 年国债 ETF 值得作为减少债券名义资金占用的长期迁移方向，但截至训练截止日 `2025-06-30`，`511090` 与 `511260` 的共同历史约 2.05 年，`511130` 约 1.25 年，均不满足大于三年的输出门槛。因此本次只形成诊断，不生成 ETF 篮子、平台配置，不运行组合回测、三滑点敏感性或最终测试。

当前固定 3× 代理存在四类关键问题：它是每日复利的收益代理而非 30 年债券定价模型；合成行情错误继承 10Y 的 `volume`、`amount`；平台把它按普通 ETF 做整手、涨跌停、滑点、拒单和盯市；两个保留配置还存在重复杠杆。真实 30Y 替换在研究语义上更正确，但在三年共同史满足前只能做影子观察，不能据此替换基线。

## 数据资格与样本隔离

- 数据文件：`platform/data/511090.csv`、`511130.csv`、`511260.csv`、`511260_3X.csv`。
- 最新交易日均为 `2026-07-10`，相对当前日期 `2026-07-11` 为 1 天，满足 7 日新鲜度。
- 完整本地范围：`511090` 为 `2023-06-13` 至 `2026-07-10`，`511130` 为 `2024-03-28` 至 `2026-07-10`，`511260` 与 `511260_3X` 均为 `2017-08-24` 至 `2026-07-10`。
- 所有代理选择与统计只截到 `2025-06-30`；未读取 `2025-07-01` 后收益指标作判断。
- 训练期重叠：`511090` 有 494 个收益观测，`2023-06-14` 至 `2025-06-30`，约 2.05 年；`511130` 有 302 个收益观测，`2024-03-29` 至 `2025-06-30`，约 1.25 年。
- 三年共同史硬门槛失败，故禁止输出候选配置并停止组合级实证。

## 当前生成与数据血缘审计

`platform/scripts/generate_leveraged_etf.py` 读取 `511260.csv` 与 `511260_hfq_factor.csv`，按 `trade_date` 左连接，因子向前填充后以 `close * hfq_factor` 得到 HFQ 价格。首日直接继承 HFQ OHLC；其后收盘和隔夜相对前收收益乘 `3.0`，日内高低相对开盘收益再乘 `3.0`。输出把价格标为 `source=simulated`、`adjust_factor=1.0`，另写全 1 的 sidecar 因子。

审计发现：

1. 缺失因子被 `ffill().fillna(1.0)` 静默补齐，没有缺失区间、来源版本或输入 hash；输出也没有公式版本和 `tradable=false`。
2. `511260_3X.csv` 的 `volume`、`amount` 与 `511260.csv` 2152 行逐行完全相同。这些字段是 10Y 的真实成交，不是虚拟 30Y 的容量。
3. 当前快照中虚拟 OHLC 没有非正数，但出现 43 行 `high` 低于 open/close/low 的行内最大值、19 行 `low` 高于 open/close/high 的行内最小值。原因是开收、日内高低分别在不同基准上放大，未在生成后强制 OHLC 包络约束。
4. 合成收益与存储的 `511260_3X` 收益最大差仅为浮点误差（`4.44e-16`），说明“每日 HFQ 收益固定乘 3”被准确实现；这只证明实现忠实，不证明经济等价。
5. 输入快照 SHA-256：`511260.csv` 为 `58398fad45e36c84cf794851e46aba6cb7b724dd508098f98f4df00f81404095`；`511260_3X.csv` 为 `0a0c6c26f86df5d67e8cfed350fd25b60991c48a4cf6079f1f2ed88b2421334a`。
6. `511090` 没有 sidecar HFQ 文件，平台使用 CSV 内 `adjust_factor`；`511130`、`511260`、`511260_3X` 使用 sidecar。分红或份额折算是否被数据供应商完整编码无法由生成脚本证明，尤其 `511090` 的调整来源缺少独立交叉校验。

## 策略、头寸与执行语义

`LocalCsvBarData` 把 sidecar 因子优先于 CSV 内因子，策略风险估计读取 `adj_close`，但执行和盯市读取原始 `close`。对虚拟序列而言，生成器已经把 HFQ 历史写成“原始”价格且因子恒为 1，因此平台不会再生成真实 ETF 的分红应收或拆分语义，而是把总收益复利路径直接当作可成交价格。

风险均衡策略中的 `vol_multipliers` 乘在估计波动率上，作用是降低目标权重，并不创建融资或保证金头寸。扫描 27 个引用 `511260_3X.SH` 的配置，发现以下两个重复放大命中：

- `platform/configs/r1_domestic_ewma_10y_bond_3x_vol.yaml`
- `platform/configs/r1_domestic_rolling_10y_bond_3x_vol.yaml`

它们先使用已 3× 的收益序列，又设置 `vol_multipliers[CN_ETF:511260_3X.SH]=3.0`。这不是 9× 实际持仓收益，却会把风险估计再乘 3、将该 sleeve 的风险预算和名义权重压低，语义与文件名“10Y 3x vol”混杂，属于硬失败。

执行层把虚拟标的配置成普通上交所 ETF：`lot_size=100`、`price_limit_pct=0.1`，按虚拟价格整手取整、检查虚拟前收推导的涨跌停、收取 ETF 费率，并用继承的 10Y `amount` 计算 `dynamic_participation` 冲击。于是订单、成交、拒单、参与率和成交容量都不是 30Y ETF 或期货的可实现结果。固定 bps 的 `default`/`stress` 同样没有融资成本、管理费、跟踪误差、买卖价差、申赎现金差额或期货保证金/基差/展期。

回测及实盘 `mark_to_market` 都用虚拟 `close × quantity`。实盘 `plan` 会为 `511260_3X` 直接输出券商下单票，但交易所不存在该代码；若真实账户无法 reconcile 同名持仓，估值还会出现代码映射断裂。因此当前数据必须显式标记 `tradable=false`，并在 live 入口拒绝出票，而不是依靠操作者理解名称中的“模拟”。

## 训练期重叠诊断

下表仅用于说明代理偏差，不用于选择或提交 ETF。`fixed3 = 3 × r(511260 HFQ)`；`rolling` 是 60 日、至少 40 日、滞后 1 日的因果波动比诊断，倍数裁剪到 `[0.5, 6]`。它仍利用短重叠期真实 ETF 收益，不能回填到上市前，更不能伪装为真实历史。

| 真实 30Y | 日收益相关（fixed3） | 年化 tracking error | 年化平均偏差 `real-fixed3` | 真实/代理波动比 | 日 MAE | 最大绝对日误差 | rolling 倍数中位数（范围） | rolling 年化 tracking error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `511090` | 0.8535 | 4.02% | -6.22% | 1.0079 | 0.1770% | 1.5478% | 2.952（1.441–3.959） | 4.12% |
| `511130` | 0.8921 | 3.79% | -6.36% | 0.9306 | 0.1771% | 0.9011% | 2.841（2.226–3.235） | 3.69% |

固定 3× 在这两个短窗口内波动量级接近真实 30Y，但相关并非 1，年化 tracking error 接近 4%，且平均收益偏差约 -6.3%/年。偏差可能混合真实 ETF 分红/折算处理、指数久期、曲线节点变化、费用与场内价格因素，不能归因于单一机制。滚动波动匹配没有对 `511090` 改善 tracking error，对 `511130` 仅小幅改善，倍数也明显时变；因此固定 3.0 不能被视为稳定结构常数。

duration+convexity/曲线节点映射分支被阻塞：仓库没有可追溯、决策时点可得且覆盖样本的 10Y/30Y 国债收益率曲线、成份券现金流、久期与凸性序列。本报告不臆造这些输入。

## 理论依据

美国 SEC 投资者资料指出，其他条件相近时期限越长，利率风险通常越高；这支持使用真实长久期资产提高单位名义资金的利率敏感度，但没有支持固定 3 倍关系。[SEC Investor Bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-86)

IMF 的主权债风险研究把 duration 描述为价格对收益率变化的一阶线性近似，把 convexity 描述为二阶曲率；较大收益率变化下同时使用两者通常优于只用 duration。由此可推断：若 10Y 与 30Y 曲线节点非平行变化，或两只指数的久期/凸性随再平衡和收益率变化，固定线性倍数会产生结构残差。[IMF 2005 工作论文](https://www.elibrary.imf.org/view/journals/001/2005/078/article-A001-en.xml)、[IMF 2006 工作论文](https://www.elibrary.imf.org/view/journals/001/2006/195/article-A001-en.xml)

上交所公告确认 `511130` 是上证 30 年期国债 ETF，且曾进行现金分红；这说明真实 ETF 具有基金合同、净值、分红和申赎现金差额等实体语义，不能由一条虚拟复利价格完整代替。[511130 分红公告](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-02-27/511130_20250227_92RG.pdf)

## 建议

1. 研究与展示层：保留 `511260_3X` 仅作 `non_tradable_duration_proxy`，补充 `source`、公式版本、输入 hash、生成时间和 `tradable=false`；将 `volume/amount` 设为空或 0，并让容量指标明确返回不可用。
2. 配置治理：停用或改名两个重复 `vol_multipliers` 配置；在配置校验中禁止 `source=simulated` 且已杠杆序列再次命中 `vol_multipliers`。
3. 实盘保护：live `plan` 必须拒绝不可交易资产，不能为 `511260_3X` 出票。虚拟标的只允许作为信号或风险参考，实际下单映射必须是用户冻结并验证过的真实 ETF。
4. 真实 30Y 路线：优先继续影子跟踪 `511090` 与 `511130` 的 HFQ、折溢价、成交额、整手偏差和公司行为；共同训练史超过三年后，才冻结候选并对 `risk_parity`、`risk_parity_ewma`、`risk_parity_ewma_dd_recovery` 运行每两自然月起点与三滑点比较。
5. 若未来补齐可追溯收益率曲线与成份券风险指标，再前推验证 duration+convexity/曲线节点代理；禁止用全样本回看拟合或把桥接数据伪装为真实 ETF 历史。

## 验证命令

```powershell
Get-Content -Raw .agents/agents/quant_researcher/agent.json
rg -n "generate_leveraged|511260_3X|vol_multipliers|slippage|lot_size|price_limit" platform -S
Get-ChildItem platform/data/511090* , platform/data/511130* , platform/data/511260*
@'
import pandas as pd
from pathlib import Path
for code in ['511090', '511130', '511260', '511260_3X']:
    path = Path('platform/data') / f'{code}.csv'
    if not path.exists():
        print(code, 'MISSING')
        continue
    frame = pd.read_csv(path)
    print(code, len(frame), frame.trade_date.min(), frame.trade_date.max(), list(frame.columns),
          'updated', frame.updated_at.iloc[-1] if 'updated_at' in frame else None)
    print('nulls', frame.isna().sum().to_dict())
'@ | .\env\python.exe -

@'
import sys
import hashlib
from pathlib import Path
from datetime import date
sys.path.insert(0, 'platform')
import pandas as pd
import numpy as np
from src.platform_core.data import LocalCsvBarData
from src.platform_core.models import Asset

root = Path('platform/data')
codes = ['511090', '511130', '511260', '511260_3X']
assets = [Asset(asset_id=code, code=code, name=code, lot_size=100) for code in codes]
data = LocalCsvBarData(root, assets)
prices = {
    code: data.frames[code].loc[data.frames[code].index <= date(2025, 6, 30), 'adj_close']
    for code in codes
}
returns = {code: series.pct_change(fill_method=None) for code, series in prices.items()}

for real in ['511090', '511130']:
    joined = pd.concat([
        returns[real].rename('real'),
        returns['511260'].mul(3).rename('fixed3'),
        returns['511260_3X'].rename('stored'),
    ], axis=1).dropna()
    error = joined.real - joined.fixed3
    rolling_real_vol = joined.real.rolling(60, min_periods=40).std().shift(1)
    rolling_10y_vol = (joined.fixed3 / 3).rolling(60, min_periods=40).std().shift(1)
    multiplier = (rolling_real_vol / rolling_10y_vol).clip(0.5, 6)
    rolling_proxy = (joined.fixed3 / 3) * multiplier
    rolling_error = (joined.real - rolling_proxy).dropna()
    print(real, {
        'n': len(joined),
        'start': str(joined.index.min()),
        'end': str(joined.index.max()),
        'years': (joined.index.max() - joined.index.min()).days / 365.25,
        'corr_fixed3': joined.real.corr(joined.fixed3),
        'te_ann_fixed3': error.std() * np.sqrt(252),
        'bias_ann_fixed3': error.mean() * 252,
        'vol_ratio_real_to_fixed3': joined.real.std() / joined.fixed3.std(),
        'mae': error.abs().mean(),
        'max_abs': error.abs().max(),
        'corr_rolling': joined.loc[rolling_error.index, 'real'].corr(rolling_proxy.loc[rolling_error.index]),
        'te_ann_rolling': rolling_error.std() * np.sqrt(252),
        'mult_median': multiplier.median(),
        'mult_min': multiplier.min(),
        'mult_max': multiplier.max(),
        'stored_diff_max': (joined.stored - joined.fixed3).abs().max(),
    })

for code in ['511260', '511260_3X']:
    frame = pd.read_csv(root / f'{code}.csv')
    print(code, {
        'nonpositive': int((frame[['open', 'high', 'low', 'close']] <= 0).sum().sum()),
        'high_breach': int((frame.high < frame[['open', 'close', 'low']].max(axis=1)).sum()),
        'low_breach': int((frame.low > frame[['open', 'close', 'high']].min(axis=1)).sum()),
        'sha256': hashlib.sha256((root / f'{code}.csv').read_bytes()).hexdigest(),
    })

source = pd.read_csv(root / '511260.csv')
proxy = pd.read_csv(root / '511260_3X.csv')
print('liquidity_equal', {
    'volume_all_equal': bool((source.volume == proxy.volume).all()),
    'amount_all_equal': bool((source.amount == proxy.amount).all()),
    'rows': len(source),
})
print('factor_files', {code: (root / f'{code}_hfq_factor.csv').exists() for code in codes})
print('quality', data.quality.notes)
'@ | .\env\python.exe -

@'
from pathlib import Path
import yaml
for path in Path('platform/configs').glob('*.yaml'):
    try:
        config = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception:
        continue
    proxies = [
        asset.get('asset_id') for asset in config.get('assets', [])
        if '511260_3X' in str(asset.get('asset_id', ''))
    ]
    multipliers = (((config.get('strategy') or {}).get('params') or {}).get('vol_multipliers', {}))
    if proxies:
        print(path.name, 'proxy', proxies, 'double', [asset_id for asset_id in proxies if asset_id in multipliers],
              'vm', multipliers)
'@ | .\env\python.exe -
```

项目环境实际布局为 `./env/python.exe`，因此按根规则使用允许的后备入口；未创建或保留临时脚本。由于三年门槛与不可交易字段污染已硬失败，本课题未运行任何 platform backtest、experiment、sensitivity 或 final test，也没有可报告的组合 turnover、`trade_count`、`order_count`、`rejection_count` artifacts。
