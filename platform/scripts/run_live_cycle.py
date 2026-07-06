"""实盘镜像组合入口：reconcile（导入真实持仓）、plan（出明日下单票）、cycle（一键环路）。

用法（从仓库根运行，相对路径按 platform/ 解析）：

  # ① 收盘后导入真实持仓（券商 App 抄下来存成两列 CSV：code,quantity[,cost_basis]）
  .\\env\\Scripts\\python.exe platform\\scripts\\run_live_cycle.py reconcile ^
      --config configs\\baseline_r1_domestic_rolling.yaml --holdings my_holdings.csv --cash 12345.67

  # ② 生成明日下单票（打印到终端，同时落盘 tickets/ticket_<date>.csv/.txt）
  .\\env\\Scripts\\python.exe platform\\scripts\\run_live_cycle.py plan ^
      --config configs\\baseline_r1_domestic_rolling.yaml [--notify]

  # ③ 一键环路（适合 Windows 任务计划每个工作日收盘后调用）：
  #    sync 行情 → （提供 --holdings 时）reconcile → plan → （--notify 时）推送
  #    非交易日/数据未更新到当日时自动跳过，不会重复出票
  .\\env\\Scripts\\python.exe platform\\scripts\\run_live_cycle.py cycle ^
      --config configs\\baseline_r1_domestic_rolling.yaml --sync --notify

推送渠道零配置：设环境变量 RQ_SERVERCHAN_KEY（Server酱/微信）或
RQ_SMTP_HOST/RQ_SMTP_USERNAME/RQ_SMTP_PASSWORD/RQ_SMTP_TO（邮件）即自动启用，
详见 src/platform_core/notify.py 模块注释。任务计划注册示例：

  schtasks /Create /TN "RetailQuant Live Cycle" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:30 ^
      /TR "D:\\qcy_project\\strategy\\env\\Scripts\\python.exe D:\\qcy_project\\strategy\\platform\\scripts\\run_live_cycle.py cycle --config configs\\baseline_r1_domestic_rolling.yaml --sync --notify"

reconcile/plan 单独使用时，跑之前先同步行情（sync_all_market_data.py），
否则会被 7 天数据新鲜度闸门拦下。环路设计见 platform/docs/next_phase_blueprint.md §5。
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# 票据含中文，Windows 默认 GBK 控制台会乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.platform_core.live import LivePortfolio
from src.platform_core.notify import send_notification


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_portfolio(args: argparse.Namespace) -> tuple[LivePortfolio, dict]:
    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config = load_config(config_path)
    portfolio_id = args.portfolio or f"live_{config_path.stem}"
    return LivePortfolio(portfolio_id, config, output_root=args.output_root), config


def resolve_holdings_path(raw: str) -> Path:
    return (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)


def notify_and_report(title: str, text: str, config: dict) -> bool:
    ok = send_notification(title, text, config.get("notify"))
    print("推送成功" if ok else "推送失败或未配置渠道（票已落盘，见上方路径）")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="LivePortfolio: reconcile real holdings and plan next-day orders.")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", required=True, help="Platform YAML config path.")
    common.add_argument("--portfolio", help="Live portfolio id. Defaults to live_<config stem>.")
    common.add_argument("--asof-date", default=date.today().isoformat(), help="As-of date, YYYY-MM-DD. Defaults to today.")
    common.add_argument("--output-root", help="Override results/live_portfolios root (mainly for tests).")

    p_reconcile = sub.add_parser("reconcile", parents=[common], help="Overwrite state from real holdings CSV.")
    p_reconcile.add_argument("--holdings", required=True, help="CSV with header code,quantity[,cost_basis].")
    p_reconcile.add_argument("--cash", required=True, type=float, help="Real account cash balance.")

    p_plan = sub.add_parser("plan", parents=[common], help="Generate next-day order ticket from current state.")
    p_plan.add_argument("--notify", action="store_true", help="Push the ticket via configured channels.")

    p_cycle = sub.add_parser("cycle", parents=[common], help="sync -> [reconcile] -> plan -> [notify]; skips non-trading days.")
    p_cycle.add_argument("--holdings", help="Optional holdings CSV; omit to plan from the last reconciled state.")
    p_cycle.add_argument("--cash", type=float, help="Real cash balance, required together with --holdings.")
    p_cycle.add_argument("--sync", action="store_true", help="Force market data sync even if config data.fetch is false.")
    p_cycle.add_argument("--notify", action="store_true", help="Push the ticket via configured channels.")
    p_cycle.add_argument("--force", action="store_true", help="Plan from the latest bar even if asof is not a trading day.")

    args = parser.parse_args()
    portfolio, config = build_portfolio(args)

    if args.command == "reconcile":
        result = portfolio.reconcile(resolve_holdings_path(args.holdings), cash=args.cash, asof_date=args.asof_date)
        print(f"已对齐真实持仓: {result.portfolio_id} @ {result.asof_date}")
        print(f"现金 {result.cash:,.2f} + 持仓市值 {result.positions_value:,.2f} = 总值 {result.total_value:,.2f}")
        print(f"状态: {result.state_path}")
        return 0

    if args.command == "plan":
        result = portfolio.plan(asof_date=args.asof_date)
        print(result.text)
        print()
        print(f"票据: {result.ticket_txt}")
        if result.ticket_csv:
            print(f"明细: {result.ticket_csv}")
        if args.notify:
            title = f"调仓提醒 {result.plan_date}" if result.has_target else f"组合无操作 {result.plan_date}"
            notify_and_report(title, result.text, config)
        return 0

    # cycle
    holdings = resolve_holdings_path(args.holdings) if args.holdings else None
    notifier = (lambda title, text: notify_and_report(title, text, config)) if args.notify else None
    result = portfolio.cycle(
        asof_date=args.asof_date,
        holdings_csv=holdings,
        cash=args.cash,
        do_sync=True if args.sync else None,
        notifier=notifier,
        force=args.force,
    )
    if result.skipped_non_trading:
        print(f"{args.asof_date} 不是交易日（或行情尚未更新到当日），本次跳过。--force 可强制按最近交易日出票。")
        return 0
    if result.reconciled:
        print("已按 --holdings 对齐真实持仓。")
    assert result.plan is not None
    print(result.plan.text)
    print()
    print(f"票据: {result.plan.ticket_txt}")
    if result.plan.ticket_csv:
        print(f"明细: {result.plan.ticket_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
