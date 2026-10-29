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
from math import isfinite
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

from src.platform_core.data import LocalCsvBarData  # noqa: E402
from src.platform_core.data_store import assets_from_config, write_csv_stable  # noqa: E402
from src.platform_core.etf_premium import NAV_DIRNAME, EtfPremiumStore  # noqa: E402

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
    """抓单只 ETF 的完整净值；分页数量、日期或数值异常时拒绝入库。"""
    rows: list[dict] = []
    total: int | None = None
    for page in range(1, max_pages + 1):
        url = f"{LSJZ_URL}?fundCode={code}&pageIndex={page}&pageSize={PAGE_SIZE}&startDate=&endDate="
        payload = None
        for attempt in range(4):
            try:
                response = session.get(url, timeout=20)
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    raise RuntimeError(f"{code} 第 {page} 页抓取失败: {type(exc).__name__}: {exc}") from exc
                time.sleep(1.5 * (attempt + 1))
        count = int(payload.get("TotalCount") or 0)
        if count <= 0 or (total is not None and count != total):
            raise RuntimeError(f"{code}: 缺少有效 TotalCount 或分页期间总数变化，拒绝入库")
        total = count
        chunk = (payload.get("Data") or {}).get("LSJZList") or []
        if not chunk:
            break
        rows.extend(chunk)
        if total and len(rows) >= total:
            break
        time.sleep(0.2)

    if not rows:
        raise RuntimeError(f"{code}: 未取到任何净值记录")
    if len(rows) != total:
        raise RuntimeError(f"{code}: 抓到 {len(rows)} 行 != TotalCount {total}，疑似分页截断，拒绝入库")

    frame = pd.DataFrame(rows)[["FSRQ", "DWJZ", "LJJZ"]]
    frame.columns = ["trade_date", "unit_nav", "cum_nav"]
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="raise").dt.date
    for column in ("unit_nav", "cum_nav"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not frame[column].map(lambda value: isfinite(value) and value > 0).all():
            raise ValueError(f"{code}: {column} 必须为有限正数，拒绝入库")
    if frame["trade_date"].isna().any() or frame["trade_date"].duplicated().any():
        raise ValueError(f"{code}: 净值日期缺失或重复，疑似重复分页，拒绝入库")
    frame = frame.sort_values("trade_date")
    return frame.reset_index(drop=True)


def codes_from_config(config_path: Path) -> list[str]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return [asset.code for asset in assets_from_config(config.get("assets") or []) if asset.asset_type == "etf"]


def guard_history_shrink(path: Path, frame: pd.DataFrame) -> None:
    """收缩保护：新抓结果的行数/覆盖区间不得倒退（与行情同步同一纪律）。"""
    if not path.exists():
        return
    old = pd.read_csv(path)
    old_dates = pd.to_datetime(old["trade_date"], errors="raise")
    new_dates = pd.to_datetime(frame["trade_date"], errors="raise")
    if old_dates.isna().any() or old_dates.duplicated().any():
        raise ValueError(f"{path.name}: 已存日期缺失或重复，拒绝覆盖")
    if not set(old_dates).issubset(new_dates):
        raise RuntimeError(f"{path.name}: 新结果缺少已存历史日期，拒绝覆盖")


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

    if not codes:
        parser.error("没有可抓取的 ETF 代码")
    data_dir = Path(args.data_dir)
    if args.report:
        assets = assets_from_config([{"asset_id": code, "code": code} for code in codes])
        market = LocalCsvBarData(data_dir, assets)
        asof = max(market.calendar)
        premiums = EtfPremiumStore(data_dir)
    out_dir = data_dir / NAV_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    session = _session()
    stamp = datetime.now().isoformat(timespec="seconds")

    failures: list[str] = []
    for code in codes:
        try:
            frame = fetch_nav(code, session)
            frame["source"] = SOURCE
            frame["updated_at"] = stamp
            path = out_dir / f"{code}.csv"
            guard_history_shrink(path, frame)
            wrote = write_csv_stable(path, frame, key_column="trade_date")
            print(
                f"[OK] {code}: {len(frame)} 行 {frame['trade_date'].iloc[0]} ~ {frame['trade_date'].iloc[-1]}"
                f" {'(已写盘)' if wrote else '(无变化)'}"
            )
            if args.report:
                history = premiums.observable_history(code, asof)
                if history.empty:
                    raise ValueError("扣除发布滞后后无可观测溢价")
                premium = history["premium"]
                print(
                    f"       可观测溢价（截至 {asof}，观测 {history.index[-1]}）: 最新 {premium.iloc[-1]*100:.2f}%"
                    f" | 中位 {premium.median()*100:.2f}% | 均值 {premium.mean()*100:.2f}% | 配对 {len(history)} 日"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {code}: {exc}")
            failures.append(code)

    if failures:
        print(f"\n失败 {len(failures)} 只: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
