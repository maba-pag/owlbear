---
id: 1284
title: 'P1-04: Update setup/init.py — scaffold consumer copilot-instructions.md'
status: research
priority: needed
created: 2026-05-02T16:01:10.625508+00:00
updated: 2026-05-02T16:02:06.202668+00:00
tags:
- phase-1
- scope:tools
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] setup/init.py generates a `.github/copilot-instructions.md` for new consumer projects
- [ ] Generated file contains a commented path-mapping section (project layout, source packages, frontend root, test paths)
- [ ] Template uses concrete illustrative examples with comments indicating customization needed
- [ ] Existing init.py functionality preserved (no regressions in other scaffolded files)
- [ ] Tests from #1281 pass for the init.py scaffold assertions

## Scope

- IN: setup/init.py modification
- OUT: Editing the OwlBear-dev copilot-instructions.md (#1282), cross-refs (#1283)
