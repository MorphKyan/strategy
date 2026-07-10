"""实盘月度归因报告（蓝图 A5）：真实账户 vs 影子模型的净值差异体检。

用法（从仓库根运行，相对路径按 platform/ 解析）：

  # 出上个自然月的归因报告（默认）
  .\\env\\Scripts\\python.exe platform\\scripts\\report_live_attribution.py ^
      --live-id live_r8_permanent_100k --shadow-id sim_r8_permanent_shadow [--notify]

  # 指定月份
  ... --month 2026-07

前置：影子组合需每日跟跑（run_live_cycle.py cycle --shadow <sim_id>）。
报告写入 platform/reports/live/<YYYY-MM>_<live_id>_attribution.md
（含个人财务数据，该目录已 gitignore 不入库）。
每月 1 日定时运行的注册示例：

  schtasks /Create /TN "RetailQuant Monthly Attribution" /SC MONTHLY /D 1 /ST 20:00 ^
      /TR "D:\\qcy_project\\strategy\\env\\Scripts\\python.exe D:\\qcy_project\\strategy\\platform\\scripts\\report_live_attribution.py --live-id live_r8_permanent_100k --shadow-id sim_r8_permanent_shadow --notify"
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.platform_core.attribution import (
    build_live_attribution,
    load_real_nav,
    load_shadow_nav,
    month_window,
    previous_month,
    render_attribution_md,
)
from src.platform_core.notify import send_notification


def main() -> int:
    parser = argparse.ArgumentParser(description="Monthly live-vs-shadow NAV attribution report.")
    parser.add_argument("--live-id", required=True, help="Live portfolio id under results/live_portfolios/.")
    parser.add_argument("--shadow-id", required=True, help="Shadow sim portfolio id under results/sim_portfolios/.")
    parser.add_argument("--month", help="YYYY-MM. Defaults to the previous calendar month.")
    parser.add_argument("--live-root", default="results/live_portfolios")
    parser.add_argument("--sim-root", default="results/sim_portfolios")
    parser.add_argument("--report-root", default="reports/live")
    parser.add_argument("--notify", action="store_true", help="Push the report via configured channels.")
    args = parser.parse_args()

    month = args.month or previous_month(date.today())
    start, end = month_window(month)

    real_rows = load_real_nav(Path(args.live_root) / args.live_id)
    shadow_rows = load_shadow_nav(Path(args.sim_root) / args.shadow_id)
    result = build_live_attribution(real_rows, shadow_rows, start, end)
    report = render_attribution_md(result, args.live_id, args.shadow_id, month)

    report_dir = Path(args.report_root)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{month}_{args.live_id}_attribution.md"
    report_path.write_text(report + "\n", encoding="utf-8")

    print(report)
    print()
    print(f"报告: {report_path}")
    if args.notify:
        ok = send_notification(f"归因月报 {month}", report, None)
        print("推送成功" if ok else "推送失败或未配置渠道（报告已落盘）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
