---
id: 532
title: Extract error-exit pattern into CLI helper
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:37.5818336+01:00
updated: 2026-03-10T17:33:21.0005128+01:00
started: 2026-03-07T00:26:12.332562+01:00
tags:
    - audit
    - dry
    - scope:cli
depends_on:
    - 481
class: standard
---

F-19: except SomeException: typer.echo(f'Error: {exc}'); raise typer.Exit(1) pattern repeated 21 times. Extract _cli_error(msg: str) -> NoReturn helper. See docs/cli-error-exit-research.md.

Research checklist: N/A - trivial DRY extraction of 2-line error-exit pattern.

Recommendation (.90): Single _cli_error(msg) helper function. Covers both try/except and validation patterns. KISS-aligned.

AC:
- _cli_error() defined with NoReturn annotation
- Zero raw typer.Exit(code=1) in cli.py except _version_callback
- All existing CLI tests pass
- ruff clean
