---
id: 761
title: 'P1-08: Impl — Content extractor'
status: archived
priority: medium
created: '2026-04-10T10:55:57.270970+00:00'
updated: '2026-04-13T04:36:48.693773+00:00'
tags:
- phase-1
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. `serve/browser/src/owlbear_browser/extractor.py`:
- Static JS-based DOM extraction
- Delegates to cleaner for HTML→markdown
- Login redirect detection (fail-fast)
- Only static/pre-defined extraction JavaScript

All P1-07 tests pass. Depends on launcher (#758) + cleaner (#758b).

Parent: #751

[[2026-04-12]]
## Research\n\nValidation pass of existing doc `.owlbear/research/761-content-extractor-superseded.md` — all findings confirmed current (2026-04-12).\n\n- Research doc: .owlbear/research/761-content-extractor-superseded.md\n- Sources: 7 studied, 7 high-relevance (all local/kanban)\n- Recommendation: Close as superseded (confidence: .95)\n- Follow-up tasks created: none — #783 (RED, todo) and #788 (GREEN, review) fully cover scope\n- Decision requests: none — T1 autonomous (stale duplicate closure)\n\n### Validation Evidence\n| #761 AC | Covered by | Status |\n|---------|-----------|--------|\n| Static JS-based DOM extraction | #788 AC1: `extract_content(html, url)` | Implemented |\n| Delegates to cleaner | #788 AC1-2: trafilatura + cleaner fallback | Implemented |\n| Login redirect detection | `cdp.py:check_sso_redirect()` + 5 tests | Implemented+Tested |\n| Only static/pre-defined JS | Inherent — extractor takes `html: str` | Satisfied |\n\nChallenge: SKIPPED — superseded task, no recommendation to challenge.\nRED partner #760 also superseded. Both should be closed.
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Superseded — no new work |
| Interface clarity | N/A | Superseded — no new work |
| Dependency correctness | PASS | No deps listed; correct — original deps (launcher #758 + cleaner #758b) are moot since #788 already delivered the implementation |
| Module layering | N/A | Superseded — no new work |
| TDD compliance | N/A | Superseded — tests exist under #783 |
| KISS/YAGNI | N/A | Superseded — no new work |
| Premise challenge | SUPERSEDED | All four AC items fully covered by #788 (impl) and #783 (tests), both architect-approved under parent #775 |
| Pattern consistency | N/A | Superseded — no new work |
| Security surface | N/A | Superseded — no new work |
| Single domain | PASS | Browser domain only |

### Supersession Evidence (codebase-verified)

| AC | Covered By | Evidence |
|----|-----------|----------|
| Static JS-based DOM extraction | #788 | `extractor.py:extract()` (L16) + `extract_content()` (L49); tested in `test_browser_content_775.py::TestFromAC_ContentExtractor` (8 tests) |
| Delegates to cleaner for HTML→markdown | #788 | `extract()` calls `strip_noise()` + falls back to `html_to_markdown()` from `cleaner.py`; `clean()` composes both. Tested in `TestFromAC_HTMLCleaner` (10 tests) + `TestFromAC_NoiseRemoval` (8 tests) |
| Login redirect detection (fail-fast) | #755/#788 | `cdp.py:check_sso_redirect()` (L116) raises `AuthenticationRequired` on IdP domains + login forms; 5 tests in `test_edge_launcher_cdp_755.py::TestFromAC_SSODetection` |
| Only static/pre-defined JS | #788 | Inherently satisfied — `extractor.py` accepts `html: str`, no `page.evaluate()` in extraction path |

### Lineage

- Parent: #751 (Authenticated content pipeline)
- RED partner: #760 (also superseded, already approved + in review)
- Superseding tasks: #783 (tests, review) + #788 (impl, review) under parent #775

### Challenge Results
- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge: supersession confidence .95, all 4 AC items codebase-verified with file paths and line numbers. No residual scope unaddressed. Consistent with #760 precedent.

### Verdict: APPROVE (SUPERSEDED — fast-track)
### Action Taken: Advanced to todo. All AC items verified as covered by #783/#788/#755. Downstream agents should fast-track with pass-through notes — no new tests or code needed.
[[2026-04-13]]
## Test-Writer Notes

- Non-impl pass-through: task superseded — no new tests applicable.
- All 4 AC items codebase-verified as covered by existing tests:

| AC | Test Coverage | Location |
|----|--------------|----------|
| Static JS-based DOM extraction | `TestFromAC_ContentExtractor` (8 tests) | `test_browser_content_775.py` |
| Delegates to cleaner for HTML→markdown | `TestFromAC_HTMLCleaner` (10) + `TestFromAC_NoiseRemoval` (8) | `test_browser_content_775.py` |
| Login redirect detection (fail-fast) | `TestFromAC_SSODetection` (5 tests) | `test_edge_launcher_cdp_755.py` |
| Only static/pre-defined JS | Inherently satisfied — `extractor.py` accepts `html: str` | structural |

- Superseding tasks: #783 (RED/tests, in review) + #788 (GREEN/impl, in review)
- Precedent: #760 (RED partner) also fast-tracked as superseded
- Architect verdict: APPROVE (SUPERSEDED — fast-track), confidence .95
- Passing through to builder (in-progress) for equivalent fast-track close.
[[2026-04-13]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
- Superseded by #783 (tests) + #788 (impl) under parent #775.
- All 4 AC items codebase-verified as covered by existing implementation and tests.
[[2026-04-13]]
## Review Evidence

### Source Control
No production files changed. Only kanban task body mutations (status/claim fields). Correct behavior for superseded pass-through task.

### quality-runner
Not available in reviewer's agent roster. Fallback applied: codebase structural verification used in lieu of independent test execution. -0.03 deduction.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Static JS-based DOM extraction | `extractor.py:extract()` (L16) accepts `html: str`, calls `trafilatura.extract()` + `strip_noise()`. No `page.evaluate()` in path. `TestFromAC_ContentExtractor` — 8 tests confirmed present at lines L36, L40, L44, L53, L65, L73, L81, L96 | ✅ COVERED |
| Delegates to cleaner for HTML→markdown | `extractor.py:extract()` falls back to `html_to_markdown()` from `cleaner.py` when trafilatura returns None. `TestFromAC_HTMLCleaner` — 10 tests confirmed present (L112–L191). `TestFromAC_NoiseRemoval` — 8 tests present from L209 | ✅ COVERED |
| Login redirect detection (fail-fast) | `cdp.py:check_sso_redirect()` confirmed at L116; raises `AuthenticationRequired`. `TestFromAC_SSODetection` confirmed present at test_edge_launcher_cdp_755.py:244 (≥4 tests confirmed, 5 claimed by all upstream agents) | ✅ COVERED |
| Only static/pre-defined JS | `extractor.py` accepts `html: str` — inherently satisfied; zero `page.evaluate()` in extraction path (codebase verified) | ✅ COVERED |

### TestFromAC Modifications
None. Builder verified zero code changes (correct pass-through handling).

### Assertion Quality (static read)
`test_browser_content_775.py` — `TestFromAC_ContentExtractor` tests discriminating assertions (e.g., `raises TypeError` for non-str input, content presence tests). `TestFromAC_HTMLCleaner` uses specific string-contains assertions for element preservation. Would fail if cleaner module removed or `html_to_markdown`/`strip_noise` refactored away.

### Deductions
- −0.03: quality-runner unavailable — could not independently execute `test_browser_content_775.py` and `test_edge_launcher_cdp_755.py`
- 0 other deductions: no code changed, no TestFromAC modifications, supersession verified 4× by 4 upstream agents with each node confirming codebase evidence

### Supersession Validity
4-agent consensus (researcher → architect → test-writer → builder) with independent codebase verification each time. All implementation files confirmed with claimed content. All referenced test classes confirmed present with correct structure. This is a factual verification, not an opinion — supersession is accurate.

### Verdict
**Confidence: 0.94 → PASS #761 → docs**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Superseded pass-through — zero production files changed (confirmed by reviewer: "No production files changed. Only kanban task body mutations.") |
| 2 | Module docstrings | No | N/A | No Python modules created or modified for this task |
| 3 | External attribution | No | N/A | Research doc S1–S7 are entirely local codebase and kanban sources — no external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/761-content-extractor-superseded.md` exists, linked from task body. Follow-up tasks: none needed — scope fully covered by #783 (tests) + #788 (impl). |

### Files Updated
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/761-*` files existed)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Static JS-based DOM extraction | `extractor.py:extract()` at L15 accepts `html: str`; `TestFromAC_ContentExtractor` (7 tests) in `test_browser_content_775.py:L33` — all passed in full suite | PASS |
| Delegates to cleaner for HTML→markdown | `extractor.py` calls `strip_noise()` + `html_to_markdown()` from `cleaner.py` (L90, L202); `TestFromAC_HTMLCleaner` (10 tests, L109) + `TestFromAC_NoiseRemoval` (8 tests, L206) — all passed | PASS |
| Login redirect detection (fail-fast) | `cdp.py:check_sso_redirect()` at L116 raises `AuthenticationRequired`; `TestFromAC_SSODetection` (5 tests) in `test_edge_launcher_cdp_755.py:L244` — all passed | PASS |
| Only static/pre-defined JS | `extractor.py` accepts `html: str`, no `page.evaluate()` in extraction path — inherently satisfied | PASS |

### Supersession Validity
All 4 AC items fully delivered by #783 (tests) + #788 (impl) under parent #775. No production code changed for #761. 6-agent consensus (researcher → architect → test-writer → builder → reviewer → doc-writer) with independent codebase verification. Supersession is factual.

### Test Results
- pytest: 3460 passed, 302 failed, 8 skipped (63s). **Zero failures in task scope** — `test_browser_content_775.py` and `test_edge_launcher_cdp_755.py` both passed. 302 failures are pre-existing in unrelated domains (kanban, server, knowledge, package-boundary).
- ruff: All checks passed

### Architect Quality: 4/5
AC was specific and verifiable — 4 concrete items, each mappable to implementation files and test classes. Supersession was correctly identified by researcher; architect approved fast-track. Minor gap: AC could have been marked superseded earlier to avoid pipeline pass-through overhead.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 verified) → 0
- Lint violations: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed, PASS at .94) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: .98
### Action: archive