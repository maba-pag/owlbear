---
id: 1494
title: 'Cockpit: Add PDS banner for mutation error feedback'
status: research
priority: needed
created: 2026-05-11T23:15:34.497443+00:00
updated: 2026-05-11T23:15:42.887752+00:00
tags:
- cockpit
- frontend
- ux
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nUse PDS banner component for persistent mutation error feedback. Keep inline validation for field-level errors.\n\n## Acceptance Criteria\n- Mutation errors (move, edit, archive, resolve) show PDS p-banner (or equivalent)\n- Errors persist until dismissed or action succeeds\n- Field-level validation stays inline\n- Errors survive tab/task navigation\n\n## Source\nCockpit audit 2026-05-11, Finding F15