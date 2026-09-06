# 文献研究总结：The Trend is Our Friend: Risk Parity, Momentum and Trend Following in Global Asset Allocation

- **作者**：Andrew Clare, James Seaton, Peter N. Smith, Stephen Thomas (Cass Business School, City University of London & University of York)
- **发表期刊**：*Journal of Behavioral and Experimental Finance* (Vol. 9, 2016, pp. 63–80)
- **PDF 本地存储**：`doc/Clare_2016_The_Trend_is_Our_Friend.pdf`

---

## 1. 核心研究背景与问题

传统资产配置（无论是 60/40 股债组合还是纯风险平价 Risk Parity）在面对单边宏观下行周期（如 2008 次贷危机、商品长期熊市或利率反转周期）时，由于缺乏右侧趋势保护，容易承受巨大的下行回撤与“顺序风险”（Sequence of Returns Risk）。

论文的核心问题是：**如何将“横截面风险平价（Risk Parity / 波动率倒数预算）”与“时间序列趋势跟踪（Time-Series Trend Following / 10-Month Moving Average）”完整结合？**

---

## 2. 论文的标准完整方案与数学模型

### 2.1 基础风险平价权重计算（Risk Parity Step）
在月末再平衡日 $t$，基于资产的历史波动率或协方差矩阵（论文基准使用 12 个月滚动窗口）计算各大类资产的无偏风险预算目标权重 $w_{i, t}^{\text{RP}}$：
$$w_{i, t}^{\text{RP}} = \frac{1/\sigma_{i, t}}{\sum_{j=1}^N 1/\sigma_{j, t}} \quad \text{或满足} \quad \text{RC}_i = b_i \text{（等风险贡献 / 预设固定风险预算）}$$

### 2.2 趋势跟踪过滤器（Trend Following Filter Step）
论文采用经典的 10 个月简单移动平均线（10-Month SMA，月频 10 个月，日频对应约 200 个交易日 SMA 或 120 个交易日 EMA/SMA）：
$$I_{i, t} = \begin{cases} 
1, & \text{若 } P_{i, t} \ge \text{SMA}_{10M}(P_{i, t}) \quad (\text{处于上升趋势，Risk-On}) \\
0, & \text{若 } P_{i, t} < \text{SMA}_{10M}(P_{i, t}) \quad (\text{处于下行趋势，Risk-Off})
\end{cases}$$

### 2.3 组合最终权重与无风险现金配置（Final Allocation & Cash Buffer）
组合在资产 $i$ 上的实际投资权重 $w_{i, t}^*$ 定义为：
$$w_{i, t}^* = w_{i, t}^{\text{RP}} \times I_{i, t}$$

- **未投资部分转入无风险资产（Risk-Off Asset）**：
$$w_{\text{Cash}, t} = 1 - \sum_{i=1}^N w_{i, t}^* = \sum_{i: I_{i, t}=0} w_{i, t}^{\text{RP}}$$
- **核心原则**：当某个资产跌破趋势线时，其对应的风险平价资金**直接转入现金/货币基金（如 3-Month T-Bills）**，而不是机械地再分配给其他风险资产（避免在系统性危机中产生风险传染）。

---

## 3. 核心实证结论

1. **大幅削减最大回撤（Drawdown Reduction）**：
   - 全球权益资产回撤从 50%+ 降至 15% 左右；
   - 风险平价组合的最大回撤从 20.95% 进一步大幅压降。
2. **夏普比率与卡玛比率全面提升**：
   - 趋势跟踪的“危机阿尔法”使组合在熊市避险而在牛市吃满收益，负偏度（Negative Skewness）被显著修正为轻微正偏度。
3. **完美解决利率与资产集中度风险**：
   - 当债券或大宗商品进入长期熊市（跌破均线）时，策略自动将仓位切入现金，彻底打破了单一资产由于波动率低而被动重仓死扛的死穴。
