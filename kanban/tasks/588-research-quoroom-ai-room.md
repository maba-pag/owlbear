---
id: 588
title: 'Research: quoroom-ai/room'
status: archived
priority: important
created: 2026-03-05T23:50:52.271264+01:00
updated: 2026-03-07T18:08:10.524733+01:00
started: 2026-03-06T21:26:11.8719566+01:00
completed: 2026-03-07T18:08:10.524733+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 580
class: standard
---

**Source:** https://github.com/quoroom-ai/room
Analyze for multi-agent delegation, orchestration patterns, and task execution logic.

**Research doc:** docs/research/quoroom-room.md

**Key findings:**
- **WIP continuity** (.80): save_wip/CONTINUE FORWARD pattern solves multi-cycle amnesia. Highest value.
- **Stuck detection** (.75): Track productive tool calls, inject warning after 2 idle cycles. Low cost.
- **Control-plane separation** (.65): Queen=delegate only, Workers=execute. Enforce via tool partitioning.
- **Agent state machine** (.60): idle/thinking/acting/rate_limited/blocked for observability.
- **Skip**: Quorum governance (too autonomous for dev assistant), session compression (PydanticAI history processors suffice).

**Research checklist:**
- [x] Theoretical validity: Swarm intelligence with Queen/Worker/Quorum. Sound approach, well-tested at scale.
- [x] Prior art: quoroom-ai/room (MIT), microsoft/autogen (MIT/CC-BY-4.0)
- [x] Technical feasibility: Patterns are language-agnostic. WIP store, stuck detection, tool partitioning all map to OwlBear Python stack.
- [x] Architecture fit: WIP store -> SessionStore extension. Stuck detection -> HookRegistry PRE_TURN hook. Tool partitioning -> bootstrap toolset config.
- [x] Implementation approach: JSONL-backed WipStore, counter-based stuck hook, orchestrator toolset allowlist.
