---
id: 1
title: ACP protocol deep-dive
status: ideation
priority: needed
created: 2026-03-26T17:18:05.2307425+01:00
updated: 2026-03-26T17:18:05.2307425+01:00
tags:
    - research
    - phase-1
    - scope:orchestrator
class: standard
---

## Objective
Research the Agent Client Protocol (ACP) and build a hello-world Python client that talks to Copilot CLI via stdin/stdout NDJSON.

## Acceptance Criteria
- [ ] Read ACP specification (agentclientprotocol/specification on GitHub)
- [ ] Document key message types: initialize, newSession, prompt, sessionUpdate
- [ ] Build minimal Python script that spawns `copilot --acp --stdio --allow-all-tools`
- [ ] Successfully send a prompt and receive streamed response
- [ ] Document error handling patterns (process crash, invalid JSON, timeout)
- [ ] Write findings to docs/research/acp-protocol.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
ACP is the communication protocol between our Python orchestrator and Copilot CLI. This is the most critical research task - everything in the orchestrator layer depends on understanding ACP well.
