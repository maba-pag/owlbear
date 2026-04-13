# P1-07: Tests — Content extractor + login redirect detection — Superseded

> **Owning task:** #760 — P1-07: Tests — Content extractor + login redirect detection
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #760 is a RED-phase test task (parent #751) covering four AC items:
1. Page content extraction from DOM via static JavaScript
2. Only pre-defined JS — no LLM-influenced scripts in authenticated contexts
3. Login redirect detection aborts extraction, reports SSO expiry
4. Returns cleaned markdown (delegates to cleaner)

The question: is #760 still needed, or has its scope been covered by other tasks?

## 2. Sources Studied

| # | Source | Kind | Relevance |
|---|--------|------|-----------|
| S1 | `serve/browser/src/owlbear_browser/cdp.py` — `check_sso_redirect()` | Local | 1.0 |
| S2 | `tests/test_edge_launcher_cdp_755.py` — `TestFromAC_SSODetection` (5 tests) | Local | 1.0 |
| S3 | Task #783 body + architect review (RED tests for extractor+cleaner) | Kanban | 1.0 |
| S4 | Task #788 body + architect review (GREEN impl for extractor+cleaner) | Kanban | 1.0 |
| S5 | Task #761 body (GREEN partner of #760) | Kanban | .95 |
| S6 | `serve/browser/src/owlbear_browser/_errors.py` — `AuthenticationRequired` | Local | .90 |
| S7 | `.owlbear/research/751-authenticated-content-pipeline.md` (parent research) | Local | .85 |

## 3. Analysis — AC-by-AC Coverage Map

| #760 AC | Covered by | Evidence | Status |
|---------|-----------|----------|--------|
| AC1: DOM extraction via static JS | #788 refined AC1 (`extract_content(html, url)`) | `page.content()` is trivial CDP call; extractor operates on HTML strings | **Superseded** |
| AC2: Only pre-defined JS | #788 architecture | Extractor takes `html: str` — no `page.evaluate()` in extraction path; security constraint inherently satisfied | **Superseded** |
| AC3: Login redirect detection | `cdp.py:check_sso_redirect()` + tests (S1, S2) | 5 passing tests: IdP URL, login form, propagation, exception type, normal page | **Implemented+Tested** |
| AC4: Returns cleaned markdown | #783/#788 refined AC | `extractor.py` + `cleaner.py` with function signatures specified | **Superseded** |

### 3.1 Overlap Evidence

The #783 architect review explicitly notes (S3):
> "Overlapping tasks #760/#761 (research status, parent #751) cover similar
> scope from a prior decomposition. #783/#788 from #775 are the active pair."

### 3.2 What About #761 (GREEN Partner)?

Task #761 describes the GREEN implementation of #760's tests. Its scope:
- `extractor.py`: superseded by #788 refined AC (same file, more specific signatures)
- Delegates to cleaner: superseded by #788 (`cleaner.py` with `strip_noise` + `html_to_markdown`)
- Login redirect: implemented in `cdp.py`
- Static JS: inherently satisfied by HTML-string extraction approach

#761 is also fully superseded.

### 3.3 Decomposition Timeline

| Decomposition | Tasks | Status | Notes |
|---------------|-------|--------|-------|
| Original (#751 children) | #760 (RED), #761 (GREEN) | research | Vague AC, "static JavaScript" |
| Refined (#775 children) | #783 (RED), #788 (GREEN) | todo, architect-approved | Specific function signatures, module boundary, refined AC |

## 4. Recommendation (.95 confidence)

**Close #760 and #761 as superseded.** All four AC items are covered:
- AC3 (login redirect): implemented and tested under #755
- AC1, AC2, AC4: superseded by #783/#788 with more specific, architect-approved AC

No new follow-up tasks needed — #783 and #788 fully cover remaining work.

**Risk:** None. Closing stale duplicates reduces board noise and prevents
confusion about which tasks are canonical.

Challenge: FALLBACK — challenger subagent not available.

## 5. Follow-up Tasks

No new tasks required. Existing coverage:

| Remaining work | Tracked by | Status |
|----------------|-----------|--------|
| RED tests for extractor + cleaner | #783 | todo (architect-approved) |
| GREEN impl for extractor + cleaner | #788 | todo (architect-approved) |
| Login redirect detection | #755 (done) | implemented + tested |
