# Close engine.py 90% Coverage Gate

> **Owning task:** #1111 — Quality: close engine.py 90pct coverage gate for task 1063
> **Date:** 2026-04-24 **Status:** Complete

## 1. Context and Question

Task #1063 (C-18: GREEN — engine activity/session wiring) has been stuck in review for multiple builder/test-writer cycles because `owlbear_kanban.engine` module coverage remains at 84% against a 90% reviewer gate. All AC-C42/C43 behavioral tests pass (126 green). The gap is structural: dead code inflates the denominator and large implemented-but-untested surface area isn't exercised.

**Question:** What's the minimum intervention to close the 90% gate?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` (1414 lines, 691 stmts) | Primary — contains all uncovered code |
| S2 | `serve/kanban/src/owlbear_kanban/models.py` `_normalise_legacy` validator | Proves dict-status branches are unreachable |
| S3 | `serve/kanban/tests/test_engine_coverage_1110.py` (51 tests, 17 classes) | Existing coverage uplift suite |
| S4 | pytest-cov term-missing output (3 scoped runs) | Empirical coverage baseline |
| S5 | Task #1063 body — test-writer/builder cycle notes (8 cycles) | Prior analysis of coverage gap |

## 3. Analysis

### 3.1 Current Coverage Baseline

| Scope | Files | Tests | Pass | engine.py % |
|-------|-------|-------|------|-------------|
| Narrow (4-file) | 1063 task + activity + atomicity + coverage_1110 | 126 | 126 | 75% |
| Broad (6-file) | + crash_safety_1101 + engine_storage | 171 | 171 | 84% |
| Broadest | all test_engine*.py | 295 | 295 | 84% |

Broad and broadest produce identical engine.py coverage — crash_safety and storage tests contribute the extra 9pp over narrow.

### 3.2 Classification of 111 Missed Lines

| Category | Lines | Count | Coverable? |
|----------|-------|-------|------------|
| Dead: Windows msvcrt branch | 299-307 | 9 | No — platform `win32` guard |
| Dead: dict-status in edit_task | 879 | 1 | No — `_normalise_legacy` ensures strings |
| Dead: dict-status in move_task | 958 | 1 | No — same reason |
| Dead: dict-status in end_work | 1173 | 1 | No — same reason |
| Hard: git mv success path | 283 | 1 | Needs git repo in tmp dir |
| Hard: git mv exception handler | 284-286 | 3 | Needs subprocess mock |
| Coverable: edit_task params | 876-878, 880-881, 883-884, 893-913 | 21 | Yes — pass each param |
| Coverable: show_task cache | 728-729, 732-748, 752-753 | 21 | Yes — warm cache + cold lookup |
| Coverable: list_tasks scan | 492-496, 513-526, 579-582, 588-590, 594, 598 | 24 | Yes — archive dir + corruption |
| Coverable: dep computation | 458-463, 477-484 | 14 | Yes — tasks with archived deps |
| Coverable: list_tasks filter/sort | 613-614, 616, 623, 632, 636, 662 | 8 | Yes — sort by created/updated/title |
| Coverable: engine properties | 415, 420, 433 | 3 | Yes — call board_config/refresh |
| Coverable: valid_transitions err | 446 | 1 | Yes — pass invalid status |
| Coverable: session/duration edges | 120, 142, 189, 217-218 | 4 | Yes — block outcome + tz-naive |
| Coverable: sweep edge | 1250 | 1 | Yes |
| Coverable: log parse errors | 1442-1443, 1449-1450 | 4 | Yes — corrupt JSONL |
| **TOTAL** | | **111** | |

**Dead: 12 lines. Coverable: 95 lines. Hard-to-cover: 4 lines.**

### 3.3 Coverage Ceiling Calculation

| Scenario | Stmts | Need (90%) | Gap from 580 |
|----------|-------|-----------|--------------|
| No changes | 691 | 622 | 42 |
| Remove dict branches (3 lines) | 688 | 620 | 40 |
| + pragma: no cover on msvcrt (9 lines) | 679 | 612 | 32 |
| + pragma on git-mv hard paths (4 lines) | 675 | 608 | 28 |

**With dead code removal + pragma on Windows branch: need to cover 32 of 95 coverable lines (34%).**

### 3.4 Highest-ROI Test Targets

| Target | Lines gained | Effort |
|--------|-------------|--------|
| edit_task params (status, priority, tags, deps, parent, block_reason) | ~21 | Low — 6-8 test methods |
| show_task index/cache paths | ~21 | Low — 3-4 tests with warm cache |
| engine properties (board_config, refresh_config, valid_transitions error) | ~4 | Trivial — 3 one-liner tests |
| dep computation (archived deps → dep_status) | ~14 | Medium — needs archive dir setup |

**Covering just edit_task + properties + show_task = ~46 lines → 626/679 = 92%.** Gate cleared.

## 4. Recommendation

**Confidence: 0.90** — the math is deterministic; only risk is off-by-one line counting.

**Approach:** Two-part intervention, single task scope:

1. **Remove dead dict-status branches** from `_status_rank()` (if present), `valid_transitions()`, `edit_task()`, `move_task()`, `end_work()`. Add `# pragma: no cover` to the Windows `msvcrt` branch in `_exclusive_file_lock()`.

2. **Add durable passing tests** to `test_engine_coverage_1110.py`:
   - `edit_task(status=..., priority=..., parent=..., add_tags=..., remove_tags=..., add_deps=..., remove_deps=..., block_reason=..., append_body+timestamp)`
   - `board_config()`, `refresh_config()`, `valid_transitions(invalid_status)`
   - `show_task()` via index hit + cache hit + glob fallback

3. **Verify** canonical 6-file quality-runner run → engine.py ≥ 90%.

Challenge: N/A — trivial quality task, no design trade-offs.

## 5. Follow-up Tasks

| ID | Title | Status |
|----|-------|--------|
| #1112 | Dead code: remove dict-status branches + pragma Windows branch in engine.py | research |
| #1113 | Coverage: add edit_task/show_task/property tests to test_engine_coverage_1110.py | research |

**Note:** Task bodies not populated due to MCP `create_task` body-parameter bug. AC and context are fully specified in this research doc (§3.2 for #1112, §3.4 for #1113).
