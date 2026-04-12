# Trafilatura Extraction Quality — CDP Spike Expansion

> **Owning task:** #777 — Expand cdp-spike.py (#776) with trafilatura extraction quality test
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

#774 research §3.2 identified that trafilatura extraction quality on corporate
intranet pages (SharePoint, Confluence) was untested — benchmarks cover
news/blog articles only. Confidence that standard mode works on corporate
pages: .65. The spike script (`.owlbear/scratch/cdp-spike.py`) validates CDP
connectivity but lacks trafilatura extraction testing. This task adds that.

Research question: What implementation approach should the builder use to
expand the spike with trafilatura quality testing?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | trafilatura Python API docs (v2.0.0) | trafilatura.readthedocs.io/en/latest/usage-python.html | .95 |
| 2 | #774 research — §3.2 quality assessment | .owlbear/research/774-edge-cdp-spike.md | .95 |
| 3 | #759 research — cleaner implementation | .owlbear/research/759-html-markdown-cleaner.md | .85 |
| 4 | Production extractor.py | serve/browser/src/owlbear_browser/extractor.py | .90 |
| 5 | Production cleaner.py | serve/browser/src/owlbear_browser/cleaner.py | .90 |
| 6 | Existing spike script | .owlbear/scratch/cdp-spike.py | .95 |
| 7 | #776 tests (spike contract) | tests/test_cdp_spike_776.py | .80 |

## 3. Analysis

### 3.1 Current State — Gap Inventory

| Component | Exists? | trafilatura? | Corporate validation? |
|-----------|---------|-------------|----------------------|
| `cdp-spike.py` (spike) | Yes, ~245 LOC | No — uses `page.inner_text("body")` only | No |
| `extractor.py` (production) | Yes, 75 LOC | Yes — standard mode, no `favor_precision` | No — synthetic HTML unit tests only |
| `cleaner.py` (production) | Yes, 227 LOC | Fallback role | No — synthetic HTML unit tests only |

**Key gap:** Production uses `trafilatura.extract()` without `favor_precision`.
#774 benchmark data shows precision mode achieves .932 precision vs .914
standard, but with lower recall (.874 vs .904). The spike should test both
to inform whether production should switch.

### 3.2 Implementation Approach — Trade-off Matrix

| Aspect | Option A: Inline in spike | Option B: Import production extractor | Option C: Separate script |
|--------|--------------------------|--------------------------------------|--------------------------|
| LOC added | ~40-60 | ~20 | ~80 (new file) |
| Tests prod code on real pages | No — tests trafilatura directly | Yes | No |
| Compares modes | Standard + precision | Only production mode | Full flexibility |
| KISS | High | Highest | Low (another file) |
| Dependency | trafilatura (already in workspace) | owlbear_browser package | trafilatura |

### 3.3 Recommended Implementation (Option A — inline)

Production extractor uses `strip_noise()` → trafilatura pipeline without
`favor_precision`. The spike should test trafilatura directly (not through
production wrappers) to isolate extraction quality from preprocessing.
After CDP text extraction succeeds, add:

1. Capture `page.content()` → raw HTML
2. Run `trafilatura.extract(html, output_format="markdown", include_links=True,
   include_tables=True, url=page_url)` → standard mode
3. Run same with `favor_precision=True` → precision mode
4. Log quality metrics for both: text length, paragraph count, boilerplate hits
5. Loop over multiple URLs (change `--url` to `--urls`, accept comma-separated)

**Boilerplate indicators** (regex patterns for detection):
`Home`, `Sign out/in`, `Copyright`, `Privacy`, `Terms of Use`, `Powered by`,
breadcrumb separators (`›`, `»`, `>`), `Cookie`, `Footer`.

**URL configuration:** 5 defaults (3 SharePoint + 2 Confluence) via `--urls`
arg or `TARGET_URLS` env var. Defaults should be company-specific placeholders
that the user replaces before execution.

### 3.4 Production Impact Assessment

| Spike outcome | Production action |
|---------------|-------------------|
| Standard mode quality adequate (.80+ precision on corporate pages) | No change to extractor.py |
| Precision mode significantly better | Add `favor_precision=True` to extractor.py |
| Both modes have boilerplate leakage | Add `prune_xpath` patterns to extractor.py (SP/Confluence-specific) |
| trafilatura fails on corporate pages | Escalate — cleaner.py fallback may need to become primary |

### 3.5 Dependency Check

trafilatura is already in the workspace via `serve/browser/pyproject.toml`
(`trafilatura>=1.6`). Since the workspace root includes `serve/*` as members,
`uv run` from the workspace root resolves trafilatura. No additional
installation needed for the spike script.

## 4. Recommendation (.88 confidence)

**Option A: Inline trafilatura testing in the existing spike script.** Add
~40-60 LOC to `cdp-spike.py`: multi-URL loop, trafilatura standard + precision
extraction, quality metrics logging. This directly addresses all 4 ACs.

The implementation is prescribed by the task AC — no design ambiguity. The
builder adds a trafilatura extraction function, modifies argparse for multiple
URLs, and wraps the navigation + extraction in a URL loop.

**Tier: T1 Autonomous** — extending existing scratch script with prescribed
functionality. No new capability, architecture, or security implications.

Challenge: FALLBACK — implementation approach is prescribed by task AC; no
controversial trade-off to challenge.

## 5. Follow-up Tasks

None needed beyond this task advancing to backlog. #777 itself is the
implementation story. #778 (hash stability) is the sibling task covering
content hash validation. #753 (execute spike) depends on both completing.
