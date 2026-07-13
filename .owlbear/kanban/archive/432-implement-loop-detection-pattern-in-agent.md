---
id: 432
title: Implement loop-detection pattern in agent instructions
status: archived
priority: medium
created: 2026-03-30 21:37:43.855377+02:00
updated: 2026-03-30 22:19:13.838265+02:00
started: 2026-03-30 22:19:13.838265+02:00
completed: 2026-03-30 22:19:13.838265+02:00
tags:
- research
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Adopt deer-flow's loop detection pattern: hash recent tool calls, inject warning at 3 repeats, force-stop at 5. Can be implemented as instruction rules in agent-common.instructions.md and/or a stop-hook.

See docs/research/deer-flow-adoptable-patterns.md S3B for analysis.

## Acceptance Criteria
- [ ] agent-common.instructions.md updated with explicit loop detection guidance (max retry counts, hash-based detection concept)
- [ ] Agents instructed to stop after 2 retries of the same logical operation (aligns with existing 'max 2 retries' red flag)

[[2026-03-30]] Mon 21:46
## Research
doc: docs/research/loop-detection-instruction-patterns.md

Key findings:
- Stop hooks not viable for pipeline agents (SubagentStop deadlock per #209)
- Programmatic middleware not available (no OwlBear runtime process)
- Instruction rules are the only viable mechanism (.85 confidence)
- Proposed 3-tier escalation: detect (1 retry) / adapt (2 approaches) / stop (3 total)
- Consolidates scattered retry guidance into one section

Follow-up tasks created:
- #435 Consolidate loop detection rules in agent-common.instructions.md (needed)
- #436 Add loop-pattern detection to reviewer checklist (important)
