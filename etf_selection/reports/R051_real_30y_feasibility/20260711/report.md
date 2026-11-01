# R051 真实 30 年国债 ETF 替代虚拟 30Y 的可行性诊断

## 结论先行

本课题结论为 `Research-Only`，当前不能把真实 30 年国债 ETF 写入平台配置或用于实盘迁移。硬阻塞不是相关性太低，而是截至训练截止日 `2025-06-30`，`511090` 只有 2.05 年历史、`511130` 只有 1.26 年历史，均未满足“共同历史严格超过 3 年”的仓库门槛。因此没有运行平台回测、三滑点、双月起点敏感性或 `2025-07-01` 后最终测试，也没有生成 ETF 篮子或平台配置。

训练期重叠证据显示，真实 30Y 与 `511260_3X` 的方向一致性较强，但固定 3× 并非等价复制：`511090`/`511130` 的日收益相关系数为 `0.854`/`0.892`，年化 tracking error 为 `4.02%`/`3.79%`；真实 30Y 相对 10Y 的同期回归 beta 仅为 `2.58`/`2.49`，而虚拟序列逐日严格等于 10Y 收益的 3 倍。真实 30Y 的年化波动 `7.46%`/`7.78%`，约为真实 10Y 的 `3.02×`/`2.79×`，确有提高单位名义资金风险暴露的潜力，但不能据此宣称固定节省某一比例资金，更不能把 ETF 现货持仓称为账户杠杆。

## 研究边界与官方依据

- 上交所公告确认 `511090` 于 2023-06-13 上市交易、申购赎回并实施日内回转交易：[上市交易公告](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20230612_5722454.shtml)。基金合同生效公告确认其为鹏扬中债-30 年期国债 ETF：[合同生效公告](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2023-05-20/511090_20230520_PID0.pdf)。
- `511130` 的基金合同生效日为 2024-03-20，上市公告书标明交易代码 `511130`，上交所上市日为 2024-03-28：[合同生效公告](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2024-03-21/511130_20240321_ZR28.pdf)、[上市公告书](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2024-03-25/511130_20240325_FFXI.pdf)。
- 上交所分别公告了 `511090`、`511130` 的主做市服务，但“有做市商”不等于任意规模都能以收盘价成交：[511090 做市公告](https://www.sse.com.cn/disclosure/announcement/general/jjzssgg/c/c_20230621_fff41a7871274256a120a5a6f514b3af.shtml)、[511130 做市公告](https://etf.sse.com.cn/disclosure/ssenotice/c/3afd5190b0c0479baed74b0c952e0c631.shtml)。
- 上交所 ETF 交易问答规定最低 1 手、即 100 份：[ETF 交易单位](https://www.sse.com.cn/assortment/fund/etf/question/c/c_20240118_5734754.shtml)。这意味着约 100 元净价的债券 ETF 单手名义金额约 1 万元，风险平价目标必须接受整手误差。

所有参数选择、比较和结论只使用 `2025-06-30` 及以前数据。`2025-07-01` 后数据只用于新鲜度检查，没有读取其收益、流动性分布或排序。

## 数据资格与血缘

在 2026-07-11（Asia/Shanghai）检查后，`511090`、`511260`、`511260_3X` 的最新交易日均为 `2026-07-10`；`511130` 原快照过期，已单独同步并复核为 `2026-07-10`。四者新鲜度和最新日期对齐通过。

| 标的 | 训练期首日 | 训练期末日 | 观测数 | 历史年数 | 调整来源 | 资格 |
| --- | --- | --- | ---: | ---: | --- | --- |
| `511090` | 2023-06-13 | 2025-06-30 | 495 | 2.05 | 文件内 `adjust_factor=1` | 不通过三年门槛；且无 sidecar HFQ，需继续审计分红完整性 |
| `511130` | 2024-03-28 | 2025-06-30 | 303 | 1.26 | `511130_hfq_factor.csv` | 不通过三年门槛 |
| `511260` | 2017-08-24 | 2025-06-30 | 1902 | 7.85 | `511260_hfq_factor.csv` | 对照可用 |
| `511260_3X` | 2017-08-24 | 2025-06-30 | 1902 | 7.85 | 合成序列 sidecar | 仅风险参考，不是可交易 ETF |

训练期文件 SHA-256 前 16 位分别为：`511090 dabc079e2fcfdfb8`、`511130 faa27f8a53349304`、`511260 58398fad45e36c84`、`511260_3X 0a0c6c26f86df5d6`。同步发生后，任何旧回测缓存均未复用。

## 重叠与桥接诊断

日收益使用调整收盘价。月收益取月末调整收盘价。tracking error 为真实 30Y 与虚拟 30Y 日收益差的年化标准差。下行偏差仅在虚拟 30Y 日收益为负时计算真实减虚拟的年化均值。

| 指标 | `511090` vs `511260_3X` | `511130` vs `511260_3X` |
| --- | ---: | ---: |
| 共同日收益观测 | 494 | 302 |
| 日收益相关 | 0.8535 | 0.8921 |
| 月收益观测 / 相关 | 24 / 0.8817 | 15 / 0.9177 |
| 真实/虚拟波动比 | 1.0079 | 0.9306 |
| 年化 tracking error | 4.0210% | 3.7926% |
| 下行偏差（年化） | +5.6927% | +9.4458% |
| 最大回撤：真实 / 虚拟 | -6.6883% / -6.4258% | -6.4433% / -6.4258% |
| 真实 30Y / 10Y 年化波动 | 7.4575% / 2.4664% | 7.7836% / 2.7879% |
| 真实对 10Y 回归 beta | 2.5808 | 2.4907 |

桥接只作诊断，不延长可交易历史。按时间顺序用前 60% 重叠日拟合 `r_real = alpha + beta × r_511260_3X`，后 40% 前推验证：

| 标的 | 拟合/验证日数 | `alpha`（日） | `beta` | 验证相关 | 验证年化 TE | 验证年化偏差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `511090` | 296 / 198 | -0.00439% | 0.7643 | 0.8851 | 4.5219% | -2.7047% |
| `511130` | 181 / 121 | -0.01951% | 0.8007 | 0.9042 | 3.4117% | +5.8007% |

两只 ETF 的验证 beta 均明显低于 1，且验证偏差方向不一致。这说明“固定 3× 十年 ETF”可以是久期风险参考，但不能替代真实 30Y 的收益、曲线、凸性、分红和交易路径。桥接序列不得进入订单、估值或 ETF 筛选历史长度计算。

## 流动性与容量证据

以下只使用训练期真实 `amount`，没有使用虚拟 `511260_3X` 继承的 `volume/amount`。`amount` 只能提供日成交额参与率上限的粗筛，不能代替盘口深度、买卖价差、可成交 VWAP、申赎清单或券商成交回报。

| 标的 | 日成交额中位数 | P10 | 最低值 | P10 的 1% / 5% 参与额 |
| --- | ---: | ---: | ---: | ---: |
| `511090` | 6.50 亿元 | 0.93 亿元 | 0.02 亿元 | 92.5 万元 / 462.7 万元 |
| `511130` | 16.67 亿元 | 9.29 亿元 | 3.06 亿元 | 928.8 万元 / 4643.9 万元 |

这组数据支持“可以启动前瞻影子观察”，不支持实盘容量承诺。现有日线没有历史 bid/ask、盘口档位、订单延迟、fill ratio、拒单日志、IOPV/净值同步快照，因此不能计算真实 spread、折溢价、冲击成本或未成交时长。日内 `high-low` 不能冒充 bid-ask spread；虚拟序列的成交额也不能用于容量。

## 对资金占用问题的解释

真实 30Y 现货 ETF 并不会让账户出现负现金或融资，它仍以 100% 购买金额占用名义资金。它可能改善的是“每元资金承载的利率风险”：训练重叠期真实 30Y 的波动约为 10Y 的 2.8–3.0 倍，因此等风险预算优化器理论上可能只需较低债券权重即可获得接近的债券风险贡献，把剩余预算留给现金或其他资产。但实际释放比例取决于完整协方差矩阵、权重约束、整手、费用、再平衡规则和利率曲线状态；本次三年门槛失败，禁止给出平台级节省比例。

与虚拟 `511260_3X` 相比，真实 30Y 的主要优势是可交易、拥有真实成交额和基金公司行为；主要劣势是短历史、期限指数与底层券差异、分红/HFQ链要求、价差与冲击尚未被历史盘口证明。固定 3× 的风险包括把每日线性放大误当期限复制，以及把继承自 10Y 的成交字段误当真实容量。

## 分阶段影子/实盘迁移门槛（吸收 R053 的证据要求，不认领 R053）

R053 仍保持 `Todo`。以下门槛是 R051 的预备治理框架，不选择最终 ETF、不校准收益参数，也不声称完成 R053 所需的前瞻盘口和券商订单审计。

1. `research-only`：当前阶段。硬条件为训练截止日共同历史不足三年或 HFQ/分红链未闭环。禁止生成平台配置、禁止实盘下单。每日只保存真实 30Y、真实 10Y、虚拟参考三组独立血缘。
2. `paper/shadow`：只有历史超过三年、HFQ/分红/申赎事件完整后才可申请。至少连续 60 个交易日记录可审计 bid/ask、盘口深度、IOPV/净值、100 份整手取整、目标权重偏离、缺价/停牌、订单延迟和模拟未成交；最大参与率先冻结为 P10 日成交额的 1%，不得用收盘价假设成交。
3. `小规模实盘`：影子期零数据断链，95% 以上订单在 1 个交易日内完成，实际成交加权价差不超过预冻结阈值，组合债券权重偏离连续 5 日不超过 1 个百分点；单日计划成交额同时不超过 P10 日成交额 1% 和盘口可见深度约束。任一拒单、缺价、连续未成交或现金拖累超阈值，立即回退真实 10Y。
4. `常规规模`：至少完成一个季度小规模审计，并在三种风险均衡算法、三滑点和双月起点下通过仓库全部验收后才可申请。容量必须由实际成交回报和盘口冲击曲线外推，不能由日成交额线性放大；扩大规模仍需逐级复核。

正式冻结前必须补齐：最终候选 ETF、最大 bid-ask spread、最大可见盘口参与率、最长未成交时长、最大现金拖累、最大资金规模、分红/申赎处理、回退触发器。缺少历史盘口时只能前瞻收集，禁止回填。

## 未运行项目与推荐

- 未运行平台 baseline/candidate 回测，因此 `annualized_return`、`sharpe_ratio`、`annualized_turnover`、`trade_count`、`order_count`、`rejected_order_count` 均为“不适用”，而不是 0。
- 未运行每两自然月起点敏感性、`default`/`stress`/`dynamic_participation` 三滑点和最终测试；原因是三年共同历史硬门槛失败。
- 未生成配置、未修改策略注册、未创建临时脚本。
- 推荐继续保留真实 10Y 作为实盘控制组，`511260_3X` 只作不可交易风险参考；真实 30Y 进入前瞻影子观察。最早在 `511090` 截至 `2026-06-13` 后才可能达到“约三年”，但仓库要求严格超过三年，届时仍须以实际共同交易日重新审计；`511130` 更晚。

## 精确命令

项目环境实际布局为 `env/python.exe`，因此按根规则使用该解释器：

```powershell
# 首次本地资格检查（发现 511130 过期）
@'
from pathlib import Path
import pandas as pd
for s in ['511090','511130','511260','511260_3X']:
    p=Path('platform/data')/f'{s}.csv'; f=Path('platform/data')/f'{s}_hfq_factor.csv'
    print(s,'price_exists',p.exists(),'factor_exists',f.exists())
    if p.exists():
        d=pd.read_csv(p); print('rows',len(d),'first',d.trade_date.min(),'last',d.trade_date.max(),'updated_at',d.updated_at.iloc[-1],'last_amount',d.amount.iloc[-1])
    if f.exists():
        x=pd.read_csv(f); print('factor_rows',len(x),'factor_first',x.trade_date.min(),'factor_last',x.trade_date.max())
'@ | .\env\python.exe -

# 仅同步缺口符号 511130；内部调用 MarketDataStore.sync_assets(fetch=True)
$env:PYTHONPATH='platform'; @'
from datetime import datetime
from pathlib import Path
from src.platform_core.data_store import MarketDataStore, assets_from_config
asset=[{"asset_id":"CN_ETF:511130.SH","code":"511130","name":"30年国债ETF博时","asset_type":"etf","exchange":"SH","currency":"CNY","lot_size":100,"price_limit_pct":0.1}]
r=MarketDataStore(Path('platform/data')).sync_assets(assets_from_config(asset),start='2010-01-01',end=datetime.now().strftime('%Y-%m-%d'),fetch=True)
print('\n'.join(r.notes))
'@ | .\env\python.exe -

# 训练期重叠、60/40 前推桥接、流动性与 hash 诊断
@'
from pathlib import Path
import hashlib, numpy as np, pandas as pd
D=Path('platform/data'); cutoff=pd.Timestamp('2025-06-30')
def load(s):
    d=pd.read_csv(D/f'{s}.csv'); d.trade_date=pd.to_datetime(d.trade_date); d=d.set_index('trade_date').sort_index()
    factor=pd.Series(pd.to_numeric(d.adjust_factor,errors='coerce').fillna(1).values,index=d.index); src='embedded_adjust_factor'
    fp=D/f'{s}_hfq_factor.csv'
    if fp.exists():
        f=pd.read_csv(fp); f.trade_date=pd.to_datetime(f.trade_date); factor=f.set_index('trade_date').hfq_factor.reindex(d.index).ffill().fillna(1); src='sidecar_hfq'
    d['adj_close']=d.close*factor
    return d[d.index<=cutoff],src
X={s:load(s) for s in ['511090','511130','511260','511260_3X']}
for s,(d,src) in X.items():
    print('QUAL',s,src,d.index.min().date(),d.index.max().date(),len(d),'years',(d.index.max()-d.index.min()).days/365.25,'amount_med',d.amount.median(),'p10',d.amount.quantile(.1),'min',d.amount.min(),'zero',int((d.amount<=0).sum()),'ohlc_range_bps_med',(((d.high-d.low)/d.close)*1e4).median(),'hash',hashlib.sha256((D/f'{s}.csv').read_bytes()).hexdigest()[:16])
def mdd(r):
    w=(1+r).cumprod(); return (w/w.cummax()-1).min()
for real in ['511090','511130']:
    dr=X[real][0]; dv=X['511260_3X'][0]; d10=X['511260'][0]
    z=pd.concat([dr.adj_close.pct_change().rename('real'),dv.adj_close.pct_change().rename('virt'),d10.adj_close.pct_change().rename('ten')],axis=1).dropna()
    k=int(len(z)*.6); fit=z.iloc[:k]; test=z.iloc[k:]
    beta=np.cov(fit.virt,fit.real,ddof=1)[0,1]/np.var(fit.virt,ddof=1); alpha=fit.real.mean()-beta*fit.virt.mean(); err=test.real-(alpha+beta*test.virt)
    beta10=np.cov(z.ten,z.real,ddof=1)[0,1]/np.var(z.ten,ddof=1)
    monthly=pd.concat([dr.adj_close.resample('ME').last().pct_change().rename('real'),dv.adj_close.resample('ME').last().pct_change().rename('virt')],axis=1).dropna(); amount=dr.loc[z.index,'amount']
    print('OVERLAP',real,'n',len(z),'from',z.index.min().date(),'to',z.index.max().date(),'daily_corr',z.real.corr(z.virt),'monthly_n',len(monthly),'monthly_corr',monthly.real.corr(monthly.virt),'vol_real_ann',z.real.std()*np.sqrt(252),'vol_ten_ann',z.ten.std()*np.sqrt(252),'vol_virt_ann',z.virt.std()*np.sqrt(252),'vol_ratio',z.real.std()/z.virt.std(),'beta10',beta10,'raw_TE_ann',(z.real-z.virt).std()*np.sqrt(252),'down_bias_ann',(z.loc[z.virt<0,'real']-z.loc[z.virt<0,'virt']).mean()*252,'mdd_real',mdd(z.real),'mdd_virt',mdd(z.virt),'fit_n',len(fit),'test_n',len(test),'alpha_daily',alpha,'beta',beta,'test_corr',test.real.corr(test.virt),'test_TE_ann',err.std()*np.sqrt(252),'test_bias_ann',err.mean()*252,'test_rmse_daily',np.sqrt(np.mean(err**2)),'amount_med',amount.median(),'amount_p10',amount.quantile(.1),'amount_min',amount.min(),'cap1_p10',amount.quantile(.1)*.01,'cap5_p10',amount.quantile(.1)*.05,'3x_identity_max_error',np.max(np.abs(z.virt-3*z.ten)))
'@ | .\env\python.exe -
```

以上命令可从仓库根目录直接重放。本研究没有覆盖或复用历史生成结果。
