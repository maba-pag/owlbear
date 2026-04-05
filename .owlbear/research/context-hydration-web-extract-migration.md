# Context Hydration web_extract Migration

> **Owning task:** #873 - Migrate context_hydration.py to use web_extract.extract_markdown
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #873 replaces the direct `trafilatura.extract(...)` call inside `src/owlbear/core/context_hydration.py::fetch_url()` with the package-root leaf helper introduced by #868. The research question is whether that migration is the correct architectural boundary for `core/`, whether it preserves `fetch_url()` ownership of HTTP and wrapping behavior, and whether the current RED chain fully proves the helper call contract.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 - canonical `extract()` parameters: Markdown output, `include_links=True`, and `url=` forwarding |
| S2 | Python `unittest.mock` docs - Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 - official rule for patching the imported name used by the module under test |
| S3 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 - module-attribute patching and helper-return mocking guidance |
| S4 | Cosmic Python ch. 2 - Repository Pattern | <https://www.cosmicpython.com/book/chapter_02_repository.html> | .85 - dependency-direction prior art for keeping core logic free of adapter imports |
| S5 | OwlBear architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 - `core/` never imports from `tools/` |
| S6 | Current caller and wrapper precedent | `src/owlbear/core/context_hydration.py`, `src/owlbear/tools/browser/content_extractor.py`, `src/owlbear/paths.py` | 1.0 - shows the current seam, the current wrapping owner, and the package-root leaf precedent |
| S7 | Current and planned tests | `tests/test_context_hydration.py`, `tests/test_content_safety_integration.py`, task #869 | 1.0 - shows the RED seam change and the remaining helper-call assertion gap |
| S8 | Related board and research context | `docs/research/leaf-markdown-extraction-helper.md`, `docs/research/context-hydration-extract-markdown-red-task.md`, task #826, task #868, task #869 | .95 - confirms the legal helper path and the stale blocked alternative |

## 3. Analysis

### 3.1 Option comparison

| Option | Layer legality | Wrap ownership | DRY impact | Evidence | Recommendation |
|--------|----------------|----------------|------------|----------|----------------|
| A. Keep direct `trafilatura` in `fetch_url()` | Legal | Local | Low | S1, S5, S6, S8 | .32 |
| B. Import `tools.browser.content_extractor.extract_content().text` | Illegal for `core/` | Shifted into `tools/` | Medium | S4, S5, S6, S8 | .06 |
| C. Import `owlbear.web_extract.extract_markdown()` and keep local wrap | Legal | Local | High | S1, S4, S5, S6, S8 | **Recommended (.95)** |

### 3.2 Contract that must stay unchanged

| Requirement | Why | Evidence |
|-------------|-----|----------|
| `fetch_url()` keeps the `httpx` request, timeout/status handling, and empty-string behavior | Those responsibilities are caller policy, not extraction policy | S5, S6, S8 |
| `fetch_url()` forwards `resp.text` and `url=url` into the helper | This preserves the current `trafilatura` behavior, including relative-link resolution | S1, S6, S8 |
| `extract_markdown()` stays raw and unwrapped | Integration tests deliberately contrast wrapped `fetch_url()` with unwrapped bookmark ingestion | S1, S6, S7, S8 |
| `context_hydration.py` stops importing `trafilatura` directly once #868 lands | The helper centralizes the raw extract call without forcing a `core -> tools` dependency | S1, S4, S5, S8 |

### 3.3 Test readiness

| Surface | Status | Evidence | Action |
|---------|--------|----------|--------|
| Patch seam from `sys.modules["trafilatura"]` to `context_hydration.extract_markdown` | Covered by existing RED task | S2, S3, S7, S8 | Keep #869 |
| Wrapping and contrast behavior after helper migration | Covered by existing integration assertions | S6, S7, S8 | Keep current assertions raw |
| Explicit assertion that the helper receives the HTML body and `url=url` | Not explicit in current tests | S1, S2, S3, S7 | New follow-up #876 |

## 4. Recommendation (.95 confidence)

Advance #873 as the correct GREEN implementation path after #868 and #869. The implementation should:

1. import `extract_markdown` from `owlbear.web_extract`
2. replace the direct `trafilatura.extract(...)` call with `extract_markdown(resp.text, url=url)`
3. keep `fetch_url()`'s local HTTP exception handling and `wrap_web_content` branch where they are
4. leave the helper raw so wrapping continues to happen once, in the caller

This is the smallest change that satisfies the layer rule and the DRY goal at the same time. Reusing `content_extractor.extract_content()` would repeat the already-blocked #826 design, while keeping direct `trafilatura` calls in `core/` ignores the new leaf helper and leaves the duplication in place. S1, S4, S5, S6, S8.

## 5. Follow-up Tasks

1. Existing prerequisite: #868 - create `owlbear.web_extract.extract_markdown`.
   Priority: nice-to-have. Dependency role: leaf helper contract for lower-layer callers. AC: raw string helper with lazy optional-dependency import and empty-string fallback.

2. Existing RED partner: #869 - switch `context_hydration` tests to module-local `extract_markdown` patches.
   Priority: nice-to-have. Dependency role: main RED seam migration. AC: replace 4 + 5 `trafilatura` patches while preserving raw helper-return wrapping assertions.

3. New #876 - add explicit helper-call assertions for `fetch_url()`.
   Priority: nice-to-have. Dependency role: closes the remaining RED gap for `resp.text` and `url=url` forwarding. AC: at least one scoped fetch-url success-path test patches `context_hydration.extract_markdown`, asserts it receives the HTML body plus forwarded URL, and keeps raw helper-return wrapping assertions intact.

```powershell
kanban\kanban-md.exe create "Add context_hydration RED assertions for extract_markdown url forwarding" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED supplement for #873 after #868. Add focused fetch_url success-path assertions in tests/test_context_hydration.py and tests/test_content_safety_integration.py that patch owlbear.core.context_hydration.extract_markdown, return raw markdown, and assert fetch_url forwards resp.text plus url=url into the helper. Source: docs/research/context-hydration-web-extract-migration.md. AC: (1) at least one scoped fetch_url test patches module-local extract_markdown, (2) it asserts the helper is called once with the HTML body and forwarded url, (3) raw helper-return mocks keep wrapping and contrast assertions meaningful, (4) scoped tests fail before #873 and pass after implementation."
```
