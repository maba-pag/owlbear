---
id: 104
title: Create bearclaw usage CLI command
status: archived
priority: medium
created: 2026-02-27T03:21:05.3113567+01:00
updated: 2026-02-27T13:21:36.6951306+01:00
started: 2026-02-27T03:32:46.946924+01:00
completed: 2026-02-27T13:21:36.6951306+01:00
tags:
    - observability
    - cli
    - phase-3
depends_on:
    - 100
class: standard
---

Add 'bearclaw usage' Typer subcommand for viewing token usage and cost stats. Follows existing CLI pattern (auth_app, browser_app, slack_app).

## Acceptance Criteria

- [ ] `usage_app = typer.Typer(name='usage', help='View token usage and cost statistics.', no_args_is_help=True)` registered via `app.add_typer(usage_app)` in `src/bearclaw/cli.py`
- [ ] `bearclaw usage show` command (default subcommand) with mutually exclusive time-window options:
  - `--last-hour`: filter to records from last 1 hour
  - `--last-24h` (default when no flag): filter to last 24 hours
  - `--last-7d`: filter to last 7 days
  - `--all`: show all records
- [ ] Tabular output columns: Model, Requests, Input Tokens, Output Tokens, Total Tokens, Est. Cost (USD)
- [ ] When provider == 'copilot' and premium_requests data present: additional Premium Requests column
- [ ] Summary row at bottom with totals across all models
- [ ] Empty usage log: prints 'No usage data found for the selected time window.' (informative, not error/traceback)
- [ ] Reads from `OwlBearSettings().usage_path` (configured in #100)
- [ ] Instantiates `UsageTracker(path)` and calls `summary()` / `query()`
- [ ] No inline test code — tests are in #105 (test_usage_cli.py)

Depends on: #100 (UsageTracker must exist to read data)
See docs/token-usage-tracking-research.md section 3.6
