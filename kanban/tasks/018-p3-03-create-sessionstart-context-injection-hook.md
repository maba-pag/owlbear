---
id: 18
title: 'P3-03: Create SessionStart context injection hook'
status: ideation
priority: medium
created: 2026-02-24T15:11:11.4147194+01:00
updated: 2026-02-26T18:52:59.5906105+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
class: standard
---

AC: Create .github/hooks/session-start-context.json. Hook fires on SessionStart event. Injects into context: (1) project purpose from copilot-instructions.md, (2) current kanban board summary via 'kanban\kanban-md.exe context'. Output via stdout as additionalContext JSON. Backing script reads copilot-instructions.md purpose section + runs kanban context command. If VS Code hooks not stable, comment out with explanation. Files: .github/hooks/session-start-context.json + backing script.
