---
id: 1295
title: 'Ideation: h-quality-runner structural config — project-level frontend/backend
  routing mechanism'
status: archived
priority: medium
created: 2026-05-02T16:08:21.876412+00:00
updated: 2026-05-04T21:27:38.340507+00:00
tags:
- deferred
- ideation
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: Resolved via prose fix + test-root utility (commit 0b662012). 
  Ideation determined the structural config was over-engineered; manifest-walk 
  heuristic suffices.
archival_refs: []
---

From neutral-shared-layer ideation (synthesis C6, critic finding 3). The quality-runner's path-prefix routing (serve/cockpit/web/ → Vitest) is behavioral coupling that needs project-level configuration, not just text edits. If the prose-routing approach from #1280 P2 proves insufficient, this task designs the structural config mechanism.