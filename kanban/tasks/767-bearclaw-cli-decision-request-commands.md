---
id: 767
title: 'BearClaw CLI: decision request commands'
status: backlog
priority: nice-to-have
created: 2026-03-13T09:31:49.4231407+01:00
updated: 2026-03-13T11:33:03.2869292+01:00
started: 2026-03-13T11:21:58.0043163+01:00
tags:
    - cli
    - process
claimed_by: researcher
claimed_at: 2026-03-13T11:33:03.2869292+01:00
class: standard
---

## Context
The decision-request process (docs/decisions/) is file-based. Add CLI convenience commands for listing and resolving decisions.

## Acceptance Criteria
- [ ] 'bearclaw decisions list'  lists pending decision requests with task ID, title, age, urgency
- [ ] 'bearclaw decisions resolve {id}'  interactive resolution flow (pick option, add notes, move file to resolved/)
- [ ] 'bearclaw decisions show {id}'  display full decision request contents
- [ ] Integration with existing Typer CLI structure

[[2026-03-13]] Fri 11:32
## Research
See docs/research/bearclaw-decision-commands.md for findings.

Key decisions:
- Manual yaml.safe_load (no python-frontmatter dep, matches agent_def.py pattern)
- Interactive resolve flow (Rich Prompt.ask + typer.prompt)
- Hardcoded docs/decisions/ path (KISS)

Follow-up tasks created:
- #777 Implement bearclaw decisions list/show/resolve commands
- #778 Tests for bearclaw decisions commands
