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
                
                # Discovery must stay metadata-only. Expensive metric generation is
                # deferred until a page actually renders the selected run.
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
                    metrics = dict(manifest.get("metrics") or {})

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


def read_run_metrics(run_dir: Path) -> dict[str, Any]:
    """Load or derive metrics for one run on demand."""
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    if metrics_path.exists():
        try:
            if metrics_path.stat().st_mtime >= manifest_path.stat().st_mtime:
                return json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return build_platform_metrics(run_dir)


def read_run_table(run_dir: Path, name: str) -> pd.DataFrame:
    """Read a single artifact table so inactive dashboard sections do no I/O."""
    if name not in {"nav", "positions", "orders", "skipped_orders", "trades"}:
        raise ValueError(f"Unsupported run table: {name}")
    path = run_dir / f"{name}.csv"
    try:
        frame = pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()
    if not frame.empty and "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        if name == "nav":
            frame = frame.dropna(subset=["date"]).sort_values("date")
            if "net_value" in frame:
                frame["drawdown"] = frame["net_value"] / frame["net_value"].cummax() - 1.0
    return frame


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
    return {name: read_run_table(run_dir, name) for name in ("nav", "positions", "orders", "skipped_orders", "trades")}


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

    "今年"取 last_date 当年 1 月 1 日；"近N周/月/年"按日历偏移回看。
    组合列表页（蓝图 B4）的近 N 期收益也复用本函数保证口径一致。
    """
    if period == "近1周":
        return pd.Timestamp(last_date) - pd.DateOffset(weeks=1)
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


def discover_market_symbols(root: Path | None = None) -> list[str]:
    """Return symbols backed by a canonical OHLCV csv, excluding factor files."""
    data_dir = (root or platform_root()).resolve() / "data"
    if not data_dir.exists():
        return []
    return sorted(
        path.stem for path in data_dir.glob("*.csv")
        if path.stem.isdigit() and not path.name.endswith("_hfq_factor.csv")
    )


def read_market_history(root: Path, symbol: str) -> pd.DataFrame:
    """Read one local market series with only chart-relevant columns."""
    if not symbol.isdigit():
        raise ValueError("Invalid market symbol")
    path = root.resolve() / "data" / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame()
    wanted = ["trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor"]
    try:
        frame = pd.read_csv(path, usecols=lambda column: column in wanted)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()
    if "trade_date" not in frame or "close" not in frame:
        return pd.DataFrame()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for column in set(wanted) & set(frame.columns) - {"trade_date"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["trade_date", "close"]).sort_values("trade_date")


def read_corporate_actions(root: Path, symbol: str) -> dict[str, pd.DataFrame]:
    """Read dividends and split/transfer records for a symbol."""
    result: dict[str, pd.DataFrame] = {}
    for key, filename, date_column in (
        ("dividends", "platform_dividends.csv", "ex_date"),
        ("splits", "platform_splits.csv", "split_date"),
    ):
        path = root.resolve() / "data" / filename
        try:
            frame = pd.read_csv(path, dtype={"code": str}) if path.exists() else pd.DataFrame()
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            frame = pd.DataFrame()
        if not frame.empty and "code" in frame:
            frame = frame[frame["code"].str.zfill(6) == symbol.zfill(6)].copy()
            if date_column in frame:
                frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
                frame = frame.sort_values(date_column)
        result[key] = frame
    return result


def build_weighted_portfolio(histories: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    """Build a buy-and-hold normalized basket on the common trading-date window."""
    series = []
    valid_weights = {key: float(value) for key, value in weights.items() if value > 0 and key in histories}
    total = sum(valid_weights.values())
    if total <= 0:
        return pd.DataFrame()
    for symbol, weight in valid_weights.items():
        frame = histories[symbol]
        if frame.empty:
            continue
        item = frame[["trade_date", "close"]].dropna().drop_duplicates("trade_date").set_index("trade_date")
        item = item.rename(columns={"close": symbol})
        series.append(item)
    if not series:
        return pd.DataFrame()
    aligned = pd.concat(series, axis=1, join="inner").dropna()
    if aligned.empty or (aligned.iloc[0] == 0).any():
        return pd.DataFrame()
    normalized = aligned / aligned.iloc[0]
    used = [column for column in normalized if column in valid_weights]
    denominator = sum(valid_weights[column] for column in used)
    normalized["portfolio"] = sum(normalized[column] * valid_weights[column] / denominator for column in used)
    normalized["drawdown"] = normalized["portfolio"] / normalized["portfolio"].cummax() - 1.0
    return normalized.rename_axis("date").reset_index()


def rebalance_events(orders: pd.DataFrame) -> pd.DataFrame:
    """Aggregate filled orders into signal/execution-date rebalance events."""
    if orders.empty or "date" not in orders:
        return pd.DataFrame()
    frame = orders.copy()
    if "status" in frame:
        frame = frame[frame["status"].astype(str).str.upper() == "FILLED"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if "signal_date" in frame:
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce")
    else:
        frame["signal_date"] = frame["date"]
    frame["trade_value"] = pd.to_numeric(frame.get("trade_value", 0), errors="coerce").fillna(0).abs()
    grouped = frame.dropna(subset=["date"]).groupby(["signal_date", "date"], dropna=False)
    return grouped.agg(order_count=("date", "size"), trade_value=("trade_value", "sum")).reset_index()


def downsample_timeseries(frame: pd.DataFrame, max_points: int = 2000) -> pd.DataFrame:
    """Reduce rendering payload while retaining first/last and extrema candidates."""
    if frame.empty or len(frame) <= max_points or max_points < 3:
        return frame
    step = max(1, math.ceil((len(frame) - 2) / (max_points - 2)))
    indexes = [0, *range(1, len(frame) - 1, step), len(frame) - 1]
    return frame.iloc[indexes[: max_points - 1] + [indexes[-1]]].drop_duplicates().copy()


def portfolio_risk_analysis(
    histories: dict[str, pd.DataFrame], weights: dict[str, float], window: int | None = None
) -> dict[str, pd.DataFrame]:
    """Calculate return correlation and Euler volatility contributions."""
    closes = []
    for symbol, frame in histories.items():
        if frame.empty or "close" not in frame or float(weights.get(symbol, 0)) <= 0:
            continue
        closes.append(frame[["trade_date", "close"]].dropna().drop_duplicates("trade_date").set_index("trade_date").rename(columns={"close": symbol}))
    if not closes:
        return {"correlation": pd.DataFrame(), "contribution": pd.DataFrame()}
    returns = pd.concat(closes, axis=1, join="inner").pct_change().dropna()
    if window and window > 1:
        returns = returns.tail(window)
    if len(returns) < 2:
        return {"correlation": pd.DataFrame(), "contribution": pd.DataFrame()}
    correlation = returns.corr()
    covariance = returns.cov() * 252
    symbols = list(covariance.columns)
    weight_series = pd.Series({symbol: max(0.0, float(weights.get(symbol, 0))) for symbol in symbols})
    weight_series /= weight_series.sum()
    marginal_variance = covariance.dot(weight_series)
    portfolio_variance = float(weight_series.dot(marginal_variance))
    if portfolio_variance <= 0:
        contribution = pd.DataFrame()
    else:
        component = weight_series * marginal_variance / math.sqrt(portfolio_variance)
        contribution = pd.DataFrame({
            "symbol": symbols,
            "weight": weight_series.values,
            "risk_contribution": component.values,
            "risk_contribution_pct": (component / component.sum()).values,
        }).sort_values("risk_contribution_pct", ascending=False)
    return {"correlation": correlation, "contribution": contribution}


SLIPPAGE_SCENARIOS = ("default", "stress", "dynamic_participation")


def infer_slippage_scenario(run_id: str, metrics: dict[str, Any]) -> str:
    """Infer scenario without silently treating legacy unknown runs as default."""
    explicit = str(metrics.get("slippage_scenario") or "").lower()
    if explicit in SLIPPAGE_SCENARIOS:
        return explicit
    lowered = run_id.lower()
    for scenario in ("dynamic_participation", "stress", "default"):
        if scenario in lowered:
            return scenario
    return "unknown"


# ---------------------------------------------------------------- 组合页（蓝图 B3/B4）
# sim/live 组合目录只有文件、没有元数据库（A1 有意未接 SQLite），读取层全部
# 基于文件契约：portfolio_state.json / real_nav.csv / runs/*/nav.csv / tickets/。


@dataclass(frozen=True)
class PortfolioRecord:
    portfolio_id: str
    kind: str  # "sim" | "live"
    path: Path
    state: dict[str, Any]


def read_portfolio_state(portfolio_dir: Path) -> dict[str, Any]:
    path = portfolio_dir / "portfolio_state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def discover_portfolios(root: Path | None = None) -> list[PortfolioRecord]:
    """扫描 results/{live,sim}_portfolios/ 下有状态文件的组合，live 在前。"""
    root = (root or platform_root()).resolve()
    records: list[PortfolioRecord] = []
    for kind, dirname in (("live", "live_portfolios"), ("sim", "sim_portfolios")):
        base = root / "results" / dirname
        if not base.exists():
            continue
        for portfolio_dir in sorted(path for path in base.iterdir() if path.is_dir()):
            state = read_portfolio_state(portfolio_dir)
            if state:
                records.append(PortfolioRecord(portfolio_dir.name, kind, portfolio_dir, state))
    return records


def read_portfolio_nav(portfolio_dir: Path, kind: str) -> pd.DataFrame:
    """组合净值序列，统一为 date/net_value 列（蓝图 9.2：sim 历史产物用
    total_value 列，勿改产物，读取层归一）。

    live 读 real_nav.csv（reconcile/每日估值追加的真实净值台账）；
    sim 拼接 runs/*/nav.csv 的增量段——advance() 每次只写新处理的日期段，
    全史 = 各段并集；同日重复时保留时间戳更新的一段。
    """
    parts: list[pd.DataFrame] = []
    if kind == "live":
        paths = [portfolio_dir / "real_nav.csv"]
    else:
        paths = sorted(portfolio_dir.glob("runs/*/nav.csv"))
    for path in paths:
        try:
            if path.exists() and path.stat().st_size:
                parts.append(pd.read_csv(path))
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            continue
    if not parts:
        return pd.DataFrame()
    frame = pd.concat(parts, ignore_index=True)
    if "date" not in frame or "total_value" not in frame:
        return pd.DataFrame()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["net_value"] = pd.to_numeric(frame["total_value"], errors="coerce")
    frame = frame.dropna(subset=["date", "net_value"])
    # 稳定排序保持段内先后，同日保留最后（=最新一次 advance）的估值
    frame = frame.sort_values("date", kind="stable").drop_duplicates("date", keep="last")
    columns = [column for column in ("date", "net_value", "cash", "positions_value", "pending_intent_count") if column in frame]
    return frame[columns].reset_index(drop=True)


def latest_ticket(portfolio_dir: Path) -> dict[str, Any] | None:
    """最近一张下单票：txt 正文必有（含"无操作"日），csv 明细仅调仓日存在。"""
    tickets_dir = portfolio_dir / "tickets"
    if not tickets_dir.exists():
        return None
    txt_paths = sorted(tickets_dir.glob("ticket_*.txt"))
    if not txt_paths:
        return None
    txt_path = txt_paths[-1]
    try:
        text = txt_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    csv_path = txt_path.with_suffix(".csv")
    orders = pd.DataFrame()
    if csv_path.exists():
        try:
            orders = pd.read_csv(csv_path, dtype={"code": str})
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            orders = pd.DataFrame()
    return {"date": txt_path.stem.removeprefix("ticket_"), "text": text, "orders": orders}


def asset_code(asset_id: str) -> str:
    """CN_ETF:510300.SH -> 510300，与行情 CSV 文件名对应。"""
    return asset_id.split(":")[-1].split(".")[0]


def position_weights(state: dict[str, Any], prices: dict[str, float]) -> pd.DataFrame:
    """由状态持仓 × 最新收盘估算当前权重，含现金行；缺价资产权重为 NaN 但保留行。

    prices 以 asset_id 为键。返回列：asset_id, code, quantity, price, market_value, weight。
    """
    rows: list[dict[str, Any]] = []
    for asset_id, position in (state.get("positions") or {}).items():
        quantity = float(position.get("quantity") or 0)
        price = prices.get(asset_id)
        rows.append(
            {
                "asset_id": asset_id,
                "code": asset_code(asset_id),
                "quantity": quantity,
                "price": price,
                "market_value": quantity * price if price is not None else None,
            }
        )
    cash = float(state.get("cash") or 0)
    rows.append({"asset_id": "现金", "code": "现金", "quantity": None, "price": None, "market_value": cash})
    frame = pd.DataFrame(rows)
    known_total = frame["market_value"].dropna().sum()
    frame["weight"] = frame["market_value"] / known_total if known_total > 0 else pd.NA
    return frame


TRAILING_RETURN_PERIODS = ["近1周", "近1月", "近3月", "近6月", "今年"]


def trailing_returns(nav: pd.DataFrame, periods: list[str] | None = None) -> dict[str, float | None]:
    """近 N 期收益：nav 两点回看，区间口径复用 window_start_date（蓝图 B4）。

    组合历史短于区间时返回 None（显示为 —），避免把"成立以来"冒充"近3月"。
    额外附带 key "成立以来" = 全样本收益。
    """
    periods = periods or TRAILING_RETURN_PERIODS
    out: dict[str, float | None] = {period: None for period in periods}
    out["成立以来"] = None
    if nav.empty or "net_value" not in nav or len(nav) < 2:
        return out
    frame = nav[["date", "net_value"]].dropna().sort_values("date")
    if len(frame) < 2:
        return out
    first_date = frame["date"].iloc[0]
    last_value = float(frame["net_value"].iloc[-1])
    first_value = float(frame["net_value"].iloc[0])
    if first_value > 0:
        out["成立以来"] = last_value / first_value - 1.0
    for period in periods:
        start = window_start_date(frame["date"].iloc[-1], period)
        if start is None or start < first_date:
            continue
        window = frame[frame["date"] >= start]
        if len(window) < 2:
            continue
        base = float(window["net_value"].iloc[0])
        if base > 0:
            out[period] = last_value / base - 1.0
    return out


def max_drawdown(nav: pd.DataFrame) -> float | None:
    if nav.empty or "net_value" not in nav or len(nav) < 2:
        return None
    series = pd.to_numeric(nav["net_value"], errors="coerce").dropna()
    if len(series) < 2 or series.cummax().le(0).any():
        return None
    return float((series / series.cummax() - 1.0).min())


def business_days_behind(last_date: Any, today: Any = None) -> int:
    """净值末日距今的工作日滞后数（近似交易日：未剔除 A 股节假日）。

    组合列表页以 >=3 判"疑似定时任务挂了"标黄——长假会有误报，可接受，
    这是发现环路中断的最廉价手段（蓝图 B4）。
    """
    last = pd.Timestamp(last_date).normalize()
    now = (pd.Timestamp(today) if today is not None else pd.Timestamp.today()).normalize()
    if last >= now:
        return 0
    return max(0, len(pd.bdate_range(last, now)) - 1)
