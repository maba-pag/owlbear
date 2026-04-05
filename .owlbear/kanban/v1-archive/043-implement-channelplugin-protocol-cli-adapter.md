---
id: 43
title: Implement ChannelPlugin Protocol + CLI adapter
status: archived
priority: high
created: 2026-02-26T15:57:07.9642917+01:00
updated: 2026-02-27T10:00:14.619446+01:00
started: 2026-02-26T19:42:32.6099182+01:00
completed: 2026-02-27T10:00:14.619446+01:00
tags:
    - phase-2
    - agent
depends_on:
    - 37
class: standard
---

## Research findings (See docs/research/pydantic-ai-integration.md §3.2)

PydanticAI has no I/O channel concept — it expects the caller to provide user prompts. This is a genuine gap for an always-on daemon. pydantic-deepagents also doesn't abstract channels — they use stdin/stdout directly.

**Decision:** Build ChannelPlugin Protocol with send() and receive() methods. CLI adapter wraps stdin/stdout. Async I/O via asyncio stdin reader. Protocol allows future Teams/voice adapters.

Python typing.Protocol is the right choice (vs ABC) per PydanticAI conventions — they use Protocol for similar patterns (BackendProtocol in pydantic-ai-backend, SandboxProtocol).

## AC
Src: src/owlbear/channels/base.py with ChannelPlugin Protocol. src/owlbear/channels/cli.py with CLIChannel adapter. Tests cover send/receive cycle.
