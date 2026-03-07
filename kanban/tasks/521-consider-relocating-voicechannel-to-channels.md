---
id: 521
title: Consider relocating VoiceChannel to channels/ package
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:30.0955145+01:00
updated: 2026-03-07T00:08:20.7874957+01:00
started: 2026-03-07T00:06:02.9207545+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

ARC-03: All channel adapters (CLI, Slack) live under channels/ except VoiceChannel under voice/. voice/ conflates I/O abstraction with voice processing. Option: move VoiceChannel to channels/voice.py (importing STT/TTS from voice/).\n\n## Research Decision (.85 confidence): Keep VoiceChannel in voice/\n\nResearch checklist items 1-3: N/A -- trivial relocation decision.\n\n**Layout:** channels/ has thin I/O wrappers (cli.py, slack.py). voice/ is a cohesive subsystem: channel.py + stt.py + tts.py + streaming_stt.py, gated behind uv sync --extra voice.\n\n**Rationale:** VoiceChannel imports STTEngine, TTSEngine, and lazily StreamingSTT -- tight coupling to 3 sibling modules. Relocating to channels/voice.py would create cross-package deps without improving cohesion. CLI/Slack are self-contained thin adapters; VoiceChannel orchestrates an audio pipeline. KISS: current layout works. YAGNI: don't restructure for consistency alone.\n\n**Action:** No code change. Decision documented. Close task.\n\nAC: design decision documented -- DONE.
