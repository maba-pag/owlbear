---
id: 462
title: Rewrite architecture.md to match actual codebase
status: archived
priority: critical
created: 2026-03-04T07:37:43.1678897+01:00
updated: 2026-03-06T19:28:08.0623017+01:00
started: 2026-03-06T00:22:58.7028783+01:00
completed: 2026-03-06T19:28:08.0623017+01:00
tags:
    - audit
    - docs
    - architecture
class: standard
---

DOC-F-01: architecture.md (v0.2) is severely outdated. Full discrepancy analysis in docs/architecture-rewrite-research.md.

**Sections to rewrite:** 2 (diagram only), 3, 4.3, 4.4, 4.6, 5.2, 6, 7

**AC (each line independently verifiable):**

1. **Section 2 diagram**: agent count shows 8 (not 5); knowledge pipeline marked wired (not 'not wired yet'); agent names list updated (architect, builder, closer, kanban-planner, orchestrator, researcher, reviewer, writer)
2. **Section 3 package tree**: lists planning/, projects/, safety/, bootstrap.py at top level; agents/ shows all 8 .md files (no coder.md); knowledge/ file count matches disk (23); core/ includes errors.py, escalation.py, progress.py; channels/ includes slack_mrkdwn.py, slack_templates.py; memory/ includes consolidation.py, error_journal.py; tools/ includes kanban.py, knowledge.py, knowledge_source.py, screenshot.py, screenshot_hook.py, visual_feedback.py, web_search.py
3. **Section 4.3 toolset table**: all toolsets marked wired; DelegationToolset, BrowserToolset, HookedToolset, MCPServerRegistry no longer show warning markers; 7 new toolsets listed (KanbanToolset, KnowledgeToolset, KnowledgeSourceToolset, ScreenshotService, VisualFeedbackToolset, WebSearchToolset, ProjectToolset)
4. **Section 4.4 agent framework**: says 8 agent definitions (not 5); lists all 8 by name; coder.md reference removed
5. **Section 4.6 knowledge**: file count updated (23 not 14); new subsystems mentioned (bookmarks, source store, refresh orchestrator, query service, inter-doc graph builder, retrieval/GAR)
6. **Section 5.2 data flow**: relabeled 'Current' (not 'Target'); task #263 reference removed
7. **Section 6**: 'Assembly Gap' heading replaced with 'Bootstrap Layer'; describes bootstrap.py wiring (hooks, toolsets, agent registry, delegation, MCP, channels, knowledge, projects); no 'not wired' or 'blocking' language remains
8. **Section 7 phase table**: PX row status is Done (not Critical); critical-path statement removed or updated to reflect current state
9. **Version bump**: header version updated to v0.3 with current date
10. **No regressions**: sections 1, 4.1, 4.2, 4.5, 4.7, 4.8, 4.9, 5.1, 8, 9 remain unchanged (spot-check any 3 sections for no accidental edits)
