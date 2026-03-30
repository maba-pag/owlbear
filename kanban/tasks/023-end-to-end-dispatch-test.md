---
id: 23
title: End-to-end dispatch test
status: todo
priority: needed
created: 2026-03-26T17:22:57.6175767+01:00
updated: 2026-03-30T08:02:48.3829699+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
depends_on:
    - 20
    - 22
    - 14
class: standard
---

## Objective

End-to-end validation test: dispatch a single task via the `owlbear dispatch` CLI, verify the agent starts autonomously, and confirm kanban board state changes and audit log entries.

## Acceptance Criteria

### Test File
- [ ] `tests/test_e2e_dispatch.py` â€” pytest test file
- [ ] All tests marked `@pytest.mark.e2e` (new marker, registered in root `conftest.py`)
- [ ] Tests skip (`pytest.skip`) when `shutil.which(copilot)` returns `None`
- [ ] Tests excluded from default `uv run pytest` (addopts or marker-based; only run via `uv run pytest -m e2e`)

### Seed Task Fixture
- [ ] Fixture creates a test task on the real kanban board via `kanban-md create` subprocess
- [ ] Task title includes a UUID4 suffix for isolation (e.g., `E2E-Test-{uuid4}`)
- [ ] Task created at `todo` status with tag `e2e-test` and body containing trivial AC
- [ ] Fixture yields the integer task ID
- [ ] Teardown deletes the seed task via `kanban-md delete <id> --yes` (runs even on failure)

### Test: dispatch completes
- [ ] Runs `owlbear dispatch <seed_task_id>` via `subprocess.run` with `timeout=300`
- [ ] Asserts exit code is 0
- [ ] Asserts stdout contains the string `Dispatched #<id> to`

### Test: kanban state changes
- [ ] After dispatch, reads task via `kanban-md show <id> --json` subprocess
- [ ] Asserts task status is no longer `todo` (agent moved it forward)
- [ ] Asserts `claimed_by` is not null (agent claimed the task during execution)

### Test: audit log written
- [ ] At least one `.jsonl` file exists under `data/audit/` after dispatch
- [ ] File contains a JSON line with `task_id: <seed_task_id>` and `type: dispatch`

### Test: repeatable execution
- [ ] Two sequential runs with distinct seed tasks both complete without interference
- [ ] Each run's seed task is independently cleaned up

### Constraints
- [ ] No modifications to production source code â€” test-only files
- [ ] Tests are idempotent: fixture teardown cleans up even on failure
- [ ] No hardcoded task IDs or session IDs

## TDD Exemption

This task IS the test (`type:test`). The deliverable is the test file itself. No separate RED-phase test task needed.

## Context

Depends on #20 (dispatch planner, `todo`), #22 (CLI trigger commands, `todo`), and #14 (mcp-kanban, `archived`). Both #20 and #22 have their own subtask pipelines in progress. Task #23 cannot be built until those deliver the `owlbear dispatch` CLI command and the planner module.

This test proves v2 is functional end-to-end: CLI entry point invokes planner gates, selects agent, spawns Copilot CLI via AcpClient/ProcessSupervisor, agent executes with MCP tools, kanban state updates, audit log records the outcome.

Test pattern follows existing integration tests:
- `packages/mcp-kanban/tests/test_integration.py` â€” real-binary subprocess tests with temp board
- `tests/test_ci_integration.py` â€” subprocess.run to test scripts
- Root `conftest.py` registers custom markers (`api`, `slow`)

[[2026-03-30]] Mon 08:02
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Create a test task on the kanban board | Vague: no method, no cleanup | Rewritten: seed fixture with kanban-md subprocess, UUID isolation, teardown delete |
| Run owlbear dispatch targeting the test task | Missing: timeout, exit code, stdout assertion | Rewritten: subprocess.run with timeout=300, exit 0, stdout pattern |
| Copilot CLI spawns, receives prompt, works on task | Untestable as stated | Replaced: verify kanban state change (status moved, claimed_by set) as proxy |
| Agent uses MCP tools during execution | Untestable from outside | Removed: implicit in kanban state verification (agent must use kanban MCP to move task) |
| Task status updates on completion | Vague: what status? | Rewritten: assert status is no longer todo after dispatch |
| Audit log records dispatch and outcome | Missing: where, what format | Rewritten: data/audit/*.jsonl contains DispatchEvent with matching task_id |
| Repeatable | Vague | Rewritten: two sequential runs with distinct seeds, independent cleanup |
| Document manual steps | Not verifiable | Moved to docs gate (writer handles) |

### Architecture Notes

**Test approach:** Subprocess-based pytest test (not imported). Tests the real CLI entry point via subprocess.run, matching the pattern in test_ci_integration.py. This validates the full stack: CLI parsing, planner gates, AcpClient spawn, agent execution, kanban updates, audit logging.

**Marker strategy:** New `@pytest.mark.e2e` marker excluded from default runs. These tests require Copilot CLI on PATH and are expensive (spawn real agent). Pattern consistent with existing `api` and `slow` markers in root conftest.py.

**Board isolation:** Tests use the real kanban board (not a temp board) because the `owlbear dispatch` CLI will wire to the project's kanban dir. Isolation via UUID task titles + fixture teardown delete. Acceptable for a validation test that runs on-demand.

**Single domain:** test-infra scope. All deliverables are test files in tests/. No production code changes.

**TDD exemption:** Task IS the test (type:test). No separate RED-phase task needed.

**Dependency readiness:** #20 (planner, todo) and #22 (CLI, todo) must complete first. depends_on correctly lists both. The planner's read_board() uses --unblocked filtering, so #23 won't be auto-dispatched until deps are met.

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| seed fixture create | kanban-md binary missing | subprocess.CalledProcessError | Yes, pytest.skip | Test skipped |
| owlbear dispatch | Copilot CLI missing | subprocess.TimeoutExpired or exit 1 | Yes, skip guard + timeout | Test skipped or fails cleanly |
| owlbear dispatch | Agent hangs indefinitely | subprocess.TimeoutExpired (300s) | Yes, timeout | Test fails with timeout message |
| seed fixture teardown | delete fails | subprocess error | Swallowed, logged | Orphan task on board (manual cleanup) |

### Changes Made
- Rewrote task body: 8 vague AC lines replaced with 18 verifiable lines grouped by concern
- Added TDD Exemption section (task IS the test)
- Added test pattern references (test_ci_integration.py, test_integration.py, conftest.py)
- Kept depends_on unchanged: [20, 22, 14]

### Dependencies
- Verified: #14 (mcp-kanban server) archived
- Verified: #20 (dispatch planner) at todo, subtasks #144/#145/#146 in pipeline
- Verified: #22 (CLI trigger commands) at todo, depends on #20 and #202
- No new dependencies needed
