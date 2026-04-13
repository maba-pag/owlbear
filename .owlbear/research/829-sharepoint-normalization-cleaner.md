# SharePoint Normalization + Idempotent Output for Cleaner

> **Owning task:** #829 — Impl — SharePoint normalization + idempotent output for cleaner
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

#829 is a GREEN-phase task extending `owlbear_browser.cleaner` with: (1) SharePoint-specific
boilerplate patterns in `strip_noise()`, (2) content normalization in the output path, and
(3) verified idempotent output for hash stability. Key questions: what specific SharePoint DOM
patterns need to be added, what normalization gaps exist, and where should normalization live
to satisfy idempotent `extract_content()` output?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Current `cleaner.py` implementation | serve/browser/src/owlbear_browser/cleaner.py | 1.0 |
| 2 | Current `extractor.py` implementation | serve/browser/src/owlbear_browser/extractor.py | 1.0 |
| 3 | #756 research (cleaner tests) | .owlbear/research/756-html-markdown-cleaner-tests.md §3.2 | .95 |
| 4 | #759 research (cleaner impl) §3c | .owlbear/research/759-html-markdown-cleaner.md | .95 |
| 5 | `compute_content_hash()` | serve/knowledge/src/owlbear_knowledge/status_store.py:39 | .90 |
| 6 | sp-dev-docs#6380 (CSS class instability) | github.com/SharePoint/sp-dev-docs/issues/6380 | .85 |
| 7 | Fluent UI v8 component CSS classes | github.com/Zerg00s/sp-modern-classes | .80 |
| 8 | trafilatura prune_xpath docs | trafilatura.readthedocs.io/en/latest/corefunctions.html | .80 |
| 9 | `test_cleaner_756.py` (existing tests) | tests/test_cleaner_756.py | .95 |
| 10 | #828 task body (RED partner) | kanban board | 1.0 |

## 3. Analysis

### 3.1 Current State vs AC Requirements

| AC Requirement | Status | Evidence |
|----------------|--------|----------|
| `strip_noise()` — breadcrumb containers | GAP | No breadcrumb class/id in `_NOISE_CLASSES`/`_NOISE_IDS` |
| `strip_noise()` — web-part wrappers | PARTIAL | `ms-commandBar`, `ms-header`, `ms-pageEditBar` present; no `ms-webpart-chrome-*` |
| `strip_noise()` — dynamic timestamps | GAP | No timestamp/date-related patterns |
| `strip_noise()` — user avatar containers | GAP | No persona/avatar patterns |
| `html_to_markdown()` — normalized whitespace | PARTIAL | `_normalize_content()` exists but only in `clean()` path |
| `html_to_markdown()` — no encoding artifacts | PARTIAL | lxml handles entities at parse; zero-width chars not stripped |
| Idempotent `extract_content()` output | RISK | Both paths are deterministic per-call, but normalization only in `clean()` |

### 3.2 SharePoint Pattern Analysis

Fluent UI v8 `ms-` class names are semi-stable (part of component library API, source 7).
Microsoft is replacing layout-level classes (`CanvasZone`, `ControlZone`) with hashed names
(source 6), but component-level `ms-` prefixes remain usable. Identified patterns:

| Pattern | CSS Class / ID | Type | Stability |
|---------|---------------|------|-----------|
| Breadcrumb nav | `ms-Breadcrumb` | class | Stable (Fluent UI v8) |
| User persona/avatar | `ms-Persona` | class | Stable (Fluent UI v8) |
| Live persona card | `ms-LivePersona` | class | Stable (Fluent UI v8) |
| Suite nav placeholder | `SuiteNavPlaceHolder` | id | Stable (SharePoint chrome) |
| O365 header bar | `O365_NavHeader` | id | Stable (SharePoint chrome) |
| Ribbon row (classic) | `s4-ribbonrow` | id | Stable (SP classic, declining) |

Timestamp elements: SharePoint uses `<time>` HTML tags and Fluent UI's `ms-DateTimeField`
for dynamic dates. Stripping `<time>` elements is too aggressive (removes legitimate content
dates). Better: add `ms-DateTimeField` to `_NOISE_CLASSES` for SharePoint edit-form timestamps,
and document that content-body dates (inside `<p>`, `<td>`) are intentionally preserved.

### 3.3 Normalization Gap Assessment

`compute_content_hash()` does `" ".join(content.split())` which collapses all whitespace
including `\r`, `\t`, and multiple spaces. This absorbs most whitespace variation at hash
time. Remaining hash-instability vectors:

| Vector | Handled by `compute_content_hash`? | Handled by `_normalize_content`? |
|--------|-------------------------------------|----------------------------------|
| Multiple spaces | YES (`.split()`) | YES |
| Mixed line endings `\r\n` | YES (`.split()`) | NO |
| `\u00a0` (nbsp) | YES (`.split()` splits on it) | YES (replace) |
| Zero-width chars (U+200B/200C/200D/FEFF) | NO | NO |
| HTML entities | N/A (lxml decodes at parse time) | N/A |

**Critical gap**: Zero-width characters survive both normalization layers. These appear in
SharePoint rendered HTML from Fluent UI's text rendering.

### 3.4 `extract_content()` Idempotency

The AC states: "Same HTML input produces identical markdown output on repeated extract_content()
calls." Both trafilatura and `html_to_markdown()` are deterministic on identical input, so
repeated calls trivially produce identical output. The deeper concern — two different HTML
representations of the same content producing different hashes — is handled by
`compute_content_hash()`'s whitespace normalization plus the zero-width fix above.

`extract_content()` does NOT need `_normalize_content()` applied to its output for the
idempotency AC (same input → same output). However, for output quality (readable markdown),
applying normalization to the fallback path would be beneficial. This is a builder decision,
not a research blocker.

### 3.5 Implementation Approach — Trade-off Matrix

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| A. Exact classes | Add known `ms-` classes to `_NOISE_CLASSES`/`_NOISE_IDS` | KISS; follows existing pattern; testable | Misses unknown variants | **.82** |
| B. Prefix matching | Match any class starting with `ms-Breadcrumb`, `ms-Persona` | Catches variants | Risk false positives; more complex; YAGNI | .55 |
| C. XPath pre-processing | Use lxml XPath like trafilatura's `prune_xpath` | Powerful, declarative | Adds mechanism; cleaner already has class/id matching | .50 |

## 4. Recommendation (.82 confidence)

**Option A: Add specific Fluent UI class/id patterns and zero-width character stripping.**

Implementation:
1. Add to `_NOISE_CLASSES`: `ms-Breadcrumb`, `ms-Persona`, `ms-LivePersona`, `ms-DateTimeField`
2. Add to `_NOISE_IDS`: `SuiteNavPlaceHolder`, `O365_NavHeader`, `s4-ribbonrow`
3. Add zero-width character removal to `_normalize_content()`: strip U+200B, U+200C, U+200D, U+FEFF
4. Add `\r` removal to `_normalize_content()` for line ending normalization
5. Verify `clean()` path produces stable hashes via existing test patterns

The `extract_content()` function does NOT need modification for the idempotency AC — same
input already produces same output. Normalization remains in `clean()` only.

Tier: **T1 Autonomous** — extends existing patterns, no new capability or architecture change.

Challenge: FALLBACK — pattern extension is mechanical, not a design trade-off requiring
challenger review. Self-challenge: prefix matching (Option B) rejected because the `ms-`
namespace contains ~200+ classes (source 7) including content-bearing ones like `ms-TextField`.
Exact matches are safer and match #828 test expectations.

## 5. Follow-up Tasks

None beyond advancing #829 itself. The implementation is mechanical: add class/id strings
to existing sets, add character stripping to `_normalize_content()`. No decomposition needed.
