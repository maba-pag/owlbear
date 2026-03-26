# Validate bookmark_pipeline extract_markdown RED task

> **Owning task:** #867 — Update bookmark_pipeline tests to mock extract_markdown instead of trafilatura
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #867 is the RED partner for #825 after #868 lands the leaf helper. The open question is whether #867 already targets the right seam and preserves the right behavior checks: once `bookmark_pipeline.py` imports `extract_markdown`, should the tests patch `owlbear.memory.knowledge.bookmark_pipeline.extract_markdown` instead of `sys.modules["trafilatura"]`, and what must remain asserted in the bookmark no-wrap contrast test?

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | Python `unittest.mock` docs — Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 — official rule: patch the name used by the system under test |
| S2 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 — official guidance for patching module attributes and returned objects in tests |
| S3 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | .85 — confirms the migration target is raw Markdown output and can preserve links |
| S4 | Current caller + affected tests | `src/owlbear/memory/knowledge/bookmark_pipeline.py`, `tests/test_bookmark_pipeline.py`, `tests/test_content_safety_integration.py` | 1.0 — confirms the live lazy `trafilatura` seam, the 3 direct `_default_web_read()` `sys.modules` patches, and the bookmark no-wrap contrast assertion |
| S5 | Refined GREEN partner | `kanban/tasks/825-migrate-bookmark-pipeline-py-to-use-web-extract.md` | 1.0 — proves the future import target is `owlbear.web_extract.extract_markdown` and that bookmark output must stay raw and unwrapped |
| S6 | Helper prerequisite | `kanban/tasks/868-create-leaf-markdown-extraction-helper-for-cross.md` | .95 — defines helper behavior as raw Markdown plus no wrapping |
| S7 | Earlier bookmark migration research | `docs/research/bookmark-pipeline-extract-content.md` | .95 — explains why bookmark ingestion must stay unwrapped and why Markdown is the new contract |

## 3. Analysis

### 3.1 What #867 already gets right

| Claim in #867 | Evidence | Result |
|---------------|----------|--------|
| Tests should patch `owlbear.memory.knowledge.bookmark_pipeline.extract_markdown` after #825 | S1, S2, S5 | Valid. Once `_default_web_read()` looks up `extract_markdown` in its own module, patching `sys.modules["trafilatura"]` no longer intercepts the seam being exercised. |
| Helper mocks should return raw Markdown, not wrapped output | S3, S5, S6, S7 | Valid. #868 and #825 keep wrapping outside the helper and move the bookmark path to raw Markdown with links. |
| The bookmark/content-safety contrast test must stay | S4, S5, S7 | Valid. The important invariant is still "bookmark ingestion stays unwrapped while `fetch_url()` wraps," even though the two sides will briefly use different seams until #873 lands. |

### 3.2 Exact test surface

| File | Current seam | Correct seam after #825 | Notes |
|------|--------------|-------------------------|-------|
| `tests/test_bookmark_pipeline.py` | 3 `patch.dict(sys.modules, {"trafilatura": ...})` sites in the happy-path, HTTP-error, and empty-result `_default_web_read()` tests | Patch `owlbear.memory.knowledge.bookmark_pipeline.extract_markdown` | One updated happy-path case should return Markdown with link syntax so the task explicitly proves Markdown output passes through unchanged. |
| `tests/test_content_safety_integration.py` | 1 bookmark-side `sys.modules` patch inside the no-wrap contrast test | Patch `owlbear.memory.knowledge.bookmark_pipeline.extract_markdown` only for the bookmark half | The `fetch_url()` half still patches `trafilatura` until #873 migrates that caller. Mixed seams are expected during the staggered rollout. |
| Import-guard tests in `tests/test_bookmark_pipeline.py` | Builtins import denial for `trafilatura` | No change required | #825 still surfaces the helper's actionable missing-dependency contract through `_default_web_read()`, so the import-guard tests remain valid. |

### 3.3 Options

| Option | Pros | Cons | Evidence | Recommendation |
|--------|------|------|----------|----------------|
| A. Advance #867 as the RED task, with architect tightening the RED phrasing and explicit prerequisite | Uses the correct seam, pairs cleanly with #825 and #868, preserves the no-wrap contrast | The current AC still says scoped tests pass instead of explicit pre-#825 failure, and #868 is implied rather than formalized in the body | S1, S2, S4, S5, S6, S7 | **Recommended (.95)** |
| B. Keep patching `sys.modules["trafilatura"]` after helper migration | Minimal task rewrite | Misses the module-local seam, becomes brittle after the refactor, and no longer proves `_default_web_read()` uses the helper | S1, S2, S4, S5 | .15 |
| C. Patch `content_extractor.extract_content` or return wrapped output from mocks | None | Violates the rejected `memory -> tools` reuse path and the bookmark no-wrap contract | S5, S6, S7 | .05 |

## 4. Recommendation (.95 confidence)

Advance #867 to backlog as the valid RED task for #825.

The evidence is consistent:

1. Once `bookmark_pipeline.py` imports `extract_markdown`, the correct seam is the module-local name, not `sys.modules["trafilatura"]`.
2. The helper mocks should stay raw and Markdown-shaped so the tests continue proving that bookmark ingestion remains unwrapped.
3. No new implementation task is needed because #825 is already the correct GREEN partner and #868 is already the helper prerequisite.

The only refinement still needed is architectural/editorial, not conceptual: the final AC should describe a RED-phase failure condition against pre-#825 code, and #868 should remain the explicit prerequisite.

## 5. Follow-up Tasks

1. Existing prerequisite: #868 — create `owlbear.web_extract.extract_markdown` as the legal leaf helper.
2. Current RED task: #867 — replace the 3 direct bookmark-pipeline `trafilatura` mocks plus the 1 bookmark-side integration seam with module-local `extract_markdown` mocks, and include a Markdown-return assertion.
3. Existing GREEN task: #825 — migrate `_default_web_read()` to `owlbear.web_extract.extract_markdown` without weakening the no-wrap invariant.

No new kanban tasks are required; the helper, RED, and GREEN chain already exists.
