# 代码库审计与精简记录（2026-10-29）

What this repo does: 本仓库提供日频事件驱动回测、模拟组合续跑、真实持仓对账与下单计划，以及独立的 ETF 筛选和只读看板。按个人本机使用、少量研究任务、单个账户状态由一个写入进程维护的负载审查。

本次按用户要求直接落实修复与精简。扫描了 61 个生产 Python 文件，对 105 个 Python 文件完成语法解析；深入检查行情读取与同步、企业行为、策略、撮合、回测归档、组合续跑、实盘核算、指标、看板读取和 ETF 筛选等主路径。没有改动历史行情、配置、结果或既有报告。

## Must fix：已修复

1. **ES 约束求解受收益单位影响，并可能接受没有尾部损失的结果**（[expected_shortfall.py](D:/strategy/platform/src/platform_core/strategies/expected_shortfall.py:388)）
   - **功能：** 按给定预算分配 Expected Shortfall，即最差一段收益样本的平均损失，同时满足权重上下限。
   - **问题：** 已有随机样本测试在收益乘 `0.001` 后报 `Positive directional derivative for linesearch`；全部收益为正时，常数惩罚也可能被求解器标记为成功。
   - **修复：** 为风险贡献误差提供显式梯度；投影后的权重必须具有正的组合尾部损失，保留求解失败时抛错的行为。增加收益放大、梯度数值校验和无损失样本回归测试。
   - **不修后果：** 相同经济情形可能无法求解，或输出没有相应风险含义的权重。现有失败用例与新增边界用例均通过；该修复不代表非光滑优化已获得全局最优保证。

2. **敏感性图表遇到缺失指标会失败**（[visualization.py](D:/strategy/platform/src/platform_core/visualization.py:143)）
   - **功能：** 绘制不同起点下的收益、Sharpe 与回撤。
   - **问题：** 纵轴先丢弃缺失指标，横轴却保留全部日期；样本不足的起点会造成横纵坐标长度不一致。
   - **修复：** 每个指标先筛出有效行，再从同一批行取得日期和值。单场景和多场景测试均实际生成图表。
   - **不修后果：** 敏感性执行可能完成，但汇总图生成失败。

3. **缺失行情日期未在日历构造前拒绝**（[data.py](D:/strategy/platform/src/platform_core/data.py:84)）
   - **功能：** 从 CSV 建立行情序列和交易日历。
   - **问题：** 空日期会被解析为 `NaT`，原先只检查重复日期，可能将缺失日期带入后续排序、比较和日历判断。
   - **修复：** 在构造日历之前明确拒绝缺失日期，并增加回归测试。
   - **不修后果：** 错误数据会在更深的执行路径才失败，难以定位到输入文件。

4. **短窗口估值导出会截断已有历史**（[ingest_index_valuation.py](D:/strategy/platform/scripts/ingest_index_valuation.py:78)）
   - **功能：** 将 Wind 指数估值导出按指数拆分，供价值轮动信号读取。
   - **问题：** 原先直接覆盖整个 CSV；本次只导出后两个日期时，已存的更早日期被删除。先按日期做不稳定排序再去重，也不能保证同日记录取原始输入的最后一条。
   - **修复：** 复用 `merge_observations` 保留响应外的历史，再用 `write_csv_stable` 原子写盘；先去重再排序。删除无人读取的 `__source` 中间列。
   - **不修后果：** 增量入库会缩短估值窗口，影响策略历史分位。测试覆盖短窗保留旧日、更新重叠日、相同内容不动文件、无交易日输入保留旧文件，以及 2/32 条同日重复记录。

## Should fix：已完成

5. **7 个策略重复实现相同收益预处理**（[strategy.py](D:/strategy/platform/src/platform_core/strategy.py:200)）
   - **功能：** 风险平价、收缩协方差、层次配置、动态预算、聚类、Gerber 与 EWMA 协方差策略均需按估计频率准备收益样本。
   - **问题：** 日、周、月重采样、窗口换算与最小样本检查各复制一遍；相同规则需要在多处同步维护。
   - **修复：** 共用 `_historical_returns`，保留各策略求解方法、默认窗口、NAV 选择及波动率乘数的原有差异。
   - **不修后果：** 后续修正一个频率或样本规则时容易遗漏策略。以 `8e7196c` 为基准的 84 组合成数据对照中，新旧权重在 `rtol=atol=1e-12` 下全部一致。

6. **首次生成和增量扩展复权因子重复计算企业行为**（[hfq_factors.py](D:/strategy/platform/src/platform_core/hfq_factors.py:16)）
   - **功能：** 将分红和拆分计入后复权因子，并延续已有历史因子。
   - **问题：** 两条分支分别复制分红、拆分、输出组装逻辑；分红截止日和拆分生效日又存在必须保留的边界差异。
   - **修复：** 先确定待计算行情段与起始因子，再共用事件计算。保留历史值、来源和时间戳；已有截止日分红不重复计入，截止日拆分仍在后续真实行情日生效。
   - **不修后果：** 修正事件处理时容易只改一个分支。新增测试同时覆盖截止日分红、拆分、新分红和重复同步不改写文件。

7. **包装函数和重复返回结构增加调用层次**（[strategy.py](D:/strategy/platform/src/platform_core/strategy.py:25)、[execution.py](D:/strategy/platform/src/platform_core/execution.py:277)、[selection.py](D:/strategy/etf_selection/src/selection.py:354)、[run_live_cycle.py](D:/strategy/platform/scripts/run_live_cycle.py:137)）
   - **功能：** 策略上下文、撮合和实验工具原有多层转发；ETF 篮子另外返回一份可由结果表取得的代码列表。
   - **问题：** `read_run_tables` 仅被测试使用；`basket_codes` 被生产调用方直接丢弃；其余若干方法只有一个使用点，或只转发到实际实现。
   - **修复：** 删除或合并 `tradable_asset_ids`、`set_rebalance_frequency`、上下文 `is_month_end`、`_is_rebalance_day`、`read_run_tables`、`run_name`、`_initial_equity`、`_slippage_rate`、`_available_buy_cash`、`index_code_for`、`TargetPortfolio.equal_weight`、`build_portfolio`、`resolve_holdings_path`。删除 `build_baskets` 的第三个返回值，更新全部仓库调用与测试；持仓参数直接用 `argparse` 解析成 `Path`，保留统一的 `Strategy.generate_targets` 和有效扩展接口。
   - **不修后果：** 修改简单规则需要跨多处跳转，并持续维护无人使用的返回结构。删除前已检索仓库代码、测试、配置和文档引用。

8. **Windows 默认编码导致测试失败和子进程读取警告**（[selection.py](D:/strategy/etf_selection/src/selection.py:126)）
   - **功能：** 测试读取中文报告，ETF 筛选从平台命令读取溢价结果。
   - **问题：** 4 项基线测试使用系统默认编码读取 UTF-8 文件；子进程错误输出混用编码时，读取线程也可能抛出解码异常。
   - **修复：** 中文产物测试明确使用 UTF-8；诊断输出使用替换方式容忍不可解码字节，继续依据退出码报错。没有放宽 JSON 解析和数据校验。
   - **不修后果：** 正确的中文文件在本机测试失败，真实数据错误又可能被输出解码异常掩盖。

## Nice to have：已完成

9. **交易日查询重复扫描整段历史**（[data.py](D:/strategy/platform/src/platform_core/data.py:215)、[strategy.py](D:/strategy/platform/src/platform_core/strategy.py:97)、[engine.py](D:/strategy/platform/src/platform_core/engine.py:123)）
   - **功能：** 查找拆分后的真实交易日、日历位置和缺行情日的上一条有效价格。
   - **问题：** 原先通过完整列表扫描或 DataFrame 布尔切片查找单个日期；回测循环还每天重复读取初始权益配置。
   - **修复：** 对已排序日期使用二分查找和 `searchsorted`，初始权益在进入日循环前计算一次。
   - **不修后果：** 长历史和批量敏感性执行承担重复扫描与临时切片开销。日期边界、严格晚于拆分日、停牌补价和月末判断均有测试；本次没有测量端到端提速倍数。

10. **指标计算重复复制和过滤同一张表**（[metrics.py](D:/strategy/platform/src/platform_core/metrics.py:47)）
    - **功能：** 从持仓和净值产物计算全期、训练段及后续样本指标。
    - **问题：** 日期筛选先复制全表，筛完又复制；有效持仓数量与首次持仓日分别重新转换、筛选同一数量列。
    - **修复：** 直接在原表计算日期掩码，只复制返回结果；首次持仓日复用已经筛好的有效持仓。
    - **不修后果：** 每次指标统计都额外创建表副本并重复扫描持仓。现有指标与归因回归测试通过；未声称端到端提速比例。

11. **依赖列表保留全库无调用的 `tqdm`**（[requirements.txt](D:/strategy/requirements.txt:1)）
    - **功能：** `tqdm` 提供进度条。
    - **问题：** 全库代码、测试、配置和文档均无引用，仅依赖列表保留该项。
    - **修复：** 删除直接依赖声明，不卸载用户环境中的包。
    - **不修后果：** 项目持续声明不需要直接使用的依赖。其他依赖仍可能间接安装它，因此不声称安装环境一定减少一个包。

## 验证与兼容边界

- 首轮记录基线：`536 passed, 5 failed`；本轮接续基线：`549 passed in 22.27s`；最终：`551 passed in 25.53s`，无测试警告。
- 最终命令：`.\env\Scripts\python.exe -m pytest platform/tests etf_selection/tests -q`。
- 84 组策略对照覆盖 7 个策略 × 3 个估计频率 × 2 种价格/NAV 输入 × 2 种样本长度；只使用合成数据，没有运行真实行情研究或绕过行情新鲜度门禁。
- `git diff --check` 通过。105 个 Python 文件语法检查通过，21 个 CLI 的 `--help` 正常；看板启动因本机缺少 `streamlit` 失败。新增脚本数量为 0；新增回归测试文件为 `platform/tests/test_sensitivity_charts.py`。
- 生产 Python 代码合计新增 166 行、删除 421 行，净减少 255 行；该统计不包含测试、依赖列表和本报告。删除或合并 13 个函数，新增 1 个被 7 个策略共用的预处理函数；直接依赖声明减少 1 项。
- `build_baskets` 现在返回 `(basket_frame, corr_by_basket)`。仓库外若有旧调用，需要同步修改解包；已删除的上下文便利方法、估值映射便利方法和等权工厂同理。
- 策略源码哈希会变化。已有版本和历史产物保留；旧状态的 runtime 续跑仍按现有源码身份校验规则处理，不伪装为旧策略版本。
- 未注册的研究策略仍有专门测试和研究复现用途，予以保留；缓存装饰器、两个存储实现的共同接口、校验与错误处理均有实际职责，予以保留。
- 最后一轮复查了低引用函数、未使用导入与参数、完全相同的函数体、删除项的全库引用及关键修改差异，没有再确认值得实施的精简点。缓存签名参数用于失效判定；包导出和策略扩展参数有实际用途，不能仅凭静态函数体未读取就删除。这是本次范围内的收敛结论，不是对未知输入和外部调用的绝对保证。

Verdict: 已修复本次确认的正确性问题，并完成有调用证据支持的精简；全量测试通过。

Lean: -255 lines, -1 direct dependency（生产 Python 代码净减少值）。

Not checked: 未逐行审阅全部测试实现、历史报告和研究资料；未运行真实行情回测、联网数据同步、SMTP/微信实际发送或人工浏览器验收。当前项目环境中 `finshare` 和 `streamlit` 模块不可用，因此没有验证真实数据源连接与看板启动后的交互；也未验证多个进程同时写同一账户状态的场景。
