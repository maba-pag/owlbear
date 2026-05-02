---
id: 1269
title: 'P1-03: Implement MemoryEntry Pydantic model'
status: review
priority: needed
created: 2026-05-02T03:43:31.714748+00:00
updated: 2026-05-02T07:45:49.903053+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1267
- 1268
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Implement the new MemoryEntry Pydantic model replacing the old SQLite-oriented schema. Must pass all tests from #1268.

Brief: see parent #1266

## Scope

**In scope:**
- Rewrite `serve/mcp-memory/src/owlbear_mcp_memory/models.py`
- 9-value category enum: knowledge, behaviour, pitfall, process, tool, goal, personality, preference, context
- 4-state enum: pending, curated, approved, deleted
- Confidence field with [0.7, 1.0] validator
- Required: id (UUIDv4), title (non-empty str), content (str), categories (list[Category], min 1), confidence, state, created_at, updated_at (ISO timestamps)
- Optional: scope_agents (list[str] | None)
- State defaults to "pending"

**Out of scope:**
- File I/O, slug generation, engine logic (handled by #1271)
- MCP tool integration (handled by #1273)
- pyproject.toml dep changes (if pyyaml needed, add in #1271)

## Acceptance Criteria

- [ ] All tests from #1268 pass GREEN
- [ ] MemoryEntry model validates confidence in [0.7, 1.0]
- [ ] Category enum has exactly 9 values
- [ ] State enum has exactly 4 values with "pending" default
- [ ] No SQLite references remain in models.py
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_mcp_memory_1269.py
- Classes: TestFromAC_IdValidation, TestFromAC_TimestampValidation
- Tests per category: happy 0, edge 2 (uuid without hyphens, uuid with braces), error 9 (non-uuid strings rejected, non-date strings rejected), boundary 0
- Total: 11 tests, all FAIL
- ruff: clean
- Commit: 7a1a7e45

## AC Coverage

| AC Line | Tests | Disposition |
|---------|-------|-------------|
| AC1: All tests from #1268 pass GREEN | — | Deferred to test_memory_models_1268.py; those tests pass against current models.py |
| AC2: MemoryEntry validates confidence [0.7, 1.0] | — | Fully covered in test_memory_models_1268.py |
| AC3: Category enum has exactly 9 values | — | models.py Literal already has exactly 9; test passes immediately → removed per RED-phase rule |
| AC4: State enum exactly 4 values, "pending" default | — | Covered in test_memory_models_1268.py (state default at line 75, all states at lines 85-100) |
| AC5: No SQLite references in models.py | — | models.py is already clean; inspection test passes immediately → removed per RED-phase rule |
| Scope: id (UUIDv4) | TestFromAC_IdValidation (5 tests) | FAIL — current id: str accepts arbitrary strings; non-UUID strings must raise |
| Scope: created_at, updated_at (ISO timestamps) | TestFromAC_TimestampValidation (6 tests) | FAIL — current fields are plain str; non-datetime strings must raise |

## RED Evidence
- pytest exit 1: 11 failed, 0 passed — all "Failed: DID NOT RAISE ValidationError"
- ruff exit 0: clean
- Commit: 7a1a7e45
[[2026-05-02]]
## Builder Notes
- Implementation: updated serve/mcp-memory/src/owlbear_mcp_memory/models.py.
- Fixes applied:
  - Added strict `id` validator requiring canonical UUIDv4 string format (`8-4-4-4-12`, version nibble `4`, variant nibble `[89ab]`), rejecting hyphenless and brace-wrapped forms.
  - Added `created_at`/`updated_at` ISO datetime validator using `datetime.fromisoformat` with `Z` normalization to `+00:00`.
  - Preserved existing schema contract (`str` field types) and retained legacy `approval_state` drop behavior.
- Tests: 45 passed, 0 failed, 0 skipped (scoped run on `tests/test_mcp_memory_1269.py` + `tests/test_memory_models_1268.py`).
- Coverage: 100% on `owlbear_mcp_memory.models`.
- Lint: ruff clean (after import ordering correction).
- Evidence summary: RED confirmed first (11/11 `TestFromAC_*` failed with "DID NOT RAISE ValidationError"); GREEN verification then passed fully with no lint violations.

Post-task reflection:
- Functional gap was isolated to format validation, allowing a single-file surgical implementation.
- Using validators instead of changing field types avoided downstream serialization/interface churn while satisfying AC.
- A small import-order lint issue required one additional scoped rerun; no further regressions were observed.