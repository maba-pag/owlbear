---
id: 1491
title: 'Cockpit: Extract CockpitProvider from Shell.tsx'
status: research
priority: important
created: 2026-05-11T23:14:53.705441+00:00
updated: 2026-05-11T23:15:04.616597+00:00
tags:
- cockpit
- frontend
- refactor
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nExtract all state management from Shell.tsx into a CockpitProvider context.\n\n## Acceptance Criteria\n- Shell.tsx becomes ~60 LOC layout-only (CSS grid + component composition)\n- CockpitProvider (~150 LOC) owns: board/tasks state, selected task lifecycle, DR state, cross-domain effects\n- Children consume via hooks: useBoardState(), useTaskSelection(), useDRState()\n- No prop drilling through Shell\n- Also fold in F10 (useSSERefetch extraction) and F11 (inline useConnectionHealth)\n\n## Source\nCockpit audit 2026-05-11, Finding F1 (+ F10, F11)