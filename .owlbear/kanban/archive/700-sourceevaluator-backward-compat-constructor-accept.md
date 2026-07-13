---
id: 700
title: SourceEvaluator backward-compat constructor — accept model string without crash
status: archived
priority: medium
created: 2026-04-08T21:39:48.0119819+02:00
updated: 2026-04-09T02:44:13.6031765+02:00
started: 2026-04-09T02:44:13.6031765+02:00
completed: 2026-04-09T02:44:13.6031765+02:00
tags:
    - scope:knowledge
    - ' type:bug'
    - ' source:research'
parent: 688
class: standard
---

## Context

From #688 research. `SourceEvaluator(model)` in `server.py:149` crashes at runtime because the constructor expects `EvaluateFn` callable but receives a string. Mirror the EntityExtractor backward-compat pattern.

## Acceptance Criteria

- [ ] AC1: `SourceEvaluator(model_string)` instantiates without error (positional arg)
- [ ] AC2: `SourceEvaluator(llm_fn=callable)` still works (keyword-only arg)
- [ ] AC3: When `llm_fn` is None, `evaluate()` returns `_default_result()` for valid content+context (no crash)
- [ ] AC4: Existing tests in `test_evaluator.py` pass without modification

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/evaluator.py` (constructor + evaluate guard)
- `tests/test_evaluator.py` (add backward-compat test)

## Research

See `.owlbear/research/fix-sourceevaluator-wiring.md` — Option A.
Pattern reference: `serve/knowledge/src/owlbear_knowledge/extractor.py:55-75`.

[[2026-04-08]] Wed 22:23
## Research

Validation pass of parent research (.owlbear/research/fix-sourceevaluator-wiring.md — Option A).

**Gate checklist:**
1. Theoretical validity — Sound. Backward-compat constructor is standard Python pattern.
2. Environment audit — N/A, must be code change.
3. Prior art — EntityExtractor (extractor.py:55-75) solves identical problem in same codebase.
4. Technical feasibility — ~10 LOC, 0 new deps, Python 3.12.
5. Architecture fit — Mirrors existing EntityExtractor pattern exactly.
6. Implementation approach — Add `model` positional (default None), make `llm_fn` keyword-only (default None), guard `evaluate()` to return `_default_result()` when `llm_fn is None`.
7. Testing strategy — 37 existing test_evaluator.py tests pass unchanged. 2 currently-failing zero-arg tests in test_knowledge_consolidation_evaluator_init.py will be fixed by this change. Add test for `SourceEvaluator("model-string")`.
8. Findings documented — Parent doc: .owlbear/research/fix-sourceevaluator-wiring.md

**Verified codebase state:**
- server.py:149 still passes `model` string to `SourceEvaluator(model)` — bug confirmed present
- evaluator.py:85 still requires `llm_fn: EvaluateFn` — no default, no backward compat
- EntityExtractor pattern at extractor.py:55-75 is stable reference

**Tier:** T1 — Autonomous (bug fix, no new capability, no arch change)
**Confidence:** 0.90 — well-defined fix, proven pattern, no ambiguity
**Challenge:** Skipped — trivial backward-compat fix mirroring existing pattern
**Follow-up tasks:** None needed — #701 already exists for real LLM wiring
**Decision requests:** None

[[2026-04-08]] Wed 22:41
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: backward-compat constructor + evaluate guard for SourceEvaluator |
| Interface clarity | PASS | AC specifies exact instantiation forms (positional string, keyword callable), return behavior when llm_fn is None |
| Dependency correctness | PASS | No dependencies — standalone crash fix. #701 handles real LLM wiring separately |
| Module layering | PASS | Changes in knowledge service layer (evaluator.py); no upward imports |
| TDD compliance | PASS | Test-writer will process before builder per pipeline |
| KISS/YAGNI | PASS | ~10 LOC change mirroring proven EntityExtractor pattern (extractor.py:55-75) |
| Premise challenge | PASS | Bug confirmed: server.py:149 passes model string where EvaluateFn callable expected |
| Pattern consistency | PASS | Mirrors EntityExtractor backward-compat constructor exactly — same model positional + injectable keyword-only pattern |
| Security surface | PASS | No new external inputs or system boundaries |
| Single domain | PASS | Knowledge domain only (scope:knowledge) |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| SourceEvaluator(model_string) | String passed as positional arg | None (accepted, ignored) | Yes — AC1 | No crash on startup |
| evaluate() with llm_fn=None | No callable to invoke | None (guard returns _default_result()) | Yes — AC3 | Neutral score 0.5, worth_ingesting=True (interim until #701) |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: `SourceEvaluator(model_string)` instantiates without error | PASS — Precise, testable: `evaluator = SourceEvaluator("gpt-4o-mini"); assert evaluator` | None |
| AC2: `SourceEvaluator(llm_fn=callable)` still works | PASS — Testable, existing test_evaluator.py tests exercise this path | None |
| AC3: When llm_fn is None, evaluate() returns _default_result() | PASS — Testable: instantiate with string, call evaluate(content, context), verify default result fields | None |
| AC4: Existing tests in test_evaluator.py pass without modification | PASS — Regression guard, mechanically verifiable | None |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in this session
- Architect response: Proceeding — all AC lines are precise, pattern is proven (EntityExtractor), T1 autonomous fix

### Architecture Notes
- Interim state (score 0.5 for all evaluations) is explicitly acceptable per parent #688 research and #701 follow-up
- EntityExtractor pattern at extractor.py:55-75 is the canonical reference for the builder
- Zero-arg tests in test_knowledge_consolidation_evaluator_init.py (lines 93, 101) will also be fixed as a side effect

### Verdict: APPROVE
### Action Taken: Advanced #700 to todo — AC verifiable, architecture sound, proven codebase pattern

[[2026-04-08]] Wed 23:28
## Test-Writer Notes

**Test file:** `tests/test_evaluator.py`
**New class:** `TestFromAC_BackwardCompatConstructor`

### Late-RED notice
Implementation was committed by #688 (`fix(knowledge): wire SourceEvaluator with make_evaluate_fn callable`) before the test-writer ran. Constructor backward-compat and evaluate() guard are already in `evaluator.py`. All 10 new tests PASS against existing code — they serve as regression tests and contract documentation.

### Tests per category

| Category | Count | Tests |
|----------|-------|-------|
| AC1 — constructor accepts positional model string | 3 | `test_ac1_model_string_positional_instantiates`, `test_ac1_arbitrary_string_positional_instantiates`, `test_ac1_none_positional_instantiates` |
| AC2 — callable keyword arg still wires fn | 2 | `test_ac2_callable_keyword_still_instantiates`, `test_ac2_callable_keyword_fn_is_invoked` |
| AC3 — evaluate() returns _default_result() when no real llm_fn | 5 | `test_ac3_model_string_evaluate_no_crash`, `test_ac3_model_string_evaluate_returns_default_relevance`, `test_ac3_model_string_evaluate_returns_worth_ingesting_true`, `test_ac3_model_string_evaluate_default_summary`, `test_ac3_none_instance_evaluate_valid_context_returns_default` |

**Total:** 10 new tests (10 PASS — implementation pre-committed by #688)

### AC coverage

| AC | Coverage |
|----|---------|
| AC1: `SourceEvaluator(model_string)` instantiates without error | ✅ 3 tests |
| AC2: `SourceEvaluator(llm_fn=callable)` still works | ✅ 2 tests (+ existing tests in TestFromAC_SourceEvaluator) |
| AC3: evaluate() returns _default_result() when llm_fn is None/non-callable, valid content+context supplied | ✅ 5 tests |
| AC4: Existing tests in test_evaluator.py pass without modification | ✅ 47/47 pass |

### Quality
- `uv run ruff check tests/test_evaluator.py` → All checks passed
- Full file: 47 passed in 2.95s

[[2026-04-09]] Thu 00:36
## Builder Notes

**Files changed:** None — implementation was pre-committed by #688 (`fix(knowledge): wire SourceEvaluator with make_evaluate_fn callable`). This was a Late-RED situation per test-writer notes.

**Test results:** 47 passed, 0 failed (tests/test_evaluator.py)
- TestFromAC_BackwardCompatConstructor: 10/10 pass
- Existing tests: 37/37 pass unchanged (AC4 ✅)

**Coverage:** evaluator.py — 100% (38 statements, 0 missed)

**Lint:** `ruff check tests/test_evaluator.py serve/knowledge/src/owlbear_knowledge/evaluator.py` → All checks passed

**Evidence:**
- AC1 ✅ `SourceEvaluator("gpt-4o-mini")` instantiates — `__init__` accepts positional via `**_kwargs` fallthrough; `llm_fn` becomes None because string is not callable
- AC2 ✅ `SourceEvaluator(llm_fn=callable)` wires the fn — existing test suite exercises this
- AC3 ✅ evaluate() with model-string instance returns `_default_result()` (relevance_score=0.5, worth_ingesting=True, summary contains "No project context available")
- AC4 ✅ Existing 37 tests pass without modification

**No builder-discovered tests needed** — implementation was already complete and correct.

[[2026-04-09]] Thu 01:20
## Review Evidence

### Test Results
- pytest: **47 passed, 0 failed, 0 skipped** (quality-runner, independent run)
- TestFromAC_BackwardCompatConstructor: 10/10
- Existing TestFromAC_SourceEvaluator: 37/37 (all pass — AC4 ✅)

### Lint
- ruff: **clean** (exit 0) on both `evaluator.py` and `tests/test_evaluator.py`

### Coverage
- `owlbear_knowledge.evaluator`: **100%** (38 statements, 0 missed)

### Source Control
Builder made no code changes (#688 pre-committed full implementation). Late-RED situation documented by test-writer.

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Tests | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `SourceEvaluator(model_string)` instantiates without error | `test_ac1_model_string_positional_instantiates`, `test_ac1_arbitrary_string_positional_instantiates`, `test_ac1_none_positional_instantiates` | Yes — constructor exception exits before assert; non-callable coercion to None prevents crash | **COVERED** |
| AC2: `SourceEvaluator(llm_fn=callable)` still works | `test_ac2_callable_keyword_still_instantiates`, `test_ac2_callable_keyword_fn_is_invoked` | Yes — `assert_awaited_once()` + `result.relevance_score == 0.8` fail if callable is not wired | **COVERED** |
| AC3: evaluate() returns `_default_result()` when llm_fn is None, valid content+context | 5 tests: `test_ac3_model_string_evaluate_no_crash`, `test_ac3_model_string_evaluate_returns_default_relevance` (score 0.5), `test_ac3_model_string_evaluate_returns_worth_ingesting_true`, `test_ac3_model_string_evaluate_default_summary`, `test_ac3_none_instance_evaluate_valid_context_returns_default` | Yes — removing `or self._llm_fn is None` from guard would raise TypeError/crash on all 5 tests; score/worth_ingesting values directly check _default_result() | **COVERED** |
| AC4: Existing tests pass without modification | 47/47 passing; 37 pre-existing tests unchanged | Yes — any regression would cause failures | **COVERED** |

No MISSING AC lines.

#### 5.1 Security Review
- No hardcoded secrets, no injection surface, no path traversal
- `callable()` check on user-supplied arg is safe (pure Python introspection)
- No new dependencies, no external I/O added
- **Clean**

#### 5.2 Test Integrity — TestFromAC Comparison
Builder made zero file changes — no TestFromAC_* modification possible. All 10 new tests preserved exactly as test-writer committed them. **No weakening detected.**

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | **ADEQUATE** | AC1 uses `assert evaluator is not None` — lazy pattern, but AC only requires "no crash" semantics; any broader assertion would be speculative. AC2/AC3 use exact values (0.5, True, exact summary substring, `assert_awaited_once()`). |
| Negative/error-path coverage | **ADEQUATE** | AC3 fully covers null-callable path; AC2 covers callable path; empty/None content covered by pre-existing suite |
| Mutation resistance | **STRONG** | Removing `callable(llm_fn)` check → AC3 tests raise TypeError. Removing `or self._llm_fn is None` from evaluate() guard → AC3 tests crash or return wrong values. Inverting `if callable(llm_fn)` → AC2 `assert_awaited_once()` fails. |
| Test independence | **STRONG** | No shared state; each test constructs its own SourceEvaluator |
| Descriptive names | **STRONG** | AC-prefixed, semantically precise names throughout |

No WEAK rating.

#### 5.4 Data Safety
- No LLM output persisted; `_default_result()` returns hardcoded values
- No race conditions; no shared mutable state
- **Clean**

#### 5.5 Implementation-Aware Test Gap Analysis
Constructor paths: `callable(llm_fn)=True` (AC2), `callable(llm_fn)=False` (AC1) — both covered.
`evaluate()` dispatch: empty content (existing), `project_context is None` (existing), `llm_fn is None` (AC3), valid+callable (existing), callable raises (existing). 100% coverage confirms all branches hit.

No significant untested paths.

#### 5.7 Builder Process Quality
Single cycle. Late-RED is a documented pipeline condition, not a loop. **CLEAN.**

### Pass 2 — Informational

1. **Constructor signature deviation** (informational): Architecture notes planned `model` as an explicit positional param + `llm_fn` as keyword-only (mirroring EntityExtractor). Actual implementation uses `llm_fn` as first positional (with `**_kwargs` absorbing extras). All ACs are met — the deviation is more permissive, not less. Builder note incorrectly states "via `**_kwargs` fallthrough" but behavior is correct (`llm_fn` receives the string, not `_kwargs`). No action needed; all tests pass.

2. **AC1 lazy assertions** (informational): `assert evaluator is not None` is the flagged pattern. AC-appropriate for "no crash" constructor tests; no tighter assertion is meaningful here. Deduction: **−0.01**.

### AC Compliance Table

| AC | Evidence | Mapped Test | Status |
|----|----------|-------------|--------|
| AC1: `SourceEvaluator(model_string)` instantiates without error | evaluator.py:89 `llm_fn if callable(llm_fn) else None` — string not callable → None; constructor returns without exception | `test_ac1_model_string_positional_instantiates` (pass) | **PASS** |
| AC2: `SourceEvaluator(llm_fn=callable)` still works | evaluator.py:89 callable check passes → `_llm_fn = llm_fn` | `test_ac2_callable_keyword_fn_is_invoked` (pass) | **PASS** |
| AC3: evaluate() returns `_default_result()` when llm_fn is None | evaluator.py:109 `if project_context is None or self._llm_fn is None: return _default_result()` | 5 `test_ac3_*` tests (all pass) | **PASS** |
| AC4: Existing tests pass without modification | 37 pre-existing tests pass; 47 total | Full pytest run | **PASS** |

### Deductions
- AC1 lazy assertions (`assert evaluator is not None`): −0.01

### Verdict
**Confidence: 0.99 → PASS → docs**

[[2026-04-09]] Thu 02:08
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `SourceEvaluator` constructor accepts positional string — internal service class only. `copilot-instructions.md` is 15 lines covering repo branches with no component API tables to update. |
| 2 | Module docstrings | Yes | Verified | All public symbols in `evaluator.py` have accurate docstrings. `SourceEvaluator` class docstring explicitly documents the new backward-compat behaviour ("If None or a non-callable is supplied…"). `evaluate()` covers all three return paths. |
| 3 | External attribution | No | N/A | Pattern sourced from `extractor.py` in same codebase (EntityExtractor). No external repos or articles used. |
| 4 | CLI changes | No | N/A | Internal constructor fix — no CLI surface touched. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/fix-sourceevaluator-wiring.md` exists, linked from task body under `## Research`. Follow-up task #701 (real LLM wiring) already exists. |

### Files Updated
None — all docstrings accurate as-written, no documentation gaps found.

### Scratch Files
No `.owlbear/scratch/700-*` files found; nothing to clean.

[[2026-04-09]] Thu 02:44
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `SourceEvaluator(model_string)` instantiates without error | evaluator.py:89 `llm_fn if callable(llm_fn) else None`; 3 tests pass (`test_ac1_*`) | PASS |
| AC2: `SourceEvaluator(llm_fn=callable)` still works | evaluator.py:89 callable check; `test_ac2_callable_keyword_fn_is_invoked` asserts `assert_awaited_once()` + score 0.8 | PASS |
| AC3: evaluate() returns `_default_result()` when llm_fn is None | evaluator.py:112 guard `or self._llm_fn is None`; 5 `test_ac3_*` tests verify score 0.5, worth_ingesting=True, summary | PASS |
| AC4: Existing tests pass without modification | 37 pre-existing tests unchanged, 47/47 pass | PASS |

### Test Results
- pytest (task-scope): 47 passed, 0 failed
- pytest (full suite): 3666 passed, 384 failed, 18 skipped — all failures pre-existing, none in task scope
- ruff (task-scope): clean (exit 0)
- ruff (full suite): 5 violations, all in mcp-kanban (unrelated to task scope)

### Architect Quality: 5/5
AC lines are specific, directly testable, no vagueness. Pattern reference to EntityExtractor (extractor.py:55-75) was actionable and helpful. Edge cases covered. Clean implementation path.

### Deduction Breakdown
- AC lines with no evidence: 0 (all evidenced) → −0.00
- Lint violations in scope: 0 → −0.00
- AC quality ≤ 3: N/A (score 5) → −0.00
- Missing reviewer evidence: N/A (present, detailed, 0.99 confidence) → −0.00
- Full-suite failures in task scope: 0 → −0.00
- Note: test-writer's 10 new tests were uncommitted — committed as leftover (c397e59)

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 55b7631 | fix(knowledge) | evaluator.py | #688 (pre-committed impl) |
| c397e59 | test | tests/test_evaluator.py | #700 |
