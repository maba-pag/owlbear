---
id: 329
title: Add NON_IMPL_TAGS cross-reference comments to 3 skill files
status: backlog
priority: nice-to-have
created: 2026-03-30T20:39:07.9214391+02:00
updated: 2026-03-30T23:43:30.4483698+02:00
tags:
    - scope:agents
    - quality
    - type:config
class: standard
---

## Acceptance Criteria
- [ ] dispatch-planning SKILL.md has NON_IMPL_TAGS comment listing secondary locations
- [ ] tdd-red SKILL.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative
- [ ] agent-audit.prompt.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative
- [ ] grep NON_IMPL_TAGS returns exactly 3 files

## Context
See docs/research/non-impl-tag-cross-references.md for recommended pattern. Created from #218 research.
