---
id: 1288
title: 'P2-04: Genericize w-doc-update and w-code-review'
status: research
priority: important
created: 2026-05-02T16:01:17.090078+00:00
updated: 2026-05-02T16:02:39.754833+00:00
tags:
- phase-2
- scope:docs
- shared-layer
parent: 1280
depends_on:
- 1285
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] w-doc-update: 3 IN-scope path entries genericized using prose-first notation
- [ ] w-code-review: lint_paths template genericized
- [ ] No `serve/` paths remain in either skill (MCP names excluded)
- [ ] Notation follows Brief convention (prose-first with framed examples)
- [ ] Tests from #1285 pass for these two skills

## Scope

- IN: w-doc-update/SKILL.md, w-code-review/SKILL.md
- OUT: Path-heavy skills (#1287), architecture extraction (#1289)