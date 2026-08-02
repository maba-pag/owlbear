---
id: 1269
title: 'P1-03: Implement MemoryEntry Pydantic model'
status: archived
priority: medium
created: 2026-05-02T03:43:31.714748+00:00
updated: 2026-05-02T13:29:21.404998+00:00
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

[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped pass: pytest 45 passed, 0 failed, 0 skipped on `tests/test_mcp_memory_1269.py` and `tests/test_memory_models_1268.py`

### Lint
- ruff clean on `serve/mcp-memory/src/owlbear_mcp_memory/models.py`, `tests/test_mcp_memory_1269.py`, and `tests/test_memory_models_1268.py`

### Coverage
- `owlbear_mcp_memory.models`: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC / scope line | Evidence | Would fail if violated? | Verdict |
|---|---|---|---|
| AC1: All tests from #1268 pass GREEN | quality-runner green run included `tests/test_memory_models_1268.py` | Yes | COVERED |
| AC2: confidence in [0.7, 1.0] | `models.py:33` plus `tests/test_memory_models_1268.py:176-224` | Yes | COVERED |
| AC3: Category enum has exactly 9 values | `models.py:11-20` currently has 9 literals, but `tests/test_memory_models_1268.py:140-158` only proves listed examples | No — adding a 10th value would stay green | LAX |
| AC4: State enum has exactly 4 values with pending default | `models.py:22,34` plus `tests/test_memory_models_1268.py:74-124` prove default + known values | No — adding a 5th state would stay green | LAX |
| AC5: No SQLite references remain in models.py | direct grep found no `sqlite` / `SQLite` matches in `models.py`, but `tests/test_mcp_memory_1269.py` header documents the inspection test was removed | No surviving TestFromAC proof | MISSING |
| Scope: id must be UUIDv4 | `models.py:58-71`; `tests/test_mcp_memory_1269.py:74-82` reject non-canonical forms | No — canonical wrong-version / wrong-variant UUIDs are not tested | LAX |
| Scope: created_at / updated_at must be ISO timestamps | `models.py:74-79`; `tests/test_mcp_memory_1269.py:96-136` reject bad / empty / integer strings | No — date-only or timezone-less values would stay green | LAX |

#### Security Review
- No security issues found in the schema-only module.

#### Test Integrity
- No visible weakened assertions in the current `TestFromAC_*` bodies.
- Diff-level immutability proof is unavailable in this environment, so this check remains low-confidence.

#### Test Quality
- WEAK. Exact-cardinality contracts (9 categories / 4 states) are not discriminated by the current assertions.
- WEAK. Strict-format contracts for UUIDv4 and ISO timestamps are only partially exercised.

#### Data Safety
- No data-safety issues found in `models.py`.

#### Implementation-Aware Test Gaps
- `models.py:75-77` accepts any value parseable by `datetime.fromisoformat()` after `Z` normalization. That predicate is broader than the task’s “ISO timestamps” wording and is not constrained by current tests.
- No test proves rejection of canonical non-v4 or wrong-variant UUIDs even though the validator at `models.py:58-71` encodes those bits.
- No test proves exclusivity for the category/state cardinality requirements.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section. No prior `## Review Evidence` section.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All tests from #1268 pass GREEN | quality-runner: 45 passed, 0 failed, 0 skipped | `tests/test_memory_models_1268.py` | PASS |
| MemoryEntry validates confidence in [0.7, 1.0] | `models.py:33`; boundary tests in `tests/test_memory_models_1268.py` | `tests/test_memory_models_1268.py` | PASS |
| Category enum has exactly 9 values | `models.py:11-20` currently has 9 literals; proof quality is lax | `tests/test_memory_models_1268.py:140-158` | PASS |
| State enum has exactly 4 values with pending default | `models.py:22,34`; default and named-state tests pass; exact-cardinality proof is lax | `tests/test_memory_models_1268.py:74-124` | PASS |
| No SQLite references remain in models.py | direct grep: no `sqlite` / `SQLite` matches in `models.py` | none surviving | PASS |
| Scope: id is UUIDv4 | `models.py:58-71` enforces canonical UUIDv4 regex | `tests/test_mcp_memory_1269.py:45-82` | PASS |
| Scope: created_at / updated_at are ISO timestamps | validator at `models.py:75-77` is broader than the contract and current tests do not pin it down | `tests/test_mcp_memory_1269.py:91-141` | FAIL |

### Deductions
- -0.04 diff-level `TestFromAC_*` immutability could not be proven in this environment
- -0.05 exact-cardinality proof for categories/states is lax
- -0.04 AC5 has no surviving `TestFromAC_*` coverage
- -0.05 UUIDv4 strictness is only partially proved
- -0.10 timestamp strictness is under-proved and the current validator likely accepts non-timestamp ISO forms

### Verdict
- FAIL -> todo
- Confidence: 0.67
- Reason: the scoped suite is green, but the review gate fails on proof quality and timestamp contract coverage. The next cycle needs stronger tests before a builder rerun can be trusted.

### Required Follow-up
- Add discriminating tests for exact category count remaining 9.
- Add discriminating tests for exact state count remaining 4.
- Add a direct assertion that `models.py` contains no `sqlite` / `SQLite` references.
- Add canonical wrong-version / wrong-variant UUID rejection cases.
- Add date-only and timezone-less timestamp rejection cases.
- After those tests exist, rerun the builder only if the strengthened suite fails against `models.py`.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 9 tests addressing reviewer's Required Follow-up gaps.
- Test file: tests/test_mcp_memory_1269.py
- New classes: TestFromAC_CategoryCardinality (1), TestFromAC_StateCardinality (1), TestFromAC_NoSQLiteReference (1)
- New methods added to existing classes: TestFromAC_IdValidation (+2), TestFromAC_TimestampValidation (+4)
- Total new tests: 9 | Regression guards (PASS): 5 | Failing (RED) tests: 4
- ruff: clean | commit: ad26ff55

### Retry gap coverage
| Reviewer Gap | New Test(s) | Result |
|---|---|---|
| Exact category count = 9 | TestFromAC_CategoryCardinality::test_category_enum_has_exactly_9_values | PASS (guard) |
| Exact state count = 4 | TestFromAC_StateCardinality::test_state_enum_has_exactly_4_values | PASS (guard) |
| AC5 no SQLite references | TestFromAC_NoSQLiteReference::test_no_sqlite_references_in_models_py | PASS (guard) |
| Wrong-version UUID (v1) | TestFromAC_IdValidation::test_uuid_v1_rejected | PASS (guard) |
| Wrong-variant UUID | TestFromAC_IdValidation::test_uuid_wrong_variant_rejected | PASS (guard) |
| Date-only timestamp rejection | TestFromAC_TimestampValidation::test_created_at_date_only_rejected, test_updated_at_date_only_rejected | FAIL (DID NOT RAISE) |
| Timezone-naive timestamp rejection | TestFromAC_TimestampValidation::test_created_at_timezone_naive_rejected, test_updated_at_timezone_naive_rejected | FAIL (DID NOT RAISE) |

### RED Evidence
- pytest exit 1: 4 failed, 16 passed — the 4 new timestamp boundary tests all "Failed: DID NOT RAISE ValidationError"
- ruff exit 0: clean
[[2026-05-02]]
## Builder Notes
- Implementation: updated serve/mcp-memory/src/owlbear_mcp_memory/models.py.
- Fixes applied:
  - Tightened timestamp validator to require a datetime separator (`T`/`t`) so date-only values are rejected.
  - Enforced timezone-aware timestamps by rejecting parsed datetimes with missing UTC offset.
  - Preserved existing UUIDv4 and other schema behavior; no interface changes.
- Tests: 54 passed, 0 failed, 0 skipped (scoped run on tests/test_mcp_memory_1269.py + tests/test_memory_models_1268.py).
- Coverage: 100% on owlbear_mcp_memory.models.
- Lint: ruff clean.
- Evidence summary: RED re-verified before edit (4 failing `TestFromAC_TimestampValidation` tests); GREEN verification passed after single-file fix.
- Commit: a97564f0.
[[2026-05-02]]
## Review Evidence
### Changed Scope
- Builder commit `a97564f0` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Diff-level file listing was not available through the current tool surface, so changed scope was reconstructed from the task body and verified in the workspace.
- Reconstructed builder scope: `serve/mcp-memory/src/owlbear_mcp_memory/models.py`.
- Downstream `MemoryEntry` usages in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` and `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` remain compatible because the field surface stays string-backed while validation is tightened.

### Test Results
- quality-runner scoped pass: pytest 54 passed, 0 failed, 0 skipped on `tests/test_mcp_memory_1269.py` and `tests/test_memory_models_1268.py`.

### Lint
- ruff clean on `serve/mcp-memory/src/owlbear_mcp_memory/models.py`, `tests/test_mcp_memory_1269.py`, and `tests/test_memory_models_1268.py`.

### Coverage
- `owlbear_mcp_memory.models`: 100%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC / scope line | Evidence | Would fail if violated? | Verdict |
|---|---|---|---|
| AC1: All tests from #1268 pass GREEN | quality-runner green run included `tests/test_memory_models_1268.py` | Yes | COVERED |
| AC2: MemoryEntry validates confidence in [0.7, 1.0] | `models.py:33` plus `test_confidence_at_min_boundary_valid`, `test_confidence_at_max_boundary_valid`, `test_confidence_below_min_raises`, and `test_confidence_above_max_raises` in `tests/test_memory_models_1268.py` | Yes | COVERED |
| AC3: Category enum has exactly 9 values | `models.py:11-20` plus `test_each_category_valid`, `test_invalid_category_raises`, `test_behavior_spelling_rejected` in `tests/test_memory_models_1268.py`, and `test_category_enum_has_exactly_9_values` in `tests/test_mcp_memory_1269.py` | Yes | COVERED |
| AC4: State enum has exactly 4 values with pending default | `models.py:22,34` plus `test_state_defaults_to_pending`, `test_state_curated_valid`, `test_state_approved_valid`, `test_state_deleted_valid`, `test_invalid_state_raises` in `tests/test_memory_models_1268.py`, and `test_state_enum_has_exactly_4_values` in `tests/test_mcp_memory_1269.py` | Yes | COVERED |
| AC5: No SQLite references remain in models.py | direct source read of `models.py` plus `TestFromAC_NoSQLiteReference::test_no_sqlite_references_in_models_py` in `tests/test_mcp_memory_1269.py` | Yes | COVERED |
| Scope: id is UUIDv4 | `models.py:56-71` plus `test_valid_entry_constructs` in `tests/test_memory_models_1268.py` and rejection tests `test_non_uuid_string_rejected`, `test_uuid_without_hyphens_rejected`, `test_uuid_with_braces_rejected`, `test_uuid_v1_rejected`, `test_uuid_wrong_variant_rejected` in `tests/test_mcp_memory_1269.py` | Yes | COVERED |
| Scope: created_at / updated_at are ISO timestamps | `models.py:72-88` plus valid `Z` timestamp construction in `test_valid_entry_constructs` and rejection tests `test_created_at_non_date_string_rejected`, `test_updated_at_non_date_string_rejected`, `test_created_at_integer_timestamp_rejected`, `test_updated_at_integer_timestamp_rejected`, `test_created_at_date_only_rejected`, `test_updated_at_date_only_rejected`, `test_created_at_timezone_naive_rejected`, `test_updated_at_timezone_naive_rejected` in `tests/test_mcp_memory_1269.py` | Yes | COVERED |

#### Security Review
- No security issues found in the schema-only module.

#### Test Integrity
- No visible weakened or removed `TestFromAC_*` assertions in the current workspace snapshot.
- Diff-level immutability proof for the builder commit was not available through the current tool surface; confidence reduced slightly rather than treating this as a defect.

#### Test Quality
- STRONG. The retry added exact-cardinality guards for categories and states, a direct source assertion for removal of SQLite references, and discriminating negative tests for wrong-version UUIDs plus date-only and timezone-naive timestamps.
- STRONG. The combined suite now proves both acceptance and rejection paths for every task-scoped validation branch.

#### Data Safety
- No data-safety issues found in `models.py`.

#### Implementation-Aware Test Gaps
- No significant untested paths remain in the task-scoped validator logic.
- Package behavior is consistent with the stricter timestamp contract: `tools.py` generates UTC `Z` timestamps via `_now_iso()`, and the memory-module brief/data proposal explicitly specifies ISO 8601 UTC timestamps with timezone.

#### Builder Process Quality
- CLEAN. Two `## Builder Notes` sections total indicate one retry cycle, and the second pass directly addressed the prior timestamp-proof gap.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All tests from #1268 pass GREEN | quality-runner: 54 passed, 0 failed, 0 skipped | `tests/test_memory_models_1268.py` | PASS |
| MemoryEntry model validates confidence in [0.7, 1.0] | `models.py:33` and the confidence boundary/error tests in `tests/test_memory_models_1268.py` | `TestFromAC_MemoryEntryModel` confidence tests | PASS |
| Category enum has exactly 9 values | `models.py:11-20` plus category-membership tests in `tests/test_memory_models_1268.py` and `test_category_enum_has_exactly_9_values` in `tests/test_mcp_memory_1269.py` | `test_each_category_valid`, `test_invalid_category_raises`, `test_category_enum_has_exactly_9_values` | PASS |
| State enum has exactly 4 values with pending default | `models.py:22,34` plus default/state validity tests in `tests/test_memory_models_1268.py` and `test_state_enum_has_exactly_4_values` in `tests/test_mcp_memory_1269.py` | `test_state_defaults_to_pending`, `test_invalid_state_raises`, `test_state_enum_has_exactly_4_values` | PASS |
| No SQLite references remain in models.py | direct source read of `models.py` and `tests/test_mcp_memory_1269.py:225` | `TestFromAC_NoSQLiteReference::test_no_sqlite_references_in_models_py` | PASS |
| Scope: id (UUIDv4) | `models.py:56-71` and UUID validity/rejection tests in `tests/test_memory_models_1268.py` and `tests/test_mcp_memory_1269.py` | `TestFromAC_IdValidation` + `test_valid_entry_constructs` | PASS |
| Scope: created_at, updated_at (ISO timestamps) | `models.py:72-88`, UTC examples in the memory brief, `_now_iso()` in `tools.py`, and timestamp rejection tests in `tests/test_mcp_memory_1269.py` | `TestFromAC_TimestampValidation` + `test_valid_entry_constructs` | PASS |

### Deductions
- -0.03 diff-level `TestFromAC_*` immutability could not be proven from the builder commit with the current tool surface.
- -0.02 changed-file scope was reconstructed from task evidence rather than a direct commit diff.

### Verdict
- PASS to docs
- Confidence: 0.95
- Reason: independent scoped evidence is fully green, the strengthened tests now discriminate the prior proof gaps, and the stricter timestamp validation matches both the live package behavior and the memory-module brief.

### Action
- Advance to docs.
[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/mcp-memory/README.md` Entry schema section accurately reflects categories, states, confidence, and scope_agents — no consumer-visible schema changes from validator tightening |
| 2 | Module docstrings | Yes | N/A | `models.py` module docstring and `MemoryEntry` class docstring are accurate; private validators need no public docstrings |
| 3 | External attribution | No | N/A | No external patterns referenced in builder notes |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/memory-layers.excalidraw` describes `serve/mcp-memory/src/**` — footer updated from `a6401e28` to `e87c9144` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation requested |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | IN (docstrings) | Verified — no docstring edits needed |
| `tests/test_mcp_memory_1269.py` | OUT | N/A |
| `tests/test_memory_models_1268.py` | OUT | N/A |
| `share/diagrams/memory-layers.excalidraw` | IN | Footer updated |

### Files Updated
- `share/diagrams/memory-layers.excalidraw` — footer: `Last verified: 2026-05-02 (e87c9144)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1269-*` scratch files found)
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All tests from #1268 pass GREEN | Scoped run: 54 passed (includes test_memory_models_1268.py) | PASS |
| MemoryEntry validates confidence [0.7, 1.0] | models.py:33 `Field(ge=0.7, le=1.0)` | PASS |
| Category enum has exactly 9 values | models.py:11-20 (9 literals) + test_category_enum_has_exactly_9_values | PASS |
| State enum has exactly 4 values with pending default | models.py:22,34 + test_state_enum_has_exactly_4_values | PASS |
| No SQLite references remain in models.py | Visual inspection: no sqlite/SQLite anywhere + TestFromAC_NoSQLiteReference | PASS |

### Test Results
- pytest (full suite): 3618 passed, 126 failed — 0 failures in task scope
- pytest (scoped): 54 passed, 0 failed
- ruff: 3 violations in unrelated modules; task scope clean

### Architect Quality: 4/5
AC lines are specific, testable, and complete. Minor gap: UUIDv4/timestamp requirements appeared in Scope section rather than as numbered AC lines, but test-writer and builder had no trouble interpreting them. Dependency graph (#1267→#1268→#1269) is logically sound.

### Commit Integrity
| Commit | Type | Role |
|--------|------|------|
| 7a1a7e45 | test: initial RED | test-writer |
| 518e14b1 | feat: initial GREEN | builder |
| ad26ff55 | test: retry gaps | test-writer |
| a97564f0 | fix: timestamp strictness | builder |
| e1266f59 | docs: diagram footer | doc-writer |

### Deduction Breakdown
- No AC lines without evidence: 0
- No lint violations in scope: 0
- AC quality 4/5 (> 3): 0
- Reviewer evidence present and detailed: 0
- No full-suite failures in task scope: 0
- -.02 environment limitation (diff-level immutability not independently verifiable)

### Confidence: .98
### Action: archive