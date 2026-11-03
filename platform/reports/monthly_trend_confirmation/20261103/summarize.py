"""由实际运行指标生成报告表格。"""
import json
import sys
from pathlib import Path

import pandas as pd

output = Path(sys.argv[1])
rows = pd.read_csv(output / "metrics.csv")
provenance = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
skipped = pd.DataFrame(json.loads((output / "skipped.json").read_text(encoding="utf-8")))
assert not rows.duplicated(["universe", "scenario", "phase", "runtime_start", "mode"]).any()
assert rows.groupby(["universe", "scenario", "phase", "runtime_start"]).size().eq(10).all()
lines = [
    "# 月末均线确认期与缓冲带",
    "",
    "检验月末趋势确认能否改善 20 万元 ES252 FHS 组合的成本后表现。每月最后一个共同交易日用收盘信号决策，最早在下一共同交易日成交。纯月频与 1 日确认共用一组结果。",
    "",
    "每个标的独立维护趋势状态。确认期要求最近 N 日的收盘价与各日 200 日 SMA 的相对位置一致，未确认则沿用上次状态。缓冲带仅在收盘价越过当日 SMA 上下对应百分比时切换。首个可用月末以当天原始趋势初始化。沿用两份配置的佣金、最小交易单位、调仓阈值和执行容忍度，分别运行默认和固定基点压力滑点。",
    "",
    "ETF 信号使用平台复权收盘价，成交采用原始报价，净值计入公司行动。代理组使用指数、期货主力连续报价及黄金 ETF，合约粒度和指数成交仅为研究模拟。两组分别以自身 1 日确认作对照。",
    "",
    "敏感性按每月首个共同交易日重启，保留预热现金期。每次重新积累 252 个共同日收益。样本截止前若没有足以产生月末信号并在下一日执行的机会，跳过。各起点共用终点，结果高度重叠，胜出数仅用于敏感性描述。",
    "",
]
for name in ("etf", "proxy"):
    info = provenance[name]
    cohort = rows[rows.universe.eq(name)]
    late = skipped[skipped.universe.eq(name)]
    full = cohort[cohort.phase.eq("full")]
    sens = cohort[cohort.phase.eq("sensitivity")]
    lines += [
        f"## {'实际 ETF' if name == 'etf' else '长期指数代理'}",
        "",
        f"共同样本 {info['start']} 至 {info['end']}，{info['common_observations']} 个交易日。完整样本首次成交 {full.loc[full['mode'].eq('confirm1'), 'first_trade'].iloc[0]}。有效月度起点 {sens.runtime_start.nunique()} 个，跳过 {len(late)} 个（{late.runtime_start.min()} 至 {late.runtime_start.max()}）。",
        "",
        "| 模式 | 滑点 | 年化收益 | 波动 | Sharpe | 最大回撤 | 年化换手 | 成交/订单/拒单 | 最大待执行数 | 平均现金 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in full.itertuples():
        lines.append(f"| {r.mode} | {r.scenario} | {r.annualized_return:.2%} | {r.annualized_volatility:.2%} | {r.sharpe_ratio:.3f} | {r.max_drawdown:.2%} | {r.annualized_turnover:.2%} | {r.trade_count}/{r.order_count}/{r.rejected_order_count} | {r.max_pending_intent_count} | {r.average_cash_weight:.2%} |")
    columns = ["annualized_return", "sharpe_ratio", "max_drawdown", "annualized_turnover"]
    baseline = sens[sens["mode"].eq("confirm1")].set_index(["scenario", "runtime_start"])[columns]
    lines += ["", "下表为相对同起点基线的配对中位差，回撤为有符号差，正值表示回撤收窄。", "",
              "| 模式 | 滑点 | 年化收益差 | Sharpe 差 | 回撤差 | 换手差 | Sharpe 胜出 |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for (mode, scenario), group in sens.groupby(["mode", "scenario"], sort=False):
        delta = group.set_index(["scenario", "runtime_start"])[columns] - baseline.reindex(group.set_index(["scenario", "runtime_start"]).index)
        a, s, d, t = delta.median()
        wins = (delta.sharpe_ratio > 1e-10).sum()
        lines.append(f"| {mode} | {scenario} | {a:+.2%} | {s:+.3f} | {d:+.2%} | {t:+.2%} | {wins}/{len(delta)} |")
    ranks = sens.groupby(["scenario", "runtime_start"]).sharpe_ratio.rank(ascending=False, method="min")
    best_counts = sens.assign(rank=ranks).query("rank == 1").groupby(["scenario", "mode"]).size()
    for scenario, counts in best_counts.groupby(level=0):
        summary = "、".join(f"{mode} {count} 次" for (_, mode), count in counts.sort_values(ascending=False).items())
        lines += ["", f"{scenario} 的起点内 Sharpe 第一名（允许并列）为 {summary}。"]
    no_trades = sens.trade_count.eq(0).sum()
    calendar = pd.read_csv(output / f"{name}_ratio.csv", usecols=[0]).iloc[:, 0].tolist()
    month_ends = [i for i, (day, nxt) in enumerate(zip(calendar, calendar[1:])) if day[:7] != nxt[:7]]
    single = [start for start in sens.runtime_start.unique()
              if sum(i >= calendar.index(start) + 252 for i in month_ends) == 1]
    lines += ["", f"有效起点中实际成交为零的运行有 {no_trades} 项。仅有一次可执行月末信号的起点为 { '、'.join(single) or '无' }。这类起点只有共同初始化，没有机会区分确认规则。", ""]
lines += ["## 复现", "", r"`./env/Scripts/python.exe platform/reports/monthly_trend_confirmation/20261103/reproduce.py --workers 8`",
          "", f"Git 基线 `{provenance['git_head']}`。行情来自本地 `platform/data`，数据和策略源码哈希见 `provenance.json`。",
          "", f"Python `{provenance['python']}`。依赖 `{json.dumps(provenance['dependencies'])}`。"]
(output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
