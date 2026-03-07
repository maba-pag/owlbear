---
id: 630
title: Replace hand-rolled CLI tables with rich.table.Table
status: archived
priority: needed
created: 2026-03-07T05:26:51.686309+01:00
updated: 2026-03-07T18:08:26.7111212+01:00
started: 2026-03-07T05:49:32.2602341+01:00
completed: 2026-03-07T18:08:26.7111212+01:00
tags:
    - phase-cli
    - scope:cli
    - cli
class: standard
---

Replace _print_usage_table() and project_list/ks_list hand-rolled column formatting with rich.table.Table. Rich is already installed (transitive dep of Typer, logfire, etc.  zero new deps). Supersedes #520 (extract _print_table helper), which should be closed.

See docs/rich-table-cli-research.md for full analysis.

AC:
- [ ] project_list() renders via rich.table.Table with columns: Name, Workspace, Last Active, Status
- [ ] ks_list() renders via rich.table.Table with columns: Name, Type, Scope, Enabled, Last Refreshed
- [ ] _print_usage_table() renders via rich.table.Table with dynamic Premium column; table.add_section() before TOTAL row
- [ ] Console() created inside each command function (not module-level)  required for CliRunner stdout capture
- [ ] All hand-rolled col_widths/fmt/separator code removed from the 3 call-sites
- [ ] Existing test assertions in test_cli_project.py, test_cli_knowledge_source.py, test_usage_cli.py pass unchanged
- [ ] ruff clean

Patterns:
- Inline Console() per call-site (no module-level console, no shared factory  YAGNI for 3 sites)
- Use console.print(table) not rich.print(table) (avoids default Console caching)
- table.add_section() for usage totals separator (replaces hand-rolled second separator line)

Files to modify: src/bearclaw/cli.py (only)
