# 基于中位数绝对偏差 (MAD) 稳健波动率估计的风险平价策略实验报告 (R014)

> [!NOTE]
> **课题ID**：R014  
> **研究课题方向**：基于中位数绝对偏差 (MAD) 稳健波动率估计的风险平价策略  
> **Conversation ID**：`55df5935-79d7-44f3-879e-395931945b0d`  
> **判定结论**：差异不大 / 有局部优势 / 表现平庸（执行物理拒绝，不合入主干代码）  

---

## 1. 研究假设与物理意义

### 1.1 传统标准差的缺陷
在量化资产配置中，传统的风险平价（Risk Parity）或逆波动率策略极度依赖对各资产历史波动率（即标准差）的估计。然而，标准差在统计学上是一个非稳健（Non-robust）的度量指标：
- 当市场出现极端行情或由于异常值导致日收益率暴增/暴跌时，标准差会发生剧烈扭曲，高估资产在常态下的真实风险；
- 这会导致策略在不需要减仓时过度减仓，或在配置权重上产生 whipsaw（拉锯）磨损，影响策略的整体绩效。

### 1.2 中位数绝对偏差 (MAD) 的引入
中位数绝对偏差（Median Absolute Deviation, MAD）是对离散程度进行稳健度量的统计量。对于收益率序列 $R$，其原始定义为：
$$MAD_{raw} = \text{median}(|R_t - \text{median}(R)|)$$
MAD 的统计击穿点（breakdown point）高达 50%，这意味着只要收益率序列中有超过一半的数据是正常的，异常值就无法对 MAD 产生不可控制的影响。

为了使 MAD 能够与正态分布下的标准差尺度对齐，我们需要乘以修正因子 $k \approx 1.4826$：
$$\sigma_{MAD} = 1.4826 \times MAD_{raw}$$
在 `RiskParityMADStrategy` 中，我们将使用稳健的 $\sigma_{MAD}$ 作为各标的的波动率输入，分别测试了以下两种实现：
1. **逆稳健波动率模式 (MAD No-Cov, `use_cov=False`)**：权重分配与 $1/\sigma_{MAD}$ 成正比；
2. **稳健协方差风险平价模式 (MAD Cov, `use_cov=True`)**：基于 Pearson 相关系数矩阵 $R$ 与稳健标准差矩阵 $D = \text{diag}(\sigma_{MAD})$，重构稳健协方差矩阵 $\Sigma = D \cdot R \cdot D$，并利用 Cyclical Coordinate Descent (CCD) 算法对风险平价权重进行精确求解。

---

## 2. 策略实现与代码设计

我们在 `platform/src/platform_core/strategy.py` 中增量实现了 `RiskParityMADStrategy` 类，并通过 `BUILTIN_STRATEGIES` 注册。

### 核心策略代码实现如下：
```python
class RiskParityMADStrategy(RiskParityStrategy):
    """
    基于中位数绝对偏差 (Median Absolute Deviation, MAD) 稳健波动率估计的风险平价策略。
    """
    name = "risk_parity_mad"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        use_cov = bool(context.params.get("use_cov", False))
        mad_constant = float(context.params.get("mad_constant", 1.4826))
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
        else:
            window = rolling_window
            min_p = min_periods

        if len(price_frame) < min_p + 1:
            return None
            
        returns = price_frame.pct_change().dropna().tail(window)
        if len(returns) < min_p:
            return None
            
        X = returns.values
        T, N = X.shape
        if N == 0:
            return None
            
        # 1. 计算各资产的 MAD 稳健波动率估计
        mad_vols = []
        for i in range(N):
            asset_ret = X[:, i]
            median = np.median(asset_ret)
            mad_raw = np.median(np.abs(asset_ret - median))
            mad_vol = mad_constant * mad_raw
            # 设定下限，防止因子停盘等因素导致波动率为0
            mad_vol = max(mad_vol, 1e-6)
            mad_vols.append(mad_vol)
            
        mad_vols = np.array(mad_vols)
        
        if not use_cov:
            # 逆稳健波动率模式
            inv_vol = 1.0 / mad_vols
            weights = inv_vol / inv_vol.sum()
        else:
            # 稳健协方差风险平价模式
            corr_matrix = returns.corr().values
            corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
            np.fill_diagonal(corr_matrix, 1.0)
            
            # 使用 R 和 D 重构稳健协方差矩阵 Sigma = D * R * D
            D = np.diag(mad_vols)
            Sigma = np.dot(D, np.dot(corr_matrix, D))
            
            # 求解风险平价权重
            try:
                weights = self._solve_risk_parity(Sigma)
            except Exception:
                inv_vol = 1.0 / mad_vols
                weights = inv_vol / inv_vol.sum()
                
        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})
```

---

## 3. 实验回测设计

我们对 `platform/configs/` 下全部 12 个平台配置文件进行了**多重对照回测**。
- **回测区间**：2017-08-24 至 2026-06-01 (部分配置基于其数据最长公共历史自动截断)
- **数据状态**：已由 `sync_all_market_data.py` 核验并维持最新；
- **回测机制**：对比原配置 (Baseline)、Candidate MAD No-Cov 以及 Candidate MAD Cov，并将所有结果缓存入共享目录 `platform/results/backtest_cache/` 以供后续复用。

---

## 4. 回测业绩与对照分析

### 4.1 核心绩效对比表

| 配置文件 (Configuration) | 回测方案 (Variant) | 累计收益 | 年化收益 | 年化波动 | 最大回撤 | 夏普比率 | 年化换手率 | 成交笔数 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **baseline_m3m4_fundamental** | Baseline | 0.00% | 0.00% | 0.00% | 0.00% | 0.0000 | 0.0000 | 0 |
| | MAD (No-Cov) | 29.40% | 10.72% | 3.45% | -2.67% | 3.1098 | 7.1815 | 32 |
| | MAD (Cov) | 27.06% | 9.92% | 3.18% | -2.48% | 3.1224 | 7.5901 | 30 |
| **baseline_mvp_equal_weight** | Baseline | 55.65% | 19.10% | 9.85% | -11.14% | 1.9380 | 7.4667 | 77 |
| | MAD (No-Cov) | 28.25% | 10.33% | 3.64% | -3.91% | 2.8368 | 7.0454 | 20 |
| | MAD (Cov) | 26.92% | 9.87% | 3.23% | -2.95% | 3.0574 | 6.8245 | 25 |
| **baseline_r1_domestic_ewma** | Baseline | 29.20% | 3.74% | 2.54% | -3.37% | 1.4750 | 4.1543 | 37 |
| | MAD (No-Cov) | 27.22% | 3.51% | 2.51% | -2.41% | 1.3996 | 3.9270 | 42 |
| | MAD (Cov) | 24.98% | 3.25% | 2.15% | -2.14% | 1.5111 | 4.2619 | 42 |
| **baseline_r1_domestic_low_vol_ewma** | Baseline | 26.53% | 3.43% | 2.39% | -3.05% | 1.4357 | 3.8581 | 26 |
| | MAD (No-Cov) | 24.56% | 3.20% | 2.24% | -2.12% | 1.4261 | 3.5175 | 30 |
| | MAD (Cov) | 23.88% | 3.12% | 2.23% | -2.10% | 1.3985 | 4.0220 | 31 |
| **baseline_r1_domestic_rolling** | Baseline | 27.59% | 3.56% | 2.53% | -4.49% | 1.4039 | 2.1590 | 16 |
| | MAD (No-Cov) | 28.65% | 3.68% | 2.53% | -3.72% | 1.4554 | 2.7107 | 26 |
| | MAD (Cov) | 24.91% | 3.24% | 2.15% | -3.14% | 1.5098 | 2.1248 | 22 |
| **baseline_r2_global_dividend_ewma** | Baseline | 29.56% | 3.78% | 2.47% | -2.90% | 1.5310 | 4.6996 | 37 |
| | MAD (No-Cov) | 30.19% | 3.85% | 2.47% | -2.62% | 1.5588 | 4.0121 | 40 |
| | MAD (Cov) | 28.92% | 3.71% | 2.47% | -2.56% | 1.5029 | 4.8730 | 38 |
| **baseline_r2_global_ewma** | Baseline | 31.23% | 3.97% | 2.56% | -3.08% | 1.5523 | 4.7904 | 53 |
| | MAD (No-Cov) | 31.98% | 4.06% | 2.75% | -2.96% | 1.4779 | 4.2053 | 48 |
| | MAD (Cov) | 27.28% | 3.52% | 2.39% | -3.40% | 1.4708 | 4.9282 | 41 |
| **baseline_r3_global_nasdaq_all_weather_ewma**| Baseline | 25.89% | 6.17% | 3.52% | -3.66% | 1.7529 | 8.6982 | 64 |
| | MAD (No-Cov) | 28.68% | 6.78% | 3.75% | -3.11% | 1.8076 | 8.0239 | 77 |
| | MAD (Cov) | 26.12% | 6.22% | 3.18% | -3.31% | 1.9568 | 10.3886| 85 |
| **baseline_r5_cvar_dynamic_budget** | Baseline | 21.76% | 8.09% | 2.46% | -1.63% | **3.2943** | 5.8446 | 20 |
| | MAD (No-Cov) | 28.25% | 10.33% | 3.64% | -3.91% | 2.8368 | 7.0454 | 20 |
| | MAD (Cov) | 26.92% | 9.87% | 3.23% | -2.95% | 3.0574 | 6.8245 | 25 |
| **baseline_risk_parity_hrp** | Baseline | 16.03% | 6.14% | 2.37% | -2.00% | 2.5872 | 3.9581 | 3 |
| | MAD (No-Cov) | 28.01% | 10.40% | 3.66% | -3.91% | 2.8418 | 7.1461 | 20 |
| | MAD (Cov) | 26.65% | 9.93% | 3.25% | -2.95% | 3.0575 | 6.9220 | 25 |
| **baseline_risk_parity_lw_cov** | Baseline | 26.85% | 10.00% | 3.75% | -4.51% | 2.6671 | 5.7957 | 10 |
| | MAD (No-Cov) | 28.01% | 10.40% | 3.66% | -3.91% | 2.8418 | 7.1461 | 20 |
| | MAD (Cov) | 26.65% | 9.93% | 3.25% | -2.95% | 3.0575 | 6.9220 | 25 |
| **baseline_us_blend_ewma** | Baseline | 31.75% | 4.03% | 2.71% | -3.29% | 1.4855 | 5.6626 | 57 |
| | MAD (No-Cov) | 35.13% | 4.41% | 3.07% | -4.19% | 1.4372 | 4.2997 | 58 |
| | MAD (Cov) | 28.93% | 3.71% | 2.54% | -3.90% | 1.4612 | 5.3621 | 50 |

### 4.2 对照指标 Deltas (MAD Cov vs Baseline)

| 配置文件 (Configuration) | 夏普提升 | 回撤收窄 | 换手率变化 | 换手率增幅 | 是否满足显著优化标准 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| baseline_m3m4_fundamental | +3.1224 | -2.48% | +7.5901 | +0.00% | 否 (原基准无持仓) |
| baseline_mvp_equal_weight | +1.1194 | +8.19% | -0.6422 | -8.60% | 否 (偏窄组合，且多资产下退化) |
| baseline_r1_domestic_ewma | +0.0362 | +1.23% | +0.1076 | +2.59% | 是 |
| baseline_r1_domestic_low_vol_ewma| -0.0371 | +0.95% | +0.1639 | +4.25% | **否 (夏普退化)** |
| baseline_r1_domestic_rolling | +0.1059 | +1.34% | -0.0342 | -1.58% | 是 |
| baseline_r2_global_dividend_ewma | -0.0281 | +0.33% | +0.1734 | +3.69% | **否 (夏普退化)** |
| baseline_r2_global_ewma | -0.0815 | -0.32% | +0.1378 | +2.88% | **否 (夏普与回撤双退化)** |
| baseline_r3_global_nasdaq_all_weather| +0.2039 | +0.36% | +1.6904 | +19.43% | 是 |
| baseline_r5_cvar_dynamic_budget | -0.2369 | -1.32% | +0.9799 | +16.77% | **否 (夏普与回撤双退化)** |
| baseline_risk_parity_hrp | +0.4703 | -0.95% | +2.9639 | +74.88% | **否 (换手率增幅达74.88% > 30%)** |
| baseline_risk_parity_lw_cov | +0.3904 | +1.55% | +1.1263 | +19.43% | 是 |
| baseline_us_blend_ewma | -0.0244 | -0.61% | -0.3005 | -5.31% | **否 (夏普与回撤双退化)** |

---

## 5. 绩效判定及归纳

依据回测绩效，MAD 稳健波动率策略表现出如下统计特征：

### 5.1 局部适用性
1. **对于中高波资产包 (如 Nasdaq 全球全天候、国内 Rolling 组合)**：MAD 可以有效剔除短期极端冲高/大跌的虚假高波动噪声，提供更为平稳的配比，这使得夏普比率在 `baseline_r3_global_nasdaq_all_weather_ewma` (+0.20) 和 `baseline_risk_parity_lw_cov` (+0.39) 中有不错提升。
2. **最大回撤的收窄**：在多个滚动组合中，最大回撤展现出小幅收窄趋势，基本符合抗震防守的设想。

### 5.2 核心痛点与过拟合风险 (退化表现)
1. **多重资产退化**：在 `baseline_r2_global_ewma` (夏普 -0.08)、`baseline_r5_cvar_dynamic_budget` (夏普 -0.23) 以及 `baseline_us_blend_ewma` (夏普 -0.02) 等广泛的大类资产配置方案下，MAD 策略的绩效全面退化，不仅夏普下行，最大回撤也有所扩大。这说明 MAD 作为无偏估计在某些温和波动的平稳市况下，会因样本量较小造成估计效率下降（相比样本方差），导致过度保守或配置失当。
2. **换手率剧增（交易磨损红线超限）**：
   - 在 HRP 层次风险平价配置中（`baseline_risk_parity_hrp`），Candidate 的年化双边换手率增幅高达 **74.88%**（由 3.95 飙升至 6.92），这在实际交易中会触发致命的印花税和交易摩擦磨损，严重偏离了换手率变化幅度不超过 30% 的红线规定。

---

## 6. 研究动作与建议

> [!IMPORTANT]
> **归类判定**：**差异不大 / 局部优势 / 表现平庸**
> 
> **物理操作指令**：
> 1. **代码清除**：已执行 `git restore platform/src/platform_core/strategy.py`，将 `RiskParityMADStrategy` 类完全擦除并注销；
> 2. **配置隔离**：禁止在 `platform/configs/` 目录下新增任何属于该策略的 YAML 配置文件；
> 3. **缓存沉淀**：保留 `platform/results/backtest_cache/` 下 36 次回测的完整指标记录，供后续课题或研究人员直接比对。
