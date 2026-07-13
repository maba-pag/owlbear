---
id: 1113
title: 'Coverage: add edit_task mutation + property tests to test_engine_coverage_1110.py'
status: archived
priority: medium
created: 2026-04-24T07:54:18.700747+00:00
updated: 2026-04-24T14:28:44.565817+00:00
tags:
- test
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-24]]
## Research
- Research doc: .owlbear/research/engine-coverage-edit-show-property-1113.md
- Sources: 7 studied, 4 high-relevance (all codebase + coverage measurement)
- Recommendation: Add 3 test classes — show_task paths (5–6 tests), edit_task field mutations (parametrized, ~12 branches), properties (3 tests). Estimated ~30 missing-line uplift. (confidence: 0.90)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none (T1 — pure test coverage)

## Challenge Results
- Challenger: SKIP — T1 coverage task, no design recommendation to challenge
- Confidence in original: 0.90

## Acceptance Criteria
### TestFromAC_EngineEditTaskFieldMutations
- title, body, priority, status, parent mutations (each verified on returned Task)
- add_tags with dedup (adding existing tag is idempotent)
- remove_tags
- add_deps with dedup (adding existing dep is idempotent)
- remove_deps
- Invalid status → ValueError
- Invalid priority → ValueError
- append_body without timestamp (no date prefix)

### TestFromAC_EngineProperties
- agent_name is non-empty str, stable across calls
- board_config() returns deep copy (mutating returned config doesn't affect engine state)
[[2026-04-24]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure test coverage task, one concern |
| Interface clarity | FAIL | AC includes 6 show_task tests and 1 revision test already covered in test_idtofilename_cache_943/944 and test_mtime_cache_942 — inflated scope |
| Dependency correctness | PASS | No deps; parent task #1110 completed (file exists with 17 classes) |
| Module layering | PASS | Tests only, no production code changes |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | FAIL | TestFromAC_EngineShowTaskPaths duplicates 12+ tests across 943/944 suites — consolidation, not coverage |
| Premise challenge | FAIL | Research baseline (64%) is stale; existing suites cover most proposed paths |
| Pattern consistency | PASS | Follows existing _make_board/_write_task helpers |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: **block** (confidence: 0.22)
- Architect response: **accepted** — verified all 4 challenger findings independently

### Evidence of Duplication

**show_task (all 6 AC paths already covered):**
- Cache hit: test_idtofilename_cache_943.py L228–L252 (3 tests: no glob, no read_task, returns correct task)
- Stale mtime: test_idtofilename_cache_943.py L257–L295 (2 tests: triggers reread, updates cache entry)
- File deleted/eviction: test_idtofilename_cache_943.py L298–L340 (2 tests: evicts task_cache, evicts id_to_filename)
- Cold glob fallback: test_idtofilename_cache_943.py L342–L348 + test_idtofilename_cache_944.py L319–L326
- Non-numeric ID: test_idtofilename_cache_943.py L352–L368 + test_idtofilename_cache_944.py L334–L347
- Not found: test_idtofilename_cache_944.py L327–L332

**revision (2 of 3 AC assertions already covered):**
- test_mtime_cache_942.py L316–L326: increments after create_task
- test_mtime_cache_942.py L328–L333: increments after edit_task

### Genuinely Uncovered Items (keep these)

**edit_task field mutations:** body=, priority=, status=, parent= (title= IS tested in rollback/cache tests but harmless to include), add_tags dedup, remove_tags, add_deps dedup, remove_deps, invalid status/priority on EDIT specifically (create validation differs at L878 — dict-status path), append_body without timestamp

**Properties:** agent_name (no direct property assertion anywhere), board_config deep copy (test_engine_storage L1032 only tests config loading, not defensive copy)

### Required AC Refinement

1. **DROP** entire TestFromAC_EngineShowTaskPaths class — all 6 paths fully covered in 943/944 suites
2. **NARROW** TestFromAC_EngineProperties: drop revision (covered in 942), keep agent_name + board_config
3. **KEEP** TestFromAC_EngineEditTaskFieldMutations as-is — genuine coverage gaps

### Verdict: REFINE
### Action Taken: Returned to backlog with required AC changes. Task needs AC rewrite before approval.
[[2026-04-24]]
## Architecture Review (retry)

### Refinement Applied
1. **DROPPED** TestFromAC_EngineShowTaskPaths — all 6 paths duplicated in test_idtofilename_cache_943/944 suites
2. **NARROWED** TestFromAC_EngineProperties — dropped revision (covered in test_mtime_cache_942 L316–L333), kept agent_name + board_config deep-copy
3. **KEPT** TestFromAC_EngineEditTaskFieldMutations — genuine uncovered branches (8 AC lines, ~12 engine branches)
4. **Added** `test` tag for pipeline pass-through
5. **Updated** title to reflect reduced scope

### Evaluation (post-refinement)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure test coverage, one concern |
| Interface clarity | PASS | Each AC line maps to a single assertion or parametrized case |
| Dependency correctness | PASS | No deps; file test_engine_coverage_1110.py exists |
| Module layering | PASS | Tests only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Duplicate paths removed; only genuinely uncovered branches remain |
| Premise challenge | PASS | edit_task field mutations have no direct coverage in any existing suite; agent_name/board_config untested |
| Pattern consistency | PASS | Follows _make_board/_write_task helpers from test_engine_coverage_1110.py |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: SKIP — refinement pass, all concerns from previous block (0.22) addressed by scope reduction
- Confidence post-refinement: 0.93

### Verdict: APPROVE
### Action Taken: AC rewritten per prior review findings. show_task class dropped (6 duplicate paths), revision assertion dropped (covered in 942). 2 classes remain with 10 genuinely uncovered AC lines. Tagged `test` for pass-through. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Test file: tests/test_engine_coverage_1113.py
- Classes: TestFromAC_EngineEditTaskFieldMutations, TestFromAC_EngineProperties
- Tests per category: happy 10, edge 3, error 2, boundary 2
- Total: 17 tests, all PASS (coverage task — tests existing engine behavior)
- ruff: clean
- Commit: d51482d4

### AC coverage table
| AC line | Test(s) |
|---------|---------|
| title mutation | test_title_mutation_reflected_on_returned_task |
| body mutation | test_body_mutation_reflected_on_returned_task |
| priority mutation | test_priority_mutation_reflected_on_returned_task |
| status mutation | test_status_mutation_reflected_on_returned_task |
| parent mutation | test_parent_mutation_reflected_on_returned_task |
| add_tags with dedup | test_add_tags_merges_with_existing, test_add_tags_dedup_is_idempotent |
| remove_tags | test_remove_tags_drops_specified_tag |
| add_deps with dedup | test_add_deps_merges_with_existing, test_add_deps_dedup_is_idempotent |
| remove_deps | test_remove_deps_drops_specified_dep |
| Invalid status → ValueError | test_invalid_status_raises_value_error |
| Invalid priority → ValueError | test_invalid_priority_raises_value_error |
| append_body without timestamp | test_append_body_without_timestamp_has_no_date_prefix |
| agent_name non-empty + stable | test_agent_name_is_non_empty_string, test_agent_name_is_stable_across_calls |
| board_config() deep copy | test_board_config_returns_deep_copy |

### Note on agent_map config fixture
The engine's _validate_engine_config (added by #1067 builder, currently uncommitted) requires all statuses present as agent_map keys. Updated _CONFIG_YAML in test fixture to include all 7 statuses with empty lists as values. This also unblocks test_engine_coverage_1110.py which uses agent_map: {} — that file needs the same fix.
[[2026-04-24]]
## Builder Notes
- Non-implementation task (tagged `test`) — no source code changes needed in GREEN phase.
- Files changed: none.
- Tests: not applicable for builder on pass-through task; test-writer already delivered 17 AC tests in `tests/test_engine_coverage_1113.py`.
- Coverage: not applicable (no implementation changes).
- ruff: not applicable (no file changes).
- Evidence summary: `test` is in NON_IMPL_TAGS and builder is expected to pass through these tasks to review.
[[2026-04-24]]
## Review Evidence
### Test Results
- Quality-Runner scoped on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): 17 passed, 0 failed, 0 skipped.
- Broader engine-focused context run across 7 related suites was not usable as gate evidence for this task: 28 passed, 144 failed, 16 errors, dominated by current suite debt outside the task-owned file. One verified example is [serve/kanban/tests/test_engine_coverage_1110.py](serve/kanban/tests/test_engine_coverage_1110.py#L55) still using `agent_map: {}` while [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L123) now requires every configured status to exist in `agent_map`.

### Lint
- Quality-Runner scoped lint on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): clean.

### Coverage
- Task-owned scoped run: `owlbear_kanban.engine` 24%.
- This is contextual only for this reject. The task-specific gate failure is weak AC proof in 3 tests, not unrelated broader-suite debt.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| title, body, priority, status, parent mutations (each verified on returned Task) | Tests in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L229) | Yes — each mutation is asserted directly on the returned Task. | COVERED |
| add_tags with dedup (adding existing tag is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L169) | Yes — merge and idempotence are both asserted. | COVERED |
| remove_tags | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177) | Yes — removed tag disappears and untouched tag remains. | COVERED |
| add_deps with dedup (adding existing dep is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L192) | Yes — merge and idempotence are both asserted. | COVERED |
| remove_deps | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200) | Yes — removed dep disappears and untouched dep remains. | COVERED |
| Invalid status → ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) | Yes — `ValueError` with `Invalid status` is required. | COVERED |
| Invalid priority → ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215) | Yes — `ValueError` with `Invalid priority` is required. | COVERED |
| append_body without timestamp (no date prefix) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L229) | No — the test only checks substring presence and absence of `[[`. It would still pass if append semantics regressed to overwrite semantics, even though the implementation appends existing body + newline + new text at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L977-L982). | LAX |
| agent_name is non-empty str, stable across calls | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L241-L252) | No — non-empty string is covered, but stability is only a two-read equality check. The value is randomised once at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L413) and returned at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L476-L478), so a recompute-per-call regression can false-green on a collision. | LAX |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L254-L264) | No — the test mutates only `statuses`, while the deep-copy contract at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L500-L506) also covers nested mutable fields such as `agent_map`, `agent_types`, and `agent_compatibility` in [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L77-L79). A partial deep-copy bug would still pass. | LAX |

#### Security Review
- No issues found. The task-owned change is a local pytest file only; no secrets, subprocesses, network calls, deserialisation, or user-controlled path handling were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L229) | Current `TestFromAC_EngineEditTaskFieldMutations` snapshot still contains direct equality, membership, count, and raises assertions for the AC lines. | PRESERVED |
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L238-L264) | Current `TestFromAC_EngineProperties` snapshot still contains the intended agent_name and board_config assertions. The problem is proof strength, not weakening or removal. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most edit_task tests use direct equality or membership assertions, but append-body uses loose substring checks at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L229). |
| Negative/error-path coverage | ADEQUATE | Invalid status and invalid priority are explicitly covered at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208-L220). |
| Manual mutation reasoning | WEAK | Three regressions can false-green: overwrite-vs-append at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L229) versus [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L977-L982); recompute-per-call `agent_name` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L248-L252) versus [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L413) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L476-L478); partial deep-copy bugs on nested config fields at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L254-L264) versus [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L500-L506) and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L77-L79). |
| Test independence | STRONG | Each test creates a fresh tmp_path board and engine via the local helpers in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L70-L106). |
| Descriptive test names | STRONG | Test names clearly encode the contract under test throughout [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L264). |

#### Data Safety
- No issues found. The task-owned file writes bounded fixture content under tmp_path and exercises in-process engine methods only.

#### Implementation-Aware Gaps
- `append_body` AC is not actually proven: [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L229) does not assert the original body is preserved or the exact append shape required by [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L977-L982).
- `agent_name` stability is not proven deterministically: [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L248-L252) samples only two reads of a randomised value set at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L413).
- `board_config()` deep copy is only partially exercised: [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L254-L264) mutates a top-level list only, not the nested mutable config fields exposed by [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L77-L79).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The task-owned file mirrors the latest refined AC closely, which is the correct authority source for this review.
- The broader engine-focused coverage context is currently noisy because older engine suites have not been updated to the current config/signature contracts. That context was not used as the primary fail reason here.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| title, body, priority, status, parent mutations (each verified on returned Task) | Direct returned-Task assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L229) | Mutation tests in `TestFromAC_EngineEditTaskFieldMutations` | PASS |
| add_tags with dedup (adding existing tag is idempotent) | Merge and count assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L169) | `test_add_tags_merges_with_existing`, `test_add_tags_dedup_is_idempotent` | PASS |
| remove_tags | Removal and preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177) | `test_remove_tags_drops_specified_tag` | PASS |
| add_deps with dedup (adding existing dep is idempotent) | Merge and count assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L192) | `test_add_deps_merges_with_existing`, `test_add_deps_dedup_is_idempotent` | PASS |
| remove_deps | Removal and preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200) | `test_remove_deps_drops_specified_dep` | PASS |
| Invalid status → ValueError | `pytest.raises(ValueError, match="Invalid status")` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) | `test_invalid_status_raises_value_error` | PASS |
| Invalid priority → ValueError | `pytest.raises(ValueError, match="Invalid priority")` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215) | `test_invalid_priority_raises_value_error` | PASS |
| append_body without timestamp (no date prefix) | Missing exact append-semantics proof versus [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L977-L982) | `test_append_body_without_timestamp_has_no_date_prefix` | FAIL |
| agent_name is non-empty str, stable across calls | Non-empty proven, stability proof is collision-prone because it is only a two-read equality check against a randomised value | `test_agent_name_is_non_empty_string`, `test_agent_name_is_stable_across_calls` | FAIL |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | Only top-level `statuses` mutation is exercised; nested mutable config structures are not | `test_board_config_returns_deep_copy` | FAIL |

### Confidence: 0.64
### Verdict: FAIL
### Action
- Reject to `todo`. The implementation under test is existing engine code; the missing work is stronger deterministic proof in the task-owned tests, not a production-code fix.
- Strengthen 3 AC tests: prove exact append semantics for `append_body`, prove `agent_name` stability without collision-based false greens, and mutate nested config structures to prove `board_config()` is a real deep copy.

### Post-task Reflection
- The scoped task-owned run was necessary to separate task evidence from background engine-suite debt.
- Deep-copy contracts need nested-mutable mutation, not just top-level list mutation.
- Random/stable property contracts need deterministic proof, not equality checks that can pass by chance.
[[2026-04-24]]
## Test-Writer Notes (retry)
- Test file: tests/test_engine_coverage_1113.py
- Retry: strengthened 3 LAX AC proofs identified by reviewer
- Existing 17 tests: all still PASS (unchanged)
- New tests added: 3

### New tests (stronger proof)
| New Test | AC Line | Weakness Fixed |
|----------|---------|----------------|
| `test_append_body_preserves_original_body` | append_body without timestamp | Proves original body is preserved and appended text comes after it (pure overwrite would fail); original test only checked substring presence |
| `test_agent_name_is_stable_across_many_calls` | agent_name stable across calls | 20-call check eliminates collision-based false-green; original 2-read check would pass by chance if implementation recomputed |
| `test_board_config_deep_copy_covers_nested_agent_map` | board_config() deep copy | Mutates `agent_map` nested dict; original test only mutated top-level `statuses` list, which passes even for a shallow copy |

### Run result
- 20 tests total, 20 passed, 0 failed, ruff clean
- Note: Coverage tasks test existing correct engine behaviour — stronger tests are regression guards, not RED-phase failing tests. All 20 pass as expected on correct implementation.
[[2026-04-24]]
## Test-Writer Notes (retry)
- Retry: reviewer rejected 3 AC lines as LAX — added deterministic companion tests, existing 17 tests untouched.
- Test file: tests/test_engine_coverage_1113.py
- Classes: TestFromAC_EngineEditTaskFieldMutations, TestFromAC_EngineProperties
- New tests added (5 total additions across two sessions):
  - `test_append_body_preserves_original_body_in_order`: asserts original body starts the result AND appended text follows it (proves append, not overwrite semantics)
  - `test_agent_name_is_stable_across_many_calls`: 10-read sample — P(collision false-green) < 1e-36 with ~10 000 name combinations
  - `test_board_config_deep_copy_covers_nested_dicts`: mutates `agent_map["INJECTED"]` and `agent_types["INJECTED"]` on the copy, asserts engine state unchanged
- Total: 22 tests, all PASS (coverage task — proves existing engine behavior)
- ruff: clean
- Commit: cee3d294

### AC coverage table (3 previously-LAX lines)
| AC line | Old verdict | New test(s) | Stronger proof |
|---------|-------------|-------------|----------------|
| append_body without timestamp | LAX | test_append_body_preserves_original_body_in_order | Original body at index < appended text index |
| agent_name stable across calls | LAX | test_agent_name_is_stable_across_many_calls | 10 reads, all equal first (P(false-green) < 1e-36) |
| board_config() deep copy | LAX | test_board_config_deep_copy_covers_nested_dicts | Mutates agent_map + agent_types nested dicts |
[[2026-04-24]]
## Review Evidence
### Test Results
- Scoped Quality-Runner on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): 22 passed, 0 failed, 0 skipped.
- Broader engine-context Quality-Runner across 7 related suites: 25 passed, 106 failed, 62 errors. This was not used as gate evidence for this reject because it is dominated by unrelated suite debt outside the task-owned file. Sample failures: `KanbanEngine(..., agent_name=...)` TypeError in older cache suites, and `agent_map missing status entries` ConfigError in older fixtures.

### Lint
- Scoped lint on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): clean.

### Coverage
- Scoped task-owned run: `owlbear_kanban.engine` 24% (`overall_pct` 29).
- Broader engine-context run: `owlbear_kanban.engine` 25% (`overall_pct` 30).
- Coverage is contextual only here. This task is a narrow test-only uplift inside a large engine module; the reject is driven by a remaining task-owned proof gap, not by module-wide percentage.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| title, body, priority, status, parent mutations (each verified on returned Task) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L160) | Yes — each mutation is asserted directly on the returned Task. | COVERED |
| add_tags with dedup (adding existing tag is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L169) | Yes — merge and dedup both fail if the `if t not in record.tags` guard regresses in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L956-L959). | COVERED |
| remove_tags | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177) | Yes — the removed tag disappears and the untouched tag remains. | COVERED |
| add_deps with dedup (adding existing dep is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L192) | Yes — merge and dedup both fail if the `if d not in record.depends_on` guard regresses in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L963-L966). | COVERED |
| remove_deps | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200) | Yes — the removed dep disappears and the untouched dep remains. | COVERED |
| Invalid status -> ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) | Yes — direct `pytest.raises(ValueError, match="Invalid status")` on `edit_task()`. | COVERED |
| Invalid priority -> ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215) | Yes — direct `pytest.raises(ValueError, match="Invalid priority")` on `edit_task()`. | COVERED |
| append_body without timestamp (no date prefix) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L257) | Yes — retry adds append-order and preserve-body guards that would fail if [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L977-L982) overwrote instead of appended. | COVERED |
| agent_name is non-empty str, stable across calls | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L265-L290) | Yes — retry adds repeated-call sampling against recompute-per-call regressions for the property implemented at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L476-L478). | COVERED |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L293-L337) | No — the retry only mutates top-level containers by appending to `statuses` and adding new keys to `agent_map` / `agent_types`. The fixture already contains pre-existing nested mutable values at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L38-L49), but the tests never mutate one of those existing nested values. A partial-copy regression that aliases `agent_map["research"]` would still pass despite the deep-copy contract in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L500-L506). | LAX |

#### Security Review
- No issues found. The task-owned change is a local pytest file only; no secrets, subprocesses, network calls, template rendering, or unsafe deserialization surface is introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L257) | `TestFromAC_EngineEditTaskFieldMutations` retained the original direct equality/membership/raises assertions and added stronger append-body guards. | STRENGTHENED |
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L265-L337) | `TestFromAC_EngineProperties` retained the original non-empty/stability/deep-copy checks and added repeated-call plus container-copy probes. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Field mutation and validation tests use direct equality, membership, count, and constrained-exception assertions throughout [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L257). |
| Negative/error-path coverage | ADEQUATE | Invalid status and invalid priority are covered directly on `edit_task()` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208-L220). |
| Manual mutation reasoning | WEAK | A buggy `board_config()` that shallow-copies the `agent_map` dict but aliases existing nested list values would still pass current tests, because [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L305-L337) adds new keys instead of mutating an existing nested mutable value from [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L38-L49). |
| Test independence | STRONG | Each test creates a fresh tmp-path board and engine. |
| Descriptive test names | STRONG | Test names map cleanly to the AC lines and guarded regressions. |

#### Data Safety
- No issues found. The task-owned tests operate on isolated temp directories only.

#### Implementation-Aware Gaps
- Remaining significant gap: the deep-copy contract on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L500-L506) is not fully proven. The current retry never mutates a pre-existing nested mutable value such as one of the existing `agent_map` lists from [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L38-L49), so shared nested-value aliasing can false-green.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L306-L309) overstates the proof: the test body does not show that all mutable nesting levels are isolated.
- [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L326-L337) says it mutates a nested dict, but it actually inserts a new top-level key into `agent_map`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| title, body, priority, status, parent mutations (each verified on returned Task) | Direct returned-Task assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124-L160) | Mutation tests in `TestFromAC_EngineEditTaskFieldMutations` | PASS |
| add_tags with dedup (adding existing tag is idempotent) | Merge and count assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162-L175) | `test_add_tags_merges_with_existing`, `test_add_tags_dedup_is_idempotent` | PASS |
| remove_tags | Removal and preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177-L183) | `test_remove_tags_drops_specified_tag` | PASS |
| add_deps with dedup (adding existing dep is idempotent) | Merge and count assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185-L198) | `test_add_deps_merges_with_existing`, `test_add_deps_dedup_is_idempotent` | PASS |
| remove_deps | Removal and preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200-L206) | `test_remove_deps_drops_specified_dep` | PASS |
| Invalid status -> ValueError | Direct `pytest.raises` on `edit_task()` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208-L213) | `test_invalid_status_raises_value_error` | PASS |
| Invalid priority -> ValueError | Direct `pytest.raises` on `edit_task()` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215-L220) | `test_invalid_priority_raises_value_error` | PASS |
| append_body without timestamp (no date prefix) | No-prefix plus append-order/preserve-body guards at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222-L257) | `test_append_body_without_timestamp_has_no_date_prefix`, `test_append_body_preserves_original_body_in_order`, `test_append_body_preserves_original_body` | PASS |
| agent_name is non-empty str, stable across calls | Non-empty and repeated-call equality checks at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L265-L290) | `test_agent_name_is_non_empty_string`, `test_agent_name_is_stable_across_calls`, `test_agent_name_is_stable_across_many_calls` | PASS |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | Only top-level list/dict-container mutation is exercised in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L293-L337); pre-existing nested mutable values are not mutated. | `test_board_config_returns_deep_copy`, `test_board_config_deep_copy_covers_nested_dicts`, `test_board_config_deep_copy_covers_nested_agent_map` | FAIL |

### Confidence: 0.78
### Verdict: FAIL
### Action
- Reject to `todo`. The implementation under test is existing engine code; the remaining work is a task-owned test gap, not a production-code fix.
- Strengthen the `board_config()` proof by mutating at least one pre-existing nested mutable value from the returned config, not just inserting a new key. The obvious target is an existing list under `agent_map` from [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L38-L49).
- This is the second review failure on the task, not the third-plus loop-breaker case.

### Post-task Reflection
- Scoped quality evidence was necessary to isolate the task-owned test file from unrelated engine-suite debt.
- Deep-copy ACs require mutation of an existing nested mutable value; adding a new dict key only proves container separation.
- The broader engine-context run remains noisy because older suites still assume an `agent_name` constructor argument or outdated config fixtures.
[[2026-04-24]]
## Builder Notes
- REJECT (test ownership): remaining failure is in `TestFromAC_EngineProperties` proof strength, not implementation.
- Files changed: none.
- Tests run: none (builder mode boundary for this task).
- Lint: n/a.
- Coverage: n/a.
- Evidence summary: latest review marks only one AC line FAIL — `board_config()` deep-copy proof remains lax because tests mutate top-level containers/new keys but do not mutate an existing nested mutable value from returned config.
- Test-writer action required: in `tests/test_engine_coverage_1113.py`, mutate an existing nested value (for example, append into `board_config().agent_map["research"]` from the returned copy) and assert a fresh `engine.board_config()` call still has original nested list content unchanged.
[[2026-04-24]]
## Test-Writer Notes (retry 3)
- Test file: tests/test_engine_coverage_1113.py
- Retry: added 1 deterministic proof for the remaining LAX AC line — `board_config()` deep copy on pre-existing nested mutable values
- Existing 22 tests: all still PASS (unchanged)
- New test added: 1

### New test
| New Test | AC Line | Weakness Fixed |
|----------|---------|----------------|
| `test_board_config_deep_copy_existing_nested_list_is_isolated` | board_config() returns deep copy | Appends to `config_copy.agent_map["research"]` (a **pre-existing** nested list from the fixture, not a newly-inserted key) and asserts a fresh `engine.board_config().agent_map["research"]` is still `[]`. A shallow copy would alias the same list object and fail. |

### Run result
- 23 tests total, 23 passed, 0 failed — ruff clean
- Coverage task: tests prove existing engine behaviour; all pass on correct implementation as expected
[[2026-04-24]]
## Test-Writer Notes (retry 3 — re-verification)
- Test file: tests/test_engine_coverage_1113.py
- Classes: TestFromAC_EngineEditTaskFieldMutations (16 tests), TestFromAC_EngineProperties (7 tests)
- Total: 23 tests, 23 passed, 0 failed — ruff clean
- Coverage task: tests prove existing engine behaviour; PASS is the correct outcome for correct implementation.

### AC coverage table
| AC line | Test(s) | Verdict |
|---------|---------|---------|
| title, body, priority, status, parent mutations | test_*_mutation_reflected_on_returned_task (×5) | PASS |
| add_tags with dedup | test_add_tags_merges_with_existing, test_add_tags_dedup_is_idempotent | PASS |
| remove_tags | test_remove_tags_drops_specified_tag | PASS |
| add_deps with dedup | test_add_deps_merges_with_existing, test_add_deps_dedup_is_idempotent | PASS |
| remove_deps | test_remove_deps_drops_specified_dep | PASS |
| Invalid status → ValueError | test_invalid_status_raises_value_error | PASS |
| Invalid priority → ValueError | test_invalid_priority_raises_value_error | PASS |
| append_body without timestamp | test_append_body_without_timestamp_has_no_date_prefix, test_append_body_preserves_original_body_in_order, test_append_body_preserves_original_body | PASS |
| agent_name non-empty + stable | test_agent_name_is_non_empty_string, test_agent_name_is_stable_across_calls, test_agent_name_is_stable_across_many_calls (10 reads) | PASS |
| board_config() deep copy | test_board_config_returns_deep_copy, test_board_config_deep_copy_covers_nested_dicts, test_board_config_deep_copy_covers_nested_agent_map, test_board_config_deep_copy_existing_nested_list_is_isolated | PASS |

### Outstanding reviewer concern addressed
The last review (22 tests) FAIL'd board_config() deep copy for only inserting new keys, not mutating pre-existing nested values. `test_board_config_deep_copy_existing_nested_list_is_isolated` (added in retry 3) fixes this: it appends to `config_copy.agent_map["research"]` — a **pre-existing** nested list from the fixture — and asserts `engine.board_config().agent_map["research"]` is unchanged. A shallow copy would alias the same list and fail.
[[2026-04-24]]
## Review Evidence
### Test Results
- Quality-Runner scoped on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): 23 passed, 0 failed, 0 skipped.

### Lint
- Scoped lint on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): clean.

### Coverage
- Scoped coverage context: `owlbear_kanban.engine` 24% (`overall_pct` 29).
- Recorded as context only. This reject is driven by task-owned proof gaps, not module-wide legacy debt.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| title, body, priority, status, parent mutations (each verified on returned Task) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L127), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L134), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L141), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L148), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L155) | Yes — each mutation is asserted directly on the returned Task. | COVERED |
| add_tags with dedup (adding existing tag is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L169) | No — the new-tag path uses set equality at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L167), which hides multiplicity. A regression on the dedup guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L958) would still pass if it duplicated the newly added tag. The count assertion at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L175) only proves the already-present-tag path. | FAIL |
| remove_tags | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177) | Yes — removed tag disappears and untouched tag remains. | COVERED |
| add_deps with dedup (adding existing dep is idempotent) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L192) | No — the new-dep path uses set equality at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L190), which hides multiplicity. A regression on the dedup guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L965) would still pass if it duplicated the newly added dependency. The count assertion at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L198) only proves the already-present-dependency path. | FAIL |
| remove_deps | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200) | Yes — removed dependency disappears and untouched dependency remains. | COVERED |
| Invalid status -> ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) | Yes — direct `pytest.raises(ValueError, match="Invalid status")` on `edit_task()`. | COVERED |
| Invalid priority -> ValueError | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215) | Yes — direct `pytest.raises(ValueError, match="Invalid priority")` on `edit_task()`. | COVERED |
| append_body without timestamp (no date prefix) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L232), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L246) | Yes for the current engine contract — no `[[...]]` timestamp marker plus preserve-body/order checks would fail if [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L982) stopped appending or started emitting the current timestamp prefix. | COVERED |
| agent_name is non-empty str, stable across calls | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L268), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L275), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L281) | Yes — non-empty string and repeated-call stability are both asserted against the property backed by the instance field set at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L413) and returned at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L476). | COVERED |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L293), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L305), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L326), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L339) | Yes — the retry-3 nested-list mutation closes the prior false-green on pre-existing mutable values from the fixture at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L42) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L43), matching the deep-copy contract at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L500). | COVERED |

#### Security Review
- No issues found. The task-owned change is a local pytest file only; no secrets, subprocesses, network calls, templating, or unsafe deserialization surface is introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124) | `TestFromAC_EngineEditTaskFieldMutations` retained the original direct equality/membership/raises assertions and added stronger append-body guards. | STRENGTHENED |
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L265) | `TestFromAC_EngineProperties` retained the original property checks and added the pre-existing nested-list isolation proof. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are direct and concrete, but the new-item dedup proofs use set equality at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L167) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L190), which discards multiplicity. |
| Negative/error-path coverage | ADEQUATE | Invalid status and invalid priority are covered directly at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215). |
| Manual mutation reasoning | WEAK | Two AC lines still false-green if the new-item dedup guard regresses: add_tags at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L958) and add_deps at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L965). |
| Test independence | STRONG | Each test creates a fresh tmp-path board and engine instance. |
| Descriptive test names | STRONG | Test names map cleanly to the AC lines. |

#### Data Safety
- No issues found. The task-owned tests operate on isolated tmp directories only.

#### Implementation-Aware Gaps
- `add_tags` dedup is not fully proven on the newly-added-tag path. Strengthen [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L162) to assert multiplicity, not just set membership.
- `add_deps` dedup is not fully proven on the newly-added-dependency path. Strengthen [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L185) to assert multiplicity, not just set membership.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Code-reader also flagged `append_body` as somewhat implementation-shaped. I did not use that as the gating failure because the combined no-prefix and preserve-body/order assertions are materially stronger than the previously rejected snapshot and are sufficient for the current engine contract.
- The task body already contains two prior `## Review Evidence` sections. This reject is the third review failure, so routing follows the loop-breaker rule to `backlog`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| title, body, priority, status, parent mutations (each verified on returned Task) | Direct returned-Task assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L127), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L134), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L141), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L148), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L155) | Mutation tests in `TestFromAC_EngineEditTaskFieldMutations` | PASS |
| add_tags with dedup (adding existing tag is idempotent) | Existing-tag idempotence is covered at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L175), but the new-tag path still hides duplication via set equality at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L167) | `test_add_tags_merges_with_existing`, `test_add_tags_dedup_is_idempotent` | FAIL |
| remove_tags | Removal/preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L177) | `test_remove_tags_drops_specified_tag` | PASS |
| add_deps with dedup (adding existing dep is idempotent) | Existing-dep idempotence is covered at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L198), but the new-dep path still hides duplication via set equality at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L190) | `test_add_deps_merges_with_existing`, `test_add_deps_dedup_is_idempotent` | FAIL |
| remove_deps | Removal/preservation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200) | `test_remove_deps_drops_specified_dep` | PASS |
| Invalid status -> ValueError | Direct `pytest.raises` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L208) | `test_invalid_status_raises_value_error` | PASS |
| Invalid priority -> ValueError | Direct `pytest.raises` at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L215) | `test_invalid_priority_raises_value_error` | PASS |
| append_body without timestamp (no date prefix) | No-prefix plus append-order/preserve-body assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L222), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L232), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L246) | `test_append_body_without_timestamp_has_no_date_prefix`, `test_append_body_preserves_original_body_in_order`, `test_append_body_preserves_original_body` | PASS |
| agent_name is non-empty str, stable across calls | Non-empty and repeated-call stability assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L268), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L275), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L281) | `test_agent_name_is_non_empty_string`, `test_agent_name_is_stable_across_calls`, `test_agent_name_is_stable_across_many_calls` | PASS |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | Top-level and nested isolation assertions at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L293), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L305), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L326), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L339) | `test_board_config_returns_deep_copy`, `test_board_config_deep_copy_covers_nested_dicts`, `test_board_config_deep_copy_covers_nested_agent_map`, `test_board_config_deep_copy_existing_nested_list_is_isolated` | PASS |

### Confidence: 0.79
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the third review failure on the task, so the loop-breaker rule applies.
- Tighten the two dedup AC proofs by asserting multiplicity on the newly-added item path, not just set membership. For example, the merge-path tests should also prove the newly added tag/dependency appears exactly once.

### Post-task Reflection
- Set equality is a common false-green for dedup ACs because it hides multiplicity.
- Scoped quality evidence isolated the task-owned file cleanly; the reject is about proof strength, not execution failures.
- The retry-3 nested-list mutation did close the prior deep-copy gap; the remaining misses are narrower than the previous rejects.
[[2026-04-24]]
## Architecture Review (loop-breaker re-evaluation)

### Context
Third review failure → loop-breaker routing to backlog. Reviewer's remaining concern: `test_add_tags_merges_with_existing` and `test_add_deps_merges_with_existing` use set equality, which hides multiplicity. Two AC lines marked FAIL.

### Loop-Breaker Assessment

The reviewer's concern is technically valid but practically marginal:

1. The engine's dedup guard (`if t not in record.tags` at engine.py L957-959) only fires when the added item already exists in the list. For the new-item merge path (adding "beta" to ["alpha"]), the guard is irrelevant — "beta" gets appended exactly once regardless of the guard.

2. The idempotency tests (`test_add_tags_dedup_is_idempotent`, `test_add_deps_dedup_is_idempotent`) already cover the actual dedup codepath with proper count assertions.

3. However, set equality IS objectively weaker than length/list assertions. Adding `len()` checks is trivially mechanical and definitively closes the loop.

### AC Refinement (breaking the loop)

Refined the two AC lines to require explicit multiplicity proof:

**Before:**
- add_tags with dedup (adding existing tag is idempotent)
- add_deps with dedup (adding existing dep is idempotent)

**After:**
- add_tags with dedup: new tag added exactly once (assert result length, not set equality); existing tag idempotent (count == 1)
- add_deps with dedup: new dep added exactly once (assert result length, not set equality); existing dep idempotent (count == 1)

This makes the assertion approach explicit in the AC, removing reviewer interpretation and preventing a 4th round-trip.

### Evaluation (post-refinement)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure test coverage, one concern |
| Interface clarity | PASS | AC now specifies exact assertion approach for dedup lines |
| Dependency correctness | PASS | No deps; test file exists with 23 tests |
| Module layering | PASS | Tests only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Only genuinely uncovered branches remain |
| Premise challenge | PASS | edit_task field mutations and properties are uncovered |
| Pattern consistency | PASS | Follows _make_board/_write_task helpers |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: SKIP — loop-breaker refinement pass, narrow AC clarification only
- Confidence post-refinement: 0.94

### Verdict: APPROVE (with REFINE)
### Action Taken: Refined add_tags/add_deps AC lines to require explicit length assertions. 21 of 23 existing tests are already compliant; the two merge tests need a mechanical `len()` addition. Tagged `test` for pipeline pass-through. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes (retry 4)
- Test file: tests/test_engine_coverage_1113.py
- Retry: tightened 2 LAX dedup proofs identified by reviewer (3rd review failure, loop-breaker routing)
- Existing 23 tests: all still PASS (unchanged)
- Change: 2 tests strengthened (no new tests added)

### Changes (mechanically applied per AC refinement)
| Test | Old assertion | New assertion | Weakness fixed |
|------|--------------|---------------|----------------|
| `test_add_tags_merges_with_existing` | `assert set(result.tags) == {"alpha", "beta"}` | `assert sorted(result.tags) == ["alpha", "beta"]` | Set equality hides multiplicity — sorted list equality proves "beta" appears exactly once |
| `test_add_deps_merges_with_existing` | `assert set(result.depends_on) == {2, 3}` | `assert sorted(result.depends_on) == [2, 3]` | Same — proves 3 appears exactly once |

### Run result
- 23 tests total, 23 passed, 0 failed — ruff clean
- Coverage task: tests prove existing engine behaviour; PASS is the correct outcome.
- Commit: d84b6fb9

### AC coverage table
| AC line | Test(s) | Verdict |
|---------|---------|---------|-
| title, body, priority, status, parent mutations | test_*_mutation_reflected_on_returned_task (×5) | PASS |
| add_tags with dedup (new tag exactly once) | test_add_tags_merges_with_existing (sorted list), test_add_tags_dedup_is_idempotent (count==1) | PASS |
| remove_tags | test_remove_tags_drops_specified_tag | PASS |
| add_deps with dedup (new dep exactly once) | test_add_deps_merges_with_existing (sorted list), test_add_deps_dedup_is_idempotent (count==1) | PASS |
| remove_deps | test_remove_deps_drops_specified_dep | PASS |
| Invalid status → ValueError | test_invalid_status_raises_value_error | PASS |
| Invalid priority → ValueError | test_invalid_priority_raises_value_error | PASS |
| append_body without timestamp | test_append_body_without_timestamp_has_no_date_prefix, test_append_body_preserves_original_body_in_order, test_append_body_preserves_original_body | PASS |
| agent_name non-empty + stable | test_agent_name_is_non_empty_string, test_agent_name_is_stable_across_calls, test_agent_name_is_stable_across_many_calls | PASS |
| board_config() deep copy | test_board_config_returns_deep_copy, test_board_config_deep_copy_covers_nested_dicts, test_board_config_deep_copy_covers_nested_agent_map, test_board_config_deep_copy_existing_nested_list_is_isolated | PASS |
[[2026-04-24]]
## Builder Notes
- Implementation: non-implementation coverage task (`test` tag); no source edits in builder phase.
- Files changed: none.
- Tests: 23 passed, 0 failed, 0 skipped on `tests/test_engine_coverage_1113.py` (quality-runner scoped verification).
- Coverage: contextual scoped result `owlbear_kanban.engine` 24% (`overall_pct` 29) for this single task-owned test file.
- Ruff: clean (`tests/test_engine_coverage_1113.py`).
- Evidence summary: retry-4 dedup-proof tightening is present (`sorted(...)` assertions for add_tags/add_deps merge paths), scoped GREEN verified, and task is ready for review.
- Fixes applied: none in builder phase (test-only pass-through with verification).
[[2026-04-24]]
## Review Evidence
### Test Results
- Quality-Runner scoped on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): 23 passed, 0 failed, 0 skipped.
- Independent code audit of the task-owned AC suite found no missing or lax AC proof. The latest retry closes the previously rejected dedup-multiplicity and deep-copy gaps.

### Lint
- Scoped lint on [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): clean.

### Coverage
- Scoped coverage context: `owlbear_kanban.engine` 24% (`overall_pct` 29).
- Recorded as context only. This task is a narrow coverage-slice on a large engine module; the scoped percentage is not evidence of a remaining task-owned AC gap.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| title, body, priority, status, parent mutations (each verified on returned Task) | Direct returned-task equality assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L127), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L134), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L141), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L148), and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L155). | PASS |
| add_tags with dedup: new tag added exactly once; existing tag idempotent | Exact multiplicity proofs at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L168) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L176), matching the guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L958). | PASS |
| remove_tags | Removal/preservation assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L178). | PASS |
| add_deps with dedup: new dep added exactly once; existing dep idempotent | Exact multiplicity proofs at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L192) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L200), matching the guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L965). | PASS |
| remove_deps | Removal/preservation assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L202). | PASS |
| Invalid status -> ValueError | Direct constrained ValueError assertion in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L210). | PASS |
| Invalid priority -> ValueError | Direct constrained ValueError assertion in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L217). | PASS |
| append_body without timestamp (no date prefix) | No-prefix plus append-order/preserve-body assertions in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L232) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L244), matching append semantics at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L982). | PASS |
| agent_name is non-empty str, stable across calls | Type/non-empty checks plus repeated-call stability proof in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L270) and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L291), matching the instance-backed property at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L413) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L478). | PASS |
| board_config() returns deep copy (mutating returned config doesn't affect engine state) | Top-level list, nested dict-container, and existing nested-list isolation checks in [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L305), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L321), [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L324), and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L361), matching [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L506) and the mutable config fields in [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L77). | PASS |

#### Security Review
- No issues found. The task-owned change is a local pytest file only; no secrets, subprocesses, network calls, user-controlled path handling, or unsafe deserialization surface was introduced.

#### Test Integrity
| Original Test Scope | Assessment |
|---------------------|------------|
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L124) `TestFromAC_EngineEditTaskFieldMutations` | PRESERVED / STRENGTHENED |
| [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L267) `TestFromAC_EngineProperties` | PRESERVED / STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality, multiplicity, ordering, and constrained-exception assertions throughout the AC suite. |
| Negative/error-path coverage | ADEQUATE | Invalid status and invalid priority are covered directly on `edit_task()`. |
| Manual mutation reasoning | STRONG | The latest retry would fail on duplicate-add regressions, overwrite-vs-append regressions, recompute-per-call `agent_name` regressions, and shallow-copy regressions on existing nested mutable values. |
| Test independence | STRONG | Each test builds a fresh temp board and engine instance. |
| Descriptive test names | STRONG | Test names map cleanly to the AC lines and guarded regressions. |

#### Data Safety
- No issues found. The task-owned tests operate only on isolated temp directories and in-process engine instances.

#### Implementation-Aware Gaps
- No significant untested task-owned paths found within the refined AC scope.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L277) is a redundant same-expression self-comparison; the real stability signal is the stronger repeated-call proof at [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py#L283).
- Module-wide engine coverage remains low in this single-file scoped run. That is broader engine debt, not a defect in this task-owned AC proof.

### Deductions
-0.02 residual broader engine coverage debt outside this task slice.
-0.02 minor redundancy in one smaller property test that is already superseded by the stronger repeated-call check.

### Verdict: PASS
### Confidence: 0.94
### Action
- Advance to `docs`. All refined AC lines are now proven by the task-owned `TestFromAC_*` suite, and no implementation, security, or test-integrity defects remain.

### Post-task Reflection
- Exact-list equality is sufficient AC proof for dedup when the refined contract requires multiplicity, even if it does not literally call `len()`.
- Deep-copy ACs need at least one mutation of an existing nested mutable value; new-key insertion alone only proves container separation.
- For narrow coverage-slice tasks, record module-wide coverage as context, but gate on the written AC and task-owned proof rather than unrelated broader-suite debt.
[[2026-04-24]]
## Docs Gate

### Checklist
| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Prose docs | No | N/A | Test-only task; no behavior, API, CLI, config, or package structure changed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Research sources are all internal codebase references |
| 4 | Research doc | Yes | PASS | `.owlbear/research/engine-coverage-edit-show-property-1113.md` exists and is linked in task body; no follow-up tasks required |
| 5 | Diagram maintenance | No | N/A | No `describes` glob in doc-index matches `tests/test_engine_coverage_1113.py` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No IN-scope docs orphaned or touched |

### Files Updated
None.

### Child Tasks Created
None.

### Scratch Files Cleaned
None created.

[[2026-04-24]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| title, body, priority, status, parent mutations | Direct equality assertions in test_engine_coverage_1113.py L127-L160 | PASS |
| add_tags with dedup (new tag exactly once) | sorted list equality at L168; count assertion at L176 | PASS |
| remove_tags | Removal/preservation at L178 | PASS |
| add_deps with dedup (new dep exactly once) | sorted list equality at L192; count assertion at L200 | PASS |
| remove_deps | Removal/preservation at L202 | PASS |
| Invalid status → ValueError | pytest.raises at L210 | PASS |
| Invalid priority → ValueError | pytest.raises at L217 | PASS |
| append_body without timestamp | No-prefix + preserve-body + ordering at L222-L257 | PASS |
| agent_name non-empty + stable | Non-empty string + 10-read stability at L268-L290 | PASS |
| board_config() deep copy | Top-level, nested-dict, and existing nested-list isolation at L293-L367 | PASS |

### Test Results
- pytest (scoped, reviewer-verified): 23 passed, 0 failed, 0 skipped
- ruff (scoped): clean
- Full suite: Quality-Runner anomaly — QR went off-script and attempted production code fixes instead of reporting. Task #1113 adds only a test file with zero production code changes; cross-task regressions are structurally impossible. Pre-existing broader engine-suite debt (agent_name constructor signature, config validation strictness) noted across multiple review cycles and is unrelated to this task.

### Architect Quality: 4/5
Initial AC was inflated with 6 duplicate show_task paths (challenger blocked at 0.22). Architect showed excellent self-correction: accepted challenge findings, dropped duplicates, narrowed properties scope, and broke the review loop by refining dedup AC lines to require explicit multiplicity proof. Final AC is specific and well-targeted with 10 testable lines.

### Deduction Breakdown
- AC lines without evidence: 0 × -.02 = 0
- Lint violations: 0 → -.00
- AC quality ≤ 3: NO (4/5) → -.00
- Missing reviewer evidence: NO → -.00
- Full-suite test failures in task scope: 0 → -.00
- QR anomaly (unable to independently verify full-suite clean state; mitigated by structural impossibility of regressions from test-only addition): -.02

### Confidence: 0.98
### Action: archive