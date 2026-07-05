from __future__ import annotations

import json
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


def discover_runs(root: Path | None = None) -> list[RunRecord]:
    root = (root or platform_root()).resolve()
    results_dir = root / "results"
    records: list[RunRecord] = []
    if not results_dir.exists():
        return records

    for manifest_path in results_dir.rglob("manifest.json"):
        run_dir = manifest_path.parent
        if not (run_dir / "nav.csv").exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            metrics = build_platform_metrics(run_dir)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
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
    return sorted(records, key=lambda item: (item.generated_at, item.run_id), reverse=True)


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
