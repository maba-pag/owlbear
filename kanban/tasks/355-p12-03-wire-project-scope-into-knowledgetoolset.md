---
id: 355
title: 'P12-03: Wire project scope into KnowledgeToolset during bootstrap'
status: archived
priority: important
created: 2026-03-01T17:31:42.2101+01:00
updated: 2026-03-02T09:14:25.2804257+01:00
started: 2026-03-01T18:13:08.9630324+01:00
completed: 2026-03-02T09:14:25.2804257+01:00
tags:
    - phase-12
    - knowledge-graph
    - daemon
    - memory
class: standard
---

AC#5 of archived task #352 (Bootstrap project-awareness). The infrastructure for project-awareness exists in bootstrap, but knowledge queries do NOT include scope='project:{id}' when an active project is set.

The KnowledgeToolset needs to receive the project scope from bootstrap so queries are scoped to the active project in addition to 'global'.

AC:
- When active project exists, KnowledgeToolset queries include scope='project:{id}'
- When no active project, queries use default global scope only
- Integration test verifies scoped queries
- See docs/research/multi-project-session.md and docs/research/knowledge-scoping.md

Context: Unfinished acceptance criterion from task #352, found during phase-12 review.
