---
id: 1287
title: 'P2-03: Genericize h-pytest-and-linting, h-vitest-and-linting, h-quality-runner'
status: research
priority: needed
created: 2026-05-02T16:01:17.076781+00:00
updated: 2026-05-02T16:02:39.747738+00:00
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

- [ ] h-pytest-and-linting: ~7 serve/ path references replaced with concrete illustrative paths + prose note pattern
- [ ] h-vitest-and-linting: ~6 serve/cockpit/web/ references replaced with "your frontend package root" + framed example
- [ ] h-quality-runner: path examples genericized; routing prose added directing agents to read project copilot-instructions.md
- [ ] All replacements use the Brief's notation convention (prose-first with framed examples, never template syntax)
- [ ] Tests from #1285 pass for these three skills

## Scope

- IN: h-pytest-and-linting/SKILL.md, h-vitest-and-linting/SKILL.md, h-quality-runner/SKILL.md
- OUT: Skills covered by #1286, workflow skills (#1288)