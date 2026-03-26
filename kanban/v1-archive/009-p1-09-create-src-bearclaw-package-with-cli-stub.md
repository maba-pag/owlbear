---
id: 9
title: 'P1-09: Create src/bearclaw/ package with CLI stub'
status: archived
priority: high
created: 2026-02-24T15:04:52.3899502+01:00
updated: 2026-02-27T09:59:56.7074974+01:00
started: 2026-02-24T15:16:56.5940145+01:00
completed: 2026-02-27T09:59:56.7074974+01:00
tags:
    - phase-1
    - cli
depends_on:
    - 6
class: standard
---

## Acceptance Criteria
- Create src/bearclaw/__init__.py (with docstring: 'BearClaw CLI for OwlBear.', from __future__ import annotations)
- Create src/bearclaw/cli.py with:
  - Typer app instance: app = typer.Typer(name='bearclaw', help='BearClaw CLI — the command-line interface for OwlBear.')
  - version_callback that prints owlbear.__version__
  - --version option on the main app
  - 'auth' subcommand group (typer.Typer) with placeholder commands:
    - auth login: prints 'Not yet implemented — will start Copilot OAuth device flow'
    - auth status: prints 'Not yet implemented — will show token status'
  - The app.add_typer(auth_app, name='auth') wiring
- Entry point matches pyproject.toml: bearclaw = bearclaw.cli:app

## Files to Create
- src/bearclaw/__init__.py
- src/bearclaw/cli.py

## Verification
- uv run bearclaw --help prints help text with 'auth' subcommand listed
- uv run bearclaw --version prints the version
- uv run bearclaw auth --help lists login and status subcommands
- ruff check passes on both files
