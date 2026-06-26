from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import MarketDataStore
from src.platform_core.engine import load_checkpoint, load_strategy_config
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
        self.strategy_config = load_strategy_config(config.get("strategy"))
        self.output_root = Path(output_root or config.get("output", {}).get("sim_dir", "results/sim_portfolios"))
        self.portfolio_dir = self.output_root / self.portfolio_id
        self.state_path = self.portfolio_dir / "portfolio_state.json"
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)

        data_config = config.get("data", {})
        self.data_fetch = bool(data_config.get("fetch", False))
        self.market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")

        execution_config = config.get("execution", {})
        fee_config = execution_config.get("fee", {})
        slippage_config = execution_config.get("slippage", {})
        self.execution = ExecutionEngine(
            ExecutionConfig(
                fee_profile=FeeProfile(rate=float(fee_config.get("rate", 0.0002)), min_fee=float(fee_config.get("min_fee", 0.0))),
                price_field=execution_config.get("execution_price_field", "open"),
                weight_tolerance=float(execution_config.get("weight_tolerance", 0.0005)),
                unfilled_policy=execution_config.get("unfilled_policy", "retry_next_day"),
                cash_buffer_pct=float(execution_config.get("cash_buffer_pct", 0.0)),
                skip_below_lot=bool(execution_config.get("skip_below_lot", True)),
                order_priority=execution_config.get("order_priority", "asset_id"),
                slippage_bps=float(slippage_config.get("default_bps", execution_config.get("slippage_bps", 2.0))),
                qdii_commodity_slippage_bps=float(
                    slippage_config.get("qdii_commodity_bps", execution_config.get("qdii_commodity_slippage_bps", 6.0))
                ),
                slippage_by_asset_id=slippage_config.get("asset_bps"),
                slippage_by_code=slippage_config.get("code_bps"),
                round_mode=execution_config.get("round_mode", "round"),
            )
        )
        self.code_to_asset_id = {asset.code: asset_id for asset_id, asset in self.assets.items()}
        self.dividends = self._load_dividends()
        self.splits = self._load_splits()

    def _load_dividends(self) -> list[dict[str, Any]]:
        platform_dir = Path(__file__).resolve().parent.parent.parent
        path = platform_dir / "data" / "platform_dividends.csv"
        if not path.exists():
            return []
        dividends = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dividends.append({
                    "code": row["code"].strip(),
                    "ex_date": parse_date(row["ex_date"].strip()),
                    "payment_date": parse_date(row["payment_date"].strip()),
                    "dividend_per_share": float(row["dividend_per_share"].strip()),
                })
        return dividends

    def _load_splits(self) -> list[dict[str, Any]]:
        platform_dir = Path(__file__).resolve().parent.parent.parent
        path = platform_dir / "data" / "platform_splits.csv"
        if not path.exists():
            return []
        splits = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                splits.append({
                    "code": row["code"].strip(),
                    "split_date": parse_date(row["split_date"].strip()),
                    "split_ratio": float(row["split_ratio"].strip()),
                })
        return splits

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
            start_date=(self.config.get("backtest") or {}).get("start_date"),
            end_date=date_str(target_date),
        )

        run_dir = self.portfolio_dir / "runs" / f"{date_str(target_date)}_{datetime.now().strftime('%H%M%S')}"
        run_dir.mkdir(parents=True, exist_ok=True)

        order_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        nav_rows: list[dict[str, Any]] = []
        active_strategy = None
        active_strategy_runtime: dict[str, Any] = {}
        active_strategy_version_id: int | None = None

        for current_date in data.calendar:
            if self.state.last_date and current_date <= self.state.last_date:
                continue
            if current_date > target_date:
                continue

            # 1. Process Splits
            for split in self.splits:
                if split["split_date"] == current_date:
                    asset_id = self.code_to_asset_id.get(split["code"])
                    if asset_id and asset_id in self.state.positions:
                        pos = self.state.positions[asset_id]
                        if pos.quantity > 0:
                            pos.quantity *= split["split_ratio"]
                            pos.cost_basis /= split["split_ratio"]

            # 2. Process Ex-Dividends
            for div in self.dividends:
                if div["ex_date"] == current_date:
                    asset_id = self.code_to_asset_id.get(div["code"])
                    if asset_id and asset_id in self.state.positions:
                        pos = self.state.positions[asset_id]
                        if pos.quantity > 0:
                            amount = pos.quantity * div["dividend_per_share"]
                            self.state.dividend_receivables.append({
                                "asset_id": asset_id,
                                "payment_date": div["payment_date"],
                                "amount": amount,
                            })

            # 3. Process Cash Payouts
            remaining_receivables = []
            for item in self.state.dividend_receivables:
                if item["payment_date"] <= current_date:
                    self.state.cash += item["amount"]
                else:
                    remaining_receivables.append(item)
            self.state.dividend_receivables = remaining_receivables

            bars = data.bars_on(current_date)
            if active_strategy is None:
                if self.strategy_config.get("cancel_pending_on_start", False):
                    self.state.pending_intents.clear()
                strategy_cls = get_strategy_class(self.strategy_config["strategy_name"])
                version_id = self.strategy_config.get("strategy_version_id")
                if version_id is None:
                    version_id = self.store.ensure_builtin_version(strategy_cls, self.strategy_config.get("params", {}))
                    self.strategy_config["strategy_version_id"] = version_id
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
                        params=self.strategy_config.get("params", {}),
                        runtime=active_strategy_runtime,
                    )
                )
                active_strategy_version_id = int(version_id)

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
                    params=self.strategy_config.get("params", {}),
                    runtime=active_strategy_runtime,
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
        if self.data_fetch:
            market_store = MarketDataStore(self.market_dir)
            market_store.sync_assets(
                list(self.assets.values()),
                start=date_str(self.state.last_date) if self.state.last_date else (self.config.get("backtest") or {}).get("start_date"),
                end=date_str(target_date),
                fetch=True,
            )

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
