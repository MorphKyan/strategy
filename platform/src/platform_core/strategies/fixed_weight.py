"""固定权重 + 阈值带再平衡策略（永久组合式，R038 课题）。

设计依据：
- 本仓库 R028（非对称滞回带）与 R037（波动率半衰期自适应阈值）两次尝试
  自适应触发机制均判 Failed——复杂度不换来稳健优势。本策略走反方向：
  **零自适应成分**，带宽为先验常数，规则来自实践文献的 Larry Swedroe
  "5/25 规则"：任一资产权重相对固定目标偏离超过 5 个绝对百分点，或超过
  目标权重的 25%（相对），才把整个组合再平衡回目标；否则什么都不做。
- 与 `monthly_equal_weight` 构成干净对照：同样的目标权重，唯一差异是
  "日历触发 vs 阈值触发"。阈值触发允许强势资产在带内顺势漂移（缓解
  日历调仓的"强趋势踏空"），同时把换手压到只在真正失衡时发生。

行为约定：
- 空仓（含首日）时建仓到目标权重；此判断基于持仓状态而非 runtime 标记，
  因此在回测、纸面 sim 与实盘 live plan 三种环路下行为一致。
- 每日只"检查"，不必然交易；触带即整体归位（不做部分修正——部分修正
  属于 R028 已失败的方向）。
- `target_weights` 缺省为 universe 等权；显式给出时会归一化。

参数：
- universe: list[str]，资产池（缺省用全部可交易资产）
- target_weights: dict[asset_id, weight]，可选，缺省等权
- abs_band: float，绝对偏离带宽，默认 0.05
- rel_band: float，相对偏离带宽（× 目标权重），默认 0.25
- cooldown_days: int，默认 0（永久组合不需要冷却）
"""

from __future__ import annotations

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import Strategy, StrategyContext


class FixedWeightThresholdStrategy(Strategy):
    name = "fixed_weight_threshold"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency("daily")  # 每日检测（不等于每日交易）

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
        for asset_id, target_w in target.weights.items():
            deviation = abs(current.get(asset_id, 0.0) - target_w)
            if deviation > abs_band or (target_w > 0 and deviation > rel_band * target_w):
                return True
        return False


    @staticmethod
    def _target_weights(context: StrategyContext) -> dict[str, float] | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets]
        if not universe:
            return None
        explicit = context.params.get("target_weights")
        if explicit:
            weights = {
                asset_id: float(explicit[asset_id])
                for asset_id in universe
                if asset_id in explicit and float(explicit[asset_id]) > 0
            }
            total = sum(weights.values())
            if total <= 0:
                return None
            return {asset_id: weight / total for asset_id, weight in weights.items()}
        equal = 1.0 / len(universe)
        return {asset_id: equal for asset_id in universe}
