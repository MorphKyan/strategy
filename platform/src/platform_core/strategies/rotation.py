"""行业 ETF 横截面动量轮动策略（R039 课题，卫星仓）。

**状态：research-only，未注册（R039 v1 验收 Failed，2026-07-12）。**
训练样本（2020-03-16 ~ 2025-06-30）上相对行业等权基线年化落后 10.5pp，
起始日敏感性 32 个起点仅 1 个为正（中位数年化 -8.2%），三滑点场景一致。
详见 platform/reports/r039_industry_rotation_report.md 与
research-dashboard/notes/R039_industry_momentum_rotation.md。
若按蓝图 D2（拥挤度否决）继续迭代，需在 strategy.py 尾部重新注册本类，
并重建候选配置（基线配置 baseline_r9_industry_equal_weight.yaml 仍在库）。

设计依据（详见 docs/r039_rotation_blueprint.md）：
- A 股个股月频动量失效甚至反转（Liu-Stambaugh-Yuan 2019），但行业层面动量
  在控制 lead-lag、一月效应、个股动量后依然显著（EMFT 2011 等），因此轮动
  颗粒度取行业 ETF、回望窗取短（1M+3M 混合），不用美式 12-1。
- A 股日频动量一周内反转（Gao-Jiang-Xiong-Xiong, NBER w31839），信号锚点
  跳过最近 skip_days 个交易日，避免在反转前夜追入。
- 负动量宁可持币：选不满 top_n 时缺额留现金（TargetPortfolio 权重和 < 1），
  这是动量崩溃防护的最简形式，不做更复杂的自适应机制（R028/R037 教训）。
- 排名缓冲带（迟滞）：现任只要仍在 top_n + rank_buffer 名内且动量为正即留任，
  与 R038 的 Swedroe 阈值带同源，用于压换手。

行为约定：
- 月频检查（月末最后一个交易日出信号，T+1 即次月首个交易日执行）。
- "现任成员"从 `context.state.positions` 读取，不自设影子状态——回测、
  纸面 sim 与实盘 live（reconcile 覆盖持仓后）三种环路下行为一致。
- 交易触发复用基类 `should_rebalance` 的 `rebalance_threshold` 阈值带：
  成员未变、权重漂移在带内时当月不交易。
- 动量用后复权价（get_price_frame 的 adj_close），分红拆分不污染信号。

参数（v1 全部先验冻结，依据见蓝图 §2.3）：
- universe: list[str]，行业 ETF 池（缺省用全部可交易资产）
- momentum_windows: list[int]，动量回望窗（交易日），默认 [21, 63]，等权混合
- skip_days: int，信号锚点跳过的最近交易日数，默认 5
- top_n: int，持有行业数，默认 3；每个入选资产固定权重 1/top_n
- rank_buffer: int，现任留任的排名容忍，默认 2（即排名 <= top_n+2 留任）
- abs_momentum_floor: float，绝对动量闸门，默认 0.0（混合动量 <= 该值不可持有）
- rebalance_threshold: float，基类阈值带（配置层给 0.05）
- cooldown_days: int，默认 0
"""

from __future__ import annotations

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import Strategy, StrategyContext


class IndustryMomentumRotationStrategy(Strategy):
    name = "industry_momentum_rotation"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency(context.params.get("rebalance_frequency", "monthly"))

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets]
        if not universe:
            return None

        scores = self._momentum_scores(context, universe)
        if scores is None:
            return None

        top_n = max(1, int(context.params.get("top_n", 3)))
        rank_buffer = max(0, int(context.params.get("rank_buffer", 2)))
        floor = float(context.params.get("abs_momentum_floor", 0.0))

        ranked = sorted(scores, key=lambda a: scores[a], reverse=True)
        rank_of = {asset_id: i + 1 for i, asset_id in enumerate(ranked)}

        incumbents = [
            asset_id
            for asset_id in ranked
            if context.state.position(asset_id).quantity > 1e-9
        ]
        # 现任留任：动量过闸门且排名在缓冲带内；异常持仓多于 top_n 时保排名最好的
        selected = [
            asset_id
            for asset_id in incumbents
            if scores[asset_id] > floor and rank_of[asset_id] <= top_n + rank_buffer
        ][:top_n]
        # 空位补入：按排名依次补最强的非现任
        for asset_id in ranked:
            if len(selected) >= top_n:
                break
            if asset_id in selected or scores[asset_id] <= floor:
                continue
            selected.append(asset_id)

        # 全体不合格 => 空目标（清仓持币），与"无信号返回 None"语义不同
        slot_weight = 1.0 / top_n
        return TargetPortfolio({asset_id: slot_weight for asset_id in selected})

    def _momentum_scores(self, context: StrategyContext, universe: list[str]) -> dict[str, float] | None:
        windows = [int(w) for w in context.params.get("momentum_windows", [21, 63])]
        skip = max(0, int(context.params.get("skip_days", 5)))
        if not windows or min(windows) <= 0:
            return None

        frame = context.data.get_price_frame(universe, context.date)
        if frame is None or frame.empty:
            return None
        need = skip + max(windows) + 1
        if len(frame) < need:
            return None

        anchor = frame.iloc[-1 - skip]
        scores: dict[str, float] = {}
        for asset_id in universe:
            total = 0.0
            for window in windows:
                base = frame[asset_id].iloc[-1 - skip - window]
                if base <= 0:
                    return None
                total += anchor[asset_id] / base - 1.0
            scores[asset_id] = total / len(windows)
        return scores
