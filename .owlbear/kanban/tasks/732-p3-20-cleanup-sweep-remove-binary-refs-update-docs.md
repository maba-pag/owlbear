---
id: 732
title: 'P3-20: Cleanup sweep — remove binary refs, update docs/guides/skills/setup'
status: backlog
priority: needed
created: 2026-04-09T03:29:09.5970795+02:00
updated: 2026-04-09T03:29:09.5970795+02:00
tags:
    - kanban
    - phase-3
    - type:docs
    - docs
parent: 712
depends_on:
    - 730
class: standard
---

## Objective
Remove all kanban-md binary references and update documentation for native engine.

Brief: see parent #712 — Phase 3: Cleanup sweep

## AC
- [ ] `.owlbear/kanban/setup.ps1` removed (binary download script)
- [ ] `seed/.owlbear/kanban/setup.ps1` removed from seed template
- [ ] `setup/setup-guide.md` updated (remove binary setup steps, uv sync is only step)
- [ ] `setup/sharing-guide.md` updated if it references binary
- [ ] `.owlbear/kanban/README.md` updated (remove binary references)
- [ ] `share/skills/h-mcp-kanban/SKILL.md` updated (remove binary references)
- [ ] `share/skills/w-retro/SKILL.md` updated if it references binary
- [ ] KANBAN_BIN env var handling removed from server.py if not already done in #730
- [ ] No remaining references to kanban-md binary in runtime code (grep verification)

## Files
- Multiple files (see AC for complete list)
