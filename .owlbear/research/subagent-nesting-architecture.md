# Subagent Nesting Architecture — Strategic Design

> **Owning task:** #228 — Subagent nesting architecture — validate designs and create implementation plan
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

VS Code Copilot supports nested subagent invocation (`chat.subagents.allowInvocationsFromSubagents`). Empirical testing confirmed nesting works to L4+ depth with full tool functionality. The current pipeline is flat: orchestrator dispatches agents, each agent works alone. This creates context pollution, sequential bottlenecks, repeated pitfall knowledge, and degrading retry quality. Four nesting categories were proposed — this research validates each against current pain points.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Agents Concepts | https://code.visualstudio.com/docs/copilot/concepts/agents | .95 — confirms parallel subagent execution |
| S2 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — nesting depth (max 5), orchestration patterns, coordinator/worker |
| S3 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — agents field overrides disable-model-invocation, inherit/assign |
| S4 | OwlBear empirical nesting test (2026-03-30) | Local testing | .95 — L4 depth, ~43 inherit / ~30 assign tools |
| S5 | OwlBear orchestrator.agent.md | agents/orchestrator.agent.md | .90 — current parallel wave dispatch (wave size 4) |
| S6 | OwlBear agent-common.instructions.md | instructions/agent-common.instructions.md | .85 — retry/block/handoff conventions, 2-retry max |

## 3. Analysis

### 3a. Parallel SubAgent Execution — CONFIRMED (empirical)

**Empirical test session — 2026-03-31** (builder #228, L2 nesting depth)

Two `runSubagent` calls were issued simultaneously from within the builder agent session:
- Call A: list kanban/tasks/ → `count=74, start=16:52:41, end=16:52:41`
- Call B: list tests/ → `count=73, start=16:52:41, end=16:52:41`

Both calls resolved successfully in under 1 second of wall-clock time. **No rate-limit errors were observed.** Both subagents executed in parallel with overlapping execution windows. This confirms `runSubagent` supports multiple simultaneous invocations from a single parent agent at L2 depth.

Rate-limit behavior: zero throttling observed for N=2 parallel calls at L2. The VS Code docs explicitly state "VS Code can spawn multiple subagents in parallel" (S1). The orchestrator already uses parallel wave dispatch (S5). For N>4 or deeper nesting, the orchestrator's existing sequential-fallback mechanism (S6) provides the mitigation pattern. Maximum nesting depth is 5 (S2).

### 3b. Category Validation

| Category | Valid | Conf | Beneficiaries | Evidence |
|----------|-------|------|---------------|----------|
| E-sub (Utility Subagents) | YES | .90 | Builder, Reviewer, Auditor, Test-Writer | 4 agents handle pytest/ruff independently; 10+ pitfalls in pytest-and-linting skill |
| B (Parallel Fan-Out) | YES | .85 | Reviewer, Auditor, Researcher | VS Code docs show coordinator/worker + multi-perspective review patterns (S2) |
| D (Context Management) | PARTIAL | .65 | Builder, Reviewer | Explore agent already covers researcher; overlaps with E-sub context savings |
| F (Fresh-Context Retry) | YES | .75 | Builder, Auditor | Orchestrator 2-retry convention (S6); context degradation is the documented cause |

### 3c. Quality-Runner Interface Design

**Mode:** Assign (.80 confidence). Needs 6 tools: `execute/runInTerminal`, `execute/getTerminalOutput`, `execute/awaitTerminal`, `execute/killTerminal`, `read/readFile`, `vscode/memory`. Assign prevents scope creep; inherit adds ~17 unnecessary tools. S3 confirms agents listed in parent's `agents:` array override `disable-model-invocation: true`.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mode | "scoped" / "full" | yes | Scoped = specific files, full = entire suite |
| test_paths | string[] | if scoped | File paths to test |
| task_id | string | yes | For COVERAGE_FILE isolation |
| coverage_modules | string[] | no | Modules to measure |
| lint_paths | string[] | no | Paths to lint (default: src/ tests/) |

**Output:** Structured text with sections: `tests` (passed count, failed [{name, error}], skipped), `lint` (clean bool, violations [{file, line, code, msg}]), `coverage` (overall_pct, modules [{name, pct}]), `errors` [string].

**Error contract:** Max 2 internal retries. Timeout: 5 min (full), 2 min (scoped). Fatal errors populate `errors`; test failures populate `failed`.

### 3d. Parallel Fan-Out Ranking

| Agent | Benefit | Context Savings | Pattern |
|-------|---------|----------------|---------|
| Reviewer | Highest | 40-50% | Quality-Runner + Code-Reader in parallel |
| Auditor | High | 35-45% | Quality-Runner + AC-Verifier + Code-Spotter |
| Researcher | Moderate | 20-30% | Already uses Explore; parallel source-gatherers add incremental value |
| Builder | Low | 10-15% | Inherently sequential (test, implement, verify cycle) |

### 3e. Fresh-Context Retry Threshold

**Recommendation: 2 failures** (.75 confidence). 1st failure: same-context retry (cheap, resolves transients). 2nd failure: delegate to fresh-context Fix-Attempt subagent. Fresh-context also fails: report to orchestrator for block/escalate. Aligns with orchestrator's 2-retry maximum (S6).

## 4. Recommendations

| Category | Recommendation | Conf | Rationale |
|----------|---------------|------|-----------|
| E-sub | Quality-Runner first, then Git-Ops | .90 | Highest ROI: 4 agents benefit, 10+ pitfalls encapsulated |
| B | Reviewer parallel first, then Auditor | .85 | Cleanest 2-way split; validates pattern before complex 3-way |
| D | Defer — subsume into E-sub and B | .65 | Explore covers researcher; residual value low until E-sub/B prove patterns |
| F | Builder threshold=2 | .75 | Most failure-prone agent; aligns with existing retry convention |

**Cross-cutting:** Assign mode for utility subagents (.80). Enable `chat.subagents.allowInvocationsFromSubagents`. Subagents use `user-invocable: false` (hidden from picker) without `disable-model-invocation: true` (so parent agents can reference them via `agents:` per S3).

## 5. Follow-up Tasks

Decision requests created in `docs/decisions/pending/228-*.md` (one per category). Implementation tasks created at `ideation` pending approval. See task body of #228 for kanban-md commands executed.

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Nesting startup latency | Medium | Only nest where context savings outweigh time cost |
| tool_search_tool_regex unavailable in subagents | Low | Deferred tools pre-expanded; MCP available via inherit or explicit tools list |
| Parent-child communication overhead | Medium | Strict I/O contracts; subagents return structured data only |
| Rate limits on parallel L2+ calls | Low | Orchestrator sequential-fallback pattern applies (S6) |
| manage_todo_list unavailable in subagents | Low | Use inline text tracking; documented limitation (S4) |
