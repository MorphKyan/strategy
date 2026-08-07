# 论文精读与学术指南：Thierry Roncalli 风险预算与 Expected Shortfall 资产配置理论

- **论文文件**: [`Roncalli_Risk_Parity_arXiv.pdf`](file:///d:/strategy/doc/Roncalli_Risk_Parity_arXiv.pdf)
- **作者**: Thierry Roncalli (Amundi Asset Management & University of Paris-Dauphine)
- **存储路径**: `d:/strategy/doc/`

---

## 1. 论文核心贡献与理论框架

本论文是风险平价（Risk Parity）与风险预算（Risk Budgeting）领域的奠基性学术著作之一。Thierry Roncalli 在论文中系统解决了**传统均值-方差优化（Markowitz Mean-Variance）估计噪点大**与**传统风险平价忽视预期收益/尾部风险**的双重难题。

### 核心结论：
1. **风险预算在尾部测度下的齐次分解（Euler Decomposition under Expected Shortfall）**：
   证明了 Expected Shortfall (ES) 风险测度满足 1 阶齐次性（Euler's Homogeneity Theorem），允许将组合总尾部风险精确分解到各个资产与宏观因子上。
2. ** Black-Litterman 混合风险预算（Black-Litterman Risk Budgeting Overlay）**：
   将投资者对资产/因子的预期收益信号 $\mu$ 或倾斜观点（Views）融入风险预算公式。证明了倾斜后的风险预算 $b_i^*$ 满足：
   $$b_i^* \propto b_i^{\text{base}} \times \exp\left( \gamma \cdot \frac{\mu_i}{\text{ES}_i} \right)$$
   实现了在保持风险平价强抗防守特性的同时，主动倾斜增效。

---

## 2. 核心数学算式推导

### 2.1 ES 风险预算下的欧拉分解
设组合资产权重为 $w \in \mathbb{R}^N$，组合预期尾部损失 Expected Shortfall 表示为 $\text{ES}_\alpha(w)$。
根据欧拉定理，组合总 ES 可展开为各资产边际风险贡献之和：
$$\text{ES}_\alpha(w) = \sum_{i=1}^N w_i \frac{\partial \text{ES}_\alpha(w)}{\partial w_i}$$

资产 $i$ 的风险预算贡献比例 $b_i$ 定义为：
$$b_i = \frac{w_i \cdot \frac{\partial \text{ES}_\alpha(w)}{\partial w_i}}{\text{ES}_\alpha(w)}, \quad \text{满足 } \sum_{i=1}^N b_i = 1$$

### 2.2 宏观因子风险预算 (Macro Factor Risk Budgeting)
设资产收益率 $r_t$ 映射至 $K$ 个宏观因子 $f_t$：
$$r_t = B f_t + \epsilon_t$$
组合在宏观因子上的暴露为 $w_f = B^T w$。
第 $k$ 个宏观因子的风险贡献 $b_k^{\text{Factor}}$ 满足：
$$b_k^{\text{Factor}} = \frac{(B^T w)_k \cdot \frac{\partial \text{ES}_\alpha(w)}{\partial (B^T w)_k}}{\text{ES}_\alpha(w)}$$

设定目标宏观因子风险预算 $b_k^{\text{Target}}$（如 Growth 33.3%, Duration 33.3%, Inflation 33.3%），通过以下凸优化目标求解权重 $w^*$：
$$\min_{w \ge 0, \mathbf{1}^T w = 1} \sum_{k=1}^K \left( \frac{(B^T w)_k \cdot \frac{\partial \text{ES}_\alpha(w)}{\partial (B^T w)_k}}{\text{ES}_\alpha(w)} - b_k^{\text{Target}} \right)^2$$

---

## 3. 对本仓库策略的落地指导意义

1. **解决 30Y 国债与商品配比过度集中问题**：
   论文证明了基于资产名称直接设定硬编码预算容易造成因子暴露倾斜。通过映射至 Growth / Duration / Inflation 三大宏观因子，能够彻底均衡全周期防守性能。
2. **结合收益观点提升夏普比率**：
   在不破坏 ES 防守机制的前提下，利用动量与下尾赔率信号对基础风险预算进行 $b_i^*$ 指数倾斜，在历史敏感性测试中能有效提升年化收益率。
