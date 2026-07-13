---
id: 172
title: Document multi-project setup and sharing guide
status: archived
priority: medium
created: 2026-03-29 19:49:54.758121+02:00
updated: 2026-03-29 21:45:21.218481+02:00
started: 2026-03-29 21:45:21.218481+02:00
completed: 2026-03-29 21:45:21.218481+02:00
tags:
- phase-2
- scope:build
- type:docs
blocked: true
block_reason: 'Duplicate of #169 (canonical). Pending archival by #182. See docs/research/duplicate-setup-guide-cleanup.md'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write setup-guide.md and sharing-guide.md for the multi-project model.

## Acceptance Criteria
- [ ] docs/setup-guide.md: step-by-step from clone to working
- [ ] docs/setup-guide.md: troubleshooting section
- [ ] docs/setup-guide.md: project-specific customization section
- [ ] docs/sharing-guide.md: how to share owlbear with teammates
- [ ] Both docs reference VS Code Diagnostics view
- [ ] Both docs note cross-drive Windows limitation
See docs/research/multi-project-setup-test.md

[[2026-03-29]] Sun 20:18
## Research
Research doc: docs/research/multi-project-doc-guide.md

Key findings:
- Doc structure validated against Aider + Claude Code prior art (Prerequisites, Quick Start, Verify, Troubleshoot)
- 60 passing setup.py tests confirm technical foundation
- New VS Code features since #25: org-level agents, parent repo discovery, Chat Customizations editor, Agent Debug Logs
- 6 troubleshooting scenarios documented with causes and resolutions
- Recommended outlines: setup-guide.md (~80 lines), sharing-guide.md (~60 lines)
- No additional follow-up tasks needed; #172 AC is complete and ready for pipeline

[[2026-03-29]] Sun 20:37
## Architecture Review
**Verdict:** Block (duplicate)

Confirmed duplicate of #169 (canonical task, same AC, same scope). Research doc docs/research/duplicate-setup-guide-cleanup.md identifies #172 as one of 4 duplicates (#171, #172, #174, #175) spawned by overlapping kanban-md create executions from #25 research. Task #182 handles archival of all duplicates.

No architectural review needed -- task should not proceed independently.
