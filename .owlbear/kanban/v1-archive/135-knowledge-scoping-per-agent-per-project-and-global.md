---
id: 135
title: Knowledge scoping — per-agent, per-project, and global namespaces
status: archived
priority: nice-to-have
created: 2026-02-27T14:57:27.4538299+01:00
updated: 2026-02-28T23:52:58.5782218+01:00
started: 2026-02-28T00:46:45.5154471+01:00
completed: 2026-02-28T23:52:58.5782218+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 133
class: standard
---

Knowledge graph needs scoping: some knowledge is global (coding patterns, best practices), some is project-specific (this codebase's architecture), some is agent-specific (this agent's learned preferences). Research how to partition the existing knowledge graph without duplicating the storage layer. May be as simple as a 'scope' column on entities/documents.
