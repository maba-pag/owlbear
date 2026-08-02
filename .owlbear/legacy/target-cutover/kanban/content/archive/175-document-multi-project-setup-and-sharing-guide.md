---
id: 175
title: Document multi-project setup and sharing guide
status: archived
priority: medium
created: 2026-03-29 19:50:07.037711+02:00
updated: 2026-03-29 21:45:21.329274+02:00
started: 2026-03-29 21:45:21.329274+02:00
completed: 2026-03-29 21:45:21.329274+02:00
tags:
- phase-2
- scope:build
- type:docs
blocked: true
block_reason: 'Duplicate of #169 -- cleanup tracked by #182'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write setup-guide.md and sharing-guide.md for the multi-project model.

## Acceptance Criteria
- [ ] docs/setup-guide.md: step-by-step from clone to working (prerequisites, setup invocation, VS Code opening, verification steps)
- [ ] docs/setup-guide.md: troubleshooting section (MCP server fails, agents not appearing, instructions not loading)
- [ ] docs/setup-guide.md: project-specific customization section (adding local agents, overriding instructions, adding MCP servers)
- [ ] docs/sharing-guide.md: how to share owlbear with teammates (clone, setup, verify)
- [ ] Both docs reference VS Code Diagnostics view for debugging
- [ ] Both docs note cross-drive Windows limitation
See docs/research/multi-project-setup-test.md for research context.

[[2026-03-29]] Sun 20:36
## Architecture Review
**Verdict:** BLOCK (duplicate)

Task #175 is a duplicate of #169 (canonical setup-guide docs task). Both have identical AC and reference the same research doc. Task #182 already tracks cleanup of this and sibling duplicates (#171, #172, #174, #175). No further work needed on this task — #169 is the canonical version to advance through the pipeline.
