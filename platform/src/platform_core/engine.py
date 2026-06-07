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
        execution_config = config.get("execution", {})
        fee_config = execution_config.get("fee", {})
        slippage_config = execution_config.get("slippage", {})
        self.execution = ExecutionEngine(
            ExecutionConfig(
                fee_profile=FeeProfile(
                    rate=float(fee_config.get("rate", 0.0002)),
                    min_fee=float(fee_config.get("min_fee", 0.0)),
                ),
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
            )
        )
        run_name = config.get("platform", {}).get("run_name", "platform_backtest")
        self.run_id = f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        configured_output = output_dir or config.get("output", {}).get("results_dir", "results/platform")
        self.output_dir = Path(configured_output) / self.run_id
        self.checkpoint_dir = self.output_dir / "checkpoints"
        
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

            # 1. Process Splits
            for split in self.splits:
                if split["split_date"] == current_date:
                    asset_id = self.code_to_asset_id.get(split["code"])
                    if asset_id and asset_id in state.positions:
                        pos = state.positions[asset_id]
                        if pos.quantity > 0:
                            pos.quantity *= split["split_ratio"]
                            pos.cost_basis /= split["split_ratio"]

            # 2. Process Ex-Dividends
            for div in self.dividends:
                if div["ex_date"] == current_date:
                    asset_id = self.code_to_asset_id.get(div["code"])
                    if asset_id and asset_id in state.positions:
                        pos = state.positions[asset_id]
                        if pos.quantity > 0:
                            amount = pos.quantity * div["dividend_per_share"]
                            state.dividend_receivables.append({
                                "asset_id": asset_id,
                                "payment_date": div["payment_date"],
                                "amount": amount,
                            })

            # 3. Process Cash Payouts
            remaining_receivables = []
            for item in state.dividend_receivables:
                if item["payment_date"] <= current_date:
                    state.cash += item["amount"]
                else:
                    remaining_receivables.append(item)
            state.dividend_receivables = remaining_receivables

            segment_key = self._segment_key(segment)
            bars = self.data.bars_on(current_date)
            if active_segment_key != segment_key:
                if segment.get("cancel_pending_on_start", False):
                    state.pending_intents.clear()
                strategy_cls = get_strategy_class(segment["strategy_name"])
                version_id = segment.get("strategy_version_id")
                if version_id is not None:
                    try:
                        self.store.get_strategy_version(int(version_id))
                    except KeyError:
                        version_id = None
                if version_id is None:
                    version_id = self.store.ensure_builtin_version(strategy_cls, segment.get("params", {}))
                    segment["strategy_version_id"] = version_id
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
            pending_target = self._target_from_pending(state, current_date)
            if pending_target is not None:
                orders, trades = self.execution.apply_target(
                    current_date=current_date,
                    state=state,
                    assets=self.assets,
                    bars=bars,
                    target=pending_target,
                    cooldown_days=int(active_strategy_runtime.get("cooldown_days", 0)),
                    close_absent_positions=False,
                    signal_dates=self._signal_dates_from_pending(state, current_date),
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
            if self.config.get("backtest", {}).get("enable_checkpoints", True):
                checkpoint_path = self.checkpoint_dir / f"{date_str(current_date)}.json"
                self._write_json(checkpoint_path, state.to_dict())
                self.store.add_checkpoint(self.run_id, date_str(current_date), checkpoint_path)

        if not self.config.get("backtest", {}).get("enable_checkpoints", True) and self.data.calendar:
            last_date = self.data.calendar[-1]
            checkpoint_path = self.checkpoint_dir / f"{date_str(last_date)}.json"
            self._write_json(checkpoint_path, state.to_dict())
            self.store.add_checkpoint(self.run_id, date_str(last_date), checkpoint_path)


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
    def _target_from_pending(state: PortfolioState, current_date: date) -> TargetPortfolio | None:
        due = {
            asset_id: intent.target_weight
            for asset_id, intent in state.pending_intents.items()
            if intent.created_date < current_date
        }
        if not due:
            return None
        return TargetPortfolio(due)

    @staticmethod
    def _signal_dates_from_pending(state: PortfolioState, current_date: date) -> dict[str, date]:
        return {
            asset_id: intent.signal_date or intent.created_date
            for asset_id, intent in state.pending_intents.items()
            if intent.created_date < current_date
        }

    @staticmethod
    def _replace_pending(state: PortfolioState, target: TargetPortfolio, current_date: date) -> None:
        target_weights = dict(target.weights)
        for asset_id, position in state.positions.items():
            if position.quantity > 1e-9 and asset_id not in target_weights:
                target_weights[asset_id] = 0.0
        state.pending_intents = {
            asset_id: PendingIntent(
                asset_id=asset_id,
                target_weight=weight,
                created_date=current_date,
                signal_date=current_date,
            )
            for asset_id, weight in target_weights.items()
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
            "execution_model": {
                "signal_execution_lag_days": 1,
                "execution_price_field": self.execution.config.price_field,
            },
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
            f"- 年化金额换手率：{metrics.get('annualized_turnover_amount', metrics.get('annualized_turnover', 0.0)) * 100:.2f}%",
            f"- 年化数量换手：{metrics.get('annualized_turnover_quantity', 0.0):.4f}",
            f"- 成交笔数：{metrics.get('trade_count', 0)}",
            f"- 期末待执行意图数：{metrics.get('pending_intent_count', 0)}",
            "",
            "## 说明",
            "- 该 M0-M2 引擎使用日频 K 线和目标权重策略。",
            "- 策略目标在信号日收盘后入队，最早于下一交易日执行。",
            "- 默认成交价使用执行日开盘价与收盘价的中间价代理。",
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
        total_values = [float(row.get("total_value", 0.0)) for row in nav_rows]
        average_total_value = sum(total_values) / len(total_values) if total_values else 0.0
        years = len(nav_rows) / 252 if nav_rows else 0.0
        turnover_amount_total = sum(abs(float(row.get("trade_value", 0.0))) for row in trade_rows)
        turnover_quantity_total = sum(abs(float(row.get("quantity", 0.0))) for row in trade_rows)
        turnover_amount_ratio = turnover_amount_total / average_total_value if average_total_value > 0 else 0.0
        annualized_turnover_amount = turnover_amount_ratio / years if years else turnover_amount_ratio
        annualized_turnover_quantity = turnover_quantity_total / years if years else turnover_quantity_total
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
            "turnover_total": turnover_amount_total,
            "annualized_turnover": annualized_turnover_amount,
            "turnover_amount_total": turnover_amount_total,
            "turnover_amount_ratio": turnover_amount_ratio,
            "annualized_turnover_amount": annualized_turnover_amount,
            "turnover_quantity_total": turnover_quantity_total,
            "annualized_turnover_quantity": annualized_turnover_quantity,
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
