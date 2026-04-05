# Browser Package Re-exports

> **Owning task:** #815 — Add re-exports to tools/browser/**init**.py
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

# 815 proposes adding 6 re-exports to `tools/browser/__init__.py` (BrowserToolset,
BrowserConfig, BrowserManager, URLSafetyGuard, BlockedURLError, CrawlConfig). It depends
on #813 (auth/planning/projects/providers/safety re-exports), which is BLOCKED pending a
user decision at `docs/decisions/pending/813-re-export-feature-gate.md`.

**Question:** Should #815 proceed independently, or does it share #813's blocker?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| init-reexports.md (2026-03-07) | Local: `docs/research/init-reexports.md` | 1.0 — .85 conf: DO NOT add |
| init-re-exports.md (2026-03-15) | Local: `docs/research/init-re-exports.md` | 1.0 — .90 conf: ADD |
| re-export-contradiction.md | Local: `docs/research/re-export-contradiction.md` | 1.0 — resolves contradiction: DO NOT add |
| PEP 8 Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | .80 — `__all__` for public API |
| Google Python Style Guide §2.2 | <https://google.github.io/styleguide/pyguide.html#22-imports> | .85 — explicit module imports |

## 3. Analysis

### 3.1 Browser-specific import evidence

| Import style | src/ | tests/ | Total |
|-------------|------|--------|-------|
| `from owlbear.tools.browser import X` (package-level) | **0** | **0** | **0** |
| `from owlbear.tools.browser.{mod} import X` (deep) | **10** | **157** | **167** |

100% of 167 browser imports use deep module paths. Zero demand for package-level imports.

### 3.2 WebCrawler optional-dep risk (confirmed)

`crawler.py` imports `trafilatura` at module level. Re-exporting WebCrawler from
`__init__.py` would break `import owlbear.tools.browser` without the `[crawl]` extra.
This risk was correctly identified in prior research and would require a lazy-import
workaround — added complexity for zero consumer demand.

### 3.3 Does #815 share #813's blocker?

| Factor | Assessment |
|--------|-----------|
| Same fundamental question | Yes — "should non-library packages get re-exports?" |
| Same empirical evidence pattern | Yes — 0 package-level, all deep |
| Same decision request covers it | Yes — `813-re-export-feature-gate.md` Option A closes both |
| Independent justification exists | No — #815 has no unique motivation beyond #813 |

**Conclusion:** #815 is fully dependent on #813's decision. No independent research needed.

## 4. Recommendation (.90 confidence)

**Do not proceed.** #815 should remain blocked until the pending decision request
(`docs/decisions/pending/813-re-export-feature-gate.md`) is resolved.

- If **Option A** (do not add): close #815 as won't-do.
- If **Option B** (add): unblock and implement per existing AC.

The browser-specific evidence (0/167) reinforces the overall finding: OwlBear is an
application, not a library. KISS/YAGNI/DRY all oppose adding re-exports with zero demand.

## 5. Follow-up Tasks

No new tasks needed. The existing decision request at
`docs/decisions/pending/813-re-export-feature-gate.md` covers #815. Tasks #812 and #822
(remove existing unused re-exports) already exist for Option A.
