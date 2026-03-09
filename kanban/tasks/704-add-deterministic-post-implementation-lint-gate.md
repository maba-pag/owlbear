---
id: 704
title: Add deterministic post-implementation lint gate
status: in-progress
priority: important
created: 2026-03-09T05:12:23.1688036+01:00
updated: 2026-03-09T16:54:04.8760931+01:00
tags:
    - phase-research
    - scope:core
    - agent
    - tooling
class: standard
---

Add a non-LLM deterministic lint gate in the daemon poll loop that runs after builder task completion and before advancing to review. Currently ruff is run by the builder agent (LLM-decided), which can be skipped. This gate guarantees lint compliance via subprocess, not agent instruction.

See docs/research/stripe-minions-research.md S3b and S5 for rationale.

AC:
- [ ] `LintGateResult` dataclass in `src/owlbear/core/lint_gate.py`: `passed: bool`, `errors: str`, `files_checked: list[str]`
- [ ] `async run_lint_gate(workspace: Path) -> LintGateResult` function in same module:
  - Changed-files strategy: union of `git diff --name-only HEAD` (uncommitted vs HEAD) and `git diff --name-only HEAD~1 HEAD` (last commit vs parent). Filter to `.py` extensions. If union is empty, return `LintGateResult(passed=True, errors="", files_checked=[])`
  - Runs `uv run ruff check <files>` and `uv run ruff format --check <files>` as two subprocess calls
  - Returns `LintGateResult` with combined error output on any failure
  - Graceful degradation: if ruff/git binary missing (`FileNotFoundError`) or subprocess times out (10s cap), returns `passed=True` with warning log. Never blocks pipeline on infrastructure failure
  - Runs subprocess with `cwd=workspace` to scope git operations correctly
- [ ] In `daemon.py:reconcile_tasks()`, after builder task success (`exc is None`) and before `kanban_move(tid, 'review')`:
  - Add two new keyword params: `lint_gate_enabled: bool = False`, `workspace: Path | None = None`
  - Thread both through `poll_tick()` and `poll_loop()` following the existing pattern (individual params, not settings object)
  - When `lint_gate_enabled and workspace is not None`: call `await run_lint_gate(workspace)`
  - On lint failure: store lint errors in WIP (`wip_store.save`), raise `LintGateError` to trigger existing task-level retry mechanism (#625)
  - On lint pass: proceed to `kanban_move` as today
  - When `lint_gate_enabled is False` or `workspace is None`: skip gate, proceed as today
- [ ] `LintGateError(Exception)` in `src/owlbear/core/lint_gate.py`  carries lint output string for WIP context
- [ ] Config field `lint_gate_enabled: bool = Field(default=True, description='Quality gate: run ruff after builder completion. Defaults to True (quality gate, not feature flag  see architecture-standards config section).')` in `OwlBearSettings`  deliberate `default=True` because this is safety infrastructure, not an opt-in feature
- [ ] In `run_daemon()`: pass `workspace=Path.cwd()` when constructing the `poll_loop` call (no `settings.workspace` exists; `Path.cwd()` is the daemon's launch directory, which is the project workspace)
- [ ] Brief doc note in `.github/agents/builder.agent.md` mentioning daemon lint gate exists
- [ ] Tests (written by test-writer): lint pass proceeds to review, lint fail triggers retry with WIP context, ruff binary missing degrades gracefully, git unavailable degrades gracefully, config toggle disables gate, empty changeset passes, `LintGateResult` dataclass construction

[[2026-03-09]] Mon 16:35
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| LintGateResult dataclass in core/lint_gate.py | Sound. Follows SubagentVerificationHook result dataclass pattern. Module in core/ respects layering. | Keep |
| run_lint_gate(workspace) function | Prior AC had git strategy gap (only uncommitted). Refined: union of uncommitted + last commit. Graceful degradation matches AutoLintHook pattern. | Refined |
| Integration in reconcile_tasks() | Prior AC referenced settings.workspace (nonexistent) and did not specify param threading. Refined: explicit lint_gate_enabled + workspace params following existing pattern. | Refined |
| LintGateError(Exception) | Control-flow exception for retry trigger. Not a classified tool error (no need for ErrorCategory). Placement in lint_gate.py is correct. | Keep |
| Config lint_gate_enabled default=True | Architecture standards say feature flags default=False. This is a quality gate, not a feature flag. default=True is deliberate. AC documents rationale. | Keep (noted) |
| workspace from Path.cwd() in run_daemon | Prior AC said settings.workspace which does not exist. Refined to Path.cwd() in run_daemon wiring. | Refined |
| Doc note in builder.agent.md | Ancillary. Fine. | Keep |
| Tests by test-writer | Comprehensive list. Added empty-changeset-passes case. | Keep |

### Architecture Notes
**Module layering verified:** lint_gate.py in core/ imports only stdlib (subprocess, pathlib, dataclasses, logging). daemon.py (assembly layer) imports from core/. No upward deps.

**Patterns followed:**
- AutoLintHook (core/lint_hook.py): ruff subprocess execution, graceful degradation on binary missing
- SubagentVerificationHook (core/subagent_hook.py): result dataclass pattern
- Task-level retry (#625): LintGateError triggers existing retry+WIP mechanism in reconcile_tasks
- OwlBearSettings Field pattern: lint_gate_enabled alongside task_retry_max_attempts, stale_task_timeout

**Key refinements from prior REFINE:**
1. Changed-files strategy: union of uncommitted + last-commit (prevents vacuous pass when builder commits)
2. Removed nonexistent settings.workspace reference; specified Path.cwd() in run_daemon wiring
3. Explicit lint_gate_enabled + workspace params on reconcile_tasks following individual-param pattern
4. Documented default=True rationale (quality gate, not feature flag)

### Changes Made
- Rewrote task body with refined AC (8 items, all verifiable)
- Corrected git diff strategy, workspace source, parameter threading
- Moving to todo

### Dependencies
- No depends_on needed. Uses existing daemon infrastructure (#625 retry, WipStore, HookRegistry).
- TDD: test task created by test-writer during RED phase.

[[2026-03-09]] Mon 16:35
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| LintGateResult dataclass in core/lint_gate.py | Sound. Follows SubagentVerificationHook result dataclass pattern. Module in core/ respects layering. | Keep |
| run_lint_gate(workspace) function | Prior AC had git strategy gap (only uncommitted). Refined: union of uncommitted + last commit. Graceful degradation matches AutoLintHook pattern. | Refined |
| Integration in reconcile_tasks() | Prior AC referenced settings.workspace (nonexistent) and did not specify param threading. Refined: explicit lint_gate_enabled + workspace params following existing pattern. | Refined |
| LintGateError(Exception) | Control-flow exception for retry trigger. Not a classified tool error (no need for ErrorCategory). Placement in lint_gate.py is correct. | Keep |
| Config lint_gate_enabled default=True | Architecture standards say feature flags default=False. This is a quality gate, not a feature flag. default=True is deliberate. AC documents rationale. | Keep (noted) |
| workspace from Path.cwd() in run_daemon | Prior AC said settings.workspace which does not exist. Refined to Path.cwd() in run_daemon wiring. | Refined |
| Doc note in builder.agent.md | Ancillary. Fine. | Keep |
| Tests by test-writer | Comprehensive list. Added empty-changeset-passes case. | Keep |

### Architecture Notes
**Module layering verified:** lint_gate.py in core/ imports only stdlib (subprocess, pathlib, dataclasses, logging). daemon.py (assembly layer) imports from core/. No upward deps.

**Patterns followed:**
- AutoLintHook (core/lint_hook.py): ruff subprocess execution, graceful degradation on binary missing
- SubagentVerificationHook (core/subagent_hook.py): result dataclass pattern
- Task-level retry (#625): LintGateError triggers existing retry+WIP mechanism in reconcile_tasks
- OwlBearSettings Field pattern: lint_gate_enabled alongside task_retry_max_attempts, stale_task_timeout

**Key refinements from prior REFINE:**
1. Changed-files strategy: union of uncommitted + last-commit (prevents vacuous pass when builder commits)
2. Removed nonexistent settings.workspace reference; specified Path.cwd() in run_daemon wiring
3. Explicit lint_gate_enabled + workspace params on reconcile_tasks following individual-param pattern
4. Documented default=True rationale (quality gate, not feature flag)

### Changes Made
- Rewrote task body with refined AC (8 items, all verifiable)
- Corrected git diff strategy, workspace source, parameter threading
- Moving to todo

### Dependencies
- No depends_on needed. Uses existing daemon infrastructure (#625 retry, WipStore, HookRegistry).
- TDD: test task created by test-writer during RED phase.

[[2026-03-09]] Mon 16:53
## Test-Writer Notes
- Test file: tests/test_lint_gate.py
- Classes: TestFromACLintGateResult, TestFromACLintGateError, TestFromACRunLintGateHappy, TestFromACRunLintGateFailure, TestFromACRunLintGateEmptyChangeset, TestFromACRunLintGatePyFilter, TestFromACRunLintGateDedup, TestFromACRunLintGateGracefulDegradation, TestFromACRunLintGateCwd, TestFromACReconcileLintPass, TestFromACReconcileLintFail, TestFromACReconcileLintDisabled, TestFromACLintGateConfig
- Tests per category: happy 7, edge 4, error 9, boundary 11
- Total: 31 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 LintGateResult dataclass -> 4 tests (construct, fields, empty)
  AC2 run_lint_gate function -> 17 tests (happy, fail, empty, filter, dedup, graceful, cwd)
  AC3 reconcile_tasks integration -> 6 tests (lint pass, lint fail+retry+wip, disabled, none workspace, defaults)
  AC5 LintGateError exception -> 4 tests (import, carries output, subclass, raise/catch)
  AC6 Config lint_gate_enabled -> 3 tests (exists, default=True, env disable)
