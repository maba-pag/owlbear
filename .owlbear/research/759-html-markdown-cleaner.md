# HTML→Markdown Cleaner Implementation Research

> **Owning task:** #759 — P1-06: Impl — HTML→markdown cleaner
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #759 is a GREEN phase task for `serve/browser/src/owlbear_browser/cleaner.py` requiring: (1) HTML→markdown conversion with boilerplate stripping, (2) SharePoint-specific normalization, (3) idempotent output for stable content hashing via `compute_content_hash()` (SHA-256 on `content.strip()`).

Parent #751 research recommended trafilatura (confidence .75). This research validates and narrows that recommendation for the concrete cleaner module, defines the API surface, and addresses SharePoint-specific normalization patterns.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | trafilatura Python API docs (v2.0.0) | trafilatura.readthedocs.io/en/latest/usage-python.html | .95 |
| 2 | trafilatura evaluation benchmarks | trafilatura.readthedocs.io/en/latest/evaluation.html | .85 |
| 3 | markdownify 1.2.2 PyPI | pypi.org/project/markdownify/ | .80 |
| 4 | Parent research #751 | .owlbear/research/751-authenticated-content-pipeline.md | .95 |
| 5 | Phase 0 spike research #774 | .owlbear/research/774-edge-cdp-spike.md | .85 |
| 6 | Phase 1 decomposition research #775 | .owlbear/research/775-phase1-browser-pipeline-schema.md | .90 |
| 7 | Existing `compute_content_hash()` | serve/knowledge/src/owlbear_knowledge/status_store.py | .90 |
| 8 | Browser package structure | serve/browser/src/owlbear_browser/ | .95 |
| 9 | Leaf extraction helper research (#868) | .owlbear/research/leaf-markdown-extraction-helper.md | .70 |

## 3. Analysis

### 3a. Library Comparison — Trade-off Matrix

| Criterion | trafilatura | markdownify + BS4 strip | readability-lxml + markdownify |
|-----------|-------------|-------------------------|-------------------------------|
| License | Apache 2.0 ✅ | MIT ✅ | Apache 2.0 + MIT ✅ |
| Main content extraction | Built-in heuristics | Manual (~50-80 LOC) | Built-in (article-biased) |
| Boilerplate removal | Built-in (nav/footer/ads) | Manual per-site rules | Built-in |
| Markdown output | Native `output_format="markdown"` | Native | 2-step (HTML→readable→MD) |
| SharePoint tuning | `prune_xpath` + `favor_precision` | Full manual control | Limited (article-bias) |
| Transitive deps added | ~8 | 1 (beautifulsoup4) | 3 (lxml, readability, bs4) |
| Integration LOC | ~15-25 | ~60-100 | ~30-40 |
| Deterministic output | Yes (same input → same output) | Yes | Yes |
| Benchmark F1 (news/blog) | 0.909 standard, 0.902 precision | N/A (converter only) | 0.801 |
| Corporate intranet quality | Unknown (.65 prediction) | Full control but brittle | Article-biased (risk) |
| KISS score | .70 (feature-rich lib) | .50 (custom boilerplate) | .65 |

### 3b. API Surface Design

The cleaner should expose a single function with a minimal contract:

```python
def clean_html(html: str, *, url: str | None = None) -> str
```

- Returns cleaned markdown string or `""` for empty/whitespace-only input.
- Idempotent: `clean_html(h) == clean_html(h)` always. No external state.
- Lazy-imports extraction library on first call (consistent with codebase patterns in `cdp.py`, `launcher.py`).

### 3c. SharePoint-Specific Normalization

trafilatura's general heuristics strip `<nav>`, `<footer>`, `<aside>`, `<header>` automatically. SharePoint pages contain additional boilerplate that leaks through general heuristics:

| Pattern | XPath | Category |
|---------|-------|----------|
| Suite navigation bar | `//div[@id='SuiteNavPlaceHolder']` | Navigation |
| O365 header chrome | `//div[@id='O365_NavHeader']` | Navigation |
| Left nav/quick launch | `//div[contains(@class,'ms-core-listMenu')]` | Navigation |
| Ribbon row | `//div[@id='s4-ribbonrow']` | UI chrome |
| Breadcrumb trail | `//div[contains(@class,'breadcrumb')]` | Navigation |
| Like/comment controls | `//div[contains(@class,'social')]` | Interactive |

These patterns can be passed as `prune_xpath` to `trafilatura.extract()`, which surgically removes matching elements before extraction. This avoids custom BS4 pre-processing.

### 3d. Idempotency for Content Hashing

`compute_content_hash()` applies `content.strip()` before SHA-256. The cleaner's idempotency requirement means: same raw HTML → same markdown. Three layers ensure this:

1. **trafilatura** is deterministic for same input + params (confirmed in docs, validated in #774 research §3.3).
2. **Post-normalization**: collapse multiple blank lines to single separator, strip trailing whitespace per line. This absorbs minor trafilatura formatting variations across versions.
3. **No external state**: no timestamps, no random seeds, no network calls in the cleaner itself.

### 3e. Dependency Impact

Adding `trafilatura>=2.0` to `serve/browser/pyproject.toml` adds ~8 transitive deps. This is scoped to the browser package only — the knowledge package is unaffected. The browser package already requires `playwright>=1.40` which pulls ~5 deps of its own, so the marginal dependency cost is proportional.

### 3f. Missing Dependency: #756 Tests

Task #759 body says "All P1-05 (#756) tests pass." But #756 is at `research` status — no tests exist yet. Per TDD protocol, #759 cannot be built until #756's tests are written and failing. **#759 should list `depends_on: [756]`.**

## 4. Recommendation (confidence: .80)

Use **trafilatura** with SharePoint-specific `prune_xpath` patterns and post-normalization for whitespace consistency.

Concrete implementation approach:
1. Lazy-import `trafilatura` on first call
2. Call `trafilatura.extract(html, output_format="markdown", include_links=True, favor_precision=True, prune_xpath=SHAREPOINT_XPATHS, url=url)`
3. Fall back to `""` when extraction returns `None`
4. Normalize: collapse `\n{3,}` → `\n\n`, strip trailing whitespace per line

This is the smallest implementation (~20-25 LOC) that satisfies all three requirements. The `prune_xpath` approach keeps SharePoint patterns declarative and extensible without custom parsing logic.

**Risk**: trafilatura's heuristics may over-strip or under-strip on corporate web-part pages (.65 confidence on first-pass quality). Mitigation: the `prune_xpath` list is extensible, and `favor_precision=True` reduces noise. Quality tuning can happen iteratively after Phase 0 spike validates real content.

Challenge: FALLBACK — no challenger subagent available. Self-challenge applied: main risk is trafilatura's ~8 deps vs KISS principle. Mitigated by: deps are scoped to browser package only; markdownify alternative requires 3-4x more LOC with lower extraction quality and no general boilerplate removal.

**Tier: T1 Autonomous** — implementation approach within already-approved architecture (T3 decision was made at #751 level). No new capability, no architecture change.

## 5. Follow-up Tasks

1. **Dependency fix**: #759 must add `depends_on: [756]` — tests must exist before GREEN implementation.
2. No additional research tasks — approach validated by prior #751/#774/#775 research chain.
