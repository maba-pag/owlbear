---
id: 19
title: Build ACP client library
status: ideation
priority: needed
created: 2026-03-26T17:22:08.8522322+01:00
updated: 2026-03-26T17:25:18.9268646+01:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 1
    - 7
class: standard
---

## Objective
Build the Python ACP client that spawns Copilot CLI and communicates via NDJSON over stdin/stdout.

## Acceptance Criteria
- [ ] Module in packages/orchestrator/src/owlbear/acp/
- [ ] spawn_copilot() - starts copilot --acp --stdio --allow-all-tools as subprocess
- [ ] send_initialize() - sends initialize message, receives response
- [ ] send_new_session() - creates a session with working directory and MCP config
- [ ] send_prompt() - sends a prompt and streams sessionUpdate responses
- [ ] Proper process lifecycle: start, health check, graceful shutdown, kill on timeout
- [ ] NDJSON parsing with error recovery (malformed lines)
- [ ] Async interface (asyncio subprocess)
- [ ] Timeout handling per message exchange
- [ ] Unit tests with mocked subprocess (no real Copilot CLI needed)
- [ ] Integration test with real Copilot CLI (hello world prompt)

## Context
Depends on R1 (ACP deep-dive) and F1 (monorepo skeleton). This is the core of the orchestrator - ~50 lines of real code that connects Python to Copilot CLI.
