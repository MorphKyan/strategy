# 动态基准利率参数

`risk_parity_expected_shortfall_fixed_budget` 新增 `trend_filter_mode: fast_slow`，使用关联研究中的月度四档快慢动量。新模式默认采用3个月国债收益率，支持1个月 Shibor，也支持固定年化利率。

旧配置无需修改；未选择 `fast_slow` 时，原有均线、连续缩放和 AQR 规则完全沿用，不读取利率文件。该利率只扣减动量信号，不改变现金计息、绩效 Sharpe 基准、交易成本或成交规则。

在现有配置的 `strategy.params` 中加入：

```yaml
trend_filter_mode: fast_slow
trend_filter_risk_free:
  source: treasury_3m       # 默认值；也可使用 shibor_1m 或 fixed
  # path: data/interest_rates/treasury_3m.csv
# trend_filter_assets: [CN_ETF:159980.SZ]  # 可选，默认作用于整个 universe
```

选择固定利率：

```yaml
trend_filter_risk_free:
  source: fixed
  annual_rate: 0.02         # 小数，0.02 表示年化2%；可设0
```

动态源默认从平台 `data/interest_rates/<source>.csv` 加载；显式 `path` 按运行目录解析，平台 CLI 通常以 `platform/` 为运行目录。文件列为 `date,annual_rate_pct`，例如 `2026-10-15,1.20` 表示年化1.20%。读取时拒绝空表、重复日期、缺失日期和非有限利率。负利率允许存在。

初始快照的国债来源为中债历史查询的国债3月期限，截至2026-10-15；Shibor 来源为东财1月 Shibor 历史接口，截至2026-10-16。运行使用的 CSV 位于 `data/interest_rates/`。更新时使用同口径的新 CSV，通过 `scripts/import_signal_interest_rates.py` 合并；已有日期的冲突值会报错。此导入工具不联网，运行研究前仍须按仓库要求同步行情及利率并检查最新日期。

```bash
python3 platform/scripts/import_signal_interest_rates.py --source treasury_3m --input /path/to/new_rates.csv
```

快信号为最近完整月的超额收益，慢信号为最近12个完整月超额收益的算术均值。慢/快信号的正负对应仓位倍率：牛市 `1`、回调 `.75`、反弹 `.5`、熊市 `.25`，零视为非负。倍率作用于 ES 原始权重，余量保留现金；不再叠加旧均线过滤。可用 `trend_filter_assets` 将过滤限定到指定资产，其余资产保留原始 ES 权重。

动态利率取每个月收益区间起点**严格之前**最后一条报价，以 `annual_rate × 实际自然日数 / 365` 扣减；不使用同日起点报价、未来月均值或当前利率回填历史。起点前没有报价或报价超过14个自然日即报错，不静默退回固定利率。固定利率沿用研究口径，以 `(1 + annual_rate)^(1/12) - 1` 扣减。

至少需要13个连续完整月的价格；不足时所选资产权重为0。月末由下一交易日跨月确认；截断样本的最后一天保守要求达到当月最后一个工作日，避免把月中结束误作月末。Shibor和国债到期收益率均为信号代理，不是可实现的月度投资回报。新增参数不构成收益提升或可执行投资建议。
