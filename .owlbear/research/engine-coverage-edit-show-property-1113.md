# Coverage: edit_task / show_task / property tests

> **Owning task:** #1113 — Coverage: add edit_task/show_task/property tests to test_engine_coverage_1110.py
> **Date:** 2026-04-24 **Status:** Complete

## 1. Context and Question

Task #1110 created `test_engine_coverage_1110.py` targeting uncovered engine paths. It covers 59 tests across 25 classes, reaching 64% engine.py coverage. Three areas remain uncovered:

1. **`show_task()`** — entirely absent (lines 726–754 uncovered)
2. **`edit_task()` mutation branches** — only unblock + timestamp tested; 6+ individual field-mutation branches uncovered (lines 876–920)
3. **Public properties** — `agent_name`, `revision`, `board_config()` not unit-tested at the engine level

Question: What specific paths need tests and what testing patterns should each use?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/kanban/src/owlbear_kanban/engine.py` L717–757 | Codebase | 1.0 — show_task implementation |
| `serve/kanban/src/owlbear_kanban/engine.py` L850–940 | Codebase | 1.0 — edit_task implementation |
| `serve/kanban/src/owlbear_kanban/engine.py` L413–420 | Codebase | 0.9 — properties + board_config |
| `serve/kanban/tests/test_engine_coverage_1110.py` L704–770 | Codebase | 1.0 — existing patterns |
| `serve/kanban/tests/test_idtofilename_cache_943.py` | Codebase | 0.7 — cache-specific tests |
| `tests/test_cockpit_mutation_api.py` | Codebase | 0.6 — endpoint-level edit coverage |
| Coverage report (pytest --cov) | Measurement | 1.0 — baseline: 64%, 250 lines missed |

## 3. Analysis

### show_task() — 6 distinct paths

| # | Path | Lines | Mechanism | Notes |
|---|------|-------|-----------|-------|
| 1 | Non-numeric task_id | 727–728 | `int()` raises → `int_id=None` | Falls through to glob |
| 2 | Cache index hit + mtime match | 731–748 | `_id_to_filename` lookup → cached | Requires `list_tasks()` first to populate index |
| 3 | Cache index hit + mtime changed | 731–750 | Stale mtime → re-read | Modify file after first read |
| 4 | Cache index hit + file deleted | 731–740 | `stat()` raises → evict + raise | Delete file after list_tasks populates cache |
| 5 | Glob fallback (found) | 752–755 | `int_id` not in index → glob | Fresh engine, no prior list_tasks |
| 6 | Not found | 752–756 | No glob matches → FileNotFoundError | Standard error path |

Path 2 is already tested in `test_idtofilename_cache_943.py` but NOT in the 1110 coverage suite. Including it here ensures the 1110 file is self-contained for engine coverage measurement.

### edit_task() — uncovered mutation branches

| # | Branch | Covered? | Line(s) |
|---|--------|----------|---------|
| 1 | `title=` | No | 889 |
| 2 | `body=` | No | 891 |
| 3 | `priority=` | No | 893 |
| 4 | `status=` | No | 895 |
| 5 | `parent=` | No | 897 |
| 6 | `add_tags` (with dedup) | No | 900–902 |
| 7 | `remove_tags` | No | 903 |
| 8 | `add_deps` (with dedup) | No | 905–907 |
| 9 | `remove_deps` | No | 908 |
| 10 | Invalid status | No | 878–880 |
| 11 | Invalid priority | No | 881–883 |
| 12 | `append_body` without timestamp | No | 924–926 |

Branches 10–11 are validation guards. Existing tests cover `blocked=False` (unblock) and `append_body+timestamp=True`.

### Properties

| Property | Type | Test approach |
|----------|------|---------------|
| `agent_name` | `str` (read-only) | Assert is non-empty string, stable across calls |
| `revision` | `int` (write counter) | Assert starts 0, increments after create/edit/move |
| `board_config()` | `BoardConfig` (deep copy) | Assert mutation of returned object doesn't affect engine |

## 4. Recommendation (confidence: 0.90)

Add three new test classes to `test_engine_coverage_1110.py`:

1. **`TestFromAC_EngineShowTaskPaths`** — 5–6 tests covering all show_task paths
2. **`TestFromAC_EngineEditTaskFieldMutations`** — parametrized tests for each field branch + validation
3. **`TestFromAC_EngineProperties`** — 3 tests for agent_name, revision, board_config

Estimated coverage uplift: ~30 missing lines → ~3.5–4% engine.py gain.

Pattern: follow existing `_make_board` / `_write_task` helpers; use `list_tasks()` to warm the cache before show_task cache-path tests; use `@pytest.mark.parametrize` for the 9 edit_task field branches to stay DRY.

Challenge: SKIP — T1 coverage task with no design recommendation to challenge.

## 5. Follow-up Tasks

Single implementation task — this IS #1113. AC written in task body; advance to backlog.
