---
id: 560
title: Rename ks_ CLI functions to full knowledge_source_ prefix
status: archived
priority: someday
created: 2026-03-04T07:39:03.1672553+01:00
updated: 2026-03-22T19:20:08.7806575+01:00
started: 2026-03-07T02:20:42.6453801+01:00
completed: 2026-03-22T19:20:08.7806575+01:00
tags:
    - audit
    - naming
    - scope:cli
blocked: true
block_reason: Already implemented in repo and git history; task text targets a pre-split CLI layout and must not re-enter builder flow.
class: standard
---

## Research Findings

See docs/research/ks-rename.md. Rename confirmed as correct approach (.85 confidence).

### Scope

- 4 function renames in src/bearclaw/cli.py (internal Python names only)
- CLI command names unchanged (users still type `bearclaw knowledge-source add`)
- Zero test changes expected (tests invoke via CLI string, not function name)
- Interacts with #481 (CLI split) but no blocking dependency

## Acceptance Criteria

- [ ] Rename ks_add -> knowledge_source_add
- [ ] Rename ks_list -> knowledge_source_list
- [ ] Rename ks_show -> knowledge_source_show
- [ ] Rename ks_remove -> knowledge_source_remove
- [ ] CLI command names unchanged (add, list, show, remove)
- [ ] All tests pass (no test changes expected)
- [ ] ruff clean
- [ ] Update docs/code-quality-audit.md F-17 as resolved

[[2026-03-21]] Sat 13:10
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Rename ks_add -> knowledge_source_add | Already satisfied in src/bearclaw/commands/knowledge_source.py after the archived CLI split; the original src/bearclaw/cli.py scope is stale. | Do not route to builder. |
| Rename ks_list -> knowledge_source_list | Already satisfied in src/bearclaw/commands/knowledge_source.py after the archived CLI split; the original src/bearclaw/cli.py scope is stale. | Do not route to builder. |
| Rename ks_show -> knowledge_source_show | Already satisfied in src/bearclaw/commands/knowledge_source.py after the archived CLI split; the original src/bearclaw/cli.py scope is stale. | Do not route to builder. |
| Rename ks_remove -> knowledge_source_remove | Already satisfied in src/bearclaw/commands/knowledge_source.py after the archived CLI split; the original src/bearclaw/cli.py scope is stale. | Do not route to builder. |
| CLI command names unchanged (add, list, show, remove) | Already satisfied via @app.command(add), @app.command(list), @app.command(show), and @app.command(remove) in the same module. | Verified as shipped. |
| All tests pass (no test changes expected) | Stale as written: the repo already contains a dedicated rename contract in tests/test_knowledge_source_rename.py, so this is not a no-test-change implementation card anymore. | Treat as already delivered, not pending GREEN work. |
| ruff clean | Standard quality gate, but there is no remaining implementation scope to send through the builder pipeline. | No builder work remains. |
| Update docs/code-quality-audit.md F-17 as resolved | Already satisfied; docs/code-quality-audit.md already marks F-17 resolved for #560. | Verified as shipped. |

### Architecture Notes
- Archived task #481 split the CLI into command modules, so this task's research/body reference to src/bearclaw/cli.py is stale against the current codebase.
- Current code already exports knowledge_source_add, knowledge_source_list, knowledge_source_show, and knowledge_source_remove in src/bearclaw/commands/knowledge_source.py.
- Current repo already contains a task-scoped regression contract in tests/test_knowledge_source_rename.py.
- Git history confirms #560 already landed: cd54025 (builder rename) and 9c2a532 (rename contract tests).
- No new failure-mode map is needed because this card should not introduce or modify codepaths; it is stale board state, not valid implementation scope.

### Changes Made
- Appended architecture review with current-repo and git-history evidence.
- Routed the task out of backlog to prevent duplicate implementation.

### Dependencies
- Verified: archived #481 moved the commands into src/bearclaw/commands/knowledge_source.py.
- Verified: tests/test_knowledge_source_rename.py already carries the executable contract for #560.
- Verified: docs/code-quality-audit.md already marks F-17 resolved for #560.
