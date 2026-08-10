# VoiceChannel Adapter Research

> **Owning task:** #63 — Implement VoiceChannel adapter
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #63 (decomposed from #49) requires a `VoiceChannel` that implements `ChannelPlugin` by wrapping `VoiceProcessManager`. The v1 VoiceChannel did STT/TTS in-process; v2 delegates ML work to an external subprocess over NDJSON stdio. This research validates the adapter design, identifies implementation patterns from prior art, and confirms dependencies.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK stdio client | `github.com/modelcontextprotocol/python-sdk/.../stdio.py` | .90 — subprocess wrapper with read/write streams, shutdown |
| 2 | v1 VoiceChannel | `v1/src/owlbear/voice/channel.py` | .90 — prior art, same ChannelPlugin protocol, DI pattern |
| 3 | v1 ChannelPlugin protocol | `v1/src/owlbear/channels/base.py` | .95 — protocol definition with default methods |
| 4 | ChannelPlugin extension research | `docs/research/channel-protocol-extension.md` | .90 — send_file/send_blocks/send_image defaults |
| 5 | Voice stdio protocol design | `docs/research/voice-stdio-protocol.md` S3.6 | .95 — architecture spec for VoiceChannel |
| 6 | v1 CLIChannel | `v1/src/owlbear/channels/cli.py` | .80 — reference thin ChannelPlugin adapter |
| 7 | v1 test_channels.py | `v1/tests/test_channels.py` | .85 — ChannelPlugin compliance test patterns |

## 3. Analysis

### 3.1 Adapter Shape: Thin vs Rich

| Approach | LOC est. | KISS | Testability | Score |
|----------|----------|------|-------------|-------|
| **A. Thin adapter** (core 3 methods + lazy spawn) | ~60 | High (.90) | High — mock process mgr | .90 |
| **B. Rich adapter** (brainstorm mode, partial handling) | ~150 | Low (.60) | Medium — more state | .55 |

v1 VoiceChannel was 239 LOC because it handled brainstorm mode, sounddevice recording, and STT/TTS orchestration directly. v2 delegates all that to the subprocess — the adapter is much thinner. `partial` messages (for live display) are a brainstorm-mode concern, not a core adapter concern. YAGNI: start thin, add later.

### 3.2 Key Design Decisions

| Decision | Choice | Rationale (Sources) |
|----------|--------|---------------------|
| DI for process manager | Constructor injection | v1 pattern (Source 2): `__init__(stt, tts, streaming_stt)` |
| Lazy spawn trigger | First `receive()` call | AC requirement + v1 pattern (lazy model loading) |
| send() semantics | Create `SpeakMsg`, delegate to mgr | Protocol spec (Source 5) S3.3 |
| receive() filtering | Return only `TranscriptMsg.text` | `partial`/`status`/`error` are not user input |
| receive() EOF | Return `None` | ChannelPlugin contract (Source 3): None = disconnect |
| Rich methods (send_file etc.) | Inherit ChannelPlugin defaults | Extension research (Source 4): defaults delegate to send() |

### 3.3 Message Flow

```
User speaks → [voice process: mic + STT] → stdout: TranscriptMsg
  → VoiceProcessManager.read() → VoiceChannel.receive() → "text"

Agent responds → VoiceChannel.send("text") → SpeakMsg
  → VoiceProcessManager.write() → stdin → [voice process: TTS + speaker]
```

### 3.4 Dependency Chain

| Upstream task | What it provides | Required by |
|---------------|-----------------|-------------|
| #61 (protocol models) | `SpeakMsg`, `TranscriptMsg`, `VoiceOutMessage` | send(), receive() type construction |
| #62 (process manager) | `VoiceProcessManager` with start/write/read/stop | All lifecycle delegation |
| #52 (workspace package) | Module structure at `owlbear_voice/` | File location |

**Critical gap:** #63 has no `depends_on` set. Must add #61 and #62.

### 3.5 Testing Strategy (from Source 7 patterns)

| Test | What it verifies |
|------|------------------|
| Protocol compliance | `isinstance(VoiceChannel(...), ChannelPlugin)` |
| name property | Returns `"voice"` |
| send() serialization | Creates SpeakMsg, calls mgr.write() |
| receive() transcript | Returns text from TranscriptMsg |
| receive() filtering | Skips partial/status/error messages |
| receive() EOF | Returns None on process disconnect |
| Lazy spawn | Process not started until first receive() |
| send_file/send_blocks/send_image | Inherited defaults work (calls send()) |

## 4. Recommendation (.90 confidence)

The AC is sound and complete. Implementation should follow the thin adapter pattern (~60 LOC):

- Constructor takes `VoiceProcessManager` (DI, testable)
- `name` → `"voice"`
- `send(message)` → `SpeakMsg(text=message, interrupt=False)` → `mgr.write(msg)`
- `receive()` → loop `mgr.read()`, skip non-transcript, return `text` (or `None` on EOF)
- Lazy spawn: `receive()` calls `mgr.start()` if not running
- No brainstorm/partial handling in v1 of the adapter (YAGNI)

**Risk:** If `VoiceProcessManager` API changes during #62 implementation, the adapter must adapt. Low risk — the interface is narrow (start, stop, read, write).

## 5. Follow-up Tasks

No new tasks needed — #63 AC is complete. Dependencies must be set:

```
kanban\kanban-md.exe edit 63 --add-dep 61
kanban\kanban-md.exe edit 63 --add-dep 62
```
