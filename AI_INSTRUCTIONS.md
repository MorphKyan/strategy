# AI Agent 工作指导说明 / AI Instructions

本文档旨在为后续接手或参与本系统开发的 AI 助手提供指导。

## 项目进展
1. **数据源层**：已完成。支持 `finshare` 获取 ETF 原始 K 线及复权因子，存储为 CSV。
2. **回测层**：已完成。实现了模块化、向量化驱动的动态再平衡系统。

## 回测框架架构 (AI 开发指南)
- `data_loader.py`：负责多标的数据对齐（trade_date 为准）及**后复权（HFQ）**价格计算。
- `backtest_engine.py`：核心逻辑。使用状态机遍历交易日，计算每日净值。
  - **动态平衡逻辑**：每季度末检查一次。
  - **触发条件**：任一资产偏离目标权重（33.33%）绝对值 > 5% 则触发全局再平衡。
  - **损耗计算**：换手额 * 0.02% 手续费。
- `metrics.py`：包含 `annualized_return`, `max_drawdown`, `sharpe_ratio` 等标准指标计算逻辑。

## 执行环境要求 (Execution Environment)
- **Conda 环境**：必须使用项目根目录下的 `./env` 环境进行所有代码执行。
- **Python 路径**：在执行命令时，优先使用 `./env/Scripts/python.exe` (Windows) 或 `./env/bin/python` (Unix)。
- **包管理**：默认使用阿里云镜像源 (`https://mirrors.aliyun.com/pypi/simple/`) 进行依赖安装。

## 后续开发要求
- **环境一致性**：Antigravity 在执行任何 Python 代码前，必须确保使用的是该项目特有的 `./env` 环境。
- **向量化优化**：在不改变逻辑的前提下，尽可能利用 Pandas 向量化操作提升回测速度。
- **绘图支持**：敏感度分析必须包含可视化输出 (`matplotlib`)，确保环境可用。
- **代码注释**：所有策略逻辑必须包含详细的中文注释，解释调仓触发机制。
