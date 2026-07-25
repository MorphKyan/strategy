"""行业指数估值数据入库：Wind 原始导出 → 平台契约 `data/index_valuation/<INDEX_CODE>.csv`。

背景：ETF 本身没有 PE/PB，其"估值"是跟踪指数的估值（ETF 全复制/抽样复制，
持仓≈指数成分）。因此估值信号的数据主体是**指数**，与 ETF 的对应关系由
`data/etf_index_map.csv` 显式维护（可审计，不靠记忆）。

输入：Wind `AIndexValuation` 表导出的 CSV（可多个文件，按 S_INFO_WINDCODE 拆分）。
输出：一个指数一个 CSV，列 trade_date,pe_ttm,pb_lf,dividend_yield,turnover,mv_total,con_num。

三处必须的清洗（每一条都有实际后果）：
1. **非交易日剔除**：Wind 按自然日导出，周末与法定节假日用前值填充（实测约占
   1/3 行数）。不清洗的话"当月最后一个自然日"会取到陈旧估值，污染月频信号。
   判据不用启发式（turnover 是否为空），而是与本地行情的权威交易日历 inner join，
   并用"被丢弃行 ≈ turnover 空行"做交叉校验，不一致时报警。
2. **指数代码大小写规范化**：Wind 中 `h30184.CSI` 是小写，其余大写，不统一会 join 不上。
3. **去重**：同一 (指数, 日期) 可能重复出现（Wind 导出常见），保留最后一条。

授权数据提醒：Wind 导出带逐账号水印，原始与加工产物均不入库（见 .gitignore），
只有本脚本与映射表入库。用法：

  .\\env\\Scripts\\python.exe platform\\scripts\\ingest_index_valuation.py ^
      --source index_performance --report
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Wind 列 → 平台列。只取估值信号需要的字段，其余（PS/PCF/EST_* 等）不入库：
# EST_* 是分析师预期，有"预测发布时点"的前视问题，要用需单独设计滞后规则。
COLUMN_MAP = {
    "TRADE_DT": "trade_date",
    "PE_TTM": "pe_ttm",
    "PB_LF": "pb_lf",
    "DIVIDEND_YIELD": "dividend_yield",
    "TURNOVER": "turnover",
    "MV_TOTAL": "mv_total",
    "CON_NUM": "con_num",
}
OUTPUT_COLUMNS = ["trade_date", "pe_ttm", "pb_lf", "dividend_yield", "turnover", "mv_total", "con_num"]

# 交易日历基准：沪深300ETF 流动性最好、历史最长，其行情日期即 A 股交易日。
CALENDAR_REFERENCE = "510300"


def load_trading_calendar(data_dir: Path, reference: str = CALENDAR_REFERENCE) -> pd.DatetimeIndex:
    path = data_dir / f"{reference}.csv"
    if not path.exists():
        raise FileNotFoundError(f"交易日历基准行情不存在: {path}")
    frame = pd.read_csv(path, usecols=["trade_date"])
    return pd.DatetimeIndex(pd.to_datetime(frame["trade_date"], errors="coerce").dropna().unique()).sort_values()


def load_raw_valuation(source_dir: Path) -> pd.DataFrame:
    """读取 source_dir 下所有 AIndexValuation 导出，纵向拼接。"""
    paths = sorted(source_dir.glob("AINDEXVALUATION*.csv"))
    if not paths:
        raise FileNotFoundError(f"{source_dir} 下没有 AINDEXVALUATION*.csv")
    frames = []
    for path in paths:
        frame = pd.read_csv(path, usecols=lambda c: c in {"S_INFO_WINDCODE", *COLUMN_MAP})
        frame["__source"] = path.name
        frames.append(frame)
        print(f"  读取 {path.name}: {len(frame):,} 行")
    return pd.concat(frames, ignore_index=True)


def normalize_index_code(code: str) -> str:
    """Wind 里 h30184.CSI 是小写、其余大写；统一为大写代码 + 大写后缀。"""
    return str(code).strip().upper()


def ingest(source_dir: Path, data_dir: Path, output_dir: Path) -> pd.DataFrame:
    calendar = load_trading_calendar(data_dir)
    raw = load_raw_valuation(source_dir)
    raw["index_code"] = raw["S_INFO_WINDCODE"].map(normalize_index_code)
    raw = raw.rename(columns=COLUMN_MAP)
    raw["trade_date"] = pd.to_datetime(raw["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    raw = raw.dropna(subset=["trade_date", "index_code"])

    output_dir.mkdir(parents=True, exist_ok=True)
    calendar_set = set(calendar)
    rows = []
    for index_code, group in raw.groupby("index_code"):
        group = group.sort_values("trade_date").drop_duplicates("trade_date", keep="last")
        raw_rows = len(group)
        # 权威交易日历过滤（不用 turnover 空值这一启发式，仅用它做交叉校验）
        kept = group[group["trade_date"].isin(calendar_set)].copy()
        dropped = group[~group["trade_date"].isin(calendar_set)]
        # 交叉校验：被丢弃的应几乎全是 turnover 为空的填充行
        dropped_with_turnover = int(dropped["turnover"].notna().sum())
        kept_without_turnover = int(kept["turnover"].isna().sum())

        kept = kept[OUTPUT_COLUMNS].copy()
        kept["trade_date"] = kept["trade_date"].dt.strftime("%Y-%m-%d")
        kept.to_csv(output_dir / f"{index_code}.csv", index=False, encoding="utf-8")

        rows.append({
            "index_code": index_code,
            "raw_rows": raw_rows,
            "trading_rows": len(kept),
            "dropped": raw_rows - len(kept),
            "start": kept["trade_date"].iloc[0] if len(kept) else "",
            "end": kept["trade_date"].iloc[-1] if len(kept) else "",
            "pe_na": float(pd.to_numeric(kept["pe_ttm"], errors="coerce").isna().mean()) if len(kept) else 1.0,
            "pb_na": float(pd.to_numeric(kept["pb_lf"], errors="coerce").isna().mean()) if len(kept) else 1.0,
            "dy_na": float(pd.to_numeric(kept["dividend_yield"], errors="coerce").isna().mean()) if len(kept) else 1.0,
            "warn_dropped_tradable": dropped_with_turnover,
            "warn_kept_no_turnover": kept_without_turnover,
        })
    return pd.DataFrame(rows).sort_values("start")


def render_report(summary: pd.DataFrame, data_dir: Path, map_path: Path) -> None:
    print("\n" + "=" * 96)
    print("入库结果")
    print("=" * 96)
    display = summary.copy()
    for column in ("pe_na", "pb_na", "dy_na"):
        display[column] = display[column].map(lambda v: f"{v:.1%}")
    print(display.to_string(index=False))

    warns = summary[(summary["warn_dropped_tradable"] > 0) | (summary["warn_kept_no_turnover"] > 0)]
    print("\n交叉校验（被丢弃行应全为非交易日填充；保留行应全有 turnover）:")
    if warns.empty:
        print("  ✓ 全部指数一致，交易日历对齐无异常")
    else:
        for _, row in warns.iterrows():
            print(f"  ! {row['index_code']}: 丢弃了 {row['warn_dropped_tradable']} 个有成交的日期,"
                  f" 保留了 {row['warn_kept_no_turnover']} 个无成交的日期")

    if not map_path.exists():
        return
    mapping = pd.read_csv(map_path, dtype=str)
    print("\n" + "=" * 96)
    print("ETF ↔ 指数映射与共同窗口")
    print("=" * 96)
    by_index = summary.set_index("index_code")
    lines = []
    for _, row in mapping.iterrows():
        etf, index_code = row["etf_code"], row["index_code"]
        price_path = data_dir / f"{etf}.csv"
        if price_path.exists():
            prices = pd.read_csv(price_path, usecols=["trade_date"])
            etf_start = str(pd.to_datetime(prices["trade_date"]).min().date())
        else:
            etf_start = "缺失"
        val_start = by_index.loc[index_code, "start"] if index_code in by_index.index else "缺失"
        lines.append({
            "ETF": f"{etf} {row['name']}",
            "指数": index_code,
            "ETF首日": etf_start,
            "估值首日": val_start,
            "可用起点": max(etf_start, val_start) if "缺失" not in (etf_start, val_start) else "—",
        })
    frame = pd.DataFrame(lines)
    print(frame.to_string(index=False))
    usable = frame[frame["可用起点"] != "—"]["可用起点"]
    if len(usable):
        common = usable.max()
        print(f"\n全池共同窗口起点: {common}（由最晚的成员决定）")
        print(f"至训练截止 2025-06-30 约 {(pd.Timestamp('2025-06-30') - pd.Timestamp(common)).days / 365.25:.1f} 年")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Wind index valuation exports into the platform contract.")
    parser.add_argument("--source", default="index_performance", help="Raw Wind export directory (repo-root relative).")
    parser.add_argument("--data-dir", default=None, help="Platform data dir. Defaults to platform/data.")
    parser.add_argument("--output", default=None, help="Output dir. Defaults to <data-dir>/index_valuation.")
    parser.add_argument("--report", action="store_true", help="Print the validation report.")
    args = parser.parse_args()

    repo_root = ROOT.parent
    source_dir = Path(args.source) if Path(args.source).is_absolute() else repo_root / args.source
    data_dir = Path(args.data_dir) if args.data_dir else ROOT / "data"
    output_dir = Path(args.output) if args.output else data_dir / "index_valuation"

    print(f"源目录: {source_dir}")
    summary = ingest(source_dir, data_dir, output_dir)
    print(f"\n已写入 {len(summary)} 个指数 → {output_dir}")
    if args.report:
        render_report(summary, data_dir, data_dir / "etf_index_map.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
