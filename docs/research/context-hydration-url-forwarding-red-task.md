# Context Hydration URL Forwarding RED Task

> **Owning task:** #876 - Add context_hydration RED assertions for extract_markdown url forwarding
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #876 supplements #869 and #873. The question is whether caller-level RED coverage still needs its own task once #869 moves the patch seam to `context_hydration.extract_markdown`, and what the smallest test contract is for proving that `fetch_url()` forwards both the fetched HTML body and source URL into `extract_markdown` without duplicating helper-boundary tests already owned by #874.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | trafilatura Python usage docs | <https://trafilatura.readthedocs.io/en/latest/usage-python.html> | 1.0 - `url=` forwarding matters for markdown extraction and relative-link resolution |
| S2 | Python `unittest.mock` - Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | 1.0 - caller tests must patch the name the module under test looks up |
| S3 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 - fixture-scoped consumer-site patching guidance |
| S4 | Existing migration research | `docs/research/context-hydration-web-extract-migration.md` | 1.0 - current GREEN path and the known remaining caller-contract gap |
| S5 | Current caller implementation | `src/owlbear/core/context_hydration.py` | 1.0 - shows `fetch_url()` still owns HTTP policy and wrapping |
| S6 | Current fetch_url tests | `tests/test_context_hydration.py`, `tests/test_content_safety_integration.py` | 1.0 - shows today's assertions stop at content and wrapping behavior |
| S7 | Existing helper tests | `tests/test_web_extract.py` | .95 - already owns helper-internal `trafilatura.extract(...)` kwarg coverage |
| S8 | Existing local-patch precedent | `tests/test_web_search.py` | .90 - repo precedent for patching a caller-local helper seam |

## 3. Analysis

### 3.1 Gap check

| Question | Evidence | Result |
|----------|----------|--------|
| Does #869 already prove the future helper call arguments? | S2, S3, S6, task #869 AC | No. #869 moves the seam to module-local `extract_markdown`, but it does not require an assertion on `resp.text` and `url=url`. |
| Are helper-internal `trafilatura` kwargs already covered elsewhere? | S1, S7 | Yes. #874 already proves `output_format="markdown"`, `include_links=True`, and `url` forwarding at the helper boundary. |
| Do current `fetch_url()` tests prove caller ownership only, not forwarding? | S5, S6 | Yes. They assert returned content and wrapping/contrast behavior, but not the future helper call arguments. |
| Is a dedicated caller-level supplement still the smallest way to close the gap? | S1, S2, S4, S5, S6, S7 | Yes. One small RED supplement closes the caller contract without duplicating helper tests. |

### 3.2 Options

| Option | Pros | Cons | Evidence | Recommendation |
|--------|------|------|----------|----------------|
| A. Let #869 cover both seam migration and forwarding assertions implicitly | Fewer tasks on paper | Leaves the most important caller contract unstated and easy to miss in review | S2, S4, S6 | .41 |
| B. Keep #876 as the scoped caller-forwarding supplement to #869 | Smallest diff, proves caller contract, avoids helper duplication | Requires architect to keep the task narrow | S1, S2, S4, S5, S6, S7, S8 | **Recommended (.94)** |
| C. Duplicate the full helper kwarg contract inside caller tests | Strongest local proof | Re-tests #874 at the wrong layer and makes future refactors brittle | S1, S2, S7 | .18 |

### 3.3 Recommended RED shape

| File | Assertion to add | What it proves | What it must not prove |
|------|------------------|----------------|------------------------|
| `tests/test_context_hydration.py` | Patch `owlbear.core.context_hydration.extract_markdown` on a success path and assert `assert_called_once_with(resp.text, url=url)` | Direct caller forwarding from `fetch_url()` | Helper-internal `trafilatura` kwargs |
| `tests/test_content_safety_integration.py` | Keep raw helper-return wrapping/contrast behavior and assert the same forwarded call on a `fetch_url()`-related integration path | Caller forwarding plus ownership of wrapping | Helper-internal extraction behavior |
| Both files | Return raw markdown from the helper mock | Preserves the current wrap/no-wrap contrast and avoids double-wrap false positives | Wrapped helper output or `ExtractionResult` objects |

## 4. Recommendation (.94 confidence)

Advance #876 to backlog as the valid RED supplement for #873. The task should stay separate from #869 because it proves a different contract: not where the helper is patched, but what `fetch_url()` sends into that helper.

The architect should tighten the task body in two places:

1. Replace "at least one scoped fetch_url test" with an explicit requirement that both `tests/test_context_hydration.py` and `tests/test_content_safety_integration.py` stay in scope.
2. State that caller tests assert only `extract_markdown(resp.text, url=url)` and raw helper-return behavior, while helper-internal `trafilatura` kwargs remain owned by #874.

This keeps the test stack clean:

- #874 owns helper internals
- #869 owns seam migration
- #876 owns caller forwarding
- #873 consumes all three as the GREEN gate

## 5. Follow-up Tasks

1. Existing task: #876 - Add context_hydration RED assertions for extract_markdown url forwarding.
   Priority: nice-to-have. Dependency role: RED supplement before #873 GREEN verification. AC: one direct and one integration `fetch_url()` assertion patch `context_hydration.extract_markdown`, assert HTML-body plus `url=url` forwarding, and keep raw helper-return wrapping checks.
2. No new kanban task was created. Reason: #876 already captures the concrete action; splitting it further would duplicate one narrow RED supplement into overlapping tasks.
