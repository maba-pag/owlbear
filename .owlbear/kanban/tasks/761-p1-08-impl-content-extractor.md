---
id: 761
title: 'P1-08: Impl — Content extractor'
status: todo
priority: needed
created: '2026-04-10T10:55:57.270970+00:00'
updated: '2026-04-12T22:43:25.306132+00:00'
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