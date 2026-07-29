"""ETF 基金净值入库：东财 F10 历史净值 → 平台契约 `data/etf_nav/<code>.csv`。

背景（R056 审计）：QDII ETF 的场内市价 = 标的收益 + 折溢价变化。`513100` 在
2025-07 ~ 2026-07 的市价年化 28.68%，其中 12.64pp 来自溢价从 0.68% 扩张到 10.42%，
而非纳斯达克本身（累计净值口径仅 16.04%）。只用市价序列的回测无法把这两者分开，
也无法实现任何以溢价为条件的执行纪律。本脚本补上净值这一侧的数据。

输出列：trade_date,unit_nav,cum_nav,source,updated_at
配套加载层：`src/platform_core/etf_premium.py`（含发布滞后前视防护）。

两个必须处理的数据源坑：
1. **分页静默截断**：东财 lsjz 单页上限 20 条，按 `len(data) < pageSize` 判停会
   静默停在 20 行并"成功"返回。必须按响应里的 `TotalCount` 翻页。本仓库历史上
   已被 eastmoney 的静默残史坑过一次（见 r039 报告 §7），同一类问题。
2. **akshare 上游 bug**：`akshare.fund_etf_fund_info_em()` 在 1.18.64 上抛
   `Length mismatch: Expected axis has 14 elements, new values have 13`，
   故直连 F10 接口而不经 akshare。

用法：

  .\\env\\Scripts\\python.exe platform\\scripts\\fetch_etf_nav.py --codes 513100,513500
  .\\env\\Scripts\\python.exe platform\\scripts\\fetch_etf_nav.py --config configs\\r10_core_satellite_premium_gated.yaml
  .\\env\\Scripts\\python.exe platform\\scripts\\fetch_etf_nav.py --codes 513100 --report
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# 与其余 platform 脚本一致：把 cwd 切到 platform/，使 data/ configs/ 相对路径按平台目录解析
os.chdir(ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.platform_core.data_store import write_csv_stable  # noqa: E402
from src.platform_core.etf_premium import NAV_DIRNAME  # noqa: E402

LSJZ_URL = "https://api.fund.eastmoney.com/f10/lsjz"
PAGE_SIZE = 20  # 东财硬上限，调大无效且会被静默截断
SOURCE = "eastmoney_f10"


def _session() -> requests.Session:
    session = requests.Session()
    # 本机系统代理在批量请求下会 RemoteDisconnected；净值接口直连即可
    session.trust_env = False
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://fundf10.eastmoney.com/",
        }
    )
    return session


def fetch_nav(code: str, session: requests.Session, max_pages: int = 400) -> pd.DataFrame:
    """抓单只 ETF 的全历史净值。按 TotalCount 翻页，空页或抓满才停。"""
    rows: list[dict] = []
    total: int | None = None
    for page in range(1, max_pages + 1):
        url = f"{LSJZ_URL}?fundCode={code}&pageIndex={page}&pageSize={PAGE_SIZE}&startDate=&endDate="
        payload = None
        for attempt in range(4):
            try:
                payload = session.get(url, timeout=20).json()
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    raise RuntimeError(f"{code} 第 {page} 页抓取失败: {type(exc).__name__}: {exc}") from exc
                time.sleep(1.5 * (attempt + 1))
        if total is None:
            total = int(payload.get("TotalCount") or 0)
        chunk = (payload.get("Data") or {}).get("LSJZList") or []
        if not chunk:
            break
        rows.extend(chunk)
        if total and len(rows) >= total:
            break
        time.sleep(0.2)

    if not rows:
        raise RuntimeError(f"{code}: 未取到任何净值记录")
    if total and len(rows) < total:
        raise RuntimeError(f"{code}: 抓到 {len(rows)} 行 < TotalCount {total}，疑似分页截断，拒绝入库")

    frame = pd.DataFrame(rows)[["FSRQ", "DWJZ", "LJJZ"]]
    frame.columns = ["trade_date", "unit_nav", "cum_nav"]
    frame = frame[frame["unit_nav"].astype(str).str.strip() != ""].copy()
    frame["unit_nav"] = pd.to_numeric(frame["unit_nav"], errors="coerce")
    frame["cum_nav"] = pd.to_numeric(frame["cum_nav"], errors="coerce")
    frame = frame.dropna(subset=["unit_nav"])
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
    frame = frame.dropna(subset=["trade_date"])
    frame = frame.sort_values("trade_date").drop_duplicates("trade_date", keep="last")
    return frame.reset_index(drop=True)


def codes_from_config(config_path: Path) -> list[str]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    codes = []
    for asset in config.get("assets") or []:
        code = str(asset.get("code") or "").strip()
        if code:
            codes.append(code)
    return codes


def guard_history_shrink(path: Path, frame: pd.DataFrame) -> None:
    """收缩保护：新抓结果的行数/覆盖区间不得倒退（与行情同步同一纪律）。"""
    if not path.exists():
        return
    old = pd.read_csv(path)
    if len(frame) < len(old):
        raise RuntimeError(
            f"{path.name}: 新数据 {len(frame)} 行 < 已入库 {len(old)} 行，疑似源端残史，拒绝覆盖"
        )
    old_last = str(old["trade_date"].max())
    new_last = str(frame["trade_date"].max())
    if new_last < old_last:
        raise RuntimeError(f"{path.name}: 新数据截止 {new_last} 早于已入库 {old_last}，拒绝覆盖")


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 ETF 历史净值并入库 data/etf_nav/")
    parser.add_argument("--codes", help="逗号分隔的 ETF 代码，如 513100,513500")
    parser.add_argument("--config", help="从 platform 配置的 assets 读取代码清单")
    parser.add_argument("--data-dir", default="data", help="平台数据目录，默认 data")
    parser.add_argument("--report", action="store_true", help="打印每只的覆盖区间与最新溢价")
    args = parser.parse_args()

    if not args.codes and not args.config:
        parser.error("必须给出 --codes 或 --config")

    codes: list[str] = []
    if args.codes:
        codes += [c.strip() for c in args.codes.split(",") if c.strip()]
    if args.config:
        codes += codes_from_config(Path(args.config))
    codes = list(dict.fromkeys(codes))

    data_dir = Path(args.data_dir)
    out_dir = data_dir / NAV_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    session = _session()
    stamp = datetime.now().isoformat(timespec="seconds")

    failures: list[str] = []
    for code in codes:
        try:
            frame = fetch_nav(code, session)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {code}: {exc}")
            failures.append(code)
            continue
        frame["source"] = SOURCE
        frame["updated_at"] = stamp
        path = out_dir / f"{code}.csv"
        try:
            guard_history_shrink(path, frame)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {code}: {exc}")
            failures.append(code)
            continue
        wrote = write_csv_stable(path, frame, key_column="trade_date")
        print(
            f"[OK] {code}: {len(frame)} 行 {frame['trade_date'].iloc[0]} ~ {frame['trade_date'].iloc[-1]}"
            f" {'(已写盘)' if wrote else '(无变化)'}"
        )
        if args.report:
            price_path = data_dir / f"{code}.csv"
            if price_path.exists():
                price = pd.read_csv(price_path)
                ccol = "close" if "close" in price.columns else "close_price"
                price["trade_date"] = pd.to_datetime(price["trade_date"], errors="coerce").dt.date
                merged = price[["trade_date", ccol]].merge(frame[["trade_date", "unit_nav"]], on="trade_date")
                premium = merged[ccol] / merged["unit_nav"] - 1.0
                print(
                    f"       溢价: 最新 {premium.iloc[-1]*100:.2f}% | 中位 {premium.median()*100:.2f}%"
                    f" | 均值 {premium.mean()*100:.2f}% | 配对 {len(merged)} 日"
                )

    if failures:
        print(f"\n失败 {len(failures)} 只: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
