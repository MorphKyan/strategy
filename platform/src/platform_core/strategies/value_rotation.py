"""行业 ETF 估值分位轮动策略（R049 课题，卫星仓，左侧价值）。

**状态：research-only，未注册（R049 验收 Failed，2026-07-25）。**
训练样本（2020-03-16 ~ 2025-06-30）年化超额 +2.60pp、回撤优 6.36pp、三滑点一致，
但**冻结样本（2025-07-01 起）累计 -8.80% vs 基线 +20.49%，跑输 29.29pp**，Sharpe -0.54。
败因是价值陷阱 + 成长行情：涨幅前三的 5G通信(+160.7%)、半导体(+113.2%)、科技(+95.4%)
因 PB 分位偏高被系统性回避，实际持有的消费(-17.4%)、白酒(-24.6%)持续变得更便宜。
详见 platform/reports/r049_value_rotation_report.md 与
research-dashboard/notes/R049_industry_value_rotation.md。
复研时需在 strategy.py 尾部重新注册本类并重建候选配置。

R039（动量轮动）当日验收 Failed——败因是鞭打与 V 型反转，本质是"追高"在 A 股行业
层面不成立。本策略是同一研究线的第二次尝试，**信号方向相反**：不追涨，而是买
**相对自身历史便宜**的行业（均值回归 / 左侧价值）。

设计依据（详见 docs/r049_value_rotation_blueprint.md）：
- **时序分位而非横截面比大小**：行业间 PB 绝对水平天然不可比（银行 0.6 与半导体 5.0
  是行业属性不是贵贱），只有"与自己历史比"才有意义。分位同时对数据源口径的常数倍
  缩放免疫，降低将来换数据源的风险。
- **用 PB 不用 PE**：实测 PE_TTM 在钢铁缺失 23.8%、地产 19.9%（Wind 规则：行业整体
  亏损时 PE 为负置空），而周期股恰恰在亏损期最便宜——用 PE 会在最该出手时失明。
  PB_LF 与股息率零缺失。
- **历史不足者排除而非降级**：科技/通信等指数 2019 年才发布，回测起点前只有约 1 年
  历史，分位是噪声；没有信号就不下注，比用"发布以来分位"充数诚实。
- **排名缓冲带**：与 R038 Swedroe 阈值带同源的迟滞，压换手。
- **v1 零自适应机制**：不做绝对估值闸门（那是择时）、不做 PE/PB 加权（多一组权重就
  多一层过拟合面）、不叠质量因子（防价值陷阱是真需求，但必须独立验收）。
  R028/R037 自适应两连败 vs R038 先验常数一次通过的教训直接适用。

行为约定：
- 月频检查（月末最后一个交易日出信号，T+1 即次月首个交易日执行）。
- "现任成员"从 `context.state.positions` 读取，不自设影子状态——回测、纸面 sim 与
  实盘 live（reconcile 覆盖持仓后）三种环路下行为一致。
- 交易触发复用基类 `should_rebalance` 的 `rebalance_threshold` 阈值带。
- 前视防护在 `index_valuation.IndexValuationStore` 内硬性保证（只用 <= 信号日的观测）。

参数（v1 全部先验冻结，依据见蓝图 §2.4）：
- universe: list[str]，行业 ETF 池（缺省用全部可交易资产）
- valuation_metric: str，估值指标，默认 "pb_lf"
- percentile_window: int，分位回望窗（交易日），默认 1250（约 5 年）
- min_history: int，参与选择所需的最少观测数，默认 750（约 3 年）
- top_n: int，持有行业数，默认 5；每个入选资产固定权重 1/top_n
- rank_buffer: int，现任留任的排名容忍，默认 2（排名 <= top_n+2 留任）
- rebalance_threshold: float，基类阈值带（配置层给 0.05）
- cooldown_days: int，默认 0
"""

from __future__ import annotations

from src.platform_core.index_valuation import get_store
from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import Strategy, StrategyContext


class IndustryValueRotationStrategy(Strategy):
    name = "industry_value_rotation"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency(context.params.get("rebalance_frequency", "monthly"))

    def should_check_rebalance(self, context: StrategyContext) -> bool:
        """入场约定与基线 monthly_equal_weight 一致：首日即建仓，此后月末检查。

        不这样做的话候选会空仓等到首个月末（最多约 22 个交易日）才进场，而基线在
        起点当天就满仓——起始日敏感性里这会变成纯粹的入场时点运气，掩盖策略本身。
        实测：2024-09-18 起点上，基线首日进场吃到政策行情（+32.6%），候选空仓等到
        09-30 才在高位买入（-17.0%），单这一项就造成 -49.6pp 的伪劣势。
        """
        if not context.params.get("rebalance_on_start", True) and context.state.last_date is None:
            return False
        if context.state.last_date is not None and not self._is_rebalance_day(context):
            return False
        return True

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets]
        if not universe:
            return None

        store = get_store(context.data.data_dir)
        results = store.percentiles_at(
            universe,
            context.date,
            metric=str(context.params.get("valuation_metric", "pb_lf")),
            window=int(context.params.get("percentile_window", 1250)),
            min_observations=int(context.params.get("min_history", 750)),
        )
        if not results:
            return None

        top_n = max(1, int(context.params.get("top_n", 5)))
        rank_buffer = max(0, int(context.params.get("rank_buffer", 2)))

        # 升序：分位越低越便宜越优先
        ranked = sorted(results, key=lambda asset_id: results[asset_id].percentile)
        rank_of = {asset_id: index + 1 for index, asset_id in enumerate(ranked)}

        incumbents = [
            asset_id for asset_id in ranked if context.state.position(asset_id).quantity > 1e-9
        ]
        # 现任留任：排名仍在缓冲带内即留任（异常持仓多于 top_n 时保排名最靠前的）
        selected = [
            asset_id for asset_id in incumbents if rank_of[asset_id] <= top_n + rank_buffer
        ][:top_n]
        # 空位补入：按分位从低到高补最便宜的非现任
        for asset_id in ranked:
            if len(selected) >= top_n:
                break
            if asset_id not in selected:
                selected.append(asset_id)

        if not selected:
            return None
        # 合格集不足 top_n 时缺额留现金（权重和 < 1，引擎自然持币）
        slot_weight = 1.0 / top_n
        return TargetPortfolio({asset_id: slot_weight for asset_id in selected})
