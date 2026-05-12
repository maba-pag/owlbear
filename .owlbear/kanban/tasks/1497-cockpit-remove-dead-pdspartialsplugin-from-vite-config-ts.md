---
id: 1497
title: 'Cockpit: Remove dead pdsPartialsPlugin from vite.config.ts'
status: backlog
priority: nice-to-have
created: 2026-05-12T02:37:04.151323+00:00
updated: 2026-05-12T14:47:19.191466+00:00
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
2026-05-12T14:47:13+00:00


## Research

- Research doc: covered by parent `.owlbear/research/1495-pds-v4-local-hosting.md` § 5
- Sources: 1 high-relevance (parent research doc + live npm verification)
- Recommendation: straight removal (confidence: 0.95)

### Verified Facts

1. PDS v4 `@porsche-design-system/components-react/partials` exports: `getComponentChunkLinks`, `getFontLinks`, `getIconLinks`, `getLoaderScript`, `getMetaTagsAndIconLinks` — no `getInitialStyles`
2. Plugin's `typeof getInitialStyles !== 'function'` guard triggers → always returns `html` unchanged
3. `createRequire` import (line 5) and `const require` (line 7) are only used by `pdsPartialsPlugin` — remove both
4. No `getInitialStyles` references anywhere else in the codebase

### Implementation Notes for Builder

Remove from `vite.config.ts`:
- Lines 5-7: `createRequire` import and `require` const
- Lines 25-42: entire `pdsPartialsPlugin()` function
- Line 46: remove `pdsPartialsPlugin()` from `plugins` array
2026-05-12T14:47:19+00:00
## Research
- Trivial dead-code cleanup — parent research (#1495) already covers rationale in § 5
- Verified live: PDS v4 partials does not export `getInitialStyles` → plugin is confirmed no-op
- `createRequire` import also orphaned by removal — noted for builder
- T1 autonomous, confidence 0.95, no follow-up tasks needed (this IS the follow-up)