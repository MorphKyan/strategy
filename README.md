# TM-Strategy

## 项目简介
本项目是一个基于Python的策略回测系统。项目主要使用 `finshare` 库获取指定ETF的全部历史期间未复权K线数据以及对应的前复权和后复权因子表，并将其存储为 `.parquet` 和 `.csv` 格式以供后续分析和回测使用。

## 环境依赖
项目运行依赖于 Python 3.11 的 Conda 环境。

### 环境安装
```bash
# 创建环境
conda create -p ./env python=3.11 -y
conda activate ./env

# 配置阿里云镜像源
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装依赖
pip install -r requirements.txt
```

## 数据获取
当前系统支持获取以下 ETF 的历史行情数据：
- 沪深 300 ETF（代码：510300）
- 易方达沪深 300 发起式 ETF（代码：510310）
- 华安黄金 ETF（代码：518880）
- 博时上证 30 年期国债 ETF（代码：511130）
- 十年国债 ETF（代码：511260）

运行 `python fetch_data.py` 可更新本地数据。

## 策略回测系统
系统实现了一个“三等分动态平衡策略”，核心逻辑如下：
1. **资产池**：沪深 300 ETF、黄金 ETF、十年国债 ETF。
2. **再平衡**：按季度检查，当任意资产权重偏离 33.33% 超过 5% 时触发强制平仓归位。
3. **交易摩擦**：双边 0.02% 手续费。

### 运行方式
- **常规回测**：运行 `python run_strategy.py`。输出年化收益、最大回撤、夏普比率等指标，并保存回测明细。
- **敏感度分析**：运行 `python sensitivity_analysis.py`。模拟从历史任意一天开始执行策略的表现，生成 `sensitivity_analysis.png` 趋势图。

## 开发指南
具体开发指南请参考 `AI_INSTRUCTIONS.md`。
