---
id: 329
title: Add NON_IMPL_TAGS cross-reference comments to 3 skill files
status: archived
priority: medium
created: 2026-03-30 20:39:07.921439+02:00
updated: 2026-04-04 07:09:55.225420+02:00
started: 2026-04-04 07:09:29.566996+02:00
completed: 2026-04-04 07:09:29.566996+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] dispatch-planning SKILL.md has NON_IMPL_TAGS comment listing secondary locations
- [ ] tdd-red SKILL.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative
- [ ] agent-audit.prompt.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative
- [ ] grep NON_IMPL_TAGS returns exactly 3 files

## Context
See docs/research/non-impl-tag-cross-references.md for recommended pattern. Created from #218 research.
