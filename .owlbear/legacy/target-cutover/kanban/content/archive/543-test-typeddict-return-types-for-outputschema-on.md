---
id: 543
title: 'Test: TypedDict return types for outputSchema on mcp-project'
status: archived
priority: medium
created: 2026-04-02 07:53:54.895174+02:00
updated: 2026-04-04 17:49:43.537522+02:00
started: 2026-04-02 07:54:11.386398+02:00
completed: 2026-04-04 17:49:43.537522+02:00
tags:
- scope:mcp
- ' type:test'
- ' test'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [x] Schema-pinning test: `fn_metadata.output_schema` for `project_info` has top-level `properties` with keys: name, type, project_path, owlbear_path, created_at (all `type: string`)
- [x] Schema-pinning test: `fn_metadata.output_schema` for `project_list` items schema contains `name` and `path` properties (inside FastMCP `result` wrapper)
- [x] ToolError test: `project_info` raises `ToolError` (from `mcp.server.fastmcp.exceptions`) when `project_file is None`
- [x] ~~All new tests fail (RED phase)~~ Pipeline note: implementation was committed (df21f2f) before RED-phase review. AC1-AC3 verified with 15 passing tests.

## Design Notes

- Access `fn_metadata.output_schema` via `mcp._tool_manager._tools` (same pattern as mcp-kanban schema overrides)
- `project_info` returns TypedDict directly: fields at top-level `properties`
- `project_list` returns `list[TypedDict]`: fields inside FastMCP `{result: {items: ...}}` wrapper
- Test file: `packages/mcp-project/tests/test_typeddict_outputschema_542.py`

Test-Writer Notes

- Task type: type:test/test - non-implementation pass-through (Step 1a).
- Test file: packages/mcp-project/tests/test_typeddict_outputschema_542.py
- All 15 tests already present and PASSING (implementation committed in df21f2f before RED-phase review per task body note).
- AC1 project_info schema: 6 tests in TestFromAC_ProjectInfoOutputSchema - verified PASS
- AC2 project_list items schema: 4 tests in TestFromAC_ProjectListOutputSchema - verified PASS
- AC3 ToolError when project_file is None: 3 tests in TestFromAC_ProjectInfoToolError - verified PASS
- pytest: 15 passed in 0.78s, no gaps.
- Pass-through to in-progress. Builder has no additional work.

[[2026-04-04]] Sat 15:49
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

pytest packages/mcp-project/tests/test_typeddict_outputschema_542.py: 15 passed in 0.78s

[[2026-04-04]] Sat 16:25
## Review Evidence

### Test Results
- pytest: 15 passed, 0 failed (independently verified)

### Lint: Clean
- ruff check packages/mcp-project/src/ + test file: All checks passed

### Coverage
- Test-only pass-through task. No source files changed in this cycle. AC-relevant paths (TypedDict schema, ToolError raise) exercised by the 15 tests.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: project_info top-level properties with 5 string fields | 6 tests in TestFromAC_ProjectInfoOutputSchema | Yes — revert TypedDict → generic wrapper fails test_project_info_output_schema_has_properties_key; remove any field fails its dedicated test | COVERED |
| AC2: project_list items schema has name + path | 5 tests in TestFromAC_ProjectListOutputSchema | Yes — untyped dict → empty properties fails test_project_list_output_schema_has_items | COVERED |
| AC3: project_info raises ToolError when project_file is None | 3 tests in TestFromAC_ProjectInfoToolError | Yes — string return fails raises test; wrong exception type also fails | COVERED |

#### Security Review
No issues — no hardcoded secrets, no injection vectors, no path traversal, no insecure deserialization, no new dependencies, no credential leakage in error messages.

#### Test Integrity
No TestFromAC modifications by builder — zero file changes in packages/mcp-project/ (confirmed via changed-files diff).

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Exact value comparisons throughout (type == "string", specific keys, pytest.raises on ToolError) |
| Negative/error-path coverage | STRONG | AC3 tests raise path, no-silent-string path, and error message content |
| Mutation resistance | STRONG | All 3 AC violations would surface as test failures |
| Test independence | STRONG | No shared mutable state, _get_tool_obj() and _make_mcp_ctx() called fresh per test |
| Descriptive test names | STRONG | All names describe exact assertion |

#### Data Safety
No issues (test file only).

#### Implementation-Aware Gaps
- AC3 broad except in test_project_info_does_not_return_string handles non-ToolError exceptions vacuously — companion test_project_info_raises_tool_error_when_no_project_file closes the gap. Complete coverage as a pair.
- No untested paths relevant to AC.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Assessment | CLEAN (pass-through task) |

### Pass 2 — INFORMATIONAL
- Design note states project_list schema is "inside FastMCP result wrapper" — actual implementation uses direct array schema override (no wrapper). Tests handle both shapes via _get_items_schema() helper. Tests are correct; design note is stale. No action needed.
- Test-writer note says 4 tests for AC2 but there are 5. Count error, no impact.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: project_info top-level properties 5 string fields | server.py ProjectInfoResult TypedDict + pytest 15/15 | TestFromAC_ProjectInfoOutputSchema (6 tests) | PASS |
| AC2: project_list items schema name + path | server.py manual output_schema override + pytest 15/15 | TestFromAC_ProjectListOutputSchema (5 tests) | PASS |
| AC3: ToolError when project_file is None | server.py raises ToolError + pytest 15/15 | TestFromAC_ProjectInfoToolError (3 tests) | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-04]] Sat 16:28
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task; no source files changed. TypedDict implementation was in prior commit df21f2f, not this task. |
| 2 | Module docstrings | No | N/A | No Python source modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns or sources cited in task body or research. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced for this task. |

### Files Updated
None — no docs impact.

### Scratch Files
None found (`docs/scratch/543-*`).

### Verdict
No documentation impact. Checklist complete.

[[2026-04-04]] Sat 17:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: project_info schema 5 string fields | 7 tests in TestFromAC_ProjectInfoOutputSchema, all PASS | PASS |
| AC2: project_list items schema name+path | 5 tests in TestFromAC_ProjectListOutputSchema, all PASS | PASS |
| AC3: ToolError when project_file is None | 3 tests in TestFromAC_ProjectInfoToolError, all PASS | PASS |

### Test Results
- pytest (task): 15 passed in 0.66s
- pytest (full suite): 2784 passed, 403 failed (all pre-existing, 0 in mcp-project scope)
- ruff: All checks passed

### Reviewer Evidence: Present, detailed, PASS (.97). Trusted.
### Architect Quality: 4/5
### Deduction Breakdown
- 3/3 AC with evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction
- Reviewer present and thorough: no deduction
- Full-suite 0 in-scope failures: no deduction
### Confidence: .98
### Action: archive
