---
id: 63
title: Implement VoiceChannel adapter
status: backlog
priority: nice-to-have
created: 2026-03-26T19:33:48.9743371+01:00
updated: 2026-03-27T02:53:17.9990323+01:00
tags:
    - phase-3
    - scope:voice
depends_on:
    - 61
    - 62
class: standard
---

## Objective
Build the ChannelPlugin adapter that wraps the voice process manager.

## Acceptance Criteria
- [ ] Implements ChannelPlugin protocol (name, send, receive)
- [ ] send() writes speak message to voice process stdin
- [ ] receive() reads next transcript message from voice process stdout
- [ ] Lazy process spawn on first receive() call
- [ ] Delegates lifecycle to VoiceProcessManager
- [ ] Unit tests with mocked process manager

## Context
See docs/research/voice-stdio-protocol.md S3.6. Mirrors v1 VoiceChannel pattern.

[[2026-03-27]] Fri 02:53
## Research
Thin adapter wrapping VoiceProcessManager (.90 confidence). See docs/research/voicechannel-adapter.md.

Key findings:
- ~60 LOC adapter: constructor DI for process manager, core 3 methods (name/send/receive)
- send() creates SpeakMsg, delegates to mgr.write(); receive() filters for TranscriptMsg
- Lazy spawn on first receive(); None on EOF
- Inherits ChannelPlugin defaults for send_file/send_blocks/send_image
- No brainstorm/partial handling in v1 of adapter (YAGNI)
- Added depends_on: #61 (protocol models), #62 (process manager)
- AC is sound and complete, no new tasks needed
