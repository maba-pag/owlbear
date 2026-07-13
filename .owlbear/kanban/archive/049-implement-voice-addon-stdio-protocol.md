---
id: 49
title: Implement voice addon stdio protocol
status: archived
priority: medium
created: 2026-03-26 18:57:17.008134+01:00
updated: 2026-03-30 15:35:59.968220+02:00
started: 2026-03-30 15:31:30.839261+02:00
completed: 2026-03-30 15:31:30.839261+02:00
tags:
- phase-3
- scope:voice
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Define and implement the line-delimited JSON protocol between owlbear and the voice addon process.

## Acceptance Criteria
- [ ] Protocol spec: message types (transcript, speak, status, error)
- [ ] Voice process reads stdin for speak commands, writes stdout for transcriptions
- [ ] Owlbear side: spawn, health-check, graceful shutdown
- [ ] Unit tests for protocol serialization/deserialization

## Context
See docs/research/voice-addon-architecture.md

[[2026-03-26]] Thu 19:34
## Research
Recommend NDJSON-framed tagged messages with Pydantic discriminated unions (.85 confidence).

**Key findings:**
- Framing: NDJSON (line-delimited JSON), aligned with MCP/ACP patterns already in codebase
- Protocol: Tagged messages with type discriminator (not JSON-RPC, KISS for fire-and-forget)
- 7 message types: transcript, partial, status, error (voice out), speak, config, shutdown (voice in)
- Lifecycle: MCP three-phase shutdown (stdin close, SIGTERM, SIGKILL)
- Restart: max 3 auto-restarts before surfacing failure (ACP pattern)
- Models: Pydantic Literal discriminated unions with TypeAdapter (matches JsonlStore/SessionStore patterns)

**Follow-up tasks created at ideation:**
- #61 Voice protocol Pydantic models
- #62 Voice process manager
- #63 VoiceChannel adapter

See docs/research/voice-stdio-protocol.md for full analysis.

[[2026-03-26]] Thu 21:48
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
AC Line: Protocol spec message types - Fully covered by #61 - Redundant
AC Line: Voice process reads stdin writes stdout - Owlbear side covered by #62, voice process side is a gap - Gap noted
AC Line: Owlbear side spawn health-check graceful shutdown - Fully covered by #62 - Redundant
AC Line: Unit tests for protocol serialization - Fully covered by #61 - Redundant

### Architecture Notes
Superseded by decomposition. The researcher correctly identified that #49 bundles three responsibilities (protocol models, owlbear-side process manager, voice process side) and created atomic follow-up tasks #61, #62, #63. Approving #49 alongside those tasks creates overlapping, redundant work.

Identified gap: The voice addon subprocess main loop (the entry point that reads stdin commands, dispatches to STT/TTS engines, and writes stdout transcript messages) is not covered by any existing task. #52 scaffolds the package but does not implement the NDJSON handler.

Implicit dependency: No packages/ directory exists yet. Task #7 (monorepo skeleton) is at ideation. All voice implementation tasks require the v2 directory structure before code can be placed.

### Changes Made
- Blocked #49 to ideation (superseded by decomposition into #61, #62, #63)

### Dependencies
- #61 (protocol models): ideation
- #62 (process manager): ideation
- #63 (VoiceChannel adapter): ideation
- #52 (package scaffold): backlog, depends_on #7
- #7 (monorepo skeleton): ideation

## Audit (manual archival 2026-03-30) Superseded by decomposition into #61, #62, #63. Architect confirmed. Confidence 1.0.
