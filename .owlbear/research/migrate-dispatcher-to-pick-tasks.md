# Migrate Dispatcher to pick_tasks MCP Tool

> **Owning task:** #619 — Migrate dispatcher to pick_tasks MCP tool in owlbear-kanban
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #619 proposes replacing the dispatcher agent (`share/agents/dispatcher.agent.md`) with a `pick_tasks` MCP tool inside the owlbear-kanban server. The dispatcher is `disable-model-invocation: true` — a deterministic pure function: board_state → dispatch list. The Python implementation already exists in `serve/orchestrator/src/owlbear/planner/` (gates.py, selector.py, board.py, models.py).

**Key questions:** (1) Is the migration technically feasible within the mcp-kanban server? (2) What are the risks of code duplication between planner/ and mcp-kanban? (3) Can the orchestrator planner/ package be removed? (4) Is the subtask decomposition (#620–#624) complete?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .95 | Tool registration patterns, `_run_kanban` infrastructure, output schema |
| S2 | `serve/orchestrator/src/owlbear/planner/gates.py` | .95 | Gate predicates: atomicity, TDD, clarity (~50 LOC) |
| S3 | `serve/orchestrator/src/owlbear/planner/selector.py` | .95 | Sort logic, STATUS_AGENT_MAP, DISPATCH_CAP, select_tasks() |
| S4 | `serve/orchestrator/src/owlbear/planner/board.py` | .90 | Board reader: `--unblocked --not-blocked --unclaimed` CLI flags |
| S5 | `share/agents/dispatcher.agent.md` | .90 | Confirms zero LLM usage, JSON-only output, read-only contract |
| S6 | `share/skills/w-orchestration/SKILL.md` | .90 | Orchestrator's current dispatcher invocation in Step 1 |
| S7 | `share/agents/orchestrator.agent.md` | .85 | Dispatcher listed in agents, subagent table shows dispatch pattern |
| S8 | MCP spec: Tools (modelcontextprotocol.io) | .80 | readOnlyHint, outputSchema, ToolAnnotations for computed tools |
| S9 | `.owlbear/research/build-dispatch-planner.md` (#20) | .80 | Prior art: planner module design, board-reading strategy |
| S10 | `serve/orchestrator/src/owlbear/orchestrator/loop.py` | .85 | Imports from planner/ — blocks removal of planner package |

## 3. Analysis

### 3.1 Feasibility: Dispatcher → MCP Tool

| Aspect | Current (dispatcher agent) | Target (pick_tasks tool) | Delta |
|--------|---------------------------|--------------------------|-------|
| Invocation | orchestrator → runSubagent("dispatcher") → agent context load → MCP calls → JSON parse | orchestrator → pick_tasks() MCP call → JSON result | -3 hops |
| LLM usage | Zero (disable-model-invocation) | Zero (server-side computation) | Same |
| Board reading | Agent calls list_tasks MCP tool | Server calls `_run_kanban` directly (same binary) | Equivalent |
| Gate logic | Agent runs w-dispatch-planning skill | Server runs gate functions inline | Equivalent |
| Sort+cap | Agent applies Recipe 1 manually | Server runs (PRIORITY_RANK, STATUS_RANK) sort + cap | Equivalent |
| Output | `{"dispatch": [{"id": N, "agent": "..."}]}` | `{"dispatch": [{"task_id": N, "status": "..."}]}` | Agent mapping removed |
| Error | Agent returns JSON or crashes | ToolError on rc≠0 or parse failure | Better |
| LOC | ~200 (agent.md + SKILL.md) | ~80 (inline in server.py) | -60% |

**Verdict: Fully feasible (.92).** The `_run_kanban` infrastructure already exists. Gate logic is ~50 LOC of pure regex/string checks. Sort logic is ~20 LOC.

### 3.2 Code Duplication Risk

mcp-kanban has **no dependency** on orchestrator (`pyproject.toml: dependencies = ["mcp[cli]>=1.26"]`). Gate functions MUST be copied, not imported.

| Option | Approach | KISS | Risk | Maintenance |
|--------|----------|:----:|:----:|:-----------:|
| A. Copy gates inline | ~50 LOC of gate logic in server.py | High | Low — gates are stable | 2 locations |
| B. Shared package | New `owlbear-gates` package imported by both | Low | Medium — new dep, packaging | 1 location |
| C. Import from orchestrator | mcp-kanban depends on orchestrator | Low | High — circular concern | 1 location |

**Recommendation (.88): Option A — copy inline.** Gates have been stable since #20 (2026-03-29). The ~50 LOC is simple regex. Shared package adds packaging overhead for 3 functions. KISS and YAGNI favor duplication over premature abstraction.

### 3.3 Planner Package Removal (#624)

`loop.py` imports `read_board` and `select_tasks` from `planner/`:
- `serve/orchestrator/src/owlbear/orchestrator/loop.py` L17-18: `from owlbear.planner.board import read_board` / `from owlbear.planner.selector import select_tasks`
- `serve/orchestrator/src/owlbear/cli.py` L15-16: same imports

**Verdict: planner/ CANNOT be removed.** The headless orchestrator loop (ACP mode) uses planner/ as an in-process library. The VS Code orchestrator agent will use pick_tasks MCP tool. These are two distinct paths:

| Path | Consumer | Mechanism | Planner dependency |
|------|----------|-----------|-------------------|
| Agent mode | orchestrator.agent.md | `pick_tasks` MCP tool call | None (server has own gates) |
| Headless mode | orchestrator/loop.py | `from owlbear.planner import select_tasks` | Direct import |

#624 outcome: keep planner/, add dual-path documentation comment.

### 3.4 Subtask Completeness

| Task | Scope | Status | Gap? |
|------|-------|--------|------|
| #620 | Tests for pick_tasks | todo (architect approved) | None — ready for TDD RED |
| #621 | Implement pick_tasks | backlog (researched) | #628 adds `tag` param — AC update needed before todo |
| #622 | Wire into orchestrator | backlog (researched) | Depends on #621; 2 follow-ups created (#628, #629) |
| #623 | Deprecate dispatcher agent | ideation | Needs #622 complete first; AC is clear |
| #624 | Evaluate planner/ cleanup | ideation | Answer known: keep planner/ (see §3.3) |
| #628 | Add tag param to pick_tasks | ideation | Pre-req for #621 AC update |
| #629 | Clean up dispatcher refs | ideation | Post-#622 cleanup |

**Gap identified:** #628 (tag parameter) blocks #621 from being fully scoped. The #621 AC currently says "no filters". The orchestrator needs tag-based scope filtering. #628 should be resolved before #621 enters todo.

### 3.5 `list_tasks` Body Stripping

The existing `list_tasks` tool strips `body` from output (performance optimization). `pick_tasks` needs body for TDD and clarity gates. **pick_tasks must issue its own `_run_kanban` call and retain full JSON**, not reuse `list_tasks`. This is correctly noted in #621 research.

## 4. Recommendation (.88 confidence)

**Proceed with the migration as designed in #619.** The architecture is sound, the decomposition is thorough, and the code paths are well-understood.

Key decisions:
1. **Copy gates inline** — ~50 LOC in server.py, no shared package (KISS)
2. **Keep planner/** — headless loop.py still imports directly
3. **Resolve #628 first** — tag parameter needed before #621 enters todo
4. **#624 outcome pre-determined** — keep planner/, add dual-path comment

Challenge: N/A — T1 migration with pre-existing architecture decision in #619. No new capability, no security/breaking change, no architecture alteration.

Tier: **T1 (Autonomous)** — deterministic code migration within approved design.

## 5. Follow-up Tasks

Existing subtasks (#620–#624, #628, #629) cover all work. No new tasks needed.

Priority sequencing:
1. #628 (tag param AC update) — unblocks #621
2. #620 (tests) — TDD RED, already at todo
3. #621 (implement) — depends on #620
4. #622 (wire orchestrator) — depends on #621
5. #623 + #629 (deprecate + cleanup) — depends on #622
6. #624 (planner eval) — depends on #621 + #622; answer: keep
