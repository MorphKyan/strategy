# Strategy: 模块化策略回测系统

## 项目简介
本项目是一个基于 Python 的高性能、解耦式策略回测系统。它支持多种投资策略（如均衡配置、风险平价等），具备自动化数据获取功能，并提供规范化的结果归档管理。

## 系统架构
项目采用模块化设计，确保各功能组件独立内聚：
- **`src/`**: 核心源代码目录。
    - `data_handler.py`: 负责数据获取（集成 Finshare）与加载，支持缺失数据自动下载。
    - `engine.py`: 通用回测计算引擎。
    - `strategies/`: 策略实现库（如 `balanced.py`, `risk_parity.py`）。
    - `metrics.py`: 量化评价指标库。
    - `utils.py`: 路径管理、配置加载等工具。
- **`configs/`**: YAML 格式的配置文件，定义资产池、权重及策略参数。
- **`data/`**: 本地行情数据存储（CSV 格式）。
- **`results/`**: 回测结果归档，按 `策略/时间戳` 分层存储。
- **`main.py`**: 项目统一执行入口。

## 环境依赖
项目推荐使用 Python 3.11 的 Conda 环境。

### 环境安装
```bash
# 创建并激活环境
conda create -p ./env python=3.11 -y
conda activate ./env

# 安装依赖
pip install -r requirements.txt
```

## 使用方法
通过根目录的 `main.py` 启动回测。

### 1. 运行默认配置
```bash
python main.py
```
默认加载 `configs/default.yaml`（等比例均衡策略）。

### 2. 指定配置文件
```bash
python main.py --config configs/risk_parity.yaml
```

### 3. 指定策略名称
可以通过参数覆盖配置中的策略：
```bash
python main.py --strategy risk_parity
```

### 4. 运行标准化研究实验
风险平价研究建议使用标准实验入口。该脚本会运行候选策略，并在可用时运行 baseline 对照，随后写入稳定的报告和指标文件：

```bash
.\env\python.exe scripts/run_experiment.py --strategy risk_parity --config configs/risk_parity.yaml
```

常见输出：
- `results/<strategy>/<timestamp>/`: 原始回测结果。
- `reports/experiments/<strategy>/<timestamp>/metrics.json`: 标准化指标。
- `reports/experiments/<strategy>/<timestamp>/report.md`: 实验报告。

### 5. 筛选风险平价 ETF 组合
ETF 组合研究使用固定候选池 `configs/risk_parity_etf_universe.yaml`。生成的候选配置会写入 `configs/generated/`，不会覆盖默认配置。

```bash
.\env\python.exe scripts/select_risk_parity_universe.py --write-configs
```

如果本地缺少候选 ETF 数据，可允许脚本先尝试补齐数据：

```bash
.\env\python.exe scripts/select_risk_parity_universe.py --fetch-missing --write-configs
```

比较候选组合与默认风险平价组合：

```bash
.\env\python.exe scripts/run_experiment.py --strategy risk_parity --config configs/generated/<candidate-config>.yaml --baseline-config configs/risk_parity.yaml
```

## 配置说明
配置文件采用 YAML 格式，位于 `configs/` 目录。

### 主要配置项：
- `strategy`:
    - `name`: 对应的策略文件名（位于 `src/strategies/`）。
    - `params`: 策略参数（如 `rebalance_threshold` 再平衡阈值, `commission` 手续费）。
- `backtest`:
    - `assets`: 资产列表，包含 `code`（合约代码）和 `name`（展示名称）。
    - `start_date` / `end_date`: 回测时间范围。
- `output`:
    - `results_dir`: 结果存放根目录。

## 数据自动获取
系统内置自动数据同步功能。当您在配置文件中新增合约代码时，`DataHandler` 会自动从 Finshare 接口下载缺失的历史行情及后复权因子，并保存至 `data/` 目录。

## 结果查看
回测完成后，结果将保存在 `results/策略名/时间戳/` 下：
- `backtest_results.csv`: 每日净值及持仓细节。
- `trade_history.csv`: 交易明细。
- `config_snapshot.yaml`: 本次运行的配置副本，方便复现。

标准化研究实验还会在 `reports/experiments/策略名/时间戳/` 下保存：
- `metrics.json`: 从原始 CSV 重新计算的核心指标、换手和交易次数。
- `report.md`: 候选策略与 baseline 的对比报告。
- `latest_raw_results_path.txt`: 对应原始结果目录。

---
*注：原始重构前的脚本已移至 `backup/` 目录归档。*
