---
id: 712
title: 'Native kanban engine: replace kanban-md Go binary with Python engine'
status: done
priority: needed
created: 2026-04-09T03:16:18.2333914+02:00
updated: 2026-04-09T07:25:39.5155586+02:00
tags:
    - phase-3
    - infrastructure
    - kanban
claimed_by: frost-knoll
claimed_at: 2026-04-09T07:25:39.5155586+02:00
class: standard
---

## Objective

Replace the kanban-md Go binary dependency with a native Python board engine inside `serve/mcp-kanban/`. Eliminates platform-specific binary download, enables cross-platform (Mac/Linux/Windows), simplifies codebase by removing subprocess calls.

## Brief

See `.owlbear/briefs/draft-kanban-native/brief.md` for full Brief including:
- Problem statement, outcomes, approach, scope, risks
- Task file format spec, config.yml schema, activity.jsonl format
- KanbanEngine API surface, behavioral contracts to replicate
- Key decisions (D1-D7)

## Outcomes
1. Native Python board engine inside mcp-kanban replaces all subprocess calls
2. Behavioral compatibility — same 8 MCP tools, existing 700+ task files preserved
3. Cross-platform — Mac, Linux, Windows without binary artifacts

## Key Decisions
- D1: ruamel.yaml for lossless YAML round-trip
- D2: No file locking (YAGNI)
- D3: Compound ops (start_work/end_work) in engine
- D4: KISS — replace only, no new features
- D5: GUI deferred
- D6: Engine inside mcp-kanban (not separate package)
- D7: Orchestrator CLI out of scope

## Migration Phases
1. Engine modules + test suite (inside serve/mcp-kanban/)
2. MCP server migration (replace _run_kanban() with engine calls)
3. Cleanup sweep (remove binary, update docs/guides/skills)

## AC
- [ ] KanbanEngine class implements all 8 board operations natively
- [ ] All existing MCP tool tests pass with native engine
- [ ] 700+ existing task files load and round-trip without data loss
- [ ] config.yml, activity.jsonl, next_id handling preserved
- [ ] No kanban-md binary dependency anywhere in runtime code
- [ ] MCP server starts and works on Mac and Windows
- [ ] setup.ps1 binary download removed
- [ ] Docs, guides, and skills updated to remove binary references

[[2026-04-09]] Thu 03:24


## CRITICAL CONSTRAINT
The kanban MCP server is managing the tasks for its own replacement. The existing subprocess-based server MUST continue working throughout Phase 1 development. Phase 2 (MCP server migration) is an atomic switchover — old code works until the switch, then new code takes over. No half-migration state. If Phase 2 fails, revert to subprocess-based server.

[[2026-04-09]] Thu 03:49
## Research
- Research doc: .owlbear/research/native-kanban-engine.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Proceed with native Python engine replacement per Brief (D1-D7 validated) (confidence: .85)
- Key findings:
  - ruamel.yaml (D1) confirmed as only viable YAML library for lossless round-trip
  - Timestamp resolver must be disabled to preserve Go nanosecond timestamps as raw strings
  - 40+ binary reference locations catalogued in seam inventory (15 subprocess calls, 15+ test files, 4 docs, 2 setup scripts)
  - 3-phase migration plan validated; Phase 2 atomic switchover correctly handles self-referential risk
  - Task requires decomposition (too large for single task)
- Follow-up tasks created: #733 (decomposition into Phase 1-3 atomic subtasks)
- Decision requests: none (T1 — all decisions already resolved in Brief)
- Challenge: FALLBACK — skipped (validates existing Brief, no novel recommendation)

[[2026-04-09]] Thu 04:50
## Architecture Review

### Context
Parent epic for native kanban engine replacement. Already decomposed into 20 subtasks (#713-#732) covering 3 migration phases. Brief (`.owlbear/briefs/draft-kanban-native/brief.md`) and research (`.owlbear/research/native-kanban-engine.md`) are thorough. Architecture decisions D1-D7 validated by research. #713 already at `todo` with completed architecture review.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| KanbanEngine implements all 8 operations | PASS — covered by subtasks #719-728 (list, show, create, edit, move, start_work, end_work, pick_tasks via CRUD+compound+claiming) | None |
| Existing MCP tool tests pass | PASS — #729-730 cover MCP migration testing | None |
| 700+ file round-trip without data loss | PASS — #731 covers; **dependency ordering issue** (see Architecture Notes) | Fix during #731 arch review |
| config.yml, activity.jsonl, next_id preserved | PASS — #715-716 (config), #727-728 (activity), #721-722 (next_id in create) | None |
| No binary dependency in runtime | PASS — #730 removes subprocess, #732 removes binary artifacts | None |
| MCP server works on Mac and Windows | PASS — implicit in #730 (engine is pure Python); cross-platform is a design outcome | None |
| setup.ps1 binary download removed | PASS — #732 AC explicitly covers this | None |
| Docs/guides/skills updated | PASS — #732 covers all doc seams | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent epic; all work decomposed into 20 atomic subtasks |
| Interface clarity | PASS | KanbanEngine API specified in brief with behavioral contracts table |
| Dependency correctness | PASS (with caveat) | #731 round-trip test depends on #730 (MCP migration) but should depend on Phase 1 completion (#726/#728) instead — fix during #731's arch review |
| Module layering | PASS | Engine modules inside `serve/mcp-kanban/`, no upward imports |
| TDD compliance | PASS | Every operation has RED/GREEN pair in subtasks |
| KISS/YAGNI | PASS | D4 explicitly: replace only, no new features |
| Premise challenge | PASS | Prior research (#144) overridden by distribution ambition growth; well-justified in brief |
| Pattern consistency | PASS | Pydantic models, MCP server conventions, async subprocess patterns all examined |
| Security surface | PASS | Brief specifies: safe YAML loading only (no !!python tags), path containment, slug allowlist, Windows reserved filename rejection |
| Single domain | PASS | Kanban engine domain exclusively |

### Architecture Notes

1. **Seam count correction**: Research claims 15 `_run_kanban()` subprocess calls; actual codebase examination found **17 call sites** across 9 functions. Not blocking — subtask #730 will handle all of them during atomic switchover.

2. **Round-trip test ordering (#731)**: Currently depends on #730 (MCP migration GREEN). Should depend on Phase 1 completion (#726 compound ops GREEN and/or #728 activity logging GREEN). The 700-file round-trip test is a critical safety gate — it must validate the engine on real data BEFORE the MCP switchover, not after. **Action: fix dependency during #731's architecture review.**

3. **Redundant task #733**: The decomposition task #733 (at `research` status) was created by the researcher to trigger planner decomposition. The decomposition was already completed (#713-#732 exist). #733 should be closed as redundant.

4. **CRITICAL CONSTRAINT preserved**: The atomic switchover design in Phase 2 (#729-#730) correctly handles the self-referential risk — the kanban MCP server manages its own replacement tasks, so the subprocess server must work throughout Phase 1.

5. **Parent epic pipeline handling**: This task produces no direct testable Python code — all implementation is in children #713-#732. The test-writer should process this as a parent epic pass-through.

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation conducted across all 13 criteria; codebase verified (17 subprocess calls confirmed); decomposition structure validated; no concerns requiring formal challenge

### Verdict: APPROVE
### Action Taken: Approved parent epic #712 to todo. 20 subtasks (#713-#732) already decomposed across 3 phases. Noted #731 dependency fix needed (during its own arch review) and #733 redundancy.

[[2026-04-09]] Thu 05:25
## Test-Writer Notes
- Non-impl pass-through: parent epic — no direct testable Python code.
- All implementation is in children #713–#732 (3 migration phases, 20 subtasks).
- Architecture review explicitly flagged this as a test-writer pass-through.
- Passing through to builder.

[[2026-04-09]] Thu 05:47
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-09]] Thu 06:08
## Review Evidence

### Test Results
N/A — non-implementation parent epic pass-through. No test files exist for this task. Architecture review explicitly flagged: "This task produces no direct testable Python code — all implementation is in children #713-#732."

### Lint
N/A — no Python source files changed.

### Coverage
N/A — no implementation.

---

### Step 1 — Changed Files
Only the kanban task file itself was created (`.owlbear/kanban/tasks/712-native-kanban-engine-replace-kanban-md-go-binary.md`) as a new board artifact, along with child task files #713-#733 and research docs — all expected from the decomposition pipeline. Zero Python source files, test files, or production modules changed.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage
No TestFromAC_* classes exist — pass-through task, correctly skipped per condition.

#### AC Delegation Audit

| AC Line | Assigned To | Status |
|---------|-------------|--------|
| KanbanEngine implements all 8 operations | #719-728 (RED/GREEN pairs per operation) | DELEGATED |
| All existing MCP tool tests pass with native engine | #729-730 (MCP migration RED/GREEN) | DELEGATED |
| 700+ task files round-trip without data loss | #731 (integration test) | DELEGATED |
| config.yml, activity.jsonl, next_id preserved | #715-716 (config), #727-728 (activity), #721-722 (next_id) | DELEGATED |
| No binary dependency in runtime code | #730 (removes subprocess), #732 (removes binary artifacts) | DELEGATED |
| MCP server starts on Mac and Windows | #730 (pure Python switchover) | DELEGATED |
| setup.ps1 binary download removed | #732 AC explicitly covers | DELEGATED |
| Docs/guides/skills updated | #732 seam inventory checklist | DELEGATED |

All 8 AC lines properly delegated across 20 child subtasks. No gap.

#### 5.1 Security Review
No implementation code added. The task file is markdown. Security surface for child tasks (safe YAML, path containment, slug allowlist, Windows reserved filename rejection) is correctly specified in the Brief and delegated to implementation subtasks. CLEAN.

#### 5.2 TestFromAC Integrity
No TestFromAC_* tests exist — conditional check skipped. CLEAN.

#### 5.3 Test Quality
N/A — no tests for pass-through epic.

#### 5.4 Data Safety
No code changed. CLEAN.

#### 5.5 Implementation-Aware Gap Analysis
N/A — no implementation in this task.

#### 5.6 Necessity Check
N/A — no new dependencies or integrations.

#### 5.7 Builder Process Quality
Single builder notes section: "Non-implementation task — no code changes needed. Passing through to review." CLEAN.

---

### Pass 2 — INFORMATIONAL
1. Architecture review noted #733 (decompose #712) is redundant — decomposition (#713-#732) already completed. Cleanup action for orchestrator. Not a review concern.
2. Architecture review noted #731 dependency ordering issue (should depend on Phase 1 completion, not #730). Flagged for resolution during #731's architecture review. Not a #712 review blocking concern.

---

### AC Compliance Summary

| AC | Evidence | Status |
|----|----------|--------|
| All 8 AC lines | Properly delegated to child subtasks #713-#732 per architecture review mapping table | DELEGATED — PASS |

---

### Deductions
None. Pass-through designation is legitimate, documented by architecture review, and the AC delegation is complete and traceable.

### Confidence: .96 → PASS

PASS #712 -> docs | confidence .96

[[2026-04-09]] Thu 06:18
## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Parent epic with no direct implementation. Binary replacement delegated to child #732 (which owns all doc/guide seam cleanup). No current behavior changed. |
| 2 | Module docstrings | No | N/A | Zero Python source files created or modified. Review Evidence confirms: "Zero Python source files, test files, or production modules changed." |
| 3 | External attribution → sources/overview.md | Yes | ✓ PRESENT | `.owlbear/sources/overview.md` already contains "Native Kanban Engine (Task #712)" section with two rows: ruamel.yaml 0.19.1 and kanban-md v0.33.0. No update needed. |
| 4 | CLI changes → README.md | No | N/A | No CLI changes in this task. |
| 5 | Research doc | Yes | ✓ VERIFIED | `.owlbear/research/native-kanban-engine.md` exists and is linked in task body. Follow-up task #733 (decomposition) created. |
| 6 | Scratch files | — | ✓ CLEAN | No `.owlbear/scratch/712-*` files found. |

### Files Updated
None — no docs updates required. Sources attribution was already written during research pipeline step.

### Commit
Skipped — no files updated.

### Verdict
No docs impact from this parent epic. All doc/guide/skill seam cleanup is correctly delegated to child #732 per architecture review and AC mapping table.
