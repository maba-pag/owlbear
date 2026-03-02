---
id: 431
title: Test CLI bearclaw knowledge source subcommands
status: archived
priority: important
created: 2026-03-02T01:51:33.9298056+01:00
updated: 2026-03-02T09:15:33.5516243+01:00
started: 2026-03-02T01:51:39.1772885+01:00
completed: 2026-03-02T09:15:33.5516243+01:00
tags:
    - phase-9
    - cli
    - knowledge-graph
    - test
class: standard
---

TDD red-phase for #385. Tests for bearclaw knowledge source CLI subcommands.

## Acceptance Criteria
- knowledge_source_app is a Typer subgroup registered on app via app.add_typer
- 'add' command: --name (required), --type (required, choices: url_list/crawl/file_glob), --urls (for url_list), --seeds (for crawl), --pattern (for file_glob), --scope (default global)
- 'add' creates a KnowledgeSource via KnowledgeSourceStore
- 'list' command: optional --scope filter, prints table with name/type/scope/enabled/last_refreshed_at
- 'show' command: positional name arg, prints full source details including config JSON
- 'refresh' command: --name for single source, --all for all enabled, invokes RefreshOrchestrator
- 'remove' command: positional name arg, deletes source from registry
- Error handling: non-existent name prints error + exit code 1
- All tests use CliRunner (typer.testing) with mocked store/orchestrator
- Follows existing CLI pattern from project_app subcommands

Depends on #428 (test #382), #430 (test #384)
