---
id: 845
title: Tests — TaskSummary adoption in server.py list_tasks
status: research
priority: needed
created: '2026-04-11T11:41:03.139406+00:00'
updated: '2026-04-12T21:01:06.507876+00:00'
tags:
- kanban
- phase-1
- type:test
- scope:mcp-kanban
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Test verifies `list_tasks` MCP tool response uses `TaskSummary` field set (not hand-built `_strip` dict pattern)
- Test verifies response includes: id, title, status, priority, tags, blocked, block_reason, claimed, parent, depends_on
- Test verifies response excludes: body, created, updated, claimed_by, claimed_at, file
- Test verifies `claimed` is a bool derived from `claimed_by` presence (boundary conversion preserved)
- Test verifies `outputSchema` JSON matches `TaskSummary` schema (not hard-coded dict)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. Supersedes stale #801 (which bundled TaskSummary model creation — now done). Scope: server.py `list_tasks` handler only.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (lines 104-180)

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Scoped to one handler's test suite |
| Interface clarity | PASS | AC specifies exact field sets |
| Dependency correctness | PASS | No dependencies listed, none needed for phase-1 independent task |
| Module layering | PASS | Tests only |
| TDD compliance | FAIL | Most AC tests pass GREEN immediately — no RED phase possible |
| KISS/YAGNI | FAIL | Duplicates existing coverage from #819 and migration tests |
| **Premise challenge** | **FAIL** | **Implementation already complete — see evidence below** |
| Pattern consistency | PASS | |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Premise Challenge — Evidence

All five AC items target behavior already implemented by commit `3703469e` (task #802):

1. **AC1: "list_tasks uses TaskSummary field set"** — Already true. `server.py:133` returns `[TaskSummary.model_validate(record.model_dump()) for record in records]`. Existing test in `test_mcp_adapter_slimming_819.py:175-189` already asserts `all(isinstance(item, TaskSummary) for item in result)`.

2. **AC2: "response includes id, title, status, priority, tags, blocked, block_reason, claimed, parent, depends_on"** — These are all `TaskSummary` model fields (models.py:95-104). Any test asserting presence would pass GREEN immediately.

3. **AC3: "response excludes body, created, updated, claimed_by, claimed_at, file"** — `body`, `claimed_by`, `claimed_at`, `file` are correctly excluded from `TaskSummary`. However, `created` and `updated` ARE present in `TaskSummary` (models.py:106-107) — the AC contradicts the actual model design. Tests for body/claimed_by/claimed_at/file exclusion would pass GREEN; tests for created/updated exclusion would test a model change not scoped to this task. `test_kanban_mcp_migration.py:233-242` already tests field stripping.

4. **AC4: "claimed is bool derived from claimed_by"** — Already implemented via `TaskSummary._coerce_claimed` validator (models.py:109-115). `test_kanban_mcp_migration.py:245-275` already tests this.

5. **AC5: "outputSchema matches TaskSummary schema"** — Already implemented at `server.py:147`: `TaskSummary.model_json_schema()`.

### AC3 Defect

AC includes `created` and `updated` in the exclusion list, but `TaskSummary` intentionally includes them (docstring: "excludes body and claimed_by" — no mention of timestamps). Removing them would be a separate model change requiring its own task.

### Sibling Task #846

The paired implementation task #846 was already REJECTED by a previous architect for the same reason — all AC items delivered by #802.

### Challenge Results
- Challenger: SKIPPED (REJECT verdict)

### Verdict: REJECT
### Action Taken: Moved to research. Task is redundant — all AC items already implemented by commit 3703469e (#802). Existing test coverage in test_mcp_adapter_slimming_819.py and test_kanban_mcp_migration.py already verifies TaskSummary adoption. AC3 contains a defect (created/updated listed as excluded but are present in TaskSummary by design).
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/task-845-tasksummary-test-redundancy.md
- Sources: 5 studied, 4 high-relevance
- Recommendation: Close as redundant — all AC items already implemented by commit 3703469e (#802) and covered by existing tests. No RED phase possible. (confidence: 0.92)
- Critical finding: 2 stale migration tests in test_kanban_mcp_migration.py::TestFromAC_ListTasks — 1 broken (TypeError from dict subscript on TaskSummary), 1 false positive (Pydantic v2 `in` operator always returns False on BaseModel)
- AC3 defect: `created`/`updated` listed as excluded but intentionally present in TaskSummary
- Follow-up tasks created: #851 (fix stale migration tests)
- Decision requests: none
[[2026-04-12]]
## Architecture Review (2nd pass)\n\n### Evaluation\n\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | Scoped to one handler's test suite |\n| Interface clarity | PASS | AC specifies exact field sets |\n| Dependency correctness | PASS | No dependencies, none needed |\n| Module layering | PASS | Tests only |\n| TDD compliance | FAIL | All AC items pass GREEN — no RED phase possible |\n| KISS/YAGNI | FAIL | Duplicates existing coverage in test_mcp_adapter_slimming_819.py |\n| Premise challenge | FAIL | Implementation complete (server.py:133, models.py:90-116), existing tests cover it |\n| Pattern consistency | PASS | |\n| Security surface | PASS | No new boundaries |\n| Single domain | PASS | scope:mcp-kanban only |\n\n### Premise Challenge — 2nd Verification\n\nIndependently re-verified all five AC items against current codebase:\n- AC1: server.py:133 uses TaskSummary.model_validate — test_mcp_adapter_slimming_819.py:176 covers this\n- AC2: All fields exist on TaskSummary model (models.py:95-107)\n- AC3: DEFECTIVE — created/updated are IN TaskSummary by design (models.py:106-107)\n- AC4: _coerce_claimed validator exists (models.py:109-115)\n- AC5: outputSchema uses TaskSummary.model_json_schema() at server.py:147\n\nFollow-up #851 (research) addresses the two stale migration tests found during initial research.\n\n### Challenge Results\n- Challenger: SKIPPED (REJECT verdict)\n\n### Verdict: REJECT\n### Action Taken: Moved to research (2nd rejection). Task is redundant — all AC items implemented by commit 3703469e (#802) with existing test coverage. No RED phase possible. AC3 defect (created/updated) unchanged. Recommend closing as duplicate/redundant.
[[2026-04-12]]
## Research (validation pass — 3rd cycle)

Validated existing research doc `.owlbear/research/task-845-tasksummary-test-redundancy.md` against current codebase. All findings confirmed current:

- server.py:135 still uses `TaskSummary.model_validate()` (AC1)
- models.py:90-116 still has TaskSummary with created/updated fields (AC3 defect intact)
- server.py:147-152 uses `TaskSummary.model_json_schema()` for outputSchema (AC5)
- Follow-up #851 at backlog — addresses stale migration tests

**Recommendation: Archive as redundant.** All AC items implemented by commit 3703469e (#802) with existing test coverage. No RED phase possible. This task has been independently validated 3 times (1 research + 2 arch reviews). Confidence: 0.95.

Follow-up tasks: #851 (already created, at backlog)
Decision requests: none
[[2026-04-12]]
## Architecture Review (3rd pass — loop-breaker)

### Independent Verification (4th total)

Verified all five AC items against current codebase:

| AC | Current Implementation | Existing Test |
|----|----------------------|---------------|
| AC1: list_tasks uses TaskSummary | server.py:135 returns TaskSummary.model_validate() | test_mcp_adapter_slimming_819.py:176-188 |
| AC2: response includes expected fields | models.py:95-104 defines all fields | test_mcp_adapter_slimming_819.py:187 (isinstance check) |
| AC3: response excludes body/created/updated/claimed_by/claimed_at/file | TaskSummary has none of these fields | test_kanban_mcp_migration.py:230-248 (false-positive, see #851) |
| AC4: claimed is bool from claimed_by | models.py:109-115 _coerce_claimed validator | test_kanban_mcp_migration.py:249-275 |
| AC5: outputSchema matches TaskSummary | server.py:147-152 uses model_json_schema() | (implicit via MCP schema) |

### AC3 Correction

Prior reviews stated created/updated ARE in TaskSummary — this was incorrect. Current models.py:90-116 shows TaskSummary has exactly: id, title, status, priority, tags, blocked, block_reason, claimed, parent, depends_on. No created/updated fields. AC3 is now factually correct, but all assertions would still pass GREEN because the implementation is already complete.

### Loop Analysis

This task has completed 4 full validation cycles (2 research + 3 arch reviews) with consistent conclusion: ALL AC items are implemented and tested. No RED phase is possible. Follow-up #851 addresses the stale migration test false-positives found during research.

### Verdict: REJECT (RECOMMEND ARCHIVE)

This task is redundant. All AC items were delivered by commit 3703469e (#802). Continuing to cycle it through the pipeline wastes agent capacity. The task should be ARCHIVED, not researched again.

### Challenge Results
- Challenger: SKIPPED (REJECT verdict — 3rd iteration)