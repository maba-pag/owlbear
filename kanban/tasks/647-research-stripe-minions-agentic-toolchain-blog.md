---
id: 647
title: 'Research: Stripe Minions agentic toolchain (blog series)'
status: archived
priority: important
created: 2026-03-07T19:21:22.3979107+01:00
updated: 2026-03-09T15:55:05.0014908+01:00
started: 2026-03-08T23:58:47.2066061+01:00
completed: 2026-03-09T15:55:05.0014908+01:00
tags:
    - research
    - phase-research
    - scope:core
    - agent
class: standard
---

Read the Stripe Minions blog series on their one-shot end-to-end coding agents and extract actionable knowledge for OwlBear.

Sources:
- https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
- https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2

AC:
- [ ] Read both blog posts and summarize key architectural patterns
- [ ] Identify patterns we already use and note any gaps
- [ ] Identify new patterns/techniques worth adopting
- [ ] Produce a research doc at docs/stripe-minions-research.md
- [ ] Create follow-up kanban tasks for any actionable findings

[[2026-03-09]] Mon 00:07
## Research
See docs/stripe-minions-research.md for full findings.

Key takeaways:
- OwlBear's orchestrator+planner already implements Stripe's 'blueprint' pattern (hybrid workflow+agent)
- Two actionable gaps: (1) context pre-hydration before dispatch, (2) deterministic post-impl lint gate
- Three follow-up tasks proposed: pre-hydration design, lint gate, instruction scoping audit

### Follow-up Tasks
```n kanban\kanban-md.exe create 'Design context pre-hydration for agent dispatch' --priority important --status backlog --tag 'phase-research,scope:core,agent'
 kanban\kanban-md.exe create 'Add deterministic post-implementation lint gate' --priority important --status backlog --tag 'phase-research,scope:core,agent,tooling'
 kanban\kanban-md.exe create 'Audit global vs scoped instruction file ratio' --priority nice-to-have --status ideation --tag 'phase-research,scope:core,docs'
```

[[2026-03-09]] Mon 04:57
Wave 1, agent: reviewer

[[2026-03-09]] Mon 05:03
test_append

[[2026-03-09]] Mon 05:03
## Review Evidence
See docs/scratch/647-reviewer.md for full evidence.

[[2026-03-09]] Mon 05:03

### AC Compliance
| AC Line | Evidence | Status |
|------|------|------|
| Read both blog posts, summarize patterns | docs/stripe-minions-research.md S3: 6 patterns | PASS |
| Identify patterns we use + gaps | S4 comparison table, 2 gaps identified | PASS |
| Identify new patterns worth adopting | S5 recommends pre-hydration (.80) + lint gate (.75) | PASS |
| Produce research doc | docs/stripe-minions-research.md exists, well-structured | PASS |
| Create follow-up kanban tasks | Commands listed in S6 and task body but NEVER EXECUTED. grep kanban/tasks/*.md finds 0 matching tasks. | FAIL |

### Rejection Details
| Failed Item | Gap | Required Fix |
|------|------|------|
| AC5: Create follow-up tasks | kanban-md create commands in doc S6 and task body were never run. Zero follow-up tasks exist on the board. Violates research-docs.instructions.md. | Execute the 3 kanban-md create commands from doc S6, verify tasks exist. |

### Verdict: FAIL confidence .92

[[2026-03-09]] Mon 05:10
## Planner Evaluation\nVerdict: RETRY. AC5 (create follow-up tasks) NOT MET  3 kanban-md create commands listed but never executed. Execute commands from doc S6, verify tasks exist on board.

[[2026-03-09]] Mon 05:12
## Builder Notes
- Executed 3 kanban-md create commands from doc S6
- Created: #703 (pre-hydration, backlog), #704 (lint gate, backlog), #705 (instruction audit, ideation)
- Verified all 3 exist via kanban-md list --tag phase-research
- No code changes needed  research task, only missing AC was task creation

[[2026-03-09]] Mon 10:32
## Planner Evaluation (Retry)
All 5 AC lines now MET. AC5 fix verified: #703 (backlog), #704 (backlog), #705 (ideation) confirmed on board. Research doc exists. Verdict: ADVANCE, confidence .92.

[[2026-03-09]] Mon 10:37
## Review Evidence (Retry)
### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Read both posts, summarize patterns | S2 lists both URLs; S3 describes 6 patterns (3a-3f) | N/A (research) | PASS |
| AC2: Identify patterns we use + gaps | S4 comparison table, 2 gaps marked (lint node, pre-hydration) | N/A (research) | PASS |
| AC3: New patterns worth adopting | S5 recommends pre-hydration (.80) + lint gate (.75), YAGNI items excluded | N/A (research) | PASS |
| AC4: Produce research doc | docs/stripe-minions-research.md exists, 200 lines, well-structured per research-docs.instructions.md | N/A (research) | PASS |
| AC5: Create follow-up kanban tasks | #703 (backlog), #704 (backlog), #705 (ideation) verified on board via kanban show | N/A (research) | PASS |

### Test Quality
N/A  research task, no code changes.

### Security
N/A  research task, no code changes.

### Research Doc Quality
- Owning task referenced (line 2)
- Sources table with relevance scores (S2)
- Concrete recommendations with confidence scores (S5)
- Follow-up Tasks section with kanban commands (S6)
- All 3 follow-up tasks verified on board with AC and back-references
- YAGNI exclusions stated explicitly

### Minor: literal \n in follow-up task bodies (#703-705)  not blocking, AC still readable.

### Verdict: PASS confidence .93

[[2026-03-09]] Mon 10:37
## Review Evidence (Retry)
### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Read both posts, summarize patterns | S2 lists both URLs; S3 describes 6 patterns (3a-3f) | N/A (research) | PASS |
| AC2: Identify patterns we use + gaps | S4 comparison table, 2 gaps marked (lint node, pre-hydration) | N/A (research) | PASS |
| AC3: New patterns worth adopting | S5 recommends pre-hydration (.80) + lint gate (.75), YAGNI items excluded | N/A (research) | PASS |
| AC4: Produce research doc | docs/stripe-minions-research.md exists, 200 lines, well-structured per research-docs.instructions.md | N/A (research) | PASS |
| AC5: Create follow-up kanban tasks | #703 (backlog), #704 (backlog), #705 (ideation) verified on board via kanban show | N/A (research) | PASS |

### Test Quality
N/A  research task, no code changes.

### Security
N/A  research task, no code changes.

### Research Doc Quality
- Owning task referenced (line 2)
- Sources table with relevance scores (S2)
- Concrete recommendations with confidence scores (S5)
- Follow-up Tasks section with kanban commands (S6)
- All 3 follow-up tasks verified on board with AC and back-references
- YAGNI exclusions stated explicitly

### Minor: literal \n in follow-up task bodies (#703-705)  not blocking, AC still readable.

### Verdict: PASS confidence .93

[[2026-03-09]] Mon 10:50
## Planner Evaluation (Wave)\nReviewer PASS with .93 confidence on retry. All 5 AC lines MET. AC5 fix verified: #703, #704, #705 confirmed. Verdict: ADVANCE to docs (writer).

[[2026-03-09]] Mon 10:56
## Docs Gate

[[2026-03-09]] Mon 10:56
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research task, no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources.md | No | N/A | Already attributed at line 1232 (added by prior agent) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/stripe-minions-research.md exists, linked in task body; follow-up tasks #703, #704, #705 verified on board |
| 6 | No impact | -- | -- | Item 5 applies |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/647-* files found)

[[2026-03-09]] Mon 11:16
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Read both posts, summarize patterns | S2 lists both URLs; S3 describes 6 patterns (3a-3f) with OwlBear equivalents and gaps | PASS |
| AC2: Identify patterns we use + gaps | S4 comparison table, 9 rows, 2 gaps marked (lint node, pre-hydration) | PASS |
| AC3: New patterns worth adopting | S5 recommends pre-hydration (.80) + lint gate (.75); YAGNI items excluded | PASS |
| AC4: Produce research doc | docs/stripe-minions-research.md exists, 136 lines, well-structured per research-docs.instructions.md | PASS |
| AC5: Create follow-up kanban tasks | #703 (backlog), #704 (backlog), #705 (ideation) verified on board with AC and back-references | PASS |

### Test Results
- pytest: 1271 passed, 1 failed (pre-existing slack_sdk env issue), 20 skipped
- ruff: 3 pre-existing errors (screenshot.py E501, test_bootstrap_structure.py I001 x2) -- none from #647

### Confidence: .96
### Action: archive
