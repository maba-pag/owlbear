# P1-05: Tests — HTML→markdown cleaner — Research

> **Owning task:** #756 — P1-05: Tests — HTML→markdown cleaner
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

#756 is a RED-phase test task (parent #751) covering four test areas for an
HTML→markdown cleaner: (1) HTML→markdown conversion with noise stripping,
(2) SharePoint-specific boilerplate removal, (3) content normalization, and
(4) idempotent output for hashing. The key research question: is #756
superseded by the active #783/#788 task pair from the #775 decomposition,
or does it carry unique scope that must be preserved?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | #783 task + arch review | .owlbear/kanban/tasks/783-*.md | 1.0 |
| 2 | #788 task + arch review | .owlbear/kanban/tasks/788-*.md | 1.0 |
| 3 | #756 task body | kanban board | 1.0 |
| 4 | #760/#761 task bodies | kanban board | .90 |
| 5 | trafilatura evaluation benchmarks | trafilatura.readthedocs.io/en/latest/evaluation.html | .90 |
| 6 | trafilatura Python API docs | trafilatura.readthedocs.io/en/latest/usage-python.html | .90 |
| 7 | Data-person voice (Gap 1, Gap 2) | .owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md | .95 |
| 8 | Brief D1 decision | .owlbear/briefs/draft-browser-knowledge-extraction/decisions.md | .90 |
| 9 | compute_content_hash() | serve/knowledge/src/owlbear_knowledge/status_store.py | .85 |
| 10 | #774 research (hash stability) | .owlbear/research/774-edge-cdp-spike.md §3.3 | .85 |

## 3. Analysis

### 3.1 Overlap — #756 vs #783 (active RED partner for #788)

| #756 scope item | #783 refined AC | Overlap |
|-----------------|-----------------|---------|
| 1. HTML→markdown + nav/header/footer/sidebar strip | AC 2 (headings/lists/tables/links) + AC 3 (nav/footer/script/style/cookies) | FULL |
| 2. SharePoint-specific boilerplate removal | Not in #783 | UNIQUE |
| 3. Content normalization (whitespace, encoding) | Not in #783 | UNIQUE |
| 4. Idempotent output for hashing | Not in #783 | UNIQUE |

**Finding:** #783 architect already noted the overlap: "Overlapping tasks
#760/#761 cover similar scope from a prior decomposition. #783/#788 from
#775 are the active pair." #756 is from the same prior decomposition.

Item 1 is fully covered by #783. Items 2–4 are unique to #756 and map
directly to data-person voice Gaps 1–2 and brief decision D1 (cleaning +
hash fix ship together).

### 3.2 Unique Scope Assessment

**SharePoint-specific boilerplate (item 2):** SharePoint modern pages embed
dynamic elements — timestamps, user avatars, breadcrumbs, web-part chrome,
`ms-` prefixed CSS class containers — that change between page loads despite
identical content. trafilatura's boilerplate heuristics (F1=0.909) are tuned
for news/blog content, not corporate web-app pages (source 5). The #788
architect acknowledged this risk: "trafilatura heuristics tuned for
article-shaped content, not corporate web-app pages." The `prune_xpath`
parameter (source 6) allows targeted removal of known SharePoint patterns
when standard heuristics fail. Tests for SharePoint-specific behavior are
correctly scoped to the cleaner — they should verify that common corporate
boilerplate patterns (breadcrumbs, web-part wrappers, timestamps) are
removed from output.

**Content normalization (item 3):** The cleaner output feeds `compute_content_hash()`
(source 9) which hashes `content.strip().encode()`. For hash stability, the
cleaner must normalize: (a) inconsistent whitespace (multiple spaces, mixed
line endings), (b) encoding artifacts (HTML entities, zero-width characters).
trafilatura handles most of this internally (source 6), but the cleaner
fallback path — `strip_noise()` + `html_to_markdown()` from #788 — has no
normalization contract. Tests should verify normalized whitespace in output
regardless of extraction path.

**Idempotent output (item 4):** trafilatura.extract() is deterministic on
identical HTML input with identical parameters (confirmed via source 6, API
docs). The hash instability risk is in the HTML input, not the extraction.
However, the cleaner's fallback path must also produce deterministic output.
Tests should verify: same HTML input → same markdown output → same hash.
This is the contract that data-person Gap 2 requires (#774 research §3.3).

### 3.3 Consolidation Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| A. Close #756, expand #783 AC | Add items 2–4 to #783 refined AC | Single test file, no duplicate tasks | #783 already architect-approved; re-opening AC is rework | .45 |
| B. Close #756, create focused follow-up | Close as superseded; new task for unique scope (items 2–4) | Clean separation; #783 stays intact; unique scope gets TDD pair | One more task | **.85** |
| C. Keep #756 as-is | Proceed with #756 independently | Preserves original intent | Duplicates #783 item 1; two test files for same modules | .20 |

## 4. Recommendation (.85 confidence)

**Option B: Close #756 as superseded by #783. Create a focused follow-up
task for the unique scope items (SharePoint boilerplate, normalization,
idempotency).**

Rationale:
- #783 is the active, architect-approved RED task for `owlbear_browser.extractor`
  and `owlbear_browser.cleaner`. Running #756 in parallel produces a second
  test file against the same modules — a maintenance burden.
- Items 2–4 are genuinely important (data-person Gaps 1–2, brief D1) and
  not covered by #783. They deserve their own focused task with concrete AC.
- The follow-up naturally pairs with #788's implementation — SharePoint
  normalization tests should fail until the cleaner handles those patterns.

**Tier: T1 Autonomous** — task consolidation, no new capability or
architecture change. Follow-up tasks created below.

Challenge: FALLBACK — consolidation recommendation is task housekeeping,
not a technical trade-off requiring challenger review.

## 5. Follow-up Tasks

1. Close #756 as superseded by #783 (orchestrator action)
2. Close #760 as superseded by #783 (same prior-decomposition overlap)
3. New task: SharePoint normalization + idempotency tests for cleaner
   (RED phase, parent #775, depends_on #783)
4. New task: SharePoint normalization + idempotency impl for cleaner
   (GREEN phase, parent #775, depends_on follow-up #3 + #788)
