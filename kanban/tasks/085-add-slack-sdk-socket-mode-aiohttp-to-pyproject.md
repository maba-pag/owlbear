---
id: 85
title: Add slack_sdk[socket_mode] + aiohttp to pyproject.toml
status: done
priority: high
created: 2026-02-27T01:44:55.5607936+01:00
updated: 2026-02-27T02:18:09.4630386+01:00
started: 2026-02-27T02:14:18.5734065+01:00
completed: 2026-02-27T02:18:09.4630386+01:00
tags:
    - phase-4
    - comms
    - slack
    - config
class: standard
---

Add Slack SDK dependency for Socket Mode integration. See docs/slack-integration-research.md.

AC:
- Add slack_sdk[socket_mode] to pyproject.toml dependencies
- Add aiohttp to dependencies (required by slack_sdk async socket_mode)
- Run uv sync, verify clean install
- Verify import: from slack_sdk.socket_mode.aiohttp import SocketModeClient
