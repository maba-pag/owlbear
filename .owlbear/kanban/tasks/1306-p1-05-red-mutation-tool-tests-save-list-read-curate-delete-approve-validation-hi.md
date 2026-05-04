---
id: 1306
title: 'P1-05: RED — Mutation tool tests (save, list, read, curate, delete, approve
  — validation + hints)'
status: in-progress
priority: needed
created: 2026-05-04T01:32:18.531671+00:00
updated: 2026-05-04T15:48:03.123251+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1305
blocked: false
block_reason:
claimed_at: 2026-05-04T15:48:03.123251+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Tests assert save_memory creates entry with state=pending, returns guidance hint (td:2)
- [ ] Tests assert list_memories returns metadata without body, sorts pending-first by created_at, filters by state/categories/scope_agents (td:2)
- [ ] Tests assert read_memory returns full entry by ID, errors on invalid/deleted IDs (td:2)
- [ ] Tests assert curate_memory validates: title non-empty, content <=1024, confidence [0.7,1.0], categories >=1 (td:2)
- [ ] Tests assert curate_memory returns correct guidance hint per state transition (td:2)
- [ ] Tests assert delete_memory returns correct hint for hard-delete vs soft-delete (td:2)
- [ ] Tests assert approve_memory only works on curated entries, errors on other states (td:2)
- [ ] Tests assert OWLBEAR_MEMORY_CALLER env var has no effect (access control removed) (td:1)
- [ ] Tests assert MEMORY_TOOLS_EXCLUDE env var has no effect (access control removed) (td:1)
- [ ] Tests assert validation errors return teaching messages (Brief guidance hints table) (td:2)
- [ ] All tests fail at assertion/method level — no collection-time ImportError (td:0)

## Scope

- In: 6 mutation tools (save, list, read, curate, delete, approve), parameter validation, guidance hints
- Out: recall_memory (separate task #1308/#1309), git integration, consumer wiring

## Structural Constraint

Tests for not-yet-existing functions (save_memory, list_memories, read_memory, approve_memory) MUST use localized import inside test methods (try/except or pytest.importorskip pattern) so each AC class produces per-method failures, not a collection-time ImportError that blocks sibling tests. Follow predecessor pattern from #1304.

[[2026-05-04]]
## Research

Research gate passed — T1 autonomous, no blockers.

**RED guarantees (6 mechanisms):**
1. `save_memory`, `list_memories`, `read_memory`, `approve_memory` — ImportError (functions don't exist)
2. `curate_memory`/`delete_memory` exist but return plain dicts without `"hint"` key
3. `OWLBEAR_MEMORY_CALLER` env var still active in server.py `app_lifespan`/`_require_role`
4. `MEMORY_TOOLS_EXCLUDE` env var still applies tool exclusions
5. Validation errors return raw Pydantic `str(exc)`, not teaching messages from Brief
6. No `list_memories` (metadata-without-body) or `read_memory` (by-ID) functions exist

**Test file:** `tests/test_mutation_tools_1306.py`
**Pattern:** Same as test_memory_schema_1302 and test_state_machine_1304 — mock MemoryEngine in tmp_path, mock MCP context, import from `owlbear_mcp_memory.tools`

**Sources:** Brief (.owlbear/briefs/draft-memory-mcp-ux/brief.md), existing tools.py, server.py, predecessor test files
**Follow-up tasks:** None needed — #1307 (GREEN) already exists as the implementation counterpart
**Decision requests:** None
[[2026-05-04]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only — single file covering 6 mutation tools |
| Interface clarity | PASS | Function names, return shapes (hint key), validation rules all explicit in AC |
| Dependency correctness | PASS | #1305 archived (done); state machine implementation complete |
| Module layering | PASS | Tests import from owlbear_mcp_memory.tools — correct direction |
| TDD compliance | PASS | This IS the RED phase task; GREEN counterpart #1307 exists |
| KISS/YAGNI | PASS | Minimal scope — tests only, no abstractions |
| Premise challenge | PASS | Required for GREEN #1307 to have verifiable target |
| Pattern consistency | PASS | Follows established pattern from #1302 and #1304 |
| Security surface | N/A | Test-only task |
| Single domain | PASS | mcp-memory only |

### Challenge Results
- Challenger: reconsider (0.64)
- Architect response: Accepted 2 of 4 concerns, rebutted 2
  - ACCEPTED: Added "sorts pending-first by created_at" to AC2 (brief-mandated sorting was missing)
  - ACCEPTED: Refined AC11 and added Structural Constraint section requiring localized imports (no collection-time ImportError)
  - REBUTTED: Access-control AC is correctly scoped — tests verify env vars don't gate, which is the right RED assertion for "access control removed"
  - REBUTTED: Delta underestimation is about GREEN complexity (#1307's problem), not RED test scope

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC2 (added sorting), AC11 (per-method failure), added Structural Constraint section. Advanced to todo.
[[2026-05-04]]
## Test-Writer Notes

**Test file:** `tests/test_mutation_tools_1306.py`
**Result:** 33 tests, all FAIL — RED confirmed. Ruff: clean (exit 0).

### Classes and test counts

| Class | AC | Tests | Failure mode |
|---|---|---|---|
| `TestFromAC_SaveMemory` | AC1 | 4 | `save_memory` not in tools → `pytest.fail` |
| `TestFromAC_ListMemories` | AC2 | 5 | `list_memories` not in tools → `pytest.fail` |
| `TestFromAC_ReadMemory` | AC3 | 4 | `read_memory` not in tools → `pytest.fail` |
| `TestFromAC_CurateMemoryValidation` | AC4 | 4 | Validation raises but message lacks teaching keywords (`non-empty`, `split`, `between`, `provide`) |
| `TestFromAC_CurateMemoryHint` | AC5 | 3 | `curate_memory` return dict has no `hint` key → `AssertionError` |
| `TestFromAC_DeleteMemoryHint` | AC6 | 3 | `delete_memory` return dict has no `hint` key → `AssertionError` |
| `TestFromAC_ApproveMemory` | AC7 | 5 | `approve_memory` not in tools → `pytest.fail` |
| `TestFromAC_CallerEnvVarNoEffect` | AC8 | 1 | `_require_role` enforces curator → unexpected `ToolError` |
| `TestFromAC_ToolExcludeEnvVarNoEffect` | AC9 | 1 | `_apply_tool_exclusions` still exists → `AssertionError` |
| `TestFromAC_ValidationTeachingMessages` | AC10 | 3 | `save_memory` not in tools → `pytest.fail` |

### AC coverage

| AC | Covered | Tests |
|---|---|---|
| AC1: save_memory creates pending + hint | ✓ | 4 |
| AC2: list_memories metadata-only, sort, filters | ✓ | 5 |
| AC3: read_memory full entry, invalid/deleted errors | ✓ | 4 |
| AC4: curate_memory validates with teaching messages | ✓ | 4 |
| AC5: curate_memory guidance hint per transition | ✓ | 3 |
| AC6: delete_memory hint hard/soft | ✓ | 3 |
| AC7: approve_memory curated-only | ✓ | 5 |
| AC8: OWLBEAR_MEMORY_CALLER no effect | ✓ | 1 |
| AC9: MEMORY_TOOLS_EXCLUDE no effect | ✓ | 1 |
| AC10: teaching messages in validation errors | ✓ | 3 |
| AC11: no collection-time ImportError | ✓ | (structural) |

**Structural constraint met:** Functions that don't exist (`save_memory`, `list_memories`, `read_memory`, `approve_memory`) use localized `try/except ImportError: pytest.fail(...)` inside each test method. No collection-time ImportError.