from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.platform_core.metrics import build_platform_metrics


@dataclass(frozen=True)
class ConfigRecord:
    path: Path
    relative_path: str
    run_name: str
    strategy_name: str
    assets: tuple[dict[str, Any], ...]
    params: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    path: Path
    generated_at: str
    start_date: str
    end_date: str
    metrics: dict[str, Any]
    manifest: dict[str, Any]


def platform_root() -> Path:
    return Path(__file__).resolve().parents[2]


def discover_configs(root: Path | None = None) -> list[ConfigRecord]:
    root = (root or platform_root()).resolve()
    config_dir = root / "configs"
    records: list[ConfigRecord] = []
    for path in sorted(config_dir.rglob("*.yaml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        strategy = payload.get("strategy") or {}
        platform = payload.get("platform") or {}
        records.append(
            ConfigRecord(
                path=path,
                relative_path=path.relative_to(root).as_posix(),
                run_name=str(platform.get("run_name") or path.stem),
                strategy_name=str(strategy.get("strategy_name") or "未指定"),
                assets=tuple(payload.get("assets") or []),
                params=dict(strategy.get("params") or {}),
                payload=payload,
            )
        )
    return records


# 不属于"回测 run 列表"的 results/ 子目录：
# - sensitivity_raw / backtest_cache：研究内部产物，单次敏感性就有数百个目录，
#   全部进看板会把启动拖到分钟级，结论看 reports/sensitivity 汇总即可；
# - sim_portfolios / live_portfolios：模拟/实盘组合的推进产物（nav 口径也不同，
#   sim 用 total_value 而非 net_value），属于将来的组合页（蓝图 B3/B4），混进
#   回测列表会出现无数据的空行。
EXCLUDED_RESULT_DIRS = {"sensitivity_raw", "backtest_cache", "sim_portfolios", "live_portfolios"}


def discover_runs(root: Path | None = None) -> list[RunRecord]:
    root = (root or platform_root()).resolve()
    results_dir = root / "results"
    records: list[RunRecord] = []
    if not results_dir.exists():
        return records

    for dirpath, dirnames, filenames in os.walk(results_dir):
        # Prune internal research, sweeps, raw folders to avoid scanning thousands of files
        pruned_dirs = []
        for d in dirnames:
            d_lower = d.lower()
            if (
                d in EXCLUDED_RESULT_DIRS or
                "sensitivity_raw" in d_lower or
                "backtest_cache" in d_lower or
                "sim_portfolios" in d_lower or
                "live_portfolios" in d_lower or
                "backtests_sweep" in d_lower or
                "research" in d_lower or
                "_sweep" in d_lower or
                "_raw" in d_lower or
                "compare" in d_lower
            ):
                continue
            pruned_dirs.append(d)
        dirnames[:] = pruned_dirs

        if "manifest.json" in filenames and "nav.csv" in filenames:
            run_dir = Path(dirpath)
            manifest_path = run_dir / "manifest.json"
            metrics_path = run_dir / "metrics.json"

            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                
                # Freshness check for cached metrics.json
                use_cache = False
                if metrics_path.exists():
                    try:
                        if metrics_path.stat().st_mtime >= manifest_path.stat().st_mtime:
                            use_cache = True
                    except OSError:
                        pass

                metrics = None
                if use_cache:
                    try:
                        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                    except (OSError, ValueError, json.JSONDecodeError):
                        use_cache = False

                if not use_cache or metrics is None:
                    metrics = build_platform_metrics(run_dir)
                    try:
                        metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
                    except OSError:
                        pass

                records.append(
                    RunRecord(
                        run_id=str(manifest.get("run_id") or run_dir.name),
                        path=run_dir,
                        generated_at=str(manifest.get("generated_at") or ""),
                        start_date=str(metrics.get("start_date") or ""),
                        end_date=str(metrics.get("end_date") or ""),
                        metrics=metrics,
                        manifest=manifest,
                    )
                )
            except (OSError, ValueError, json.JSONDecodeError):
                continue

    return sorted(records, key=lambda item: (item.generated_at, item.run_id), reverse=True)


def get_runs_signature(root: Path | None = None) -> str:
    root = (root or platform_root()).resolve()
    results_dir = root / "results"
    if not results_dir.exists():
        return ""

    items: list[str] = []
    for dirpath, dirnames, filenames in os.walk(results_dir):
        pruned_dirs = []
        for d in dirnames:
            d_lower = d.lower()
            if (
                d in EXCLUDED_RESULT_DIRS or
                "sensitivity_raw" in d_lower or
                "backtest_cache" in d_lower or
                "sim_portfolios" in d_lower or
                "live_portfolios" in d_lower or
                "backtests_sweep" in d_lower or
                "research" in d_lower or
                "_sweep" in d_lower or
                "_raw" in d_lower or
                "compare" in d_lower
            ):
                continue
            pruned_dirs.append(d)
        dirnames[:] = pruned_dirs

        if "manifest.json" in filenames and "nav.csv" in filenames:
            manifest_path = Path(dirpath) / "manifest.json"
            try:
                mtime = manifest_path.stat().st_mtime
                items.append(f"{dirpath}:{mtime}")
            except OSError:
                pass
    return ",".join(sorted(items))


def get_configs_signature(root: Path | None = None) -> str:
    root = (root or platform_root()).resolve()
    config_dir = root / "configs"
    if not config_dir.exists():
        return ""

    items: list[str] = []
    for dirpath, dirnames, filenames in os.walk(config_dir):
        for f in filenames:
            if f.endswith(".yaml"):
                path = Path(dirpath) / f
                try:
                    mtime = path.stat().st_mtime
                    items.append(f"{path.as_posix()}:{mtime}")
                except OSError:
                    pass
    return ",".join(sorted(items))


def read_run_tables(run_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for name in ("nav", "positions", "orders", "skipped_orders", "trades"):
        path = run_dir / f"{name}.csv"
        try:
            tables[name] = pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            tables[name] = pd.DataFrame()
    nav = tables["nav"]
    if not nav.empty and "date" in nav:
        nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
        nav = nav.dropna(subset=["date"]).sort_values("date")
        if "net_value" in nav:
            peak = nav["net_value"].cummax()
            nav["drawdown"] = nav["net_value"] / peak - 1.0
        tables["nav"] = nav
    for name in ("positions", "orders", "skipped_orders", "trades"):
        frame = tables[name]
        if not frame.empty and "date" in frame:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return tables


def nav_analytics(nav: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """从 nav.csv 派生多尺度收益视图所需的全部数据框。

    返回键：daily（日收益）、monthly（月收益长表）、monthly_pivot（年×月透视）、
    yearly（年度收益）、rolling（滚动年化波动/滚动 Sharpe）。数据不足时对应值为空表。
    """
    empty = pd.DataFrame()
    out = {"daily": empty, "monthly": empty, "monthly_pivot": empty, "yearly": empty, "rolling": empty}
    if nav.empty or "net_value" not in nav.columns or "date" not in nav.columns:
        return out
    frame = nav[["date", "net_value"]].dropna().sort_values("date")
    series = pd.Series(
        pd.to_numeric(frame["net_value"], errors="coerce").values,
        index=pd.DatetimeIndex(frame["date"]),
    ).dropna()
    if len(series) < 2 or series.iloc[0] == 0:
        return out

    daily = series.pct_change().dropna()
    out["daily"] = daily.rename("ret").rename_axis("date").reset_index()

    monthly_nav = series.resample("ME").last().dropna()
    if not monthly_nav.empty:
        monthly_ret = monthly_nav.pct_change()
        monthly_ret.iloc[0] = monthly_nav.iloc[0] / series.iloc[0] - 1
        monthly = monthly_ret.rename("ret").rename_axis("date").reset_index()
        monthly["year"] = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month
        out["monthly"] = monthly
        out["monthly_pivot"] = (
            monthly.pivot(index="year", columns="month", values="ret").reindex(columns=range(1, 13))
        )

    yearly_nav = series.resample("YE").last().dropna()
    if not yearly_nav.empty:
        yearly_ret = yearly_nav.pct_change()
        yearly_ret.iloc[0] = yearly_nav.iloc[0] / series.iloc[0] - 1
        out["yearly"] = pd.DataFrame({"year": yearly_nav.index.year.astype(str), "ret": yearly_ret.values})

    rolling = pd.DataFrame(index=daily.index)
    if len(daily) >= 60:
        rolling["vol_60d"] = daily.rolling(60).std() * math.sqrt(252)
    if len(daily) >= 252:
        rolling_std = daily.rolling(252).std() * math.sqrt(252)
        rolling["sharpe_252d"] = (daily.rolling(252).mean() * 252) / rolling_std.replace(0, pd.NA)
    if not rolling.empty:
        out["rolling"] = rolling.dropna(how="all").rename_axis("date").reset_index()
    return out


TRAILING_MONTHS = {"近1月": 1, "近3月": 3, "近6月": 6, "近1年": 12, "近2年": 24, "近3年": 36}


def window_start_date(last_date: Any, period: str) -> pd.Timestamp | None:
    """把区间标签换算成起始日期；"全部"或未知标签返回 None（不裁剪）。

    "今年"取 last_date 当年 1 月 1 日；"近N月/年"按日历偏移回看。
    组合列表页（蓝图 B4）的近 N 期收益也应复用本函数保证口径一致。
    """
    if period in TRAILING_MONTHS:
        return pd.Timestamp(last_date) - pd.DateOffset(months=TRAILING_MONTHS[period])
    if period == "今年":
        return pd.Timestamp(year=pd.Timestamp(last_date).year, month=1, day=1)
    return None


def rebase_benchmark(candidate: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """把基准净值缩放到候选曲线的坐标系：首个共同交易日两线相交。

    返回列 date, net_value（缩放后基准），无重叠区间时返回空表。
    """
    if candidate.empty or benchmark.empty:
        return pd.DataFrame()
    left = candidate[["date", "net_value"]].dropna()
    right = benchmark[["date", "net_value"]].dropna()
    start = max(left["date"].min(), right["date"].min())
    end = min(left["date"].max(), right["date"].max())
    if start >= end:
        return pd.DataFrame()
    left = left[(left["date"] >= start) & (left["date"] <= end)]
    right = right[(right["date"] >= start) & (right["date"] <= end)].copy()
    if left.empty or right.empty or right["net_value"].iloc[0] == 0:
        return pd.DataFrame()
    scale = float(left["net_value"].iloc[0]) / float(right["net_value"].iloc[0])
    right["net_value"] = right["net_value"] * scale
    return right


def align_navs(
    nav_map: dict[str, pd.DataFrame],
    overlap_only: bool = True,
    start_date: Any = None,
) -> pd.DataFrame:
    """多回测净值对齐：可选裁剪到共同重叠区间，各自归一到区间首日 = 1.0。

    start_date 非空时先把各序列裁剪到该日期之后再归一（用于"近N月"区间对比）。
    返回长表：run_id, date, net_value, drawdown。
    """
    cleaned: dict[str, pd.DataFrame] = {}
    for run_id, nav in nav_map.items():
        if nav.empty or "net_value" not in nav.columns or "date" not in nav.columns:
            continue
        frame = nav[["date", "net_value"]].dropna().sort_values("date")
        if len(frame) >= 2:
            cleaned[run_id] = frame
    if not cleaned:
        return pd.DataFrame()

    if overlap_only:
        start = max(frame["date"].min() for frame in cleaned.values())
        end = min(frame["date"].max() for frame in cleaned.values())
        if start >= end:
            return pd.DataFrame()
        cleaned = {
            run_id: frame[(frame["date"] >= start) & (frame["date"] <= end)]
            for run_id, frame in cleaned.items()
        }
        cleaned = {run_id: frame for run_id, frame in cleaned.items() if len(frame) >= 2}

    if start_date is not None:
        cleaned = {run_id: frame[frame["date"] >= pd.Timestamp(start_date)] for run_id, frame in cleaned.items()}
        cleaned = {run_id: frame for run_id, frame in cleaned.items() if len(frame) >= 2}
    if not cleaned:
        return pd.DataFrame()

    parts: list[pd.DataFrame] = []
    for run_id, frame in cleaned.items():
        base = float(frame["net_value"].iloc[0])
        if base == 0:
            continue
        rebased = frame.copy()
        rebased["net_value"] = rebased["net_value"] / base
        rebased["drawdown"] = rebased["net_value"] / rebased["net_value"].cummax() - 1.0
        rebased["run_id"] = run_id
        parts.append(rebased)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def latest_positions(positions: pd.DataFrame) -> pd.DataFrame:
    if positions.empty or "date" not in positions:
        return pd.DataFrame()
    latest_date = positions["date"].max()
    columns = [
        column
        for column in ("asset_id", "quantity", "price", "market_value", "weight", "cost_basis")
        if column in positions
    ]
    return positions.loc[positions["date"] == latest_date, columns].sort_values(
        "weight" if "weight" in columns else columns[0], ascending=False
    )
