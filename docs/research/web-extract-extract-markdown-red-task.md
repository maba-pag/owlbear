# Validate owlbear.web_extract.extract_markdown RED task

> **Owning task:** #874 — Add RED tests for owlbear.web_extract.extract_markdown
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #874 is the paired RED task for #868's new leaf helper `owlbear.web_extract.extract_markdown()`. The open questions are whether #874 already targets the right test seam for the helper itself, and whether the board needs any additional follow-up once #875 moves `content_extractor.py` onto that helper.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 — canonical `extract()` parameters for Markdown output, `include_links`, and `url` forwarding |
| S2 | adbar/trafilatura | <https://github.com/adbar/trafilatura> | .85 — upstream project context confirming Markdown/text extraction is a stable public surface |
| S3 | Python `unittest.mock` docs — Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 — official rule to patch the name used by the system under test |
| S4 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .95 — official guidance for scoped attribute/import patching and warnings about broad builtin patches |
| S5 | Current OwlBear test precedents | `tests/test_content_extractor.py`, `tests/test_bookmark_pipeline.py` | 1.0 — existing module-local mock pattern plus actionable ImportError coverage pattern |
| S6 | Current helper/refactor board context | `docs/research/leaf-markdown-extraction-helper.md`, `kanban/tasks/875-refactor-content-extractor-to-reuse-web-extract.md` | 1.0 — defines the helper contract and shows the downstream refactor that will consume it |
| S7 | Current tools-layer implementation | `src/owlbear/tools/browser/content_extractor.py` | .95 — shows which assertions belong to the helper today and which will become stale after #875 |

## 3. Analysis

### 3.1 What #874 already gets right

| Claim in #874 | Evidence | Result |
|---|---|---|
| Helper tests should own the raw `trafilatura.extract(..., output_format="markdown", include_links=True, url=url)` contract | S1, S2, S6, S7 | Valid. These kwargs are part of the helper's public contract after #868 and should not stay duplicated in downstream caller tests. |
| The task should cover `None` and raised-exception fallback as `""` | S5, S6, S7 | Valid. OwlBear's current extraction wrappers already normalize failures to empty text, and #868 explicitly makes that the helper contract. |
| Missing-dependency coverage belongs at the helper boundary | S3, S4, S5, S6 | Valid. #868 moves the lazy optional-dependency import into the helper, and OwlBear already uses narrow import-denial tests to assert actionable `ImportError` messages. |

### 3.2 What is still missing

| Gap | Evidence | Impact |
|---|---|---|
| #875 has no paired RED task | S5, S6, S7 | The TDD chain is incomplete for the `content_extractor.py` refactor. |
| Current `tests/test_content_extractor.py` assertions still pin the old raw `trafilatura.extract` seam | S3, S5, S7 | After #875, those tests would be checking helper internals from the wrong module and would force later agents to infer the replacement seam. |
| Expanding #874 to also cover `content_extractor.py` would mix two different seams | S3, S5, S6 | Poor fit. Helper-contract tests and downstream delegation tests should remain separate RED tasks. |

### 3.3 Options

| Option | Pros | Cons | Evidence | Recommendation |
|---|---|---|---|---|
| A. Advance #874 unchanged and create no further follow-up | Smallest immediate board change | Leaves #875 without a paired RED task even though its current tests target the soon-to-be-replaced seam | S5, S6, S7 | .45 |
| B. Advance #874 and create a separate RED task for #875 | Keeps #874 focused on helper behavior and restores a clean RED/GREEN pairing for the downstream refactor | Adds one extra ideation task | S3, S4, S5, S6, S7 | **Recommended (.93)** |
| C. Broaden #874 so it covers both the helper and `content_extractor.py` refactor | No additional board task | Violates single-responsibility and blurs which seam each test set is supposed to prove | S3, S5, S6 | .20 |

## 4. Recommendation (.93 confidence)

Advance #874 to backlog unchanged.

Implementation guidance for the RED tests:

1. Success and `url`-forwarding cases should patch the helper-local `trafilatura` lookup site and assert a single call with `html`, `output_format="markdown"`, `include_links=True`, and `url=url`.
2. `None` and raised-exception cases should use `return_value` / `side_effect` to prove the helper returns `""` instead of surfacing extraction failures.
3. Missing-dependency coverage should use a narrowly scoped import-denial patch, or an equivalent helper-local import seam, to assert the actionable install hint without relying on suite-global state.
4. Create a separate RED task for #875 because `content_extractor.py` will need delegation-focused tests after its raw extraction call moves to `owlbear.web_extract.extract_markdown()`.

## 5. Follow-up Tasks

1. Existing prerequisite: #868 — create the leaf helper and make #874's contract real.
2. Current RED task: #874 — prove the helper's direct contract at the helper boundary.
3. New RED successor — update `content_extractor.py` tests for the post-#875 delegation seam.

```powershell
kanban\kanban-md.exe create "Update content_extractor tests to mock extract_markdown delegation" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED phase for #875. Update tests/test_content_extractor.py for the post-refactor seam where extract_content() delegates raw markdown extraction to owlbear.web_extract.extract_markdown while extract_metadata and wrap_web_content remain local. Source: docs/research/web-extract-extract-markdown-red-task.md. AC: (1) focused tests exist for the post-#875 seam, (2) success-path tests patch owlbear.tools.browser.content_extractor.extract_markdown where extract_content() looks it up and assert one delegation with html and url while preserving ExtractionResult metadata fields, (3) empty-text and metadata-failure behavior stays covered without re-testing helper-internal trafilatura kwargs already owned by #874, (4) no test continues to assert direct raw markdown calls through content_extractor.trafilatura.extract, (5) scoped tests fail before #875 is implemented."
```
