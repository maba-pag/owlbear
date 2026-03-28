---
id: 62
title: Implement voice process manager
status: backlog
priority: nice-to-have
created: 2026-03-26T19:33:42.8168161+01:00
updated: 2026-03-27T08:04:01.0153755+01:00
tags:
    - phase-3
    - scope:voice
depends_on:
    - 61
class: standard
---

## Objective

Build the owlbear-side subprocess manager for the voice addon.

## Acceptance Criteria

- [ ] Spawn voice process via asyncio.create_subprocess_exec
- [ ] Async read loop: parse NDJSON lines from stdout into VoiceOutMessage
- [ ] Async write method: serialize VoiceInMessage to stdin
- [ ] Three-phase shutdown: shutdown msg, close stdin, terminate, kill
- [ ] Health check: detect process crash via returncode/EOF
- [ ] Auto-restart up to 3 attempts
- [ ] Init timeout: 30s wait for ready status
- [ ] Unit tests with mocked subprocess

## Context

See docs/research/voice-stdio-protocol.md S3.4-S3.5. Follow MCP SDK shutdown pattern.

[[2026-03-27]] Fri 08:02

## Research

Independent class following MCP SDK patterns (.85 confidence). See docs/research/voice-process-manager.md.

Key findings:

- Independent from ProcessSupervisor (#58): different package scope, voice needs typed NDJSON I/O + init handshake + app-level shutdown. KISS: copy pattern, don't abstract for 2 users.
- 6-phase shutdown: send ShutdownMsg, close stdin, wait(5s), terminate, wait(2s), kill. Richer than ProcessSupervisor's 2-phase.
- Read loop: background asyncio.Task with asyncio.Queue buffer, parses VoiceOutMessage via TypeAdapter. Malformed JSON logged and skipped.
- Write method: model_dump_json() + newline. BrokenPipeError triggers crash/restart.
- Init handshake: 30s wait for ready status message after spawn.
- Restart budget: max 3 (same as ProcessSupervisor).
- Added depends_on: #61 (protocol models required for typed read/write).

AC refinements for architect:

- Add module location (voice package process.py)
- Clarify read loop as background asyncio.Task with Queue
- Add BrokenPipeError handling on write
- Add malformed JSON skip behavior
- Specify 6-phase shutdown (not 3)
