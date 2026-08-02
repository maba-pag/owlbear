---
id: 156
title: Implement E2E dispatch integration test
status: archived
priority: medium
created: 2026-03-29 19:33:58.200794+02:00
updated: 2026-04-01 23:46:29.091714+02:00
started: 2026-04-01 23:46:28.473290+02:00
completed: 2026-04-01 23:46:28.473290+02:00
tags:
- phase-2
- scope:orchestrator
- type:test
depends_on:
- 155
- 146
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Integration test proving full dispatch stack: planner gates, wave assembly, AcpClient, mock ACP agent (#155), kanban board mutations, audit log. Deterministic and CI-friendly (no Copilot CLI required). Tests `orchestrate()` from `owlbear.orchestrator.loop` directly -- bypasses CLI thin layer (already unit-tested by #22).

## Acceptance Criteria

### Test file and structure

- [ ] Test file at `tests/test_dispatch_integration.py` (distinct from #23's live E2E tests at `tests/test_e2e_dispatch.py`)
- [ ] Marked `@pytest.mark.integration` and `@pytest.mark.asyncio(loop_scope="function")` (not `@pytest.mark.e2e`)
- [ ] Test functions are `async def` -- tests call `orchestrate()` directly, no CliRunner

### Fixtures and isolation

- [ ] Temp kanban board fixture via `tmp_path`: `config.yml` + `tasks/` dir + seed task at `todo` status (follow `packages/mcp-kanban/tests/test_integration.py` board_dir pattern)
- [ ] Temp audit dir fixture via `tmp_path / "audit"`, injected as `AuditLog(audit_dir)` to `orchestrate(audit_log=...)`
- [ ] `monkeypatch.setenv("KANBAN_DIR", str(board_dir))` and `monkeypatch.setenv("KANBAN_BIN", str(kanban_bin))` so mock agent subprocess inherits correct temp board paths
- [ ] Mock agent injection via `copilot_cmd=[sys.executable, str(MOCK_AGENT_PATH)]` where `MOCK_AGENT_PATH = Path("tests/fixtures/mock_acp_agent.py").resolve()`
- [ ] Skip guard: tests skip if `kanban/kanban-md.exe` binary not found (follow `real_kanban_bin` fixture pattern from mcp-kanban)

### Entry point

- [ ] Tests invoke `orchestrate(kanban_bin=..., kanban_dir=..., copilot_cmd=[...], audit_log=..., wave_size=4)` from `owlbear.orchestrator.loop` directly

### Assertions

- [ ] Assert `orchestrate()` completes without raising
- [ ] Assert seed task status changed from `todo` after orchestrate completes (mock agent calls `kanban-md move --next`)
- [ ] Assert seed task body contains "Mock agent processed" annotation (mock agent calls `kanban-md edit -a`)
- [ ] Assert audit log temp dir contains at least one `.jsonl` file with a DispatchEvent entry matching the seed task ID

### Quality

- [ ] Repeatable: passes on 2 consecutive runs with no side effects
- [ ] All tests pass: `uv run pytest tests/test_dispatch_integration.py -q --tb=short`

## Patterns to follow

- Board fixture: `packages/mcp-kanban/tests/test_integration.py` (tmp_path + config.yml + tasks/)
- Kanban binary fixture: same file, `real_kanban_bin` with skip-on-missing
- Async test style: `@pytest.mark.asyncio(loop_scope="function")` per `asyncio_mode = "strict"` in pyproject.toml
- Mock agent: `tests/fixtures/mock_acp_agent.py` reads KANBAN_DIR/KANBAN_BIN from env vars
- `orchestrate()` signature: `(kanban_bin, kanban_dir, *, copilot_cmd, client, scope, wave_size, audit_log)`

## Context

See docs/research/e2e-dispatch-integration-test.md for full research findings.
See docs/research/e2e-dispatch-test.md S3.3 (Layer 1) for design.
Depends on #20 (planner), #146 (dispatch loop with orchestrate()), and #155 (mock agent).

[[2026-03-30]] Mon 23:03
## Architecture Review (cycle 1)
**Verdict:** REFINE

Rewrote AC: 9 to 17 verifiable lines. Renamed file to test_dispatch_integration.py (conflict with #23). Removed @pytest.mark.e2e. Added monkeypatch targets, skip guard, audit dir isolation. See task git history for full cycle 1 details.

[[2026-04-01]] Tue 01:15
## Architecture Review (cycle 2)
**Verdict:** REFINE
**DR Verification:** N/A -- not research-driven (T1 test implementation)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| owlbear dispatch via CliRunner | CRITICAL: cli.py _do_dispatch() is a stub (AcpClient(None)); no ProcessSupervisor, no audit log, no mock agent injection target | Replaced with orchestrate() direct invocation |
| Sync test functions | Unnecessary: sync constraint was for CliRunner+asyncio.run() conflict; orchestrate() is async | Changed to async def with @pytest.mark.asyncio |
| Monkeypatch CLI constants | No longer needed: orchestrate() accepts kanban_bin/kanban_dir as params | Replaced with direct param injection |
| Monkeypatch _check_copilot() | No longer needed: orchestrate() doesn't check for gh CLI | Removed |
| Mock agent injection (unspecified) | RESOLVED: orchestrate() accepts copilot_cmd for ProcessSupervisor spawn | Pinned to copilot_cmd=[sys.executable, str(MOCK_AGENT_PATH)] |
| Audit log assertion | Was untestable via cli.py; now testable via orchestrate(audit_log=AuditLog(tmp)) | Kept, injection mechanism specified |
| Temp kanban board fixture | Correct, verifiable | Kept |
| Skip guard | Correct, verifiable | Kept |
| Assert task status changed | Correct, verifiable | Kept, added body annotation assertion |
| Repeatable + all tests pass | Correct, verifiable | Kept |

### Architecture Notes

CRITICAL FINDING: cli.py dispatch command is a thin stub. _do_dispatch() creates AcpClient(None) with null connection. No ProcessSupervisor, no subprocess spawn, no audit logging. Full dispatch stack exists only in loop.py orchestrate()/run_loop().

RESOLUTION: Test orchestrate() directly. Injection points: kanban_bin/kanban_dir (board isolation), copilot_cmd (mock agent), audit_log (AuditLog(tmp_path)). Mock agent env var propagation via monkeypatch.setenv().

Single domain: scope:orchestrator, type:test. TDD N/A (this IS the test task).

### Changes Made

- Rewrote AC: replaced CLI CliRunner entry point with orchestrate() direct invocation
- Changed from sync to async tests
- Pinned mock agent injection to copilot_cmd parameter
- Pinned audit log injection to audit_log parameter
- Added monkeypatch.setenv for mock agent subprocess env var propagation
- Added body annotation assertion
- Updated depends_on: removed #22 (CLI), added #146 (dispatch loop)

### Dependencies

- #155 (mock agent) archived
- #20 (planner umbrella) todo
- #146 (dispatch loop) todo/blocked (provides orchestrate())
- Removed: #22 (CLI commands)

### Challenge Results

- Challenger: block (confidence 0.35)
- Key challenges: C1 (cli.py stub), C2 (no audit in CLI), C3 (no mock injection target)
- Architect response: accepted C1/C2/C3; overrode block to REFINE -- research valid, only entry point needed correction
- Confidence in revised: .88

[[2026-04-01]] Wed 19:38
## Test-Writer Notes
- Non-implementation task (tagged type:test) -- no tests applicable.
- AC deliverables: tests/test_dispatch_integration.py
- Passing through to builder.

[[2026-04-01]] Wed 22:12
## Builder Notes
- Files changed: tests/test_dispatch_integration.py (new), models.py, loop.py
- Tests: 4 passed (TestFromAC_DispatchIntegration), 2 consecutive runs clean
- Coverage: loop.py 72%, models.py 100%
- Lint: ruff clean
- Fixes: (1) Task.tags/depends_on defaulted to [] (kanban-md omits when empty); (2) dispatch_entry cwd=None fixed to str(Path.cwd()); (3) Path moved from TYPE_CHECKING to runtime

[[2026-04-01]] Wed 22:43
## Review Evidence
See docs/scratch/156-reviewer.md for full evidence.

[[2026-04-01]] Wed 23:06
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Bug fixes only (default list fields, cwd fix); no behavior/API/convention change |
| 2 | Docstrings | Yes | Pass | Task, DispatchEntry, DispatchPlan, dispatch_entry all have accurate docstrings; no new public API added |
| 3 | docs/sources/overview.md | No | N/A | Patterns used are internal (mcp-kanban test fixtures); no external attribution needed |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/e2e-dispatch-integration-test.md exists and linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/156-coverage-run.txt
- docs/scratch/156-regression-run.txt
- docs/scratch/156-review-test-run.txt
- docs/scratch/156-reviewer.md

[[2026-04-01]] Wed 23:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at tests/test_dispatch_integration.py | File exists (226 LOC) | PASS |
| Marked @pytest.mark.integration + @pytest.mark.asyncio | All 4 tests carry both decorators (L153,166,182,198) | PASS |
| Test functions are async def | All 4 are async def | PASS |
| Temp kanban board fixture via tmp_path | board_dir fixture creates config.yml + tasks/ + seed task at todo | PASS |
| Temp audit dir fixture via tmp_path/audit | Used in _run_orchestrate helper (L123) | PASS |
| monkeypatch.setenv KANBAN_DIR and KANBAN_BIN | Present in _run_orchestrate (L121-122) | PASS |
| Mock agent injection via copilot_cmd | copilot_cmd=[sys.executable, str(MOCK_AGENT_PATH)] at L127 | PASS |
| Skip guard if kanban-md.exe not found | real_kanban_bin fixture with pytest.skip (L86-90) | PASS |
| Tests invoke orchestrate() directly | _run_orchestrate calls orchestrate(kanban_bin, kanban_dir, copilot_cmd, audit_log, wave_size=4) | PASS |
| Assert orchestrate() completes without raising | test_orchestrate_completes_without_raising (L152) | PASS |
| Assert seed task status changed from todo | test_seed_task_status_changes_from_todo (L165) | PASS |
| Assert seed task body contains Mock agent processed | test_seed_task_body_contains_mock_annotation (L181) | PASS |
| Assert audit log .jsonl with DispatchEvent | test_audit_log_contains_dispatch_event_for_seed_task (L197) | PASS |
| Repeatable: 2 consecutive runs | Builder confirmed; tmp_path isolation ensures no side effects | PASS |
| All tests pass | 4 passed in 15.97s | PASS |

### Test Results
- pytest: 4/4 passed (tests/test_dispatch_integration.py)
- ruff: All checks passed (test file + loop.py)
- Full suite: pre-existing collection error in test_tools_exclude_493.py (unrelated, #493 scope)

### AC Quality Score: 4
AC was specific (17 verifiable lines after 2 architect cycles). Builder discovered 2 runtime bugs (tags/depends_on defaults, cwd=None) not in AC, but those are runtime integration issues that AC cannot predict. Good AC overall.

### Deduction breakdown: none (all 15 AC lines verified with evidence, lint clean, AC quality 4, reviewer evidence present, no task-scope failures)
### Confidence: .98
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0651963 | test | tests/test_dispatch_integration.py, loop.py, models.py | #156 |
