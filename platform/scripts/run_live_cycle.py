"""实盘镜像组合入口：reconcile（导入真实持仓）与 plan（生成明日下单票）。

用法（从仓库根运行，相对路径按 platform/ 解析）：

  # ① 收盘后导入真实持仓（券商 App 抄下来存成两列 CSV：code,quantity[,cost_basis]）
  .\\env\\Scripts\\python.exe platform\\scripts\\run_live_cycle.py reconcile ^
      --config configs\\baseline_r1_domestic_rolling.yaml --holdings my_holdings.csv --cash 12345.67

  # ② 生成明日下单票（打印到终端，同时落盘 tickets/ticket_<date>.csv/.txt）
  .\\env\\Scripts\\python.exe platform\\scripts\\run_live_cycle.py plan ^
      --config configs\\baseline_r1_domestic_rolling.yaml

跑之前先同步行情（sync_all_market_data.py），否则会被 7 天数据新鲜度闸门拦下。
环路设计见 platform/docs/next_phase_blueprint.md §5。
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


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_portfolio(args: argparse.Namespace) -> LivePortfolio:
    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config = load_config(config_path)
    portfolio_id = args.portfolio or f"live_{config_path.stem}"
    return LivePortfolio(portfolio_id, config, output_root=args.output_root)


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

    sub.add_parser("plan", parents=[common], help="Generate next-day order ticket from current state.")

    args = parser.parse_args()
    portfolio = build_portfolio(args)

    if args.command == "reconcile":
        holdings = (ROOT / args.holdings).resolve() if not Path(args.holdings).is_absolute() else Path(args.holdings)
        result = portfolio.reconcile(holdings, cash=args.cash, asof_date=args.asof_date)
        print(f"已对齐真实持仓: {result.portfolio_id} @ {result.asof_date}")
        print(f"现金 {result.cash:,.2f} + 持仓市值 {result.positions_value:,.2f} = 总值 {result.total_value:,.2f}")
        print(f"状态: {result.state_path}")
        return 0

    result = portfolio.plan(asof_date=args.asof_date)
    print(result.text)
    print()
    print(f"票据: {result.ticket_txt}")
    if result.ticket_csv:
        print(f"明细: {result.ticket_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
