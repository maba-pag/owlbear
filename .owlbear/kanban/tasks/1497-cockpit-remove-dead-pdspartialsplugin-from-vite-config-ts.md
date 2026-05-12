---
id: 1497
title: 'Cockpit: Remove dead pdsPartialsPlugin from vite.config.ts'
status: review
priority: nice-to-have
created: 2026-05-12T02:37:04.151323+00:00
updated: 2026-05-12T16:56:18.282657+00:00
tags:
  - cockpit
  - frontend
  - cleanup
  - type:config
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
2026-05-12T15:33:51+00:00


Proof bundle: skip
Test-writer: SKIP
2026-05-12T15:34:05+00:00
## Architecture Review

**Verdict:** APPROVE — trivial dead-code removal, single file, no consumers, no behavioral change.

### AC Assessment

| AC | Assessment | Action |
|---|---|---|
| AC1: `pdsPartialsPlugin` function and usage removed | Target verified: lines 4-6 (`createRequire`/`require`), 25-43 (function), 46 (invocation). Implementation Notes already enumerate all removals. | Pass |
| AC2: `npm run build` succeeds | Concrete, verifiable | Pass |
| AC3: No `getInitialStyles` reference in codebase | Grep-verifiable. Only source occurrence is vite.config.ts:34. | Pass |

### Architecture Notes

- **Single responsibility** ✓ — one dead plugin, one file
- **Dependency correctness** ✓ — no deps, independent of sibling #1496 (property trap) and #1510 (asset sync)
- **KISS/YAGNI** ✓ — pure deletion, no new abstractions
- **No failure modes** — removing a confirmed no-op cannot change runtime behavior
- **Proof bundle: skip** — no testable interface; verification is `npm run build` (AC2)
- **Pass-through tag: type:config** — no testable Python/TS application code; test-writer passes through

### Challenger

Skipped per Step 2.1 — finalized proof bundle is `skip`.

### Sibling Analysis

3 siblings under #1495: #1496 (in-progress), #1497 (this), #1510 (research). No consolidation-test gap — tasks touch disjoint code surfaces.
2026-05-12T16:13:19+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Tagged `type:config`; task is pure dead-code deletion from `vite.config.ts` (no testable interface).
- Passing through to builder.
2026-05-12T16:56:18+00:00
## Builder Notes
- Implementation: removed dead `pdsPartialsPlugin` and orphaned `createRequire` usage from `serve/cockpit/web/vite.config.ts`.
- Files changed: `serve/cockpit/web/vite.config.ts`
- Proof bundle handling: `skip` (no `TestFromAC_*` gate required).
- Verification:
  - `npm run build` (in `serve/cockpit/web`) passed.
  - `rg -n "getInitialStyles" .` (repo root) returned no matches.
- Commit:
  - `acb876652bb9197adcbe5f2457fbb869bccde45d`
  - `1 file changed, 1 insertion(+), 24 deletions(-)`
- Evidence summary: AC1 satisfied by removal of function + invocation; AC2 satisfied by successful build; AC3 satisfied by zero codebase references.