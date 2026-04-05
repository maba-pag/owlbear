---
id: 619
title: Migrate dispatcher to pick_tasks MCP tool in owlbear-kanban
status: review
priority: needed
created: 2026-04-05T01:30:40.2393944+02:00
updated: 2026-04-05T16:06:47.4550641+02:00
started: 2026-04-05T11:14:35.6735559+02:00
tags:
    - scope:mcp
    - scope:orchestrator
    - phase-2
    - type:restructure
    - quality
class: standard
---

## Summary

Replace the dispatcher agent (share/agents/dispatcher.agent.md) with a `pick_tasks` MCP tool inside the owlbear-kanban server. The dispatcher workflow is fully deterministic (`disable-model-invocation: true`) and the Python implementation already exists in serve/orchestrator/src/owlbear/planner/.

## Motivation

- Dispatcher uses zero LLM reasoning — it's pure function: board_state → dispatch list
- Current path: orchestrator → subagent call → agent context load → MCP calls → JSON output → parse
- Target path: orchestrator → single MCP tool call → JSON result
- Eliminates agent infrastructure overhead for a deterministic computation
- Tested Python code already exists in planner/ package (gates.py, selector.py, board.py, models.py)

## Scope

- New `pick_tasks` tool in owlbear-kanban MCP server
- Orchestrator agent updated to call tool directly (crash_failures filtering and agent mapping stay in orchestrator)
- Dispatcher agent deprecated and removed from orchestrator
- w-dispatch-planning skill archived (or kept as design doc)

## Architecture Decision

Tool signature:
```
pick_tasks(limit: int = 25) → {"dispatch": [{"task_id": int, "status": str}]}
```

One parameter: limit (default 25). No filters — the tool is zero-config and opinionated about what's eligible.

Logic: read board (unblocked, not-blocked, unclaimed) → apply gates (atomicity, TDD, clarity) → sort by priority then pipeline proximity → cap at limit → return task_id + status.

Agent mapping stays in orchestrator (status → agent is orchestrator's responsibility).
Crash failure exclusion stays in orchestrator loop (cycle-specific state).
Gate logic migrates from planner/gates.py. Sort logic from planner/selector.py.
Board reading reuses existing _run_kanban infrastructure.

Subtasks: #620-#624.

[[2026-04-05]] Sun 11:14
## Research
- Research doc: .owlbear/research/migrate-dispatcher-to-pick-tasks.md
- Sources: 10 studied, 8 high-relevance
- Recommendation: Proceed with migration as designed; copy gates inline (~50 LOC), keep planner/ for headless loop.py path, resolve #628 tag param before #621 enters todo (confidence: .88)
- Follow-up tasks created: none (subtasks #620-#624, #628, #629 already exist and cover all work)
- Decision requests: none, T1 autonomous migration

## Challenge Results
- Challenger: N/A, T1 migration, architecture pre-decided in task body
- Tier: T1 (autonomous), deterministic code migration within approved design
- Key finding: planner/ package CANNOT be removed (#624 answer: keep, dual-path comment)
- Key finding: #628 (tag param) should resolve before #621 enters todo

[[2026-04-05]] Sun 12:04
## Acceptance Criteria

- All subtasks (#620-#624, #628, #629, #630) complete or archived
- pick_tasks MCP tool registered and functional in owlbear-kanban server
- Orchestrator calls pick_tasks directly; no dispatcher subagent invocation
- Dispatcher agent marked deprecated
- planner/ package disposition documented (keep for headless loop.py, dual-path comment added)

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent coordination task for dispatcher-to-MCP migration |
| Interface clarity | PASS (refined) | AC section added with 5 verifiable completion criteria |
| Dependency correctness | FAIL | #628 depends_on [621] is inverted; #628 must update #621 AC before #621 starts |
| Module layering | PASS | mcp-kanban server standalone (no orchestrator dep), gates copied inline per KISS |
| TDD compliance | PASS | #620 covers TDD RED; parent tagged quality (pass-through) |
| KISS/YAGNI | PASS | Inline gate copy (~50 LOC) avoids shared-package overhead |
| Premise challenge | PASS | Dispatcher is disable-model-invocation=true; MCP tool is correct target |
| Pattern consistency | PASS | Follows _run_kanban infrastructure, ToolError conventions, readOnlyHint annotations |
| Security surface | PASS | No new system boundaries; local kanban-md binary only |
| Single domain | PASS | scope:mcp + scope:orchestrator, parent task is coordination-only |

### Dependency Graph Analysis

Chain: #620 (tests, todo), #621 (implement, backlog), #622 (wire, backlog), #623 (deprecate, ideation), #629 (cleanup, ideation). Also #621 depends on #624 (planner eval, ideation).

DEFECT: #628 depends_on [621] is wrong direction. #628 updates #621 AC for tag param; research doc says "resolve #628 before #621 enters todo." Dependency must be removed or reversed.

ADVISORY: #622 AC omits 4 findings from its own research: DECOMP routing via show_task post-filter, last_dispatched state tracking, retry-hint extraction, gate_warning removal. #622 architect must catch these.

ADVISORY: #623 last AC item ("No remaining references") is a superset of #629 scope. Clarify boundary during those tasks' reviews.

NEW: Created #630 (Fix TDD gate to exempt non-impl pass-through tags). gates.py check_tdd() does not implement the non-impl tag exemption documented in w-dispatch-planning Gate 4 spec. Pre-existing bug that will be copied into pick_tasks by #621.

### Challenge Results

- Challenger: RECONSIDER (confidence: 0.55)
- Key challenges: (1) #628 dep inversion is live dispatch-order defect, (2) #622 AC missing 4 research findings, (3) TDD gate exemption not in code, (4) no AC in parent task, (5) #623/#629 overlap
- Architect response: Accepted C1 as blocking; C2 deferred to #622 architect; C3 tracked as #630; C4 fixed (AC added above); C5 advisory

### Verdict: REFINE

### Re-approval conditions

1. Fix #628 dependency: remove depends_on [621] (or reverse so #621 depends on #628)
2. Once fixed, #619 can be re-reviewed and approved to todo

[[2026-04-05]] Sun 12:45
## Architecture Re-Review

### Re-approval condition check
- Fix #628 dep on #621: RESOLVED. #621 architect deliberately chose incremental build (base tool first, tag param second). depends_on [621] is correct direction for enhancement. KISS/YAGNI validated.

### New finding
#622 AC references pick_tasks(limit=25, tag=scope) but only depended on #621 (no tag). Added depends_on #628 to #622 so tag param exists before orchestrator wiring.

Corrected chain: #620 (tests) then #621 (base) then #628 (tag) then #622 (wire) then #623/#629 (deprecate/cleanup) then #624 (planner eval).

### Updated Evaluation
All criteria PASS. Dependency correctness fixed: #628 direction accepted per #621 architect; #622 dep on #628 added.

### Challenge Results
Challenger: SKIP. Re-review of previously challenged task; only dep graph correction. Previous findings all addressed or tracked.

### Verdict: APPROVE
### Action: #622 dep on #628 added; backlog to todo

[[2026-04-05]] Sun 13:48
## Test-Writer Notes
- Non-implementation task (tagged quality) — no tests applicable.
- Passing through to builder.

[[2026-04-05]] Sun 16:06
Non-implementation task — no code changes needed. Passing through to review.
