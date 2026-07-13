---
id: 694
title: Fix 3 MCP tool error signaling bugs and tighten convention docs
status: archived
priority: medium
created: 2026-04-08T21:24:23.3457999+02:00
updated: 2026-04-09T05:42:04.7119722+02:00
started: 2026-04-09T05:42:04.7119722+02:00
completed: 2026-04-09T05:42:04.7119722+02:00
tags:
    - scope:mcp
    - ' type:refactor'
    - ' source:research'
depends_on:
    - 680
class: standard
---

## Context

Research #680 audited all 28 MCP tools and found 3 error-signaling bugs:

1. **Double-prefix (list_sources):** `raise ToolError("error: source store not available")` — remove "error: " prefix; ToolError already sets `isError: true`.
2. **Double-prefix (get_stats):** Same pattern — `raise ToolError("error: graph store not available")`.
3. **Mixed pattern (set_approval_state):** Raises `ToolError` for missing entry but returns `"error: ..."` for invalid transitions → unify to ToolError for all error paths.

Also: tighten convention docs to eliminate ambiguity about when each pattern applies.

See: `.owlbear/research/mcp-tool-error-signaling-680.md`

## Acceptance Criteria

- [ ] AC1: `list_sources` ToolError message does not start with `"error: "` prefix
- [ ] AC2: `get_stats` ToolError message does not start with `"error: "` prefix
- [ ] AC3: `set_approval_state` raises ToolError for invalid transitions (not error string)
- [ ] AC4: Tests updated for all 3 changes (test_null_safety_539, test_set_approval_state_569)
- [ ] AC5: r-architecture-standards SKILL.md updated with explicit guidance on double-prefix anti-pattern
- [ ] AC6: h-mcp-memory SKILL.md updated to reflect set_approval_state change

## Affected Files

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (list_sources, get_stats)
- `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` (set_approval_state)
- `serve/mcp-knowledge/tests/test_null_safety_539.py`
- `tests/test_set_approval_state_569.py`
- `share/skills/r-architecture-standards/SKILL.md`
- `share/skills/h-mcp-memory/SKILL.md`

[[2026-04-09]] Thu 00:57
## Research
- Research doc: .owlbear/research/mcp-error-signaling-fixes-694.md
- Sources: 6 studied, 5 high-relevance
- Recommendation: Proceed with all 6 AC items as specified — clean T1 bug fix (confidence: .90)
- Follow-up tasks created: none (task #694 covers all work)
- Decision requests: none

**Key findings:**
1. All 3 bugs confirmed in source code (double-prefix in list_sources/get_stats, mixed pattern in set_approval_state)
2. Test blast radius: 13 assertions across 3 files (not 2 — `serve/mcp-memory/tests/test_server.py` also needs 3 test updates, but is NOT listed in AC's affected files)
3. Runtime consumer (approve.py): unaffected — checks `result.isError` first, which covers ToolError responses via MCP transport
4. test_null_safety_539.py tests for list_sources/get_stats appear already broken — they expect error string returns but code raises ToolError

## Challenge Results
- Challenger: FALLBACK — trivial bug fix with clear scope, no design alternatives
- Confidence in original: .90
- Key challenges: none (no challenger invoked)
- Researcher response: N/A

[[2026-04-09]] Thu 01:41
## Architecture Review

### AC Assessment

| AC | Text | Assessment | Action |
|----|------|-----------|--------|
| AC1 | `list_sources` ToolError message no `"error: "` prefix | PRECISE — verified at server.py L236 | None |
| AC2 | `get_stats` ToolError message no `"error: "` prefix | PRECISE — verified at server.py L304 | None |
| AC3 | `set_approval_state` raises ToolError for invalid transitions | PRECISE — verified at tools.py L267-269; returns error string currently | None |
| AC4 | Tests updated (test_null_safety_539, test_set_approval_state_569) | **REFINED** — missing `serve/mcp-memory/tests/test_server.py` (3 invalid-transition tests at L162-197 assert `result.startswith("error:")` → must change to `pytest.raises(ToolError)`) | Updated to include all 3 test files |
| AC5 | r-architecture-standards SKILL.md updated | PRECISE | None |
| AC6 | h-mcp-memory SKILL.md updated | PRECISE | None |

### Refined AC4

`Tests updated for all 3 changes (serve/mcp-knowledge/tests/test_null_safety_539.py, tests/test_set_approval_state_569.py, AND serve/mcp-memory/tests/test_server.py — 3 invalid-transition tests at L162-197)`

### Affected Files (corrected)

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (list_sources, get_stats)
- `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` (set_approval_state)
- `serve/mcp-knowledge/tests/test_null_safety_539.py`
- `tests/test_set_approval_state_569.py`
- `serve/mcp-memory/tests/test_server.py` ← **ADDED** (3 invalid-transition tests)
- `share/skills/r-architecture-standards/SKILL.md`
- `share/skills/h-mcp-memory/SKILL.md`

### Builder Notes

- **Docstring update required**: `set_approval_state` docstring (tools.py L248) currently says "returns an 'error: ...' string for disallowed transitions" — this becomes false after AC3 and must be updated to say "Raises ToolError for disallowed transitions."
- **approve.py**: Research confirmed unaffected — checks `result.isError` first, which catches ToolError via MCP transport. No changes needed.
- **test_null_safety_539.py**: Research notes these tests may already be broken (expect error string returns but code raises ToolError). The fix corrects both production code (remove prefix) and tests (assert ToolError).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes address one concern: MCP error signaling consistency |
| Interface clarity | PASS | After AC4 refinement — all inputs/outputs specified |
| Dependency correctness | PASS | depends_on: [680] — archived/done |
| Module layering | PASS | Changes within MCP server modules, no new cross-module deps |
| TDD compliance | PASS | Test files listed per AC4 |
| KISS/YAGNI | PASS | Minimal scope — only fixes identified bugs + doc alignment |
| Premise challenge | PASS | All 3 bugs confirmed via read_file |
| Pattern consistency | PASS | Aligns with existing convention (ToolError for typed returns, no double-prefix) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cross-server but same bug class; splitting would over-fragment a T1 fix |

### Challenge Results

- Challenger: reconsider (0.32)
- Architect response: ACCEPTED in part, REBUTTED on 2 of 4 points
  - ACCEPTED: missing test_server.py in AC4 (corrected), docstring update needed (added as builder note)
  - REBUTTED: bugs unverified (confirmed via read_file, grep failed on multi-line pattern); approve.py risk (research doc Section 3c confirmed safe)
- Challenger overweighted already-addressed issues; core concerns resolved via refinement

### Verdict: APPROVE (REFINE then advance)
### Action Taken: Refined AC4 to include serve/mcp-memory/tests/test_server.py, corrected Affected Files, added builder notes for docstring and approve.py. Advanced to todo.

[[2026-04-09]] Thu 02:53
## Test-Writer Notes
- Test file: tests/test_mcp_error_signaling_694.py
- Classes: TestFromAC_ListSourcesErrorPrefix, TestFromAC_GetStatsErrorPrefix, TestFromAC_SetApprovalStateRaisesToolError
- Tests per category: happy 0, edge 0, error 11, boundary 0
- Total: 11 tests, all FAIL
- ruff: clean
- Commit: 7c66cfe

### AC Coverage

| AC | Tests | Failure reason |
|----|-------|---------------|
| AC1: list_sources no "error: " prefix | 2 | ToolError message is "error: source store not available" (has prefix) |
| AC2: get_stats no "error: " prefix | 2 | ToolError message is "error: graph store not available" (has prefix) |
| AC3: set_approval_state raises ToolError for 6 invalid transitions | 7 | DID NOT RAISE — function returns soft error string instead |
| AC4: test file updates | covered via new test file | — |
| AC5: r-architecture-standards SKILL.md | non-impl, no tests | — |
| AC6: h-mcp-memory SKILL.md | non-impl, no tests | — |

### Notes for Builder
- AC1/AC2 fix: remove "error: " prefix from ToolError message strings in server.py L236 and L304
- AC3 fix: replace `return f"error: transition from..."` in tools.py L267-269 with `raise ToolError(msg)`
- AC4: update test_null_safety_539.py (assert ToolError, check message prefix), test_set_approval_state_569.py (assert ToolError not string), serve/mcp-memory/tests/test_server.py (3 invalid-transition tests at L162-197 assert startswith "error:" → must change to pytest.raises(ToolError))
- Tools.py docstring at L248 must also be updated (says "returns error string" — becomes false after AC3 fix)

[[2026-04-09]] Thu 04:28
## Builder Notes

### Files Changed
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — removed `"error: "` prefix from ToolError message in `list_sources` (L236) and `get_stats` (L304)
- `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — replaced soft-error `return f"error: ..."` with `raise ToolError(msg)` for invalid transitions; updated docstring
- `serve/mcp-knowledge/tests/test_null_safety_539.py` — updated 2 tests (list_sources, get_stats null checks) from return-string assertions to `pytest.raises(ToolError)` + checked message; added ToolError import
- `tests/test_set_approval_state_569.py` — updated 6 invalid-transition tests + 1 error-format test to use `pytest.raises(ToolError)` (AC-T4 through AC-T10)
- `serve/mcp-memory/tests/test_server.py` — updated 3 invalid-transition tests (L162-197) to use `pytest.raises(ToolError)`
- `share/skills/r-architecture-standards/SKILL.md` — added explicit "Anti-pattern: double-prefix" section with correct/wrong examples
- `share/skills/h-mcp-memory/SKILL.md` — updated `set_approval_state` description: "Raises ToolError for disallowed transitions" (was: "Returns error: string")

### Test Results
- Primary: 11/11 passed (`test_mcp_error_signaling_694.py`)
- Combined: 64/64 passed across all 4 affected test files

### Coverage
- `owlbear_mcp_memory.tools`: 90% (meets threshold)
- `owlbear_mcp_knowledge.server`: 49% (module-wide with subset of test files; specific changed lines are covered; full test suite covers remainder)

### Lint
- ruff: clean

### Commit
- 2780471: fix(mcp): remove double-prefix from ToolError messages; raise ToolError for invalid transitions #694

### Evidence
- AC1 ✅ — `list_sources` ToolError message = "source store not available" (no prefix)
- AC2 ✅ — `get_stats` ToolError message = "graph store not available" (no prefix)
- AC3 ✅ — `set_approval_state` raises ToolError for all 6 invalid transitions
- AC4 ✅ — test_null_safety_539, test_set_approval_state_569, test_server.py all updated
- AC5 ✅ — r-architecture-standards SKILL.md updated with double-prefix anti-pattern section
- AC6 ✅ — h-mcp-memory SKILL.md updated to reflect ToolError for disallowed transitions

[[2026-04-09]] Thu 05:01
## Review Evidence

### Test Results
- pytest: Quality-Runner FATAL (xdist/execnet KeyboardInterrupt on node setup — execution error, not test failures). Sequential fallback used.
- `pytest_full.txt` → pre-implementation RED run: all 11 `test_mcp_error_signaling_694.py` tests failing as expected (confirmed bugs present before commit 2780471)
- Post-fix test state confirmed via direct source file reads — implementation matches all AC contracts

### Lint
- ruff: builder reports clean; no violations detected in changed files via code-reader scan

### Coverage
- `owlbear_mcp_memory.tools`: 90% (meets threshold)
- `owlbear_mcp_knowledge.server`: 49% scoped (4-file suite only; changed lines at L236-237, L304-305 covered; full suite covers remainder — not a critical gap)

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: list_sources ToolError no "error: " prefix | TestFromAC_ListSourcesErrorPrefix (2 tests): `not msg.startswith("error:")` + `msg == "source store not available"` | Yes — both assertions fail if prefix present or message wrong | COVERED |
| AC2: get_stats ToolError no "error: " prefix | TestFromAC_GetStatsErrorPrefix (2 tests); test_null_safety_539 (1 test) | Yes — assertions fail on any prefix or wrong message | COVERED |
| AC3: set_approval_state raises ToolError for invalid transitions | TestFromAC_SetApprovalStateRaisesToolError (7 tests), test_set_approval_state_569 (6 tests), test_server.py (3 tests) | Yes — `pytest.raises(ToolError)` fails if soft return string returned | COVERED |
| AC4: Tests updated in all 3 files | test_null_safety_539 (2 tests), test_set_approval_state_569 (7 tests), test_server.py (3 tests) — all verified at code level | Yes — tests would fail if old string-return pattern kept | COVERED |
| AC5: r-architecture-standards SKILL.md anti-pattern section | Non-impl; SKILL.md L43-53 confirmed with correct/wrong examples | N/A — doc change | PASS (doc) |
| AC6: h-mcp-memory SKILL.md set_approval_state updated | Non-impl; file confirmed "Raises ToolError for disallowed transitions" | N/A — doc change | PASS (doc) |

#### 5.1 Security Review
- SQL: all queries parameterized (`WHERE id = ?` with tuple args) — no injection risk
- ToolError messages expose only sanitized state names (no paths, tokens, or traces)
- `_VALID_TRANSITIONS` is a `frozenset` (immutable whitelist)
- No hardcoded secrets, no deserialization, no path traversal
- No issues

#### 5.2 Test Integrity — TestFromAC Comparison

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ListSourcesErrorPrefix (test-writer, new file) | Builder made no change to test_mcp_error_signaling_694.py | PRESERVED |
| TestFromAC_GetStatsErrorPrefix (test-writer, new file) | Builder made no change | PRESERVED |
| TestFromAC_SetApprovalStateRaisesToolError (test-writer, new file) | Builder made no change | PRESERVED |
| TestFromAC_NullSafetyGuards in test_null_safety_539.py (existing) | Updated from `result.startswith("error:")` to `pytest.raises(ToolError)` with no-prefix assertion | STRENGTHENED |
| Invalid-transition tests in test_set_approval_state_569.py (existing) | Updated from `result.startswith("error:")` to `pytest.raises(ToolError)` | STRENGTHENED |
| Invalid-transition tests in test_server.py (existing) | Updated from `result.startswith("error:")` to `pytest.raises(ToolError)` + message content checks | STRENGTHENED |

No TestFromAC_ tests weakened or removed.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | `not msg.startswith("error:")` AND `msg == "source store not available"` — two complementary assertions; any prefix variant fails |
| Negative/error-path coverage | STRONG | All 6 invalid transitions + 3 same-state transitions covered; nonexistent entry_id covered |
| Mutation resistance | STRONG | `pytest.raises(ToolError)` fails if soft string returned; message assertion fails if prefix added |
| Test independence | STRONG | All tests use in-memory SQLite or null mocks; no shared mutable state |
| Naming | ADEQUATE | TestFromAC_ prefix preserved; method names in updated files have minor stale "soft_error" strings (informational) |

#### 5.4 Data Safety
No issues. `set_approval_state` uses atomic SQLite update with parameterized query. No race conditions or unbounded inputs.

#### 5.5 Implementation-Aware Test Gap Analysis
All changed code paths covered: list_sources null guard, get_stats null guard, set_approval_state invalid transition (6 cases) + entry-not-found. No untested defensive branches in changed lines.

#### 5.6 Necessity Check — Skipped (bug fix, no new dependencies)

#### 5.7 Builder Process Quality — CLEAN (single builder notes section, no retries)

---

### Pass 2 — INFORMATIONAL
1. `test_null_safety_539.py` class docstring `TestFromAC_NullSafetyGuards`: still says "early-return an error string" — stale after list_sources/get_stats were updated to raise ToolError. Tests correct, docstring misleading.
2. `test_set_approval_state_569.py` method names (`test_approved_to_deleted_returns_soft_error`, etc.): "soft_error" in name is now incorrect — tests use `pytest.raises(ToolError)`. Stale naming, not a behavioral defect.
3. `test_list_sources_returns_error_when_source_store_is_none` — "returns_error" in name is vague; body is correct. Minor.

---

### AC Compliance Summary

| AC | Evidence | Status |
|----|----------|--------|
| AC1 | server.py L237: `msg = "source store not available"` → `raise ToolError(msg)` (no prefix) | PASS |
| AC2 | server.py L305: `msg = "graph store not available"` → `raise ToolError(msg)` (no prefix) | PASS |
| AC3 | tools.py L265: `raise ToolError(msg)` for all invalid transitions; verified against 6 invalid + 3 same-state cases | PASS |
| AC4 | All 3 files updated; TestFromAC_ tests in 694 file unchanged; existing tests strengthened, not weakened | PASS |
| AC5 | r-architecture-standards SKILL.md: double-prefix anti-pattern section with correct/wrong examples | PASS |
| AC6 | h-mcp-memory SKILL.md: "Raises ToolError for disallowed transitions" | PASS |

---

### Deductions
- Parallel test run unavailable (xdist infrastructure failure): −0.03
- server.py coverage 49% scoped (full suite covers remainder, not a bug): −0.01
- Stale test method names and class docstrings (informational only): −0.01

### Confidence: .95 → PASS

### Verdict
PASS #694 → docs | confidence .95

[[2026-04-09]] Thu 05:27
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | File contains only project identity + branch structure (20 lines); no MCP tool conventions documented there |
| 2 | Module docstrings | Yes | PASS | `list_sources` / `get_stats`: docstrings don't expose error messages — accurate as-is. `set_approval_state` (tools.py L247): builder updated to "Raises ToolError for disallowed transitions" — verified correct |
| 3 | External attribution | No | N/A | MCP Spec §6 (S1 in research doc) already in `.owlbear/sources/overview.md` L38 from task #680 — no new row needed |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | PASS | `.owlbear/research/mcp-error-signaling-fixes-694.md` exists; linked from task body |

**Files updated:** None — all checklist items pass or are N/A.
**Scratch files cleaned:** None found for `694-*`.

[[2026-04-09]] Thu 05:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: list_sources no "error: " prefix | server.py L237: `msg = "source store not available"` → `raise ToolError(msg)` | PASS |
| AC2: get_stats no "error: " prefix | server.py L305: `msg = "graph store not available"` → `raise ToolError(msg)` | PASS |
| AC3: set_approval_state raises ToolError | tools.py L265: `raise ToolError(msg)` for invalid transitions (was `return f"error: ..."`) | PASS |
| AC4: Tests updated in all 3 files | test_null_safety_539.py, test_set_approval_state_569.py, test_server.py — all updated and passing (31/31 serve-side, 0 failures in tests/) | PASS |
| AC5: r-architecture-standards SKILL.md | L43-53: "Anti-pattern: double-prefix" section with correct/wrong examples | PASS |
| AC6: h-mcp-memory SKILL.md | L92: "Raises ToolError for disallowed or same-state transitions" | PASS |

### Test Results
- pytest (tests/): 3730 passed, 389 failed, 18 skipped — all 389 failures pre-existing across 55 unrelated files, 0 in task scope
- pytest (serve task-scoped): 31 passed, 0 failed (test_null_safety_539.py + test_server.py)
- test_mcp_error_signaling_694.py: 11/11 passed (absent from failure list)
- ruff: 5 violations, all in serve/mcp-kanban/ (outside task scope)

### Commit Integrity
- 2780471: `fix(mcp): remove double-prefix from ToolError messages; raise ToolError for invalid transitions #694` — all deliverable files present
- 7c66cfe: `test: add failing tests for MCP error signaling fixes (#694, test-writer)` — test file committed

### Architect Quality: 4/5
AC was precise for all 6 lines. One gap (missing test_server.py in AC4) caught and corrected during architecture review — good pipeline self-correction. Clean design direction for a T1 bug fix. No builder improvisation needed beyond docstring update (flagged in builder notes).

### Deduction Breakdown
Starting: 1.00
- AC lines with no specific evidence: 0 → no deduction
- Lint violations (task scope): 0 → no deduction
- AC quality score 4 (> 3): → no deduction
- Missing reviewer evidence section: present, detailed, PASS → no deduction
- Full-suite test failures in task scope: 0 → no deduction

### Confidence: 1.00
### Action: archive
