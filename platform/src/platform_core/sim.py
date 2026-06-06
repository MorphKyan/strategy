from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import FundamentalStore, MarketDataStore, PointInTimeFundamentals
from src.platform_core.engine import load_checkpoint
from src.platform_core.execution import ExecutionConfig, ExecutionEngine, FeeProfile
from src.platform_core.models import Asset, PendingIntent, PortfolioState, TargetPortfolio, date_str, parse_date
from src.platform_core.storage import SQLiteStore
from src.platform_core.strategy import StrategyContext, get_strategy_class


@dataclass
class SimAdvanceResult:
    portfolio_id: str
    output_dir: Path
    state_path: Path
    metrics: dict[str, Any]


class SimPortfolio:
    def __init__(self, portfolio_id: str, config: dict[str, Any], store: SQLiteStore, state: PortfolioState, source_checkpoint: str | Path, output_root: str | Path | None = None):
        self.portfolio_id = portfolio_id
        self.config = config
        self.store = store
        self.state = state
        self.source_checkpoint = Path(source_checkpoint)
        self.assets = self._load_assets(config.get("assets", []))
        self.output_root = Path(output_root or config.get("output", {}).get("sim_dir", "results/sim_portfolios"))
        self.portfolio_dir = self.output_root / self.portfolio_id
        self.state_path = self.portfolio_dir / "portfolio_state.json"
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)

        data_config = config.get("data", {})
        self.data_fetch = bool(data_config.get("fetch", False))
        self.market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")
        self.fundamentals_dir = data_config.get("fundamentals_dir")

        fee_config = config.get("execution", {}).get("fee", {})
        self.execution = ExecutionEngine(
            ExecutionConfig(
                fee_profile=FeeProfile(rate=float(fee_config.get("rate", 0.0002)), min_fee=float(fee_config.get("min_fee", 0.0))),
                price_field=config.get("execution", {}).get("execution_price_field", "open_close_mid"),
                weight_tolerance=float(config.get("execution", {}).get("weight_tolerance", 0.0005)),
                unfilled_policy=config.get("execution", {}).get("unfilled_policy", "retry_next_day"),
                cash_buffer_pct=float(config.get("execution", {}).get("cash_buffer_pct", 0.0)),
                skip_below_lot=bool(config.get("execution", {}).get("skip_below_lot", True)),
                order_priority=config.get("execution", {}).get("order_priority", "asset_id"),
            )
        )

    @classmethod
    def create_from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        config: dict[str, Any],
        store: SQLiteStore,
        portfolio_id: str | None = None,
        output_root: str | Path | None = None,
    ) -> "SimPortfolio":
        checkpoint = Path(checkpoint_path)
        state = load_checkpoint(checkpoint)
        resolved_id = portfolio_id or f"sim_{checkpoint.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        portfolio = cls(resolved_id, config, store, state, checkpoint, output_root)
        portfolio._write_state(portfolio.state_path)
        store.create_sim_portfolio(resolved_id, checkpoint, portfolio.state_path, config)
        return portfolio

    def advance(self, asof_date: str) -> SimAdvanceResult:
        target_date = parse_date(asof_date)
        self._sync_data_if_requested(target_date)
        data = LocalCsvBarData(
            data_dir=self.market_dir,
            assets=self.assets.values(),
            start_date=date_str(self.state.last_date) if self.state.last_date else self.config.get("backtest", {}).get("start_date"),
            end_date=date_str(target_date),
        )
        fundamentals = PointInTimeFundamentals(self.fundamentals_dir) if self.fundamentals_dir else None

        run_dir = self.portfolio_dir / "runs" / f"{date_str(target_date)}_{datetime.now().strftime('%H%M%S')}"
        run_dir.mkdir(parents=True, exist_ok=True)

        order_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        nav_rows: list[dict[str, Any]] = []
        active_segment_key = None
        active_strategy = None
        active_strategy_runtime: dict[str, Any] = {}
        active_strategy_version_id: int | None = None

        for current_date in data.calendar:
            if self.state.last_date and current_date <= self.state.last_date:
                continue
            if current_date > target_date:
                continue
            segment = self._segment_for_date(current_date)
            if segment is None:
                continue

            bars = data.bars_on(current_date)
            segment_key = self._segment_key(segment)
            if active_segment_key != segment_key:
                if segment.get("cancel_pending_on_start", False):
                    self.state.pending_intents.clear()
                strategy_cls = get_strategy_class(segment["strategy_name"])
                version_id = segment.get("strategy_version_id")
                if version_id is None:
                    version_id = self.store.ensure_builtin_version(strategy_cls, segment.get("params", {}))
                    segment["strategy_version_id"] = version_id
                self.store.get_strategy_version(int(version_id))
                self.store.add_portfolio_reference(int(version_id), self.portfolio_id)
                active_strategy = strategy_cls()
                active_strategy_runtime = {}
                active_strategy.initialize(
                    StrategyContext(
                        date=current_date,
                        assets=self.assets,
                        bars=bars,
                        state=self.state,
                        data=data,
                        params=segment.get("params", {}),
                        runtime=active_strategy_runtime,
                        fundamental_provider=fundamentals,
                    )
                )
                active_strategy_version_id = int(version_id)
                active_segment_key = self._segment_key(segment)

            self.state.decrement_cooldowns()
            pending_target = self._target_from_pending(current_date)
            if pending_target is not None:
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=self.state,
                    assets=self.assets,
                    bars=bars,
                    target=pending_target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                    close_absent_positions=False,
                    signal_dates=self._signal_dates_from_pending(current_date),
                )
                order_rows.extend(order.to_row() for order in orders)
                trade_rows.extend(trade.to_row() for trade in trades)

            assert active_strategy is not None
            target = active_strategy.generate_targets(
                StrategyContext(
                    date=current_date,
                    assets=self.assets,
                    bars=bars,
                    state=self.state,
                    data=data,
                    params=segment.get("params", {}),
                    runtime=active_strategy_runtime,
                    fundamental_provider=fundamentals,
                )
            )
            if target is not None:
                self._replace_pending(target, current_date)

            prices = {asset_id: bar.close for asset_id, bar in bars.items()}
            total_value = self.state.total_value(prices)
            nav_rows.append(
                {
                    "date": date_str(current_date),
                    "total_value": total_value,
                    "cash": self.state.cash,
                    "pending_intent_count": len(self.state.pending_intents),
                    "strategy_version_id": active_strategy_version_id,
                }
            )
            self.state.last_date = current_date

        self._write_csv(run_dir / "suggested_orders.csv", order_rows)
        self._write_csv(run_dir / "trades.csv", trade_rows)
        self._write_csv(run_dir / "nav.csv", nav_rows)
        self._write_state(run_dir / "portfolio_state.json")
        self._write_state(self.state_path)
        metrics = {
            "portfolio_id": self.portfolio_id,
            "asof_date": date_str(target_date),
            "processed_days": len(nav_rows),
            "trade_count": len(trade_rows),
            "pending_intent_count": len(self.state.pending_intents),
            "last_date": date_str(self.state.last_date),
        }
        self._write_json(
            run_dir / "manifest.json",
            {
                "portfolio_id": self.portfolio_id,
                "source_checkpoint": str(self.source_checkpoint),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "execution_model": {
                    "signal_execution_lag_days": 1,
                    "execution_price_field": self.execution.config.price_field,
                },
                "metrics": metrics,
            },
        )
        self.store.record_sim_run(self.portfolio_id, date_str(target_date), run_dir)
        self.store.add_sim_event(self.portfolio_id, "advance", metrics)
        self.store.create_sim_portfolio(self.portfolio_id, self.source_checkpoint, self.state_path, self.config)
        return SimAdvanceResult(self.portfolio_id, run_dir, self.state_path, metrics)

    def export_state(self, output_dir: str | Path) -> Path:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        self._write_state(target / "portfolio_state.json")
        if self.state_path.exists():
            shutil.copy2(self.state_path, target / "portfolio_state.json")
        return target

    def _sync_data_if_requested(self, target_date) -> None:
        data_config = self.config.get("data", {})
        if self.data_fetch:
            market_store = MarketDataStore(self.market_dir)
            market_store.sync_assets(
                list(self.assets.values()),
                start=date_str(self.state.last_date) if self.state.last_date else self.config.get("backtest", {}).get("start_date"),
                end=date_str(target_date),
                fetch=True,
            )
            if self.fundamentals_dir:
                fundamental_store = FundamentalStore(self.fundamentals_dir, fields=data_config.get("fundamental_fields"))
                fundamental_store.sync_financial_indicators(list(self.assets.values()), fetch=True)

    def _load_assets(self, payload: list[dict[str, Any]]) -> dict[str, Asset]:
        assets: dict[str, Asset] = {}
        for item in payload:
            asset = Asset(
                asset_id=item["asset_id"],
                code=str(item["code"]),
                name=item.get("name", item["code"]),
                asset_type=item.get("asset_type", "etf"),
                exchange=item.get("exchange", "CN"),
                currency=item.get("currency", "CNY"),
                lot_size=int(item.get("lot_size", 100)),
                price_limit_pct=item.get("price_limit_pct", 0.10),
            )
            assets[asset.asset_id] = asset
        return assets

    def _segment_for_date(self, current_date) -> dict[str, Any] | None:
        for segment in self.config.get("strategies", {}).get("segments", []):
            start = parse_date(segment["start_date"])
            end = parse_date(segment["end_date"]) if segment.get("end_date") else None
            if current_date >= start and (end is None or current_date <= end):
                return segment
        return None

    @staticmethod
    def _segment_key(segment: dict[str, Any]) -> str:
        return "|".join(
            [
                str(segment.get("start_date")),
                str(segment.get("end_date")),
                str(segment.get("strategy_name")),
                str(segment.get("strategy_version_id")),
            ]
        )

    def _target_from_pending(self, current_date) -> TargetPortfolio | None:
        due = {
            asset_id: intent.target_weight
            for asset_id, intent in self.state.pending_intents.items()
            if intent.created_date < current_date
        }
        if not due:
            return None
        return TargetPortfolio(due)

    def _signal_dates_from_pending(self, current_date) -> dict[str, Any]:
        return {
            asset_id: intent.signal_date or intent.created_date
            for asset_id, intent in self.state.pending_intents.items()
            if intent.created_date < current_date
        }

    def _replace_pending(self, target: TargetPortfolio, current_date) -> None:
        target_weights = dict(target.weights)
        for asset_id, position in self.state.positions.items():
            if position.quantity > 1e-9 and asset_id not in target_weights:
                target_weights[asset_id] = 0.0
        self.state.pending_intents = {
            asset_id: PendingIntent(
                asset_id=asset_id,
                target_weight=weight,
                created_date=current_date,
                signal_date=current_date,
            )
            for asset_id, weight in target_weights.items()
        }

    def _write_state(self, path: Path) -> None:
        self._write_json(path, self.state.to_dict())

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
