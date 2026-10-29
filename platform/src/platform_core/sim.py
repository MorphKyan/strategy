from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.platform_core.corporate_actions import (
    apply_due_dividends, apply_due_splits, load_corporate_actions, resolve_split_effective_dates,
)
from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import MarketDataStore, assets_from_config
from src.platform_core.engine import load_checkpoint, load_strategy_config
from src.platform_core.execution import ExecutionConfig, ExecutionEngine
from src.platform_core.models import PortfolioState, date_str, parse_date
from src.platform_core.storage import SQLiteStore, InMemoryStore, write_csv_rows, write_json
from src.platform_core.strategy import StrategyContext, get_strategy_class


@dataclass
class SimAdvanceResult:
    portfolio_id: str
    output_dir: Path
    state_path: Path
    metrics: dict[str, Any]


class SimPortfolio:
    def __init__(self, portfolio_id: str, config: dict[str, Any], store: SQLiteStore | InMemoryStore, state: PortfolioState, source_checkpoint: str | Path, output_root: str | Path | None = None):
        self.portfolio_id = portfolio_id
        self.config = config
        self.store = store
        self.state = state
        self.source_checkpoint = Path(source_checkpoint)
        self.assets = {asset.asset_id: asset for asset in assets_from_config(config.get("assets", []))}
        self.state.validate_assets(self.assets)
        self.strategy_config = load_strategy_config(config.get("strategy"))
        self.output_root = Path(output_root or config.get("output", {}).get("sim_dir", "results/sim_portfolios"))
        self.portfolio_dir = self.output_root / self.portfolio_id
        self.state_path = self.portfolio_dir / "portfolio_state.json"
        self.committed_run_ids: list[str] = []

        data_config = config.get("data", {})
        self.data_fetch = bool(data_config.get("fetch", False))
        self.market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")

        self.execution = ExecutionEngine(ExecutionConfig.from_config(config.get("execution", {})))
        self.code_to_asset_id = {asset.code: asset_id for asset_id, asset in self.assets.items()}
        self.dividends = load_corporate_actions(self.config, "dividends")
        self.splits = load_corporate_actions(self.config, "splits")

    @classmethod
    def load(
        cls,
        portfolio_id: str,
        config: dict[str, Any],
        store: SQLiteStore | InMemoryStore,
        output_root: str | Path | None = None,
    ) -> "SimPortfolio":
        """从 `results/sim_portfolios/<id>/portfolio_state.json` 恢复既有模拟组合。

        与 create_from_checkpoint 的区别：不回到原始 checkpoint 重放，而是从上次
        advance 持久化的状态继续增量推进——影子组合每日跟跑（蓝图 A5）用这个。
        """
        root = Path(output_root or config.get("output", {}).get("sim_dir", "results/sim_portfolios"))
        state_path = root / portfolio_id / "portfolio_state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"模拟组合状态不存在: {state_path}（先用 create_from_checkpoint 建立）")
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        state = PortfolioState.from_dict(payload)
        origin = state.strategy_state.get("_sim_source_checkpoint", str(state_path))
        portfolio = cls(portfolio_id, config, store, state, source_checkpoint=origin, output_root=output_root)
        portfolio.committed_run_ids = payload.get("committed_run_ids", [])
        return portfolio

    @classmethod
    def create_from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        config: dict[str, Any],
        store: SQLiteStore | InMemoryStore,
        portfolio_id: str | None = None,
        output_root: str | Path | None = None,
    ) -> "SimPortfolio":
        checkpoint = Path(checkpoint_path)
        state = load_checkpoint(checkpoint)
        state.strategy_state["_sim_source_checkpoint"] = str(checkpoint)
        resolved_id = portfolio_id or f"sim_{checkpoint.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        portfolio = cls(resolved_id, config, store, state, checkpoint, output_root)
        portfolio.portfolio_dir.mkdir(parents=True, exist_ok=False)
        write_json(portfolio.state_path, portfolio.state.to_dict())
        store.create_sim_portfolio(resolved_id, checkpoint, portfolio.state_path, config)
        return portfolio

    def advance(self, asof_date: str) -> SimAdvanceResult:
        target_date = parse_date(asof_date)
        state = copy.deepcopy(self.state)
        state.strategy_state.setdefault("_sim_source_checkpoint", str(self.source_checkpoint))
        self._sync_data_if_requested(target_date)
        data = LocalCsvBarData(
            data_dir=self.market_dir,
            assets=self.assets.values(),
            start_date=(self.config.get("backtest") or {}).get("start_date"),
            end_date=date_str(target_date),
        )
        processing_dates = list(data.calendar)
        data.extend_calendar()

        run_dir = self.portfolio_dir / "runs" / f"{date_str(target_date)}_{datetime.now().strftime('%H%M%S_%f')}"
        run_dir.mkdir(parents=True, exist_ok=False)

        order_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        nav_rows: list[dict[str, Any]] = []
        active_strategy = None
        active_strategy_runtime: dict[str, Any] = {}
        active_strategy_version_id: int | None = None
        identity = {"strategy_name": self.strategy_config["strategy_name"],
                    "params": self.strategy_config.get("params", {})}

        resolve_split_effective_dates(self.splits, self.code_to_asset_id, data)

        for current_date in processing_dates:
            if state.last_date and current_date <= state.last_date:
                continue
            if current_date > target_date:
                continue

            # 1. Process Splits（在 split_date 后首个真实交易日生效，见 corporate_actions）
            apply_due_splits(self.splits, state, self.code_to_asset_id, current_date)

            apply_due_dividends(self.dividends, state, self.code_to_asset_id, current_date)

            bars = data.bars_on(current_date)
            if active_strategy is None:
                if self.strategy_config.get("cancel_pending_on_start", False):
                    state.pending_intents.clear()
                strategy_cls = get_strategy_class(self.strategy_config["strategy_name"])
                version_id = self.store.ensure_builtin_version(strategy_cls, self.strategy_config.get("params", {}))
                self.strategy_config["strategy_version_id"] = version_id
                identity["source_hash"] = self.store.get_strategy_version(version_id)["source_hash"]
                self.store.add_portfolio_reference(int(version_id), self.portfolio_id)
                active_strategy = strategy_cls()
                active_strategy_runtime = {}
                active_strategy.initialize(
                    StrategyContext(
                        date=current_date,
                        assets=self.assets,
                        bars=bars,
                        state=state,
                        data=data,
                        params=self.strategy_config.get("params", {}),
                        runtime=active_strategy_runtime,
                    )
                )
                saved = state.strategy_state.get("_strategy_runtime", {})
                if saved.get("identity") == identity:
                    active_strategy_runtime.update(saved["runtime"])
                elif "opened" in active_strategy_runtime and any(
                    position.quantity > 1e-9 for position in state.positions.values()
                ):
                    active_strategy_runtime["opened"] = True
                active_strategy_version_id = int(version_id)

            state.decrement_cooldowns()
            pending_target = state.pending_target(current_date)
            if pending_target is not None:
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=state,
                    assets=self.assets,
                    bars=bars,
                    target=pending_target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                    close_absent_positions=False,
                    signal_dates=state.pending_signal_dates(current_date),
                )
                order_rows.extend(order.to_row() for order in orders)
                trade_rows.extend(trade.to_row() for trade in trades)

            assert active_strategy is not None
            target = active_strategy.generate_targets(
                StrategyContext(
                    date=current_date,
                    assets=self.assets,
                    bars=bars,
                    state=state,
                    data=data,
                    params=self.strategy_config.get("params", {}),
                    runtime=active_strategy_runtime,
                )
            )
            if target is not None:
                unknown = set(target.weights) - set(self.assets)
                if unknown:
                    raise ValueError(f"Target portfolio contains unknown assets: {sorted(unknown)}")
                state.replace_pending(target, current_date)

            state.strategy_state["_strategy_runtime"] = {"identity": identity, "runtime": active_strategy_runtime}

            prices = {asset_id: bar.close for asset_id, bar in bars.items()}
            total_value = state.total_value(prices)
            nav_rows.append(
                {
                    "date": date_str(current_date),
                    "total_value": total_value,
                    "cash": state.cash,
                    "pending_intent_count": len(state.pending_intents),
                    "strategy_version_id": active_strategy_version_id,
                }
            )
            state.last_date = current_date

        write_json(run_dir / "manifest.json", {"requires_state_commit": True})
        write_csv_rows(run_dir / "suggested_orders.csv", order_rows)
        write_csv_rows(run_dir / "trades.csv", trade_rows)
        write_csv_rows(run_dir / "nav.csv", nav_rows)
        write_json(run_dir / "portfolio_state.json", state.to_dict())
        metrics = {
            "portfolio_id": self.portfolio_id,
            "asof_date": date_str(target_date),
            "processed_days": len(nav_rows),
            "trade_count": len(trade_rows),
            "pending_intent_count": len(state.pending_intents),
            "last_date": date_str(state.last_date),
        }
        write_json(
            run_dir / "manifest.json",
            {
                "portfolio_id": self.portfolio_id,
                "requires_state_commit": True,
                "source_checkpoint": str(self.source_checkpoint),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "execution_model": {
                    "signal_execution_lag_days": 1,
                    "execution_price_field": self.execution.config.price_field,
                },
                "metrics": metrics,
            },
        )
        committed_run_ids = [*self.committed_run_ids, run_dir.name]
        write_json(self.state_path, state.to_dict() | {"committed_run_ids": committed_run_ids})
        self.state.__dict__.update(state.__dict__)
        self.committed_run_ids = committed_run_ids
        self.store.record_sim_run(self.portfolio_id, date_str(target_date), run_dir)
        self.store.add_sim_event(self.portfolio_id, "advance", metrics)
        self.store.create_sim_portfolio(self.portfolio_id, self.source_checkpoint, self.state_path, self.config)
        return SimAdvanceResult(self.portfolio_id, run_dir, self.state_path, metrics)

    def _sync_data_if_requested(self, target_date) -> None:
        if self.data_fetch:
            market_store = MarketDataStore(self.market_dir)
            market_store.sync_assets(
                list(self.assets.values()),
                start=date_str(self.state.last_date) if self.state.last_date else (self.config.get("backtest") or {}).get("start_date"),
                end=date_str(target_date),
                fetch=True,
            )
