# Research Dashboard

`research-dashboard/` 是平台研究的轻量协调目录，用来保存课题看板、研究笔记模板、成果摘要和待合并研究 PR 摘要。

本目录不保存原始回测结果、标准实验报告或平台配置。那些 artifact 仍按系统边界写入：

- 平台原始结果：`platform/results/`
- 平台标准报告：`platform/reports/`
- ETF 筛选结果：`etf_selection/reports/` 和 `etf_selection/generated_configs/`

## 文件说明

- `research_backlog.md`：研究看板，包含当前待办、进行中、完成和失败课题；历史课题必须保留，用于去重和避免重复研究。
- `research_note_template.md`：统一研究笔记模板，用于记录假设、冻结条件、验证命令、指标和建议。
- `research_history_summary.md`：成果历史登记表；保留历史课题、结论和报告链接，供新课题探索时检索。
- `pull_requests/`：研究 agent 提交的待合并 PR 摘要。

Harness prompt 只保存在 `.agents/agents/*/agent.json`，本目录不保留重复副本。

## 使用原则

1. 根目录 `AGENTS.md` 是最高优先级规则来源，本目录不能引入冲突规则。
2. 新课题先进入 `research_backlog.md`，再由研究 agent 认领。
3. 每个正式研究应使用 `research_note_template.md` 生成一份研究笔记，并在标准实验报告中回链。
4. 已完成、失败和 research-only 课题不得从看板或历史摘要中删除；如需压缩，只能改写为更短的可检索摘要并保留 ID、主题、结论和报告链接。
5. 失败、research-only 或探索性结论不得留下已注册策略或新的平台 baseline 配置。
