---
id: 993
title: '1b: Create h-memory-structure handbook (new skill)'
status: archived
priority: medium
created: 2026-04-18T21:23:32.409493+00:00
updated: 2026-04-18T23:42:37.813907+00:00
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

# 993 was created at 21:23 as a planner artifact. #1001 was created at 21:34 during the architect's formal SPLIT of parent #984. The parent's `## Architecture Review` section explicitly lists #1001 (not #993) as the canonical child

# 1001 has stricter AC (specific section names, ≤5 required fields, ≤150 line limit, ≤5 anti-patterns ≤2 lines each) vs. #993's vaguer "covers all content scope items" criteria

**Action:** Reject as duplicate. #1001 is the authoritative task — no further work needed on #993. This task should be archived or deleted.
[[2026-04-18]]

## Research

Confirmed duplicate of #1001 — no research doc needed.

- **Evidence:** Both tasks share parent #984, create identical file (`share/skills/h-memory-structure/SKILL.md`), cover identical scope. Parent #984's SPLIT table lists #1001 (not #993) as canonical child.
- **#1001 status:** `todo` (architect-approved with refined AC — specific section names, ≤5 fields, ≤150 lines, ≤5 anti-patterns).
- **#993 origin:** Planner artifact (21:23), superseded by architect's formal decomposition (#1001, 21:34).
- **Disposition:** Reject to done for archival. No follow-up tasks, no decision requests.
[[2026-04-18]]

## Audit

### Duplicate Verification

Confirmed duplicate of #1001. Evidence:

- Both tasks share parent #984, target identical file (`share/skills/h-memory-structure/SKILL.md`), identical scope
- Parent #984 SPLIT table lists #1001 (not #993) as canonical child
- #1001 has refined AC (specific section names, field counts, line limits) vs #993's vague "covers all content scope items"
- #993 origin: planner artifact (21:23), superseded by architect SPLIT (#1001, 21:34)
- Deliverable file does not exist — no orphaned work

### AC Verification

N/A — task correctly identified as duplicate before implementation. AC will be fulfilled by #1001.

### Test Results

N/A — no code changes (duplicate disposition, no deliverables)

### Architect Quality: 3/5

Planner-authored AC was reasonable but vaguer than #1001's refined version. Architect correctly caught the duplicate and created #1001 with stricter, mechanically-verifiable AC. System worked as designed.

### Deduction Breakdown

- Start: 1.00
- AC quality 3/5: -.03
- Missing reviewer section: no deduction (expected for duplicate-disposition flow)

### Confidence: .97

### Action: archive
