---
id: 769
title: 'P1-16: Impl — Content safety wrapping'
status: archived
priority: medium
created: '2026-04-10T10:56:34.284918+00:00'
updated: '2026-04-12T01:17:51.734576+00:00'
tags:
- phase-1
- scope:knowledge
- security
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Content safety predicate inverted to wrap-by-default. AUTHENTICATED_WEB wrapped automatically. IDPI scan integration point.

All P1-15 tests pass.

Parent: #751

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/769-content-safety-wrapping.md
- Sources: 6 studied, 5 high-relevance
- Recommendation: No implementation work remains — all wrapping objectives already shipped via #751 builder (commit 2dfae28b). IDPI scanning properly carved to #833/#834. Advance directly. (confidence: .90)
- Follow-up tasks created: #835 (archive redundant tasks #768, #786)
- Decision requests: none

### Key Findings
1. Predicate inversion DONE: content_safety.py has _TRUSTED_SOURCE_TYPES deny-list, should_wrap() returns True for unknown types, 11 tests pass
2. AUTHENTICATED_WEB wrapping DONE: ingest.py uses should_wrap(), old _is_url removed, 7 tests pass
3. IDPI scanning NOT HERE: already carved to #833 (RED) and #834 (GREEN) by #768 research
4. Task #786 redundant: describes exact same predicate inversion already implemented, plus stale dep on deleted #781
5. Task #768 superseded: its own research concluded AC1+AC2 redundant, created #833/#834 for AC3
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Wrapping + predicate inversion are tightly coupled; IDPI properly carved to #833/#834 |
| Interface clarity | PASS | `should_wrap()` and `wrap_untrusted_content()` have clear contracts; ingest.py integration at L188 is straightforward |
| Dependency correctness | PASS | No dependencies listed; correct since work shipped via parent #751 builder |
| Module layering | PASS | content_safety.py → ingest.py direction is correct (utility → pipeline) |
| TDD compliance | PASS | Tests exist in `test_content_safety_inversion_775.py` (11 tests) and `test_authenticated_content_pipeline_751.py` (multi-AC) |
| KISS/YAGNI | PASS | Minimal scope, deny-list approach is simplest correct design |
| Premise challenge | PASS | Work is already implemented; advancing through pipeline for verification is the correct path |
| Pattern consistency | PASS | Follows existing frozenset deny-list pattern, pydantic-style type hints |
| Security surface | PASS | This IS the security feature — defense-in-depth wrapping of untrusted content with sentinel tags |
| Single domain | PASS | scope:knowledge only |

### Code Quality Note
`content_safety.py` has duplicate constant definitions (`_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` at lines 10-17 and 48-54). Not a functional blocker — code review should flag for cleanup.

### Challenge Results
- Challenger: proceed — no blocking issues found, confirmed all 3 objectives implemented and tested
- Architect response: accepted

### Codebase Evidence
- `content_safety.py:22-23` — `_TRUSTED_SOURCE_TYPES = frozenset({"file", "file_glob", "text"})`, deny-list predicate
- `content_safety.py:25-42` — `should_wrap()` returns True for all non-trusted types
- `ingest.py:188-195` — integration: `should_wrap(_meta.get("source_type"))` → conditional `wrap_untrusted_content()`
- 11+ tests in `test_content_safety_inversion_775.py`, 7+ in `test_authenticated_content_pipeline_751.py`
- Research doc at `.owlbear/research/769-content-safety-wrapping.md` (confidence .90)
- Follow-up #835 created for archiving redundant tasks #768/#786

### Verdict: APPROVE
### Action Taken: Advanced to todo — all wrapping objectives already implemented and tested via #751 builder. No new code needed; pipeline agents will verify existing work.
[[2026-04-11]]
## Test-Writer Notes
- Pass-through: implementation-complete verification pass — all AC already implemented and tested via #751 builder (commit 2dfae28b). No unimplemented behavior exists; writing new tests would produce immediate passes, violating RED discipline.

**AC coverage (existing test files):**

| AC | Description | Test file | Tests |
|----|-------------|-----------|-------|
| AC1 | `should_wrap()` returns True for untrusted/unknown types (predicate inversion, deny-list) | `test_content_safety_inversion_775.py` | 11 PASS |
| AC2 | `should_wrap()` returns False for file/text/file_glob (trusted exempt set) | `test_content_safety_inversion_775.py` | (included above) |
| AC3 | AUTHENTICATED_WEB chunks wrapped in sentinel tags via IngestPipeline | `test_authenticated_content_pipeline_751.py` | 7+ PASS |
| AC4 | url_list + novel source types wrapped; file_glob not wrapped (predicate inversion) | `test_authenticated_content_pipeline_775.py` | 4 PASS |
| —  | `wrap_untrusted_content()` sentinel tag contract | `test_content_safety_735.py` | 6+ PASS |
| —  | IDPI scan integration | out of scope → #833 (RED), #834 (GREEN) |

- Total tests across AC: 105 collected, **105 PASS** (zero failures)
- IDPI scanning (AC3 from original brief) properly carved to #833/#834 and excluded here
- Architecture review confirmed TDD compliance PASS; advance for builder verification
[[2026-04-11]]
## Builder Notes
- **Pass-through**: implementation-complete verification pass per Test-Writer Notes.
- No code changes made — all AC implemented and tested via #751 builder (commit 2dfae28b).

**Test results (existing tests, no new code):**
| Test file | Tests |
|-----------|-------|
| test_content_safety_inversion_775.py | 11 PASS |
| test_authenticated_content_pipeline_751.py | 7 PASS |
| test_authenticated_content_pipeline_775.py | 4 PASS |
| test_content_safety_735.py | 6 PASS |
| + combined | **105 passed, 0 failed** |

**Lint:** ruff clean on content_safety.py + ingest.py (exit 0)
**Coverage:** not re-measured — no new code; prior coverage established by #751 builder
**Files changed:** 0
**Verdict:** DONE — advancing to review
[[2026-04-11]]
## Review Evidence

### Test Execution
Quality-Runner (independent run): **105 passed, 0 failed, 0 skipped**
Scoped test files: `test_content_safety_inversion_775.py`, `test_authenticated_content_pipeline_751.py`, `test_authenticated_content_pipeline_775.py`, `test_content_safety_735.py`

### Lint
ruff: **clean** (exit 0) on all scoped test files

### Coverage
- `content_safety`: **100%**
- `ingest`: **88%** (pre-existing; no new code written for this task)

### Step 5.0 — TestFromAC Coverage Audit

| AC Line | Mapped TestFromAC Class/Test | Would Fail If AC Violated? | Verdict |
|---------|------------------------------|---------------------------|---------|
| AC1: should_wrap() True for untrusted types | `TestFromAC_ShouldWrapPredicate.test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` | Yes — all use `is True` strict bool assertions | COVERED |
| AC2: should_wrap() False for file/text/file_glob/None | `TestFromAC_ShouldWrapPredicate.test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false`, `test_none_returns_false`, `test_empty_string_returns_false` | Yes — all use `is False` strict bool assertions | COVERED |
| AC3: AUTHENTICATED_WEB wrapped via IngestPipeline | `TestFromAC_AuthenticatedContentSafety.test_authenticated_web_sourced_ingest_wraps_chunk` (asserts open tag, close tag, AND original text in extracted call) | Yes — all 3 assertions required | COVERED |
| AC4: url_list + novel types wrapped; file_glob not wrapped | `TestFromAC_ContentSafetyInversion` (4 tests; url_list, novel future type, file_glob negation, source URL attribute) | Yes for wrapping tests; URL-attribute test LAX but compensated | COVERED |

### Step 5.1 — Security Review
- Deny-list predicate (unknown types default to wrapped): defense-in-depth ✓
- Advisory preamble instructs LLM to treat content as data-only (prompt injection mitigation) ✓
- Idempotency guard prevents double-wrapping ✓
- No hardcoded secrets, no shell injection, no path traversal, no unsafe deserialization ✓
- Minor: `url="{source_url}"` in sentinel open tag is not HTML-escaped. Pattern is theoretical-only — URLs have already survived HTTP fetch, output is LLM text not parsed XML. Flagged informational only (§6.1).

### Step 5.2 — TestFromAC Comparison
Builder declared Files changed: 0 (pass-through). Source control confirms no knowledge-module test files modified in this task cycle. No TestFromAC_* tests were weakened or removed. N/A — no modifications to compare.

### Step 5.3 — Test Quality
- `TestFromAC_ShouldWrapPredicate`: **STRONG** — `is True`/`is False` strict bool assertions, full boundary coverage (None, empty, all trusted types, multiple untrusted types)
- `TestFromAC_AuthenticatedContentSafety`: **STRONG** — asserts both sentinel tags present AND original text preserved; per-chunk test verifies all chunks wrapped
- `TestFromAC_ContentSafetyInversion`: **ADEQUATE** — primary wrapping tests check sentinel tag presence; URL-attribute supplementary test LAX (`source_url in call_text` only) but compensated by primary test in same class
- `TestFromAC_WrapUntrustedContent`: **STRONG** — idempotency, empty-string guard, open/close tag, original text, URL attribute

### Step 5.7 — Builder Process Quality
CLEAN — single pass-through attempt, consistent non-implementation rationale, no loop pattern.

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: should_wrap() True for untrusted/unknown | `content_safety.py:L43` — `return source_type not in _TRUSTED_SOURCE_TYPES` | `TestFromAC_ShouldWrapPredicate` (4 tests) | PASS |
| AC2: should_wrap() False for file/text/file_glob/None | `content_safety.py:L21` `_TRUSTED_SOURCE_TYPES = frozenset({"file","file_glob","text"})` + `L40` None guard | `TestFromAC_ShouldWrapPredicate` (5 tests) | PASS |
| AC3: AUTHENTICATED_WEB wrapped via IngestPipeline | `ingest.py:L193-198` — `should_wrap(_meta.get("source_type"))` → `wrap_untrusted_content()` | `TestFromAC_AuthenticatedContentSafety.test_authenticated_web_sourced_ingest_wraps_chunk` | PASS |
| AC4: url_list + novel wrapped; file_glob not wrapped | `content_safety.py:L43` + `ingest.py:L195-198` integration | `TestFromAC_ContentSafetyInversion` (4 tests) | PASS |

### Step 6 — Informational Findings
1. `content_safety.py` defines `_ADVISORY`, `_OPEN_TAG`, `_CLOSE_TAG` twice (lines 9-17 and 48-56). Python uses last definition; no functional impact. Code debt — first block should be removed.
2. `url="{source_url}"` attribute in sentinel open tag is unescaped. Theoretical injection only; URLs pre-validated by HTTP layer.

### Deductions
0 deductions — no Pass 1 failures.

### Verdict
Confidence: **0.95** → **PASS**
Action: advancing to docs.
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pass-through: Files changed = 0. Behavior shipped via #751 builder (commit 2dfae28b). `copilot-instructions.md` is branch-only; no module API section to update. |
| 2 | Module docstrings | No | N/A | No Python files modified in this task. Existing `content_safety.py` docstrings (module, `should_wrap`, `wrap_untrusted_content`) and `ingest.py` `ingest()` docstring are accurate and describe wrapping behavior correctly. Read and verified. |
| 3 | External attribution | No | N/A | Research doc cites only internal sources (code files, other tasks). No external URLs — no new `sources/overview.md` row needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/769-content-safety-wrapping.md` exists, linked from task body `## Research` section, follow-up #835 created for archiving redundant tasks. |

### Files Updated
None — no documentation changes required.

### Scratch Files
None found — no `.owlbear/scratch/769-*` files to clean.
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: should_wrap() True for untrusted/unknown types | content_safety.py:L42 `return source_type not in _TRUSTED_SOURCE_TYPES`; 4 tests in TestFromAC_ShouldWrapPredicate | PASS |
| AC2: should_wrap() False for file/text/file_glob/None | content_safety.py:L22 `_TRUSTED_SOURCE_TYPES = frozenset({"file","file_glob","text"})` + L40 None guard; 5 tests | PASS |
| AC3: AUTHENTICATED_WEB wrapped via IngestPipeline | ingest.py:L201-209 `should_wrap(_meta.get("source_type"))` → `wrap_untrusted_content()`; TestFromAC_AuthenticatedContentSafety | PASS |
| AC4: url_list + novel types wrapped; file_glob not | content_safety.py:L42 + ingest.py:L201-209; 4 tests in TestFromAC_ContentSafetyInversion | PASS |

### Test Results
- pytest: 3,538 passed, 275 failed, 8 skipped — all 275 failures in kanban/orchestrator/planner scope (pre-existing), 0 failures in content safety scope
- ruff: clean (exit 0)

### Architect Quality: 3/5
AC embedded in prose description, not enumerated. Task was entirely redundant — all work shipped via #751 builder (commit 2dfae28b). Decomposition created unnecessary pass-through. Architect review correctly identified this and advanced; right call.

### Deduction Breakdown
- AC quality ≤ 3: -.03

### Confidence: 0.97
### Action: archive