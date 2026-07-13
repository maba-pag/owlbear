---
id: 770
title: 'P1-17: Tests — MCP browser server + URL domain allowlist'
status: archived
priority: medium
created: '2026-04-10T10:56:34.316989+00:00'
updated: '2026-04-15T10:49:09.116231+00:00'
tags:
- phase-1
- type:test
- scope:mcp-browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for MCP browser server:
1. FastMCP server registers tools: navigate, click, type, select, read_text, snapshot
2. URL domain allowlist enforcement at tool level — tools reject URLs outside allowed domains
3. Allowlist read from env var
4. Tool annotations set correctly
5. BROWSER_TOOLS_EXCLUDE env var removes tools

Mock-based. All tests fail (RED).

Parent: #751

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/770-mcp-browser-tests.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Descope #770 to AC4 only (ToolAnnotations tests). AC1/2/3/5 are exact duplicates of #790's 25 delivered tests (.95 reviewer confidence). (confidence: .88)
- Follow-up tasks created: none — #770 itself is the follow-up, descoped to ToolAnnotations-only
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — challenger subagent not available
- Confidence in original: .88
- Key challenges: n/a
- Researcher response: n/a

## Key Findings
1. **4/5 ACs are duplicates of #790** — tests already exist in `tests/test_mcp_browser_775.py` (25 tests, all passing)
2. **AC4 (ToolAnnotations) is the only unique gap** — mcp-browser is the only MCP server without ToolAnnotations
3. **Test pattern exists** — `serve/mcp-kanban/tests/test_tool_annotations_494.py` provides exact template
4. **#794 AC already expects ToolAnnotations** — #770's AC4 fills the missing RED-phase test for #794's TDD cycle
5. **Expected ~15 tests** for ToolAnnotations: 1 import + 1 all-have-annotations + ~13 per-hint assertions across 6 tools

## Scope Revision
AC1 (6 tools registered) → covered by #790 TestFromAC_MCPServerLifespan
AC2 (domain allowlist enforcement) → covered by #790 TestFromAC_NavigateToolError
AC3 (allowlist from env var) → covered by #790 TestFromAC_DomainAllowlistEnvVar
AC4 (ToolAnnotations) → **UNIQUE — retain as sole AC for #770**
AC5 (BROWSER_TOOLS_EXCLUDE) → covered by #790 TestFromAC_ApplyToolExclusions
[[2026-04-11]]
## Architecture Review

### Scope Revision (from Research)
AC1/2/3/5 are exact duplicates of #790's delivered tests (25 tests in `tests/test_mcp_browser_775.py`). **Descoped to AC4 only: ToolAnnotations tests.**

### Refined Acceptance Criteria
Test file: `tests/test_mcp_browser_tool_annotations_770.py`
Pattern: follow `serve/mcp-kanban/tests/test_tool_annotations_494.py`
RED phase — all tests must FAIL.

1. `owlbear_mcp_browser.server` module imports `ToolAnnotations` from `mcp.types`
2. All 6 tools have `annotations is not None`: navigate, click, type, select, read_text, snapshot
3. `read_text`: readOnlyHint=True, idempotentHint=True
4. `snapshot`: readOnlyHint=True, idempotentHint=True
5. `navigate`: idempotentHint=True, destructiveHint=False
6. `select`: idempotentHint=True, destructiveHint=False
7. `click`: destructiveHint=False
8. `type`: destructiveHint=False

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | ToolAnnotations tests for mcp-browser only |
| Interface clarity | PASS | Exact hint values specified per tool |
| Dependency correctness | PASS | No deps needed for RED-phase test task (see correction below for #794) |
| Module layering | PASS | Tests import from `owlbear_mcp_browser.server` — correct direction |
| TDD compliance | PASS | This IS the RED phase; GREEN phase is #794 |
| KISS/YAGNI | PASS | Descoped from 5 ACs to 1; ~15 focused tests |
| Premise challenge | PASS | mcp-browser is the only MCP server missing ToolAnnotations |
| Pattern consistency | PASS | Follows `test_tool_annotations_494.py` template from mcp-kanban |
| Security surface | PASS | Tests only, no new security boundaries |
| Single domain | PASS | scope:mcp-browser only |

### Dependency Correction
DEPENDS_ON-CORRECTION: task #794 should have depends_on [790, 788, 770] — #770 provides RED-phase ToolAnnotations tests that #794's GREEN implementation must pass.

### Challenge Results
- Challenger: FALLBACK — challenger subagent not available in agent list
- Architect response: N/A

### Codebase Evidence
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py`: 6 bare `@_mcp.tool()` decorators, no ToolAnnotations
- `tests/test_mcp_browser_775.py`: 25+ tests covering AC1/2/3/5 (from #790)
- `serve/mcp-kanban/tests/test_tool_annotations_494.py`: exact template for ToolAnnotations tests
- No existing ToolAnnotations tests for mcp-browser anywhere in workspace

### Verdict: APPROVE
### Action Taken: Descoped to AC4 (ToolAnnotations), refined AC with specific per-tool hint assertions, advanced to todo.
[[2026-04-11]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_browser_tool_annotations_770.py`
**Class:** `TestFromAC_ToolAnnotations`
**Pattern:** Follows `serve/mcp-kanban/tests/test_tool_annotations_494.py`

### Test counts by category

| Category | Count |
|----------|-------|
| Import assertion | 1 |
| All-tools-have-annotations (parametrized × 6) | 6 |
| Per-hint boundary assertions | 10 |
| **Total** | **17** |

### Fail confirmation
`pytest tests/test_mcp_browser_tool_annotations_770.py -v --tb=short`
→ **17 failed, 0 passed** ✓ (RED phase confirmed)
→ `ruff check` → clean ✓

### AC coverage

| AC | Tests |
|----|-------|
| ToolAnnotations imported in server module | `test_tool_annotations_used_in_server_module` |
| All 6 tools have annotations ≠ None | `test_all_tools_have_annotations[navigate\|click\|type\|select\|read_text\|snapshot]` |
| read_text: readOnlyHint=True | `test_read_text_read_only_hint_true` |
| read_text: idempotentHint=True | `test_read_text_idempotent_hint_true` |
| snapshot: readOnlyHint=True | `test_snapshot_read_only_hint_true` |
| snapshot: idempotentHint=True | `test_snapshot_idempotent_hint_true` |
| navigate: idempotentHint=True | `test_navigate_idempotent_hint_true` |
| navigate: destructiveHint=False | `test_navigate_destructive_hint_false` |
| select: idempotentHint=True | `test_select_idempotent_hint_true` |
| select: destructiveHint=False | `test_select_destructive_hint_false` |
| click: destructiveHint=False | `test_click_destructive_hint_false` |
| type: destructiveHint=False | `test_type_destructive_hint_false` |

All AC lines covered. Every test fails. Builder (#794) must add ToolAnnotations to all 6 `@_mcp.tool()` decorators in `serve/mcp-browser/src/owlbear_mcp_browser/server.py`.
[[2026-04-11]]
## Builder Notes

**Files changed:** 1
- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — added `from mcp.types import ToolAnnotations` import + added `annotations=ToolAnnotations(...)` to all 6 `@_mcp.tool()` decorators

**Test results:**
- RED verified: 17 failed, 0 passed before implementation
- GREEN: 17 passed, 0 failed after implementation
- Regression: `test_mcp_browser_775.py` — 25 passed (no regressions)
- Total: 42 passed

**Coverage:** 92.6% on `server.py` (57/62 stmts, 6/6 branches) — combined with `test_mcp_browser_775.py`; uncovered lines are async function return stubs with no logic

**Lint:** `ruff check` — All checks passed

**Annotations applied:**
- `navigate`: `idempotentHint=True, destructiveHint=False`
- `click`: `destructiveHint=False`
- `type`: `destructiveHint=False`
- `select`: `idempotentHint=True, destructiveHint=False`
- `read_text`: `readOnlyHint=True, idempotentHint=True`
- `snapshot`: `readOnlyHint=True, idempotentHint=True`

**Commit:** `feat(mcp-browser): add ToolAnnotations to all 6 browser tools (#770, builder)`
[[2026-04-11]]
## Review Evidence

### Tests (independent run)
- `pytest tests/test_mcp_browser_tool_annotations_770.py tests/test_mcp_browser_775.py` → **42 passed, 0 failed**
- Regression check: all 25 pre-existing tests in `test_mcp_browser_775.py` pass

### Lint
- `ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py tests/test_mcp_browser_tool_annotations_770.py` → **clean**

### Coverage
- `owlbear_mcp_browser.server`: **92%** (≥ 90% threshold ✓)

---

### 5.0 Test-Writer Audit — AC-to-Test Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| ToolAnnotations imported in server module | `test_tool_annotations_used_in_server_module` | Yes — `hasattr` check fails if import removed | COVERED |
| All 6 tools have annotations ≠ None | `test_all_tools_have_annotations[navigate\|click\|type\|select\|read_text\|snapshot]` | Yes — `assert annotations is not None` | COVERED |
| read_text: readOnlyHint=True | `test_read_text_read_only_hint_true` | Yes — `assert ann.readOnlyHint is True` | COVERED |
| read_text: idempotentHint=True | `test_read_text_idempotent_hint_true` | Yes — identity check | COVERED |
| snapshot: readOnlyHint=True | `test_snapshot_read_only_hint_true` | Yes | COVERED |
| snapshot: idempotentHint=True | `test_snapshot_idempotent_hint_true` | Yes | COVERED |
| navigate: idempotentHint=True | `test_navigate_idempotent_hint_true` | Yes | COVERED |
| navigate: destructiveHint=False | `test_navigate_destructive_hint_false` | Yes | COVERED |
| select: idempotentHint=True | `test_select_idempotent_hint_true` | Yes | COVERED |
| select: destructiveHint=False | `test_select_destructive_hint_false` | Yes | COVERED |
| click: destructiveHint=False | `test_click_destructive_hint_false` | Yes | COVERED |
| type: destructiveHint=False | `test_type_destructive_hint_false` | Yes | COVERED |

No MISSING. All 12 covered.

### 5.1 Security
No security concerns. Changes are decorator metadata only — no secrets, injection vectors, path ops, or new dependencies.

### 5.2 Test Integrity — TestFromAC Comparison
Builder did not modify the test file. All 17 test-writer tests preserved unchanged.

### 5.3 Test Quality — STRONG
- Assertion specificity: `is True` / `is False` identity comparisons. Any wrong value (None, incorrect bool) fails. STRONG.
- Mutation resistance: Flipping any hint value in server.py would trip the matching assertion. STRONG.
- Test independence: `_get_tool_annotations` calls `list_tools()` per call, no shared mutable state. STRONG.
- Names: All descriptive snake-case per Python convention. STRONG.
- Error paths: N/A for static metadata assertions.

### 5.4 Data Safety — PASS
No LLM output persistence, no shared mutable state, no resource-intensive ops.

### 5.5 Implementation-Aware Test Gap Analysis
All 6 tools verified against server.py:
- `navigate` (server.py:63): `idempotentHint=True, destructiveHint=False` ✓ tested
- `click` (server.py:69): `readOnlyHint=False, destructiveHint=False` — destructiveHint tested ✓; readOnlyHint not in AC (not a gap)
- `type` (server.py:74): `readOnlyHint=False, destructiveHint=False` — destructiveHint tested ✓
- `select` (server.py:79): `idempotentHint=True, destructiveHint=False` ✓ tested
- `read_text` (server.py:84): `readOnlyHint=True, idempotentHint=True` ✓ tested
- `snapshot` (server.py:101): `readOnlyHint=True, idempotentHint=True` ✓ tested

No significant untested paths.

### 5.7 Builder Process Quality — CLEAN
One `## Builder Notes` section. Single-attempt delivery.

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| ToolAnnotations imported | server.py:14 `from mcp.types import ToolAnnotations` | `test_tool_annotations_used_in_server_module` | PASS |
| All 6 tools annotated | server.py:63,69,74,79,84,101 — all 6 decorators | `test_all_tools_have_annotations[*]` | PASS |
| read_text readOnlyHint=True | server.py:84 `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` | `test_read_text_read_only_hint_true` | PASS |
| read_text idempotentHint=True | server.py:84 same | `test_read_text_idempotent_hint_true` | PASS |
| snapshot readOnlyHint=True | server.py:101 `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` | `test_snapshot_read_only_hint_true` | PASS |
| snapshot idempotentHint=True | server.py:101 same | `test_snapshot_idempotent_hint_true` | PASS |
| navigate idempotentHint=True | server.py:63 `ToolAnnotations(idempotentHint=True, destructiveHint=False)` | `test_navigate_idempotent_hint_true` | PASS |
| navigate destructiveHint=False | server.py:63 same | `test_navigate_destructive_hint_false` | PASS |
| select idempotentHint=True | server.py:79 `ToolAnnotations(idempotentHint=True, destructiveHint=False)` | `test_select_idempotent_hint_true` | PASS |
| select destructiveHint=False | server.py:79 same | `test_select_destructive_hint_false` | PASS |
| click destructiveHint=False | server.py:69 `ToolAnnotations(readOnlyHint=False, destructiveHint=False)` | `test_click_destructive_hint_false` | PASS |
| type destructiveHint=False | server.py:74 `ToolAnnotations(readOnlyHint=False, destructiveHint=False)` | `test_type_destructive_hint_false` | PASS |

### Informational (non-blocking)
- `mcp_app = _mcp._tool_manager` in server.py accesses a private FastMCP attribute. This is consistent with the reference pattern from `test_tool_annotations_494.py` — acceptable.

### Deductions
None.

### Verdict
**PASS → docs | confidence .97**
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | ToolAnnotations are decorator metadata on browser tools; copilot-instructions.md covers project-level conventions, not per-tool hint metadata. No update needed. |
| 2 | Module docstrings | Yes | Updated | `server.py` — all 9 public symbols have accurate docstrings. Test file module docstring had stale RED-phase note ("All tests FAIL in RED phase — ToolAnnotations not yet applied"); removed since GREEN is complete and all 17 tests pass. |
| 3 | External attribution | No | N/A | Research doc `770-mcp-browser-tests.md` cites 6 internal sources only. ToolAnnotations sources already attributed in overview.md from prior tasks (#494, #771). No new rows needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/770-mcp-browser-tests.md` exists and is linked in task body. Follow-up tasks noted as N/A (task itself was the descoped follow-up). |

### Files Updated
- `tests/test_mcp_browser_tool_annotations_770.py` — removed stale RED-phase docstring note
- Commit: `792022b6` — `docs: remove stale RED-phase docstring note (#770, doc-writer)`

### Scratch Files Cleaned
- None (no `.owlbear/scratch/770-*` files found)
[[2026-04-15]]
## Audit
### AC Verification (descoped to AC4 — ToolAnnotations only)
| AC Line | Evidence | Status |
|---------|----------|--------|
| ToolAnnotations imported in server module | server.py:16 `from mcp.types import ToolAnnotations` | PASS |
| All 6 tools have annotations != None | server.py:98,136,145,155,170,183 — all 6 decorators have `annotations=ToolAnnotations(...)` | PASS |
| read_text: readOnlyHint=True | server.py:170, test `test_read_text_read_only_hint_true` passes | PASS |
| read_text: idempotentHint=True | server.py:170, test `test_read_text_idempotent_hint_true` passes | PASS |
| snapshot: readOnlyHint=True | server.py:183, test `test_snapshot_read_only_hint_true` passes | PASS |
| snapshot: idempotentHint=True | server.py:183, test `test_snapshot_idempotent_hint_true` passes | PASS |
| navigate: idempotentHint=True | server.py:98, test `test_navigate_idempotent_hint_true` passes | PASS |
| navigate: destructiveHint=False | server.py:98, test `test_navigate_destructive_hint_false` passes | PASS |
| select: idempotentHint=True | server.py:155, test `test_select_idempotent_hint_true` passes | PASS |
| select: destructiveHint=False | server.py:155, test `test_select_destructive_hint_false` passes | PASS |
| click: destructiveHint=False | server.py:136, test `test_click_destructive_hint_false` passes | PASS |
| type: destructiveHint=False | server.py:145, test `test_type_destructive_hint_false` passes | PASS |

### Test Results
- pytest (task scope): 42 passed, 0 failed (17 #770 + 25 #775 regression)
- pytest (full suite): 4386 passed, 192 failed, 8 skipped — no failures in #770 scope; all failures in unrelated files
- ruff: 3 violations in unrelated files (engine.py E501, test_refresh_sharepoint_879.py RUF002/UP024); zero in #770 files

### Reviewer Evidence
Detailed review section present. PASS at .97. AC-to-test mapping complete (12/12 COVERED). Test integrity, security, and builder process quality all assessed. Trusted.

### Architect Quality: 4/5
Original 5-AC scope was over-broad (4/5 ACs duplicated #790). Research correctly descoped to AC4. Refined AC was specific with exact per-tool hint values. Minor deduction for upstream AC quality requiring descoping.

### Commit Integrity
- Test file committed in `792022b6` (docs commit, first commit of file)
- ToolAnnotations on decorators committed in `60af19c0` (batch chore commit)
- Builder's claimed commit message not found — work was swept into batch commits
- Informational only; deliverables are present and committed

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (all 12 verified) — no deduction
- Lint violations in scope: 0 — no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence: present, detailed — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: .98
### Action: archive