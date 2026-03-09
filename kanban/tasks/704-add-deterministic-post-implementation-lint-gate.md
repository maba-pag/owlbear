---
id: 704
title: Add deterministic post-implementation lint gate
status: backlog
priority: important
created: 2026-03-09T05:12:23.1688036+01:00
updated: 2026-03-09T15:36:12.1688789+01:00
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
  - Discovers changed `.py` files via `git diff --name-only HEAD` in *workspace*
  - Runs `uv run ruff check <files>` and `uv run ruff format --check <files>`
  - Returns `LintGateResult` with combined error output on any failure
  - Graceful degradation: if ruff/git binary missing or subprocess times out (10s cap), returns `passed=True` with warning log (never blocks the pipeline on infrastructure failure)
- [ ] In `daemon.py:reconcile_tasks()`, after builder task success (`exc is None`) and before `kanban_move(tid, 'review')`:
  - When `settings.lint_gate_enabled` is True, call `run_lint_gate(workspace)`
  - On lint failure: store lint errors in WIP (`wip_store.save`), raise a `LintGateError` to trigger the existing task-level retry mechanism (#625)
  - On lint pass: proceed to `kanban_move` as today
- [ ] `LintGateError(Exception)` in `src/owlbear/core/lint_gate.py`  carries lint output for WIP context
- [ ] Config field `lint_gate_enabled: bool = Field(default=True, description='...')` in `OwlBearSettings`
- [ ] `workspace` parameter threaded through `reconcile_tasks()` (from `settings.workspace` or `Path.cwd()`)
- [ ] Brief doc note in `.github/agents/builder.agent.md` mentioning daemon lint gate exists
- [ ] Tests (written by test-writer): lint pass proceeds to review, lint fail triggers retry with WIP context, ruff binary missing degrades gracefully, git unavailable degrades gracefully, config toggle disables gate, `LintGateResult` dataclass construction

[[2026-03-09]] Mon 15:36
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Define a deterministic lint check in the orchestrator pipeline | Correct intent, wrong location name. Goes in daemon.py:reconcile_tasks(), not VS Code orchestrator agent (no terminal tools). | Rewrite |
| Lint step runs ruff check + ruff format --check on changed files | 'Changed files' needs precision: .py files from git diff --name-only HEAD. | Rewrite |
| On lint failure: auto-retry builder with lint errors as context | Sound. Maps to existing task-level retry (#625). Lint errors stored in WIP. | Keep (clarify) |
| On lint pass: proceed to reviewer dispatch | Correct. Existing kanban_move(tid, 'review'). | Keep |
| Document in orchestrator.agent.md and builder.agent.md | Fine as sub-AC. | Keep |

### Architecture Notes
**Insertion point:** daemon.py:reconcile_tasks() ~line 555, between builder success and kanban_move(tid, 'review').

**Design: standalone function, not a hook.** HookRegistry is observational (fire-and-forget). Lint gate needs blocking pass/fail semantics. Direct async function call is simpler.

**Patterns to follow:** AutoLintHook (ruff subprocess), SubagentVerificationHook (result dataclass), task-level retry (#625), OwlBearSettings bool Field pattern.

**Changed-files strategy:** git diff --name-only HEAD filtered to .py. Graceful degradation if git unavailable.

### Changes Made
- Refined AC: specified file location, interface contract, insertion point, graceful degradation, config field
- Retained daemon scope (scope:core), removed misleading orchestrator-pipeline framing

### Dependencies
- No depends_on needed. Uses existing daemon infrastructure.
- TDD: test task will be created by test-writer during RED phase.
