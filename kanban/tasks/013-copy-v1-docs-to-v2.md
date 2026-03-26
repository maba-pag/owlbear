---
id: 13
title: Copy v1 docs to v2
status: ideation
priority: important
created: 2026-03-26T17:20:40.4674737+01:00
updated: 2026-03-26T17:20:40.4674737+01:00
tags:
    - phase-1
    - scope:docs
    - type:docs
depends_on:
    - 7
class: standard
---

## Objective
Copy valuable v1 documentation assets to the v2 directory structure.

## Acceptance Criteria
- [ ] Copy docs/research/*.md to v2 docs/research/ (50+ research documents)
- [ ] Copy docs/sources/overview.md to v2 docs/sources/
- [ ] Copy docs/decisions/ to v2 docs/decisions/
- [ ] Review and remove v1-specific docs that are no longer relevant
- [ ] Update any internal cross-references that broke due to path changes
- [ ] Verify docs/scratch/ exists and is gitignored

## Context
Depends on F1 (monorepo skeleton) for directory structure. V1 has 50+ research docs, source attributions, and decision records that are valuable for v2. This is a bulk copy with light curation.
