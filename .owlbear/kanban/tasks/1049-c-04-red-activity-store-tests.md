---
id: 1049
title: 'C-04: RED — activity_store tests'
status: in-progress
priority: needed
created: 2026-04-21T10:42:50.268061+00:00
updated: 2026-04-21T21:40:10.392985+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §8.9
Module: `serve/kanban/tests/test_activity_store.py`

## Acceptance Criteria

- [ ] AC-C42: `append_activity_event(...)` writes structured `ActivityEvent` JSONL entries to gitignored board-level `activity.jsonl`; `list_activity_events(...)` applies declared filters without scanning task frontmatter
- [ ] AC-C44: No separate session table on disk — `activity.jsonl` is the only persistent history substrate
- [ ] AC-C44a: `compact_activity_log` tests: (a) `before_dt=None` auto-resolves to most recently closed session `ended_at`; (b) entries in open sessions always retained; (c) last 500 entries always retained; (d) rewritten atomically via `atomic_write`; (e) idempotent on re-run
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_activity_store.py`
- Classes: `TestFromAC_ActivityAppendQuery`, `TestFromAC_ActivityCompaction`, `TestBuilderDiscovered`
- Tests per category: happy 10, edge 5, error 2, boundary 5
- Total: 22 tests
- ruff: clean (fixed ARG002 unused `tmp_path` param and UP017 `timezone.utc` → `UTC` alias)
- Commits: `de06fa41` (original RED tests — failing before impl), `1af4efc0` (ruff fix)

**Context:** Test file was committed in `de06fa41` before any implementation existed (RED state at commit time). Implementation `activity_store.py` was subsequently written to the working tree (untracked) by the builder. Tests now pass — implementation is ready to be committed by the builder.

**AC coverage:**
| AC | Tests |
|----|-------|
| C42 — append writes JSONL to activity.jsonl | `test_ac_c42_append_writes_to_activity_jsonl`, `test_ac_c42_append_multiple_events_each_on_own_line`, `test_ac_c42_event_fields_match_activity_event_schema` |
| C42 — list_activity_events filters (task_id, action, source, since, limit, no filters) | 6 filter tests |
| C42 — no task .md scanning | `test_ac_c42_does_not_scan_task_frontmatter` |
| C44 — only activity.jsonl on disk | `test_ac_c44_no_session_jsonl_file_on_disk` |
| C44 — empty/missing returns [] | `test_ac_c44_empty_log_returns_empty_list` |
| C44a(a) — before_dt=None resolves to last closed session | `test_ac_c44a_a_before_dt_none_resolves_to_latest_closed_session` |
| C44a(b) — open sessions retained | `test_ac_c44a_b_open_sessions_always_retained` |
| C44a(c) — last 500 retained | `test_ac_c44a_c_last_500_entries_always_retained` |
| C44a(d) — atomic rewrite | `test_ac_c44a_d_rewritten_atomically` |
| C44a(e) — idempotent | `test_ac_c44a_e_idempotent_no_new_appends` |
[[2026-04-21]]
## Builder Notes
- Implementation file: serve/kanban/src/owlbear_kanban/activity_store.py
- Test file touched: serve/kanban/tests/test_activity_store.py (TestBuilderDiscovered only)
- Scoped quality-runner result: 26 passed, 0 failed, 0 skipped
- Coverage: 98 percent on module owlbear_kanban.activity_store
- Lint: ruff clean on serve/kanban/src/owlbear_kanban/activity_store.py and serve/kanban/tests/test_activity_store.py
- Evidence summary: append/query/compact behaviors validated, malformed JSONL rows ignored safely, missing and empty compaction inputs handled, hard-floor retention path exercised
- Fixes applied during retry: added targeted builder-discovered tests to cover malformed rows and compaction edge branches, raising module coverage from 86 percent to 98 percent

Post-task reflection
- Initial quality run showed coverage below gate despite all tests passing.
- Hard-floor branch was initially not exercised because claim actions implied open sessions; using non-claim events made the branch observable.
- Focused test additions in TestBuilderDiscovered achieved gate compliance without changing TestFromAC classes or AC behavior.
- Main time sink was isolating which missing lines were true behavior gaps versus intentionally defensive exception paths.
[[2026-04-21]]
## Review Evidence
### Test Results
- Scoped quality-runner: pytest 26 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_activity_store.py`.
- Downstream regression context only: pytest 74 passed, 10 failed on `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_list_sessions.py`, and `serve/kanban/tests/test_list_sessions_952.py`. Those failures are in AC-C43 / task #1054 RED coverage (`serve/kanban/tests/test_engine_activity.py:3-5`) and were not used to gate #1049.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/activity_store.py` and `serve/kanban/tests/test_activity_store.py`.

### Coverage
- `owlbear_kanban.activity_store`: 98% (quality-runner reported missing lines 153-154).

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C42 append/query/frontmatter separation | `test_ac_c42_*` at `serve/kanban/tests/test_activity_store.py:70,85,96,110,121,132,142,156,165,174` | Yes for the declared append/filter/no-frontmatter behaviors | COVERED |
| AC-C44 only `activity.jsonl` persists | `serve/kanban/tests/test_activity_store.py:196,206` | Yes | COVERED |
| AC-C44a(a) `before_dt=None` resolves to latest closed session | `serve/kanban/tests/test_activity_store.py:221` | No; the assertion at `serve/kanban/tests/test_activity_store.py:242-244` only proves that bytes shrank, not that the latest closed session was used | LAX |
| AC-C44a(b) open sessions retained | `serve/kanban/tests/test_activity_store.py:246` | Partial; catches a single unclosed claim, but not reopened-task/session-boundary behavior | LAX |
| AC-C44a(c) last 500 retained | `serve/kanban/tests/test_activity_store.py:267` and builder-discovered `serve/kanban/tests/test_activity_store.py:397` | Yes | COVERED |
| AC-C44a(d) atomic rewrite via `atomic_write` | `serve/kanban/tests/test_activity_store.py:284` | No; `serve/kanban/tests/test_activity_store.py:293-294` only checks for no leftover temp files, not delegation to `atomic_write` | LAX |
| AC-C44a(e) idempotent re-run | `serve/kanban/tests/test_activity_store.py:296` | Yes | COVERED |

#### Security Review
- No hardcoded secrets, injection points, path traversal, unsafe deserialization, or new dependency risk found in `serve/kanban/src/owlbear_kanban/activity_store.py`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ActivityAppendQuery` (`serve/kanban/tests/test_activity_store.py:67`) | No weakening visible in current file | PRESERVED |
| `TestFromAC_ActivityCompaction` (`serve/kanban/tests/test_activity_store.py:218`) | No weakening visible in current file | PRESERVED |
| Builder additions under `TestBuilderDiscovered` (`serve/kanban/tests/test_activity_store.py:338`); task body says `TestBuilderDiscovered only` at `.owlbear/kanban/tasks/1049-c-04-red-activity-store-tests.md:57` | Added coverage only | STRENGTHENED |
- Note: commit snapshots `de06fa41` / `1af4efc0` were not directly accessible from available review tools, so integrity assessment is based on current file structure plus task-body evidence.

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | `serve/kanban/tests/test_activity_store.py:242-244` and `serve/kanban/tests/test_activity_store.py:293-294` allow multiple incorrect implementations to pass |
| Negative/error-path coverage | ADEQUATE | Missing file, empty file, malformed rows, and parser failure paths are covered at `serve/kanban/tests/test_activity_store.py:341-432` |
| Manual mutation reasoning | WEAK | A task-level open-session implementation passes the current suite even though same-task re-claim cycles are normal domain behavior (`serve/kanban/tests/test_list_sessions.py:444-459`) |
| Test independence | STRONG | Each test creates isolated temp board state |
| Descriptive test names | STRONG | Names map directly to ACs and edge cases |

#### Data Safety
- No separate blocking data-safety finding beyond the compaction logic defect below.

#### Implementation-Aware Gaps
- FAIL: `compact_activity_log()` retains any row whose `task_id` is in `open_task_ids` (`serve/kanban/src/owlbear_kanban/activity_store.py:161,169`), but `_find_open_session_task_ids()` tracks only task IDs, not claim-cycle boundaries (`serve/kanban/src/owlbear_kanban/activity_store.py:221-231`). For a task that was claimed, closed, and later re-claimed, compaction will keep the old closed session as well as the current open session. Same-task multi-session logs are an explicit domain path in `serve/kanban/tests/test_list_sessions.py:444-459`. Current compaction tests do not exercise that case.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 1 (`.owlbear/kanban/tasks/1049-c-04-red-activity-store-tests.md:55`) |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Broader regression checks found 10 AC-C43 failures in `serve/kanban/tests/test_engine_activity.py`, but that suite is its own RED task (`serve/kanban/tests/test_engine_activity.py:3-5`) and was treated as non-gating context only.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C42 | `append_activity_event` / `list_activity_events` implemented at `serve/kanban/src/owlbear_kanban/activity_store.py:22,37`; focused tests pass at `serve/kanban/tests/test_activity_store.py:70-192` | `test_ac_c42_*` | PASS |
| AC-C44 | No session table is created; focused tests pass at `serve/kanban/tests/test_activity_store.py:196,206` | `test_ac_c44_*` | PASS |
| AC-C44a(a) | Cutoff resolution calls `_find_last_closed_session_dt()` at `serve/kanban/src/owlbear_kanban/activity_store.py:158`; focused test passes but is lax | `test_ac_c44a_a_before_dt_none_resolves_to_latest_closed_session` | PASS |
| AC-C44a(b) | Keep rule is task-level, not session-level (`serve/kanban/src/owlbear_kanban/activity_store.py:161,169,221-231`) | `test_ac_c44a_b_open_sessions_always_retained` | FAIL |
| AC-C44a(c) | Hard-floor logic at `serve/kanban/src/owlbear_kanban/activity_store.py:173-180`; both focused tests pass | `test_ac_c44a_c_last_500_entries_always_retained`, `test_compact_activity_log_hard_floor_500` | PASS |
| AC-C44a(d) | Uses `atomic_write(activity_path, new_content)` at `serve/kanban/src/owlbear_kanban/activity_store.py:186` | `test_ac_c44a_d_rewritten_atomically` | PASS |
| AC-C44a(e) | Focused idempotence test passes at `serve/kanban/tests/test_activity_store.py:296-315` | `test_ac_c44a_e_idempotent_no_new_appends` | PASS |
| RED-phase `All tests fail` clause | Historical upstream handoff condition, not a review gate after builder implementation | Task body context | N/A |

### Confidence: 0.78
### Verdict: FAIL
### Action
- Reject to `in-progress`.
- Fix `compact_activity_log()` so open-session retention is claim-cycle aware rather than task-ID aware.
- Add a regression test for `claim -> close/release -> re-claim` on the same task under compaction.
- Tighten AC-C44a(a) and AC-C44a(d) assertions so incorrect cutoff selection or non-atomic rewrites cannot pass.