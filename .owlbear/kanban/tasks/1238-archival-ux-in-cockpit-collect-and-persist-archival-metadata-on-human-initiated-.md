---
id: 1238
title: Archival UX in Cockpit — collect and persist archival metadata on
  human-initiated archive
status: todo
priority: important
created: 2026-05-01T03:04:34.449352+00:00
updated: 2026-05-01T03:11:20.232562+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Summary

Extend the Cockpit `→ archived` flow to collect and persist `archival_reason` and
`archival_refs`. Currently every human-initiated archive lands with
`archival_reason=None` / `archival_refs=[]`, breaking downstream dependency resolution.

**Scope:** `existing-feature/refactor` — engine and cockpit view are complete.
Gaps: `MoveRequest`, move route, `CockpitView.move_task` (no validation block), and
frontend (`handleTransitionClick`, new `ArchivalModal` component).

## Brief

See `.owlbear/briefs/draft-archival-ux/brief.md` for the full specification including
backend changes (B1–B3), frontend changes (F1–F3), acceptance criteria, out-of-scope
boundaries, and known limitations.

[[2026-05-01]]
## Planning

**8 subtasks created** across 2 domains (backend + frontend), 3 dependency layers.

| ID | Title | Priority | Deps | Tags |
|----|-------|----------|------|------|
| #1239 | Test: MoveRequest archival fields and route pass-through | needed | — | scope:backend |
| #1240 | Test: CockpitView archival validation block | needed | — | scope:backend |
| #1241 | Test: ArchivalModal component | needed | — | scope:frontend |
| #1242 | Test: handleTransitionClick archive intercept | needed | — | scope:frontend |
| #1243 | Implement: MoveRequest archival fields and route pass-through | needed | #1239 | scope:backend |
| #1244 | Implement: CockpitView archival validation block | important | #1240, #1243 | scope:backend |
| #1245 | Implement: ArchivalModal component and ARCHIVAL_REASONS constant | needed | #1241 | scope:frontend |
| #1246 | Implement: handleTransitionClick archive intercept | important | #1242, #1245 | scope:frontend |

**Dependency layers:**
- Layer 1 (parallel): #1239, #1240, #1241, #1242 (all test tasks, no deps)
- Layer 2 (parallel): #1243 (after #1239), #1245 (after #1241)
- Layer 3 (parallel): #1244 (after #1240 + #1243), #1246 (after #1242 + #1245)

Backend and frontend tracks are independent — can run concurrently after layer 1.

**Decomposition notes:**
- B1+B2 paired (#1239/#1243): simple and tightly coupled, no justification for a split
- B3 owns its own pair (#1240/#1244): 10+ validation cases, the most complex backend task
- F1+F2 paired (#1241/#1245): ARCHIVAL_REASONS is a dependency of ArchivalModal, trivial to co-locate
- F3 owns its own pair (#1242/#1246): depends on ArchivalModal existing
