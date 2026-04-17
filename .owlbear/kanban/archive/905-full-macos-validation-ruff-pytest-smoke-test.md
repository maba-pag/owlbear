---
id: 905
title: Full macOS validation (ruff + pytest + smoke test)
status: research
priority: critical
created: 2026-04-16T22:54:53.396876+00:00
updated: 2026-04-16T22:54:53.396876+00:00
tags:
- phase-3
- scope:platform
- type:user-action
- platform
parent: 890
depends_on:
- 901
- 902
- 903
- 904
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] `uv run ruff check .` exits 0 on macOS
- [ ] `uv run pytest` exits 0 on macOS (no test failures, no collection errors)
- [ ] All agents visible in VS Code on macOS (agent discovery works)
- [ ] At least one hook executes successfully on macOS (manual or automated smoke test)
- [ ] MCP servers start and respond on macOS (kanban, knowledge, memory)
- [ ] No .ps1 references remain anywhere in codebase: grep -r ".ps1" share/ seed/ setup/ .owlbear/hooks/ returns no results
- [ ] No powershell references remain in agent files: grep -r "powershell" share/agents/ returns no results
- [ ] Consumer workflow validated: setup/init.py seeds correctly into a fresh target on macOS

## Notes
This is the exit gate for the entire macOS compatibility feature (#890). All prior tasks must be complete before this runs. Type: type:user-action — requires physical macOS validation by the user.

## Files
- (validation only, no files changed)