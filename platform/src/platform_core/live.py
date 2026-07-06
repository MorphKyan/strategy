"""实盘镜像组合（LivePortfolio）：mark-to-real 环路的最小闭环。

与 `sim.py` 的纸面组合是两套环路：SimPortfolio 自动模拟撮合，LivePortfolio
**绝不模拟成交**——现实才是撮合引擎。环路见 `docs/next_phase_blueprint.md` §5：

  每个交易日收盘后：
    reconcile  用户提供真实持仓+现金 → 覆盖写入组合状态（真值重置，误差每天清零）
    plan       策略基于真实权重+最新数据算目标 → dry-run 执行引擎出"明日下单票"
  次日：用户照票下单（成交价/股数偏差落在阈值带内，下次调仓自然修正）

产物目录 `results/live_portfolios/<portfolio_id>/`：
  portfolio_state.json   组合状态（reconcile 覆盖；plan 只更新 pending_intents）
  real_nav.csv           每次 reconcile 追加一行真实净值（月度归因的数据源）
  tickets/ticket_<date>.csv / .txt   下单票（CSV 供程序读，TXT 人可照做）

票面股数按 plan 日收盘价估算（执行引擎 price_field 强制为 close），次日实际
成交价的偏差无需在意。与 SQLite 元数据库的集成留待主线 A4。
"""

from __future__ import annotations

import copy
import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import MarketDataStore
from src.platform_core.engine import load_strategy_config
from src.platform_core.execution import ExecutionConfig, ExecutionEngine, FeeProfile
from src.platform_core.models import (
    Asset,
    Order,
    PendingIntent,
    PortfolioState,
    Position,
    TargetPortfolio,
    date_str,
    parse_date,
)
from src.platform_core.strategy import StrategyContext, get_strategy_class


def _next_weekday(day: date) -> date:
    candidate = day + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


@dataclass
class ReconcileResult:
    portfolio_id: str
    asof_date: date
    cash: float
    positions_value: float
    total_value: float
    state_path: Path


@dataclass
class PlanResult:
    portfolio_id: str
    plan_date: date
    has_target: bool
    order_count: int
    ticket_csv: Path | None
    ticket_txt: Path
    text: str


@dataclass
class CycleResult:
    portfolio_id: str
    asof_date: date
    synced: bool
    skipped_non_trading: bool
    reconciled: bool
    plan: PlanResult | None
    notified: bool


TICKET_COLUMNS = [
    "date",
    "asset_id",
    "code",
    "name",
    "side",
    "quantity",
    "est_price",
    "est_value",
    "weight_before",
    "weight_target",
    "est_fee",
    "note",
]


class LivePortfolio:
    def __init__(self, portfolio_id: str, config: dict[str, Any], output_root: str | Path | None = None):
        self.portfolio_id = portfolio_id
        self.config = config
        self.assets = self._load_assets(config.get("assets", []))
        self.code_to_asset_id = {asset.code: asset_id for asset_id, asset in self.assets.items()}
        self.strategy_config = load_strategy_config(config.get("strategy"))

        data_config = config.get("data", {})
        self.data_fetch = bool(data_config.get("fetch", False))
        self.market_dir = data_config.get("market_store_dir") or data_config.get("data_dir", "data")

        execution_config = config.get("execution", {})
        fee_config = execution_config.get("fee", {})
        slippage_config = execution_config.get("slippage", {})
        self.execution = ExecutionEngine(
            ExecutionConfig(
                fee_profile=FeeProfile(rate=float(fee_config.get("rate", 0.0002)), min_fee=float(fee_config.get("min_fee", 0.0))),
                # 票面按 plan 日收盘价估算，与配置的回测执行价字段无关
                price_field="close",
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

        self.output_root = Path(output_root or config.get("output", {}).get("live_dir", "results/live_portfolios"))
        self.portfolio_dir = self.output_root / self.portfolio_id
        self.state_path = self.portfolio_dir / "portfolio_state.json"
        self.real_nav_path = self.portfolio_dir / "real_nav.csv"
        self.tickets_dir = self.portfolio_dir / "tickets"

    # ---------------------------------------------------------------- reconcile

    def reconcile(self, holdings_csv: str | Path, cash: float, asof_date: str | date) -> ReconcileResult:
        """真值重置：用真实持仓+现金构造全新组合状态覆盖写入。

        holdings_csv 契约（表头必需）：code,quantity[,cost_basis]
        cost_basis 缺省时用 asof 日收盘价近似（只影响展示，不影响策略）。
        """
        asof = parse_date(asof_date)
        holdings = self._read_holdings(holdings_csv)

        data = self._load_data(asof)
        bars = data.bars_on(asof)
        prices = {asset_id: bar.close for asset_id, bar in bars.items()}

        previous = self._load_state()
        positions: dict[str, Position] = {}
        for code, quantity, cost_basis in holdings:
            asset_id = self.code_to_asset_id.get(code)
            if asset_id is None:
                known = ", ".join(sorted(self.code_to_asset_id))
                raise ValueError(f"holdings 中的代码 {code} 不在组合配置里（已知代码: {known}）")
            if quantity <= 0:
                continue
            resolved_cost = cost_basis if cost_basis is not None else prices.get(asset_id, 0.0)
            positions[asset_id] = Position(asset_id=asset_id, quantity=quantity, cost_basis=resolved_cost)

        state = PortfolioState(
            cash=float(cash),
            positions=positions,
            pending_intents={},  # 昨日的票现实已处理完毕
            cooldown_pool=dict(previous.cooldown_pool) if previous else {},
            strategy_state=dict(previous.strategy_state) if previous else {},
            last_date=asof,
        )
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)
        self._write_state(state)

        positions_value = sum(pos.quantity * prices.get(asset_id, 0.0) for asset_id, pos in positions.items())
        total_value = float(cash) + positions_value
        self._append_real_nav(asof, float(cash), positions_value, total_value)
        return ReconcileResult(self.portfolio_id, asof, float(cash), positions_value, total_value, self.state_path)

    # ---------------------------------------------------------------- plan

    def plan(self, asof_date: str | date) -> PlanResult:
        """生成明日下单票。不改真实持仓：撮合只发生在 deepcopy 的状态上。"""
        state = self._load_state()
        if state is None:
            raise FileNotFoundError(f"{self.state_path} 不存在，请先 reconcile 导入真实持仓。")

        asof = parse_date(asof_date)
        data = self._load_data(asof)
        tradable = [d for d in data.calendar if d <= asof]
        if not tradable:
            raise ValueError(f"{date_str(asof)} 之前没有任何行情数据。")
        plan_date = max(tradable)
        # 实盘 plan 时 plan_date 必然是数据末日，而 is_month_end() 等节奏判断把
        # "日历最后一天"视为月末/季末——不补日历的话月频策略会天天触发。
        # 用下一个工作日近似真实日历（极端情形：月末最后几个交易日全是节假日时，
        # 当月的月末触发会顺延到下次偏离超阈值或下一个月末，可接受）。
        if plan_date == data.calendar[-1]:
            data.calendar.append(_next_weekday(plan_date))
        bars = data.bars_on(plan_date)
        prices = {asset_id: bar.close for asset_id, bar in bars.items()}

        strategy_cls = get_strategy_class(self.strategy_config["strategy_name"])
        strategy = strategy_cls()
        runtime: dict[str, Any] = {}
        context = StrategyContext(
            date=plan_date,
            assets=self.assets,
            bars=bars,
            state=state,
            data=data,
            params=self.strategy_config.get("params", {}),
            runtime=runtime,
        )
        strategy.initialize(context)
        target = strategy.generate_targets(context)

        self.tickets_dir.mkdir(parents=True, exist_ok=True)
        ticket_txt = self.tickets_dir / f"ticket_{date_str(plan_date)}.txt"

        if target is None:
            text = f"【无操作】{date_str(plan_date)} 组合权重在阈值带内，今日无需交易。"
            ticket_txt.write_text(text + "\n", encoding="utf-8")
            return PlanResult(self.portfolio_id, plan_date, False, 0, None, ticket_txt, text)

        # 未出现在目标里的既有持仓视为清仓目标（与 sim 的 _replace_pending 口径一致）
        target_weights = dict(target.weights)
        for asset_id, position in state.positions.items():
            if position.quantity > 1e-9 and asset_id not in target_weights:
                target_weights[asset_id] = 0.0

        # 把目标记入 pending_intents 便于核对/看板展示；真实持仓与现金不动
        state.pending_intents = {
            asset_id: PendingIntent(asset_id=asset_id, target_weight=weight, created_date=plan_date, signal_date=plan_date)
            for asset_id, weight in target_weights.items()
        }
        self._write_state(state)

        weights_before = state.weights(prices)
        dry_state = copy.deepcopy(state)
        orders, trades = self.execution.apply_target(
            current_date=plan_date,
            state=dry_state,
            assets=self.assets,
            bars=bars,
            target=TargetPortfolio(target_weights),
            cooldown_days=int(runtime.get("cooldown_days", 0)),
            close_absent_positions=False,
        )
        fee_by_order = {trade.order_id: trade.fee for trade in trades}
        total_value = state.total_value(prices)

        ticket_csv = self.tickets_dir / f"ticket_{date_str(plan_date)}.csv"
        rows = [
            self._ticket_row(order, weights_before, target_weights, fee_by_order)
            for order in orders
            if order.quantity > 0
        ]
        self._write_ticket_csv(ticket_csv, rows)
        text = self._render_ticket_text(plan_date, rows, total_value, state.cash)
        ticket_txt.write_text(text + "\n", encoding="utf-8")
        actionable = [row for row in rows if row["note"] == ""]
        return PlanResult(self.portfolio_id, plan_date, True, len(actionable), ticket_csv, ticket_txt, text)

    # ---------------------------------------------------------------- cycle

    def cycle(
        self,
        asof_date: str | date,
        holdings_csv: str | Path | None = None,
        cash: float | None = None,
        do_sync: bool | None = None,
        notifier: Callable[[str, str], bool] | None = None,
        force: bool = False,
    ) -> CycleResult:
        """一条命令跑完整环路：sync →（可选）reconcile → plan →（可选）notify。

        - holdings_csv 缺省时跳过 reconcile，直接用上次对齐的状态 plan（推荐的
          自动化节奏：定时任务每天只 plan，用户实际下单后才手动 reconcile）。
        - asof 不在交易日历里（周末/节假日/数据未同步到位）时直接跳过，
          避免用陈旧 bar 重复出票；`force=True` 可强制按最近交易日出票。
        - notifier 为 (title, text) -> bool 的可调用对象；推送失败不影响主流程。
        """
        asof = parse_date(asof_date)
        synced = False
        if do_sync or (do_sync is None and self.data_fetch):
            self._sync_data(asof)
            synced = True

        data = self._load_data(asof)
        if asof not in set(data.calendar) and not force:
            return CycleResult(self.portfolio_id, asof, synced, True, False, None, False)

        reconciled = False
        if holdings_csv is not None:
            if cash is None:
                raise ValueError("reconcile 需要同时提供 cash（真实账户现金余额）。")
            self.reconcile(holdings_csv, cash=cash, asof_date=asof)
            reconciled = True

        plan_result = self.plan(asof)
        notified = False
        if notifier is not None:
            title = f"调仓提醒 {date_str(plan_result.plan_date)}" if plan_result.has_target else f"组合无操作 {date_str(plan_result.plan_date)}"
            notified = bool(notifier(title, plan_result.text))
        return CycleResult(self.portfolio_id, asof, synced, False, reconciled, plan_result, notified)

    def _sync_data(self, end: date) -> None:
        market_store = MarketDataStore(self.market_dir)
        state = self._load_state()
        start = date_str(state.last_date) if state and state.last_date else (self.config.get("backtest") or {}).get("start_date")
        market_store.sync_assets(list(self.assets.values()), start=start, end=date_str(end), fetch=True)

    # ---------------------------------------------------------------- helpers

    def _ticket_row(
        self,
        order: Order,
        weights_before: dict[str, float],
        target_weights: dict[str, float],
        fee_by_order: dict[str, float],
    ) -> dict[str, Any]:
        asset = self.assets[order.asset_id]
        # dry-run 中被拒的订单（如涨跌停）保留在票上并注明原因，由人判断
        note = "" if order.status == "FILLED" else f"dry-run:{order.status}:{order.reason}"
        return {
            "date": date_str(order.date),
            "asset_id": order.asset_id,
            "code": asset.code,
            "name": asset.name,
            "side": order.side,
            "quantity": order.quantity,
            "est_price": order.price,
            "est_value": round(order.trade_value, 2),
            "weight_before": round(weights_before.get(order.asset_id, 0.0), 6),
            "weight_target": round(target_weights.get(order.asset_id, 0.0), 6),
            "est_fee": round(fee_by_order.get(order.order_id, 0.0), 2),
            "note": note,
        }

    def _render_ticket_text(self, plan_date: date, rows: list[dict[str, Any]], total_value: float, cash: float) -> str:
        lines = [
            f"【调仓单】基于 {date_str(plan_date)} 收盘估算，建议下一交易日执行",
            f"组合: {self.portfolio_id} | 估算总值 ≈ {total_value:,.0f} 元 | 现金 {cash:,.0f} 元",
        ]
        if not rows:
            lines.append("目标权重与当前持仓的偏离都在阈值带内，今日无需交易。")
            return "\n".join(lines)
        side_label = {"BUY": "买入", "SELL": "卖出"}
        for index, row in enumerate(rows, start=1):
            line = (
                f"{index}. {side_label.get(row['side'], row['side'])} {row['code']} {row['name']} "
                f"{row['quantity']:,.0f} 股 ≈ {row['est_value']:,.0f} 元"
                f"（{row['weight_before']:.1%} → {row['weight_target']:.1%}）"
            )
            if row["note"]:
                line += f" [注意: {row['note']}]"
            lines.append(line)
        total_fee = sum(row["est_fee"] for row in rows)
        lines.append(
            f"估算费用合计 ≈ {total_fee:,.2f} 元。股数为估算，按券商实际可成交数量就近取整即可；"
            "成交价与估算价的偏差会被阈值带吸收，无需在意。"
        )
        return "\n".join(lines)

    def _load_data(self, end: date) -> LocalCsvBarData:
        return LocalCsvBarData(
            data_dir=self.market_dir,
            assets=self.assets.values(),
            start_date=(self.config.get("backtest") or {}).get("start_date"),
            end_date=date_str(end),
        )

    def _read_holdings(self, holdings_csv: str | Path) -> list[tuple[str, float, float | None]]:
        path = Path(holdings_csv)
        if not path.exists():
            raise FileNotFoundError(f"持仓文件不存在: {path}")
        holdings: list[tuple[str, float, float | None]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or "code" not in reader.fieldnames or "quantity" not in reader.fieldnames:
                raise ValueError(f"持仓文件表头必须包含 code,quantity（可选 cost_basis）: {path}")
            for row in reader:
                code = str(row["code"]).strip()
                if not code:
                    continue
                quantity = float(str(row["quantity"]).strip())
                raw_cost = str(row.get("cost_basis") or "").strip()
                cost_basis = float(raw_cost) if raw_cost else None
                holdings.append((code, quantity, cost_basis))
        return holdings

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

    def _load_state(self) -> PortfolioState | None:
        if not self.state_path.exists():
            return None
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return PortfolioState.from_dict(payload)

    def _write_state(self, state: PortfolioState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)

    def _append_real_nav(self, asof: date, cash: float, positions_value: float, total_value: float) -> None:
        rows: list[dict[str, str]] = []
        if self.real_nav_path.exists():
            with self.real_nav_path.open("r", encoding="utf-8", newline="") as handle:
                rows = [row for row in csv.DictReader(handle) if row["date"] != date_str(asof)]
        rows.append(
            {
                "date": date_str(asof),
                "cash": f"{cash:.2f}",
                "positions_value": f"{positions_value:.2f}",
                "total_value": f"{total_value:.2f}",
            }
        )
        rows.sort(key=lambda row: row["date"])
        with self.real_nav_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "cash", "positions_value", "total_value"])
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_ticket_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TICKET_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
