"""真实账户的手机邮件：只读台账、六图归因和内嵌图片正文。"""
from __future__ import annotations

import html
import io
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import assets_from_config
from src.platform_core.metrics import _annualized_growth
from src.platform_core.notify import markdown_to_html

COLORS = ["#56B4E9", "#009E73", "#E69F00", "#0072B2", "#D55E00", "#CC79A7"]
SHORT_NAMES = {"510300": "沪深300", "563020": "红利低波", "518880": "黄金",
               "511130": "30年国债", "159985": "豆粕", "159980": "有色"}


def load_daily_history(config: dict, portfolio_dir: Path, asof: str):
    """核对真实证券、现金及应收，禁止用目标持仓或残差补造归因。"""
    nav = pd.read_csv(portfolio_dir / "real_nav.csv", parse_dates=["date"]).set_index("date").sort_index()
    nav = nav.loc[:asof]
    if nav.empty or not nav.index.is_unique or nav.index[-1] != pd.Timestamp(asof):
        raise ValueError("缺少当日净值或日期重复")
    fields = ["total_value", "unit_nav", "cash", "external_flow"]
    if not np.isfinite(nav[fields]).all().all() or (nav[["total_value", "unit_nav"]] <= 0).any().any():
        raise ValueError("净值、现金或资金流无效")
    assets = config["assets"]
    codes = [str(a["code"]) for a in assets]
    if not codes or len(codes) > len(COLORS) or len(codes) != len(set(codes)):
        raise ValueError("六图邮件需要1至6只不同的配置资产")
    data_config = config.get("data", {})
    market = LocalCsvBarData(data_config.get("market_store_dir") or data_config.get("data_dir", "data"),
                             assets_from_config(assets))
    raw, adjusted, latest_dates = {}, {}, set()
    for asset in assets:
        code = str(asset["code"])
        frame = market.frames[asset["asset_id"]]
        latest = pd.Timestamp(frame.index[-1])
        latest_dates.add(latest)
        if (pd.Timestamp(date.today()) - latest).days > 7:
            raise ValueError(f"{code} 行情超过7自然日")
        frame = frame.copy()
        frame.index = pd.to_datetime(frame.index)
        raw[code], adjusted[code] = frame.close, frame.adj_close
    if len(latest_dates) != 1:
        raise ValueError("成分行情最新日期不一致")
    prices = pd.DataFrame(raw).loc[nav.index[0]:nav.index[-1]]
    if prices.isna().any().any() or not prices.index.equals(nav.index):
        raise ValueError("账户净值日期与成分行情未完整对齐")
    adjusted = pd.DataFrame(adjusted).reindex(nav.index)
    ledger = pd.read_csv(portfolio_dir / "execution_ledger.csv", dtype={"code": str}, parse_dates=["date"])
    ledger = ledger[ledger.date <= pd.Timestamp(asof)]
    quantity = pd.DataFrame(0., index=nav.index, columns=codes)
    costs = quantity.copy()
    income = quantity.copy()
    cash = pd.Series(0., index=nav.index)
    receivable = pd.Series(0., index=nav.index)
    recognized, paid = set(), set()

    def add_on_day(frame, code, day, amount):
        # 台账可能在休市日登记现金；记入其后首个真实估值日。
        index = nav.index.searchsorted(pd.Timestamp(day))
        if index < len(nav):
            frame.iloc[index, frame.columns.get_loc(code)] += amount

    allowed = {"INITIAL_CAPITAL", "DEPOSIT", "WITHDRAWAL", "BUY", "SELL",
               "INTERNAL_TRANSFER_IN", "DIVIDEND_RECEIVABLE", "DIVIDEND_PAYMENT"}
    for row in ledger.itertuples():
        if row.event not in allowed:
            raise ValueError("成交流水存在不支持的事件")
        numbers = [row.quantity, row.gross_amount, row.fee, row.cash_delta, row.external_flow]
        if not np.isfinite(numbers).all() or min(row.quantity, row.gross_amount, row.fee) < 0:
            raise ValueError("成交流水金额或数量无效")
        mask = nav.index >= row.date
        cash.loc[mask] += row.cash_delta
        if row.event in {"BUY", "SELL", "INTERNAL_TRANSFER_IN"}:
            if row.code not in codes or row.quantity <= 0:
                raise ValueError("成交流水资产或数量不匹配")
            sign = -1 if row.event == "SELL" else 1
            quantity.loc[mask, row.code] += sign * row.quantity
            add_on_day(costs, row.code, row.date, sign * row.gross_amount + row.fee)
        elif row.event in {"DIVIDEND_RECEIVABLE", "DIVIDEND_PAYMENT"}:
            if row.code not in codes:
                raise ValueError("股息资产不在配置中")
            if row.event == "DIVIDEND_RECEIVABLE":
                add_on_day(income, row.code, row.date, row.gross_amount)
                receivable.loc[mask] += row.gross_amount
                recognized.add((row.code, row.date.strftime("%Y-%m-%d")))
            else:
                receivable.loc[mask] -= row.gross_amount
                paid.add((row.code, row.date.strftime("%Y-%m-%d")))

    # 每日环路自动股息存于状态，而人工确认的旧股息存于流水；按资产与日期去重。
    state = json.loads((portfolio_dir / "portfolio_state.json").read_text(encoding="utf-8"))
    asset_codes = {a["asset_id"]: str(a["code"]) for a in assets}
    for event in state.get("live_accounting", {}).get("dividends", {}).values():
        code = asset_codes[event["asset_id"]]
        amount = float(event["amount"])
        if not np.isfinite(amount) or amount < 0:
            raise ValueError("自动股息金额无效")
        ex, payment = event["ex_date"], event["payment_date"]
        if ex <= asof and (code, ex) not in recognized:
            add_on_day(income, code, ex, amount)
            receivable.loc[nav.index >= pd.Timestamp(ex)] += amount
        if payment <= asof and (code, payment) not in paid:
            receivable.loc[nav.index >= pd.Timestamp(payment)] -= amount
            cash.loc[nav.index >= pd.Timestamp(payment)] += amount
    value = quantity * prices
    if (quantity < -1e-8).any().any() or (receivable < -.011).any():
        raise ValueError("历史持仓或应收股息为负")
    if not np.allclose(cash, nav.cash, rtol=0, atol=.011):
        raise ValueError("现金与已确认成交流水不一致")
    if not np.allclose(value.sum(axis=1) + cash + receivable, nav.total_value, rtol=0, atol=.011):
        raise ValueError("持仓市值与真实净值台账不一致")
    pnl = value.diff() - costs + income
    pnl.iloc[0] = 0.
    expected = nav.total_value.diff() - nav.external_flow
    if not np.allclose(pnl.sum(axis=1).iloc[1:], expected.iloc[1:], rtol=0, atol=.011):
        raise ValueError("资产损益无法还原组合损益")
    returns = (expected / nav.total_value.shift()).fillna(0.)
    chain = (1 + returns).cumprod()
    if not np.allclose(chain, nav.unit_nav / nav.unit_nav.iloc[0], rtol=0, atol=2e-8):
        raise ValueError("资金流与单位净值不一致")
    linked = pnl.div(nav.total_value.shift(), axis=0).mul(chain.shift(), axis=0).fillna(0.)
    weights = value.div(nav.total_value, axis=0)
    weights["cash"] = cash / nav.total_value
    weights["receivables"] = receivable / nav.total_value
    if not np.allclose(weights.sum(axis=1), 1., atol=1e-8, rtol=0):
        raise ValueError("成分权重加总不为100%")
    return nav, adjusted, weights, linked, chain


def _chart(curves, total, kind, colors):
    # Agg + 独立 Figure 不依赖桌面或 pyplot 全局后端，兼容定时任务的WSL环境。
    from matplotlib import dates as mdates
    from matplotlib import font_manager
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter

    family = next((f.name for f in font_manager.fontManager.ttflist
                   if f.name in {"Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Zen Hei"}), None)
    if family is None:
        for path in [Path("C:/Windows/Fonts/msyh.ttc"), Path("/mnt/c/Windows/Fonts/msyh.ttc")]:
            if path.exists():
                font_manager.fontManager.addfont(str(path))
                family = font_manager.FontProperties(fname=str(path)).get_name()
                break
    font = font_manager.FontProperties(family=family or "sans-serif", size=11.5)
    fig = Figure(figsize=(3.5, 3.8), dpi=200, facecolor="white")
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    fig.subplots_adjust(left=.19, right=.975, top=.965, bottom=.14)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#E8EDF3", linewidth=.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, pad=7, colors="#64748B")
    ax.yaxis.set_major_locator(MaxNLocator(4))
    index = curves.index
    if kind == "weights":
        ax.stackplot(index, *[curves[c] for c in curves], colors=[colors[c] for c in curves],
                     edgecolor="white", linewidth=.4)
        ax.set_ylim(0, 1)
        ax.set_yticks([0, .25, .5, .75, 1])
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    else:
        styles, markers = ["--", "-", "-.", "-", "--", ":"], ["o", "s", "^", "D", "v", "P"]
        for i, code in enumerate(curves):
            ax.plot(index, curves[code], color=colors[code], linewidth=1.7, linestyle=styles[i],
                    marker=markers[i], markersize=2.8, markevery=max(1, len(index)//5), markeredgewidth=.3)
        ax.plot(index, total, color="black", linewidth=2.4, zorder=10)
        ax.axhline(1 if kind == "nav" else 0, color="#CBD5E1", linestyle="--", linewidth=.7, zorder=0)
        ax.yaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{v:.2f}" if kind == "nav" else f"{v:+.1f}"))
    if len(index) > 1:
        first, last = index[0], index[-1]
        mid = index[np.argmin(abs(index - (first + (last-first)/2)))]
        ax.set_xlim(first, last)
        ax.set_xticks(sorted({first, mid, last}))
    else:
        ax.set_xlim(index[0] - pd.Timedelta(days=1), index[0] + pd.Timedelta(days=1))
        ax.set_xticks(index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font)
    if len(index) > 1:
        ax.get_xticklabels()[0].set_ha("left")
        ax.get_xticklabels()[-1].set_ha("right")
    buffer = io.BytesIO()
    canvas.print_png(buffer)
    fig.clear()
    return buffer.getvalue()


def build_daily_email(config: dict, portfolio_dir: Path, asof: str, digest: str):
    nav, adjusted, weights, linked, chain = load_daily_history(config, portfolio_dir, asof)
    codes = list(adjusted)
    colors = dict(zip(codes, COLORS))
    colors.update(cash="#D9D9D9", receivables="#595959")
    names = {str(a["code"]): SHORT_NAMES.get(str(a["code"]), a.get("name", str(a["code"])))
             for a in config["assets"]}
    names.update(cash="现金", receivables="应收股息")
    cards, images = [], {}
    for key, start, period in [("recent30", nav.index[-1]-pd.Timedelta(days=29), "近30日"),
                               ("full", nav.index[0], "全周期")]:
        index = nav.index[nav.index >= start]
        for kind, title in [("nav", "净值走势"), ("contribution", "收益贡献"), ("weights", "持仓占比")]:
            if kind == "nav":
                curves = adjusted.loc[index] / adjusted.loc[index[0]]
                total = nav.loc[index, "unit_nav"] / nav.loc[index[0], "unit_nav"]
                values = {c: f"{curves[c].iloc[-1]-1:+.2%}" for c in codes}
                metric = f"组合 {total.iloc[-1]-1:+.2%}"
                note = "首日 = 1 · 黑线为组合 · 成分为后复权走势"
            elif kind == "contribution":
                increments = linked.loc[index].copy()
                increments.iloc[0] = 0.
                curves = increments.cumsum() / chain.loc[index[0]] * 100
                total = (chain.loc[index] / chain.loc[index[0]] - 1) * 100
                if not np.allclose(curves.sum(axis=1), total, rtol=0, atol=1e-5):
                    raise ValueError("累计贡献加总失败")
                values = {c: f"{curves[c].iloc[-1]:+.3f} pp" for c in codes}
                metric = f"合计 {total.iloc[-1]:+.3f} pp"
                note = "单位：百分点（pp）· 各项相加等于组合收益"
            else:
                curves = weights.loc[index, weights.loc[index].max() > 1e-10]
                total = None
                values = {c: f"{curves[c].iloc[-1]:.1%}" for c in curves}
                metric = f"现金 {weights.loc[index[-1], 'cash']:.1%}"
                note = "图例为期末比例 · 未持有资产省略"
            cid = f"{key}_{kind}"
            images[cid] = _chart(curves, total, kind, colors)
            cells = [f'<td style="width:33.33%;padding:5px 3px;font-size:13px;line-height:1.45;vertical-align:top;">'
                     f'<span style="color:{colors[c]};">■</span> {html.escape(names[c])}<br>'
                     f'<span style="color:#475569;">{v}</span></td>' for c, v in values.items()]
            while len(cells) % 3:
                cells.append("<td></td>")
            legend = '<table role="presentation" style="width:100%;table-layout:fixed;border-collapse:collapse;">' + ''.join(
                '<tr>' + ''.join(cells[i:i+3]) + '</tr>' for i in range(0, len(cells), 3)) + '</table>'
            cards.append(f'<tr><td style="padding:18px 14px 16px;background:white;border-bottom:8px solid #F1F4F8;">'
                         f'<div style="font-size:19px;font-weight:700;">{len(cards)+1:02d}　{period} · {title}</div>'
                         f'<div style="font-size:13px;color:#64748B;margin:3px 0 6px;">{index[0]:%m.%d}—{index[-1]:%m.%d}　'
                         f'<strong style="color:#172033;">{metric}</strong></div>'
                         f'<img width="320" src="cid:{cid}" alt="{period}{title}" style="display:block;width:100%;max-width:320px;height:auto;margin:0 auto;border:0;">'
                         f'{legend}<div style="font-size:12px;color:#64748B;margin-top:9px;">{note}</div></td></tr>')
    current = nav.iloc[-1]
    annual = _annualized_growth(nav.unit_nav)
    annual_text = f"{annual:+.2%}" if annual is not None else "—"
    day = "暂无前日估值"
    if len(nav) > 1:
        previous = nav.iloc[-2]
        day = (f"当日 {current.total_value-previous.total_value-current.external_flow:+,.2f} 元"
               f"（{current.unit_nav/previous.unit_nav-1:+.2%}）")
    # 原日报的盈亏核对、持仓涨跌及完整目标监控保留为可复制文字。
    details = markdown_to_html(digest).split("<body", 1)[1].split(">", 1)[1].rsplit("</body>", 1)[0]
    body = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#F1F4F8;color:#172033;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif;line-height:1.6;-webkit-text-size-adjust:100%;">
<table role="presentation" style="width:100%;table-layout:fixed;border-collapse:collapse;"><tr><td align="center">
<table role="presentation" style="width:100%;max-width:400px;table-layout:fixed;border-collapse:collapse;text-align:left;">
<tr><td style="padding:24px 18px 20px;background:white;border-bottom:8px solid #F1F4F8;">
<div style="font-size:12px;color:#64748B;">{asof} 收盘</div><h1 style="font-size:25px;margin:10px 0 16px;">组合日报</h1>
<div style="font-size:13px;color:#64748B;">成立以来年化收益</div><div style="font-size:32px;font-weight:700;">{annual_text}</div>
<div style="font-size:12px;color:#64748B;margin:3px 0 16px;">252个交易日复利折算 · {len(nav)-1}期收益观测{' · 短期样本' if len(nav) <= 252 else ''}</div>
<div style="font-size:13px;color:#64748B;">总资产（元）</div><div style="font-size:30px;font-weight:700;">{current.total_value:,.2f}</div>
<div style="font-size:15px;">{day}</div><div style="font-size:15px;margin-top:14px;">成立以来 <strong>{current.unit_nav/nav.unit_nav.iloc[0]-1:+.2%}</strong><br>现金 <strong>{current.cash:,.2f}</strong> 元</div>
</td></tr>{''.join(cards)}
<tr><td style="padding:16px 14px;background:white;overflow-wrap:anywhere;word-break:break-word;font-size:15px;">{details}</td></tr>
<tr><td style="padding:16px 18px 28px;font-size:12px;color:#64748B;">真实账户 · 净值与贡献剔除外部资金流，贡献含真实费用与股息。<br>全周期 {nav.index[0]:%Y-%m-%d}—{nav.index[-1]:%Y-%m-%d}</td></tr>
</table></td></tr></table></body></html>'''
    return body, images, annual_text
