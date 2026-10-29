# -*- coding: utf-8 -*-
"""中债 30 年期国债财富指数数据按需抓取脚本。

背景：
在杠杆/久期策略研究中，除了使用 10 年期国债 ETF 3x 虚拟放大（`511260_3X`）或场内 30 年国债 ETF 现货（如 `511090`），
亦可引入中债 30 年期国债财富（总值）指数（标的代码 `CBA21801`）作为无跟踪误差的久期与收益基准。

数据源：
中债官方指数查询 API（`yield.chinabond.com.cn`）。
节点标识：`8a8b2cef77b239980177b485d20a6379`（ChinaBond 30-year Treasury Bond Index）。

输出列契约（与平台 `MarketDataStore` 行情契约一致）：
`trade_date, open, high, low, close, volume, amount, adjust_factor, source, updated_at`

用法：
  .\\env\\python.exe platform\\scripts\\fetch_chinabond_30y.py
  .\\env\\python.exe platform\\scripts\\fetch_chinabond_30y.py --output-filename CBA21801.csv
"""

import argparse
import os
import sys
from pathlib import Path

ORIG_CWD = Path.cwd()
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.platform_core.data_store import write_csv_stable  # noqa: E402

from scripts.sync_index_benchmark_data import fetch_chinabond_index, merge_chinabond_history  # noqa: E402


def resolve_path(path_str: str, root_dir: Path, orig_cwd: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    if (orig_cwd / p).exists():
        return orig_cwd / p
    if (root_dir / p).exists():
        return root_dir / p
    return root_dir / p


def main() -> int:
    orig_cwd = Path(os.environ.get("INIT_CWD", ORIG_CWD))
    parser = argparse.ArgumentParser(description="按需抓取中债 30 年期国债财富指数数据并落盘。")
    parser.add_argument("--data-dir", default="data", help="数据输出目录，默认为 data。")
    parser.add_argument("--output-filename", default="CBA21801.csv", help="输出文件名，默认为 CBA21801.csv。")
    parser.add_argument("--timeout", type=int, default=15, help="网络请求超时时间（秒）。")

    args = parser.parse_args()

    data_dir = resolve_path(args.data_dir, ROOT, orig_cwd)
    output_file = data_dir / args.output_filename
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("正在从中债官网抓取 30 年期国债财富指数数据...")
    try:
        fetched = fetch_chinabond_index("CBA21801", timeout=args.timeout)
        df = merge_chinabond_history(output_file, fetched, None, None)
        written = write_csv_stable(output_file, df, key_column="trade_date")
    except Exception as e:
        print(f"错误: 抓取中债 30 年期国债财富指数失败: {e}", file=sys.stderr)
        return 1

    start_date = df["trade_date"].min()
    end_date = df["trade_date"].max()
    count = len(df)

    if written:
        print(f"抓取成功并写盘: {output_file} (共 {count} 个交易日, {start_date} ~ {end_date})")
    else:
        print(f"抓取成功但数据未变（保留磁盘原样）: {output_file} (共 {count} 个交易日, {start_date} ~ {end_date})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
