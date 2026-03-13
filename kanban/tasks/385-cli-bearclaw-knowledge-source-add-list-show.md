---
id: 385
title: 'CLI: bearclaw knowledge source add/list/show/refresh/remove'
status: archived
priority: important
created: 2026-03-01T20:15:20.217962+01:00
updated: 2026-03-02T09:14:50.6040209+01:00
started: 2026-03-01T20:23:04.4517185+01:00
completed: 2026-03-02T09:14:50.6040209+01:00
tags:
    - phase-9
    - cli
    - knowledge-graph
depends_on:
    - 431
class: standard
---

From #254 source-registry.md. Typer CLI subcommands for managing knowledge sources.

## Location
- src/bearclaw/cli.py: knowledge_source_app Typer group, registered via app.add_typer
- Follows existing project_app pattern (subcommand group with helper functions)

## Acceptance Criteria
- knowledge_source_app = typer.Typer(name='knowledge-source', help='Manage knowledge sources.', no_args_is_help=True)
- Registered via app.add_typer(knowledge_source_app) under 'bearclaw knowledge-source' namespace
- 'add' command: --name (str, required), --type (str, required: url_list|crawl|file_glob), --urls (str, comma-separated, for url_list), --seeds (str, comma-separated, for crawl), --pattern (str, for file_glob), --scope (str, default 'global'), --max-depth (int, default 1, for crawl), --max-pages (int, default 50, for crawl)
- 'add' validates type-specific options: url_list requires --urls, crawl requires --seeds, file_glob requires --pattern
- 'add' builds config dict from type-specific flags, creates KnowledgeSource via store, echoes confirmation
- 'list' command: optional --scope filter, prints table: Name | Type | Scope | Enabled | Last Refreshed
- 'show' command: positional name argument, prints full source details (name, type, scope, enabled, priority, config JSON, last_refreshed_at, last_error, created_at)
- 'show' with non-existent name: echoes error + exit code 1
- 'refresh' command: --name for single source, --all flag for all enabled sources, invokes RefreshOrchestrator, prints summary
- 'refresh' requires exactly one of --name or --all (mutually exclusive)
- 'remove' command: positional name argument, deletes source, echoes confirmation
- 'remove' with non-existent name: echoes error + exit code 1
- Helper _get_source_store() returns KnowledgeSourceStore (follows _get_project_store pattern)

Depends on test task #431, #382, #384.
