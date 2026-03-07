---
id: 638
title: Tests for HeartbeatRunner
status: backlog
priority: needed
created: 2026-03-07T06:35:11.2825439+01:00
updated: 2026-03-07T13:59:31.1227923+01:00
started: 2026-03-07T13:59:31.1227923+01:00
tags:
    - scope:core
    - agent
    - test
class: standard
---

TDD test suite for HeartbeatRunner (#616). Write tests BEFORE implementation.

AC:
- [ ] test_heartbeat_tick_calls_agent_turn: Patch asyncio.sleep, supply HEARTBEAT.md content, assert agent.turn() called with file content
- [ ] test_heartbeat_ok_suppresses_channel_send: Mock agent returning 'HEARTBEAT_OK', assert channel.send() NOT called
- [ ] test_heartbeat_non_ok_sends_to_channel: Mock agent returning findings, assert channel.send() called with response
- [ ] test_heartbeat_active_hours_skip: Set current UTC hour outside (8, 22) window, assert agent.turn() NOT called
- [ ] test_heartbeat_active_hours_wraparound: Set active_hours=(22, 6), test hour=2 (inside) and hour=10 (outside)
- [ ] test_heartbeat_missing_file_skips: Remove HEARTBEAT.md, assert tick logged at DEBUG, no crash, no agent.turn() call
- [ ] test_heartbeat_shutdown_mid_sleep: Set shutdown_event during sleep, assert clean exit within timeout
- [ ] test_heartbeat_agent_exception_continues: Mock agent.turn() raising, assert logged + runner continues to next tick
- [ ] test_heartbeat_disabled_config_skips_launch: heartbeat_enabled=False, assert runner not started in run_daemon()

Architecture notes:
- Use tmp_path for HEARTBEAT.md (injectable heartbeat_path)
- AsyncMock for agent.turn() and channel.send()
- Patch datetime.now(UTC) for active-hours tests
- Follow existing test_daemon.py patterns
