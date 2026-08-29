# AQR 经典文献研究总结：Risk Parity 与 Trend Following（趋势跟踪）体系

- **核心文献 1**：Asness, C., Frazzini, A., Pedersen, L. (2012), *"Leverage Aversion and Risk Parity"*, *Financial Analysts Journal* / AQR Capital Management (PDF: `doc/AQR_2012_Leverage_Aversion_and_Risk_Parity.pdf`)
- **核心文献 2**：Hurst, B., Ooi, Y. H., Pedersen, L. (2017), *"A Century of Evidence on Trend-Following Investing"*, *Journal of Portfolio Management* / AQR (PDF: `doc/AQR_Demystifying_Managed_Futures.pdf`, `doc/AQR_Time_Series_Momentum.pdf`)
- **核心文献 3**：Asness, C., Moskowitz, T., Pedersen, L. (2013), *"Value and Momentum Everywhere"*, *Journal of Finance* (PDF: `doc/AQR_Value_and_Momentum_Everywhere.pdf`)

---

## 1. AQR 的核心理论演进脉络

### 1.1 为什么 Risk Parity 天然重仓债券（以及由此引发的久期集中风险）？
在 *Leverage Aversion and Risk Parity (2012)* 中，Asness、Frazzini 和 Pedersen 指出：
- 由于大部分投资者（尤其是个人投资者与多数机构）存在“杠杆厌恶（Leverage Aversion）”或无法使用显式杠杆，导致高风险资产（如股票）被过度追捧而预期夏普较低，低风险资产（如债券）被低估而拥有更高的无杠杆夏普比率。
- 风险平价通过超配低波动债券，构建出高夏普的资产配置基底。
- **但这也导致无杠杆组合中的资金权重极度倾斜向长期债券（如 60%~70%）**。

### 1.2 为什么必须引入 Trend Following（时间序列趋势跟踪）？
在 *A Century of Evidence on Trend-Following Investing (2017)* 与 *Time Series Momentum (2012)* 中，Pedersen 团队通过穿越 1880 年至 2016 年逾 137 年的百年跨周期实证证明：
1. **危机阿尔法（Crisis Alpha）与凸性保护**：
   - Trend Following 表现出显著的正偏度（Positive Skewness），其收益特征类似于“跨品种的跨式期权（Long Straddle）”。
   - 在股票或债券遭遇大级别单边熊市（如 2008 次贷危机、历史级大债灾、通胀上行周期）时，趋势跟踪能够迅速通过右侧破位（如 10-Month / 200 SMA 均线或 12-Month Momentum）识别单边下行，并**主动斩断亏损、切入现金或反向做空**。
2. **与 Risk Parity 的完美共生互补**：
   - 风险平价提供常态下的“横截面低波动贝塔收割”；
   - 趋势跟踪提供极端下行期的“时间序列下行防护与止损截断”。

---

## 2. 结合实现方案（AQR 框架与 Clare 2016 体系的关系）

- AQR（Cliff Asness 团队）确立了 **Risk Parity（横截面风险平价） + Time-Series Trend Following（时间序列趋势跟踪）** 相互补充的底层宏观与行为金融学理论；
- Clare, Seaton, Smith, Thomas (2016, *Journal of Behavioral and Experimental Finance*) 则是国际上首篇在同行评议顶级期刊中，将 AQR 的 10-Month Trend 过滤器与 Risk Parity 权重进行数学显式融合，并对“破位转入现金（Cash Switching）”进行标准化实证的权威论文。
