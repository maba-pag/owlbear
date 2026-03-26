---
id: 590
title: 'Research: OpenClaw skills (proactive, self-improving, browser, automation)'
status: archived
priority: important
created: 2026-03-05T23:51:11.7101786+01:00
updated: 2026-03-07T18:08:11.5299478+01:00
started: 2026-03-06T21:26:13.6974322+01:00
completed: 2026-03-07T18:08:11.5299478+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 581
class: standard
---

See docs/research/openclaw-skills.md for details.

**Research checklist:**
1. Theoretical validity -- Heartbeat proactive pattern is sound (timer + checklist + suppression). Session-memory hook prevents context loss. Both are well-tested in OpenClaw (271k stars).
2. Prior art -- OpenClaw heartbeat docs, hooks docs, cron docs, browser docs, Lobster repo, skills docs (7 sources).
3. Technical feasibility -- All patterns portable to Python/PydanticAI. Heartbeat ~100 LOC, session-memory hook ~30 LOC, DAEMON_STARTUP hook 1-line enum addition.
4. Architecture fit -- Heartbeat: new HeartbeatRunner using existing HookRegistry + daemon loop. Session-memory: new hook on SESSION_END. DAEMON_STARTUP: add to HookEvent enum + emit in bootstrap.
5. Implementation approach -- Heartbeat: asyncio.sleep timer + HEARTBEAT.md file read + agent.turn() + HEARTBEAT_OK check. Session-memory: hook handler that persists context summary on session end.

**Recommendations (.85 confidence):**
- ADOPT: Heartbeat runner (.90), session-memory hook (.80), DAEMON_STARTUP event (.75)
- REJECT: Lobster workflow engine (.30, YAGNI), snapshot/ref browser system (.40, marginal gain)

**Follow-up tasks:** See research doc section 5.
