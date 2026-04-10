---
id: 581
title: 'Research: OpenClaw Ecosystem & Skills'
status: archived
priority: important
created: 2026-03-05T23:50:03.4624028+01:00
updated: 2026-03-07T18:08:06.8294288+01:00
started: 2026-03-07T04:08:41.3243981+01:00
completed: 2026-03-07T18:08:06.8294288+01:00
tags:
    - research
    - phase-research
    - scope:agent
class: standard
---

Epic: Analyze agent autonomy, self-correction patterns, and web interaction from OpenClaw ecosystem. Children cover individual repos/skill areas.

**Research:** See docs/research/openclaw-ecosystem.md

**Children:**
- #590 (backlog) -- OpenClaw skills: heartbeat, hooks, browser, Lobster
- #591 (backlog) -- ClawFeed: feed curation, prompt templates, source registry

**Research checklist:** All items completed.

**Recommendations (.85 confidence):**
- ADOPT: HeartbeatRunner (.90), context condenser (.85), session-memory hook (.80)
- CONSIDER: keyword skill triggers (.60), externalized prompt templates (.55)
- REJECT: Lobster (.30), MCP skill embedding (.35), third-party skill compat (.25)

**Follow-up tasks created:**
- #616 -- Implement HeartbeatRunner for proactive agent autonomy (needed)
- #619 -- Implement context condenser as PydanticAI HistoryProcessor (needed)
- #622 -- Implement session-memory hook for context persistence (important)
- #624 -- Add DAEMON_STARTUP hook event (important, split from heartbeat for atomicity)

**Architectural refinements applied during review:**
1. Condenser uses PydanticAI HistoryProcessor protocol (existing integration point) instead of custom middleware
2. Session-memory persists per-project ({workspace}/.owlbear/) not global config_dir
3. DAEMON_STARTUP hook extracted to separate task (single responsibility)
4. HeartbeatRunner runs as sibling asyncio task in run_daemon(), not new entrypoint
