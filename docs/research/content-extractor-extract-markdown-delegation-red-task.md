# Validate content_extractor Delegation RED Coverage

> **Owning task:** #881 - Update content_extractor tests to mock extract_markdown delegation
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #881 is the RED partner for #875. The question is whether
`tests/test_content_extractor.py` should stop patching
`owlbear.tools.browser.content_extractor.trafilatura` for raw markdown
extraction and instead patch
`owlbear.tools.browser.content_extractor.extract_markdown` once #875 moves the
raw extraction call into `src/owlbear/web_extract.py`, while still preserving
the caller-local metadata/result behavior that belongs in
`extract_content()`. This research also checks whether #881 needs new follow-up
tasks or whether the existing RED/GREEN pair is already sufficient.

## 2. Sources Studied

| ID | Source | Kind | Relevance | What it established |
|----|--------|------|-----------|---------------------|
| S1 | Python `unittest.mock` docs | External | .98 | Canonical rule: patch the name used by the system under test |
| S2 | pytest monkeypatch docs | External | .93 | Patches are scoped to the consumer lookup site and should stay narrow |
| S3 | trafilatura usage docs and GitHub repo | External | .92 | Raw markdown extraction contract is `extract(..., output_format="markdown", include_links=True, url=...)`; project license is Apache-2.0 |
| S4 | `src/owlbear/tools/browser/content_extractor.py`, `tests/test_content_extractor.py` | Local | 1.0 | Current implementation and tests still call and patch `trafilatura` directly |
| S5 | `src/owlbear/web_extract.py`, `tests/test_web_extract.py` | Local | .99 | The leaf helper already owns the raw `trafilatura.extract()` contract, empty-string fallback, and import-error behavior |
| S6 | `docs/research/web-extract-extract-markdown-red-task.md` | Local | .98 | Prior research already split helper-internal assertions from downstream delegation coverage and created #881 for the latter |
| S7 | `docs/research/leaf-markdown-extraction-helper.md`, task #875 | Local | .97 | Architecture intent: `extract_markdown()` owns raw markdown extraction; `extract_content()` keeps higher-level browser-tool behavior |
| S8 | task #881 | Local | .96 | Acceptance criteria already target `owlbear.tools.browser.content_extractor.extract_markdown` as the new seam |

## 3. Ownership Split After #875

| Concern | Best test home | Why |
|---------|----------------|-----|
| `extract_content()` delegates raw text extraction to `extract_markdown(html, url=...)` | `tests/test_content_extractor.py` | This is the caller seam #881 exists to validate, and the patched lookup site is the consumer module (`S1`, `S4`, `S8`) |
| `trafilatura.extract()` receives `output_format="markdown"`, `include_links=True`, and forwarded `url` | `tests/test_web_extract.py` | Those kwargs are the helper's public contract, not the browser tool's contract (`S3`, `S5`, `S6`) |
| `extract_metadata()` success/failure handling and `ExtractionResult` field preservation | `tests/test_content_extractor.py` | Metadata assembly remains local to `extract_content()` after #875 (`S4`, `S7`) |
| Empty helper output becomes `text=""` in the result | `tests/test_content_extractor.py` | The caller still owns how helper output is surfaced in `ExtractionResult`, but it should mock the helper return value rather than helper internals (`S4`, `S5`, `S8`) |
| Helper import errors and helper-side extraction exceptions | `tests/test_web_extract.py` | `extract_markdown()` already normalizes these behaviors; duplicating them downstream would re-test the helper instead of the caller seam (`S5`, `S6`) |

## 4. Patch-Target Comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Patch `owlbear.tools.browser.content_extractor.extract_markdown` | Matches the name `extract_content()` will look up after #875; directly proves the delegation seam; keeps the RED task stable if helper internals change again | Requires #875 to import/bind `extract_markdown` in the consumer module | Best fit (.96) (`S1`, `S4`, `S7`, `S8`) |
| B. Patch `owlbear.web_extract.extract_markdown` | Looks superficially closer to the real helper | Fails if #875 binds the helper into `content_extractor.py` via direct import; proves provider-module behavior instead of caller lookup behavior | Acceptable only if implementation deliberately does module attribute lookup at call time (.49) (`S1`, `S2`, `S7`) |
| C. Keep patching `owlbear.tools.browser.content_extractor.trafilatura` | Minimal test edits from the current file | Re-tests helper internals, misses the new delegation seam, and duplicates coverage already living in `tests/test_web_extract.py` | Reject (.08) (`S3`, `S5`, `S6`, `S8`) |

## 5. Minimal RED Scope for #881

Keep the RED task narrow. After #875 exists, `tests/test_content_extractor.py`
should cover only these behaviors:

1. Happy path: patch `content_extractor.extract_markdown` to return markdown,
   patch metadata locally, and assert `extract_markdown` was called once with
   the HTML and URL supplied to `extract_content()`.
2. Default URL path: assert the caller passes `url=None` to
   `content_extractor.extract_markdown` when no URL argument is supplied.
3. Empty-text path: mock `extract_markdown` to return `""` and keep the result
   text empty without reaching into `trafilatura` internals.
4. Metadata-failure path: keep the existing local behavior where metadata
   extraction errors do not discard already-extracted markdown text.

Do not add helper-internal assertions here. `tests/test_web_extract.py` already
owns the exact `trafilatura.extract()` kwargs, `None` fallback, and helper
import-error contract (`S5`, `S6`).

## 6. Recommendation (.95 confidence)

Advance #881 to backlog unchanged. The task is the correct RED companion for
task #875, and it should be implemented with one explicit constraint: patch
`owlbear.tools.browser.content_extractor.extract_markdown`, not
`owlbear.web_extract.extract_markdown` and not raw `trafilatura` calls. That
keeps the test focused on the consumer seam, preserves the existing local
metadata behavior, and avoids duplicating helper-boundary coverage that already
belongs in `tests/test_web_extract.py`.

## 7. Follow-up Tasks

No new kanban tasks are required.

- #881 already captures the RED change required before #875.
- #875 already captures the GREEN implementation that introduces the
  delegation seam.
- Earlier helper-boundary work is already tracked by #874 and documented in
  `docs/research/web-extract-extract-markdown-red-task.md`.

The correct action is to move #881 to backlog and let the normal architect
review gate decide when the RED work should enter implementation.
