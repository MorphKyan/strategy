from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import FundamentalStore, MarketDataStore, PointInTimeFundamentals
from src.platform_core.execution import ExecutionConfig, ExecutionEngine, FeeProfile
from src.platform_core.models import Asset, PendingIntent, PortfolioState, TargetPortfolio, date_str, parse_date
from src.platform_core.storage import SQLiteStore
from src.platform_core.strategy import StrategyContext, get_strategy_class


@dataclass
class PlatformBacktestResult:
    run_id: str
    output_dir: Path
    metrics: dict[str, Any]


class PlatformBacktestEngine:
    def __init__(self, config: dict[str, Any], store: SQLiteStore, output_dir: str | Path | None = None):
        self.config = config
        self.store = store
        self.assets = self._load_assets(config.get("assets", []))
        backtest_config = config.get("backtest", {})
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
        self.fundamentals: PointInTimeFundamentals | None = None
        fundamentals_dir = data_config.get("fundamentals_dir")
        if fundamentals_dir:
            if data_fetch:
                fundamental_store = FundamentalStore(fundamentals_dir, fields=data_config.get("fundamental_fields"))
                fundamental_report = fundamental_store.sync_financial_indicators(list(self.assets.values()), fetch=True)
                self.data_quality_notes.extend(fundamental_report.notes)
            self.fundamentals = PointInTimeFundamentals(fundamentals_dir)
        fee_config = config.get("execution", {}).get("fee", {})
        self.execution = ExecutionEngine(
            ExecutionConfig(
                fee_profile=FeeProfile(
                    rate=float(fee_config.get("rate", 0.0002)),
                    min_fee=float(fee_config.get("min_fee", 0.0)),
                ),
                price_field=config.get("execution", {}).get("price_field", "close"),
                weight_tolerance=float(config.get("execution", {}).get("weight_tolerance", 0.0005)),
                unfilled_policy=config.get("execution", {}).get("unfilled_policy", "retry_next_day"),
            )
        )
        run_name = config.get("platform", {}).get("run_name", "platform_backtest")
        self.run_id = f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        configured_output = output_dir or config.get("output", {}).get("results_dir", "results/platform")
        self.output_dir = Path(configured_output) / self.run_id
        self.checkpoint_dir = self.output_dir / "checkpoints"

    def run(self) -> PlatformBacktestResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._write_config_snapshot()
        backtest_id = self.store.record_backtest(self.run_id, self.config, self.output_dir)

        state = self._initial_state()
        nav_rows: list[dict[str, Any]] = []
        position_rows: list[dict[str, Any]] = []
        order_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        active_segment_key = None
        active_strategy = None
        active_strategy_runtime: dict[str, Any] = {}
        active_strategy_version_id: int | None = None

        for current_date in self.data.calendar:
            segment = self._segment_for_date(current_date)
            if segment is None:
                continue

            segment_key = self._segment_key(segment)
            bars = self.data.bars_on(current_date)
            if active_segment_key != segment_key:
                if segment.get("cancel_pending_on_start", False):
                    state.pending_intents.clear()
                strategy_cls = get_strategy_class(segment["strategy_name"])
                version_id = segment.get("strategy_version_id")
                if version_id is None:
                    version_id = self.store.ensure_builtin_version(strategy_cls, segment.get("params", {}))
                    segment["strategy_version_id"] = version_id
                self.store.get_strategy_version(int(version_id))
                self.store.add_strategy_reference(int(version_id), "backtest", str(backtest_id))
                active_strategy = strategy_cls()
                active_strategy_runtime = {}
                init_context = StrategyContext(
                    date=current_date,
                    assets=self.assets,
                    bars=bars,
                    state=state,
                    data=self.data,
                    params=segment.get("params", {}),
                    runtime=active_strategy_runtime,
                    fundamental_provider=self.fundamentals,
                )
                active_strategy.initialize(init_context)
                active_strategy_version_id = int(version_id)
                active_segment_key = self._segment_key(segment)

            state.decrement_cooldowns()
            pending_target = self._target_from_pending(state)
            if pending_target is not None:
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=state,
                    assets=self.assets,
                    bars=bars,
                    target=pending_target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                    close_absent_positions=False,
                )
                order_rows.extend(order.to_row() for order in orders)
                trade_rows.extend(trade.to_row() for trade in trades)

            assert active_strategy is not None
            context = StrategyContext(
                date=current_date,
                assets=self.assets,
                bars=bars,
                state=state,
                data=self.data,
                params=segment.get("params", {}),
                runtime=active_strategy_runtime,
                fundamental_provider=self.fundamentals,
            )
            target = active_strategy.generate_targets(context)
            if target is not None:
                self._validate_target_assets(target)
                self._replace_pending(state, target, current_date)
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=state,
                    assets=self.assets,
                    bars=bars,
                    target=target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                )
                order_rows.extend(order.to_row() for order in orders)
                trade_rows.extend(trade.to_row() for trade in trades)

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
            checkpoint_path = self.checkpoint_dir / f"{date_str(current_date)}.json"
            self._write_json(checkpoint_path, state.to_dict())
            self.store.add_checkpoint(self.run_id, date_str(current_date), checkpoint_path)

        self._write_csv("nav.csv", nav_rows)
        self._write_csv("positions.csv", position_rows)
        self._write_csv("orders.csv", order_rows)
        self._write_csv("trades.csv", trade_rows)
        metrics = self._metrics(nav_rows, trade_rows)
        self._write_manifest(metrics)
        self._write_report(metrics)
        return PlatformBacktestResult(run_id=self.run_id, output_dir=self.output_dir, metrics=metrics)

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
        if not assets:
            raise ValueError("At least one asset is required.")
        return assets

    def _initial_state(self) -> PortfolioState:
        portfolio = self.config.get("portfolio", {})
        state = PortfolioState(cash=float(portfolio.get("initial_cash", 0.0)))
        for item in portfolio.get("initial_positions", []):
            position = state.position(item["asset_id"])
            position.quantity = float(item.get("quantity", 0.0))
            position.cost_basis = float(item.get("cost_basis", 0.0))
        return state

    def _initial_equity(self) -> float:
        portfolio = self.config.get("portfolio", {})
        return float(portfolio.get("initial_equity") or portfolio.get("initial_cash") or 1.0)

    def _segment_for_date(self, current_date: date) -> dict[str, Any] | None:
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

    @staticmethod
    def _target_from_pending(state: PortfolioState) -> TargetPortfolio | None:
        if not state.pending_intents:
            return None
        return TargetPortfolio({asset_id: intent.target_weight for asset_id, intent in state.pending_intents.items()})

    @staticmethod
    def _replace_pending(state: PortfolioState, target: TargetPortfolio, current_date: date) -> None:
        state.pending_intents = {
            asset_id: PendingIntent(asset_id=asset_id, target_weight=weight, created_date=current_date)
            for asset_id, weight in target.weights.items()
        }

    def _validate_target_assets(self, target: TargetPortfolio) -> None:
        unknown = set(target.weights) - set(self.assets)
        if unknown:
            raise ValueError(f"Target portfolio contains unknown assets: {sorted(unknown)}")

    def _write_config_snapshot(self) -> None:
        with (self.output_dir / "config_snapshot.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self.config, handle, allow_unicode=True, sort_keys=False)

    def _write_manifest(self, metrics: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine": "platform_core.daily_event",
            "metrics": metrics,
            "data_quality_notes": self.data.quality.notes + self.data_quality_notes,
        }
        self._write_json(self.output_dir / "manifest.json", payload)

    def _write_report(self, metrics: dict[str, Any]) -> None:
        lines = [
            f"# 平台回测报告：{self.run_id}",
            "",
            "## 摘要",
            f"- 开始日期：{metrics.get('start_date')}",
            f"- 结束日期：{metrics.get('end_date')}",
            f"- 累计收益率：{metrics.get('total_return', 0.0) * 100:.2f}%",
            f"- 最大回撤：{metrics.get('max_drawdown', 0.0) * 100:.2f}%",
            f"- 成交笔数：{metrics.get('trade_count', 0)}",
            f"- 期末待执行意图数：{metrics.get('pending_intent_count', 0)}",
            "",
            "## 说明",
            "- 该 M0-M2 引擎使用日频 K 线和目标权重策略。",
            "- 未成交的再平衡意图会在后续交易日继续重试。",
        ]
        quality_notes = self.data.quality.notes + self.data_quality_notes
        if quality_notes:
            lines.extend(["", "## 数据质量"])
            lines.extend(f"- {note}" for note in quality_notes)
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _metrics(nav_rows: list[dict[str, Any]], trade_rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not nav_rows:
            return {"trade_count": len(trade_rows)}
        net_values = [float(row["net_value"]) for row in nav_rows]
        peak = net_values[0]
        max_drawdown = 0.0
        for value in net_values:
            peak = max(peak, value)
            if peak:
                max_drawdown = min(max_drawdown, value / peak - 1)
        return {
            "start_date": nav_rows[0]["date"],
            "end_date": nav_rows[-1]["date"],
            "observations": len(nav_rows),
            "total_return": net_values[-1] / net_values[0] - 1 if net_values[0] else 0.0,
            "max_drawdown": max_drawdown,
            "trade_count": len(trade_rows),
            "turnover_total": sum(abs(float(row.get("trade_value", 0.0))) for row in trade_rows),
            "pending_intent_count": int(nav_rows[-1].get("pending_intent_count", 0)),
        }

    def _write_csv(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self.output_dir / name
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_checkpoint(path: str | Path) -> PortfolioState:
    with Path(path).open("r", encoding="utf-8") as handle:
        return PortfolioState.from_dict(json.load(handle))
