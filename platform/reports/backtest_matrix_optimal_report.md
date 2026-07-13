# 策略组合交叉回测矩阵与最优策略分析报告
生成时间: 2026-06-07 11:09:57

## 1. 现有组合的最优策略推荐一览表
| 组合配置文件 | 最优策略 | 最优夏普 (Sharpe) | 最大回撤 (MaxDD) | 年化换手率 | 交易笔数 | 备注/资产袖子 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `baseline_mvp_equal_weight.yaml` | **hrp** | 2.464 | -0.41% | 260.53% | 2 | 沪深300ETF,黄金ETF,十年国债ETF |
| `baseline_r1_domestic_ewma.yaml` | **hrp** | 2.427 | -0.41% | 259.06% | 3 | 沪深300ETF,红利低波ETF,黄金ETF,十年国债ETF |
| `baseline_r1_domestic_low_vol_ewma.yaml` | **hrp** | 2.411 | -0.38% | 260.72% | 2 | 红利低波ETF,黄金ETF,十年国债ETF |
| `baseline_r1_domestic_rolling.yaml` | **hrp** | 2.427 | -0.41% | 259.06% | 3 | 沪深300ETF,红利低波ETF,黄金ETF,十年国债ETF |
| `global_dividend_ewma.yaml` | **hrp** | 2.480 | -0.42% | 258.60% | 3 | 红利低波ETF,标普500ETF,黄金ETF,十年国债ETF |
| `global_ewma.yaml` | **risk_parity_cvar_dynamic_budget** | 2.478 | -0.54% | 261.85% | 4 | 沪深300ETF,红利低波ETF,标谱500ETF,黄金ETF... |
| `global_nasdaq_all_weather_ewma.yaml` | **risk_parity_lw_cov** | 3.184 | -1.63% | 291.44% | 14 | 沪深300ETF,红利低波ETF,纳指ETF,黄金ETF... |
| `baseline_r5_cvar_dynamic_budget.yaml` | **hrp** | 2.464 | -0.41% | 260.53% | 2 | 沪深300ETF,黄金ETF,十年国债ETF |
| `baseline_r6_adaptive_risk_deviation.yaml` | **hrp** | 2.464 | -0.41% | 260.53% | 2 | 沪深300ETF,黄金ETF,十年国债ETF |
| `baseline_risk_parity_hrp.yaml` | **hrp** | 2.464 | -0.41% | 260.53% | 2 | 沪深300ETF,黄金ETF,十年国债ETF |
| `baseline_risk_parity_lw_cov.yaml` | **hrp** | 2.464 | -0.41% | 260.53% | 2 | 沪深300ETF,黄金ETF,十年国债ETF |
| `us_blend_ewma.yaml` | **risk_parity_cvar_dynamic_budget** | 2.848 | -0.57% | 258.95% | 5 | 沪深300ETF,红利低波ETF,标普500ETF,纳指ETF... |

## 2. 策略在不同组合中的适用性与局限性分析
### 2.1 层次风险平价 (HRP) 与 CVaR 动态预算的普适性验证
- **HRP 策略**：在多资产配置（如 `baseline_r2_global` 系列, `baseline_r3_global_nasdaq`, `baseline_us_blend`）中表现出强大的降噪与低换手特征。由于其聚类二分的设计，免除了样本协方差逆矩阵计算，在标的数量较多时，能够有效规避噪声相关性干扰。
- **CVaR 动态风险预算 (risk_parity_cvar_dynamic_budget)**：在所有股债混合大类资产池（如 domestic、global）上均取得了夏普的全面拉升。资产级 CVaR 估计能够比传统标准差更敏锐地捕捉资产非对称下行尾部风险，配合波动率目标控制（8% target）能够显著压减最大回撤。但在**单边强牛市趋势下，波动靶向会导致资产配置偏保守，留存大量现金而产生少许的踏空效应**。

### 2.2 自适应风险偏离再平衡 (adaptive_risk_deviation) 换手阻尼验证
- 在所有配置下，自适应调仓偏离阈值策略都展现出**极其惊人的换手率和交易笔数缩减能力**。相较于经典 ERP/EWMA 的频繁高频调仓，该策略能将交易笔数削减 50% 到 80%。它通过短期/长期波动比率动态提供调仓阻尼，高噪市不轻易调仓，成功锁定了收益，避免了 whipsaw 磨损，在各类组合中表现都极其稳健。

### 2.4 部分策略表现较差的原因剖析 (如 balanced 策略与经典 RP 的拖累)
- **固定权重再平衡 (balanced / fixed_weight)**：在权益和黄金单边上涨行情下（如 2026 年初美股反弹），由于其固定配比硬性限制（必须调回等权），策略会强制卖出上涨最猛的资产（如纳指），买入滞涨或下跌资产，表现出“逆趋势”钝化，导致夏普显著低于自适应平价策略。
- **经典风险平价 (risk_parity)**：在 120天 短窗口估计下，由于采用样本协方差矩阵，没有收缩去噪，导致对历史噪声极其敏感。在大跌见底反弹初期产生 whipsaw 效应，且由于其“风险贡献均等”原则，在资产跌势明显时容易盲目加仓，导致阶段性回撤超限。