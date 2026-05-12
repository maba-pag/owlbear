---
id: 1495
title: 'Cockpit: Research PDS v4 local hosting and scope CDN patch'
status: in-progress
priority: important
created: 2026-05-11T23:15:45.844267+00:00
updated: 2026-05-12T08:19:21.159794+00:00
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

## Objective
Eliminate or scope the global appendChild monkeypatch in main.tsx that redirects PDS CDN scripts to localhost.

## Acceptance Criteria
- Research: does PDS v4 support CDN_BASE_URL, partialBundling, or similar config for local hosting?
- If yes: replace monkeypatch with native config
- If no: scope the patch to only be active during PDS load() initialization, then restore original appendChild
- Document the approach and rationale

## Source
Cockpit audit 2026-05-11, Finding F16
2026-05-12T02:37:17+00:00
## Planning

Created 2 follow-up subtasks at research status:

| ID | Title | Priority | Tags |
|----|-------|----------|------|
| #1496 | Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn | important | cockpit, frontend |
| #1497 | Cockpit: Remove dead pdsPartialsPlugin from vite.config.ts | nice-to-have | cockpit, frontend, cleanup |

Both parented to #1495. No dependencies between them — they can be worked independently.
2026-05-12T02:37:53+00:00
## Research
- Research doc: .owlbear/research/1495-pds-v4-local-hosting.md
- Sources: 5 external + 2 local npm artifacts studied, 4 high-relevance
- Recommendation: Replace appendChild monkeypatch with Object.defineProperty trap on document.porscheDesignSystem.cdn (confidence: 0.80)
- Challenge: block on original "scoped appendChild" approach (0.23) — revised to property trap after challenger identified double-load timing bug, core chunk caching, and readiness boundary issues
- Follow-ups: #1496 (property trap implementation), #1497 (remove dead pdsPartialsPlugin)
- Key finding: PDS v4 has NO native self-hosting config; load() only accepts cdn: 'auto' | 'cn'
2026-05-12T08:19:21+00:00
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.