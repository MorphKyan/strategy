from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
import pandas as pd

from src.platform_core.corporate_actions import (
    apply_due_dividends, apply_due_splits, load_corporate_actions, resolve_split_effective_dates,
)
from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import MarketDataStore, assets_from_config
from src.platform_core.execution import ExecutionConfig, ExecutionEngine
from src.platform_core.metrics import compute_period_metrics
from src.platform_core.models import PortfolioState, Position, date_str
from src.platform_core.runtime_config import apply_runtime_dates
from src.platform_core.slippage import SLIPPAGE_SCENARIOS, apply_slippage_scenario
from src.platform_core.storage import SQLiteStore, InMemoryStore, write_csv_rows, write_json
from src.platform_core.strategy import StrategyContext, get_strategy_class

PLATFORM_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PlatformBacktestResult:
    run_id: str
    output_dir: Path
    metrics: dict[str, Any]


def load_strategy_config(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Platform config requires a single `strategy` mapping.")
    if "strategy_name" not in payload:
        raise ValueError("Platform `strategy.strategy_name` is required.")
    if "start_date" in payload or "end_date" in payload:
        raise ValueError("Platform strategy configs must not include dates.")
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("Platform strategy.params must be a mapping.")
    universe = params.get("universe", [])
    if not isinstance(universe, (list, tuple)) or any(not isinstance(asset_id, str) or not asset_id for asset_id in universe):
        raise ValueError("Platform strategy universe must be a list of asset IDs.")
    if len(universe) != len(set(universe)):
        raise ValueError("Platform strategy universe contains duplicate asset IDs.")
    return dict(payload)


class PlatformBacktestEngine:
    def __init__(self, config: dict[str, Any], store: SQLiteStore | InMemoryStore,
                 output_dir: str | Path | None = None, config_path: str | Path | None = None):
        self.config = config
        self.store = store
        self.assets = {asset.asset_id: asset for asset in assets_from_config(config.get("assets", []))}
        if not self.assets:
            raise ValueError("At least one asset is required.")
        self.non_tradable_indices = [asset.asset_id for asset in self.assets.values() if asset.asset_type == "index"]
        self.strategy_config = load_strategy_config(config.get("strategy"))
        backtest_config = config.get("backtest") or {}
        data_config = config.get("data", {})
        data_fetch = bool(data_config.get("fetch", False))
        market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")
        self.data_quality_notes: list[str] = []
        if data_config.get("market_store_dir") or data_fetch:
            market_store = MarketDataStore(market_dir)
            market_report = market_store.sync_assets(
                list(self.assets.values()),
                start=backtest_config.get("start_date"),
                end=backtest_config.get("end_date"),
                fetch=data_fetch,
            )
            self.data_quality_notes.extend(market_report.notes)
        self.data = LocalCsvBarData(
            data_dir=market_dir,
            assets=self.assets.values(),
            start_date=backtest_config.get("start_date"),
            end_date=backtest_config.get("end_date"),
        )
        if not self.data.calendar:
            raise ValueError("No market data in the requested runtime window.")

        execution_config = config.get("execution", {})
        self.execution = ExecutionEngine(ExecutionConfig.from_config(execution_config))
        self.slippage_scenario = execution_config.get("slippage_scenario", "custom")
        run_name = config.get("platform", {}).get("run_name", "platform_backtest")
        self.run_id = f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.artifact_provenance = self._artifact_provenance(config_path)
        temporary_root = PLATFORM_ROOT / "results/temporary_backtests/direct"
        configured_output = Path(output_dir or config.get("output", {}).get("results_dir") or temporary_root).resolve()
        if configured_output.is_relative_to(PLATFORM_ROOT / "results/backtests"):
            if self.artifact_provenance["classification"] != "fixed_full_history":
                configured_output = temporary_root
        self.output_dir = configured_output / self.run_id
        self.checkpoint_dir = self.output_dir / "checkpoints"
        
        self.code_to_asset_id = {asset.code: asset_id for asset_id, asset in self.assets.items()}
        self.dividends = load_corporate_actions(self.config, "dividends")
        self.splits = load_corporate_actions(self.config, "splits")

    def run(self) -> PlatformBacktestResult:
        state = self._initial_state()
        state.validate_assets(self.assets)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._write_config_snapshot()
        backtest_id = self.store.record_backtest(self.run_id, self.config, self.output_dir)
        resolve_split_effective_dates(self.splits, self.code_to_asset_id, self.data)

        nav_rows: list[dict[str, Any]] = []
        position_rows: list[dict[str, Any]] = []
        order_rows: list[dict[str, Any]] = []
        skipped_order_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        active_strategy = None
        active_strategy_runtime: dict[str, Any] = {}
        active_strategy_version_id: int | None = None
        identity = {"strategy_name": self.strategy_config["strategy_name"], "params": self.strategy_config.get("params", {})}

        for current_date in self.data.calendar:
            # 1. Process Splits（在 split_date 后首个真实交易日生效，见 corporate_actions）
            apply_due_splits(self.splits, state, self.code_to_asset_id, current_date)

            apply_due_dividends(self.dividends, state, self.code_to_asset_id, current_date)

            bars = self.data.bars_on(current_date)
            if active_strategy is None:
                if self.strategy_config.get("cancel_pending_on_start", False):
                    state.pending_intents.clear()
                strategy_cls = get_strategy_class(self.strategy_config["strategy_name"])
                version_id = self.store.ensure_builtin_version(strategy_cls, self.strategy_config.get("params", {}))
                self.strategy_config["strategy_version_id"] = version_id
                identity["source_hash"] = self.store.get_strategy_version(version_id)["source_hash"]
                self.store.add_strategy_reference(int(version_id), "backtest", str(backtest_id))
                active_strategy = strategy_cls()
                active_strategy_runtime = {}
                init_context = StrategyContext(
                    date=current_date,
                    assets=self.assets,
                    bars=bars,
                    state=state,
                    data=self.data,
                    params=self.strategy_config.get("params", {}),
                    runtime=active_strategy_runtime,
                )
                active_strategy.initialize(init_context)
                active_strategy_version_id = int(version_id)

            state.decrement_cooldowns()
            pending_target = state.pending_target(current_date)
            if pending_target is not None:
                skipped_orders = []
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=state,
                    assets=self.assets,
                    bars=bars,
                    target=pending_target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                    close_absent_positions=False,
                    signal_dates=state.pending_signal_dates(current_date),
                    skipped_orders=skipped_orders,
                )
                order_rows.extend(order.to_row() for order in orders)
                skipped_order_rows.extend(order.to_row() for order in skipped_orders)
                trade_rows.extend(trade.to_row() for trade in trades)

            assert active_strategy is not None
            context = StrategyContext(
                date=current_date,
                assets=self.assets,
                bars=bars,
                state=state,
                data=self.data,
                params=self.strategy_config.get("params", {}),
                runtime=active_strategy_runtime,
            )
            target = active_strategy.generate_targets(context)
            if target is not None:
                unknown = set(target.weights) - set(self.assets)
                if unknown:
                    raise ValueError(f"Target portfolio contains unknown assets: {sorted(unknown)}")
                state.replace_pending(target, current_date)

            state.strategy_state["_strategy_runtime"] = {
                "identity": identity,
                "runtime": active_strategy_runtime,
            }

            prices = {asset_id: bar.close for asset_id, bar in bars.items()}
            total_value = state.total_value(prices)
            nav_rows.append(
                {
                    "date": date_str(current_date),
                    "net_value": total_value / self._initial_equity(),
                    "total_value": total_value,
                    "cash": state.cash,
                    "pending_intent_count": len(state.pending_intents),
                    "strategy_version_id": active_strategy_version_id,
                }
            )
            for asset_id, position in sorted(state.positions.items()):
                price = prices.get(asset_id, 0.0)
                position_rows.append(
                    {
                        "date": date_str(current_date),
                        "asset_id": asset_id,
                        "quantity": position.quantity,
                        "price": price,
                        "market_value": position.quantity * price,
                        "weight": position.quantity * price / total_value if total_value else 0.0,
                        "cost_basis": position.cost_basis,
                    }
                )

            state.last_date = current_date
            if (self.config.get("backtest") or {}).get("enable_checkpoints", False):
                checkpoint_path = self.checkpoint_dir / f"{date_str(current_date)}.json"
                write_json(checkpoint_path, state.to_dict())
                self.store.add_checkpoint(self.run_id, date_str(current_date), checkpoint_path)

        if not (self.config.get("backtest") or {}).get("enable_checkpoints", False) and self.data.calendar:
            last_date = self.data.calendar[-1]
            checkpoint_path = self.checkpoint_dir / f"{date_str(last_date)}.json"
            write_json(checkpoint_path, state.to_dict())
            self.store.add_checkpoint(self.run_id, date_str(last_date), checkpoint_path)


        write_csv_rows(self.output_dir / "nav.csv", nav_rows)
        write_csv_rows(self.output_dir / "positions.csv", position_rows)
        write_csv_rows(self.output_dir / "orders.csv", order_rows)
        write_csv_rows(self.output_dir / "skipped_orders.csv", skipped_order_rows)
        write_csv_rows(self.output_dir / "trades.csv", trade_rows)
        metrics = compute_period_metrics(
            pd.DataFrame(nav_rows), pd.DataFrame(trade_rows), pd.DataFrame(order_rows),
            pd.DataFrame(skipped_order_rows), pd.DataFrame(position_rows),
        )
        metrics["slippage_scenario"] = self.slippage_scenario
        self._write_manifest(metrics)
        self._write_report(metrics)
        return PlatformBacktestResult(run_id=self.run_id, output_dir=self.output_dir, metrics=metrics)

    def _initial_state(self) -> PortfolioState:
        portfolio = self.config.get("portfolio", {})
        positions = {}
        for item in portfolio.get("initial_positions", []):
            asset_id = item["asset_id"]
            if asset_id in positions:
                raise ValueError(f"Duplicate initial position: {asset_id}")
            positions[asset_id] = Position(asset_id, float(item.get("quantity", 0.0)), float(item.get("cost_basis", 0.0)))
        return PortfolioState(cash=float(portfolio.get("initial_cash", 0.0)), positions=positions)

    def _initial_equity(self) -> float:
        portfolio = self.config.get("portfolio", {})
        return float(portfolio.get("initial_equity") or portfolio.get("initial_cash") or 1.0)

    def _artifact_provenance(self, config_path: str | Path | None) -> dict[str, Any]:
        common_dates = set.intersection(*(set(days) for days in self.data.real_bar_dates.values()))
        common_start = min(common_dates) if common_dates else None
        common_end = max(common_dates) if common_dates else None
        fixed_config = False
        source = Path(config_path).resolve() if config_path is not None else None
        if source is not None and source.suffix in {".yaml", ".yml"} and source.is_relative_to(PLATFORM_ROOT / "configs"):
            if not source.is_relative_to(PLATFORM_ROOT / "configs/generated"):
                original = yaml.safe_load(source.read_text(encoding="utf-8"))
                if not any((original.get("backtest") or {}).get(key) for key in ("start_date", "end_date")):
                    runtime = self.config.get("backtest") or {}
                    expected = apply_runtime_dates(original, runtime.get("start_date"), runtime.get("end_date"))
                    if self.slippage_scenario in SLIPPAGE_SCENARIOS:
                        expected = apply_slippage_scenario(expected, self.slippage_scenario)
                    fixed_config = expected == self.config
        full_history = self.data.calendar[0] == common_start and self.data.calendar[-1] == common_end
        return {
            "classification": "fixed_full_history" if fixed_config and full_history else "temporary",
            "config_path": str(source) if source is not None else None,
            "fixed_config": fixed_config,
            "common_start_date": date_str(common_start),
            "common_end_date": date_str(common_end),
            "start_date": date_str(self.data.calendar[0]),
            "end_date": date_str(self.data.calendar[-1]),
        }

    def _write_config_snapshot(self) -> None:
        with (self.output_dir / "config_snapshot.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self.config, handle, allow_unicode=True, sort_keys=False)

    def _write_manifest(self, metrics: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine": "platform_core.daily_event",
            "artifact_provenance": self.artifact_provenance,
            "instrument_semantics": {"research_simulation": bool(self.non_tradable_indices),
                                     "non_tradable_indices": self.non_tradable_indices},
            "execution_model": {
                "signal_execution_lag_days": 1,
                "execution_price_field": self.execution.config.price_field,
                "slippage_scenario": self.slippage_scenario,
                "slippage": self.config.get("execution", {}).get("slippage", {}),
            },
            "metrics": metrics,
            "data_quality_notes": self.data.quality.notes + self.data_quality_notes,
        }
        write_json(self.output_dir / "manifest.json", payload)

    def _write_report(self, metrics: dict[str, Any]) -> None:
        lines = [
            f"# 平台回测报告：{self.run_id}",
            "",
            "## 摘要",
            f"- 开始日期：{metrics.get('start_date')}",
            f"- 结束日期：{metrics.get('end_date')}",
            f"- 累计收益率：{metrics['total_return']:.2%}" if metrics.get("total_return") is not None else "- 累计收益率：无有效净值基准",
            f"- 最大回撤：{metrics['max_drawdown']:.2%}" if metrics.get("max_drawdown") is not None else "- 最大回撤：无有效净值基准",
            f"- 年化金额换手率：{metrics.get('annualized_turnover_amount', metrics.get('annualized_turnover', 0.0)) * 100:.2f}%",
            f"- 年化数量换手：{metrics.get('annualized_turnover_quantity', 0.0):.4f}",
            f"- 成交笔数：{metrics.get('trade_count', 0)}",
            f"- 期末待执行意图数：{metrics.get('pending_intent_count', 0)}",
            "",
            "## 说明",
            "- 该 M0-M2 引擎使用日频 K 线和目标权重策略。",
            "- 策略目标在信号日收盘后入队，最早于下一交易日执行。",
            f"- 成交估值价使用配置字段 `{self.execution.config.price_field}`，再按场景计入滑点与交易费。",
            "- 未成交的再平衡意图会在后续交易日继续重试。",
        ]
        quality_notes = self.data.quality.notes + self.data_quality_notes
        if self.non_tradable_indices:
            lines.append(f"- 本结果为含发布指数的研究模拟：{', '.join(self.non_tradable_indices)}；指数不可直接交易，模拟成交不代表可执行容量。")
        if quality_notes:
            lines.extend(["", "## 数据质量"])
            lines.extend(f"- {note}" for note in quality_notes)
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_checkpoint(path: str | Path) -> PortfolioState:
    with Path(path).open("r", encoding="utf-8") as handle:
        return PortfolioState.from_dict(json.load(handle))
