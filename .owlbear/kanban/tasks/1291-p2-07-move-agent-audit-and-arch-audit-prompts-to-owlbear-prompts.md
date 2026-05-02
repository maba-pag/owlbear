---
id: 1291
title: 'P2-07: Move agent-audit and arch-audit prompts to .owlbear/prompts/'
status: research
priority: important
created: 2026-05-02T16:01:17.128331+00:00
updated: 2026-05-02T16:02:39.776595+00:00
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

- [ ] agent-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] arch-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] No dangling references to old locations in any instruction or skill file
- [ ] Tests from #1285 pass for prompt-location assertions

## Scope

- IN: share/prompts/agent-audit.prompt.md, share/prompts/arch-audit.prompt.md → .owlbear/prompts/
- OUT: doc-audit.prompt.md (handled by #1290 as part of atomic chain)