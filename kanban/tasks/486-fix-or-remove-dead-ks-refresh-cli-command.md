---
id: 486
title: Fix or remove dead ks_refresh CLI command
status: archived
priority: important
created: 2026-03-04T07:38:02.9004356+01:00
updated: 2026-03-07T18:07:54.8538445+01:00
started: 2026-03-06T19:39:18.1536294+01:00
completed: 2026-03-07T18:07:54.8538445+01:00
tags:
    - audit
    - yagni
    - scope:cli
class: standard
---

## Acceptance Criteria

Remove the dead `ks_refresh` CLI command. `RefreshOrchestrator` itself stays (daemon-only, used by `KnowledgeSourceToolset`).

### Deletions in `src/bearclaw/cli.py`

- [ ] Delete `_make_refresh_orchestrator()` factory (L370-389, ~20 LOC)
- [ ] Delete `ks_refresh()` CLI command (L521-559, ~39 LOC including `@knowledge_source_app.command(refresh)` decorator)
- [ ] Remove `from owlbear.memory.knowledge.refresh import RefreshOrchestrator` from the `TYPE_CHECKING` block (L46)

### Deletions in `tests/test_cli_knowledge_source.py`

- [ ] Delete entire `TestKnowledgeSourceRefresh` class (L381-462, 4 test methods) and the `# refresh` section comment
- [ ] Remove any now-unused imports (`AsyncMock` if no other test uses it)

### Documentation updates (docs gate)

- [ ] `README.md` L44: remove `bearclaw knowledge-source refresh --name N | --all` line
- [ ] `.github/copilot-instructions.md` Knowledge row: change `add/list/show/refresh/remove` to `add/list/show/remove`

### Verification

- [ ] `uv run pytest tests/test_cli_knowledge_source.py -q --tb=short` passes (remaining add/list/show/remove tests unaffected)
- [ ] `uv run ruff check src/bearclaw/cli.py tests/test_cli_knowledge_source.py` clean
- [ ] `bearclaw knowledge-source --help` no longer shows `refresh` subcommand
- [ ] No production code references `_make_refresh_orchestrator`

### What stays

- `owlbear.memory.knowledge.refresh.RefreshOrchestrator` (used by daemon via `KnowledgeSourceToolset`)
- `owlbear.tools.knowledge_source.KnowledgeSourceToolset.refresh_source` (agent-facing)
- All non-refresh tests in `test_cli_knowledge_source.py`
