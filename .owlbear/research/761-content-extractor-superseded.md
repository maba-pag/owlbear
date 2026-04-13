# P1-08: Impl — Content extractor — Superseded

> **Owning task:** #761 — P1-08: Impl — Content extractor
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #761 is a GREEN phase task (parent #751) for `serve/browser/src/owlbear_browser/extractor.py` covering: (1) Static JS-based DOM extraction, (2) Delegation to cleaner for HTML→markdown, (3) Login redirect detection (fail-fast), (4) Only static/pre-defined extraction JavaScript.

The question: is #761 still needed, or is its scope covered by the refined #775 decomposition?

## 2. Sources Studied

| # | Source | Kind | Relevance |
|---|--------|------|-----------|
| S1 | `serve/browser/src/owlbear_browser/cdp.py` — `check_sso_redirect()` | Local | 1.0 |
| S2 | `tests/test_edge_launcher_cdp_755.py` — `TestFromAC_SSODetection` (5 tests) | Local | 1.0 |
| S3 | Task #783 body + architect review (RED tests for extractor+cleaner) | Kanban | 1.0 |
| S4 | Task #788 body + architect review (GREEN impl for extractor+cleaner) | Kanban | 1.0 |
| S5 | `.owlbear/research/760-content-extractor-tests-superseded.md` (#760 research) | Local | .95 |
| S6 | Task #759 architect review (supersede verdict) | Kanban | .90 |
| S7 | `.owlbear/research/751-authenticated-content-pipeline.md` | Local | .85 |

## 3. Analysis — AC-by-AC Coverage Map

| #761 AC | Covered by | Evidence | Status |
|---------|-----------|----------|--------|
| Static JS-based DOM extraction | #788 refined AC1: `extract_content(html, url)` | Extractor takes `html: str` — no JS execution needed; `page.content()` is a trivial CDP call upstream (S4) | **Superseded** |
| Delegates to cleaner | #788 refined AC1–2: trafilatura primary + `cleaner.strip_noise()` / `html_to_markdown()` fallback | Full function signatures and module boundary specified (S4) | **Superseded** |
| Login redirect detection | `cdp.py:check_sso_redirect()` | 5 passing tests: IdP URL, login form, propagation, exception type, normal page (S1, S2) | **Implemented+Tested** |
| Only static/pre-defined JS | #788 architecture | Extractor operates on HTML strings — no `page.evaluate()` in extraction path; constraint inherently satisfied (S4) | **Superseded** |

### Decomposition Timeline

| Decomposition | RED task | GREEN task | Status |
|---------------|-------|--------|-------|
| Original (#751 children) | #760 | **#761** (this task) | Both superseded |
| Refined (#775 children) | #783 | #788 | Both at `todo`, architect-approved |

### Cross-Referencing Evidence

1. **#760 researcher** (S5): "Close #760 and #761 as superseded — all scope covered" (confidence .95)
2. **#783 architect** (S3): "Overlapping tasks #760/#761 cover similar scope from a prior decomposition. #783/#788 from #775 are the active pair"
3. **#759 architect** (S6): "#760/#761 (parent #751, research status) cover similar scope from a prior decomposition"
4. **RED partner absent**: #761's RED partner #760 is also superseded. GREEN phase cannot proceed without RED tests.

## 4. Recommendation (.95 confidence)

**Close #761 as superseded.** All four AC items are covered:
- Login redirect: implemented and tested under #755 in `cdp.py`
- Static extraction + cleaner delegation + JS constraint: superseded by #788 with architect-approved refined AC including function signatures, module boundary, and library choice

No new follow-up tasks needed — #783 and #788 fully cover remaining work.

Challenge: FALLBACK — challenger subagent not available.

## 5. Follow-up Tasks

No new tasks required. Existing coverage:

| Remaining work | Tracked by | Status |
|----------------|-----------|--------|
| RED tests for extractor + cleaner | #783 | todo (architect-approved) |
| GREEN impl for extractor + cleaner | #788 | todo (architect-approved) |
| Login redirect detection | #755 (done) | implemented + tested |
