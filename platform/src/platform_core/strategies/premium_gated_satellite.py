"""核心/卫星固定权重 + 5/25 阈值带 + 溢价闸门（R056 课题）。

## 设计依据

R039（行业动量）与 R049（行业估值）在同一行业池上方向相反却双双跑输等权，
证伪了行业横截面择时；R050 虽 Passed 但按 `core + w·satellite` vs `core` 的边际口径
贡献为负（行业池与核心相关 0.763，是核心里 510300 的高波动翻版）。
卫星仓因此改用**与核心低相关**的跨市场标的（`513100` 与核心训练段相关 0.283）。

但 R056 审计发现 `513100` 的场内溢价是结构性的（QDII 额度稀缺，日频自相关 0.855，
月均标准差 2.99%）：以 10.42% 的溢价建仓，回到历史中位 0.44% 即一次性 -9.03%。
本策略的唯一新增成分就是把这件事变成**纪律**而非预测：

  溢价高于上限时不持有卫星，其权重回流核心；溢价回落后再持有。

## 为什么是闸门而不是打分

R022（QDII 折溢价轮动）用折溢价做**连续打分**并 Passed；本策略刻意退化为**二值闸门**，
理由与 R038 相同——本仓库四次自适应触发（R028/R037/R045/R048）全部 Failed，
而零自适应的固定阈值带 Passed。闸门不预测溢价何时回归，只回答"当前是否可入场"。

## 参数（全部为先验常数，首次运行前冻结，无搜参）

- `core_weights`: dict[asset_id, weight]，核心篮子及其**组内**相对权重
- `satellite`: str，卫星资产 asset_id
- `satellite_weight`: float，卫星目标权重，默认 0.30
- `premium_cap`: float，溢价上限，默认 **0.02**
  锚定申赎套利往返成本（QDII 申购费 + 汇兑 + T+2 到账的价格风险，量级约 1~2%）。
  溢价长期高于该水平意味着套利通道被额度限制堵死，不是市场定价——这是机制推断，
  不是从回测里挑出来的数。
- `publication_lag_days`: int，净值发布滞后，默认 **2**（QDII 普遍 T+1~T+2，取上界）
- `gate_eval`: {"month_end", "daily"}，闸门重估频率，默认 **month_end**
  溢价是慢变量（日频自相关 0.855），与之匹配的评估频率才不会制造 whipsaw；
  权重漂移仍由 5/25 带每日检查。**慢信号慢评估、快漂移快纠正。**
- `abs_band` / `rel_band`: 逐字沿用 R038 的 0.05 / 0.25
- `cooldown_days`: 默认 0

## 行为约定

- 闸门关闭时卫星目标权重为 0，其权重按核心**组内**相对权重回流核心（核心内部比例不变）。
- 闸门状态在 `月末` 重估并记忆；非重估日沿用上次状态，避免日内翻转。
- 卫星无净值数据 / 历史不足以扣除滞后时，**闸门默认关闭**（没有信号就不下注）。
- 空仓建仓、触带整体归位等行为与 R038 一致，回测 / 纸面 sim / 实盘 live plan 三环路同构。
"""

from __future__ import annotations

from src.platform_core.etf_premium import DEFAULT_PUBLICATION_LAG_DAYS, get_store
from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import Strategy, StrategyContext

_GATE_STATE_KEY = "r056_premium_gate_open"
_GATE_DIAG_KEY = "r056_premium_gate_diagnostics"


class PremiumGatedSatelliteStrategy(Strategy):
    name = "premium_gated_satellite"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency("daily")  # 每日检测（不等于每日交易）

    # ------------------------------------------------------------------ 闸门

    def _evaluate_gate(self, context: StrategyContext) -> bool:
        """返回闸门是否开启（True = 可持有卫星）。无数据/历史不足一律关闭。"""
        satellite = context.params.get("satellite")
        if not satellite:
            return False
        cap = float(context.params.get("premium_cap", 0.02))
        lag = int(context.params.get("publication_lag_days", DEFAULT_PUBLICATION_LAG_DAYS))
        try:
            store = get_store(context.data.data_dir)
            result = store.premium_at(satellite, context.date, publication_lag_days=lag)
        except FileNotFoundError:
            return False
        if result is None:
            return False
        context.runtime[_GATE_DIAG_KEY] = {
            "date": str(context.date),
            "observed_date": str(result.observed_date),
            "premium": result.premium,
            "cap": cap,
        }
        return result.premium <= cap

    def _gate_open(self, context: StrategyContext) -> bool:
        """闸门状态：按 gate_eval 频率重估，其余日期沿用记忆值。"""
        mode = str(context.params.get("gate_eval", "month_end")).lower()
        remembered = context.runtime.get(_GATE_STATE_KEY)
        if mode == "daily" or remembered is None or context.is_month_end():
            state = self._evaluate_gate(context)
            context.runtime[_GATE_STATE_KEY] = state
            return state
        return bool(remembered)

    # ------------------------------------------------------------------ 目标

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        targets = self._target_weights(context)
        if not targets:
            return None
        return TargetPortfolio(targets)

    def should_rebalance(self, context: StrategyContext, target: TargetPortfolio) -> bool:
        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        has_position = any(
            position.quantity > 1e-9 for position in context.state.positions.values()
        )
        if not has_position:
            return True

        current = context.state.weights(prices)
        abs_band = float(context.params.get("abs_band", 0.05))
        rel_band = float(context.params.get("rel_band", 0.25))
        # 目标里已消失的资产（闸门刚关掉的卫星）也要参与判定，否则关闸不触发交易
        for asset_id in set(target.weights) | set(current):
            target_w = target.weights.get(asset_id, 0.0)
            deviation = abs(current.get(asset_id, 0.0) - target_w)
            if deviation > abs_band or (target_w > 0 and deviation > rel_band * target_w):
                return True
        return False

    def _target_weights(self, context: StrategyContext) -> dict[str, float] | None:
        core_weights = context.params.get("core_weights") or {}
        core = {
            asset_id: float(weight)
            for asset_id, weight in core_weights.items()
            if asset_id in context.assets and float(weight) > 0
        }
        core_total = sum(core.values())
        if core_total <= 0:
            return None

        satellite = context.params.get("satellite")
        sat_weight = float(context.params.get("satellite_weight", 0.30))
        tradable = satellite in context.assets and satellite in context.bars
        if not tradable or sat_weight <= 0 or not self._gate_open(context):
            sat_weight = 0.0

        # 核心吸收全部剩余权重，组内相对比例保持不变
        remaining = 1.0 - sat_weight
        targets = {asset_id: remaining * weight / core_total for asset_id, weight in core.items()}
        if sat_weight > 0:
            targets[satellite] = sat_weight
        return targets
