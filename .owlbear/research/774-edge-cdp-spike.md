# Phase 0: Edge CDP Technical Spike — Research

> **Owning task:** #774 — Phase 0: Edge CDP Technical Spike
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

#774 is a go/no-go gate for the Authenticated Content Pipeline (#751). It
requires empirical validation of 7 acceptance criteria: CDP connectivity,
Playwright connection, SSO session reuse, content extraction, EDR/DLP
clearance, trafilatura extraction quality, and content hash stability.

Key research questions: (1) Does the existing task chain (#752→#776→#753)
already cover these ACs? (2) What gaps remain? (3) What technical guidance
is needed for the empirical validation that can't be done by an agent?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | Chrome 136 remote-debugging-port blog | developer.chrome.com/blog/remote-debugging-port | .95 |
| 2 | trafilatura evaluation benchmarks | trafilatura.readthedocs.io/en/latest/evaluation.html | .90 |
| 3 | trafilatura Python API docs (v2.0.0) | trafilatura.readthedocs.io/en/latest/usage-python.html | .90 |
| 4 | CDP spike research (#752) | .owlbear/research/cdp-spike-752.md | .95 |
| 5 | CDP spike execution research (#753) | .owlbear/research/cdp-spike-execution-753.md | .90 |
| 6 | Existing `compute_content_hash()` | serve/knowledge/src/owlbear_knowledge/status_store.py | .85 |
| 7 | Content hashing research (#253) | .owlbear/research/content-hashing.md | .85 |
| 8 | Brief data-person voice | .owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md | .90 |
| 9 | #751 parent research | .owlbear/research/751-authenticated-content-pipeline.md | .85 |
| 10 | Centralize trafilatura research (#537, #868) | .owlbear/research/centralize-trafilatura.md, leaf-markdown-extraction-helper.md | .75 |

## 3. Analysis

### 3.1 Scope Overlap — #774 vs Existing Task Chain

| AC | #774 | #752 (research) | #776 (implement script) | #753 (execute) |
|----|------|-----------------|------------------------|----------------|
| 1. Edge launches with CDP port | ✓ | ✓ Research done | ✓ Script step 3 | ✓ Execution |
| 2. Playwright connects | ✓ | ✓ Research done | ✓ Script step 5 | ✓ Execution |
| 3. SSO-protected page succeeds | ✓ | ✓ Research done | ✓ Script steps 6-7 | ✓ Execution |
| 4. Content extractable via CDP | ✓ | ✓ Research done | ✓ Script step 8 | ✓ Execution |
| 5. EDR/DLP doesn't block | ✓ | ✓ Research done | — (user observes) | ✓ Execution |
| **6. trafilatura quality** | ✓ | **Not in scope** | **Not in script** | **Not in scope** |
| **7. Content hash stability** | ✓ | **Not in scope** | **Not in script** | **Not in scope** |

**Finding:** AC 1-5 are fully covered by #752/#776/#753. AC 6-7 are unique
to #774 — they were added by the #751 researcher who recommended testing
extraction quality alongside transport connectivity. Neither #776's script
design nor #753's execution checklist includes trafilatura or hash testing.

### 3.2 trafilatura Extraction Quality Assessment

trafilatura v2.0.0 benchmark results (2022-05-18 evaluation set):

| Mode | Precision | Recall | Accuracy | F1 | Speed |
|------|-----------|--------|----------|-----|-------|
| Standard | 0.914 | 0.904 | 0.910 | 0.909 | 7.1x |
| Fast | 0.914 | 0.886 | 0.902 | 0.900 | 4.8x |
| Precision | 0.932 | 0.874 | 0.905 | 0.902 | 9.4x |

Comparison targets: readability-lxml (0.801 F1), goose3 (0.793 F1).

**Critical caveat:** The benchmark uses news/blog articles — NOT corporate
intranet content. SharePoint and Confluence have structurally different HTML:

| Content type | Challenge for trafilatura |
|-------------|--------------------------|
| SharePoint modern pages | Web parts (cards, links, embedded content), heavy JS rendering |
| SharePoint classic pages | Wiki HTML, metadata web parts, ribbon markup |
| Confluence pages | Macro output, panel elements, embedded JIRA refs |
| Common to both | Nav bars, breadcrumbs, footers, user avatars, dynamic timestamps |

trafilatura's `favor_precision` mode (0.932 precision) should reduce
boilerplate leakage. `prune_xpath` allows surgical removal of known
SharePoint/Confluence boilerplate patterns if needed.

**Risk:** trafilatura's heuristics are tuned for article-shaped content.
Corporate web-app pages with multiple content regions (web parts) may
confuse its main-content detection. Empirical testing is the only way to
validate (.65 confidence prediction that standard mode works adequately).

### 3.3 Content Hash Stability

The existing `compute_content_hash()` (SHA-256 on `content.strip()`) is
deterministic. The instability risk is NOT in the hash function — it's in the
**input** to the hash:

| Layer | Stability risk | Source |
|-------|---------------|--------|
| HTTP/CDP response | Dynamic: timestamps, session avatars, "last modified" footers | Data voice Gap 2 |
| trafilatura extraction | Deterministic on same HTML input (same params → same output) | trafilatura docs |
| Hash computation | Deterministic (SHA-256) | status_store.py |

**Protocol for spike validation:** Extract the same page 3+ times, 60s
apart. Compare: (a) raw HTML (likely differs), (b) trafilatura output
(should be identical if boilerplate stripped), (c) SHA-256 hashes of
cleaned output (must match). If (b) differs, the dynamic boilerplate is
leaking through trafilatura — `prune_xpath` or custom post-processing
needed.

### 3.4 Chrome 136 + SSO: Confirmed Constraint

The Chrome 136 blog post [1] confirms: `--remote-debugging-port` requires
`--user-data-dir` pointing to a non-standard directory. The default Chrome/Edge
profile cannot be debugged. This means SSO cookies from the default profile are
unavailable. Windows Integrated Auth (Kerberos/NTLM) must provide SSO
automatically — an empirical question already documented in #752 research.

### 3.5 Recommendation: Consolidate #774 into Existing Chain

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Close #774, expand #776/#753 | Add AC 6-7 to spike script and execution | Eliminates duplicate task, single chain | Changes existing task scope |
| B. Keep #774 as tracking task | Add `depends_on: [753]`, redefine as go/no-go aggregator | Clean separation | One more task to manage |
| C. Keep #774 as-is | Treat as independent Phase 0 task | Preserves original intent | 5/7 ACs duplicate #753 |

## 4. Recommendation (.82 confidence)

**Option A: Consolidate.** Close #774 and expand the spike chain:

1. Add trafilatura extraction testing to #776's script (AC 6 validation)
2. Add hash stability protocol to #753's execution checklist (AC 7 validation)
3. Both additions are < 30 LOC in the spike script + checklist items

This eliminates the 5-AC overlap while preserving the unique extraction
quality and hash stability validation that the #751 researcher correctly
identified as Phase 0 scope. The go/no-go decision already lives in #753.

**Tier: T1 Autonomous** — task housekeeping (duplicate consolidation) with
no new capability, architecture, or security implications.

Challenge: FALLBACK — consolidation recommendation is task management,
not a technical trade-off warranting challenger review.

## 5. Follow-up Tasks

1. Expand #776 spike script: add trafilatura extraction quality test
2. Expand #753 execution checklist: add hash stability validation protocol
3. Close #774 as consolidated into #776/#753 (requires user action)
