---
id: 3
title: agentskills.io spec validation
status: archived
priority: medium
created: 2026-03-26 17:18:26.772286+01:00
updated: 2026-03-29 01:25:07.078250+01:00
started: 2026-03-29 01:25:06.779633+01:00
completed: 2026-03-29 01:25:06.779633+01:00
tags:
- research
- phase-1
- scope:skills
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Research the agentskills.io open standard and validate whether v1 skills can be ported with minimal changes.

## Acceptance Criteria
- [ ] Read agentskills.io specification and document findings in a trade-off matrix
- [ ] Map v1 SKILL.md format to agentskills.io format: identify gaps in required/optional fields
- [ ] Document required changes per skill (scripts/, references/, assets/ structure)
- [ ] Document skill discovery paths and auto-loading mechanism for VS Code and Copilot CLI
- [ ] Document progressive disclosure pattern (metadata -> instructions -> resources) with tier compliance for all 21 skills
- [ ] Write findings to docs/research/agentskills-io.md
- [ ] Create follow-up tasks for any gaps discovered (implementation tasks at ideation)

## Context
OwlBear v1 has 21 skills in .github/skills/. The agentskills.io standard may require restructuring. Need to know the delta before porting.

Note: Empirical testing of skill auto-loading and CLI loading belongs in the porting task #9, not this research task.

[[2026-03-28]] Sat 21:20
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-28]] Sat 21:56
## Builder Notes
- Non-implementation research task — no code changes.
- Verified docs/research/agentskills-io.md exists and covers all AC items.
- Updated doc with accurate per-skill compliance table (21 skills audited directly from files).
- Corrected inaccuracies: user-invocable and argument-hint were already set in 11 and 5 skills respectively (doc previously said Not used).
- Follow-up tasks confirmed: #42 (in-progress), #79 (todo), #44 (todo).
- Committed: docs update (#3, builder).

[[2026-03-28]] Sat 22:39
## Review Evidence

### Test Results
- N/A - research task, no implementation code

### Lint Results
- N/A - no Python source files changed

### Coverage
- N/A

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage
- N/A - tagged research, no TestFromAC classes

#### Security Review
- No security issues found - pure documentation task, no code, no secrets

#### Test Integrity
- N/A

#### Test Quality
- N/A

#### Data Safety
- No data safety issues found

#### Implementation-Aware Test Gaps
- N/A

### Pass 2 - INFORMATIONAL
- AC line 1 says trade-off matrix but Section 3 uses compliance tables; substance is equivalent
- Auto-loading mechanism section describes paths and flags but not the full relevance-based injection lifecycle; acceptable for this scope

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Read spec + findings in trade-off matrix | Section 2 (5 sources + relevance scores); Section 3a-3f analysis tables | PASS |
| Map v1 SKILL.md to agentskills.io: gaps in required/optional fields | Section 3a (frontmatter compliance table, 100% required fields met); Section 3b (VS Code extensions) | PASS |
| Document required changes per skill | Section 3c - 21-row per-skill table, Required changes column; 19/21 zero changes, 2 optional | PASS |
| Document skill discovery paths and auto-loading mechanism | Section 3e (3 discovery paths); Section 3b (user-invocable, disable-model-invocation flags) | PASS |
| Progressive disclosure with tier compliance for all 21 skills | Section 3d - explicit 3-tier table; all 21 skills verified 49-366 lines | PASS |
| Write findings to docs/research/agentskills-io.md | File exists; 21-skill count matches .github/skills/ directory (21 subdirs verified) | PASS |
| Create follow-up tasks at ideation | Task #42 (in-progress), #79 (todo), #44 (todo) confirmed on board | PASS |

### Verdict: PASS - confidence .92

[[2026-03-29]] Sun 00:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research-only task, no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Entry present — all 5 sources listed with URLs, license, Where Used |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/agentskills-io.md exists; follow-up tasks #42 #79 #44 confirmed on board |
| 6 | Scratch files | N/A | Pass | No docs/scratch/3-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None
