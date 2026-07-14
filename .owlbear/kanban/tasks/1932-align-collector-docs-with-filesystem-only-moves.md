---
id: 1932
title: Keep collector commit guidance procedural
status: verify
priority: high
created: 2026-07-14T02:40:32.435475+02:00
updated: 2026-07-14T04:05:08.615388+02:00
tags:
  - agent
  - docs
  - type:docs
parent:
depends_on: []
ac:
  - Collector commits both task and archive paths
  - Pre-staged owned paths remain untouched and route to COMMIT_FAILED
  - Obsolete recovery and implementation-history prose is absent
  - Focused assertions guard durable guidance
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Keep collector commit guidance procedural, concise, and independent of Kanban move implementation details.

## Acceptance Criteria
- Collector guidance requires both the old task path and new archive path in the scoped commit.
- An already-staged owned path is left untouched and routes to `COMMIT_FAILED` containment.
- Obsolete archive-move recovery and implementation-history prose is absent from the skills.
- Focused assertions guard the durable guidance.