# Validate context_hydration extract_markdown RED task

> **Owning task:** #869 — Update context_hydration tests to mock extract_markdown instead of trafilatura
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #869 already captures the correct post-#868 test seam: once `context_hydration.py`
imports a leaf helper, the tests should patch `owlbear.core.context_hydration.extract_markdown`
rather than `sys.modules["trafilatura"]`. The remaining question is task readiness: can #869
advance as the RED task now, and what follow-up is needed because its named parent #826 is
still blocked on the illegal `core -> tools` `extract_content` plan?

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | Python `unittest.mock` docs — Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 — official rule: patch the name used by the system under test |
| S2 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 — official guidance for patching module attributes and returned objects in tests |
| S3 | Architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 — `core/` may not import from `tools/` |
| S4 | Current caller + affected tests | `src/owlbear/core/context_hydration.py`, `tests/test_context_hydration.py`, `tests/test_content_safety_integration.py` | 1.0 — confirms the live seam, the 4 + 5 test sites, and the wrapping assertions that must survive |
| S5 | Existing local-patch precedent | `tests/test_web_search.py` | .95 — same repo already patches a module-local helper after a legal migration |
| S6 | Blocked parent task | `kanban/tasks/826-migrate-context-hydration-py-to-use-extract.md` | 1.0 — shows the stale `extract_content` plan is still blocked |
| S7 | Leaf-helper prerequisite | `kanban/tasks/868-create-leaf-markdown-extraction-helper-for-cross.md` | .95 — defines the legal helper `owlbear.web_extract.extract_markdown` |
| S8 | Sibling refined implementation task | `kanban/tasks/825-migrate-bookmark-pipeline-py-to-use-web-extract.md` | .95 — shows the correct pattern: keep RED/helper tasks separate and rewrite the GREEN task to the legal leaf helper |

## 3. Analysis

### 3.1 What #869 already gets right

| Claim in #869 | Evidence | Result |
|---------------|----------|--------|
| Tests should patch `owlbear.core.context_hydration.extract_markdown` | S1, S2, S4, S5 | Valid. Once the helper is imported into `context_hydration.py`, the module-local name is the correct patch target. |
| Raw helper-return mocks preserve current behavior checks | S4, S7 | Valid. `fetch_url()` still owns HTTP error handling and conditional wrapping, so helper mocks can stay raw. |
| The task scope is concrete and bounded | S4 | Valid. The blast radius is still the 4 direct mocks in `tests/test_context_hydration.py` and the 5 fetch-url-related mocks in `tests/test_content_safety_integration.py`. |

### 3.2 What is still missing

| Gap | Evidence | Impact |
|-----|----------|--------|
| #869 still names #826 as its parent | S6 | Misleading. #826 is blocked for the wrong abstraction, so the RED task currently points at a stale GREEN target. |
| No successor GREEN task exists yet | S6, S8 | The dependency chain is incomplete. Architect/test-writer would have to infer the missing implementation task instead of reading one from the board. |
| Reverting to `sys.modules["trafilatura"]` would keep the wrong seam alive | S1, S2, S4 | Brittle. It would bypass the imported helper boundary and reintroduce refactor-sensitive tests. |

### 3.3 Options

| Option | Pros | Cons | Evidence | Recommendation |
|--------|------|------|----------|----------------|
| A. Advance #869 unchanged and rely on later agents to reinterpret #826 | Smallest board diff | Leaves a stale parent and an ambiguous RED/GREEN pairing | S6, S8 | .40 |
| B. Advance #869 and create a successor GREEN task that targets `owlbear.web_extract.extract_markdown` | Keeps the correct RED seam, restores a coherent dependency chain, mirrors the sibling #825 pattern | Leaves #826 blocked/stale until later cleanup | S1, S3, S5, S6, S7, S8 | **Recommended (.93)** |
| C. Keep patching `sys.modules["trafilatura"]` even after #868 | No new follow-up task needed | Violates official patch guidance and keeps tests coupled to the old implementation detail | S1, S2, S4 | .15 |

## 4. Recommendation (.93 confidence)

Advance #869 to backlog as the valid RED task, and create a new GREEN implementation task that
replaces #826's blocked `extract_content` plan with a legal `owlbear.web_extract.extract_markdown`
migration.

This is the smallest action that preserves all of the evidence already gathered:

1. #869 itself is correct after #868 because tests should patch the imported helper where `fetch_url()` looks it up.
2. The wrapping assertions remain meaningful because the helper stays raw and `fetch_url()` keeps the local wrapping branch.
3. A separate GREEN successor is required because #826 is still architect-blocked and cannot serve as the parent implementation task anymore.

## 5. Follow-up Tasks

1. Existing prerequisite: #868 — create `owlbear.web_extract.extract_markdown` as the legal leaf helper.
2. Current RED task: #869 — replace the 4 + 5 `trafilatura` patches with module-local `extract_markdown` mocks.
3. New GREEN successor — replace stale #826 with a legal helper-based migration task.

```powershell
kanban\kanban-md.exe create "Migrate context_hydration.py to use web_extract.extract_markdown" --priority nice-to-have --status ideation --tags "dry,type:build,scope:core,phase-9" --body "Replace the direct trafilatura extraction in src/owlbear/core/context_hydration.py::fetch_url with the package-root leaf helper from #868 rather than src/owlbear/tools/browser/content_extractor.py. This task is the GREEN implementation step after RED task #869 and helper task #868. Source: docs/research/context-hydration-extract-markdown-red-task.md. AC: (1) src/owlbear/core/context_hydration.py imports and calls owlbear.web_extract.extract_markdown(resp.text, url=url) from fetch_url(), and no longer imports trafilatura directly, (2) fetch_url() does not import from owlbear.tools.* and still owns the local wrap_web_content behavior plus current HTTP error handling, (3) helper output remains raw markdown so fetch_url() continues to control wrapping and avoid double-wrap behavior, (4) the RED cases introduced by #869 pass, (5) the scoped tests covering tests/test_context_hydration.py and the fetch_url-related assertions in tests/test_content_safety_integration.py pass."
```
