---
id: 196
title: Add necessity check to code-review skill critical checks
status: in-progress
priority: needed
created: 2026-03-29T23:08:30.248244+02:00
updated: 2026-03-30T02:54:47.3962044+02:00
tags:
    - agent
    - quality
    - scope:agents
class: standard
---

## Objective
Add a necessity verification step to the code-review skill so the reviewer questions whether feature additions are genuinely needed.

## Acceptance Criteria
- [ ] skills/code-review/SKILL.md: new section "### 6.6 Necessity check" inserted after existing 6.5, inside Step 6 (Pass 1: CRITICAL checks). Content includes: (a) Conditional gate using existing "> **Conditional:**" pattern -- only applies when the task adds a new dependency, integration, tool, server, or external capability; not triggered by bug fixes, refactors, renames, config tweaks, or test improvements. (b) Three questions the reviewer must answer: (1) Does the IDE, runtime, or an installed extension already provide this? (2) Does existing project tooling already solve this need? (3) Is this a presumptive feature (building for speculated future need)? (c) If yes to any question: FAIL with evidence citing the existing provider.
- [ ] agents/reviewer.agent.md: one new entry added to "Red flags -- STOP and reassess" list: "You are about to PASS a feature addition without checking if the environment already provides it"
- [ ] No other files modified

## Context
See docs/research/pipeline-quality-audit.md recommendation R3.
See docs/research/necessity-check-code-review.md for full research findings.

## Research
Researched by researcher agent, 2026-03-29.
See docs/research/necessity-check-code-review.md for full findings.
Key finding: AC said section 6.5, but 6.5 is already taken (Implementation-aware test gap analysis). Correct section is 6.6.
Sources: Google eng-practices Design section, Fowler YAGNI, SmartBear checklists, pipeline-quality-audit S1.
Confidence: .90

[[2026-03-30]] Mon 00:06
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New section 6.6 in code-review skill | Original said 6.5 but 6.5 is taken. Research doc identified this. Corrected to 6.6. Precise: specifies file, location, conditional gate, three questions, FAIL behavior. | Refined (6.5 to 6.6) |
| Red-flags list update in reviewer.agent.md | Clear and specific. Single line addition. | Kept as-is |
| No other files modified | Scoping constraint, verifiable. | Kept as-is |

### Architecture Notes
- Single domain: reviewer agent/skill files only. No split needed.
- Existing pattern: sections 6.0 and 6.2 already use Conditional gates. New section follows same convention.
- Current sections: 6.0 through 6.5. New 6.6 appends cleanly at end of Pass 1.
- No application code involved. Markdown-only change to skill and agent files. TDD test task not applicable.
- Red-flags list at agents/reviewer.agent.md L107 currently has 16 entries. One addition is low burden.

### Changes Made
- Corrected section number from 6.5 to 6.6 in AC
- Added explicit file paths (skills/code-review/SKILL.md, agents/reviewer.agent.md)
- Referenced research doc in Context section
- Preserved researcher notes in body

### Dependencies
- None. No depends_on required. Task is self-contained.
