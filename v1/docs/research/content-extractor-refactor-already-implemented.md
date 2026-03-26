# Refactor content_extractor to reuse web_extract — Already Implemented

> **Owning task:** #875 — Refactor content_extractor to reuse web_extract.extract_markdown
> **Date:** 2026-03-24  **Status:** Complete

## 1. Context and Question

Task #875 requests that `content_extractor.py` delegate raw markdown text
extraction to `owlbear.web_extract.extract_markdown` while preserving metadata,
`ExtractionResult`, and `wrap_web_content` behavior. The question is whether
this work is still needed or has already been completed.

## 2. Sources Studied

| # | Source | Kind | Relevance |
|---|--------|------|-----------|
| S1 | `src/owlbear/tools/browser/content_extractor.py` (current HEAD) | Local | 1.0 |
| S2 | `git log --oneline -- src/owlbear/tools/browser/content_extractor.py` | Local | 1.0 |
| S3 | Commit `83eb7a9` — `feat: delegate extract_content text extraction to extract_markdown (#881, builder)` | Local | 1.0 |
| S4 | `tests/test_content_extractor.py` (current HEAD) | Local | .98 |
| S5 | `kanban/tasks/881-update-content-extractor-tests-to-mock-extract.md` | Local | .97 |
| S6 | `docs/research/leaf-markdown-extraction-helper.md` | Local | .95 |
| S7 | `src/owlbear/web_extract.py` (current HEAD) | Local | .95 |
| S8 | pytest run: `tests/test_content_extractor.py` — 12 passed | Local | 1.0 |

## 3. Analysis

### 3.1 AC verification against current codebase

| AC | Evidence | Status |
|----|----------|--------|
| AC1: no raw `trafilatura.extract` markdown call | `content_extractor.py:18` imports `extract_markdown`; line 83 calls `extract_markdown(html, url=url)`; `grep trafilatura.extract content_extractor.py` returns only `extract_metadata` refs (S1) | Done |
| AC2: metadata/wrapping unchanged | `extract_metadata()` at line 86, `wrap_untrusted_content` at line 107 remain local (S1) | Done |
| AC3: existing tests pass | `uv run pytest tests/test_content_extractor.py -q` → 12 passed (S4, S8) | Done |
| AC4: no new upward dependency | `owlbear.web_extract` is a leaf module importing no higher layers (S6, S7) | Done |

### 3.2 How it happened

Commit `83eb7a9` (2026-03-21) was made by the builder during task #881. The
commit message references `#881` but the diff includes both
`src/owlbear/tools/browser/content_extractor.py` (source) and
`tests/test_content_extractor.py` (tests). Task #881's AC was test-only, so
this was a scope breach: the builder implemented #875's source changes inside
# 881's commit (S2, S3, S5).

Task #881 was subsequently blocked with reason: "AC1 scope breach: #881 refined
contract is test-only, but commit 83eb7a9 also changes
`src/owlbear/tools/browser/content_extractor.py` while #875 remains ideation."

### 3.3 Current task state

| Task | Status | Observation |
|------|--------|-------------|
| #868 | Archived | Prerequisite: created `web_extract.extract_markdown` |
| #875 | Ideation | Described work already exists in codebase |
| #881 | Todo (blocked) | Blocked because its builder committed #875's source changes |

## 4. Recommendation (.97 confidence)

**Close #875 as already-implemented** and unblock #881.

The implementation in commit `83eb7a9` satisfies all 4 AC items. The scope
breach is a process issue, not a quality issue — the code is correct, tested,
and ruff-clean. Creating a new commit to re-do the same work would be waste.

**Action plan:**

1. Move #875 directly to `done` (all AC verified against current codebase).
2. Unblock #881 — its blocking reason ("while #875 remains ideation") no longer
   applies once #875 is acknowledged as done. The #881 test-only scope is
   already satisfied: `TestFromAC_ExtractMarkdownDelegation` exists and passes.
3. No new follow-up tasks needed — the delegation is complete.

## 5. Follow-up Tasks

No new tasks. The code change and its tests are already merged and green.
Downstream consumer migrations (#825, #873) are tracked separately.
