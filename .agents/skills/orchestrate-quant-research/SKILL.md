---
name: orchestrate-quant-research
description: Coordinate multi-agent quant research in D:\strategy. Use when the user asks to explore x research directions with .agents/agents/topic_explorer/agent.json, launch 1-2 .agents/agents/quant_researcher/agent.json workers based on the number of directions, and have .agents/agents/research_reviewer/agent.json wait for results and review them.
---

# Orchestrate Quant Research

Use this skill to run the repository's quant research agent pipeline without mixing responsibilities:

1. `topic_explorer` proposes or refreshes exactly the requested number of research directions.
2. One or two `quant_researcher` agents claim and research directions from the backlog.
3. `research_reviewer` performs an independent read-only review after researcher outputs are available.

## Preconditions

- Work from `D:\strategy`.
- Read `AGENTS.md` before launching agents, and preserve its priority over this skill.
- If any task involves `etf_selection/`, require the relevant agent to read `etf_selection/AGENTS.md`.
- Use the actual harness files:
  - `.agents/agents/topic_explorer/agent.json`
  - `.agents/agents/quant_researcher/agent.json`
  - `.agents/agents/research_reviewer/agent.json`
- If sub-agent tools are not currently exposed, call `tool_search` for sub-agent management tools before proceeding.

## Direction Count

Interpret `x` as the number of research directions the user wants explored.

- If `x <= 0`, ask the user for a positive integer.
- If `x == 1`, launch one researcher.
- If `x >= 2`, launch two researchers unless the user explicitly requests only one.
- Do not launch more than two researchers for this workflow unless the user explicitly overrides it.

## Agent Launch Protocol

Use `multi_agent_v1.spawn_agent` when available.

For every spawned agent:

- Pass the relevant `agent.json` as a structured `items` entry when possible, using type `text` with the JSON content or type `mention`/`skill` only if the tool supports the local harness path.
- State that the harness prompt is binding but cannot weaken `AGENTS.md`.
- State that all markdown reports, backlog updates, and summaries must be in Chinese.
- Do not set a model override unless the user explicitly asks for one.

### 1. Topic Explorer

Spawn one explorer first. Its task must ask for exactly `x` suitable directions and must require writing eligible new items to `research-dashboard/research_backlog.md`.

Prompt shape:

```text
Use the harness at .agents/agents/topic_explorer/agent.json.
In D:\strategy, explore exactly <x> quant research directions suitable for this repository and update research-dashboard/research_backlog.md as required by the harness and AGENTS.md.
Do not use final test-sample information to form hypotheses. Report the backlog item IDs/titles and any blockers.
```

Wait for this agent before launching researchers unless the backlog already contains enough unclaimed suitable `Todo` directions and the user explicitly asked to start immediately.

### 2. Quant Researchers

After topic exploration completes, spawn the researcher agents in parallel:

- For `x == 1`, spawn one `quant_researcher`.
- For `x >= 2`, spawn two `quant_researcher` agents.

Give each researcher a non-overlapping ownership rule:

- Researcher 1 claims the first suitable unclaimed `Todo` direction.
- Researcher 2 claims the next suitable unclaimed `Todo` direction.
- They must record their own session/owner in the backlog or research note before implementation.
- They are not alone in the workspace and must not revert or overwrite others' changes or generated artifacts.

Prompt shape:

```text
Use the harness at .agents/agents/quant_researcher/agent.json.
In D:\strategy, claim <first|second> suitable unclaimed Todo research topic from research-dashboard/research_backlog.md and complete the repository-required research workflow.
Use .\env\Scripts\python.exe for Python commands, or .\env\python.exe when the local environment uses that layout. Preserve sample isolation: research/training through 2025-06-30, final test only after candidate freeze from 2025-07-01 onward. Write Chinese reports and summarize exact artifact/report paths for review.
You are working concurrently with other agents; do not revert or overwrite their changes.
```

Do not redo researcher work in the parent thread. While researchers run, perform only coordination tasks such as tracking agent IDs and checking for obvious blockers.

### 3. Research Reviewer

Wait for the researcher agents to complete or report blockers. Then spawn one reviewer with read-only instructions and the researcher outputs.

Include all available evidence paths from researcher final messages:

- research note paths
- report paths
- `metrics.json` paths
- config copies
- raw artifact directories
- exact commands, if provided

Prompt shape:

```text
Use the harness at .agents/agents/research_reviewer/agent.json.
In D:\strategy, independently review these completed research outputs: <paths and summaries>.
Operate read-only. Verify AGENTS.md compliance, sample isolation, candidate freeze order, artifact traceability, metric completeness, and whether each result should be Accept, Reject, Needs Fix, or Research-only. Output the review in Chinese.
```

If any researcher blocks before producing reviewable evidence, the reviewer should still be launched only when it can review concrete partial artifacts or explicit blocker evidence. Otherwise report that review is blocked and why.

## Parent Thread Responsibilities

- Keep a compact coordination log in the conversation: agent IDs, assigned role, assigned topic if known, and status.
- Use `wait_agent` sparingly but with long enough timeouts to avoid busy polling.
- Close completed subagents with `close_agent` after their results have been captured.
- Final response must summarize:
  - requested `x`
  - number of researchers launched
  - backlog directions explored or claimed
  - research report/artifact paths
  - reviewer recommendation for each result
  - any blockers or follow-up fixes

## Integrity Rules

- Never allow topic exploration or parameter selection to use data from `2025-07-01` onward.
- Never ask the reviewer to modify files or complete missing research.
- Never overwrite historical results, reports, configs, checkpoints, or raw artifacts.
- Do not merge platform and `etf_selection/` source/config/report ownership unless the specific workflow requires generated platform configs.
- If an agent discovers stale data and sync fails, stop that research line and report the failure instead of continuing to backtest.
