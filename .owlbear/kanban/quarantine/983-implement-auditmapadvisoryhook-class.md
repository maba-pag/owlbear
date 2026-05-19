---
id: 983
title: Implement AuditMapAdvisoryHook class
status: archived
priority: needed
created: 2026-03-24T03:48:08.9934376+01:00
updated: 2026-03-24T21:07:08.3551733+01:00
started: 2026-03-24T21:06:28.9665542+01:00
completed: 2026-03-24T21:06:28.9665542+01:00
tags:
    - phase-6
    - hooks
    - type:build
depends_on:
    - 982
class: standard
---

## Acceptance Criteria

- [ ] AC1: New module `src/owlbear/core/audit_map_hook.py` containing `AuditMapAdvisoryHook` class
- [ ] AC2: `__call__(data: TaskCompleteData)` gates in order: (1) `outcome == success`, (2) `settings.audit_map_worker_enabled` is True, (3) task has `worker:audit-map` tag (resolved via `kanban-md show --json` subprocess, following `RetrospectiveHook._get_priority()` pattern at `src/owlbear/core/retrospective_hook.py:230`)
- [ ] AC3: When all gates pass, delegates to `supervisor.schedule(_LazyCoroutine(...))` for background execution
- [ ] AC4: Background coroutine writes a template-based markdown advisory (no LLM) to `docs/scratch/{task-id}-audit-map.md`. Template aggregates task metadata (title, status, tags, AC section) read from the kanban task file
- [ ] AC5: When a `ChannelPlugin` is injected and non-None, sends a single notification message on advisory completion; silent when channel is `None`
- [ ] AC6: No mutations to kanban board state, claims, docs (non-scratch), or source files
- [ ] AC7: `audit_map_worker_enabled: bool = Field(default=False)` added to `OwlBearSettings` in `src/owlbear/config.py`
- [ ] AC8: Wired in `_wire_post_model_hooks()` (not `build_hooks()`) behind config flag, sharing the existing `HookWorkerSupervisor`. Builder adds `channel: ChannelPlugin | None = None` parameter to `_wire_post_model_hooks()` and threads it from the `bootstrap()` call site
- [ ] AC9: All RED tests from #982 pass
- [ ] AC10: ruff clean on all changed files

See docs/research/task-complete-audit-map-advisory-worker.md for design.
Depends on #982 (RED tests).

[[2026-03-24]] Tue 04:46

## Architecture Review

**Verdict:** Approve (after refinement)

### AC Assessment

| AC Line | Original | Assessment | Action |

|---------|----------|------------|--------|

| AC1: New module | src/owlbear/core/audit_map_hook.py | Clear, verifiable, correct layer (core/) | Kept |

| AC2: **call** filters | outcome, config flag, tag | Vague on tag resolution: TaskCompleteData has only task_id+outcome. Refined: specify kanban-md show --json subprocess | Refined |

| AC3: supervisor.schedule() | Delegates to supervisor | Clear, verifiable | Kept |

| AC4: Writes advisory | markdown to docs/scratch/ | Vague on content. Refined: template-based, no LLM, aggregates task metadata | Refined |

| AC5: Channel notification | Optional ChannelPlugin | Clear, verifiable | Kept |

| AC6: No mutations | No board/claims/docs/source changes | Clear boundary | Kept |

| AC7: Config flag | audit_map_worker_enabled default=False | Clear, follows existing pattern | Kept |

| AC8: Register in build_hooks() | build_hooks() behind flag | WRONG: supervisor lives in _wire_post_model_hooks(). Refined: correct wiring location + channel threading | Refined |

| AC9: RED tests pass | All #982 tests pass | Clear, verifiable | Kept |

| AC10: ruff clean | (added) | Missing from original AC | Added |

### Architecture Notes

### Architecture Notes

- Module: src/owlbear/core/audit_map_hook.py as peer to retrospective_hook.py. Correct core/ layer.

- Pattern: follows RetrospectiveHook **call** + _LazyCoroutine + supervisor.schedule() pipeline.

- Wiring: _wire_post_model_hooks() needs new channel param. bootstrap() has channel at line ~174 but does not pass it.

- No LLM: template-based advisory is KISS. Model available at call site if ever needed (YAGNI).

- Security: no new system boundaries. Writes confined to docs/scratch/ (gitignored). Read-only kanban-md subprocess.

- Single domain: hooks (core/). No cross-domain concerns.

### Changes Made

- Refined AC: AC2 (tag resolution), AC4 (template content), AC8 (wiring location), AC10 (added ruff)

- Added depends_on: [982] via --add-dep 982

### Dependencies

- Added: depends_on #982 (RED tests) - was in body but missing from frontmatter

- Verified: #982 is backlog, unclaimed, ready for test-writer

[[2026-03-24]] Tue 18:00

## Test-Writer Notes

- Test file: tests/test_audit_map_hook.py
- Classes: TestFromAC_983_AuditMapConfigFlag, TestFromAC_983_AuditMapWiringInBootstrap
- Tests per category: happy 5, edge 2, error 0, boundary 5
- Total: 12 tests, all FAIL
- ruff: clean
- AC7 (config field): 5 tests
- AC8 (wiring): 7 tests
- AC9 (RED tests from 982): 27 existing TestFromAC_ tests preserved in file for builder

[[2026-03-24]] Tue 18:13

## Builder Notes

- Files changed: src/owlbear/config.py; src/owlbear/bootstrap/**init**.py; src/owlbear/core/audit_map_hook.py; tests/test_audit_map_hook.py
- Tests: 12 passed in TestFromAC_983 classes; 43 passed in tests/test_audit_map_hook.py; 4 passed in TestBuilderDiscovered
- Coverage: src/owlbear/core/audit_map_hook.py 99 percent in scoped bare coverage run (config.py 70 percent and bootstrap/**init**.py 35 percent in the same scoped run).
- Lint: ruff clean on changed files
- Evidence: task-specific and full-file pytest runs passed with controlled plugin loading; scoped bare coverage run passed; ruff reported All checks passed.
- Fixes applied: added audit_map_worker_enabled setting, wired AuditMapAdvisoryHook in_wire_post_model_hooks with channel threading, implemented task-file metadata advisory template, added builder-discovered metadata tests.

[[2026-03-24]] Tue 20:24

## Review Evidence

### Review: #983 - Implement AuditMapAdvisoryHook class

### Test Results

- Scoped task-file run completed cleanly: `tests/test_audit_map_hook.py` passed with 43 passed and 2 expected optional-dependency warnings.
- Related wiring regression slice completed cleanly: `tests/test_bootstrap.py` filtered to `wire_post_model_hooks` passed with 205 passed and the same 2 expected warnings.
- The warnings were the existing `qdrant_client`-missing skips from `tests/conftest.py`.
- Tooling note: the first foreground scoped pytest attempt was interrupted during pytest startup with a `KeyboardInterrupt`; one isolated background retry completed cleanly and is the evidence used here.

### Lint Results

- Task-scoped ruff on `src/owlbear/core/audit_map_hook.py`, `src/owlbear/config.py`, `src/owlbear/bootstrap/__init__.py`, and `tests/test_audit_map_hook.py` returned clean.

### Coverage

- `src/owlbear/core/audit_map_hook.py`: 99 percent in the scoped task-file coverage run.
- `src/owlbear/config.py`: 70 percent and `src/owlbear/bootstrap/__init__.py`: 35 percent in that same bare whole-file report.
- Tooling gap: repo coverage is whole-file only for bare coverage runs, so large pre-existing modules are not changed-line precise. The new config and wiring lines are directly exercised by `TestFromAC_983_AuditMapConfigFlag`, `TestFromAC_983_AuditMapWiringInBootstrap`, and the 205 passing bootstrap regression tests.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|-------------------------|---------|
| AC1 module and class | file import plus scoped file run | Yes, import and instantiation would fail immediately | COVERED |
| AC2 gate order and tag resolution | `test_failure_outcome_skips_schedule`, `test_config_flag_false_skips_schedule`, `test_missing_audit_map_tag_skips_schedule`, `test_empty_tags_skips_schedule`, `test_tag_resolution_uses_subprocess_kanban_show_json` | Yes | COVERED |
| AC3 schedule lazy background work | `test_all_gates_pass_calls_schedule_exactly_once`, `test_all_gates_pass_schedule_receives_lazy_awaitable` | Yes | COVERED |
| AC4 advisory template and task metadata | `test_worker_writes_scratch_file_at_correct_path` plus builder-discovered metadata tests | Yes | COVERED |
| AC5 optional completion notification | `test_worker_sends_channel_message_once`, `test_worker_channel_message_contains_task_id`, `test_worker_channel_send_not_called_when_channel_none` | Yes | COVERED |
| AC6 scratch-only and no board or source mutations | `test_worker_creates_no_other_docs_files`, `test_worker_does_not_call_subprocess_during_execution`, `test_worker_does_not_write_to_src`, path-safety tests | Yes | COVERED |
| AC7 config flag field | `TestFromAC_983_AuditMapConfigFlag` methods | Yes | COVERED |
| AC8 post-model hook wiring and shared supervisor | `TestFromAC_983_AuditMapWiringInBootstrap` methods | Yes | COVERED |
| AC9 prior RED tests pass | scoped file run with 43 passed | Yes | COVERED |
| AC10 lint clean | task-scoped ruff command | Yes | COVERED |

#### Security Review

- No hardcoded secrets found in the reviewed files.
- The kanban inspection call uses `subprocess.run` with an argv list and no shell at `src/owlbear/core/audit_map_hook.py:91`, so shell injection was not introduced.
- File output is confined by `_safe_task_id()` at `src/owlbear/core/audit_map_hook.py:273` before writing under `docs/scratch` at lines 122 through 127; the traversal tests at lines 331, 350, and 372 passed.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All `TestFromAC_*` methods from test-writer commit `bc9482e` | `git diff bc9482e..d0c606a -- tests/test_audit_map_hook.py` shows only a new `TestBuilderDiscovered` block appended after the final `TestFromAC_983` method; no deletions and no assertion changes inside `TestFromAC_*` blocks | PRESERVED |
| Current worktree drift versus builder commit | `tests/test_audit_map_hook.py` has formatting-only line wrapping in three method signatures and two `read_text()` calls; no semantic change to assertions or coverage intent | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact `assert_not_called`, `assert_called_once`, path existence, channel message content, and exact advisory text checks at lines 109, 183, 235, 277, 285, and 737 |
| Negative and error paths | STRONG | Failure, skipped, disabled flag, missing tag, empty tag list, empty task id, subprocess exception, bad return code, malformed JSON, non-dict payload, non-list tags, missing AC section, and read-error cases are covered at lines 109, 131, 143, 155, 396, 406, 415, 427, 439, 451, 777, and 818 |
| Mutation reasoning | STRONG | Removing `_safe_task_id`, metadata parsing, fallback behavior, or lazy scheduling would fail lines 195, 331, 350, 372, 737, 777, and 818 |
| Test independence | STRONG | Tests build isolated tmp workspaces and fresh mocks through helpers at the top of the file and do not share mutable state |
| Descriptive names | STRONG | Test names describe exact scenarios and outcomes across the file, especially the `TestFromAC_983_*` and path-safety cases |

#### Data Safety

- No data-safety issue found. Writes are limited to `docs/scratch` at lines 122 through 127, task IDs are sanitized at line 273, and malformed or missing task metadata falls back safely through lines 134 through 277.

#### Implementation-Aware Test Gaps

- No significant untested behavioral paths found. The current tests cover the helper and branch complexity actually introduced by the implementation: empty task IDs, subprocess failures, malformed JSON, malformed task frontmatter, missing acceptance criteria, read errors, and path traversal confinement.

### Pass 2 - INFORMATIONAL

- Current worktree drift on `src/owlbear/core/audit_map_hook.py` is line-ending churn only relative to builder commit `d0c606a`; no semantic source drift was detected.
- Current worktree drift on `tests/test_audit_map_hook.py` is formatting-only and does not weaken any `TestFromAC_*` case.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `AuditMapAdvisoryHook` is defined at `src/owlbear/core/audit_map_hook.py:42`; the module import succeeds in the 43 passing task-file tests | scoped file run | PASS |
| AC2 | `__call__` gates are implemented at lines 64 through 79 and tag lookup is the read-only kanban subprocess at lines 87 through 118 | lines 109, 131, 143, 155, 167 | PASS |
| AC3 | background delegation is `self._supervisor.schedule(_LazyCoroutine(...))` at line 79 | lines 183 and 195 | PASS |
| AC4 | worker writes to `docs/scratch` at lines 122 through 127; advisory building and task-file parsing are at lines 134 through 277 | lines 235, 737, 777, 818 | PASS |
| AC5 | optional channel send is guarded at line 130 | lines 277, 285, 299, 306 | PASS |
| AC6 | no non-scratch or source writes are introduced beyond lines 122 through 127; no worker subprocess call after scheduling; sanitized path leaf at line 273 | lines 243, 257, 265, 331, 350, 372 | PASS |
| AC7 | `audit_map_worker_enabled` field is added at `src/owlbear/config.py:486` with `default=False` | lines 491, 499, 517, 524 | PASS |
| AC8 | `_wire_post_model_hooks()` signature accepts `channel` at `src/owlbear/bootstrap/__init__.py:112`; hook registration is behind the flag at lines 141 through 148; `bootstrap()` threads `channel=channel` at line 221 | lines 552, 571, 598, 623, 648, 676, 702; related bootstrap slice 205 passed | PASS |
| AC9 | all RED tests from #982 in `tests/test_audit_map_hook.py` pass in the scoped reviewer run | scoped file run with 43 passed | PASS |
| AC10 | task-scoped ruff returned clean on all changed files | task-scoped ruff command | PASS |

### Verdict: PASS

- Confidence: .93

### Action Taken

- Review evidence appended.
- Task moved to `docs`.
- Reviewer claim released.

[[2026-03-24]] Tue 21:06

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 module + class | src/owlbear/core/audit_map_hook.py:42 defines AuditMapAdvisoryHook | PASS |
| AC2 gate order | **call** gates: outcome (L69), config flag (L72), tag via subprocess (L79) | PASS |
| AC3 supervisor.schedule | _LazyCoroutine dispatched at L82 | PASS |
| AC4 advisory template | _run_worker writes to docs/scratch/{id}-audit-map.md at L122-127 | PASS |
| AC5 optional channel | channel.send guarded by None check at L130 | PASS |
| AC6 no mutations | writes confined to docs/scratch, no board or src mutations | PASS |
| AC7 config flag | audit_map_worker_enabled: bool = Field(default=False) at config.py:486 | PASS |
| AC8 wiring | _wire_post_model_hooks accepts channel kwarg (L117), hook behind flag (L141-148), bootstrap threads channel (L228) | PASS |
| AC9 RED tests pass | 43 passed in test_audit_map_hook.py | PASS |
| AC10 ruff clean | All checks passed on changed files | PASS |

### Test Results

- pytest (task-specific): 43 passed, 0 failed
- pytest (full suite): 4264 passed, 35 failed (all pre-existing, none related to #983)
- ruff: clean on all changed files

### AC Quality Score: 4

AC was adequate with minor gaps refined by architect (wiring location, tag resolution, ruff).

### Confidence: .96

### Action: archive

[[2026-03-24]] Tue 21:07

## Audit

Confidence: .96 - All 10 AC items verified. 43 task tests pass, 4264 full-suite pass (35 pre-existing failures unrelated). Ruff clean. AC quality 4/5.
Action: archive
