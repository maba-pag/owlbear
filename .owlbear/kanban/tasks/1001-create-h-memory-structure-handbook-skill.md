---
id: 1001
title: Create h-memory-structure handbook skill
status: backlog
priority: needed
created: 2026-04-18T21:34:33.195499+00:00
updated: 2026-04-18T21:34:33.195499+00:00
tags:
- agent
- agent-ecosystem
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Create `share/skills/h-memory-structure/SKILL.md` — a terse handbook defining structural standards for OwlBear memory entries (file-based and MCP-based). Terse-by-construction: required fields only, tight length limits, explicit anti-patterns.

## Context

No handbook currently exists for memory entry structure. `owlbear-system.instructions.md` § Memory Governance defines which tier stores what, but not the shape, quality bar, or deduplication rules for entries. The audit prompt (Task 2, sibling) needs this handbook to probe Memory Governance findings.

## Acceptance Criteria

- [ ] New file at `share/skills/h-memory-structure/SKILL.md` with frontmatter: `name: h-memory-structure`, `description: "Handbook: Memory entry structure — tiers, entry shape, and content-quality bar"`, `user-invocable: false`.
- [ ] `## Entry Shape` section with ≤5 required fields per entry template. Zero optional fields.
- [ ] `## Tier-Content Fit` table mapping content types to memory tiers per `owlbear-system.instructions.md` § Memory Governance. References (does not restate) the governance section.
- [ ] `## File vs. MCP Relationship` section: when each is used, dual-write during migration (per `r-pipeline-protocol` § Post-task Reflection).
- [ ] `## Deduplication Rules` section: how to detect duplicates, supersede/merge procedure, which entry wins on conflict.
- [ ] `## Content-Quality Bar` section: concrete pass/fail criteria (not aspirational). Example: "Entry must cite a specific task ID or file path; generic advice fails."
- [ ] `## Anti-Patterns` section with ≤5 items, each ≤2 lines.
- [ ] Total file length ≤150 lines.
- [ ] No optional fields, no menus of choices, no "consider also" language.

## Files

- `share/skills/h-memory-structure/SKILL.md` (new)
