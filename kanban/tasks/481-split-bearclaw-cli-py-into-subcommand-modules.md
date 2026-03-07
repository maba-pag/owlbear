---
id: 481
title: Split bearclaw/cli.py into subcommand modules
status: backlog
priority: important
created: 2026-03-04T07:37:58.8848631+01:00
updated: 2026-03-06T23:18:26.4411968+01:00
started: 2026-03-06T23:05:04.3207802+01:00
tags:
    - audit
    - refactor
    - modularity
    - scope:cli
class: standard
---

MOD-01/F-04: cli.py is 1275 lines with 8+ concern areas (auth, browser, slack, project, usage, voice, knowledge-source, chat, daemon). Split into bearclaw/commands/{auth,browser,slack,project,usage,voice,knowledge_source,chat,daemon}.py. Wire via app.add_typer(). AC: cli.py <200 lines, all commands work. See docs/software-design-audit.md, docs/code-quality-audit.md.
