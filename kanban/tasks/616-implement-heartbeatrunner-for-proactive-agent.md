---
id: 616
title: Implement HeartbeatRunner for proactive agent autonomy
status: archived
priority: needed
created: 2026-03-07T05:20:41.9963824+01:00
updated: 2026-03-07T18:08:22.5119475+01:00
started: 2026-03-07T06:17:59.6283276+01:00
completed: 2026-03-07T18:08:22.5119475+01:00
tags:
    - scope:core
    - phase-research
    - agent
class: standard
---

Implement HeartbeatRunner: an asyncio task that runs alongside the daemon receive-loop. Configurable interval (default 30m) and active-hours window. Reads workspace HEARTBEAT.md as agent prompt context. HEARTBEAT_OK string in response suppresses further action until next tick.

Integration: starts as a sibling coroutine in run_daemon(), shares the agent and shutdown_event. Does NOT require a new daemon entrypoint. Starts regardless of autonomous_mode — guarded only by heartbeat_enabled config.

See docs/research/openclaw-ecosystem.md S3a, S4. See docs/research/heartbeat-runner.md.

depends_on: #640

AC:

- [ ] HeartbeatRunner class in src/owlbear/heartbeat.py (~80 LOC)
- [ ] __init__(agent: OwlBearAgent, channel: ChannelPlugin, interval_seconds: int, active_hours: tuple[int, int], shutdown_event: asyncio.Event, heartbeat_path: Path)
- [ ] async run() loop: check active hours -> read heartbeat_path -> agent.turn(content) -> parse HEARTBEAT_OK -> optionally channel.send() -> interruptible sleep
- [ ] Active hours: tuple[int, int] (start_hour, end_hour) in UTC. Skip tick when current UTC hour is outside the window.
- [ ] Overnight wrap-around: when start > end (e.g. (22, 6)), treat as overnight window — hour 2 is inside, hour 10 is outside.
- [ ] HEARTBEAT_OK: case-insensitive substring match in agent response. When present, suppress channel.send(). When absent, call channel.send(response) to deliver proactive findings.
- [ ] Missing HEARTBEAT.md: skip tick, log at DEBUG level. No crash, no agent.turn() call.
- [ ] Exception in agent.turn(): catch broadly, log at ERROR with exc_info, continue to next tick. Runner must never crash.
- [ ] Config fields in OwlBearSettings: heartbeat_enabled (bool, default False), heartbeat_interval (int, default 1800), heartbeat_active_hours (tuple[int,int], default (8, 22))
- [ ] field_validator for heartbeat_interval: must be > 0, following existing poll_interval pattern
- [ ] run_daemon() launches HeartbeatRunner via asyncio.create_task when heartbeat_enabled is True. Works both with and without autonomous_mode. When TaskGroup is active (autonomous), heartbeat is a third tg.create_task sibling.
- [ ] Respects shutdown_event for clean exit — uses asyncio.wait_for(shutdown_event.wait(), timeout=interval) pattern (same as poll_loop)

Architecture notes:

- Follow poll_loop's interruptible-sleep pattern: asyncio.wait_for(shutdown_event.wait(), timeout=interval)
- ChannelPlugin protocol (channels/base.py) for channel param
- OwlBearAgent.turn(prompt: str) -> str for agent interaction
- heartbeat_path: Path enables test injection (tmp_path fixture)
- No dependency on #614 (poll-dispatch) — works standalone
