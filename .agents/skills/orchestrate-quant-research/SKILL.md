---
name: orchestrate-quant-research
description: Coordinate the repository's autonomous multi-agent quant research pipeline. Use when the user asks agents to explore a specified number of directions, run one or two researchers, and independently review their results using the repository harnesses. Do not use for a user-defined research direction that does not require autonomous topic selection or multi-agent orchestration.
---

# Orchestrate Quant Research

Coordinate roles; leave research policy to `$run-autonomous-quant-research`.

## Preconditions

- Work from `D:\strategy`.
- Read root `AGENTS.md` and `.agents/skills/run-autonomous-quant-research/SKILL.md`.
- Use the actual harnesses under `.agents/agents/`.
- Require agents working in `platform/` or `etf_selection/` to read the relevant subsystem `AGENTS.md`.
- Do not set a model override unless the user requests it.

## Direction and Worker Count

- Interpret `x` as the requested number of new research directions; ask for a positive integer if `x <= 0`.
- Launch one researcher when `x == 1`.
- Launch two researchers when `x >= 2`, unless the user explicitly requests one.
- Do not launch more than two researchers unless the user explicitly overrides this limit.

## Pipeline

### 1. Topic explorer

Launch one `topic_explorer` first and request exactly `x` directions. Explicitly instruct it to use `$run-autonomous-quant-research`, follow `.agents/agents/topic_explorer/agent.json`, and update `research-dashboard/research_backlog.md`.

Wait for the explorer unless enough suitable unclaimed `Todo` items already exist and the user explicitly asks to start immediately.

### 2. Researchers

Launch researchers in parallel after exploration. Explicitly instruct each to use `$run-autonomous-quant-research` and `.agents/agents/quant_researcher/agent.json`.

- Researcher 1 claims the first suitable unclaimed `Todo`.
- Researcher 2 claims the next suitable unclaimed `Todo`.
- Each records its owner/session before implementation.
- Agents share the workspace and must not revert or overwrite another agent's changes or artifacts.

The parent thread coordinates only; do not duplicate researcher work.

### 3. Reviewer

After researchers finish or produce concrete blocker evidence, launch one reviewer with `.agents/agents/research_reviewer/agent.json` and explicit use of `$run-autonomous-quant-research`.

Pass the available research note, report, `metrics.json`, config, raw artifact, and exact-command paths. Keep the reviewer read-only. If no concrete evidence exists, report why independent review cannot start.

## Parent Output

Maintain a compact coordination log of agent IDs, roles, topics, and status. The final Chinese summary must include:

- requested direction count and researcher count;
- directions explored and claimed;
- report and artifact paths;
- reviewer recommendation per result;
- blockers and required follow-up fixes.
