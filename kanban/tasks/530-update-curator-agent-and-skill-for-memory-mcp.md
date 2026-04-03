---
id: 530
title: Update curator agent and skill for memory-mcp
status: ideation
priority: important
created: 2026-04-01T19:13:05.3558386+02:00
updated: 2026-04-01T19:13:05.3558386+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
class: standard
---

Update curator.agent.md and curation-workflow/SKILL.md for memory-mcp integration. Per docs/research/curator-workflow-memory-mcp.md. Depends on #525.

AC:
- [ ] Curator agent tools include owlbear-memory list_entries, mark_for_deletion, record_learning
- [ ] Curator agent retains vscode/memory for /memories/ access
- [ ] Curation-workflow Step 1 updated: list_entries(status=pending) replaces memory view
- [ ] Curation-workflow Step 4 updated: mark_for_deletion replaces memory delete
- [ ] New cross-pollination step: record_learning with source=curator:cross-pollinate:{id}
- [ ] Report format includes entry IDs with short preview and recommendation
