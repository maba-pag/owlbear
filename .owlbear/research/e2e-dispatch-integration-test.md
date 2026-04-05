# E2E Dispatch Integration Test — Implementation Research

> **Owning task:** #156 — Implement E2E dispatch integration test
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #156 implements the deterministic, CI-friendly integration test from the
layered architecture designed in `docs/research/e2e-dispatch-test.md` (Layer 1).
Key questions: (1) Can Typer CliRunner invoke async CLI commands that spawn
subprocesses? (2) How to inject the mock ACP agent in place of Copilot CLI?
(3) How to isolate the kanban board and audit log in tests? (4) What pytest
markers are needed?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|:---------:|
| S1 | Typer testing docs | [typer.tiangolo.com/tutorial/testing](https://typer.tiangolo.com/tutorial/testing/) | .90 |
| S2 | Click CliRunner docs | [click.palletsprojects.com/testing](https://click.palletsprojects.com/en/stable/testing/) | .90 |
| S3 | ACP SDK `test_rpc.py` — spawn roundtrip | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py) | .95 |
| S4 | OwlBear mcp-kanban `test_integration.py` | `packages/mcp-kanban/tests/test_integration.py` | .95 |
| S5 | OwlBear `process_supervisor.py` | `packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py` | .95 |
| S6 | OwlBear `acp_client.py` | `packages/orchestrator/src/owlbear_orchestrator/acp_client.py` | .95 |
| S7 | OwlBear `audit/log.py` | `packages/orchestrator/src/owlbear/audit/log.py` | .90 |
| S8 | Parent research: `e2e-dispatch-test.md` | `docs/research/e2e-dispatch-test.md` | .95 |
| S9 | OwlBear root `pyproject.toml` marker config | `pyproject.toml` | .85 |

## 3. Analysis

### 3.1 CliRunner + asyncio.run() Compatibility

| Concern | Finding | Source |
|---------|---------|--------|
| CliRunner invocation model | Synchronous — invokes CLI function in-process on same thread [S1, S2] | S1, S2 |
| CLI async pattern (#22 AC) | Commands use `asyncio.run(_async_impl())` wrapper | #22 AC |
| Nested event loop risk | `asyncio.run()` creates a new loop; fails if called from running loop | Python docs |
| **Verdict** | Tests MUST be synchronous (`def`, not `async def`) to avoid nested loop error | S1, S2 |

CliRunner works correctly because `asyncio.run()` inside the CLI command creates
and manages its own event loop. The test function itself must not be marked
`@pytest.mark.asyncio` — it must be a plain synchronous function.

### 3.2 Mock Agent Injection

| Option | Mechanism | KISS | Invasiveness |
|--------|-----------|:----:|:------------:|
| A: monkeypatch command | Patch the `command` list passed to ProcessSupervisor | High | None |
| B: env var `OWLBEAR_AGENT_CMD` | CLI reads env to override binary | Medium | Adds prod code |
| C: DI param on dispatch fn | Pass `agent_command` kwarg down | Medium | Alters API surface |

**Recommendation (.90 confidence): Option A — monkeypatch.** ProcessSupervisor
accepts `command: list[str]` in its constructor [S5]. The CLI's dispatch function
constructs this (per #22 AC). Monkeypatching the construction site to inject
`[sys.executable, str(mock_agent_py)]` is zero-invasive to production code.

The ACP SDK proves this works: `spawn_agent_process(client, sys.executable,
str(script))` spawns any Python script as an ACP agent [S3].

### 3.3 Board and Audit Isolation

| Component | Isolation approach | Proven by |
|-----------|-------------------|-----------|
| Kanban board | `tmp_path` + `config.yml` + `tasks/` + `kanban-md create` | S4 (mcp-kanban tests) |
| Audit log | `tmp_path / "audit"` + monkeypatch audit_dir | S7 (AuditLog constructor) |
| kanban-md binary | `real_kanban_bin` fixture with skip-on-missing | S4 |

The test monkeypatches kanban_dir and audit_dir to temp paths. Both `read_board()`
[S5] and `AuditLog()` [S7] accept explicit path arguments, making isolation
straightforward.

### 3.4 Marker and Configuration Gaps

| Gap | Current state | Required | Action |
|-----|--------------|----------|--------|
| `e2e` marker | Not registered in conftest.py or pyproject.toml [S9] | AC requires `@pytest.mark.e2e` | Register in pyproject.toml markers list |
| `integration` marker | Registered in pyproject.toml [S9] | AC requires `@pytest.mark.integration` | Already available |
| Marker-based exclusion | No addopts exclude for e2e | AC: "excluded from default runs" | Add to pyproject.toml or document `-m "not e2e"` |

### 3.5 Dependency Chain Timeline

| Dep | Task | Status | What #156 needs from it |
|-----|------|--------|------------------------|
| #20 | Planner umbrella | `todo` | `read_board()`, gate checks, task selector |
| #22 | CLI commands | `todo` | `owlbear dispatch` Typer command, `app` object |
| #155 | Mock ACP agent | `ideation` | `tests/fixtures/mock_acp_agent.py` script |

All three must complete before #156 can be built. #20's subtasks (#144 at backlog,
#145 and #146 at ideation) are the bottleneck — #22 and #155 both depend on #20.

## 4. Recommendation (.85 confidence)

The #156 AC is well-scoped and technically feasible. Key implementation notes
for the builder:

1. **Synchronous tests only** — no `@pytest.mark.asyncio` (CliRunner + `asyncio.run()`)
2. **Monkeypatch injection** for mock agent command (Option A)
3. **Temp board + temp audit dir** via `tmp_path` fixtures
4. **Register `e2e` marker** in `pyproject.toml` as part of this task
5. **Existing pattern** in mcp-kanban `test_integration.py` for board fixtures

**Risk:** The CLI dispatch function's internal wiring (how it constructs the
ProcessSupervisor command and passes kanban_dir/audit_dir) is not yet designed
(#22 not implemented). The monkeypatch targets will depend on #22's implementation.
Mitigation: #155 and #156 should be implemented after #22 is complete.

## 5. Follow-up Tasks

No new tasks needed — #155 (mock agent) and #156 (this task) already cover the
full scope from the parent research (`docs/research/e2e-dispatch-test.md`).

The `e2e` marker registration is a minor AC addition that belongs in #156's
scope (the test file that introduces the marker should also register it).
