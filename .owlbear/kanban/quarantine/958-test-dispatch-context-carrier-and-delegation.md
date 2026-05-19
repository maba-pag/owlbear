---
id: 958
title: Test dispatch-context carrier and delegation runtime instructions
status: archived
priority: important
created: 2026-03-23T04:15:53.0195222+01:00
updated: 2026-03-23T16:33:18.6405971+01:00
started: 2026-03-23T16:33:13.5700075+01:00
completed: 2026-03-23T16:33:13.5700075+01:00
tags:
    - agent
    - scope:core
    - type:test
parent: 951
class: standard
---

See docs/research/dispatched-agent-runtime-context.md. Scope: core delegation only.

AC:

- Add or update failing tests in tests/test_delegation.py only to define the RED contract for the shared core dispatch-context carrier and formatter used by child-agent runs.
- Tests assert DelegationToolset._delegate() keeps the delegated task as the positional prompt and passes usage=, an incremented delegation_depth, and per-run instructions= to inner agent.run(...).
- Tests assert a dispatch context containing workspace_root, channel_name, and populated task metadata produces deterministic instructions= text and matching metadata= values for the child run.
- Tests assert absent or unknown task fields are omitted from formatted runtime context and metadata= so interactive delegation does not fabricate kanban labels or task metadata.
- Do not modify src/owlbear/daemon.py or daemon-focused tests in this task.

[[2026-03-23]] Mon 05:14

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add or update failing tests in tests/test_delegation.py only to define the RED contract for the shared core dispatch-context carrier and formatter used by child-agent runs. | The original suite boundary was too loose for a single RED seam. | Rewrote the AC to pin the task to tests/test_delegation.py and keep daemon coverage out of scope. |
| Tests assert DelegationToolset._delegate() keeps the delegated task as the positional prompt and passes usage=, an incremented delegation_depth, and per-run instructions= to inner agent.run(...). | Existing tests already cover usage passthrough and depth increment, but the new runtime-instructions seam needed explicit run-kwarg coverage. | Tightened the AC to require the positional prompt plus usage=, depth, and instructions= together. |
| Tests assert a dispatch context containing workspace_root, channel_name, and populated task metadata produces deterministic instructions= text and matching metadata= values for the child run. | The original AC mentioned instructions and optional metadata without defining the populated content the RED tests must lock down. | Rewrote the AC to specify the runtime fields the tests must cover. |
| Tests assert absent or unknown task fields are omitted from formatted runtime context and metadata= so interactive delegation does not fabricate kanban labels or task metadata. | The omission requirement was correct but needed a pass/fail outcome tied to interactive delegation. | Rewrote the AC to require omission from both formatted context and metadata without fabricated kanban state. |
| Do not modify src/owlbear/daemon.py or daemon-focused tests in this task. | This is already precise and preserves the parent split between core delegation and daemon dispatch. | Preserved unchanged. |

### Architecture Notes

- src/owlbear/core/agent.py already uses per-run instructions= for runtime-only context, and tests/test_agent.py shows the existing assertion style for run kwargs.
- src/owlbear/core/delegation.py currently forwards only the delegated task, deps=, and usage= to agent.run(...); this card is the RED gate for adding instructions=/metadata= without touching daemon wiring.
- src/owlbear/daemon.py has separate retry and fresh-dispatch builder.run(...) call sites covered by tests/test_daemon_coverage_gaps.py; those remain reserved for #960 and #961.
- src/owlbear/core/deps.py intentionally keeps workspace_root and session out of top-level OwlBearDeps, so this task should lock runtime-context behavior rather than reopen daemon or broad deps concerns.
- Verified #959 depends on #958, so moving #958 to todo preserves TDD ordering for the paired implementation card.

### Changes Made

- Rewrote the AC to name tests/test_delegation.py as the only RED seam for this task.
- Tightened the contract around instructions=, metadata=, positional prompt preservation, and omission of missing task fields.
- Verified the parent split from #951 and the paired dependency from #959 before approving the card.

### Dependencies

- Verified: docs/research/dispatched-agent-runtime-context.md, src/owlbear/core/agent.py, src/owlbear/core/delegation.py, src/owlbear/core/deps.py, tests/test_agent.py, tests/test_delegation.py, tests/test_daemon_coverage_gaps.py.
- Verified: #959 depends on #958.
- No dependency changes required on #958.

[[2026-03-23]] Mon 06:01

## Test-Writer Notes

- Test file: tests/test_delegation.py
- Classes: TestFromAC_RuntimeInstructionsKwarg, TestFromAC_DispatchContextFormatter, TestFromAC_AbsentTaskFieldsOmitted
- Tests per category: happy 6, formatter 8, omission 4
- Total: 18 tests, all FAIL
- ruff: clean
- AC coverage: AC2 (instructions+metadata kwargs via _delegate) -> 6 tests; AC3 (populated context formatter) -> 8 tests; AC4 (absent fields omitted) -> 4 tests

[[2026-03-23]] Mon 07:11

## Builder Notes

- Files changed: src/owlbear/core/delegation.py, src/owlbear/core/deps.py
- Tests: 35 passed (18 TestFromAC + 17 pre-existing), 100% coverage on delegation.py and deps.py
- Lint: ruff clean
- Evidence: 35 passed in 1.19s; all TestFromAC_RuntimeInstructionsKwarg, TestFromAC_DispatchContextFormatter, TestFromAC_AbsentTaskFieldsOmitted pass
- Fixes applied: Added DispatchContext dataclass and format_dispatch_context() to delegation.py; added dispatch_context field (TYPE_CHECKING import) to OwlBearDeps; updated _delegate() to forward instructions=/metadata= via run_kwargs when dispatch_context is present

[[2026-03-23]] Mon 07:50

## Review Evidence

## Review: #958 - Test dispatch-context carrier and delegation runtime instructions

### Test Results

- pytest tests/test_delegation.py: 35 passed, 0 failed, 2 warnings
- pytest tests/test_agent.py: 47 passed, 0 failed, 2 warnings

### Lint Results

- ruff src/ tests/: 240 RUF100 baseline errors (repo-wide, unrelated to #958 scope)
- ruff task scope (delegation.py, deps.py, test_delegation.py): all checks passed

### Coverage

- pytest --cov on tests/test_delegation.py reports src/owlbear/core/delegation.py at 100% and src/owlbear/core/deps.py at 100%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Verdict |
|---------|-------------|---------|
| _delegate positional task + usage + depth + instructions | test_run_call_has_task_usage_depth_and_instructions | COVERED |
| Populated dispatch context deterministic text + matching metadata values | test_formatting_is_deterministic, test_task_id_in_metadata_when_populated, test_task_title_in_instructions_when_populated | LAX (no positive task_status assertions) |
| Absent or unknown task fields omitted | TestFromAC_AbsentTaskFieldsOmitted suite | LAX (absent covered, unknown-field omission not directly exercised) |

No compensating TestBuilderDiscovered tests were added for the LAX areas.

#### Test Integrity

- git show --name-only for builder commit 01d0b40 lists only src/owlbear/core/delegation.py and src/owlbear/core/deps.py.
- TestFromAC classes in tests/test_delegation.py were preserved (no builder-side edits).

#### Test Quality

- Assertion specificity: ADEQUATE
- Negative/error paths: ADEQUATE
- Mutation reasoning: WEAK (removing task_status handling in format_dispatch_context lines 89-91 is not caught by a positive test)
- Test independence: STRONG
- Descriptive names: STRONG

#### Implementation-Aware Test Gaps

- format_dispatch_context task_status branch (src/owlbear/core/delegation.py:89-91) has no positive test coverage (task_status= is never set in tests/test_delegation.py).
- AC requires absent or unknown field omission; unknown-field omission is not explicitly asserted.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| RED tests in tests/test_delegation.py only | test-writer commit 2d6af77 touches only tests/test_delegation.py | PASS |
| _delegate forwards task + usage + depth + instructions | run kwargs wiring in delegation.py lines 192-204 + test at tests/test_delegation.py:360 | PASS |
| Populated context deterministic instructions + matching metadata values | delegation.py lines 64-93 and tests at 517/528/541 | FAIL (task_status matching not positively tested) |
| Absent/unknown fields omitted | omission tests at 599/611/623 | FAIL (unknown-field omission not directly tested) |
| No daemon changes | builder commit 01d0b40 file list excludes daemon files | PASS |

### Verdict: FAIL

### Action Taken

- Move #958 from review to todo and release claim.

[[2026-03-23]] Mon 08:44

## Test-Writer Notes (retry)

- Retry reason: reviewer cited missing tests -- task_status positive coverage + unknown-field omission
- Added 4 new tests to tests/test_delegation.py:
  - TestFromAC_DispatchContextFormatter: test_task_status_in_instructions_when_populated, test_task_status_in_metadata_when_populated
  - TestFromAC_AbsentTaskFieldsOmitted: test_workspace_root_not_in_metadata_keys, test_channel_name_not_in_metadata_keys
- All 4 new tests PASS (implementation already correct; tests add mutation-catching coverage)
- Preserved: 35 existing tests (all PASS), 39 total
- ruff: clean

[[2026-03-23]] Mon 11:50

## Builder Notes (retry)

- Files changed: src/owlbear/core/delegation.py, src/owlbear/core/deps.py (unchanged -- impl already correct)
- Tests: 39 passed (18 TestFromAC + 17 pre-existing + 4 test-writer retry), 0 failed
- Coverage: delegation.py 100%, deps.py 100% (bare --cov)
- Lint: ruff clean (delegation.py, deps.py, test_delegation.py)
- Evidence: 39 passed in 1.11s, EXIT:0
- Action: No code changes needed -- test-writer retry +4 tests pass against existing implementation
- Commits in main: 2d6af77 (tw RED), 01d0b40 (builder GREEN), 3541768 (tw retry +4)

[[2026-03-23]] Mon 12:52

## Review Evidence

### Review: #958 - Test dispatch-context carrier and delegation runtime instructions (retry)

### Test Results

- `uv run pytest tests/test_delegation.py -q --tb=short`: **39 passed, 0 failed** (2 optional-dependency warnings from `tests/conftest.py`).
- `uv run pytest tests/test_delegation.py::TestFromAC_RuntimeInstructionsKwarg tests/test_delegation.py::TestFromAC_DispatchContextFormatter tests/test_delegation.py::TestFromAC_AbsentTaskFieldsOmitted -v --tb=short --no-header`: **22 passed, 0 failed** (all AC-mapped tests green).
- `uv run pytest tests/test_agent.py -q --tb=short`: **47 passed, 0 failed** (adjacent regression check for delegation call paths).

### Lint Results

- `uv run ruff check src/owlbear/core/delegation.py src/owlbear/core/deps.py tests/test_delegation.py`: **All checks passed**.
- `uv run ruff check src/ tests/`: **233 RUF100 baseline findings** (repo-wide pre-existing lint debt, unrelated to #958 scope).

### Coverage

- `uv run pytest tests/test_delegation.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`:
  - `src/owlbear/core/delegation.py`: **100%**
  - `src/owlbear/core/deps.py`: **100%**

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Tests in `tests/test_delegation.py` define RED contract for shared dispatch-context carrier/formatter | `TestFromAC_RuntimeInstructionsKwarg`, `TestFromAC_DispatchContextFormatter`, `TestFromAC_AbsentTaskFieldsOmitted` | Yes - all AC seams are asserted directly in TestFromAC classes | COVERED |
| `_delegate()` preserves positional task and forwards `usage=`, incremented depth, and `instructions=` | `test_run_call_has_task_usage_depth_and_instructions` (line 360) | Yes - asserts task positional arg + usage identity + depth `== 1` + `instructions` kwarg presence | COVERED |
| Populated context (`workspace_root`, `channel_name`, task metadata) yields deterministic `instructions` and matching `metadata` | `test_workspace_root_in_instructions`, `test_channel_name_in_instructions`, `test_task_id_in_metadata_when_populated`, `test_task_title_in_instructions_when_populated`, `test_task_status_in_metadata_when_populated`, `test_formatting_is_deterministic` | Yes - violates on missing fields, wrong metadata keys/values, or unstable formatting | COVERED |
| Absent/unknown task fields omitted from formatted context + metadata | `test_no_task_fields_produces_no_kanban_keys_in_metadata`, `test_partial_task_fields_only_present_keys_in_metadata`, `test_absent_task_title_not_fabricated_in_instructions`, `test_workspace_root_not_in_metadata_keys`, `test_channel_name_not_in_metadata_keys` | Yes - fails on fabricated labels/metadata keys | COVERED |
| Do not modify daemon/daemon tests | Commit/file evidence: builder commit `01d0b40` touches only `src/owlbear/core/delegation.py` + `src/owlbear/core/deps.py`; test-writer commits touch only `tests/test_delegation.py` | Yes - any daemon-file touch would violate file list evidence | COVERED |

#### Security Review

- No security issues found in #958 scope. Changes add a typed context carrier (`DispatchContext`) and formatter logic only; no new file I/O, shell execution, eval/deserialization, SQL, or secret handling paths were introduced.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing `TestFromAC_*` methods from `2d6af77` | No weakening/removal by builder (`git diff --name-only 2d6af77 01d0b40 -- tests/test_delegation.py` produced no output) | PRESERVED |
| `TestFromAC_DispatchContextFormatter::test_task_status_in_instructions_when_populated` | Added in retry commit `3541768` | STRENGTHENED |
| `TestFromAC_DispatchContextFormatter::test_task_status_in_metadata_when_populated` | Added in retry commit `3541768` | STRENGTHENED |
| `TestFromAC_AbsentTaskFieldsOmitted::test_workspace_root_not_in_metadata_keys` | Added in retry commit `3541768` | STRENGTHENED |
| `TestFromAC_AbsentTaskFieldsOmitted::test_channel_name_not_in_metadata_keys` | Added in retry commit `3541768` | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact key/value assertions for metadata, explicit positional/kwarg checks for `_delegate()` call contract |
| Negative/error paths | ADEQUATE | Absent-field omission tests and existing pre-AC delegation error-path tests (missing agent, max depth, exceptions) |
| Mutation reasoning | STRONG | Removing `task_status` handling (`src/owlbear/core/delegation.py:89-91`) or omitting forwarded kwargs breaks explicit tests |
| Test independence | STRONG | Fresh deps/context per test, no shared mutable fixtures driving order-dependent outcomes |
| Descriptive names | STRONG | Test names encode scenario + expectation (forwarding contract, deterministic formatting, omitted fields) |

#### Data Safety

- No data safety issues found in #958 scope (no persistence/transaction changes, no shared-state concurrency mutation added).

#### Implementation-Aware Test Gaps

- No significant untested paths introduced by this implementation.
- Formatter branch coverage exists for task fields present/absent (`task_id`, `task_title`, `task_status`) and for non-task keys excluded from metadata.
- Delegation run-path verifies kwargs contract and depth propagation at call site (`src/owlbear/core/delegation.py:192-204`).

### Pass 2 - INFORMATIONAL

- Repo-wide `ruff` currently reports pre-existing `RUF100` debt (233 findings). Task-scoped files are clean.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add/update tests in `tests/test_delegation.py` only for dispatch-context carrier/formatter RED contract | Commits: `2d6af77` and `3541768` touch only `tests/test_delegation.py` | `TestFromAC_*` classes at lines 350, 481, 609 | PASS |
| `_delegate()` keeps positional task and passes `usage=`, incremented depth, and `instructions=` | `_delegate` run kwargs wiring at `src/owlbear/core/delegation.py:192-204`; validated by test at line 360 | `test_run_call_has_task_usage_depth_and_instructions` | PASS |
| Populated dispatch context produces deterministic instructions + matching metadata values | Formatter logic at `src/owlbear/core/delegation.py:64-93`; tests at lines 486-591 | `TestFromAC_DispatchContextFormatter` suite | PASS |
| Absent/unknown task fields omitted from instructions + metadata | Conditional metadata inclusion at `src/owlbear/core/delegation.py:81-91`; omission tests at lines 616-675 | `TestFromAC_AbsentTaskFieldsOmitted` suite | PASS |
| Do not modify daemon files/tests | Builder commit file list for `01d0b40` excludes daemon paths | N/A | PASS |

### Verdict: PASS

- Confidence: **.92**

### Action Taken

- `kanban\kanban-md.exe edit 958 --status docs --release`

[[2026-03-23]] Mon 16:33

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Add/update failing tests in tests/test_delegation.py only | Commits 2d6af77, 3541768 touch only tests/test_delegation.py; 3 TestFromAC classes exist | PASS |
| _delegate() positional task + usage= + depth + instructions= | Source delegation.py:192-204 builds run_kwargs with instructions/metadata; test at L360 asserts all 4 kwargs | PASS |
| Populated context -> deterministic instructions + matching metadata | format_dispatch_context() at delegation.py:64-93; 10 TestFromAC_DispatchContextFormatter tests cover all fields + determinism | PASS |
| Absent/unknown fields omitted from context + metadata | Conditional inclusion at delegation.py:81-91; 6 TestFromAC_AbsentTaskFieldsOmitted tests cover omission/no-fabrication | PASS |
| Do not modify daemon files | Builder commit 01d0b40 touches only delegation.py + deps.py; no daemon files | PASS |

### Test Results

- pytest full suite: 3925 passed, 88 failed (all pre-existing: numpy compat, RED tests for other tasks, bootstrap unpacking, etc.), 20 skipped
- pytest task-scoped (test_delegation.py): 39/39 passed (verified via absence from failure list)
- ruff task-scoped: All checks passed

### Architect Quality

- AC specificity: Good -- named exact file, method, kwargs, and expected behaviors
- Edge case coverage: Adequate -- reviewer caught task_status and unknown-field gaps on first pass; addressed on retry
- Design direction: Helpful architecture notes pointed to correct files and scoped away from daemon
- AC quality score: 4/5

### Commit Evidence

| Commit | Type | Files | Task |
|--------|------|-------|------|
| 2d6af77 | test (RED) | tests/test_delegation.py | #958 |
| 01d0b40 | feat (GREEN) | src/owlbear/core/delegation.py, src/owlbear/core/deps.py | #958 |
| 3541768 | test (retry) | tests/test_delegation.py | #958 |
| 16fe5f9 | docs | .github/copilot-instructions.md | #958 |

### Notes

- Uncommitted cosmetic diff in tests/test_delegation.py (paren removal, line formatting) -- no logic changes
- Reviewer evidence thorough: first pass caught genuine gaps, retry addressed them properly

### Confidence: .96

### Action: archive
