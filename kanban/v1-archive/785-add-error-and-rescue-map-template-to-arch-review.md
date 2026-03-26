---
id: 785
title: Add Error and Rescue Map template to arch-review skill
status: archived
priority: important
created: 2026-03-13T16:48:00.1684142+01:00
updated: 2026-03-15T08:21:17.9316092+01:00
started: 2026-03-13T17:06:25.0745643+01:00
completed: 2026-03-15T08:20:55.6378077+01:00
tags:
    - research
    - scope:agent-config
    - type:docs
class: standard
---

## Goal
Add a structured failure-mode analysis template to the arch-review skill, inspired by gstack's Error and Rescue Map.

## AC
- [ ] arch-review SKILL.md Step 3 adds sub-step 10: **Failure Mode Map**  applicable only when the task introduces or modifies codepaths with potential failure modes (skip for docs/config-only tasks)
- [ ] Sub-step includes a markdown template table with columns: CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT
- [ ] Sub-step includes one example row, e.g.: `store()` | DB write fails | `sqlite3.OperationalError` | Yes  retry 2x | Stale data until next sync
- [ ] arch-review SKILL.md self-critique checklist adds: `- [ ] Failure mode map assessed (for tasks with new/modified codepaths)`
- [ ] architect.agent.md `<self_critique>` quick checks adds: `- [ ] Failure mode map assessed (if task introduces codepaths)`
- [ ] No changes to .py files

## Files to modify
- `.github/skills/arch-review/SKILL.md`  Step 3 sub-step + self-critique item
- `.github/agents/architect.agent.md`  self-critique quick check item

See docs/research/gstack-agent-patterns.md for prior art.

[[2026-03-13]] Fri 17:39
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Step 3 adds sub-step 10: Failure Mode Map with scoping | Clear, verifiable  builder adds numbered item after existing 9 criteria | OK |
| Template table with 5 columns | Columns specified exactly: CODEPATH, FAILURE MODE, EXCEPTION, HANDLED?, USER IMPACT | OK |
| Example row included | Prevents ambiguity on column semantics  concrete example required | Refined (added) |
| SKILL.md self-critique checklist item | Verifiable  grep for the line | OK |
| architect.agent.md quick check item | Verifiable  grep for the line in self_critique section | OK |
| No .py changes | Guard rail | OK |

### Architecture Notes
- Scoping condition added: failure mode map only applies to tasks with new/modified codepaths. Prevents empty tables for docs/config tasks.
- Example row added to AC to prevent column-semantic ambiguity (original AC just listed column names).
- Original AC3 split into two items: SKILL.md checklist + agent.md quick checks  separate files, separate verifications.
- Pattern consistency: Step 3 already has 9 numbered sub-steps. Sub-step 10 follows the same style.
- TDD: N/A  type:docs task, no .py files.
- No dependencies required. Research #783 complete.

### Changes Made
- Refined body: added scoping condition, example row, split checklist items, added Files to modify section

### Dependencies
- None required. Research #783 is complete (archived).

[[2026-03-13]] Fri 18:01
## Test-Writer Notes
- Non-implementation task (tagged type:docs, scope:agent-config)  no tests applicable.
- AC modifies only .md files (SKILL.md, .agent.md). No .py files involved.
- Passing through to builder.

[[2026-03-13]] Fri 18:56
## Builder Notes
- Files changed: .github/skills/arch-review/SKILL.md, .github/agents/architect.agent.md
- Tests: N/A (type:docs task, no .py changes)
- Lint: N/A
- SKILL.md Step 3: added sub-step 10 Failure Mode Map with scoping condition, template table (5 columns), and example row
- SKILL.md self-critique: added failure mode map checklist item
- architect.agent.md self_critique: added failure mode map quick check
- No .py files touched

[[2026-03-15]] Sun 07:42
## Review Evidence
### Test Results
- N/A (type:docs task, no .py files)

### Lint Results
- N/A (markdown-only changes)

### Coverage
- N/A

### Pass 1 -- CRITICAL
- Security, Test Integrity, Test Quality, Data Safety: all N/A (no code changes)

### Pass 2 -- INFORMATIONAL
- Self-critique items use slightly different wording (acceptable for quick-check brevity)
- Markdown table valid, sub-step 10 follows existing numbered pattern

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 sub-step 10 | SKILL.md L55-57: Failure Mode Map with scoping | PASS |
| Template table 5 cols | SKILL.md L58-59: all 5 columns present | PASS |
| Example row | SKILL.md L60: store()/DB write/OperationalError | PASS |
| SKILL.md self-critique | SKILL.md L91: checklist item added | PASS |
| agent.md quick check | architect.agent.md L169: quick check added | PASS |
| No .py changes | git diff: 0 .py files in commits | PASS |

### Verdict: PASS (.95)

[[2026-03-15]] Sun 07:48
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Task modifies only agent/skill .md files; no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | No .py files modified (AC6: no .py changes) |
| 3 | sources/overview.md | Yes | Pass | Task references docs/research/gstack-agent-patterns.md (already attributed) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/gstack-agent-patterns.md exists, referenced in task body |
| 6 | No impact | -- | -- | Items 1,2,4 N/A; items 3,5 verified |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/785-* files found)

[[2026-03-15]] Sun 08:21
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 sub-step 10 Failure Mode Map | SKILL.md L55-60: sub-step 10 with scoping condition | PASS |
| Template table 5 cols | SKILL.md L58-59: CODEPATH, FAILURE MODE, EXCEPTION, HANDLED?, USER IMPACT | PASS |
| Example row | SKILL.md L60: store()/DB write/OperationalError/retry 2x/Stale data | PASS |
| SKILL.md self-critique item | SKILL.md L96: Failure mode map assessed checklist | PASS |
| architect.agent.md quick check | architect.agent.md L186: quick check present | PASS |
| No .py changes | Commits 31abb27 + fa36f9e: 0 .py files | PASS |

### Test/Lint Results
- N/A (type:docs task, no .py files modified)
- Research doc: docs/research/gstack-agent-patterns.md exists

### Commits
Deliverables committed by user in batch commits:
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 31abb27 | docs | arch-review/SKILL.md + 10 skills | #785 (batch) |
| fa36f9e | docs | architect.agent.md + 8 agents | #785 (batch) |

### Confidence: .97
### Action: archive

[[2026-03-15]] Sun 08:21
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 sub-step 10 Failure Mode Map | SKILL.md L55-60: sub-step 10 with scoping | PASS |
| Template table 5 cols | SKILL.md L58-59: all 5 columns present | PASS |
| Example row | SKILL.md L60: store()/DB write/OperationalError | PASS |
| SKILL.md self-critique item | SKILL.md L96: checklist item added | PASS |
| architect.agent.md quick check | architect.agent.md L186: quick check added | PASS |
| No .py changes | Commits 31abb27+fa36f9e: 0 .py files | PASS |

### Confidence: .97
### Action: archive
