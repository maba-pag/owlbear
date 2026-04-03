---
id: 528
title: Design curator workflow for memory-mcp
status: backlog
priority: important
created: 2026-04-01T16:11:51.0425772+02:00
updated: 2026-04-01T19:15:26.9802065+02:00
started: 2026-04-01T19:15:15.4660781+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
class: standard
---

Update curator agent and curation-workflow skill for memory-mcp integration per docs/research/memory-mcp-server-design.md sec 3I. Depends on #525.

AC:
- [ ] Curator agent updated to use list_entries for reviewing pending entries
- [ ] Curator can call mark_for_deletion for noise entries
- [ ] Curator can call record_learning to cross-pollinate insights to broader scopes
- [ ] Curation report includes recommendations for user approval (promote to approved)
- [ ] CLI or admin tool for user to batch-approve curator recommendations

[[2026-04-01]] Wed 19:14
## Research
Doc: docs/research/curator-workflow-memory-mcp.md

Follow-up tasks: #529 #530 #531. All contingent on DR #387 approval.

[[2026-04-01]] Wed 19:14
## Challenge Results

[[2026-04-01]] Wed 19:14
Challenger: block, confidence .45. Researcher revised to .78. Adopted MCP-routed approval, source lineage, kept vscode/memory.
