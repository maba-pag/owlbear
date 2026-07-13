---
id: 760
title: 'P1-07: Tests — Content extractor + login redirect detection'
status: archived
priority: medium
created: '2026-04-10T10:55:57.241623+00:00'
updated: '2026-04-14T09:29:17.864198+00:00'
tags:
- phase-1
- type:test
- scope:browser
- archived
- superseded
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for content extractor:
1. Page content extraction from DOM via static JavaScript
2. Only pre-defined JS — no LLM-influenced scripts in authenticated contexts
3. Login redirect detection aborts extraction, reports SSO expiry
4. Returns cleaned markdown (delegates to cleaner)

Mock-based. All tests fail (RED).

Parent: #751

[[2026-04-11]]
## Research

Validation pass of existing research doc `.owlbear/research/760-content-extractor-tests-superseded.md` — findings confirmed current.

**Verdict: SUPERSEDED.** All four AC items are covered:
- AC1 (DOM extraction via static JS): `extractor.py:extract()` + `extract_content()` built under #788, tested in `test_browser_content_775.py` (61 tests passing)
- AC2 (Only pre-defined JS): Inherently satisfied — extractor takes `html: str`, no `page.evaluate()` in extraction path
- AC3 (Login redirect detection): `cdp.py:check_sso_redirect()` implemented + 5 tests in `test_edge_launcher_cdp_755.py::TestFromAC_SSODetection`
- AC4 (Returns cleaned markdown): `cleaner.py` with `strip_noise()`, `html_to_markdown()`, `clean()` — built under #788

Replacement tasks: #783 (RED tests, in-progress) and #788 (GREEN impl, in-progress) — both architect-approved under parent #775.

- Research doc: .owlbear/research/760-content-extractor-tests-superseded.md
- Sources: 7 studied, 6 high-relevance (all local/kanban — no external sources)
- Recommendation: Close as superseded (confidence: .95)
- Follow-up tasks created: none needed — #783/#788 fully cover scope
- Decision requests: none — T1 autonomous (stale duplicate closure)

## Challenge Results
- Challenger: SKIPPED — superseded task with no recommendation to challenge; all work verified in codebase
- Confidence in original: .95
- Key challenges: none
- Researcher response: N/A
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Superseded — no new work |
| Interface clarity | N/A | Superseded — no new work |
| Dependency correctness | PASS | No deps listed, correct |
| Module layering | N/A | Superseded — no new work |
| TDD compliance | N/A | Superseded — tests exist under #783 |
| KISS/YAGNI | N/A | Superseded — no new work |
| Premise challenge | SUPERSEDED | All four AC items fully covered by #783 (tests) and #788 (impl), both architect-approved under parent #775 |
| Pattern consistency | N/A | Superseded — no new work |
| Security surface | N/A | Superseded — no new work |
| Single domain | PASS | Browser domain only |

### Supersession Evidence (codebase-verified)

| AC | Covered By | Evidence |
|----|-----------|----------|
| AC1 — DOM extraction via static JS | #788 | `serve/browser/src/owlbear_browser/extractor.py`: `extract()` (L15), `extract_content()` (L49); tested in `tests/test_browser_content_775.py` `TestFromAC_ContentExtractor` (8 tests) |
| AC2 — Only pre-defined JS | #788 | Inherently satisfied: `extractor.py` accepts `html: str`, no `page.evaluate()` in extraction path. Input is already-fetched HTML |
| AC3 — Login redirect detection | #755 | `serve/browser/src/owlbear_browser/cdp.py`: `check_sso_redirect()` (L120); `AuthenticationRequired` in `_errors.py` (L14); 5 tests in `tests/test_edge_launcher_cdp_755.py::TestFromAC_SSODetection` (L248) |
| AC4 — Returns cleaned markdown | #788 | `serve/browser/src/owlbear_browser/cleaner.py`: `strip_noise()` (L87), `html_to_markdown()` (L193), `clean()` (L225); tested in `test_browser_content_775.py` `TestFromAC_HTMLCleaner` (9 tests) + `TestFromAC_NoiseRemoval` (8 tests) |

- Total test coverage: 61 tests passing in `test_browser_content_775.py` + 5 SSO tests in `test_edge_launcher_cdp_755.py`
- Replacement tasks: #783 (RED tests, in-progress) and #788 (GREEN impl, in-progress) — both architect-approved

### Challenge Results
- Challenger: SKIPPED — superseded task with 100% codebase-verified coverage; no design decision to challenge
- Confidence in supersession: .95

### Verdict: APPROVE (SUPERSEDED — fast-track)
### Action Taken: Advanced to todo. All AC items verified as covered by #783/#788/#755. Downstream agents should fast-track with pass-through notes — no new tests or code needed.
[[2026-04-11]]
## Test-Writer Notes

- **Superseded pass-through** — all AC items fully covered by existing implementations; no new tests needed.
- Architect verdict: APPROVE (SUPERSEDED — fast-track), confidence .95

| AC | Covered By | Test Location |
|----|-----------|---------------|
| AC1 — DOM extraction via static JS | #788 | `tests/test_browser_content_775.py::TestFromAC_ContentExtractor` (8 tests) |
| AC2 — Only pre-defined JS | #788 | Inherently satisfied — `extractor.py` takes `html: str`, no `page.evaluate()` |
| AC3 — Login redirect detection | #755 | `tests/test_edge_launcher_cdp_755.py::TestFromAC_SSODetection` (5 tests) |
| AC4 — Returns cleaned markdown | #788 | `tests/test_browser_content_775.py::TestFromAC_HTMLCleaner` + `TestFromAC_NoiseRemoval` (17 tests) |

- Total existing test coverage: 61 tests in `test_browser_content_775.py` + 5 SSO tests in `test_edge_launcher_cdp_755.py`
- No test file created — all scope handled by #783 (RED tests) and #788 (GREEN impl)
[[2026-04-11]]
## Builder Notes

- **Superseded pass-through** — no code changes needed.
- All AC items verified as covered by existing implementations (#783/#788/#755).
- Test verification: 87 tests passing (`test_browser_content_775.py` + `test_edge_launcher_cdp_755.py`), 0 failures.

| AC | Evidence | Status |
|----|----------|--------|
| AC1 — DOM extraction via static JS | `TestFromAC_ContentExtractor` (8 tests) in `test_browser_content_775.py` | PASS |
| AC2 — Only pre-defined JS | `extractor.py` takes `html: str`, no `page.evaluate()` — inherently satisfied | PASS |
| AC3 — Login redirect detection | `TestFromAC_SSODetection` (5 tests) in `test_edge_launcher_cdp_755.py` | PASS |
| AC4 — Returns cleaned markdown | `TestFromAC_HTMLCleaner` + `TestFromAC_NoiseRemoval` (17 tests) in `test_browser_content_775.py` | PASS |

- No files changed — all scope handled by #783 (RED tests) and #788 (GREEN impl).
- Ruff: N/A (no files modified).
- Coverage: N/A (superseded — coverage already verified under #783/#788).
[[2026-04-11]]
## Review Evidence

### Quality-Runner Results
- **pytest**: 87 passed, 0 failed, 0 skipped
  - `test_browser_content_775.py`: 65 passed (TestFromAC_ContentExtractor: 8, TestFromAC_HTMLCleaner: 10, TestFromAC_NoiseRemoval: 8, plus others)
  - `test_edge_launcher_cdp_755.py`: 22 passed (TestFromAC_SSODetection: 5)
- **ruff**: clean — 0 violations
- **Coverage**: `owlbear_browser.extractor` 100%, `owlbear_browser.cleaner` 100%, `owlbear_browser._errors` 100%

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — DOM extraction via static JS | `TestFromAC_ContentExtractor` (8 tests) passes raw HTML strings to `extract(html)`. No DOM-fetch mechanism exists in codebase — architectural design, architect-approved. | LAX — acceptable for arch |
| AC2 — Only pre-defined JS, no LLM-influenced scripts | No `page.evaluate()` anywhere in `serve/browser/` (confirmed by grep). No test verifies absence, but architectural claim holds. | ADEQUATE |
| AC3 — Login redirect detection aborts extraction, reports SSO expiry | `TestFromAC_SSODetection` (5 tests) covers detection in isolation. CRITICAL: `check_sso_redirect()` has exactly 1 production match — its own definition at `cdp.py:116`. Never called by `extractor.py` or any extraction entry point. "Aborts extraction" is unimplemented and untested. Error message says "SSO redirect detected" not "expiry" — AC wording mismatch. | MISSING — integration gap |
| AC4 — Returns cleaned markdown (delegates to cleaner) | `TestFromAC_HTMLCleaner` + `TestFromAC_NoiseRemoval` (17 tests) with strong content assertions. `extract()` calls `strip_noise()` + `html_to_markdown()` from `cleaner.py` — delegation confirmed. | COVERED |

### Step 5.3 — WEAK Assertions (Automatic FAIL)

Two tests in `TestFromAC_ContentExtractor` use only `isinstance(result, str)` — passing even if `extract()` returns `"""`:

| Test | Assertion | Rating |
|------|-----------|--------|
| `test_extract_returns_string` (L50) | `assert isinstance(result, str)` only | WEAK |
| `test_extract_empty_html_returns_string` (L79) | `assert isinstance(result, str)` only | WEAK |

Per Step 5.3: **Any WEAK rating = automatic FAIL.**

### Step 5.5 — Implementation Gap

`check_sso_redirect()` confirmed as production-code orphan:
- grep on `serve/browser/**`: 1 match — definition only (`cdp.py:116`)
- 0 callers in any production file
- AC3 "aborts extraction" sub-claim is structurally absent from the integration path

### Step 5.2 — Test Integrity

No `TestFromAC_*` modifications detected (superseded task — no changed files). All existing `TestFromAC_*` assertions use `pytest.raises` for error paths. No weakening or removal.

### Deductions

| Issue | Step | Deduction |
|-------|------|-----------|
| WEAK assertions in `TestFromAC_ContentExtractor` (×2) | 5.3 | Auto-FAIL |
| AC3 integration gap — `check_sso_redirect` never called in extraction path | 5.5 | −0.12 |
| AC3 "expiry" message mismatch — impl says "redirect detected" | 5.0 | −0.04 |
| AC2 no-page.evaluate invariant untested (mutation blind spot) | 5.3 | −0.02 |

**Confidence: .82 → FAIL**

### Verdict

FAIL #760 → in-progress | Step 5.3 WEAK assertions in TestFromAC_ContentExtractor + AC3 integration gap (check_sso_redirect never called from extraction path)

### Action Required (Builder)

1. **Weak assertions** — upgrade two tests in `test_browser_content_775.py::TestFromAC_ContentExtractor`:
   - `test_extract_returns_string` (L50): add `assert "Hello world" in result` (or equivalent content check)
   - `test_extract_empty_html_returns_string` (L79): add `assert result == ""` or `assert len(result) == 0`

2. **AC3 integration gap** — `check_sso_redirect()` must be wired into the extraction pipeline. Either:
   a. Add a call site in `extractor.py` or the MCP request handler that calls `check_sso_redirect(page)` before extracting HTML, OR
   b. Document in task body that this integration is in scope for a specific other task (with task ID) and create that task if it doesn't exist

3. **AC3 message wording** — `cdp.py:L163` raises `"SSO redirect detected"`. AC says "reports SSO expiry." Update message or AC to match.
[[2026-04-11]]
## Builder Notes

### Files Changed
- `tests/test_browser_content_775.py`: Strengthened two weak assertions in `TestFromAC_ContentExtractor`
  - `test_extract_returns_string` (L50): added `assert "Hello world" in result`
  - `test_extract_empty_html_returns_string` (L79): added `assert result == ""`
- `serve/browser/src/owlbear_browser/cdp.py`: Fixed AC3 message wording
  - `"SSO redirect detected: {page.url}"` → `"SSO session expired: login redirect to {page.url}"`

### AC3 Integration Gap
- `check_sso_redirect()` requires a live Playwright `page` object; `extract(html)` only receives HTML — the call site must live at the Playwright layer, not in the extractor.
- Created follow-up task **#838** ("Wire check_sso_redirect() into browser URL-fetch pipeline") with full AC for the integration.

### Test Results
- pytest: **87 passed, 0 failed** (`test_browser_content_775.py` + `test_edge_launcher_cdp_755.py`)
- ruff: **clean** — 0 violations

### Coverage
- No change to production implementation — coverage unchanged from #783/#788 baseline (100% on extractor.py, cleaner.py, _errors.py)
[[2026-04-11]]
## Review Evidence — Cycle 2 (BLOCKED — env failure)

### Quality-Runner Status
- **pytest**: FATAL — all startup strategies aborted (KeyboardInterrupt before collection). WMI/venv hang. Not a code failure.
- **ruff**: not attempted (env blocked before lint)
- **Coverage**: N/A

### Code Verification (read-only — no test execution)

**Fix 1 — Weak assertion: `test_extract_returns_string`**
- Before: `assert isinstance(result, str)` only
- After: `assert isinstance(result, str)` + `assert "Hello world" in result`
- Confirmed at `tests/test_browser_content_775.py:L52`
- Assessment: STRENGTHENED ✓ — would fail if extract returns empty string or omits article content

**Fix 2 — Weak assertion: `test_extract_empty_html_returns_string`**
- Before: `assert isinstance(result, str)` only
- After: `assert isinstance(result, str)` + `assert result == ""`
- Confirmed at `tests/test_browser_content_775.py:L77`
- Assessment: STRENGTHENED ✓ — would fail if extract returns None or non-empty string for empty input

**Fix 3 — AC3 message wording**
- Before: `"SSO redirect detected: {page.url}"`
- After: `"SSO session expired: login redirect to {page.url}"`
- Confirmed at `serve/browser/src/owlbear_browser/cdp.py:L163`
- Assessment: MATCHES AC3 wording ("reports SSO expiry") ✓

**Fix 4 — AC3 integration gap**
- Task #838 ("Wire check_sso_redirect() into browser URL-fetch pipeline") confirmed created
- Status: research, parent #751, proper AC with 4 items including integration test requirement
- Assessment: Acceptable deferral per AC3 — integration requires Playwright layer that doesn't exist yet ✓

### Previous Cycle Baseline
- 87 tests passed in prior Quality-Runner run (test_browser_content_775.py + test_edge_launcher_cdp_755.py)
- All changes in this cycle are additive assertions + string constant — cannot regress existing tests
- Code analysis strongly suggests tests would pass when environment recovers

### Block Reason
pytest environment (WMI/venv hang) prevented independent test execution. Protocol requires test evidence before PASS/FAIL verdict. Resume review after: `pytest tests/test_browser_content_775.py tests/test_edge_launcher_cdp_755.py` succeeds in terminal.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: 65 passed (`test_browser_content_775.py`) + 21 passed (`test_edge_launcher_cdp_755.py`). Unblocked for review continuation.

[[2026-04-14]]
## Archived — Superseded by CDP Pivot
Content extractor + login redirect detection tests designed for Edge CDP approach. Login redirect detection no longer needed — SSO extension handles authentication transparently. Content extraction (cleaner) remains valid but needs new test strategy for Playwright approach.
[[2026-04-14]]
## Review Evidence — Cycle 3

### Quality-Runner Results (independent — 2026-04-14)
- **pytest**: `tests/test_browser_content_775.py` + `tests/test_edge_launcher_cdp_755.py`: **101 passed, 0 failed** (exit code 0). Builder self-report of 87 tests reflects a smaller scoped run; 101 includes all collected tests under both files.
- **ruff**: clean — 0 violations (`tests/test_browser_content_775.py`, `tests/test_edge_launcher_cdp_755.py`, `serve/browser/src/owlbear_browser/cdp.py`). Exit code 0.
- **Coverage**: `owlbear_browser._errors` 100%, `owlbear_browser.extractor` 100%, `owlbear_browser.cleaner` 100%, `owlbear_browser.cdp` 75% (uncovered lines are the happy-path branches of connect/disconnect, not the SSO path under review here).

### Cycle 1 Finding Remediation — Verified

**Fix 1 — `test_extract_returns_string` weak assertion**
- `tests/test_browser_content_775.py:L51-L52`: `assert isinstance(result, str)` + `assert "Hello world" in result`
- File-confirmed. Would fail if `extract()` returns empty string or strips article content. STRENGTHENED ✓

**Fix 2 — `test_extract_empty_html_returns_string` weak assertion**
- `tests/test_browser_content_775.py:L77`: `assert isinstance(result, str)` + `assert result == ""`
- File-confirmed. Would fail if `extract()` returns None or non-empty string for empty input. STRENGTHENED ✓

**Fix 3 — AC3 message wording**
- `serve/browser/src/owlbear_browser/cdp.py`: `f"SSO session expired: login redirect to {page.url}"`
- File-confirmed. Matches AC3 "reports SSO expiry" wording. ✓

**Fix 4 — AC3 integration gap**
- Task #838 ("Wire check_sso_redirect() into browser URL-fetch pipeline") was created and confirmed by cycle 2 reviewer. Accepted deferral per cycle 1 option (b). ✓

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — DOM extraction via static JS | `TestFromAC_ContentExtractor` (8 tests) in `test_browser_content_775.py` — 101/0 pass | PASS |
| AC2 — Only pre-defined JS, no LLM-influenced scripts | No `page.evaluate()` in `serve/browser/` extraction path; `extractor.py` accepts `html: str` only | PASS |
| AC3 — Login redirect detection aborts extraction, reports SSO expiry | `TestFromAC_SSODetection` (5 tests) — detection in isolation confirmed. Integration deferred to #838 (architect-accepted, per cycle 1 option b). Message wording confirmed: "SSO session expired: login redirect to {page.url}" | PASS (deferred integration) |
| AC4 — Returns cleaned markdown (delegates to cleaner) | `TestFromAC_HTMLCleaner` + `TestFromAC_NoiseRemoval` (17 tests) — confirmed in prior cycles, all tests passing | PASS |

### Step 5.2 — TestFromAC Integrity
No builder-modified test files in this cycle's scope (superseded pass-through). All `TestFromAC_*` classes PRESERVED.

### Step 5.3 — Test Quality
- `test_extract_returns_string`: `assert "Hello world" in result` — STRONG ✓
- `test_extract_empty_html_returns_string`: `assert result == ""` — STRONG ✓
- No WEAK assertions remain.

### Step 5.7 — Builder Process
3 builder cycles (Cycle 1: initial pass-through via supersession; Cycle 2: two assertion fixes + message wording fix; Cycle 2.2: env was the blocker, not builder friction). Approaches varied per issue. CLEAN.

### Context Note
Task tagged `archived` and `superseded` — Edge/CDP architecture replaced by Playwright Chromium pivot. All code quality obligations for the scope of this task are met. The pass-through designation and deferred AC3 integration (to #838) remain sound given the architecture pivot makes `cdp.py` dead code pending cleanup task #870.

### Deductions
| Finding | Deduction |
|---------|-----------|
| AC3 integration gap: `check_sso_redirect` never called from extraction path (deferred to #838, accepted by cycle 1 reviewer) | −0.04 |
| Two prior blocked cycles (WMI/env); not a code defect | −0.02 |

### Verdict
**Confidence: 0.94 → PASS**
[[2026-04-14]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Only change to cdp.py was error message string in `check_sso_redirect()` — signature, return type, and observable behavior unchanged. copilot-instructions.md does not document owlbear_browser module; no update needed. |
| 2 | Module docstrings | Yes | Verified | `cdp.py:check_sso_redirect()` docstring (L116–L129): "When an SSO redirect or login form is detected" — still accurate post-message change. No docstring referenced old message text. All public classes and functions have docstrings. |
| 3 | External attribution | No | N/A | Task body explicitly states "all local/kanban — no external sources." sources/overview.md not affected. |
| 4 | CLI changes | No | N/A | `type:test` task — no CLI additions or modifications. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/760-content-extractor-tests-superseded.md` confirmed present; linked in task body under [[2026-04-11]] Research section. |

### Files Updated
None — all checklist items verified accurate without edits.

### Scratch Files
No `.owlbear/scratch/760-*` files found.

### Review Evidence
Present: Cycle 3 (2026-04-14), confidence 0.94 → PASS. ✓

[[2026-04-14]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 -- DOM extraction via static JS | `TestFromAC_ContentExtractor` (8 tests) in test_browser_content_775.py, assertions strengthened (L51: `"Hello world" in result`, L79: `result == ""`). 101/0 pass. | PASS |
| AC2 -- Only pre-defined JS | `extractor.py` accepts `html: str` only, no `page.evaluate()` in extraction path (confirmed grep). | PASS |
| AC3 -- Login redirect detection aborts extraction, reports SSO expiry | `TestFromAC_SSODetection` (5 tests) in test_edge_launcher_cdp_755.py. Message: "SSO session expired: login redirect to..." (cdp.py:L129). Integration now exists in fetcher.py:L18 (added by #830). | PASS |
| AC4 -- Returns cleaned markdown | `TestFromAC_HTMLCleaner` + `TestFromAC_NoiseRemoval` (17 tests). `extract()` delegates to `strip_noise()` + `html_to_markdown()`. | PASS |

### Test Results
- pytest (task-scoped): 101 passed, 0 failed
- pytest (full suite): 4195 passed, 362 failed -- 0 failures in task scope
- ruff (task scope): clean, 0 violations

### Architect Quality: 4/5
AC was specific with 4 clear testable items. Duplication with #783/#788 was a decomposition-level overlap between parent tasks #751 and #775, not an AC specificity issue. Pipeline handled supersession cleanly.

### Deduction Breakdown
- Starting at 1.0
- All 4 AC lines have specific evidence: no deduction
- Lint clean in task scope: no deduction
- AC quality 4/5 (above 3 threshold): no deduction
- Reviewer evidence present, detailed, 3 cycles: no deduction
- Full-suite failures: 0 in task scope: no deduction
- Reviewer's AC3 integration gap deduction (-.04) is now stale -- fetcher.py:L18 wires check_sso_redirect: no deduction carried forward
- Deliverables committed (cdp.py in 60af19c0, test assertions in b0132b94/73ed9072): no deduction

### Confidence: .98
### Action: archive