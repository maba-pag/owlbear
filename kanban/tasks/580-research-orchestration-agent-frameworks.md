---
id: 580
title: 'Research: Orchestration & Agent Frameworks'
status: archived
priority: important
created: 2026-03-05T23:49:54.63337+01:00
updated: 2026-03-07T18:08:06.3127563+01:00
started: 2026-03-07T04:08:13.7555939+01:00
completed: 2026-03-07T18:08:06.3127563+01:00
tags:
    - research
    - phase-research
    - scope:agent
class: standard
---

Epic: Analyze multi-agent delegation, project-board monitoring, and task execution logic from orchestration frameworks. Children cover individual repos.

**Research doc:** docs/research/orchestration-agent-frameworks.md

**Child tasks (all complete):**
- #584 openai/symphony  poll-dispatch-reconcile, task-level retry, continuation turns
- #585 ComposioHQ/agent-orchestrator  reaction engine, priority notifications, prompt layering
- #586 harshkedia177/axon  MCP next-step hints, hybrid search RRF
- #587 Ibrahim-3d/conductor  retrospective learning, anti-rationalization, plan critique
- #588 quoroom-ai/room  WIP continuity, stuck detection, control-plane separation
- #589 nWave-ai/nWave  rigor profiles, reviewer pairing, stale detection, turn limits

**Key recommendation (.85 confidence):**
Adopt patterns in 3 tiers: (1) poll-dispatch-reconcile + WIP continuity + task retry (needed), (2) rigor profiles + retrospective learning + stale detection (important), (3) reaction engine + rationalization tables + tool partitioning (nice-to-have).

**Follow-up tasks:** 6 cross-cutting tasks proposed in research doc S5.

**Research checklist:**
- [x] Theoretical validity  7 orchestration paradigms compared
- [x] Prior art  9 repos + 3 framework docs studied across 6 child tasks
- [x] Technical feasibility  all patterns portable to PydanticAI + asyncio
- [x] Architecture fit  extends existing daemon loop, hooks, toolsets, knowledge graph
- [x] Implementation approach  3-tier priority + trade-off matrices
- [x] Testing strategy  covered per child task
- [x] Findings documented in docs/research/orchestration-agent-frameworks.md
