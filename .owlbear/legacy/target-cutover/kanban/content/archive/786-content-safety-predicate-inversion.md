---
id: 786
title: Content safety predicate inversion
status: archived
priority: medium
created: '2026-04-10T12:31:05.221180+00:00'
updated: '2026-04-13T10:47:04.123286+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 781
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `content_safety.py` predicate changed from `== "url"` to `not in ("file", "text", "file_glob")`
- All #781 tests pass; existing content_safety tests still pass
- Defense-in-depth: new source types are wrapped by default
- File: `serve/knowledge/src/owlbear_knowledge/content_safety.py`

## Context
- WS-B: Pipeline Quality
- Scope item 8 from #775
- See research F4: defense-in-depth, safe to ship independently

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: invert `should_wrap()` predicate from allow-list to deny-list |
| Interface clarity | PASS | AC specifies exact predicate change, inputs/outputs clear from `should_wrap(source_type: str | None) -> bool` |
| Dependency correctness | PASS | Depends on #781 (Tests — Content safety predicate inversion) which is `done`. AC references #781 tests. |
| Module layering | PASS | Self-contained change within `owlbear_knowledge.content_safety` — no cross-package imports |
| TDD compliance | PASS | Preceding test task #781 is `done`; 11 predicate tests in `test_content_safety_inversion_775.py` |
| KISS/YAGNI | PASS | Minimal change: one predicate function, one constant definition |
| Premise challenge | NOTE | **Implementation already exists in codebase.** `should_wrap()` at line 42 of `content_safety.py` already returns `source_type not in _TRUSTED_SOURCE_TYPES`. All 27 tests pass. Likely completed as part of #769 (P1-16). Builder can fast-track with verification-only pass. |
| Pattern consistency | PASS | Follows deny-list pattern consistent with defense-in-depth security principle |
| Security surface | PASS | This is a security improvement — unknown future source types are now wrapped by default |
| Single domain | PASS | Knowledge domain only (`scope:knowledge`) |

### Code Quality Note
`content_safety.py` has duplicate constant definitions: `_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` are defined at lines 9–17 and again at lines 44–52. The second assignment overwrites harmlessly but is dead code. Builder should deduplicate during this task.

### Challenge Results
- Challenger: FALLBACK — agent not available
- Architect response: proceeded without challenge; implementation is straightforward and already verified in codebase

### Verdict: APPROVE
### Action Taken: Advanced to `todo`. Implementation already exists — builder should verify code matches AC and deduplicate constants. All 27 content-safety tests confirmed passing.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_content_safety_inversion_786.py
- Classes: TestFromAC_ConstantDeduplication
- Tests per category: happy 0, edge 0, error 0, boundary 3 (constant-count structural assertions)
- Total: 3 tests, all FAIL
- ruff: clean
- Commit: b373ec6d

### AC Coverage

| AC Line | Coverage | Notes |
|---------|----------|-------|
| AC1: predicate `not in ("file","text","file_glob")` | Pre-covered | #781 tests in test_content_safety_inversion_775.py (11 tests, all pass). No new behavioral tests possible — correct implementation already exists per arch review. |
| AC-quality: deduplicate `_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` | 3 failing tests | `TestFromAC_ConstantDeduplication` — each constant currently assigned twice; tests assert count == 1. All 3 fail with `assert 2 == 1`. |

### Why only 3 tests

Arch review confirmed implementation already correct (done as part of #769). Every behavioral test for `should_wrap()` passes on current code. The only remaining builder work is constant deduplication (lines 44–52 are dead code). Three structural inspection tests via `inspect.getsource()` enforce the single-definition invariant and will turn green once the builder removes the duplicate block.
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/content_safety.py` — removed duplicate constant block (lines 44–52: second definitions of `_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG`)

### RED Verification
- 3 tests FAILED before change: `TestFromAC_ConstantDeduplication` — each constant assigned 2× (`assert 2 == 1`)

### Implementation
Removed the dead-code duplicate block that followed `should_wrap()`. The first definitions (lines 9–17) are the single authoritative source. No behavioral changes — `wrap_untrusted_content()` still uses the same constant values.

### Test Results
- `test_content_safety_inversion_786.py`: 3/3 passed (GREEN)
- `test_content_safety_inversion_775.py`: 11/11 passed
- `test_content_safety_735.py`: 16/16 passed
- Total: 30 passed, 0 failed

### Lint
- ruff: clean (no issues)

### Coverage
Not measured separately — single-file change covering the target module; all 30 content-safety tests pass.

### Evidence Summary
- RED → GREEN: duplicate constant block removed
- AC1 (predicate `not in ("file","text","file_glob")`): pre-existing, confirmed passing via #781 tests
- AC-quality (constant deduplication): 3 new tests now GREEN
- No other files touched
[[2026-04-12]]
## Review Evidence

### Test Execution
pytest initialization hung in quality-runner (Windows env degradation / venv state — pytest_load_initial_conftests stall). Fell back to sequential workflow with static test verification.
ruff (via quality-runner): **clean** — 0 violations.

### Static Test Verification
All test assertions verified by reading `content_safety.py` (66 lines) against test logic:

**TestFromAC_ConstantDeduplication (3 tests) — test_content_safety_inversion_786.py**
- `count("_ADVISORY = ")` in source → 1 (line 9 only) ✓
- `count("_OPEN_TAG = ")` in source → 1 (line 16 only) ✓
- `count("_CLOSE_TAG = ")` in source → 1 (line 17 only) ✓
Duplicate block (former lines 44–52) confirmed absent. All 3 → PASS.

**TestFromAC_ShouldWrapPredicate (11 tests) — test_content_safety_inversion_775.py**
All 11 assertions verified against `should_wrap()` at line 25–40 and `_TRUSTED_SOURCE_TYPES = frozenset({"file","file_glob","text"})` at line 22. Every test maps directly to correct implementation behaviour. All 11 → PASS.

**test_content_safety_735.py (16 tests)**
`wrap_untrusted_content()` unchanged in builder diff; constants have same values; existing tests exercise untouched code paths → PASS (static).

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: predicate `not in ("file","text","file_glob")` | Line 40: `return source_type not in _TRUSTED_SOURCE_TYPES`; frozenset contains exactly {"file","file_glob","text"} | PASS |
| AC2: All #781 tests pass; existing tests pass | 11/11 inversion tests + 16/16 existing tests verified statically | PASS |
| AC3: Defense-in-depth — new types wrapped by default | `not in` predicate inherently wraps any source_type not explicitly trusted | PASS |
| AC4: File is content_safety.py | Only file touched per builder + confirmed by code read | PASS |
| Arch-quality: deduplicate _ADVISORY/_OPEN_TAG/_CLOSE_TAG | Duplicate block removed; each constant appears exactly once; enforced by 3 structural tests | PASS |

### TestFromAC_ Integrity
No modifications to any `TestFromAC_` class detected. Test assertions would fail on the original (pre-builder) code and pass on current code — RED→GREEN confirmed by static analysis.

### Security
No new security concerns introduced. Pre-existing note: `source_url` attribute in `wrap_untrusted_content()` is unescaped in the open tag (line 62). Not in scope for this task; not introduced by this change.

### Deductions
- −0.04: pytest not independently executed (environment issue, not code issue); static analysis substituted for all assertions.

### Verdict
Confidence: **0.96** → **PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `should_wrap()` and `wrap_untrusted_content()` signatures unchanged; predicate inversion is internal. `copilot-instructions.md` is 80 lines covering only project identity and branch structure — no knowledge module section to update. |
| 2 | Module docstrings | Yes | Verified | Read all 66 lines of `content_safety.py`. Module docstring accurate. `should_wrap()` docstring (lines 25–38) correctly describes deny-list predicate and `None` treatment. `wrap_untrusted_content()` docstring (lines 44–54) accurate. No changes needed. |
| 3 | External attribution | No | N/A | Change derived entirely from internal research finding F4 in `.owlbear/research/775-phase1-browser-pipeline-schema.md`. No external repos, articles, or docs used. |
| 4 | CLI changes | No | N/A | Pure internal implementation change in `content_safety.py` — no CLI additions or modifications. |
| 5 | Research doc | No | N/A | No dedicated `786-*.md` research file produced. Finding F4 confirmed in `.owlbear/research/775-phase1-browser-pipeline-schema.md` (line 68). Task context references it correctly. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/786-*` files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: predicate `not in ("file","text","file_glob")` | content_safety.py:L40 `return source_type not in _TRUSTED_SOURCE_TYPES`; L22 `frozenset({"file","file_glob","text"})` | PASS |
| AC2: All #781 tests pass; existing tests pass | 30/30 pass (11 inversion + 16 existing + 3 dedup) | PASS |
| AC3: Defense-in-depth — new types wrapped by default | `not in` predicate wraps unknown types; confirmed by `test_unknown_future_type_returns_true` | PASS |
| AC4: File is content_safety.py | Only file touched per git log + code read | PASS |

### Test Results
- pytest (task-scoped): 30/30 passed, 0 failed
- pytest (full suite): 4076 passed, 335 failed, 8 skipped — all 335 failures unrelated (kanban model renames, analysis schema, browser scaffold)
- ruff: clean (0 violations)

### Architect Quality: 4/5
AC was specific and verifiable. Minor gap: constant deduplication was an arch review note rather than a formal AC line, but correctly picked up by test-writer. Design direction (deny-list predicate) well-motivated by research F4.

### Deduction Breakdown
- All 4 AC lines have specific evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5 > 3: no deduction
- Reviewer evidence present and detailed (PASS at 0.96): no deduction
- Full-suite failures: none in task scope: no deduction

### Confidence: 0.98
### Action: archive