# Moonshine Streaming API Patterns

> **Owning task:** #246 — Research Moonshine streaming API patterns
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

Task #240 recommended Moonshine (.82 confidence) over faster-whisper for OwlBear's local STT. Tasks #241–#245 define the migration. Task #243 specifically requires streaming STT for brainstorming sessions (30–240s, 15–90s speech increments). This research deep-dives into Moonshine's streaming API internals to inform implementation of #241–#245.

**Key questions:** What are the exact Python classes, methods, event model, audio format requirements, VAD integration, session lifecycle, and error handling? How does this map onto our `STTEngine`, `AudioRecorder`, and `VoiceChannel`?

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | Moonshine repo README (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | .95 | Full API reference, concepts, event flow guarantees, debugging options |
| 2 | `python/src/moonshine_voice/transcriber.py` | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/transcriber.py> | .95 | Transcriber, Stream, TranscriptEventListener, event dispatch implementation |
| 3 | `python/src/moonshine_voice/mic_transcriber.py` | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/mic_transcriber.py> | .90 | MicTranscriber — sounddevice integration, callback pattern |
| 4 | `python/src/moonshine_voice/moonshine_api.py` | <https://github.com/moonshine-ai/moonshine/blob/main/python/src/moonshine_voice/moonshine_api.py> | .90 | ModelArch enum, TranscriptLine/Transcript dataclasses, C API bindings |
| 5 | Moonshine v2 paper | <https://arxiv.org/abs/2602.12241> | .85 | Ergodic streaming encoder, encoder caching mechanism |
| 6 | OwlBear prior research | `docs/research/moonshine-vs-whisper.md` | .90 | Baseline comparison, migration strategy, model recommendations |
| 7 | OwlBear voice code | `src/owlbear/voice/{stt,recorder,channel}.py` | .95 | Current implementation we must integrate with |

## 3. Streaming API Internals

### 3.1 Class Hierarchy

```
Transcriber                      # Loads model, owns C library handle
├── transcribe_without_streaming()  # Batch: audio[] → Transcript (one-shot)
├── start()/stop()/add_audio()      # Delegates to default Stream
├── add_listener()                  # Delegates to default Stream
└── create_stream()                 # Factory for multi-input scenarios
    └── Stream                   # Real-time transcription session
        ├── start()/stop()       # Session lifecycle
        ├── add_audio(data, sr)  # Feed audio chunks (any size, any rate)
        ├── update_transcription()  # Manual transcription trigger
        └── add_listener()       # Event registration

MicTranscriber                   # Convenience: Transcriber + sounddevice mic
├── start()/stop()/close()
└── add_listener()               # Delegates to internal Stream
```

### 3.2 Audio Format for `add_audio()`

| Parameter | Value | Notes |
|-----------|-------|-------|
| `audio_data` | `List[float]` or numpy `float32` array | Mono PCM, range -1.0 to 1.0 |
| `sample_rate` | `int` (any rate) | Library converts to 16kHz internally |
| Chunk size | Any length | Library handles arbitrary durations |
| Channels | Mono only | Flatten multi-channel before feeding |

**Conversion from our current int16 PCM bytes:**

```python
import numpy as np
audio_float = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
```

### 3.3 Event Model

Four event types, all subclasses of `TranscriptEvent(line: TranscriptLine, stream_handle: int)`:

| Event | When fired | Guaranteed? |
|-------|-----------|-------------|
| `LineStarted` | Beginning of new speech segment detected | Exactly once per segment |
| `LineTextChanged` | Text content of current line updated | Zero or more times (suppressed if `update_interval` very large) |
| `LineUpdated` | Any line property changed (duration, audio, text) | Zero or more times |
| `LineCompleted` | Pause detected, segment finalized | Exactly once per segment, after LineStarted |
| `Error` | Exception in processing | As needed |

**Guarantees** (from README + source):

- `LineStarted` → (zero or more `LineUpdated`/`LineTextChanged`) → `LineCompleted`
- Only one active line per stream at any time
- Once `LineCompleted` fires, the line's data is immutable
- Calling `stop()` triggers `LineCompleted` for any active line
- Each line has a `line_id` (uint64) that persists from start to completion

### 3.4 Transcription Update Timing

The `Stream.add_audio()` method **automatically triggers transcription** when enough audio has accumulated:

```python
# From Stream.add_audio() source:
self._stream_time += len(audio_data) / sample_rate
if self._stream_time - self._last_update_time >= self._update_interval:
    self.update_transcription(0)
    self._last_update_time = self._stream_time
```

Default `update_interval` is **0.5 seconds**. For streaming models, most encoder work happens inside `add_audio()` (C library processes incrementally), so `update_transcription()` is mainly the final decode step — fast due to cached state.

### 3.5 VAD (Voice Activity Detection) Integration

VAD is **built into the C++ core** — no separate Python VAD library needed. Configured via `options` dict on `Transcriber` constructor:

| Option | Default | Effect |
|--------|---------|--------|
| `vad_threshold` | `0.5` | Speech detection sensitivity (lower = longer segments, more noise) |
| `vad_window_duration` | `0.5s` | Averaging window for VAD confidence |
| `vad_look_behind_sample_count` | `8192` | Samples prepended before speech start (catches onset) |
| `vad_max_segment_duration` | `15s` | Max line length before forced break |

VAD runs every 30ms. When speech ends (confidence drops below threshold averaged over window), the library marks the line complete and emits `LineCompleted`. A new segment starts when speech resumes.

**For brainstorming sessions:** The 15s `vad_max_segment_duration` default is appropriate — long monologues get broken into manageable lines. Between pauses, the library automatically segments. No manual silence handling needed.

### 3.6 Session Lifecycle

```
transcriber = Transcriber(model_path, model_arch)
transcriber.add_listener(my_listener)
transcriber.start()          # Begins session, resets transcript
# ... feed audio chunks via add_audio() ...
# ... events fire as speech is detected and transcribed ...
transcript = transcriber.stop()  # Finalizes, emits LineCompleted for active line
# transcript contains all lines from this session
transcriber.start()          # New session, fresh transcript
# ...
transcriber.close()          # Release model resources
```

**Important:** `start()` resets the transcript. Copy any data you need before calling `start()` again.

### 3.7 MicTranscriber Internals

`MicTranscriber` wraps `Transcriber` + `sounddevice.InputStream`:

- Creates a **separate stream** via `transcriber.create_stream()` (not the default stream)
- `sounddevice` callback converts `in_data` to float32 numpy array and calls `mic_stream.add_audio()`
- Uses `sounddevice` instead of PyAudio — `sd.InputStream(samplerate=16000, blocksize=1024, channels=1, dtype='float32', callback=...)`
- Does NOT support `add_audio()` — it manages audio capture internally

### 3.8 Error Handling

- **C library errors:** All C API calls return error codes, checked via `check_error()` which raises `MoonshineError`
- **Listener exceptions:** Caught and logged to stderr, do not break the stream. Error events are forwarded to other listeners.
- **Bad audio:** The library accepts any sample rate/length. Corrupted audio produces poor transcription, not crashes. Use `save_input_wav_path` option to debug.
- **Model not found:** Exception thrown at `Transcriber.__init__()` with descriptive message

### 3.9 ModelArch Enum

```python
class ModelArch(IntEnum):
    TINY = 0              # 26M, non-streaming
    BASE = 1              # 58M, non-streaming
    TINY_STREAMING = 2    # 34M, streaming, 12.00% WER
    BASE_STREAMING = 3    # streaming variant of Base
    SMALL_STREAMING = 4   # 123M, streaming, 7.84% WER ← recommended
    MEDIUM_STREAMING = 5  # 245M, streaming, 6.65% WER
```

## 4. Integration Design for OwlBear

### 4.1 Two-Mode Architecture

| Mode | API | Use case | Model |
|------|-----|----------|-------|
| **Quick command** | `transcribe_without_streaming()` | 2–10s push-to-talk commands | SMALL_STREAMING (works for both batch and streaming) |
| **Brainstorm** | `Transcriber.start/add_audio/stop` + events | 30–240s sessions, live text | SMALL_STREAMING |

Both modes use the **same model** — streaming models work for batch too (via `transcribe_without_streaming()`). No need to load two models.

### 4.2 MicTranscriber vs Manual Feed Decision

| Approach | Pros | Cons |
|----------|------|------|
| **MicTranscriber** | Simplest (KISS), handles mic + streaming in one object | Adds `sounddevice` + `numpy` deps, replaces PyAudio, less control |
| **Transcriber + manual add_audio()** | Full control, compatible with any audio source | More code, must manage audio capture separately |
| **Transcriber + our AudioRecorder** | Reuses existing code | AudioRecorder does fixed-duration recording, not streaming-friendly |

**Recommendation (.85 confidence): Use MicTranscriber for brainstorm mode.**

Rationale:

- KISS — one object handles mic capture + streaming + VAD + segmentation
- `sounddevice` is a better library than PyAudio for streaming (callback-based, numpy-native, actively maintained)
- We can add `sounddevice` and `numpy` to the `[voice]` extras (they're Moonshine's own deps anyway — `moonshine-voice` already pulls them in)
- Our `AudioRecorder` (fixed-duration recording) is incompatible with open-ended brainstorm sessions
- `PyAudio` can be removed from `[voice]` extras if no other consumers need it

For quick-command mode, use `transcribe_without_streaming()` — no mic management needed, just pass audio bytes.

### 4.3 Proposed Class Design

```
STTEngine  (stt.py — rewrite for #242)
├── __init__(model_name, model_arch)    # Lazy-loads Transcriber
├── transcribe(audio: bytes) → str      # Batch: uses transcribe_without_streaming()
└── close()                             # Release model resources

StreamingSTT  (streaming_stt.py — new for #243)
├── __init__(model_name, model_arch)    # Creates MicTranscriber
├── start() → None                      # Begins streaming session
├── stop() → str                        # Returns full transcript text
├── on_text_update: Callable            # Callback for partial text
├── on_line_complete: Callable          # Callback for completed lines
└── close()                             # Release resources

VoiceChannel  (channel.py — refactor for #244)
├── receive() → str | None              # Quick mode: record + batch transcribe
└── brainstorm(duration, on_update) → str  # Stream mode: MicTranscriber + events
```

### 4.4 Memory/CPU Estimates (Ryzen 8840U)

| Resource | Small Streaming (123M) | Tiny Streaming (34M) | Source |
|----------|----------------------|---------------------|--------|
| Model RAM | ~400 MB | ~130 MB | Moonshine repo model table [1] |
| Peak RAM (model + audio + ONNX) | ~600 MB | ~250 MB | Estimated from model + ONNX Runtime overhead |
| Response latency (x86 CPU) | 165ms | 69ms | Moonshine benchmarks [1] |
| Steady-state CPU (active speech) | ~10–15% | ~5–8% | Estimated: ONNX Runtime encoder on 8 Zen4 cores |
| Idle CPU (silence, VAD only) | ~1–2% | ~1–2% | VAD is a tiny Silero model running every 30ms |

These estimates are conservative. The Ryzen 8840U (8-core Zen 4, 4.5GHz boost) is significantly faster than the generic "Linux x86" benchmarks (which were run on unspecified hardware). Actual latency will likely be lower.

### 4.5 Gaps and Risks

| Gap | Impact | Mitigation |
|-----|--------|------------|
| `sounddevice` replaces `PyAudio` as mic library | Low — both are audio capture, `sounddevice` is better | `sounddevice` is already a Moonshine dep |
| No `add_audio()` on MicTranscriber | Can't feed external audio in brainstorm mode | Use raw `Transcriber` + `Stream` if custom sources needed |
| Alpha status (v0.0.49) | API may change between versions | Pin version, test on upgrade |
| `numpy` becomes a required dep for `[voice]` | Low — it's already pulled in by `moonshine-voice` | Already transitive, just make explicit |
| `update_interval` tuning | Too frequent = more CPU, too rare = stale text | Default 0.5s is fine for brainstorming; configurable |
| Thread safety of listener callbacks | Callbacks fire on whichever thread calls `add_audio` | MicTranscriber: callbacks fire on sounddevice audio thread — keep handlers lightweight, queue to main thread if needed |

## 5. Recommendation (.85 confidence)

**Two-mode STT architecture using a single Moonshine model:**

1. **Batch mode** (`STTEngine.transcribe()`) — for quick commands. Uses `transcribe_without_streaming()`. Drops in where faster-whisper was.
2. **Streaming mode** (`StreamingSTT`) — for brainstorming. Uses `MicTranscriber` which handles mic + streaming + VAD. Returns partial text via callbacks, full text on `stop()`.

**Model choice:** `SMALL_STREAMING` (123M, 7.84% WER, 165ms latency). Works for both modes. Make configurable.

**Dependency changes:** Replace `faster-whisper` + `pyaudio` with `moonshine-voice` (which brings `sounddevice`, `numpy`). Keep `pyttsx3` for TTS.

## 6. Impact on Tasks #241–#245

| Task | Status | AC Changes Needed |
|------|--------|-------------------|
| #241 (Swap deps) | AC adequate | Add: also replace `pyaudio` with `sounddevice` (Moonshine transitive dep). Add `numpy` explicitly. |
| #242 (Batch STT rewrite) | AC adequate | Add: convert int16 PCM bytes to float32 array. Use `ModelArch.SMALL_STREAMING` default. |
| #243 (Streaming STT) | **Needs refinement** | Replace vague "streaming API" with specific MicTranscriber pattern. Add: `on_text_update` callback, `on_line_complete` callback, `sounddevice` thread safety note. |
| #244 (VoiceChannel brainstorm) | AC adequate | Add: MicTranscriber replaces AudioRecorder for brainstorm mode. `sounddevice` handles mic capture. |
| #245 (Remove faster-whisper) | AC adequate | Add: also remove `pyaudio` references if it's fully replaced by `sounddevice`. |

## 7. Follow-up Tasks

Existing tasks #241–#245 cover the implementation. This research recommends AC updates rather than new tasks. One new task is needed for the `sounddevice`/`pyaudio` decision cleanup:

```
kanban\kanban-md.exe edit 243 --body "## Context\nImplement Moonshine streaming STT using MicTranscriber for brainstorming sessions.\n\n## Acceptance Criteria\n- [ ] New StreamingSTT class in src/owlbear/voice/streaming_stt.py\n- [ ] Uses MicTranscriber(model_path, model_arch=SMALL_STREAMING, update_interval=0.5)\n- [ ] start() begins mic capture + streaming transcription\n- [ ] stop() returns full transcript as str, calls MicTranscriber.stop()\n- [ ] on_text_update callback fires on LineTextChanged events\n- [ ] on_line_complete callback fires on LineCompleted events\n- [ ] Thread safety: callbacks queued to asyncio event loop (sounddevice fires on audio thread)\n- [ ] close() releases MicTranscriber + Transcriber resources\n- [ ] Configurable model_arch (default SMALL_STREAMING) and update_interval (default 0.5s)\n- [ ] All tests mock the moonshine_voice C library layer\n- [ ] TDD: write failing tests first\n\n## Design Reference\nSee docs/research/moonshine-streaming.md §4.3 for class design.\n\n## Notes\n- MicTranscriber handles mic + VAD + streaming internally\n- Events fire on sounddevice audio thread — use asyncio.get_event_loop().call_soon_threadsafe()\n- VAD auto-segments speech at pauses (default vad_max_segment_duration=15s)\n- LineCompleted carries final immutable text for each segment"
```

```
kanban\kanban-md.exe edit 241 --body "## Context\nReplace faster-whisper with moonshine-voice in pyproject.toml [voice] extras.\n\n## Acceptance Criteria\n- [ ] pyproject.toml [voice] group: moonshine-voice>=0.0.49,<0.1.0 replaces faster-whisper\n- [ ] pyaudio removed from [voice] group (sounddevice is a moonshine-voice transitive dep)\n- [ ] numpy added explicitly to [voice] group\n- [ ] pyttsx3 remains (TTS unchanged)\n- [ ] uv sync --extra voice installs moonshine-voice + sounddevice + numpy successfully\n- [ ] No import errors on import owlbear.voice\n\n## Notes\n- moonshine-voice v0.0.49, MIT license, ONNX Runtime core\n- sounddevice replaces pyaudio for mic capture (pulled in by moonshine-voice)\n- See docs/research/moonshine-streaming.md §4.2"
```

```
kanban\kanban-md.exe edit 242 --body "## Context\nRewrite STTEngine to use Moonshine batch mode (transcribe_without_streaming).\n\n## Acceptance Criteria\n- [ ] STTEngine wraps moonshine_voice.Transcriber (not faster-whisper)\n- [ ] transcribe(audio: bytes, language='en') -> str API preserved\n- [ ] Audio conversion: int16 PCM bytes → float32 numpy array (/ 32768.0)\n- [ ] Uses transcribe_without_streaming(audio_data, sample_rate=16000)\n- [ ] Returns concatenated text from Transcript.lines\n- [ ] Default model: ModelArch.SMALL_STREAMING (works in batch mode too)\n- [ ] Model path resolved via moonshine_voice.get_model_for_language()\n- [ ] Lazy model loading preserved (Transcriber created on first transcribe call)\n- [ ] ImportError with helpful message when moonshine-voice not installed\n- [ ] All existing STT tests updated + passing\n- [ ] TDD: write failing tests first\n\n## Design Reference\nSee docs/research/moonshine-streaming.md §3.2 for audio format, §4.1 for two-mode arch."
```

```
kanban\kanban-md.exe edit 245 --body "## Context\nClean sweep: remove all traces of faster-whisper AND pyaudio from the codebase.\n\n## Acceptance Criteria\n- [ ] No import of faster_whisper anywhere in src/ or tests/\n- [ ] No import of pyaudio anywhere in src/ or tests/\n- [ ] No mention of faster-whisper or pyaudio in pyproject.toml\n- [ ] No mention of faster-whisper in docs (except research docs which are historical)\n- [ ] No mention of whisper in code comments (except research context)\n- [ ] AudioRecorder updated or removed (sounddevice replaces pyaudio for mic capture)\n- [ ] All voice tests pass without faster-whisper or pyaudio installed\n- [ ] ruff check clean\n\n## Notes\n- pyaudio is replaced by sounddevice (Moonshine transitive dep, used via MicTranscriber)\n- AudioRecorder may be removed if no non-voice consumers exist"
```
