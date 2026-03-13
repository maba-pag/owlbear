# Olanetsoft AI Agent Workflow Patterns for OwlBear

> **Task:** #747 — Research Olanetsoft AI agent workflow patterns for OwlBear
> **Date:** 2026-03-12
> **Status:** Complete

## 1. Context

Evaluate the [Olanetsoft workflow gist](https://gist.githubusercontent.com/Olanetsoft/5931f1861d2ee9bcefb16774ff21e41e/raw/e4231969f53af71ffaeb4bb61fa7cfa13317f1a6/workflow.md) — 6 orchestration patterns, a task management flow, and 3 core principles — for adoption into OwlBear's multi-agent pipeline.

## 2. Sources

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Olanetsoft workflow gist | [gist.githubusercontent.com/.../workflow.md](https://gist.githubusercontent.com/Olanetsoft/5931f1861d2ee9bcefb16774ff21e41e/raw/e4231969f53af71ffaeb4bb61fa7cfa13317f1a6/workflow.md) | Primary source — 6 workflow patterns + task mgmt + principles |
| 2 | OwlBear agent-common.instructions.md | `.github/instructions/agent-common.instructions.md` | Existing post-task reflection, task discipline, terminal discipline |
| 3 | OwlBear copilot-instructions.md | `.github/copilot-instructions.md` | Existing KISS/YAGNI/DRY, "Think before coding", quality principles |
| 4 | OwlBear orchestrator + planner agents | `.github/agents/orchestrator.agent.md`, `planner.agent.md` | Existing plan→dispatch→loop, wave planning, DAG-based scheduling |
| 5 | OwlBear builder/reviewer/auditor agents | `.github/agents/{builder,reviewer,auditor}.agent.md` | Existing 3-line verification model, TDD workflow, confidence thresholds |
| 6 | OwlBear daemon.py (RetrospectiveHook) | `src/owlbear/core/retrospective_hook.py` | Existing self-improvement: structured retro findings → KG ingestion |
| 7 | OwlBear ContextInjectionHook | `src/owlbear/core/context_hook.py` | Session-start context injection (context.md, not lessons) |
| 8 | AutoGen event logging | `github.com/microsoft/autogen` | Prior art for self-improvement patterns (cited in `docs/agent-analytics-research.md`) |

## 3. Overlap Analysis

| # | Olanetsoft Pattern | OwlBear Equivalent | Overlap | Gap |
|---|--------------------|--------------------|---------|-----|
| 1 | Plan Node Default | Planner agent + wave-planning skill; builder "Think before coding" | .95 | None material — OwlBear plans at both dispatch and code level |
| 2 | Subagent Strategy | DelegationToolset (depth=5); orchestrator waves of 4; "ONE task per invocation" | .95 | None — OwlBear has deeper infra (registry, role policies, delegation depth) |
| 3 | Self-Improvement Loop | Post-task reflection → inbox → curator; RetrospectiveHook → KG; ErrorJournal | .60 | **No "review lessons at session start"** — lessons exist but aren't injected into agent context |
| 4 | Verification Before Done | 3-line defense model (builder→reviewer→auditor); TDD; confidence thresholds (.90/.95) | 1.0 | None — OwlBear exceeds this pattern |
| 5 | Demand Elegance | "Quality over speed"; KISS/YAGNI as counterbalance | .70 | **No explicit self-review step** in builder workflow |
| 6 | Autonomous Bug Fixing | Autonomous mode (poll_loop); but all work goes through full TDD pipeline | .40 | **No fast-track for trivial bugs** — every fix requires TDD + review |
| 7 | Task Management (6 steps) | kanban-md + manage_todo_list + builder notes + review evidence | .90 | None material |
| 8 | Core Principles (3) | KISS, "Surgical changes", "Simplicity first", "No legacy code" | .95 | None — OwlBear principles are broader |

## 4. Trade-Off Analysis: Candidate Patterns

Only patterns with overlap < .90 (gaps exist) are candidates:

### 4a. Lessons Injection at Session Start (from #3)

| Factor | Assessment |
|--------|------------|
| **Value** | Medium — prevents repeat mistakes across sessions; closes the loop between post-task reflection and agent behavior |
| **Effort** | Low (~30 LOC) — new hook on `SESSION_START` reads recent lessons from `/memories/repo/` and injects as context |
| **Risk** | Context bloat if unfiltered; mitigated by token budget cap and curator pre-filtering |
| **KISS** | Passes — small hook, reuses existing infra (HookRegistry, ContextInjectionHook pattern) |
| **YAGNI** | Borderline — lessons exist but aren't consumed yet; this closes a designed-but-unwired loop |
| **Confidence** | .80 — clear gap, low effort, proven pattern (Olanetsoft + OwlBear's own ContextInjectionHook) |

### 4b. Self-Review Prompt in Builder Workflow (from #5)

| Factor | Assessment |
|--------|------------|
| **Value** | Low — the reviewer already catches quality issues; adding a self-check adds latency |
| **Effort** | Minimal — one sentence in builder agent system prompt |
| **Risk** | Over-engineering risk; contradicts KISS if it causes unnecessary refactoring |
| **KISS** | Marginal — adds cognitive load to builder for little measurable benefit |
| **YAGNI** | Fails — the reviewer already provides adversarial quality checks |
| **Confidence** | .40 — reviewer makes this redundant; not recommended |

### 4c. Fast-Track Bug Fix Pipeline (from #6)

| Factor | Assessment |
|--------|------------|
| **Value** | Medium — reduces latency for trivial fixes; matches user expectation for quick bug resolution |
| **Effort** | High — requires new status flow, pipeline exception, risk of bypassing quality gates |
| **Risk** | Quality regression; undermines TDD discipline; "trivial" is subjective |
| **KISS** | Fails — adds complexity to the pipeline for an edge case |
| **YAGNI** | Fails — no evidence of velocity problems from the current pipeline |
| **Confidence** | .25 — high effort, high risk, insufficient justification |

## 5. Recommendation (.80 confidence)

**Adopt one pattern: Lessons Injection at Session Start (4a).**

Reject 4b (reviewer makes it redundant) and 4c (YAGNI, high risk). The remaining Olanetsoft patterns (1, 2, 4, 7, 8) are already well-implemented in OwlBear — no action needed.

The lessons injection hook closes a designed-but-unwired loop: agents write post-task reflections, the curator curates them, but no agent _reads_ them at session start. This is the single highest-value gap the Olanetsoft workflow reveals.

## 6. Follow-Up Tasks

```
kanban\kanban-md.exe create "Implement LessonsInjectionHook for session-start context" --priority nice-to-have --tags "hooks,agent,scope:core" --status backlog --body "Implement a SESSION_START hook that reads recent curated lessons from /memories/repo/ and injects them into agent context.\n\nAC:\n- [ ] New hook class LessonsInjectionHook in src/owlbear/core/lessons_hook.py\n- [ ] Reads .md files from configured lessons directory (default: workspace/.owlbear/lessons/)\n- [ ] Token-budgeted injection (max 500 tokens) to prevent context bloat\n- [ ] Registered in bootstrap/hooks.py alongside existing hooks\n- [ ] Unit tests in tests/test_lessons_hook.py\n- [ ] Gated behind settings.lessons_injection_enabled (default False)\n\nRef: docs/research/olanetsoft-workflow-research.md"
```
