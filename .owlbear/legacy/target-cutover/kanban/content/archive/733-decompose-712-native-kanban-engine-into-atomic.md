---
id: 733
title: 'Decompose #712: Native kanban engine into atomic subtasks (Phase 1-3)'
status: archived
priority: medium
created: 2026-04-09T03:49:14.6128637+02:00
updated: 2026-04-09T10:52:03.413364+02:00
started: 2026-04-09T10:52:03.413364+02:00
completed: 2026-04-09T10:52:03.413364+02:00
tags:
    - phase-3
    - infrastructure
    - kanban
depends_on:
    - 712
class: standard
---

## Objective

Break #712 (native kanban engine) into atomic TDD-paired subtasks across three phases.

Needs decomposition: The parent task spans engine design, YAML I/O, 8 board operations, compound ops, MCP server migration, and cleanup across 40+ seam locations.

## Input
- Brief: `.owlbear/briefs/draft-kanban-native/brief.md`
- Research: `.owlbear/research/native-kanban-engine.md`
- Seam inventory in research doc (Section 3b)
- Key decisions D1-D7 in task #712 body

## AC
- [ ] Phase 1 subtasks: config loader, task YAML I/O (ruamel.yaml round-trip), each of 8 operations, compound ops — each with TDD test file
- [ ] Phase 2 subtasks: MCP server migration (atomic switchover), test migration
- [ ] Phase 3 subtasks: remove binary, remove setup scripts, update docs/guides/skills (checklist from seam inventory)
- [ ] Dependency graph between subtasks reflects build order
- [ ] All subtasks are children of #712
- [ ] CRITICAL CONSTRAINT preserved: existing subprocess server must work throughout Phase 1

[[2026-04-09]] Thu 07:04
## Research

**Finding: Task is redundant — decomposition already complete.**

The architect review on #712 explicitly flagged: "Redundant task #733 — decomposition was already completed (#713-#732 exist). #733 should be closed as redundant."

### AC Validation

All 6 AC lines satisfied by existing subtask structure:
- **Phase 1** (16 tasks): #713-728 cover models, config, I/O, listing, CRUD, claiming, compound ops, activity logging — each as RED/GREEN TDD pair
- **Phase 2** (2 tasks): #729-730 cover MCP server migration RED/GREEN
- **Phase 3** (2 tasks): #731 (700-file round-trip test), #732 (cleanup sweep per seam inventory)
- **Dependency graph**: verified — models→config→I/O→(listing∥CRUD)→claiming→compound+activity→MCP→(integration∥cleanup)
- **All subtasks parent: #712**: confirmed
- **CRITICAL CONSTRAINT**: Phase 2 atomic switchover correctly preserves subprocess server during Phase 1

### Status
- #713: archived (complete), #714: todo, #715-#732: backlog
- Existing research doc: `.owlbear/research/native-kanban-engine.md`
- No new follow-up tasks needed — #713-#732 already exist
- No new research doc — existing doc covers the domain
- Tier: T1 (redundant task, no decisions needed)
- Recommendation: Archive this task as redundant (confidence: .95)

[[2026-04-09]] Thu 07:52
## Architecture Review

### Context
Decomposition task requesting breakdown of #712 into atomic subtasks. Research phase already identified this as redundant — decomposition was completed prior to this task reaching backlog.

### Decomposition Detection Override
Task body contains `Needs decomposition:` without `## Planning`, which normally triggers planner delegation. **Override justified:** Research section provides T1-confidence (.95) evidence that all 20 subtasks (#713-#732) already exist as children of #712. Delegating to the planner would produce no new work. Proceeding with architecture review of the AC instead.

### AC Assessment

| AC Line | Assessment | Evidence |
|---------|-----------|----------|
| Phase 1 subtasks: config loader, task YAML I/O, 8 operations, compound ops — each with TDD test file | SATISFIED | #713 (archived), #714-#728: models, config, I/O, listing, CRUD, claiming, compound ops, activity logging — all RED/GREEN TDD pairs |
| Phase 2 subtasks: MCP server migration, test migration | SATISFIED | #729 (RED), #730 (GREEN) — MCP server migration pair |
| Phase 3 subtasks: remove binary, update docs/guides/skills | SATISFIED | #731 (700-file round-trip test), #732 (cleanup sweep per seam inventory) |
| Dependency graph reflects build order | SATISFIED | Verified: models→config→I/O→(listing∥CRUD)→claiming→compound+activity→MCP→(integration∥cleanup) |
| All subtasks are children of #712 | SATISFIED | All 19 active tasks (#714-#732) confirmed parent=712. #713 archived with parent=712. |
| CRITICAL CONSTRAINT: subprocess server works throughout Phase 1 | SATISFIED | Phase 2 (#729-#730) performs atomic switchover. Phase 1 tasks operate on engine module only, no server.py changes. |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Decomposition only — no code changes |
| Interface clarity | N/A | Planning task, no interfaces |
| Dependency correctness | PASS | depends_on=[712] correct — parent task |
| Module layering | N/A | No code |
| TDD compliance | N/A | Planning task |
| KISS/YAGNI | PASS | Task is redundant — all work already done |
| Premise challenge | FAIL (redundant) | Task should not have been created; decomposition was already complete when #713-#732 were created. Not blocking — advancing as pass-through. |
| Pattern consistency | PASS | Follows decomposition task pattern |
| Security surface | N/A | No code changes |
| Single domain | PASS | Kanban planning domain only |

### Challenge Results
- Challenger: SKIPPED — redundant task, no design decisions to challenge
- Architect response: All 6 AC lines independently verified against board state

### Non-Implementation Tag
Task produces no testable Python code. Needs pass-through tag (e.g., `type:docs` or `type:config`). Downstream agents should treat as pipeline pass-through — all AC already satisfied by existing subtasks.

### Verdict: APPROVE (redundant — pipeline pass-through)
### Action Taken: Advanced #733 to todo. All AC already satisfied by existing subtasks #713-#732. Downstream agents should confirm board state and fast-track to archive. Redundancy noted for future retro.

[[2026-04-09]] Thu 08:13
## Test-Writer Notes
- Non-implementation task (planning/decomposition — no Python interfaces) — no tests applicable.
- AC describes only kanban task structure (subtask creation, dependency graph, board state) — all non-Python deliverables.
- Architecture review confirmed redundant pass-through: all 6 AC lines already satisfied by existing subtasks #713-#732.
- Passing through to builder.

[[2026-04-09]] Thu 08:17
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
- All 6 AC lines already satisfied by existing subtasks #713-#732 per research and architecture review.
- No tests, no files changed, no lint to run.

[[2026-04-09]] Thu 08:55
## Review Evidence

### Step 1 — Changed Files
No Python source files changed. Only the kanban task file itself (.owlbear/kanban/tasks/733-*.md) is the artifact. Confirmed via board state — task is a non-implementation planning/decomposition pass-through.

### Step 2 — Tests
N/A — no TestFromAC_* classes exist. Test-writer correctly skipped: AC describes only kanban board structure (subtask creation, dependency graph), not Python interfaces. No TestFromAC modifications possible.

### Step 3 — Lint
N/A — no Python files in scope.

### Step 4 — Coverage
N/A — no implementation.

---

### AC Compliance

**Independent board verification via list_tasks + show_task.**

| AC Line | Evidence | Status |
|---------|----------|--------|
| Phase 1 subtasks: config loader, task YAML I/O, 8 operations, compound ops — each with TDD test file | #713 (archived), #714-#728 confirmed parent=712: models RED/GREEN, config RED/GREEN (#715-#716), I/O RED/GREEN (#717-#718), listing (#719-#720), CRUD (#721-#722), claiming (#723-#724), compound ops (#725-#726), activity logging (#727-#728). All tagged type:test for RED tasks. | PASS |
| Phase 2 subtasks: MCP server migration (atomic switchover), test migration | #729 RED (replace _run_kanban with engine), #730 GREEN (wire KanbanEngine into server.py) — confirmed parent=712, depends_on chains correct. | PASS |
| Phase 3 subtasks: remove binary, remove setup scripts, update docs/guides/skills | #732 "Cleanup sweep — remove binary refs, update docs/guides/skills/setup" — confirmed parent=712, tagged type:docs; #731 "700-file round-trip parity test" — confirmed parent=712. | PASS |
| Dependency graph reflects build order | Verified: #715 depends=[714], #717 depends=[714], #718 depends=[717,716], #719 depends=[718], #721 depends=[718], #723 depends=[722], #725 depends=[724,720], #727 depends=[722], #729 depends=[726,728], #730 depends=[729], #731 depends=[730], #732 depends=[730]. Build order correct. | PASS |
| All subtasks are children of #712 | All #713-#732 list_tasks output shows parent=712. #713 is archived with parent=712. 19 active + 1 archived = 20 subtasks confirmed. | PASS |
| CRITICAL CONSTRAINT: subprocess server works throughout Phase 1 | Phase 2 (#729-#730) performs atomic switchover. Phase 1 tasks (#713-#728) scoped to engine module only (tagged scope:mcp-kanban). No server.py changes occur in Phase 1. Design confirmed in #712 architecture review. | PASS |

---

### Pass 1 — CRITICAL
- **TestFromAC coverage**: 0 TestFromAC_* classes — legitimate, correctly skipped for non-implementation task.
- **TestFromAC integrity**: N/A — no tests to modify.
- **Security surface**: No code changes. Security requirements (safe YAML, path containment, slug allowlist, Windows reserved filename rejection) correctly delegated to child subtasks per brief spec.
- **Builder process quality**: Single pass-through note, accurate, no overclaiming.

### Pass 2 — INFORMATIONAL
1. AC1 "each of 8 operations" — operations are grouped (show_task folded into CRUD, pick_tasks into listing/CRUD). Grouping is an architectural choice, not an AC violation — TDD test files will cover all 8 operations within their scope. Approved by architect on #712.
2. #731 dependency ordering issue (should depend on Phase 1 Green #726/#728, not Phase 2 Green #730) — flagged by architect, deferred to #731's own review. Not a #733 concern.
3. Task is genuinely redundant (decomposition was already complete at creation). Retro note for planner calibration — the researcher should have surfaced redundancy before creating #733, rather than creating a task that flows through the full pipeline to be closed as redundant. Minor process cost only.

---

### Deductions
- Start: 1.00
- No tests for non-impl task: 0 (legitimate)
- All 6 AC lines independently verified: 0
- Minor redundancy cost (pipeline throughput waste): -.04
- Retro note: researcher created #733 after decomposition was complete — planner/researcher coordination gap

### Confidence: .96 → PASS

[[2026-04-09]] Thu 09:07
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Planning/decomposition pass-through — no Python code created or modified. No behavior or convention changes. copilot-instructions.md unchanged. |
| 2 | Module docstrings | No | N/A | No Python source files touched. Confirmed by review evidence: zero changed files. |
| 3 | External attribution | No | N/A | No external repo patterns or articles used. Decomposition derived from existing research doc and board state only. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/native-kanban-engine.md` exists — confirmed. Linked from task body. No new follow-up tasks needed (all 20 subtasks #713-#732 already existed). |

### Files Updated
None — no docs impact. All AC was satisfied by existing board state.

### Scratch Files
No `.owlbear/scratch/733-*` files found — nothing to clean.

### Verdict
No docs impact. Non-implementation redundant pass-through. All checklist items N/A or verified. Advancing to done.

[[2026-04-09]] Thu 10:52
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Phase 1 subtasks: config, I/O, 8 ops, compound ops — TDD pairs | #713-#728 confirmed parent=712 via list_tasks + show_task. RED/GREEN pairs verified. | PASS |
| Phase 2 subtasks: MCP migration, test migration | #729-#730 confirmed parent=712. depends_on chains correct. | PASS |
| Phase 3 subtasks: remove binary, update docs | #731-#732 confirmed parent=712, tagged type:test / type:docs. | PASS |
| Dependency graph reflects build order | depends_on chains verified: models→config→I/O→(listing∥CRUD)→claiming→compound+activity→MCP→(integration∥cleanup) | PASS |
| All subtasks children of #712 | All 20 tasks (#713-#732) confirmed parent=712. #713-#714 archived, #715-#732 active. | PASS |
| CRITICAL CONSTRAINT: subprocess server works throughout Phase 1 | Phase 2 (#729-#730) atomic switchover. Phase 1 tasks scoped to engine module only — no server.py changes. | PASS |

### Test Results
- pytest: 3770 passed, 387 failed, 18 skipped, 3 errors — all failures pre-existing; no code changed by this task; zero regressions possible
- ruff: 5 pre-existing violations in serve/mcp-kanban/server.py and tests/test_server.py — not in task scope

### Architect Quality: 4/5
AC was specific and verifiable against board state (6 concrete lines). Minor issue: task was redundant — decomposition was already complete when #733 was created. Process coordination gap (researcher/planner), not an AC quality problem.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 6 PASS) → 0
- Lint violations in task scope: 0 → 0
- AC quality ≤ 3: No (4/5) → 0
- Missing reviewer evidence: No (present, detailed, PASS at .96) → 0
- Full-suite failures in task scope: 0 (no code changed) → 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a6e0dda | chore | .owlbear/kanban/tasks/733-*.md | #733 |
