---
id: 266
title: Add fresh-context retry to builder agent
status: archived
priority: medium
created: 2026-03-30 19:31:28.635773+02:00
updated: 2026-04-04 07:24:33.653117+02:00
started: 2026-04-04 07:24:33.653117+02:00
completed: 2026-04-04 07:24:33.653117+02:00
tags:
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

After 2 failed attempts in same context, builder delegates fix to a Fix-Attempt subagent with minimal context. See docs/research/subagent-nesting-architecture.md S3e.

[[2026-03-30]] Mon 20:40
## Research
Research doc: docs/research/fresh-context-retry-builder.md
Key finding: Reflexion-style verbal retry_hint critical for fresh-context repair quality
Threshold: 2 failures before delegation (pending decision 228-fresh-context-retry.md)
Fix-attempt subagent: assign mode, 9 tools (builder minus kanban), one-shot
Follow-ups at ideation: #318 (agent), #319 (workflow), #320 (tests)

[[2026-03-30]] Mon 21:45
## Architecture Review
**Verdict:** Block

### AC Assessment
- 'After 2 failed attempts, builder delegates to Fix-Attempt subagent': Feature-level description, not verifiable AC. No interface, no input/output contract, no pass/fail criteria. Actual AC lives in #318, #319, #320.

### Architecture Notes
1. Pending decision blocks implementation. Decision 228-fresh-context-retry.md is approved:false. Research doc explicitly requires approval before implementation.
2. Task is a decomposed parent. Researcher decomposed #266 into #318 (agent file), #319 (workflow), #320 (tests).
3. No path through builder pipeline. Test-writer would have nothing to test; testable AC is in #320.
4. Codebase verified: builder agents:[] and tdd-workflow has no fresh-context retry. Correct touch-points captured in #319 AC.

### Recommended Path
When decision 228-fresh-context-retry.md is approved, architect should review #318 (already in backlog) as entry point.

### Changes Made
- Blocked #266 to ideation (pending decision, decomposed parent)
