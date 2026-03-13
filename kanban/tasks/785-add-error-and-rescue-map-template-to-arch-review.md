---
id: 785
title: Add Error and Rescue Map template to arch-review skill
status: in-progress
priority: important
created: 2026-03-13T16:48:00.1684142+01:00
updated: 2026-03-13T18:56:58.1133787+01:00
started: 2026-03-13T17:06:25.0745643+01:00
tags:
    - research
    - scope:agent-config
    - type:docs
claimed_by: builder
claimed_at: 2026-03-13T18:56:58.1133787+01:00
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
