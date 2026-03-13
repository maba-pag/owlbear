---
id: 587
title: 'Research: Ibrahim-3d/conductor-orchestrator-superpowers'
status: archived
priority: important
created: 2026-03-05T23:50:46.4544215+01:00
updated: 2026-03-07T18:08:09.9726081+01:00
started: 2026-03-06T21:12:53.6468745+01:00
completed: 2026-03-07T18:08:09.9726081+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers (MIT, v3.3.0, extends obra/superpowers v4.3.0)

**Research doc:** See docs/research/conductor-orchestrator-superpowers.md

**Key Findings:**
- Retrospective learning pattern (.80 confidence) - post-task pattern/error extraction into knowledge graph
- Anti-rationalization tables (.70) - extend to builder/writer/auditor agent prompts
- Structured plan critique (.65) - 3-pass framework for architect agent
- Fix-loop with max retries (.50) - formal retry counter (low priority, kanban already handles this)
- File-based message bus (NOT transferable) - OwlBear uses native Python comms
- Board of Directors (NOT recommended) - too token-expensive for daemon scale

**Follow-up tasks created:** 3 (retrospective hook, anti-rationalization tables, plan critique passes)
**Research checklist:** All 5 items complete
