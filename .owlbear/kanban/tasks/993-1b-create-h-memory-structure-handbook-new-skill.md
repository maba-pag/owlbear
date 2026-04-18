---
id: 993
title: '1b: Create h-memory-structure handbook (new skill)'
status: research
priority: needed
created: 2026-04-18T21:23:32.409493+00:00
updated: 2026-04-18T21:39:29.081629+00:00
tags:
- type:docs
- scope:skills
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective
Create `share/skills/h-memory-structure/SKILL.md` — a new handbook defining what makes a well-formed memory entry. **Terse-by-construction**: few required fields, tight length limits, explicit anti-patterns. No optional-menu sections (LLMs invent content to fill them).

## Content Scope
- Entry shape (required fields, length limits)
- Categories (from `r-pipeline-protocol` post-task reflection mapping)
- File-based `/memories/` vs. `owlbearMemory` MCP relationship
- Tier-content fit (user vs. session vs. repo vs. canonical — per `owlbear-system.instructions.md` S4)
- Dedupe/supersede rules
- Content-quality bar
- Explicit anti-patterns

## Acceptance Criteria
- [ ] `share/skills/h-memory-structure/SKILL.md` exists with valid frontmatter (`name`, `description`, `user-invocable: false`).
- [ ] Covers all content scope items above.
- [ ] Terse-by-construction: required + bounded fields only, no optional menus.
- [ ] References (not restates) tier boundaries from `owlbear-system.instructions.md` S4.
- [ ] Style matches existing handbook skills (to-the-point, no fluff).

## Files
- `share/skills/h-memory-structure/SKILL.md` (new)
[[2026-04-18]]
## Architecture Review

### Verdict: REJECT (Duplicate)

**This task is a duplicate of #1001.** Both tasks:
- Share parent #984
- Create the same file: `share/skills/h-memory-structure/SKILL.md`
- Cover the same content scope (entry shape, tiers, dedup, anti-patterns)

#993 was created at 21:23 as a planner artifact. #1001 was created at 21:34 during the architect's formal SPLIT of parent #984. The parent's `## Architecture Review` section explicitly lists #1001 (not #993) as the canonical child.

#1001 has stricter AC (specific section names, ≤5 required fields, ≤150 line limit, ≤5 anti-patterns ≤2 lines each) vs. #993's vaguer "covers all content scope items" criteria.

**Action:** Reject as duplicate. #1001 is the authoritative task — no further work needed on #993. This task should be archived or deleted.