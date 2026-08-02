---
id: 1932
title: Keep collector commit guidance procedural
status: archived
priority: high
created: 2026-07-14T02:40:32.435475+02:00
updated: 2026-07-14T04:11:35.728517+02:00
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
archival_reason: completed
archival_refs: []
---
## Objective
Keep collector commit guidance procedural, concise, and independent of Kanban move implementation details.

## Acceptance Criteria
- Collector guidance requires both the old task path and new archive path in the scoped commit.
- An already-staged owned path is left untouched and routes to `COMMIT_FAILED` containment.
- Obsolete archive-move recovery and implementation-history prose is absent from the skills.
- Focused assertions guard the durable guidance.

[[2026-07-14T04:07:28+02:00]]
## Verify Notes

- Verified amended builder commit `5a0fadcb5`.
- Removed implementation-history and obsolete archive-recovery prose from the skills.
- Durable guidance now requires both archive paths and leaves pre-staged owned paths untouched under `COMMIT_FAILED` containment.
- Corrected the task objective and acceptance criteria to the procedural contract.
- Checks: 4 focused tests passed; Ruff clean; all 23 agent definitions valid; rejected historical phrases absent.
- Patches applied: focused contract assertions only.
- Verifier challenger: pass; final route PASS to collect.

[[2026-07-14T04:11:35+02:00]]
## Collect Notes

- Confirmed the committed skills contain only durable collector commit procedure.
- Confirmed both-path archive commits and pre-staged-path `COMMIT_FAILED` routing are guarded by focused assertions.
- Builder commit: `5a0fadcb5`; verifier transition: `970b62224`.
- Verification: 4 focused tests passed; Ruff clean; all 23 agent definitions valid.
- Archived as completed.
