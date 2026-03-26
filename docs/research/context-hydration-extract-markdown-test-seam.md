# Re-scope context_hydration Test Seam After Layer Review

> **Owning task:** #864 — Update context_hydration tests to mock extract_content instead of trafilatura
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #864 assumes #826 will import `extract_content` into `context_hydration.py`, then the RED task should patch `owlbear.core.context_hydration.extract_content`. That assumption no longer holds: #826 was architect-blocked because `core/` may not import from `tools/`. The question for this research pass is narrower: what should the RED task patch instead, and what prerequisite makes that seam legal?

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | Architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 — canonical layer rule: `core/` never imports from `tools/` |
| S2 | Python `unittest.mock` — Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 — official rule: patch where the name is looked up |
| S3 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 — official pytest guidance for patching module attributes and returned objects |
| S4 | Current caller | `src/owlbear/core/context_hydration.py` | 1.0 — shows the current lazy `trafilatura` seam and local wrapping behavior |
| S5 | Affected tests | `tests/test_context_hydration.py`, `tests/test_content_safety_integration.py` | 1.0 — exact 4 + 5 `sys.modules` patches and the wrapping assertions that must survive |
| S6 | Existing local-patch precedent | `tests/test_web_search.py` | .95 — same repo already patches module-local `extract_content` after a legal in-layer migration |
| S7 | #826 architecture review | `kanban/tasks/826-migrate-context-hydration-py-to-use-extract.md` | 1.0 — explicit verdict that `core -> tools` import is invalid |
| S8 | Cross-layer helper prerequisite | `kanban/tasks/868-create-leaf-markdown-extraction-helper-for.md` | .95 — defines legal leaf helper `owlbear.web_extract.extract_markdown` with raw, unwrapped output |

## 3. Analysis

### 3.1 Why #864 is stale as written

| Assumption in current task | Evidence | Result |
|---------------------------|----------|--------|
| `context_hydration.py` can import `tools.browser.content_extractor.extract_content` | S1, S4, S7 | Invalid. That import direction is already blocked by the layer rule and by #826's architecture review. |
| The RED task should hardcode the future symbol now | S2, S3, S4 | Invalid. Tests should patch the name the module under test actually uses, not a guessed future import. |
| Wrapping assertions require `ExtractionResult.text` specifically | S4, S5, S8 | Invalid. A raw-string helper mock preserves the same wrapping assertions because `fetch_url()` still owns wrapping in `context_hydration.py`. |

### 3.2 Options

| Option | Pros | Cons | Evidence | Recommendation |
|--------|------|------|----------|----------------|
| A. Keep #864 targeting `context_hydration.extract_content` | Reuses the current task text | Bakes in an illegal seam; cannot be correct unless the layer rule is ignored | S1, S4, S7 | .05 |
| B. Re-scope the RED task to `context_hydration.extract_markdown` after #868 | Patches where looked up, uses a legal leaf helper, preserves wrapping assertions with raw text mocks, mirrors the `web_search` local-patch pattern | Depends on #868 and on refining #826 | S1, S2, S4, S6, S8 | **Recommended (.94)** |
| C. Keep patching `sys.modules["trafilatura"]` even after a helper exists | No task rewrite | Bypasses the real seam, stays brittle across refactors, ignores official mocking guidance | S2, S3, S5 | .20 |

### 3.3 Test surface after the helper exists

| File | Current seam | Correct seam after #868 | Why it still covers behavior | Evidence |
|------|--------------|-------------------------|------------------------------|----------|
| `tests/test_context_hydration.py` | `sys.modules["trafilatura"]` at 4 sites | Patch `owlbear.core.context_hydration.extract_markdown` | The helper returns raw markdown; `fetch_url()` still owns HTTP, error handling, and wrapping | S4, S5, S8 |
| `tests/test_content_safety_integration.py` | `sys.modules["trafilatura"]` at 5 fetch-url-related sites | Patch the same module-local helper | Raw helper output keeps the wrap and contrast assertions meaningful; bookmark exclusion remains covered separately by #867 | S5, S8 |

## 4. Recommendation (.94 confidence)

Task #864 should not proceed as written. The correct sequence is:

1. Land #868 so non-tools callers have a legal leaf helper.
2. Refine #826 so `context_hydration.py` imports `owlbear.web_extract.extract_markdown`, not `tools.browser.content_extractor.extract_content`.
3. Replace the RED task wording with a module-local patch target: `owlbear.core.context_hydration.extract_markdown`.
4. Keep the wrapping assertions by returning raw markdown from the helper mock; #868 deliberately leaves wrapping and settings out of the helper.

This is the smallest change that satisfies the layer rules and the official patching guidance at the same time. The web-search tests already demonstrate the right shape: patch the imported helper inside the caller's module, not the lower-level library. S1, S2, S4, S6, S8.

## 5. Follow-up Tasks

1. Existing prerequisite: #868 — create leaf helper `owlbear.web_extract.extract_markdown`.
2. New replacement RED task — supersede #864 with helper-based mocks.

```powershell
kanban\kanban-md.exe create "Update context_hydration tests to mock extract_markdown instead of trafilatura" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED phase for #826 after #868. Update fetch_url-related tests in tests/test_context_hydration.py and tests/test_content_safety_integration.py so they patch owlbear.core.context_hydration.extract_markdown instead of patching trafilatura through sys.modules. Preserve wrapping assertions by returning raw markdown from helper mocks; #868 keeps helper output raw and unwrapped. Source: docs/research/context-hydration-extract-markdown-test-seam.md. AC: (1) 4 direct trafilatura mocks in tests/test_context_hydration.py are replaced with extract_markdown-based mocks, (2) 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced likewise, (3) wrapping and contrast assertions remain by controlling raw markdown return values, (4) scoped tests pass."
```
