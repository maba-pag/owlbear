---
id: 319
title: Add fix-attempt delegation to builder tdd-workflow
status: backlog
priority: needed
created: 2026-03-30T20:38:22.4647449+02:00
updated: 2026-04-05T10:27:38.1391275+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 318
class: standard
---

AC:
1. tdd-workflow skill updated: after 2nd verify failure, construct retry_hint and delegate to fix-attempt subagent
2. Builder agents array updated to include fix-attempt
3. Retry_hint includes specific error info (Reflexion-style verbal feedback)
4. Builder handles fix-attempt result: FIXED continues to commit, FAILED blocks task
5. Builder still caps at 2 retries total (same-context + fresh-context = 2 total attempts after initial)
See docs/research/fresh-context-retry-builder.md

[[2026-04-05]] Sun 10:27
## Research
- Research doc: .owlbear/research/fix-attempt-delegation-tdd-workflow.md
- Sources: 8 studied, 6 high-relevance (>=.90)
- Finding: **Implementation already exists** (commit c2b93a9, refined in 1d05a86). All 5 AC items satisfied.
- Recommendation: advance to pipeline verification — no new implementation needed (confidence: .92)
- Follow-up tasks created: none (work complete, sibling tasks #318 and #320 archived)
- Decision requests: none
- Board sync gap: #319 was implemented 2026-04-04 but never advanced from ideation

## Challenge Results
- Challenge: SKIPPED — validation pass on existing implementation, no new recommendation
- Confidence in original: .92
- Key validation checks: AC compliance (5/5), test coverage (9/9 pass), git history confirms commit scope
- Researcher response: findings hold — implementation matches AC with one accepted refinement (reject vs block, auditor-approved at .97)
