---
id: 156
title: Implement E2E dispatch integration test
status: backlog
priority: needed
created: 2026-03-29T19:33:58.2007939+02:00
updated: 2026-03-30T23:03:54.722081+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
depends_on:
    - 20
    - 22
    - 155
class: standard
---

## Objective
Integration test proving full dispatch stack: CLI command, planner gates, AcpClient, mock ACP agent (#155), kanban board mutations, audit log. Deterministic and CI-friendly (no Copilot CLI required).

## Acceptance Criteria

### Test file and structure
- [ ] Test file at `tests/test_dispatch_integration.py` (distinct from #23's live E2E tests at `tests/test_e2e_dispatch.py`)
- [ ] Marked `@pytest.mark.integration` ONLY (not `@pytest.mark.e2e` â€” this test uses mock agent, does not require Copilot CLI)
- [ ] All test functions are synchronous `def` (not `async def`) â€” CliRunner invokes `asyncio.run()` internally, nested event loops crash (see research S3.1)

### Fixtures and isolation
- [ ] Temp kanban board fixture via `tmp_path`: `config.yml` + `tasks/` dir + seed task at `todo` status (follow `packages/mcp-kanban/tests/test_integration.py` pattern)
- [ ] Temp audit dir fixture via `tmp_path / audit`
- [ ] Monkeypatch board paths: CLI module-level `_KANBAN_BIN` and `_KANBAN_DIR` pointed to temp board
- [ ] Monkeypatch Copilot check: bypass `_check_copilot()` so tests run without `gh` on PATH
- [ ] Mock agent injection: patch the agent command construction so `tests/fixtures/mock_acp_agent.py` (#155) is spawned instead of Copilot CLI (exact patch target depends on #146 dispatch loop wiring)
- [ ] Audit log dir patched to temp path so assertions read from isolated dir
- [ ] Skip guard: tests skip if `kanban/kanban-md.exe` binary not found

### Command invocation
- [ ] `owlbear dispatch <id>` invoked via Typer `CliRunner` (in-process, not subprocess)

### Assertions
- [ ] Assert exit code 0 on successful dispatch
- [ ] Assert stdout contains `Dispatched #<id> to <agent>` confirmation string
- [ ] Assert task status changed from `todo` after dispatch completes (mock agent advances the task via kanban-md)
- [ ] Assert audit log temp dir contains a dispatch event entry with matching task ID

### Quality
- [ ] Repeatable: passes on 2 consecutive runs with no side effects
- [ ] All tests pass: `uv run pytest tests/test_dispatch_integration.py -q --tb=short`

## Context
See docs/research/e2e-dispatch-integration-test.md for full research findings.
See docs/research/e2e-dispatch-test.md S3.3 (Layer 1) for design.
Depends on #20 (planner), #22 (CLI), and #155 (mock agent).
Transitively depends on #146 (dispatch loop) via #20 â€” by the time this task is built, the dispatch loop must be wired and audit log integration complete.

Note: `e2e` marker is already registered in pyproject.toml (line 26) â€” no pyproject.toml changes needed for this task.

[[2026-03-30]] Mon 23:03
## Architecture Review
**Verdict:** REFINE

### AC Assessment

- Test file at tests/test_e2e_dispatch.py: CONFLICT with #23 live E2E file. Renamed to tests/test_dispatch_integration.py
- Temp kanban board fixture: Good intent, lacked specificity. Added tmp_path pattern details.
- owlbear dispatch via CliRunner: Correct, verifiable. Kept.
- Mock ACP agent spawned: Correct but injection point unspecified. Added monkeypatch target guidance.
- Assert task status changed: Verifiable. Kept.
- Assert audit log contains dispatch entry: Depends on #146 (transitive via #20). Kept with note.
- @pytest.mark.integration AND e2e: CONTRADICTION (e2e requires Copilot, test uses mock). Removed e2e.
- Repeatable: Verifiable. Kept.
- All tests pass command: Updated file path after rename.
- Register e2e marker: Already at pyproject.toml line 26. Removed from scope.

### Architecture Notes

File conflict resolved: tests/test_e2e_dispatch.py is #23 live E2E (7 tests, real Copilot + real board). #156 is CI-friendly integration test (mock agent + temp board). Separate files mandatory.

Monkeypatch targets from codebase analysis:
- owlbear.cli._KANBAN_BIN and _KANBAN_DIR: module-level Path constants for board isolation
- owlbear.cli._check_copilot: bypass gh/Copilot check
- Agent command: depends on #146 orchestrate() wiring (copilot_cmd param injectable)
- AuditLog: constructor accepts explicit audit_dir Path

Pattern compliance:
- Board fixture: packages/mcp-kanban/tests/test_integration.py (tmp_path + config.yml + tasks/)
- CliRunner: tests/test_cli.py (_SeparatedCliRunner for Click 8.2+)
- Sync tests: research S3.1 (CliRunner + asyncio.run() conflict)

Single domain: scope:orchestrator, type:test. TDD N/A (this IS the test task).

### Changes Made

- Rewrote AC: 9 lines to 17 verifiable lines grouped by category
- Renamed test file to test_dispatch_integration.py (conflict avoidance)
- Removed @pytest.mark.e2e (contradicts mock approach)
- Added monkeypatch isolation targets based on actual CLI code
- Added skip guard, audit dir isolation, sync-only constraint

### Dependencies

- #155 (mock agent) archived (done)
- #20 (planner umbrella) review (in pipeline)
- #22 (CLI commands) review (in pipeline)
- #146 (dispatch loop) todo, transitive via #20. Audit log depends on this.
