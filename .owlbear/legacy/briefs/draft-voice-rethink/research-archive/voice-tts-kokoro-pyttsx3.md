# Voice Addon TTS: Kokoro + pyttsx3 Fallback

> **Owning task:** #51 — Implement voice addon TTS with Kokoro and pyttsx3 fallback
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #51 implements the TTS component of the voice addon (architecture decided in #30, see `docs/research/voice-addon-architecture.md`). This research validates the AC, identifies the correct API patterns for Kokoro and pyttsx3, evaluates the fallback mechanism, and recommends an implementation approach.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Kokoro GitHub + PyPI | <https://github.com/hexgrad/kokoro>, <https://pypi.org/project/kokoro/> | .95 | KPipeline API, generator-based streaming, voice loading, speed control |
| Kokoro pipeline.py source | <https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py> | .90 | Result dataclass (.audio → torch.FloatTensor @ 24kHz), chunked generation |
| pyttsx3 PyPI | <https://pypi.org/project/pyttsx3/> | .85 | Engine init, say/runAndWait, rate/volume/voice properties, SAPI5/espeak backends |
| sounddevice docs | <https://python-sounddevice.readthedocs.io/en/latest/usage.html> | .80 | sd.play(array, rate), sd.wait(), non-blocking playback of numpy arrays |
| v1 TTSEngine | `v1/src/owlbear/voice/tts.py` | .90 | Lazy pyttsx3 init, asyncio.to_thread wrapper, rate/volume config |
| voice-addon-architecture | `docs/research/voice-addon-architecture.md` | .95 | Architecture decision: stdio pipes, Kokoro primary + pyttsx3 fallback |

## 3. Analysis

### 3.1 Kokoro API Pattern

Kokoro uses a generator pipeline. Key API surface:

```python
from kokoro import KPipeline

pipeline = KPipeline(lang_code="a")  # downloads model from HF on first use
generator = pipeline(text, voice="af_heart", speed=1.0)
for result in generator:
    audio = result.audio  # torch.FloatTensor, 24kHz mono
```

| Property | Value |
|----------|-------|
| Sample rate | 24000 Hz |
| Audio format | torch.FloatTensor (convert via `.numpy()` for sounddevice) |
| Chunking | Generator yields per-sentence/paragraph segments |
| Voices | String names (e.g. `af_heart`, `af_bella`) or `.pt` file path |
| Speed | Float multiplier (default 1.0) or callable |
| Model size | ~82M params, ~500MB RAM with torch |
| System dep | espeak-ng (MSI installer on Windows) |

### 3.2 pyttsx3 API Pattern (from PyPI docs + v1 code)

```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty("rate", 200)  # WPM
engine.setProperty("volume", 1.0)  # 0.0–1.0
engine.say(text)
engine.runAndWait()  # blocking
```

| Property | Value |
|----------|-------|
| Windows backend | SAPI5 (built-in, zero deps) |
| Linux backend | espeak-ng |
| Blocking | Yes — `runAndWait()` blocks the thread |
| RAM | ~10MB |
| Quality | Robotic but clear |

### 3.3 Fallback Detection Pattern

| Approach | KISS | Reliability | Score |
|----------|------|-------------|-------|
| **A. Import-time flag** (`try: import kokoro` at module top) | High | High — fails fast | .85 |
| **B. Runtime factory** (check on each speak call) | Low | Medium — repeated overhead | .55 |
| **C. Config toggle** (user sets `tts_engine=kokoro\|pyttsx3`) | Medium | High — explicit | .70 |

**Verdict (.85):** Option A. Set `_kokoro_available = True/False` at import time. The voice process is long-lived, so detection once at startup is sufficient. v1 used this exact pattern (`try: import pyttsx3 except ImportError: pyttsx3 = None`).

### 3.4 Audio Playback Integration

| Method | For | Pattern |
|--------|-----|---------|
| Kokoro | `sd.play(result.audio.numpy(), 24000); sd.wait()` | Blocks per chunk |
| pyttsx3 | `engine.say(text); engine.runAndWait()` | Blocks on engine |

Kokoro's generator allows streaming: play each chunk as it's synthesized. For the stdio-based voice process, the TTS handler reads `{"type":"speak","text":"..."}` from stdin, synthesizes, plays audio to speakers, and optionally sends `{"type":"speak_done"}` on stdout.

### 3.5 Configuration Mapping

| Config field | Kokoro | pyttsx3 | Type |
|-------------|--------|---------|------|
| `voice` | Voice name string (`af_heart`) | Voice ID from `getProperty('voices')` | str |
| `speed` | Float multiplier (1.0 = normal) | WPM integer (200 = normal) | float → int conversion |
| `language` | `lang_code` in KPipeline constructor | N/A (engine-level) | str |

**Design note:** Use a normalized config (voice name + speed float) and map to each backend internally. Speed 1.0 → Kokoro speed=1.0, pyttsx3 rate=200.

### 3.6 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| espeak-ng not installed on Windows | Kokoro fails at G2P | Detect at init, fall back to pyttsx3 with warning |
| torch download ~2GB | Long first install | Document in package extras; pyttsx3 works without torch |
| Model download from HuggingFace | Offline failure | Lazy download, cache locally, warn on failure |
| pyttsx3 thread safety | runAndWait is not reentrant | Serialize speak calls (one at a time) — already the case in a stdin-reading loop |

## 4. Recommendation (.85 confidence)

Implement TTS as a module in the owlbear-voice package with:

1. **Backend protocol** — `TTSBackend` with `speak(text: str) -> None` (blocking, called from the voice process's main loop)
2. **KokoroTTSBackend** — uses `KPipeline` generator + `sounddevice.play()` per chunk
3. **Pyttsx3TTSBackend** — mirrors v1's lazy init + `say()`/`runAndWait()` pattern
4. **Factory function** — `create_tts_backend(config)` → tries Kokoro first, falls back to pyttsx3
5. **Stdin loop** — reads JSON lines, dispatches `speak` commands to the active backend

AC refinements based on research:
- "Kokoro TTS: generate audio from text, play via sounddevice" — confirmed: `KPipeline.__call__` yields `Result` with `.audio` (torch tensor @ 24kHz), play with `sd.play(audio.numpy(), 24000)`
- "pyttsx3 fallback when torch/kokoro not installed" — confirmed: import-time detection, same pattern as v1
- "Reads speak commands from stdin JSON" — confirmed: line-delimited JSON, `{"type":"speak","text":"..."}`
- "Configurable voice and speed" — confirmed: normalized config mapped to each backend
- "Unit tests with mocked dependencies" — mock `kokoro.KPipeline` and `pyttsx3.init()`, test both backends + fallback logic + stdin parsing

## 5. Follow-up Tasks

Task #51's AC is well-scoped and validated. No new tasks needed — the AC covers the full TTS implementation scope. The architect should refine the AC with the API details above.
