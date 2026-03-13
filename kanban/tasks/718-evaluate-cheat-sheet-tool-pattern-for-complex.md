---
id: 718
title: Evaluate cheat-sheet tool pattern for complex toolsets
status: backlog
priority: nice-to-have
created: 2026-03-09T23:06:33.8890974+01:00
updated: 2026-03-13T10:43:11.394014+01:00
started: 2026-03-10T04:41:00.3600922+01:00
tags:
    - research
    - tooling
    - scope:core
claimed_by: researcher
claimed_at: 2026-03-13T10:43:11.394014+01:00
class: standard
---

Investigate adding read_me-style companion tools to complex OwlBear toolsets (KnowledgeToolset, KanbanToolset) that pre-load format/schema context before the main tool call. Inspired by excalidraw-mcp read_me pattern. See docs/research/excalidraw-mcp.md S3.2.

[[2026-03-13]] Fri 09:12

## AC
- [ ] Research doc at docs/research/cheat-sheet-tool.md
- [ ] Evaluate read_me pattern from excalidraw-mcp for KnowledgeToolset and KanbanToolset
- [ ] Compare: inline tool descriptions vs companion read_me tool vs structured prompt injection
- [ ] Recommendation with confidence score
- [ ] Follow-up kanban tasks for adopted patterns

[[2026-03-13]] Fri 10:43
## Research
- Recommendation (.80): Don't add companion read_me tools. SkillRegistry already provides progressive disclosure.
- Follow-ups: #773, #774, #775
- Doc: docs/research/cheat-sheet-tool.md
