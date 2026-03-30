---
id: 156
title: Implement E2E dispatch integration test
status: backlog
priority: needed
created: 2026-03-29T19:33:58.2007939+02:00
updated: 2026-03-30T08:23:42.1781454+02:00
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
Integration test proving full dispatch stack: CLI command, planner, AcpClient, mock agent, kanban board mutations.

## Acceptance Criteria
- [ ] Test file at tests/test_e2e_dispatch.py
- [ ] Temp kanban board fixture with pre-created test task
- [ ] owlbear dispatch invoked via Typer CliRunner
- [ ] Mock ACP agent spawned instead of Copilot CLI
- [ ] Assert task status changed after dispatch completes
- [ ] Assert audit log contains dispatch entry
- [ ] Marked @pytest.mark.integration and @pytest.mark.e2e
- [ ] Repeatable: passes on consecutive runs
- [ ] All tests pass with uv run pytest tests/test_e2e_dispatch.py -q --tb=short

## Context
See docs/research/e2e-dispatch-test.md S3.3 (Layer 1). Depends on #20 (planner), #22 (CLI), and #155 (mock agent).

[[2026-03-30]] Mon 08:23
## Research
See docs/research/e2e-dispatch-integration-test.md for full findings.

Key implementation notes:
- Tests MUST be synchronous (not @pytest.mark.asyncio) due to CliRunner + asyncio.run() conflict
- Use monkeypatch to inject mock agent command into ProcessSupervisor (zero prod-code changes)
- Temp board fixture follows mcp-kanban test_integration.py pattern (tmp_path + config.yml + tasks/)
- Register e2e marker in pyproject.toml as part of this task
- Audit log isolation via tmp_path audit dir (AuditLog accepts explicit path)
- All deps (#20, #22, #155) must complete first; #20 subtasks are the bottleneck
