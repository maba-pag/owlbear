---
id: 1495
title: 'Cockpit: Research PDS v4 local hosting and scope CDN patch'
status: research
priority: important
created: 2026-05-11T23:15:45.844267+00:00
updated: 2026-05-11T23:15:58.157078+00:00
tags:
- cockpit
- frontend
- research
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nEliminate or scope the global appendChild monkeypatch in main.tsx that redirects PDS CDN scripts to localhost.\n\n## Acceptance Criteria\n- Research: does PDS v4 support CDN_BASE_URL, partialBundling, or similar config for local hosting?\n- If yes: replace monkeypatch with native config\n- If no: scope the patch to only be active during PDS load() initialization, then restore original appendChild\n- Document the approach and rationale\n\n## Source\nCockpit audit 2026-05-11, Finding F16