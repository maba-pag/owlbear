---
id: 1521
title: 'P3-03: Pipeline skill updates for frontmatter ac/proof_bundle'
status: backlog
priority: important
created: 2026-05-13T02:29:51.822731+00:00
updated: 2026-05-13T02:38:42.826581+00:00
tags:
  - phase-3
  - scope:skills
  - feature
  - docs
parent: 1514
depends_on:
  - 1518
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Update w-tdd-red, w-tdd-green, w-code-review, w-arch-review, w-task-decomposition skill files to read/write ac and proof_bundle from frontmatter
Out of scope: Code changes, tests, migration

## Acceptance Criteria
- AC1: `w-tdd-red` SKILL.md reads `ac` and `proof_bundle` from `show_task` frontmatter fields instead of parsing body markdown sections
- AC2: `w-tdd-green`, `w-code-review`, and `w-arch-review` SKILL.md files reference `proof_bundle` field from `show_task` response instead of body text
- AC3: `w-task-decomposition` SKILL.md writes `proof_bundle` via `create_task` parameter instead of `Proof bundle: X` body text line
- AC4: Builder greps `share/skills/` for remaining references to body-based `Proof bundle` and `Acceptance Criteria` patterns and updates any consumers not listed above

Proof bundle: skip