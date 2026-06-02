# AI Agent 工作指导说明 / AI Instructions

本文档旨在为后续接手或参与本系统开发的 AI 助手提供指导。

## 项目进展
1. **平台系统**：位于 `platform/`，实现日频事件驱动回测、执行撮合、checkpoint 和模拟组合推进。
2. **ETF 筛选系统**：位于 `etf_selection/`，独立的 ETF 标的筛选与组合篮子构建流程，负责根据历史数据及板块轮动规则，为 `platform/` 自动生成对应的资产配置 YAML 文件。

## 系统框架架构 (AI 开发指南)
- **回测引擎** ([engine.py](file:///D:/strategy/platform/src/platform_core/engine.py))：核心事件驱动回测类 `PlatformBacktestEngine`。使用状态机遍历交易日，通过策略生成的目标权重进行每日撮合模拟、净值计算及状态备份。
- **策略模块** ([strategy.py](file:///D:/strategy/platform/src/platform_core/strategy.py))：定义了统一的 `Strategy` 接口。内置有经典风险平价 (`"risk_parity"`)、EWMA 协方差估计 (`"risk_parity_ewma"`) 以及结合非线性阈值和大跌惩罚机制的自适应回撤恢复算法 (`"risk_parity_ewma_dd_recovery"`)。策略通过 `generate_targets(context)` 返回 `TargetPortfolio`。
- **数据与存储** ([data.py](file:///D:/strategy/platform/src/platform_core/data.py) & [data_store.py](file:///D:/strategy/platform/src/platform_core/data_store.py))：负责本地 ETF 复权价格数据的加载与基础财务信息的对齐。
- **表现评价** ([metrics.py](file:///D:/strategy/platform/src/platform_core/metrics.py))：在回测结束后解析输出的 CSV，计算年化收益、最大回撤、夏普比率、交易笔数及换手率等指标并输出成标准 `metrics.json`。

## 执行环境要求 (Execution Environment)
- **Conda 环境**：必须使用项目根目录下的 `./env` 环境进行所有代码执行。
- **Python 路径**：在执行命令时，优先使用 `.\env\python.exe` (Windows) 或 `./env/bin/python` (Unix)。
- **路径边界**：
  * 运行平台回测或实验时，解析的相对路径起点为 `platform/`。
  * 运行 ETF 筛选任务时，解析的相对路径起点为 `etf_selection/`。

## 后续开发要求
- **环境一致性**：执行任何 Python 脚本前，必须确保调用的是该项目特有的 `./env` 虚拟环境。
- **图表渲染**：在执行可视化绘图（如 `matplotlib`、`seaborn`）时，需确保使用 Agg 无界面后端渲染，以避免在无图形界面服务器上抛出 X11/Windows 窗口错误。
- **代码注释**：所有策略逻辑或核心改动必须包含详细的中文注释，以解释参数设定（如 $\alpha, \beta, \tau$ 等参数）和重平衡触发逻辑。
- **目录纯净**：绝对禁止混淆各系统的源码、配置文件、实验结果或分析报告。保证平台专有代码归入 `platform/`，筛选专有代码归入 `etf_selection/`。
