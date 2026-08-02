---
id: 1074
title: 'B-13: RED — pick_tasks tests'
status: archived
priority: medium
created: 2026-04-21T10:49:15.735084+00:00
updated: 2026-04-25T07:59:38.655083+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1072
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.3, §3.3, §4
Module: `serve/kanban/tests/test_engine_pick_tasks.py`

Test AgentView.pick_tasks — the 4-step dispatcher pipeline: filter (exclude claimed/archived/blocked/dep-blocked per D42+D58), sort (priority_rank ASC, age DESC, id ASC per D60), greedy wave assembly with size/dep-disjointness/agent-compatibility constraints (D63), cardinality limits.

## Acceptance Criteria

- [ ] AC22: `pick_tasks()` returns ≤3 waves; no intra-wave dep edges; no claimed; no archived; no `dep_status="blocked"`; no `blocked==true` (D58)
- [ ] AC23: Each DispatchEntry includes computed `agent` per BoardConfig.agent_map (D24)
- [ ] AC27: Task with dep on wontfix-archived → dep_status="blocked", excluded from pick_tasks
- [ ] AC28: Task with dep on deprecated-archived → dep_status="redirect" (not excluded)
- [ ] wave_size < 1 or max_waves < 1 → ValidationError(ERR_INVALID_WAVE_PARAM)
- [ ] Default wave_size falls back to BoardConfig.wave_size (D42)
- [ ] Sort: priority_rank ASC, age DESC, id ASC (deterministic) per D60
- [ ] Greedy wave assembly: three constraints (size, dep-disjointness, agent-compatibility) per D62+D63
- [ ] Task not fitting any wave and max_waves reached → dropped from this cycle
- [ ] pick_tasks is on AgentView, NOT CockpitView
- [ ] All tests fail (RED phase)
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_pick_tasks_1074.py
- Classes: TestFromAC_PickTasksFilter, TestFromAC_PickTasksSort, TestFromAC_PickTasksWaveAssembly, TestFromAC_PickTasksAgent, TestFromAC_PickTasksArchivedDeps, TestFromAC_PickTasksDefaults
- Tests per category: happy 2, edge 3, error 4, boundary 4
- Total: 13 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) |
|---|---|
| AC22 filter (dep_status=blocked, intra-wave dep) | test_dep_status_blocked_task_excluded, test_no_intra_wave_dep_edges_across_all_waves |
| AC23 agent from agent_map (D24) | test_agent_is_full_agent_map_value_not_first_character, test_different_status_tasks_carry_correct_agent |
| AC27 wontfix → blocked, excluded | test_wontfix_archived_dep_excludes_dependent_task, test_dropped_archived_dep_also_excluded, test_ac27_blocked_excluded_ac28_redirect_included_simultaneously |
| AC28 deprecated → redirect, included | test_ac27_blocked_excluded_ac28_redirect_included_simultaneously |
| wave_size < 1 → ValidationError | already covered by test_engine_coverage_1068.py (passes) — skipped per RED rule |
| max_waves < 1 → ValidationError | already covered by test_engine_coverage_1068.py (passes) — skipped per RED rule |
| Default wave_size fallback (D42) | test_default_wave_size_from_config_and_sort_order_combined (combined with sort) |
| Sort: priority_rank ASC, age DESC, id ASC (D60) | test_sort_priority_rank_age_desc_id_asc_combined, test_default_wave_size_from_config_and_sort_order_combined |
| Greedy wave dep-disjointness (D62) | test_dep_disjointness_splits_dependent_tasks_into_different_waves, test_task_dropped_when_dep_conflict_and_max_waves_exhausted |
| Greedy wave agent-compat (D63) | test_incompatible_agent_buckets_go_to_different_waves |
| Non-todo status included (§1.3 filter) | test_non_todo_status_tasks_included_when_unclaimed_and_unblocked |
| Task dropped when no wave fits | test_task_dropped_when_dep_conflict_and_max_waves_exhausted |
| pick_tasks on AgentView NOT CockpitView | already tested in test_engine_init_1068.py — skipped per RED rule |

Key failures surfaced:
1. dep_status='blocked' tasks not excluded (filter only checks blocked flag, not computed dep_status)
2. Current code limits pick_tasks to status='todo' only (should be all non-archived/non-claimed/non-blocked)
3. No sort applied — arbitrary filesystem order returned
4. No dep-disjointness check in wave assembly — dependent tasks can share a wave
5. No agent-compatibility check — incompatible buckets can share a wave
6. agent_map string value: code does string[0] returning 'b' instead of full 'builder'

Commit: 8a34ef8b
[[2026-04-25]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) `AgentView.pick_tasks` to implement full dispatch pipeline behavior.
- Fixes applied:
  - Filter now excludes tasks with computed `dep_status="blocked"` while retaining non-`todo` eligible statuses.
  - Deterministic sort added: `priority_rank ASC`, age (older first) via `created`, then `id ASC`.
  - Greedy wave assembly now enforces all three constraints: wave size, dependency disjointness, and agent-bucket compatibility.
  - Agent assignment now uses full `agent_map` value (no first-character truncation).
  - Tasks that cannot fit and when `max_waves` is exhausted are dropped for the current cycle with guidance.
- Tests: 13/13 `TestFromAC_*` tests in [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py) passing via quality-runner.
- Lint: clean (ruff) on touched source and task test file.
- Coverage: quality-runner reported `owlbear_kanban.engine` at 29% module-wide in scoped run (large legacy module); task-scoped assertions for #1074 all green.
- Commit: `349d0050` (`feat: implement pick_tasks dispatch pipeline (#1074, builder)`).

- Reflection:
  - Main failure root was an overly narrow `todo` filter plus naive chunking.
  - Minimal-risk path was to keep changes isolated to `pick_tasks` and reuse existing dependency semantics.
  - Scoped quality-runner evidence remained stable across retry after lint-only adjustment.
[[2026-04-25]]
## Review Evidence
### Test Results
- pytest: 279 passed, 0 failed via quality-runner on serve/kanban/tests/test_engine_pick_tasks_1074.py, serve/kanban/tests/test_engine_coverage_1068.py, and serve/kanban/tests/test_engine_init_1068.py

### Lint: clean

### Coverage: owlbear_kanban.engine 82% (below the 90% review gate)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC22: at most 3 waves; no intra-wave dep edges; no claimed; no archived; no dep_status blocked; no blocked=true | test_dep_status_blocked_task_excluded; test_no_intra_wave_dep_edges_across_all_waves | Only partially. The suite proves dep_status blocked exclusion and dep-edge separation, but there is no pick_tasks proof for claimed tasks, blocked=true tasks, archived tasks, or the default 3-wave cap despite the filter path at serve/kanban/src/owlbear_kanban/engine.py:1999 and default max_waves at serve/kanban/src/owlbear_kanban/engine.py:1977 | MISSING |
| AC23: DispatchEntry carries BoardConfig.agent_map value | test_agent_is_full_agent_map_value_not_first_character; test_different_status_tasks_carry_correct_agent | Yes | COVERED |
| AC27: wontfix or dropped archived dependency becomes blocked and excluded | test_wontfix_archived_dep_excludes_dependent_task; test_dropped_archived_dep_also_excluded; test_ac27_blocked_excluded_ac28_redirect_included_simultaneously | Yes | COVERED |
| AC28: deprecated archived dependency becomes redirect and remains included | test_ac27_blocked_excluded_ac28_redirect_included_simultaneously | Yes | COVERED |
| wave_size < 1 or max_waves < 1 raises ERR_INVALID_WAVE_PARAM | test_pick_tasks_invalid_max_waves_raises; test_pick_tasks_invalid_wave_size_raises in serve/kanban/tests/test_engine_coverage_1068.py:2098 and :2105 | Yes | COVERED |
| Default wave_size falls back to BoardConfig.wave_size | test_default_wave_size_from_config_and_sort_order_combined | Yes | COVERED |
| Sort is priority_rank ASC, age DESC, id ASC | test_sort_priority_rank_age_desc_id_asc_combined; test_default_wave_size_from_config_and_sort_order_combined | Yes | COVERED |
| Greedy wave assembly enforces size, dep-disjointness, and agent-compatibility | test_dep_disjointness_splits_dependent_tasks_into_different_waves; test_task_dropped_when_dep_conflict_and_max_waves_exhausted; test_incompatible_agent_buckets_go_to_different_waves | Yes for the main three constraints | COVERED |
| Task that cannot fit any wave and max_waves is reached is dropped | test_task_dropped_when_dep_conflict_and_max_waves_exhausted | Yes | COVERED |
| pick_tasks is on AgentView and not on CockpitView | test_agent_view_has_pick_tasks_stub in serve/kanban/tests/test_engine_init_1068.py:264 | No. This only proves positive AgentView ownership; there is no negative CockpitView proof although CockpitView omits the method at serve/kanban/src/owlbear_kanban/engine.py:2583 | MISSING |
| All tests fail in RED phase | Task body self-report only | No independent recorded failing output | MISSING |

#### Security Review
- No issues found in serve/kanban/src/owlbear_kanban/engine.py:1977-2127. The reviewed change is an in-memory selector with no shell, SQL, template, path, or secret-handling surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC classes in serve/kanban/tests/test_engine_pick_tasks_1074.py | No builder edits detected; quality-runner changed-files report attributes only serve/kanban/src/owlbear_kanban/engine.py to the builder commit | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | serve/kanban/tests/test_engine_coverage_1068.py:2088 only checks wave count is at least one and that ids are present; it would not catch ordering, default-cap, or filter regressions |
| Negative and error-path coverage | WEAK | No pick_tasks proof for claimed, blocked=true, archived, missing-dependency exclusion, or invalid config.wave_size fallback at serve/kanban/src/owlbear_kanban/engine.py:1992 and :1642 |
| Manual mutation reasoning | WEAK | Removing unclaimed or blocked filtering from serve/kanban/src/owlbear_kanban/engine.py:1999 or changing the default max_waves=3 at :1977 would not fail the current scoped suite |
| Test independence | ADEQUATE | Tests build isolated temp boards |
| Descriptive names | STRONG | Task tests are clearly named |

#### Data Safety
- No issues found. AgentView.pick_tasks is read-only in the reviewed path.

#### Implementation-Aware Gaps
- No direct behavioral proof for claimed, blocked=true, or archived exclusion through the pick_tasks filter path at serve/kanban/src/owlbear_kanban/engine.py:1999.
- No pick_tasks proof for the missing-dependency blocked branch at serve/kanban/src/owlbear_kanban/engine.py:1642.
- No proof for invalid BoardConfig.wave_size fallback at serve/kanban/src/owlbear_kanban/engine.py:1992.
- No behavioral proof for the default max_waves=3 cap at serve/kanban/src/owlbear_kanban/engine.py:1977.
- Repo-wide search found no explicit test proving CockpitView does not expose pick_tasks; existing evidence is only indirect adapter coverage.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Static code reading suggests the implementation itself matches the requested pipeline: filter at serve/kanban/src/owlbear_kanban/engine.py:1999, dep_status exclusion at :2006, deterministic ordering at :2030, overflow handling at :2100, and DispatchEntry agent assignment at :2109.
- There is duplicate _compute_dep_status logic at serve/kanban/src/owlbear_kanban/engine.py:575 and :1627. Not blocking here, but it is drift-prone.
- The quality-runner summary sentence said the task passed scoped gates, but the numeric report still shows 82% module coverage and the code review found missing AC proof. Those numbers govern the verdict.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC22 | Partial proof only: serve/kanban/tests/test_engine_pick_tasks_1074.py:217 and :237 cover dep_status blocked and dep-edge separation, but not claimed, blocked=true, archived, or default 3-wave cap | test_dep_status_blocked_task_excluded; test_no_intra_wave_dep_edges_across_all_waves | FAIL |
| AC23 | serve/kanban/tests/test_engine_pick_tasks_1074.py:442 and :465 assert full agent_map values | agent-map tests | PASS |
| AC27 | serve/kanban/tests/test_engine_pick_tasks_1074.py:501, :519, and :530 prove blocked archived-dep exclusion | archived-dependency tests | PASS |
| AC28 | serve/kanban/tests/test_engine_pick_tasks_1074.py:530 proves redirect archived-dep inclusion | combined AC27/AC28 test | PASS |
| Invalid params | serve/kanban/tests/test_engine_coverage_1068.py:2098 and :2105 raise ERR_INVALID_WAVE_PARAM | invalid-param tests | PASS |
| Default wave_size fallback | serve/kanban/tests/test_engine_pick_tasks_1074.py:567 proves config wave_size success path | default fallback test | PASS |
| Deterministic sort | serve/kanban/tests/test_engine_pick_tasks_1074.py:272 proves priority, age, and id ordering | sort test | PASS |
| Greedy wave assembly | serve/kanban/tests/test_engine_pick_tasks_1074.py:321, :344, and :378 exercise the three main constraints | wave assembly tests | PASS |
| Drop when no wave fits | serve/kanban/tests/test_engine_pick_tasks_1074.py:344 proves drop-on-overflow behavior | overflow test | PASS |
| AgentView only, not CockpitView | serve/kanban/tests/test_engine_init_1068.py:264 proves only positive AgentView ownership; no negative CockpitView test | method existence test | FAIL |
| RED phase all fail | No independent recorded failing output in the task body | none | FAIL |

### Confidence: 0.82
### Verdict: FAIL

- Reflection:
  - The implementation reads as correct; the failure is evidence quality and missing AC proof.
  - The biggest gap is AC22 coverage drift: the suite spends assertions on dep-disjointness twice while never proving claimed, blocked=true, archived, or default 3-wave-cap behavior.
  - Module coverage on the touched engine module remains below the review gate, so more targeted tests are still needed even with a green task subset.
[[2026-04-25]]
## Test-Writer Notes (Retry)

**Test file:** serve/kanban/tests/test_engine_pick_tasks_1074.py
**Retry reason:** Reviewer cited missing AC22 proof tests and no negative CockpitView test.

### Changes — 6 new tests added

Two new classes appended (original 13 tests in 6 classes unchanged):

| Class | Tests | Coverage |
|---|---|---|
| `TestFromAC_PickTasksAC22Proof` | 5 | claimed exclusion, blocked=true exclusion, archived exclusion, missing-dep blocked branch, default 3-wave cap |
| `TestFromAC_PickTasksViewScope` | 1 | Negative CockpitView proof |

### AC coverage table (retry additions)

| Reviewer-cited gap | Test | Mutation guard |
|---|---|---|
| No proof for claimed exclusion | `test_claimed_task_excluded_from_pick_tasks` | Fails if unclaimed=True removed from engine.py:1999 |
| No proof for blocked=true exclusion | `test_blocked_flag_true_task_excluded` | Fails if blocked=False removed from engine.py:1999 |
| No proof for archived exclusion | `test_archived_task_absent_from_dispatchable_pool` | Fails if archived=False removed from engine.py:1999 |
| No proof for missing-dep blocked branch | `test_missing_dependency_makes_task_dep_blocked` | Fails if engine.py:1642 missing-dep branch removed |
| No proof for default 3-wave cap | `test_default_max_waves_cap_is_three` | Fails if engine.py:1977 default max_waves raised |
| No negative CockpitView proof | `test_cockpit_view_does_not_expose_pick_tasks` | Fails if pick_tasks added to CockpitView |

### Pytest result
`19 passed` (13 original + 6 new) — ruff clean.

### Retry-cycle note
Builder commit 349d0050 preempted the RED phase for these specific behaviors: `list_tasks(archived=False, blocked=False, unclaimed=True)` at engine.py:1999 and `max_waves=3` default at engine.py:1977 already implement every filter the new tests exercise. All 6 new tests pass immediately — they serve as forward mutation guards rather than RED-phase failures. Reviewer requested these tests as proof; they now provide direct behavioral evidence for each AC22 sub-criterion.
[[2026-04-25]]
## Builder Notes
- Implementation: no code changes in this builder cycle; existing `AgentView.pick_tasks` implementation retained.
- Verification scope: `serve/kanban/tests/test_engine_pick_tasks_1074.py` plus related durable checks referenced by task notes.
- Tests: 285 passed, 0 failed, 0 skipped (quality-runner scoped run).
- Lint: ruff clean on scoped paths.
- Coverage snapshot: `owlbear_kanban.engine` 82%, `owlbear_kanban.storage` 64%, `owlbear_kanban.models` 96%.
- Evidence summary: retry-added AC22/AC27/AC28 proof tests and CockpitView negative test are green against the current implementation.

- Reflection:
  - Retry cycle objective was evidence closure, not feature implementation.
  - Expanded proof tests now directly guard previously flagged AC22 sub-criteria.
  - Kept scope surgical by avoiding unrelated module edits.
  - Coverage remains constrained by legacy module breadth outside this task path.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner scoped run on [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py): pytest 285 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: clean.

### Coverage
- `owlbear_kanban.engine`: 82% in the scoped quality-runner report, below the 90% review gate for the touched module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC22: `pick_tasks()` returns <=3 waves; no intra-wave dep edges; no claimed; no archived; no `dep_status="blocked"`; no `blocked==true` | [test_dep_status_blocked_task_excluded](serve/kanban/tests/test_engine_pick_tasks_1074.py#L217), [test_no_intra_wave_dep_edges_across_all_waves](serve/kanban/tests/test_engine_pick_tasks_1074.py#L237), [test_claimed_task_excluded_from_pick_tasks](serve/kanban/tests/test_engine_pick_tasks_1074.py#L618), [test_blocked_flag_true_task_excluded](serve/kanban/tests/test_engine_pick_tasks_1074.py#L639), [test_archived_task_absent_from_dispatchable_pool](serve/kanban/tests/test_engine_pick_tasks_1074.py#L659), [test_missing_dependency_makes_task_dep_blocked](serve/kanban/tests/test_engine_pick_tasks_1074.py#L680), [test_default_max_waves_cap_is_three](serve/kanban/tests/test_engine_pick_tasks_1074.py#L699) | Yes | COVERED |
| AC23: each `DispatchEntry` includes computed `agent` per `BoardConfig.agent_map` | [test_agent_is_full_agent_map_value_not_first_character](serve/kanban/tests/test_engine_pick_tasks_1074.py#L442), [test_different_status_tasks_carry_correct_agent](serve/kanban/tests/test_engine_pick_tasks_1074.py#L465) | Yes | COVERED |
| AC27: dep on `wontfix`-archived -> `dep_status="blocked"`, excluded from `pick_tasks` | [test_wontfix_archived_dep_excludes_dependent_task](serve/kanban/tests/test_engine_pick_tasks_1074.py#L501) plus current helper mapping at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1637) | Partially. The test proves exclusion through the current path, but no current test directly asserts the exact `wontfix -> "blocked"` value named in the AC. | LAX |
| AC28: dep on `deprecated`-archived -> `dep_status="redirect"`, not excluded | [test_ac27_blocked_excluded_ac28_redirect_included_simultaneously](serve/kanban/tests/test_engine_pick_tasks_1074.py#L530) plus current helper mapping at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1639) | Partially. The test proves inclusion through the current path, but no current test directly asserts the exact `deprecated -> "redirect"` value named in the AC. | LAX |
| `wave_size < 1` or `max_waves < 1` -> `ValidationError(ERR_INVALID_WAVE_PARAM)` | [test_pick_tasks_invalid_max_waves_raises](serve/kanban/tests/test_engine_coverage_1068.py#L2098), [test_pick_tasks_invalid_wave_size_raises](serve/kanban/tests/test_engine_coverage_1068.py#L2105), validation branch at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2009) | Partially. Explicit args are covered, but there is no proof for the `effective_wave < 1` fallback branch when config `wave_size` is invalid. | LAX |
| Default `wave_size` falls back to `BoardConfig.wave_size` | [test_default_wave_size_from_config_and_sort_order_combined](serve/kanban/tests/test_engine_pick_tasks_1074.py#L567) | Yes | COVERED |
| Sort is `priority_rank ASC`, `age DESC`, `id ASC` | [test_sort_priority_rank_age_desc_id_asc_combined](serve/kanban/tests/test_engine_pick_tasks_1074.py#L272) and [test_default_wave_size_from_config_and_sort_order_combined](serve/kanban/tests/test_engine_pick_tasks_1074.py#L567) | Yes | COVERED |
| Greedy wave assembly enforces size, dep-disjointness, and agent-compatibility | [test_dep_disjointness_splits_dependent_tasks_into_different_waves](serve/kanban/tests/test_engine_pick_tasks_1074.py#L321), [test_task_dropped_when_dep_conflict_and_max_waves_exhausted](serve/kanban/tests/test_engine_pick_tasks_1074.py#L344), [test_incompatible_agent_buckets_go_to_different_waves](serve/kanban/tests/test_engine_pick_tasks_1074.py#L378) | Yes | COVERED |
| Task not fitting any wave and `max_waves` reached is dropped | [test_task_dropped_when_dep_conflict_and_max_waves_exhausted](serve/kanban/tests/test_engine_pick_tasks_1074.py#L344) | Yes | COVERED |
| `pick_tasks` is on `AgentView`, not `CockpitView` | [test_agent_view_has_pick_tasks_stub](serve/kanban/tests/test_engine_init_1068.py#L264) and [test_cockpit_view_does_not_expose_pick_tasks](serve/kanban/tests/test_engine_pick_tasks_1074.py#L731) with current `CockpitView` surface at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2604) | Yes | COVERED |
| All tests fail (RED phase) | No current-snapshot proof. The retry note explicitly states the added proofs were written after the implementation was already green, and the live implementation at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1993) already satisfies those assertions. | No | MISSING |

#### Security Review
- No issues found in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1993). The reviewed code is an in-memory selector with no shell, SQL, path, template, or deserialization surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suite in [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py) | Current file is additive relative to the original task-owned suite: the original assertions remain and six retry tests were appended at [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L608). No weakening is visible in the live file. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The task-owned 1074 suite uses direct ID and agent assertions, but the durable smoke test [test_pick_tasks_todo_tasks_returned_in_waves](serve/kanban/tests/test_engine_coverage_1068.py#L2088) remains broad. |
| Negative and error-path coverage | WEAK | No test exercises the invalid-config fallback guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2009), and the current snapshot cannot satisfy the RED-phase AC. |
| Manual mutation reasoning | WEAK | The exact `wontfix -> blocked` and `deprecated -> redirect` strings could drift while the current inclusion/exclusion assertions still pass. |
| Test independence | STRONG | The reviewed tests use isolated `tmp_path` boards throughout [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py). |
| Descriptive names | STRONG | The task-owned tests are behavior-specific and readable. |

#### Data Safety
- No issues found. `AgentView.pick_tasks` is read-only on the reviewed path.

#### Implementation-Aware Gaps
- No direct proof for the `effective_wave < 1` fallback branch at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2009).
- No current-snapshot proof for the RED-phase AC. The live workspace snapshot is green on the retry-added proofs.
- The touched module still sits at 82% coverage in the independent scoped quality run.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The implementation itself appears correct on the reviewed path: filter at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2015), deterministic sort at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2035), greedy placement at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2094), and `DispatchEntry.agent` assignment at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2125).
- `dep_status` helper logic remains duplicated between [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L564) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1643). Not blocking here, but it is drift-prone.
- Several task-owned docstrings still narrate the pre-fix state. Non-blocking, but stale commentary weakens the evidence story.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC22 | Current filter call at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2015) plus direct filter/cap tests at [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L618), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L639), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L659), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L680), and [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L699) | AC22 proof set | PASS |
| AC23 | [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L442) and [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L465) against [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2125) | agent-map tests | PASS |
| AC27 | Behavior is correct in the live code via [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1637) and exclusion is exercised at [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L501), but the exact string contract is not directly asserted by a current test | wontfix exclusion test | FAIL |
| AC28 | Behavior is correct in the live code via [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1639) and inclusion is exercised at [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L530), but the exact string contract is not directly asserted by a current test | AC27/AC28 combined test | FAIL |
| Invalid params | Explicit arg validation passes at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2098) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2105), but the fallback-invalid branch at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2009) is unproven | invalid-param tests | FAIL |
| Default `wave_size` fallback | [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L567) | default fallback test | PASS |
| Deterministic sort | [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L272) | sort test | PASS |
| Greedy wave assembly | [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L321), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L344), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L378) | wave assembly tests | PASS |
| Drop when no wave fits | [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L344) | overflow test | PASS |
| `AgentView` only, not `CockpitView` | [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L264), [serve/kanban/tests/test_engine_pick_tasks_1074.py](serve/kanban/tests/test_engine_pick_tasks_1074.py#L731), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2604) | ownership/scope tests | PASS |
| All tests fail in RED phase | No valid proof in the current snapshot; retry note states the added proofs passed immediately against already-green code | none | FAIL |

### Confidence: 0.83
### Verdict: FAIL
### Action
- Route to `backlog`. The implementation now looks correct, but the task contract no longer matches the live deliverable because AC11 still requires a RED snapshot that the current workspace cannot provide. The remaining exact-string and fallback-branch proof gaps also keep the test evidence below review standard.

- Reflection:
  - The implementation path itself is in good shape; the blocker is evidence quality and stale AC state.
  - The retry closed the earlier AC22 and CockpitView gaps, but it did so after the code was already green.
  - Exact sibling-reason mappings (`wontfix`, `deprecated`) remain easy to under-prove when tests only assert the downstream include/exclude effect.
[[2026-04-25]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED-phase test suite for pick_tasks only |
| Interface clarity | REFINE | AC27/AC28 need explicit dep_status string assertion requirement; config fallback AC missing (see refinements below) |
| Dependency correctness | PASS | Dep #1072 is done/archived |
| Module layering | PASS | Tests only; no import violations |
| TDD compliance | PASS | This IS the test task (tdd:red) |
| KISS/YAGNI | PASS | Scoped to pick_tasks behavior only |
| Premise challenge | PASS | Valid — pick_tasks is a new Brief B feature requiring test coverage |
| Pattern consistency | PASS | Follows existing test patterns (isolated tmp_path boards, TaskSummary assertions) |
| Security surface | N/A | In-memory selector with no external I/O |
| Single domain | PASS | kanban engine domain only |

### AC Refinements (supersede original AC where noted)

**AC27 (refined):** Task with dep on wontfix-archived → `dep_status="blocked"` asserted via `list_tasks` or `show_task` on the same board AND excluded from `pick_tasks`. The behavioral exclusion test alone is insufficient because `dep_status` is a public field on `TaskSummary` (models.py:301) projected through `list_tasks` (engine.py:791) and `show_task` (engine.py:1955). The existing test pattern in `test_engine_reads_1069.py:483` and `test_engine_list_show_1071.py:274` already demonstrates how to assert the exact string. The test-writer should add a `dep_status` string assertion to the existing AC27 test or add a companion assertion.

**AC28 (refined):** Task with dep on deprecated-archived → `dep_status="redirect"` asserted via `list_tasks` or `show_task` AND included in `pick_tasks`. This refinement is critical: the pick_tasks filter only excludes `"blocked"`, so inclusion cannot distinguish `"redirect"` from `"ok"` — the string assertion is the ONLY way to prove AC28's dep_status contract. See `test_engine_list_show_1071.py:295` for the existing pattern.

**New AC — config fallback validation:** `BoardConfig.wave_size < 1` (no explicit `wave_size` arg to `pick_tasks`) → `ValidationError(ERR_INVALID_WAVE_PARAM)`. `BoardConfig` has no `ge=1` validator on `wave_size` (models.py:161), so the defensive guard at engine.py:2009 is genuinely reachable. One new test needed.

**RED phase (scoped):** "All tests fail (RED phase)" applies to the original 13-test RED commit (8a34ef8b). The 6 retry-added proof tests (TestFromAC_PickTasksAC22Proof, TestFromAC_PickTasksViewScope) were written after the builder's GREEN implementation and are post-GREEN mutation guards by design — they cannot exhibit RED-phase failure. The reviewer should verify RED-phase evidence against the original commit, not the current snapshot. Retry proof tests are evaluated on assertion quality and mutation resistance, not RED-phase failure.

**Coverage scope:** The 90% coverage target (r-pipeline-protocol) applies to task-touched code paths. `pick_tasks` spans engine.py:1993-2130 (~137 lines). Module-wide 82% reflects untouched legacy code across the ~2600-line engine module and is not in scope for this task. The reviewer should assess coverage of pick_tasks-adjacent lines specifically.

### Challenge Results
- Challenger: `reconsider` (confidence 0.46)
- Key challenges: (1) dep_status is public, not internal — behavioral proof insufficient for AC28; (2) RED rewrite is historical not current; (3) coverage waiver lacks protocol citation
- Architect response: **accepted challenges 1 and 3**, revised AC27/AC28 to require explicit dep_status string assertions through public API, added coverage scoping note. **Partially rebutted challenge 2**: RED evidence is inherently historical in the TDD cycle (reviewer always sees GREEN snapshot), but added scoping clarity and separated retry proof tests from RED-phase deliverables. The revised REFINE addresses all challenger concerns.

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| config.wave_size < 1, no explicit arg | Invalid effective wave size | ValidationError(ERR_INVALID_WAVE_PARAM) | Yes (engine.py:2009) | Clear error message |

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC27, AC28, added config fallback AC, scoped RED-phase and coverage requirements. Advanced to todo. Test-writer should add: (1) dep_status string assertions for AC27/AC28 tests, (2) one config fallback validation test, then proceed through pipeline.
[[2026-04-25]]
## Test-Writer Notes (Retry 2)

**Test file:** serve/kanban/tests/test_engine_pick_tasks_1074.py
**Retry reason:** Architect review cited 3 remaining gaps after Retry 1: (1) no exact dep_status string assertion for AC27/AC28 through public API; (2) no config fallback validation test (BoardConfig.wave_size < 1, no explicit arg).

### Changes — 3 new tests added in 2 new classes

| Class | Tests | Coverage |
|---|---|---|
| `TestFromAC_PickTasksDepStatusString` | 2 | AC27: show_task returns dep_status='blocked' for wontfix-archived dep; AC28: show_task returns dep_status='redirect' for deprecated-archived dep |
| `TestFromAC_PickTasksConfigFallback` | 1 | config.wave_size=0 + no explicit arg → ValidationError(ERR_INVALID_WAVE_PARAM) |

### AC coverage table (retry 2 additions)

| Architect-cited gap | Test | Mutation guard |
|---|---|---|
| AC27: no exact dep_status='blocked' string assertion | `test_wontfix_archived_dep_sets_dep_status_blocked_string` | Fails if `_compute_dep_status` renames 'blocked' or breaks wontfix mapping |
| AC28: no exact dep_status='redirect' string assertion | `test_deprecated_archived_dep_sets_dep_status_redirect_string` | Fails if `_compute_dep_status` renames 'redirect' or breaks deprecated mapping; this is the ONLY way to prove AC28's dep_status contract (inclusion alone cannot distinguish 'redirect' from 'ok') |
| New AC: config.wave_size < 1, no explicit arg → ValidationError | `test_config_wave_size_zero_raises_validation_error_without_explicit_arg` | Fails if effective_wave guard at engine.py:2009 is removed |

### Imports added
- `import pytest`
- `from owlbear_kanban.errors import ValidationError`

### Pytest result
22 passed (19 original + 3 new) — all tests green against current implementation (post-GREEN mutation guards per architect's scoping note). Ruff: clean.

### Retry-cycle note
All 3 new tests pass immediately against the current green implementation, consistent with the architect's guidance that retry proof tests are evaluated on assertion quality and mutation resistance, not RED-phase failure. The dep_status string tests are the ONLY direct proof for the exact AC27/AC28 string contracts — behavioral exclusion/inclusion alone was insufficient (AC28 'redirect' is indistinguishable from 'ok' in pick_tasks output).
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this cycle; existing `AgentView.pick_tasks` implementation in `serve/kanban/src/owlbear_kanban/engine.py` satisfies retry-2 assertions.
- Files changed: none.
- Tests: scoped quality-runner pass on `serve/kanban/tests/test_engine_pick_tasks_1074.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, and `serve/kanban/tests/test_engine_init_1068.py` -> 288 passed, 0 failed, 0 errors.
- Lint: `ruff check` clean for `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_pick_tasks_1074.py`.
- Coverage: `owlbear_kanban.engine` = 82% in scoped run (module-wide legacy breadth; task-path assertions for #1074 are green).
- Evidence summary: AC22/AC23/AC27/AC28 and retry-2 dep_status-string + config-fallback tests are passing against current implementation; no additional GREEN-phase code changes were required.

- Reflection:
  - Retry-2 was evidence closure, not behavior-gap repair; implementation was already aligned.
  - quality-runner output remains stable across repeated scoped verification.
  - Remaining coverage shortfall is module-wide and outside this task’s narrowly exercised path.
  - Kept this cycle surgical by avoiding unrelated edits.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_engine_pick_tasks_1074.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, and `serve/kanban/tests/test_engine_init_1068.py`: pytest 288 passed, 0 failed, 0 skipped, 0 errors.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_pick_tasks_1074.py`.
- VS Code diagnostics: no errors in the reviewed files.

### Coverage
- `owlbear_kanban.engine`: 82% in the scoped report.
- Latest Architecture Review on this task scoped the coverage gate to the `pick_tasks` path rather than whole-module legacy breadth. The live suite directly covers filter, sort, wave assembly, dep_status string mapping, config fallback, and view-scope paths.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC22: `pick_tasks()` returns <=3 waves; no intra-wave dep edges; no claimed; no archived; no `dep_status="blocked"`; no `blocked==true` | `test_dep_status_blocked_task_excluded` (`serve/kanban/tests/test_engine_pick_tasks_1074.py:220`), `test_no_intra_wave_dep_edges_across_all_waves` (`:240`), `test_claimed_task_excluded_from_pick_tasks` (`:621`), `test_blocked_flag_true_task_excluded` (`:642`), `test_archived_task_absent_from_dispatchable_pool` (`:662`), `test_missing_dependency_makes_task_dep_blocked` (`:683`), `test_default_max_waves_cap_is_three` (`:702`) | Yes | COVERED |
| AC23: each `DispatchEntry` includes computed `agent` per `BoardConfig.agent_map` | `test_agent_is_full_agent_map_value_not_first_character` (`:445`), `test_different_status_tasks_carry_correct_agent` (`:468`) | Yes | COVERED |
| AC27 refined: wontfix archived dep becomes exact public `dep_status="blocked"` and is excluded from `pick_tasks` | `test_wontfix_archived_dep_excludes_dependent_task` (`:504`) and `test_wontfix_archived_dep_sets_dep_status_blocked_string` (`:765`) | Yes | COVERED |
| AC28 refined: deprecated archived dep becomes exact public `dep_status="redirect"` and remains included | `test_ac27_blocked_excluded_ac28_redirect_included_simultaneously` (`:533`) and `test_deprecated_archived_dep_sets_dep_status_redirect_string` (`:783`) | Yes | COVERED |
| `wave_size < 1` or `max_waves < 1` raises `ERR_INVALID_WAVE_PARAM` | `test_pick_tasks_invalid_max_waves_raises` (`serve/kanban/tests/test_engine_coverage_1068.py:2098`) and `test_pick_tasks_invalid_wave_size_raises` (`:2105`) | Yes | COVERED |
| Refined AC: config `wave_size < 1` with no explicit arg raises `ERR_INVALID_WAVE_PARAM` | `test_config_wave_size_zero_raises_validation_error_without_explicit_arg` (`serve/kanban/tests/test_engine_pick_tasks_1074.py:817`) | Yes | COVERED |
| Default `wave_size` falls back to `BoardConfig.wave_size` | `test_default_wave_size_from_config_and_sort_order_combined` (`:570`) | Yes | COVERED |
| Sort is `priority_rank ASC`, `age DESC`, `id ASC` | `test_sort_priority_rank_age_desc_id_asc_combined` (`:275`) | Yes | COVERED |
| Greedy wave assembly enforces size, dep-disjointness, and agent-compatibility | `test_dep_disjointness_splits_dependent_tasks_into_different_waves` (`:324`), `test_task_dropped_when_dep_conflict_and_max_waves_exhausted` (`:347`), `test_incompatible_agent_buckets_go_to_different_waves` (`:381`) | Yes | COVERED |
| Task not fitting any wave and max_waves reached is dropped | `test_task_dropped_when_dep_conflict_and_max_waves_exhausted` (`:347`) | Yes | COVERED |
| `pick_tasks` is on `AgentView`, not `CockpitView` | `test_agent_view_has_pick_tasks_stub` (`serve/kanban/tests/test_engine_init_1068.py:264`) and `test_cockpit_view_does_not_expose_pick_tasks` (`serve/kanban/tests/test_engine_pick_tasks_1074.py:734`) | Yes | COVERED |

#### Security Review
- No issues. The reviewed path is in-memory selection logic with no shell, SQL, path, template, or deserialization surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| Task-owned `TestFromAC_*` suite in `serve/kanban/tests/test_engine_pick_tasks_1074.py` | Current live file preserves the original methods at `:220`, `:240`, `:275`, `:324`, `:412`, `:445`, `:468`, `:504`, `:533`, and `:570`, then adds proof classes at `:612`, `:731`, `:755`, and `:807` | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Direct ID, agent, dep_status string, wave count, and `ValidationError.code` assertions across the 1074 suite. |
| Negative and error-path coverage | STRONG | Claimed, blocked=true, archived, missing-dependency, explicit invalid params, and config-fallback invalid params are all exercised. |
| Manual mutation reasoning | STRONG | Removing the unclaimed/blocked/archived filters, dep_status mappings, default `max_waves` cap, or effective-wave guard would fail named tests. |
| Test independence | STRONG | All reviewed tests use isolated `tmp_path` boards. |
| Descriptive names | STRONG | Names are behavior-specific and map cleanly to the AC. |

#### Data Safety
- No issues. `AgentView.pick_tasks` is read-only on the reviewed path.

#### Implementation-Aware Gaps
- No significant untested contract paths remain for the refined AC.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The live implementation aligns with the refined contract at `serve/kanban/src/owlbear_kanban/engine.py:1955`, `:2008`, `:2009`, `:2015`, `:2025`, `:2059`, `:2094`, `:2096`, `:2103`, `:2116`, `:2119`, and `:2131`.
- Module-wide engine coverage remains 82%, but the latest Architecture Review on this task explicitly scoped the coverage gate to the `pick_tasks` path inside the legacy engine module.
- Some test commentary still narrates the pre-fix implementation state at `serve/kanban/tests/test_engine_pick_tasks_1074.py:293`, `:362`, and `:420`. Non-blocking.
- Historical RED-state evidence for original commit `8a34ef8b` was not independently inspectable with the current reviewer toolset. I applied the latest Architecture Review refinement, which scoped that line to historical TDD evidence and evaluated the current live snapshot on assertion strength and mutation resistance.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC22 filter and 3-wave cap | `serve/kanban/src/owlbear_kanban/engine.py:2015`, `:2025`, `:2094`, `:2096`; tests at `serve/kanban/tests/test_engine_pick_tasks_1074.py:220`, `:240`, `:621`, `:642`, `:662`, `:683`, `:702` | AC22 proof set | PASS |
| AC23 agent_map value | `serve/kanban/src/owlbear_kanban/engine.py:2059`, `:2060`, `:2063`, `:2131`; tests at `serve/kanban/tests/test_engine_pick_tasks_1074.py:445`, `:468` | agent tests | PASS |
| AC27 exact `blocked` string plus exclusion | `serve/kanban/src/owlbear_kanban/engine.py:1637`, `:1662`, `:1955`, `:2025`; tests at `serve/kanban/tests/test_engine_pick_tasks_1074.py:504`, `:765` | wontfix dep tests | PASS |
| AC28 exact `redirect` string plus inclusion | `serve/kanban/src/owlbear_kanban/engine.py:1639`, `:1664`, `:1955`, `:2025`; tests at `serve/kanban/tests/test_engine_pick_tasks_1074.py:533`, `:783` | deprecated dep tests | PASS |
| Explicit invalid params | `serve/kanban/tests/test_engine_coverage_1068.py:2098`, `:2105` and `serve/kanban/src/owlbear_kanban/engine.py:1993` | invalid-param tests | PASS |
| Config fallback invalid param | `serve/kanban/src/owlbear_kanban/engine.py:2008`, `:2009`; test at `serve/kanban/tests/test_engine_pick_tasks_1074.py:817` | config fallback test | PASS |
| Default wave_size fallback | `serve/kanban/src/owlbear_kanban/engine.py:2008`; test at `serve/kanban/tests/test_engine_pick_tasks_1074.py:570` | default fallback test | PASS |
| Deterministic sort | `serve/kanban/src/owlbear_kanban/engine.py:2046`; test at `serve/kanban/tests/test_engine_pick_tasks_1074.py:275` | sort test | PASS |
| Greedy wave assembly | `serve/kanban/src/owlbear_kanban/engine.py:2094`, `:2096`, `:2103`; tests at `serve/kanban/tests/test_engine_pick_tasks_1074.py:324`, `:347`, `:381` | wave assembly tests | PASS |
| Drop when no wave fits | `serve/kanban/src/owlbear_kanban/engine.py:2116`, `:2119`; test at `serve/kanban/tests/test_engine_pick_tasks_1074.py:347` | overflow test | PASS |
| `AgentView` only, not `CockpitView` | `serve/kanban/src/owlbear_kanban/engine.py:2604`; tests at `serve/kanban/tests/test_engine_init_1068.py:264` and `serve/kanban/tests/test_engine_pick_tasks_1074.py:734` | scope tests | PASS |

### Confidence: 0.92
### Verdict: PASS

- Reflection:
  - The latest Architecture Review changed the gate materially; older review failures were stale once retry-2 landed.
  - Module-wide coverage stayed low, but the task-path proof is now direct and mutation-resistant.
  - The only unresolved point was historical RED-state reconstruction, which was not possible with the available reviewer tools and was treated per the task's own architecture note.
[[2026-04-25]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` had no mention of `AgentView.pick_tasks`; added "AgentView dispatch pipeline" subsection describing the four-step pipeline and `PickTasksResponse` shape. |
| 2 | Module docstrings | Yes | Updated | `AgentView.pick_tasks` at `engine.py:1993` had no docstring despite being a public method. Added full docstring with Args/Returns/Raises consistent with sibling methods `list_tasks` and `show_task`. |
| 3 | External attribution | No | N/A | No external patterns cited in task body or AC. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (also describes `serve/kanban/src/**`) — both footers updated to `Last verified: 2026-04-25 (581dd938)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN | Docstring added to `AgentView.pick_tasks` |
| `serve/kanban/README.md` | IN | Added AgentView dispatch pipeline subsection |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated |
| `serve/kanban/tests/test_engine_pick_tasks_1074.py` | OUT | Test file — no action |
| `serve/kanban/tests/test_engine_coverage_1068.py` | OUT | Test file — no action |
| `serve/kanban/tests/test_engine_init_1068.py` | OUT | Test file — no action |

### Files Updated

- `serve/kanban/src/owlbear_kanban/engine.py` — docstring added
- `serve/kanban/README.md` — AgentView dispatch pipeline section added
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated

### Child Tasks Created

- None

### Scratch Files Cleaned

- None found (`1074-*` search returned no results)

Commit: `11b54eec`
[[2026-04-25]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC22: ≤3 waves, no intra-wave deps, no claimed/archived/blocked/dep_status blocked | 7 tests: filter proofs at :621, :642, :662, :683; cap at :702; dep-edge at :240; dep_status at :220 | PASS |
| AC23: DispatchEntry.agent from agent_map | :445 and :468 assert full string value | PASS |
| AC27 (refined): wontfix → dep_status="blocked" string + excluded | :504 behavioral exclusion + :765 exact string assertion via show_task | PASS |
| AC28 (refined): deprecated → dep_status="redirect" string + included | :533 behavioral inclusion + :783 exact string assertion via show_task | PASS |
| Invalid params → ValidationError | test_engine_coverage_1068.py:2098 and :2105 | PASS |
| Config fallback: wave_size=0 → ValidationError | :817 config fallback test | PASS |
| Default wave_size from BoardConfig | :570 combined test | PASS |
| Sort: priority_rank ASC, age DESC, id ASC | :275 deterministic sort test | PASS |
| Greedy wave assembly (size, dep-disjointness, agent-compat) | :324, :347, :381 | PASS |
| Drop when max_waves exhausted | :347 overflow test | PASS |
| pick_tasks on AgentView, not CockpitView | test_engine_init_1068.py:264 + :734 negative CockpitView proof | PASS |

All line refs are serve/kanban/tests/test_engine_pick_tasks_1074.py unless noted otherwise.

### Test Results
- pytest (full suite): 2082 passed, 165 failed, 209 errors, 4 skipped
- Task-scope failures: 0 — all 22 task-owned tests pass
- Cross-task failures: all 165+209 from unrelated `agent_name` parameter removal (126+) and `agent_map` config validation (18+) in cockpit/guidance/corruption suites — none in kanban pick_tasks path
- ruff: 8 violations, all outside serve/kanban/ (knowledge, mcp-knowledge, mcp-memory, orchestrator packages)

### Architect Quality: 4/5
Original AC was adequate but underspecified AC27/AC28 string contracts and missed config fallback edge case. Architect caught this via challenger (confidence 0.46 → reconsider), accepted 2/3 challenges, refined AC to require exact dep_status string assertions and added config fallback AC. Refinements were material and directly caused the evidence gaps in review cycles 1-2. Minor: AC22 was overloaded (6+ filter criteria in one line).

### Deduction Breakdown
- AC lines without evidence: 0 (all 11 refined AC lines have test evidence) → 0
- Lint violations in task scope: 0 → 0
- AC quality: 4/5 (above ≤3 threshold) → 0
- Reviewer evidence section: present, detailed, 3-cycle PASS → 0
- Full-suite test failures in task scope: 0 → 0
- RED-phase historical AC: architect scoped to original commit 8a34ef8b; not evaluable against current green snapshot but correctly handled per architect guidance → -.02 (unverifiable claim)

### Confidence: .98
### Action: archive