---
id: 1497
title: 'Cockpit: Remove dead pdsPartialsPlugin from vite.config.ts'
status: research
priority: nice-to-have
created: 2026-05-12T02:37:04.151323+00:00
updated: 2026-05-12T02:37:12.541478+00:00
tags:
  - cockpit
  - frontend
  - cleanup
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

PDS v4 removed `getInitialStyles()` from partials (v4 migration guide, Breaking Changes → Partials). The `pdsPartialsPlugin()` in vite.config.ts calls this removed function inside a try/catch, making it a silent no-op. Remove the plugin and its invocation. See `.owlbear/research/1495-pds-v4-local-hosting.md` section 5.

## Acceptance Criteria

1. `pdsPartialsPlugin` function and its usage removed from vite.config.ts
2. `npm run build` succeeds
3. No `getInitialStyles` import or reference in codebase