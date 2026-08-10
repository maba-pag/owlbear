# Voice I/O Module Design Research

> **Owning task:** #49 — Design voice I/O module
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs local voice I/O for hands-free interaction. The tech stack table lists "Whisper STT + pyttsx3 TTS" as planned. This research validates that choice, compares alternatives, and recommends an architecture that fits the existing `ChannelPlugin` protocol (`name`, `send()`, `receive()`).

Key constraints: must work offline on a laptop (no cloud APIs required), Python 3.12+, low priority (keep it simple).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| faster-whisper | <https://github.com/SYSTRAN/faster-whisper> | .95 | CTranslate2-based Whisper — 4x faster, int8 quantization, built-in Silero VAD, no FFmpeg needed |
| openai/whisper | <https://github.com/openai/whisper> | .85 | Reference Whisper implementation — model size table, accuracy baselines |
| pyttsx3 | <https://pypi.org/project/pyttsx3/> | .80 | Offline TTS — SAPI5 on Windows, eSpeak on Linux, zero-cost |
| edge-tts | <https://github.com/rany2/edge-tts> | .60 | Microsoft Edge online TTS — high quality but requires internet |
| SpeechRecognition | <https://pypi.org/project/SpeechRecognition/> | .75 | Unified STT API — wraps Whisper, faster-whisper, Google, Vosk; handles microphone via PyAudio |
| Silero VAD | <https://github.com/snakers4/silero-vad> | .85 | Voice Activity Detection — <1ms per chunk, built into faster-whisper |
| PyAudio | <https://pypi.org/project/PyAudio/> | .70 | PortAudio Python bindings — microphone capture, prebuilt Windows wheels |
| Disler hooks (agent-patterns §2.7) | <https://github.com/disler/claude-code-hooks-mastery> | .75 | TTS priority chain pattern (ElevenLabs → OpenAI → pyttsx3 fallback) |

## 3. Analysis

### 3.1 STT Engine Comparison

| Criterion | openai/whisper (.65) | faster-whisper (.90) | SpeechRecognition + faster-whisper (.70) | Cloud APIs (.30) |
|-----------|---------------------|---------------------|----------------------------------------|-----------------|
| Speed (small, CPU, 13min audio) | 6m58s (fp32) | 1m42s (int8) | Same as faster-whisper backend | N/A |
| Memory (small, CPU) | 2335MB | 1477MB (int8) | Same | N/A |
| FFmpeg required | Yes | No (PyAV bundled) | No | No |
| VAD built-in | No | Yes (Silero VAD) | No | Varies |
| Python 3.12 | Yes | Yes (≥3.9) | Yes (≥3.9) | Yes |
| Quantization (int8) | No | Yes (CPU + GPU) | Yes | N/A |
| Offline | Yes | Yes | Yes (with local backend) | No |
| Dependency weight | torch (~2GB) | ctranslate2 (~200MB) | +pyaudio +speech_recognition | SDK |
| API simplicity | `model.transcribe()` | `model.transcribe()` | `recognizer.recognize_faster_whisper()` | Varies |
| KISS score | Medium | High | Medium (extra abstraction layer) | Low |

**Verdict:** faster-whisper dominates. 4x faster, half the memory, no FFmpeg, built-in VAD, int8 quantization. SpeechRecognition adds a microphone abstraction but also adds an unnecessary wrapper — we can use PyAudio directly for mic capture (simpler).

### 3.2 Whisper Model Size Tradeoffs (for dev-command English speech)

| Model | Parameters | VRAM/RAM | Relative Speed | English WER | Recommendation |
|-------|-----------|----------|----------------|-------------|----------------|
| tiny.en | 39M | ~1GB | ~10x | Higher | Too inaccurate for commands |
| base.en | 74M | ~1GB | ~7x | Good | (.80) Sweet spot for dev commands |
| small.en | 244M | ~2GB | ~4x | Better | (.85) Best accuracy/speed balance |
| medium.en | 769M | ~5GB | ~2x | Very good | Overkill for short commands |
| turbo | 809M | ~6GB | ~8x (GPU) | Excellent | GPU-only, too heavy for CPU |

**Recommendation (.85):** Start with `base.en` (fast, tiny, good enough for English dev commands). Make model configurable so users can upgrade to `small.en` if accuracy matters more than latency. With faster-whisper int8, `base.en` transcribes a 13-min file in ~20s on CPU — short voice commands (2-5s) would complete in <1s.

### 3.3 TTS Engine Comparison

| Criterion | pyttsx3 (.80) | edge-tts (.50) | ElevenLabs/OpenAI (.20) |
|-----------|--------------|----------------|------------------------|
| Offline | Yes | No (needs internet) | No |
| Cost | Free | Free (Edge API) | Paid |
| Quality | Robotic but clear | Natural, many voices | Best quality |
| Windows (SAPI5) | Native | N/A | N/A |
| Linux (eSpeak) | Yes | N/A | N/A |
| Async API | No (sync engine.runAndWait()) | Yes (async generator) | Yes |
| Dependencies | pywin32 (Windows) / espeak (Linux) | aiohttp | openai SDK |
| KISS score | High | Medium | Low |
| Latency | Instant (local) | ~200ms+ (network) | ~500ms+ (network) |

**Verdict (.80):** pyttsx3 for MVP. It's offline, instant, zero-cost. The voice is robotic but perfectly adequate for status announcements ("Task complete", "Tests passing"). The sync API is a minor annoyance — wrap in `asyncio.to_thread()`. Edge-tts is a nice future upgrade for better voice quality but violates the offline-first principle.

### 3.4 Audio Input Strategy

| Approach | Description | KISS | Recommendation |
|----------|-------------|------|----------------|
| Push-to-talk (hotkey) | User presses key → record → transcribe | High (.90) | **Start here** — simplest, no false activations |
| Always-on + VAD | Silero VAD detects speech → transcribe | Medium (.60) | Phase 2 — needs wake word to avoid constant transcription |
| Wake word + VAD | "Hey Bear" → VAD → transcribe | Low (.40) | Complex — needs separate wake word model (Porcupine, etc.) |

**Recommendation (.90):** Push-to-talk. Record while key held (or record for N seconds after keypress). Transcribe the captured audio chunk. No false activations, no always-on mic concerns. Silero VAD (built into faster-whisper) can trim silence from the captured chunk.

### 3.5 Architecture Fit

Voice I/O maps cleanly to the `ChannelPlugin` protocol:

```
VoiceChannel (ChannelPlugin)
├── name → "voice"
├── send(message) → pyttsx3 TTS speaks the message
├── receive(prompt?) → record mic audio → faster-whisper STT → return text
│
├── _stt: STTEngine  (faster-whisper wrapper)
├── _tts: TTSEngine  (pyttsx3 wrapper)
└── _recorder: AudioRecorder  (PyAudio mic capture)
```

**Module layout** (`src/owlbear/voice/`):

| File | Responsibility |
|------|---------------|
| `stt.py` | `STTEngine` — loads faster-whisper model, `transcribe(audio_bytes) → str` |
| `tts.py` | `TTSEngine` — wraps pyttsx3, `speak(text) → None` (async via to_thread) |
| `recorder.py` | `AudioRecorder` — PyAudio mic capture, `record(duration) → bytes` |
| `channel.py` | `VoiceChannel` — composes STT+TTS+Recorder, implements `ChannelPlugin` |
| `__init__.py` | Exports `VoiceChannel` |

**Key design decisions:**

1. **Optional dependency group** — `voice = ["faster-whisper>=1.0", "pyaudio>=0.2.14", "pyttsx3>=2.90"]` in pyproject.toml. Voice is not a core feature.
2. **Lazy model loading** — Load Whisper model on first `receive()` call, not at init. Model download happens once (~150MB for base.en).
3. **Configurable model** — `VoiceSettings(model_size="base.en", compute_type="int8", device="cpu")` in pydantic-settings.
4. **Sync-to-async bridge** — Both pyttsx3 and PyAudio are synchronous. Wrap in `asyncio.to_thread()` to not block the event loop.

## 4. Recommendation (.85 confidence)

**Use faster-whisper (int8, base.en) + pyttsx3 + PyAudio with push-to-talk input.**

This is the KISS-optimal stack:

- **STT:** faster-whisper with int8 quantization on CPU. `base.en` model for speed, configurable to `small.en`. Built-in Silero VAD trims silence.
- **TTS:** pyttsx3 using SAPI5 on Windows. Synchronous calls wrapped in `asyncio.to_thread()`.
- **Audio:** PyAudio for microphone capture. Prebuilt Windows wheels, no compilation needed.
- **Input mode:** Push-to-talk (record on keypress). Simplest UX, no false triggers.
- **Architecture:** `VoiceChannel` implements `ChannelPlugin`, lives in `src/owlbear/voice/`.
- **Dependencies:** Optional `[voice]` extra in pyproject.toml.

Risks and mitigations:

- **pyttsx3 async issue:** sync engine blocks event loop → mitigate with `asyncio.to_thread()`
- **Model download size:** ~150MB first run → document in README, cache in HuggingFace default cache
- **PyAudio installation:** prebuilt wheel on Windows; may need portaudio on Linux → document in README

## 5. Follow-up Tasks

1. Create `src/owlbear/voice/stt.py` — STTEngine wrapping faster-whisper
2. Create `src/owlbear/voice/tts.py` — TTSEngine wrapping pyttsx3
3. Create `src/owlbear/voice/recorder.py` — AudioRecorder wrapping PyAudio
4. Create `src/owlbear/voice/channel.py` — VoiceChannel implementing ChannelPlugin
5. Add `[voice]` optional dependency group to pyproject.toml
6. Write tests for all voice components (mock audio streams, mock pyttsx3 engine)
7. Add `owlbear voice` CLI subcommand for testing voice I/O
