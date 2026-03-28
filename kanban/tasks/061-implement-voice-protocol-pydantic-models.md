---
id: 61
title: Implement voice protocol Pydantic models
status: backlog
priority: nice-to-have
created: 2026-03-26T19:33:36.0085175+01:00
updated: 2026-03-27T08:13:14.7689857+01:00
tags:
    - phase-3
    - scope:voice
depends_on:
    - 7
class: standard
---

## Objective
Define the NDJSON protocol models for voice addon communication.

## Acceptance Criteria
- [ ] VoiceOutMessage union: transcript, partial, status, error (Literal discriminator)
- [ ] VoiceInMessage union: speak, config, shutdown (Literal discriminator)
- [ ] Serialize via model_dump_json(), deserialize via TypeAdapter.validate_json()
- [ ] Located in src/owlbear/voice/protocol.py
- [ ] Unit tests for round-trip serialization of all 7 message types

## Context
See docs/research/voice-stdio-protocol.md S3.3 and S3.7

[[2026-03-27]] Fri 08:13
## Research
Validated implementation approach (.90 confidence). See docs/research/voice-protocol-models.md.

Key findings:
- Pattern confirmed: Pydantic Literal discriminated unions + module-level TypeAdapter instances. Matches MCP SDK and v1 codebase patterns.
- Dependency gap: Added depends_on #7 (monorepo skeleton must exist for package structure).
- Location: AC says src/owlbear/voice/protocol.py. Full v2 path is packages/orchestrator/src/owlbear/voice/protocol.py.
- model_dump_json() returns str (ready for stdin.write). TypeAdapter.validate_json() accepts str or bytes.
- All 7 message types are pure data models. No mocks needed for tests.

AC refinements for architect:
- Clarify location to full monorepo path
- Add frozen=True on all protocol models (immutable value objects)
- Add module-level TypeAdapter instances (one per union)
- Add VoiceState type alias for status message state field
- Testing: ~25 tests (7 round-trip, 7 discriminator, 7 type-check, 2 unknown-type, 2 missing-field)
