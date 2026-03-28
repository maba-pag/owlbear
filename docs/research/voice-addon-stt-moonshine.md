# Voice Addon STT with Moonshine

> **Owning task:** #50 — Implement voice addon STT with Moonshine
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #50 asks for the STT component of the voice addon process. Per the architecture research (#30, `docs/research/voice-addon-architecture.md`), voice runs as a standalone process communicating via line-delimited JSON on stdio. This research validates the Moonshine Python API, identifies porting patterns from v1, and defines the implementation approach.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Moonshine Voice GitHub (v0.0.51) | <https://github.com/moonshine-ai/moonshine> | .95 | Full Python API: `MicTranscriber`, `TranscriptEventListener`, `ModelArch`, `get_model_for_language()` |
| Moonshine `mic_transcriber.py` source | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/mic_transcriber.py> | .90 | `MicTranscriber` wraps `Transcriber` + `sounddevice.InputStream`, event dispatch on audio thread |
| Moonshine `transcriber.py` source | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/transcriber.py> | .90 | `Stream._emit()` dispatches typed events, `TranscriptEventListener` ABC, ctypes C bindings |
| Moonshine Ollama voice example | <https://github.com/moonshine-ai/moonshine/blob/main/examples/python/ollama-voice/ollama_voice.py> | .80 | Real-world `TranscriptEventListener` subclass pattern, `on_line_completed` for downstream processing |
| v1 `StreamingSTT` | `v1/src/owlbear/voice/streaming_stt.py` | .90 | Lazy creation, async bridge via `call_soon_threadsafe`, `start()`/`stop()`/`close()` lifecycle |
| v1 `STTEngine` (batch) | `v1/src/owlbear/voice/stt.py` | .75 | `_ensure_transcriber()` lazy loading pattern, `transcribe_without_streaming()` API |

## 3. Analysis

### 3.1 Moonshine v0.0.51 API Surface (for STT)

Key classes the implementation needs:

| Class/Function | Role | Thread safety |
|----------------|------|---------------|
| `MicTranscriber(model_path, model_arch, update_interval, options)` | Owns `Transcriber` + `sounddevice.InputStream` | Callbacks fire on sounddevice audio thread |
| `TranscriptEventListener` | ABC with `on_line_started/text_changed/completed/error` | Must handle cross-thread if writing stdout |
| `get_model_for_language(language, model_arch)` | Returns `(model_path, model_arch)` with auto-download | Blocking I/O on first call |
| `ModelArch` | Enum: `TINY`, `BASE`, `TINY_STREAMING`, `SMALL_STREAMING`, `MEDIUM_STREAMING` | N/A |

### 3.2 v1 Patterns to Port vs. Discard

| Pattern | v1 | v2 decision | Rationale |
|---------|-----|------------|-----------|
| Lazy `MicTranscriber` creation | `_create_mic_transcriber()` on first `start()` | **Port** (.90) | Avoids loading ONNX model until needed |
| Async bridge (`call_soon_threadsafe`) | `_bridge()` wraps callbacks for asyncio loop | **Discard** (.85) | Stdio process has no asyncio loop; use `threading.Lock` on stdout |
| `start()`/`stop()`/`close()` lifecycle | Three-phase in `StreamingSTT` | **Port** (.90) | Clean state machine for stdin command handling |
| Batch transcription (`transcribe_without_streaming`) | `STTEngine.transcribe()` | **Discard for now** (.70) | Stdio process focuses on live streaming; batch is out of scope |
| `VoiceChannel` ChannelPlugin | Tight coupling to owlbear event loop | **Discard** (.95) | v2 uses process isolation per architecture decision |

### 3.3 Thread Safety for stdout

Moonshine callbacks fire on the sounddevice audio thread. Writing JSON to stdout must be thread-safe. Options:

| Approach | Complexity | Reliability | Score |
|----------|-----------|-------------|-------|
| `threading.Lock` around `sys.stdout.write` + `flush` | Low | High | .85 |
| `queue.Queue` + dedicated writer thread | Medium | Higher | .75 |
| `print()` (already thread-safe in CPython) + explicit `flush` | Lowest | Adequate | .80 |

**Verdict (.85):** `threading.Lock` around `sys.stdout.buffer.write()` + `flush()`. Simple, explicit, and the Ollama voice example validates that direct writes from callbacks work fine at Moonshine event frequencies (~2-4 events/second).

### 3.4 JSON Message Format (aligns with #49 protocol)

```json
{"type":"transcript","event":"line_started","line_id":123,"text":"","speaker":null}
{"type":"transcript","event":"text_changed","line_id":123,"text":"Hello world"}
{"type":"transcript","event":"line_completed","line_id":123,"text":"Hello world.","duration":2.1,"speaker_index":0}
{"type":"error","code":"mic_unavailable","message":"..."}
{"type":"status","state":"ready"}
```

### 3.5 Configuration Surface

| Setting | Source | Default | Notes |
|---------|--------|---------|-------|
| `language` | CLI arg or stdin config | `"en"` | Passed to `get_model_for_language()` |
| `model_arch` | CLI arg or stdin config | `ModelArch.SMALL_STREAMING` | Best quality/speed for live voice |
| `update_interval` | CLI arg | `0.5` | Seconds between transcription updates |
| `vad_threshold` | Options dict | `0.5` | Sensitivity of speech detection |
| `identify_speakers` | Options dict | `true` | Enable diarization |

## 4. Recommendation (.85 confidence)

Implement a `TranscriptJsonListener(TranscriptEventListener)` that serializes Moonshine events to line-delimited JSON on stdout, wrapped in an `SttRunner` class with lazy `MicTranscriber` creation. Use `threading.Lock` for thread-safe writes. Handle lifecycle via stdin JSON commands (`start`, `stop`, `configure`).

**Risks:**

- sounddevice requires PortAudio (bundled in pip wheel, but manual install on some Linux distros)
- Model download blocks on first run (mitigate: emit `{"type":"status","state":"downloading"}` before download)
- ONNX Runtime CPU-only by default (adequate for target laptop; GPU acceleration is an optimization task)

## 5. Follow-up Tasks

Task #50 AC is already well-scoped. No new tasks needed — the existing AC covers:

- MicTranscriber-based streaming STT with VAD
- JSON stdout output
- Configurable model arch and language
- Lazy model loading
- Unit tests with mocked moonshine-voice

The implementation depends on #49 (stdio protocol spec) for message format alignment, and #52 (owlbear-voice package) for the pyproject.toml scaffold.
