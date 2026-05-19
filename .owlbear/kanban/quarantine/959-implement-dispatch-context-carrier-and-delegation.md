---
id: 959
title: Implement dispatch-context carrier and delegation runtime instructions
status: archived
priority: important
created: 2026-03-23T04:15:53.7466639+01:00
updated: 2026-03-23T22:29:30.1473446+01:00
started: 2026-03-23T22:29:00.9105356+01:00
completed: 2026-03-23T22:29:00.9105356+01:00
tags:
    - agent
    - scope:core
    - type:build
parent: 951
depends_on:
    - 958
class: standard
---

See docs/research/dispatched-agent-runtime-context.md. Scope: core delegation only. Current repo state already contains the shared formatter and delegated run-kwarg forwarding from #958; this task finalizes the build-half contract by making the carrier immutable and preserving the existing delegation behavior.

AC:

- Keep `DispatchContext` and `format_dispatch_context()` in `src/owlbear/core/delegation.py`; `DispatchContext` must be a frozen dataclass carrying `workspace_root`, `channel_name`, and optional `task_id`, `task_title`, and `task_status`.
- Keep `OwlBearDeps` propagation limited to one optional `dispatch_context: DispatchContext | None`; do not add raw `workspace_root`, `channel_name`, or `session` fields to `OwlBearDeps` or `OwlBearAgent`.
- Keep `DelegationToolset._delegate()` passing the delegated task as the positional prompt and forwarding `usage=`, incremented `delegation_depth`, and shared `instructions=`/`metadata=` only when `dispatch_context` is present.
- Preserve the current formatter contract: populated task fields appear deterministically in `instructions=` and `metadata=`, while absent task fields and non-task runtime fields are omitted from `metadata=`.
- Limit implementation changes to `src/owlbear/core/delegation.py` and `src/owlbear/core/deps.py`; do not modify `src/owlbear/daemon.py`, daemon-focused tests, or agent markdown definitions in this task.
- Use the existing `tests/test_delegation.py` coverage from #958 as the verification contract; no new daemon-focused work belongs here.

[[2026-03-23]] Mon 16:49

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Keep DispatchContext and format_dispatch_context in src/owlbear/core/delegation.py, with DispatchContext as a frozen dataclass carrying workspace_root, channel_name, and optional task metadata. | The repo already has the carrier, formatter, and field set, but DispatchContext is still mutable, so the remaining build delta needed to be made explicit. | Rewrote the AC to lock the implementation to a frozen carrier in the existing core seam. |
| Keep OwlBearDeps propagation limited to one optional dispatch_context runtime object. | This preserves the split from #951 and the archived #153 deps invariant. | Preserved and tightened around the existing nested runtime object. |
| Keep DelegationToolset._delegate() passing the delegated task as the positional prompt and forwarding usage, incremented delegation_depth, and shared instructions and metadata only when dispatch_context is present. | The forwarding seam already exists in src/owlbear/core/delegation.py, so the card needed a preserve-the-contract requirement instead of broad new implementation scope. | Rewrote the AC around the current run-kwargs contract. |
| Preserve the current formatter contract for populated and absent task fields. | The RED suite from #958 already locks these behaviors down. | Tightened the AC to the behaviors the existing tests verify. |
| Limit implementation changes to src/owlbear/core/delegation.py and src/owlbear/core/deps.py; no daemon, daemon-test, or agent-markdown changes. | This keeps the task in the core domain and preserves the parent split between delegation and daemon dispatch work. | Added as an explicit scope boundary. |
| Use the existing tests/test_delegation.py coverage from #958 as the verification contract. | TDD is already satisfied by archived RED task #958. | Added to keep the builder on the approved verification seam. |

### Architecture Notes

- src/owlbear/core/delegation.py already contains DispatchContext, format_dispatch_context(), and _delegate() runtime-kwarg forwarding. The meaningful gap against the original card is that DispatchContext is still declared as a mutable dataclass.
- src/owlbear/core/deps.py already keeps dispatch context as a single optional nested runtime object, which preserves the archived #153 invariant and avoids reopening raw workspace or channel or session fields on OwlBearDeps or OwlBearAgent.
- tests/test_delegation.py from #958 already locks the forwarding and formatting contract for populated and absent task fields, so this build card should preserve that tested surface instead of widening into daemon or bootstrap wiring.
- Failure mode map:

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| DispatchContext construction | Runtime dispatch context can be mutated after creation | FrozenInstanceError after the fix | Yes, by the immutability requirement | Prevents delegated runs from drifting after handoff |
| DelegationToolset._delegate() | Child run fails after kwargs assembly | Existing ToolError path | Yes, existing error handling stays unchanged | Delegated subtask returns a structured failure instead of raising |

### Changes Made

- Rewrote the task body to reflect current repo state and isolate the remaining implementation delta.
- Tightened the AC around a frozen DispatchContext carrier, the nested OwlBearDeps propagation rule, and the already-landed _delegate() run-kwarg contract.
- Preserved the existing dependency on archived RED task #958; no new tasks were created.

### Dependencies

- Verified: docs/research/dispatched-agent-runtime-context.md, src/owlbear/core/delegation.py, src/owlbear/core/deps.py, tests/test_delegation.py, and archived task #958.
- Verified: current repo state already contains the formatter and delegation forwarding seam; daemon dispatch wiring remains a separate track from this card.
- Added/Removed/Verified: no dependency changes required.

[[2026-03-23]] Mon 17:14

## Test-Writer Notes

- Test file: tests/test_dispatch_context.py
- Classes: TestFromAC_FrozenDispatchContext
- Tests per category: happy 0, edge 3, error 5, boundary 0
- Total: 8 tests, all FAIL ✓
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| DispatchContext must be a frozen dataclass (workspace_root immutable) | test_mutating_workspace_root_raises | error |
| DispatchContext must be a frozen dataclass (channel_name immutable) | test_mutating_channel_name_raises | error |
| DispatchContext must be a frozen dataclass (task_id immutable) | test_mutating_task_id_raises | error |
| DispatchContext must be a frozen dataclass (task_title immutable) | test_mutating_task_title_raises | error |
| DispatchContext must be a frozen dataclass (task_status immutable) | test_mutating_task_status_raises | error |
| Optional field cannot be set after construction (frozen) | test_setting_optional_field_from_none_raises | edge |
| Frozen dataclass must be hashable | test_instance_is_hashable | edge |
| Equal frozen instances hash equally | test_equal_instances_have_equal_hashes | edge |
- Note: formatter + delegation forwarding contract already covered by tests/test_delegation.py from #958

[[2026-03-23]] Mon 17:43

## Builder Notes

- Files changed: src/owlbear/core/delegation.py
- Change: Added frozen=True to @dataclasses.dataclass decorator on DispatchContext
- Tests: 8 passed (test_dispatch_context.py), 39 passed (test_delegation.py), 47 total
- Coverage: 100% on src/owlbear/core/delegation.py
- Lint: ruff clean
- Evidence: All 8 TestFromAC_FrozenDispatchContext tests pass; 39 delegation tests from #958 unchanged
- Fixes applied: DispatchContext was mutable - frozen=True makes fields immutable and auto-generates **hash**

[[2026-03-23]] Mon 18:22

## Review Evidence

## Review: #959 - Implement dispatch-context carrier and delegation runtime instructions

### Test Results

- `uv run pytest tests/test_dispatch_context.py -q --tb=short` -> 8 passed, 0 failed, 2 warnings (optional `qdrant_client` skips from tests/conftest.py).
- `uv run pytest tests/test_delegation.py -q --tb=short` -> 39 passed, 0 failed, 2 warnings (same optional-dependency skips).
- Combined regression run: `uv run pytest tests/test_dispatch_context.py tests/test_delegation.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> 47 passed, 0 failed.

### Lint Results

- Repo baseline: `uv run ruff check src/ tests/` -> FAIL with 216 pre-existing `RUF100` findings in unrelated test files.
- Task-scoped gate: `uv run ruff check src/owlbear/core/delegation.py src/owlbear/core/deps.py tests/test_dispatch_context.py tests/test_delegation.py` -> All checks passed.

### Coverage

- `src/owlbear/core/delegation.py`: 100%
- `src/owlbear/core/deps.py`: 100%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC line | Mapped evidence | Would fail if violated? | Verdict |
|---|---|---|---|
| Frozen `DispatchContext` carrier with required fields in `delegation.py` | `TestFromAC_FrozenDispatchContext` methods in `tests/test_dispatch_context.py` (`test_mutating_workspace_root_raises`, `test_mutating_channel_name_raises`, `test_mutating_task_id_raises`, `test_mutating_task_title_raises`, `test_mutating_task_status_raises`, `test_setting_optional_field_from_none_raises`, `test_instance_is_hashable`, `test_equal_instances_have_equal_hashes`) | Yes | COVERED |
| Keep deps propagation limited to optional `dispatch_context` field | Static boundary AC validated by source inspection: `src/owlbear/core/deps.py:34` has only `dispatch_context: DispatchContext | None`; no builder changes outside allowed file scope | Yes (source-scope violation detectable by diff/read) | COVERED |
| `_delegate()` preserves positional task + usage + depth + instructions/metadata forwarding when dispatch context exists | `TestFromAC_RuntimeInstructionsKwarg::test_run_call_has_task_usage_depth_and_instructions` and related metadata assertions in `tests/test_delegation.py` | Yes | COVERED |
| Formatter deterministic and omits absent/non-task runtime fields from metadata | `TestFromAC_DispatchContextFormatter::test_formatting_is_deterministic`; `TestFromAC_AbsentTaskFieldsOmitted::test_no_task_fields_produces_no_kanban_keys_in_metadata`, `test_workspace_root_not_in_metadata_keys`, `test_channel_name_not_in_metadata_keys` | Yes | COVERED |
| Implementation scope limited to delegation/deps; no daemon/agent-md changes | Builder commit `55bb2ff` changes only `src/owlbear/core/delegation.py` | Yes | COVERED |
| Verification contract uses existing `tests/test_delegation.py` from #958 | Independent run of `tests/test_delegation.py` passed (39/39) | Yes | COVERED |

#### Security Review

- No hardcoded secrets, injection sinks, unsafe deserialization, or new dependency risk in the builder diff.
- Builder diff is a one-line decorator change (`@dataclass` -> `@dataclass(frozen=True)`).

#### Test Integrity (TestFromAC comparison)

| Original Test Set | Builder change | Assessment |
|---|---|---|
| `tests/test_dispatch_context.py` (`TestFromAC_FrozenDispatchContext`) | No changes between `8cb6c81..55bb2ff` | PRESERVED |
| `tests/test_delegation.py` (`TestFromAC_*` classes from #958) | No changes between `8cb6c81..55bb2ff` | PRESERVED |

Evidence: `git diff --unified=0 8cb6c81..55bb2ff -- tests/test_dispatch_context.py tests/test_delegation.py` produced no diff.

#### Test Quality

- Assertion specificity: STRONG (explicit exception types, field-level immutability checks, exact metadata-key assertions).
- Negative/error-path coverage: STRONG (mutation attempts for every field + optional field set-after-init path).
- Mutation reasoning: STRONG (removing `frozen=True` breaks multiple TestFromAC checks immediately).
- Test independence: STRONG (fresh contexts/mocks in each case).
- Descriptive names: STRONG.

#### Data Safety

- No data-integrity risks identified in scope.

#### Implementation-Aware Test Gaps

- No significant untested paths for this builder delta. The implementation change is one-line (`frozen=True`) and is directly exercised by dedicated immutability/hash tests plus unchanged delegation-contract tests.

### Pass 2 - INFORMATIONAL

- Repo-wide `RUF100` debt remains outside this task scope; task-scoped files are lint-clean.

### AC Compliance

| AC line | Evidence | Status |
|---|---|---|
| Keep `DispatchContext` and `format_dispatch_context()` in `src/owlbear/core/delegation.py`; carrier is frozen with required fields | `src/owlbear/core/delegation.py:45`, `src/owlbear/core/delegation.py:46`, `src/owlbear/core/delegation.py:57`, `src/owlbear/core/delegation.py:58`, `src/owlbear/core/delegation.py:59`, `src/owlbear/core/delegation.py:60`, `src/owlbear/core/delegation.py:61`, `src/owlbear/core/delegation.py:64`; plus 8/8 TestFromAC frozen-carrier tests pass | PASS |
| Keep OwlBearDeps propagation limited to optional `dispatch_context` only; no raw workspace/channel/session fields added | `src/owlbear/core/deps.py:34`; builder commit scope shows no changes to `src/owlbear/core/agent.py` or extra deps fields | PASS |
| `_delegate()` passes positional task and forwards usage, incremented depth, and instructions/metadata only when dispatch context is present | `src/owlbear/core/delegation.py:186`, `src/owlbear/core/delegation.py:188`, `src/owlbear/core/delegation.py:192`, `src/owlbear/core/delegation.py:194`, `src/owlbear/core/delegation.py:197`, `src/owlbear/core/delegation.py:198`, `src/owlbear/core/delegation.py:199`, `src/owlbear/core/delegation.py:200`, `src/owlbear/core/delegation.py:204`; tested by `tests/test_delegation.py:360`, `tests/test_delegation.py:437` | PASS |
| Formatter contract preserved for populated vs absent fields; non-task runtime fields omitted from metadata | `src/owlbear/core/delegation.py:81`, `src/owlbear/core/delegation.py:83`, `src/owlbear/core/delegation.py:85`, `src/owlbear/core/delegation.py:87`, `src/owlbear/core/delegation.py:89`, `src/owlbear/core/delegation.py:91`; tested by `tests/test_delegation.py:541`, `tests/test_delegation.py:623`, `tests/test_delegation.py:658`, `tests/test_delegation.py:675` | PASS |
| Limit implementation to delegation/deps and do not modify daemon/daemon tests/agent markdown | `git show --name-only --pretty=format:%H%n%s 55bb2ff` lists only `src/owlbear/core/delegation.py` | PASS |
| Use existing `tests/test_delegation.py` coverage contract from #958; no daemon-focused work | `uv run pytest tests/test_delegation.py -q --tb=short` -> 39 passed; no daemon-focused file deltas in builder commit | PASS |

### Verdict

- PASS
- Confidence: .96

[[2026-03-23]] Mon 22:28

## Audit

### AC Verification

- PASS: DispatchContext is frozen dataclass with correct fields in delegation.py. Evidence: delegation.py L44 @dataclasses.dataclass(frozen=True), fields at L61-L65.
- PASS: OwlBearDeps has only dispatch_context: DispatchContext | None. Evidence: deps.py L35, no raw workspace/channel/session fields.
- PASS: _delegate() forwarding contract preserved. Evidence: 39/39 delegation tests pass unchanged from #958.
- PASS: Formatter contract preserved for populated vs absent fields. Evidence: delegation tests cover deterministic formatting, absent-fields omission, metadata keys.
- PASS: Implementation scoped to delegation.py only. Evidence: git show --name-only 55bb2ff lists only src/owlbear/core/delegation.py.
- PASS: Existing test_delegation.py from #958 used as verification contract. Evidence: 39 passed independently.

### Test Results

- Task-scoped: 47 passed (8 test_dispatch_context + 39 test_delegation), 0 failed.
- Full suite: 3963 passed, 91 failed (all pre-existing: numpy mock issues, #897 seams, knowledge module gaps). No regressions from #959.
- Ruff (task-scoped): All checks passed.

### Architect Quality

- AC specificity: Excellent. Each AC line was directly verifiable with file/line evidence.
- Edge case coverage: Complete. AC correctly scoped to remaining frozen delta with #958 providing the rest.
- Design direction: Clear, well-grounded architect notes led to a clean one-line implementation.
- AC quality score: 5/5.

### Upstream Commits

- Test-writer: 8cb6c81 test: add failing tests for frozen DispatchContext carrier (#959, test-writer)
- Builder: 55bb2ff feat: make DispatchContext a frozen dataclass (#959, builder)
- Both commits verified as correctly scoped.

### Note

- Uncommitted changes detected in tests/test_dispatch_context.py and tests/test_delegation.py (789 ins / 799 del). These are outside the builder commit scope and likely from parallel task work. All 47 task tests pass in current working tree.

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 22:29

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 5736c80 | chore | kanban/tasks/959-*.md | #959 |
