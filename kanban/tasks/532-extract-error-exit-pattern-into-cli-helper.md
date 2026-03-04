---
id: 532
title: Extract error-exit pattern into CLI helper
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:37.5818336+01:00
updated: 2026-03-04T07:38:37.5818336+01:00
tags:
    - audit
    - dry
    - scope:cli
class: standard
---

F-19: except SomeException: typer.echo(f'Error: {exc}'); raise typer.Exit(1) pattern repeated 15+ times. Extract _exit_on_error(exc) helper or decorator. AC: no duplicated error-exit blocks. See docs/code-quality-audit.md.
