# Board Fixture Helper RED Gate Validation

> **Owning task:** #935 — Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #935 proposes extracting the `_task`, `_move`, and paired JSON-payload builders from `tests/test_cli_board.py` into a dedicated `tests/cli_board_fixtures.py` module with a RED-phase test contract in `tests/test_cli_board_fixtures.py`. This gate validates the approach before it enters the architect queue.

Parent research: `docs/research/bearclaw-board-kanban-json-fixtures.md` (task #923).

## 2. Sources Studied

| ID | Source | Relevance |
|----|--------|-----------|
| S1 | `docs/research/bearclaw-board-kanban-json-fixtures.md` | Parent research with full trade-off analysis (.93 confidence for Option B) |
| S2 | `tests/test_cli_board.py` (830 lines, current HEAD) | Confirms `_task`, `_move`, `_subproc` remain local; `_subproc([_task()], [])` pattern repeated 15+ times |
| S3 | pytest how-to fixtures docs | Factory-style helpers are standard for reusable test arrangement data |
| S4 | `kanban/tasks/926-*.md` (archived) | Subprocess-helper lane is complete; boundary between #926 (CompletedProcess) and #935 (board JSON) is clear |
| S5 | `tests/conftest.py` → `make_completed_process` | Confirms shared helpers live in conftest only when multi-file; board helpers are single-file today |

## 3. Analysis

### Research checklist

| Item | Verdict | Evidence |
|------|---------|----------|
| Theoretical validity | Pass | Factory extraction of paired list/log payloads reduces within-file repetition and creates a testable data contract [S1, S2] |
| Prior art | Pass (2 sources) | pytest factory fixtures [S3]; existing `_task`/`_move` pattern in test_cli_board.py [S2] |
| Technical feasibility | Pass | Standard Python module import, no new deps, works with existing pytest infra |
| Architecture fit | Pass | Stays under `tests/`, avoids premature `conftest.py` widening, clear boundary with archived #926 [S4, S5] |
| Implementation approach | Pass | `board_task()` → dict, `board_move()` → dict, `board_payloads()` → `(list_json, log_json)` tuple [S1] |

### YAGNI assessment

`_task` and `_move` exist only in `test_cli_board.py` — zero second consumers [S2]. The extraction is motivated by **within-file** DRY (15+ repeated `_subproc([_task()], [])` setups), not cross-file reuse. Priority `nice-to-have` is appropriate. The parent research rated this .93 confidence, which is reasonable given the clear repetition pattern.

### Duplicate task issue

**#935 and #936 are near-identical tasks.** Both have the same title, AC, and purpose. The parent research doc explicitly references #936 (and #939) as its follow-ups. #935 was created 19 seconds before #936 — likely an accidental double-creation during research execution. Only one should proceed through the pipeline.

## 4. Recommendation (.90 confidence)

Advance #935 to backlog. The approach is sound, dependencies are satisfied (#910 and #926 both archived), and the AC is concrete and TDD-compatible.

Task 936 should be archived as a duplicate — it is not referenced by any other task's `depends_on`. Task 939 (the implementation task) should update its `depends_on` to reference 935 if it currently references 936.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Archive duplicate task #936 (duplicate of #935)" --priority nice-to-have --status ideation --tags cli,test,tooling,phase-14,scope:cli
```
