---
id: 218
title: Sync non-impl tag list cross-references across skill files
status: backlog
priority: nice-to-have
created: 2026-03-30T14:54:54.311161+02:00
updated: 2026-03-30T20:40:49.2995903+02:00
tags:
    - scope:agents
    - quality
    - type:config
class: standard
---

[[2026-03-30]] Mon 14:55
## Acceptance Criteria
- [ ] Each file containing the non-impl tag list (dispatch-planning SKILL, tdd-red SKILL, agent-audit prompt) has a cross-reference comment pointing to dispatch-planning SKILL.md agent dispatch table as the authoritative list
- [ ] Adding a new non-impl tag requires updating only one authoritative location plus following the cross-references

## Context
See docs/research/gate4-tw-missing-tag-exemptions.md section 3.4 (tag list synchronization risk). Created from #215 research.

[[2026-03-30]] Mon 20:40
## Research

- 3 files contain the non-impl tag list (not 4 as #215 research claimed)
- Authoritative: dispatch-planning SKILL.md (table L21 + paragraph L27-28)
- Secondary: tdd-red SKILL.md (L26), agent-audit.prompt.md (L107-108)
- Recommended: HTML comment markers with NON_IMPL_TAGS keyword (grep-searchable)
- Follow-up: #329 created at ideation
- Doc: docs/research/non-impl-tag-cross-references.md
