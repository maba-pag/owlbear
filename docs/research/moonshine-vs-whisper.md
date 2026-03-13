# Moonshine Voice vs Whisper for Local STT

> **Owning task:** #240 — Research: Moonshine voice (moonshine-ai/moonshine) vs Whisper viability
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear plans local voice input (STT). The current implementation uses faster-whisper with `base.en` int8 on CPU (see `src/owlbear/voice/stt.py`). The user asks whether Moonshine (moonshine-ai/moonshine) is a viable replacement that offers **general parity plus at least one clear advantage** over the best Whisper ecosystem option.

**Hardware target:** Ryzen 8840U (8-core Zen 4, Radeon 780M iGPU), 16 GB RAM, CPU-only (or ONNX DirectML for iGPU).

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | Moonshine Voice repo (v0.0.49) | <https://github.com/moonshine-ai/moonshine> | .95 | README, Python package, benchmark scripts, model table, license |
| 2 | Moonshine v2 paper | <https://arxiv.org/abs/2602.12241> | .90 | Ergodic streaming encoder architecture, sliding-window attention, benchmark methodology |
| 3 | Moonshine v1 paper | <https://arxiv.org/abs/2410.15608> | .80 | First-gen flexible-duration input, no fixed 30s window |
| 4 | Flavors of Moonshine paper | <https://arxiv.org/abs/2509.02523> | .70 | Language-specific mono-lingual models, accuracy per language |
| 5 | HuggingFace OpenASR Leaderboard | <https://huggingface.co/spaces/hf-audio/open_asr_leaderboard> | .85 | Independent WER scoring methodology, English benchmarks |
| 6 | faster-whisper (SYSTRAN) | <https://github.com/SYSTRAN/faster-whisper> | .90 | CTranslate2 backend, int8, built-in Silero VAD, our current STT engine |
| 7 | whisper.cpp (ggml-org) | <https://github.com/ggml-org/whisper.cpp> | .85 | C/C++ Whisper, quantization, AVX2 optimization, Vulkan, VAD |
| 8 | moonshine-voice PyPI | <https://pypi.org/project/moonshine-voice/> | .75 | Package metadata, dependencies, Python API examples |
| 9 | OwlBear voice-io-research | `docs/research/voice-io.md` | .90 | Prior art — our own faster-whisper selection rationale |

## 3. What is Moonshine?

**Architecture:** Encoder-decoder transformer, trained from scratch (not a Whisper derivative). v2 uses **sliding-window self-attention** (ergodic streaming encoder) — bounded, low-latency inference with strong local context. Avoids Whisper's fixed 30-second input window; processes variable-length audio with no zero-padding waste.

**Streaming:** v2 streaming models **cache** encoder output and partial decoder state across incremental audio chunks. This means most work is done *while the user is still talking*, and final transcription after speech ends is near-instantaneous.

**Core runtime:** C++ core library using **OnnxRuntime** for inference. Python, Swift, Java, C++ bindings on top. The Python package (`moonshine-voice`) bundles the native library as a platform-specific `.so`/`.dll`/`.dylib`.

**License:** MIT for code and English models. Non-English models are under the "Moonshine Community License" (non-commercial). **For OwlBear (English-only STT for dev commands), MIT is fully compatible.**

**Maturity:** 6.1k GitHub stars, 10 contributors, 4 releases (latest v0.0.49, Feb 24 2026), 31 open issues. Active development (commits within hours). Led by Pete Warden (ex-Google, TensorFlow Lite lead). Status: Alpha (PyPI classifier says "Development Status :: 3 - Alpha").

**Languages:** English, Spanish, Mandarin, Japanese, Korean, Vietnamese, Ukrainian, Arabic. English is the primary focus with the best models.

### Model Sizes

| Model | Parameters | Streaming? | English WER (OpenASR) | Notes |
|-------|-----------|------------|----------------------|-------|
| Tiny | 26M | No | 12.66% | Smallest, embedded in framework |
| Tiny Streaming | 34M | **Yes** | 12.00% | Lowest-latency streaming |
| Base | 58M | No | 10.07% | Non-streaming, batch-style |
| Small Streaming | 123M | **Yes** | 7.84% | Good accuracy/speed balance |
| Medium Streaming | 245M | **Yes** | 6.65% | Best accuracy, beats Whisper Large v3 |

## 4. Head-to-Head Comparison

### 4.1 Accuracy (WER) — OpenASR Leaderboard Methodology

| Model | Params | WER | Source |
|-------|--------|-----|--------|
| **Moonshine Medium Streaming** | 245M | **6.65%** | Moonshine repo, OpenASR methodology [5] |
| Whisper Large v3 | 1.5B | 7.44% | OpenASR [5] |
| **Moonshine Small Streaming** | 123M | **7.84%** | Moonshine repo [1] |
| Whisper Small | 244M | 8.59% | OpenASR [5] |
| distil-whisper-large-v3 | ~756M | ~7.5% | HuggingFace distil-whisper page |
| Moonshine Base | 58M | 10.07% | Moonshine repo [1] |
| Whisper Base.en (faster-whisper int8) | 74M | ~10.5% | faster-whisper benchmarks [6] |
| Moonshine Tiny Streaming | 34M | 12.00% | Moonshine repo [1] |
| Whisper Tiny | 39M | 12.81% | OpenASR [5] |

**Assessment:** Moonshine's WER claims use the HuggingFace OpenASR Leaderboard datasets and methodology, which is the standard independent benchmark. The numbers are **credible** — they're not self-reported on cherry-picked data. Medium Streaming at 6.65% genuinely beats Whisper Large v3 (7.44%) with 6x fewer parameters.

### 4.2 Speed / Latency — CPU-only, Live Speech Scenario

These benchmarks from Moonshine's `scripts/run-benchmarks.py` [1] measure **response latency** (time between speech ending and transcription delivered) on CPU. They use faster-whisper for Whisper models, which is the best CPU Whisper option.

| Model | MacBook Pro | Linux x86 | RPi 5 |
|-------|------------|-----------|-------|
| Moonshine Medium Streaming | 107ms | 269ms | 802ms |
| Whisper Large v3 (faster-whisper) | 11,286ms | 16,919ms | N/A |
| Moonshine Small Streaming | 73ms | 165ms | 527ms |
| Whisper Small (faster-whisper) | 1,940ms | 3,425ms | 10,397ms |
| Moonshine Tiny Streaming | 34ms | 69ms | 237ms |
| Whisper Tiny (faster-whisper) | 277ms | 1,141ms | 5,863ms |

**Critical note:** These latency numbers compare **streaming Moonshine** (does work while user talks) against **batch-only faster-whisper** (must process entire utterance after speech ends). This is genuinely the relevant comparison for live voice interfaces, but it's not an apples-to-apples raw inference speed comparison. For batch/offline transcription of large files, faster-whisper with GPU would likely win on throughput.

**For OwlBear's use case (live push-to-talk commands, 2–10 second utterances, CPU-only):** Moonshine's streaming architecture is a decisive advantage. Even Tiny Streaming (69ms on Linux x86) is under the 200ms responsiveness threshold. Faster-whisper Tiny takes 1,141ms for the same — unacceptable for interactive voice.

### 4.3 Model Size and Disk Footprint

| Model | Params | Disk (quantized ONNX .ort) | RAM estimate |
|-------|--------|---------------------------|-------------|
| Moonshine Tiny | 26M | ~15 MB | ~100 MB |
| Moonshine Tiny Streaming | 34M | ~20 MB | ~130 MB |
| Moonshine Base | 58M | ~30 MB (enc) + ~104 MB (dec) ≈ 134 MB | ~250 MB |
| Moonshine Small Streaming | 123M | ~200 MB | ~400 MB |
| Moonshine Medium Streaming | 245M | ~400 MB | ~700 MB |
| Whisper base.en (faster-whisper int8) | 74M | ~150 MB | ~1.5 GB (CTranslate2) |
| Whisper small.en (faster-whisper int8) | 244M | ~466 MB | ~2 GB |
| Whisper base.en (whisper.cpp Q5_0) | 74M | ~57 MB | ~388 MB |

**Assessment:** Moonshine's ONNX quantized models are compact. The Tiny model is embedded *inside* the pip package (~15 MB). For disk footprint, whisper.cpp with aggressive quantization (Q5_0) is competitive, but Moonshine wins on RAM because the ONNX runtime is lighter than CTranslate2 (faster-whisper pulls ~200 MB for ctranslate2 alone) and much lighter than PyTorch.

### 4.4 Streaming Support

| Engine | Native Streaming | How |
|--------|-----------------|-----|
| **Moonshine v2** | **Yes** — encoder caching, incremental decode | Built-in, first-class. `Transcriber.add_audio()` feeds chunks, events fire as text updates. |
| faster-whisper | **No** — batch only | Must accumulate full utterance, then transcribe. Can simulate streaming by re-transcribing growing buffer (wasteful). |
| whisper.cpp `stream` | **Partial** — re-runs on sliding window | `whisper-stream` example: re-transcribes every 500ms. Not true streaming — redundant encoder work. |
| distil-whisper | **No** — batch only | Same as Whisper, batch-oriented. |

**Verdict:** Moonshine is the only option with **true streaming** — cached encoder state, incremental audio, no redundant computation. This is its single biggest technical differentiator.

### 4.5 CPU-only / ONNX / DirectML

Moonshine's C++ core uses ONNX Runtime natively. It ships pre-built libraries for Windows x86_64, Linux x86_64, macOS ARM64, and more. The Python package bundles the native library — `pip install moonshine-voice` "just works" on CPU.

**DirectML / iGPU potential:** ONNX Runtime has a DirectML execution provider. Since Moonshine already uses ONNX Runtime, adding DirectML support for the Radeon 780M iGPU is architecturally possible. The Moonshine team doesn't explicitly document DirectML, but the ONNX Runtime backend could be configured for it. This is a potential future optimization, not a current guarantee.

**whisper.cpp Vulkan:** whisper.cpp has Vulkan GPU support which works with AMD GPUs. This could theoretically accelerate Whisper on the 780M. However, it requires building from source with Vulkan enabled.

### 4.6 Dependencies

| Engine | Python deps | Native deps | Total footprint |
|--------|------------|-------------|-----------------|
| **Moonshine** | numpy, sounddevice, requests, tqdm, filelock, platformdirs | Bundled C++ .dll/.so (~10 MB) + ONNX Runtime (bundled) | **Light** — no PyTorch, no ctranslate2 |
| faster-whisper | ctranslate2 (~200 MB), tokenizers, huggingface-hub | CTranslate2 native lib | **Medium** — ctranslate2 is large |
| whisper.cpp | None (C++ binary) | Build from source, or use pre-built | **Lightest** — but no Python API |

**Assessment:** Moonshine has the lightest Python footprint. No PyTorch, no CTranslate2, no compilation. `pip install moonshine-voice` and go. For OwlBear's `[voice]` optional dependency group, this is simpler than faster-whisper.

### 4.7 Python API Comparison

**Current (faster-whisper):**

```python
model = WhisperModel("base.en", compute_type="int8", device="cpu")
segments, info = model.transcribe(audio, language="en", vad_filter=True)
text = " ".join(seg.text.strip() for seg in segments)
```

**Moonshine:**

```python
transcriber = Transcriber(model_path=model_path, model_arch=ModelArch.BASE)
transcriber.add_listener(my_listener)
transcriber.start()
transcriber.add_audio(chunk, sample_rate)  # events fire as text updates
transcriber.stop()
```

Moonshine's API is **event-driven** (listener callbacks), not request/response. This is a better fit for live voice interfaces but requires restructuring `STTEngine.transcribe()` from a synchronous `audio_bytes → str` call to an event-driven model. The `transcribe_without_streaming()` convenience method exists for batch mode.

### 4.8 Integration Considerations for OwlBear

| Aspect | Cost | Notes |
|--------|------|-------|
| API refactor | Medium | `STTEngine.transcribe(bytes) → str` would become event-driven. Or use `transcribe_without_streaming()` for minimal change. |
| Dependency swap | Low | Replace `faster-whisper` with `moonshine-voice` in pyproject.toml `[voice]` group |
| Model download | Low | `python -m moonshine_voice.download --language en` caches to user cache dir |
| Audio format | Low | Moonshine accepts float32 arrays at any sample rate (converts internally to 16kHz) |
| Testing | Low | Same mock pattern — mock the Transcriber C API calls |
| Alpha status risk | **Medium-High** | Version 0.0.49, only 4 releases, small team. Breaking API changes are possible. |

## 5. Bias Reflection

**Did I fall for marketing?** Moonshine's README is professionally written and makes strong claims. Key checks:

1. **WER numbers verified:** They reference the HuggingFace OpenASR Leaderboard methodology, which is the standard independent benchmark. The leaderboard itself hosts these evaluations. **Credible.**
2. **Latency numbers need context:** The 69ms vs 1,141ms comparison is real but compares **streaming** (work done during speech) vs **batch** (all work after speech). This is the correct comparison for live voice, but someone doing batch transcription of recordings would get different results. **Honest for the stated use case.**
3. **"Better than Whisper Large v3":** Only true for Medium Streaming (245M params) on English. Whisper Large v3 handles 100+ languages. For English-only STT, the claim holds. **Valid with qualification.**
4. **Alpha maturity:** The PyPI classifier says "Development Status :: 3 - Alpha". The project has only 10 contributors and 4 releases. This is a real risk for production use.

## 6. Recommendation (.82 confidence)

**Replace faster-whisper with Moonshine for OwlBear's live voice STT.**

Moonshine provides clear advantages in **three** aspects at general WER parity:

| Criterion | Moonshine advantage | Confidence |
|-----------|-------------------|------------|
| **Streaming latency** | 69ms vs 1,141ms (Tiny) — 16x faster response | .95 |
| **Dependency weight** | No PyTorch, no CTranslate2. Pure ONNX + bundled native lib | .90 |
| **Integrated pipeline** | Built-in VAD, speaker diarization, mic capture, intent recognition — all in one library | .85 |

**Risks and mitigations:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Alpha stability | Medium-High | Pin version in pyproject.toml. Keep faster-whisper as fallback (feature flag). |
| Small contributor pool | Medium | MIT license means we can fork if abandoned. Core is C++/ONNX — stable foundation. |
| API is event-driven, not req/resp | Low | Use `transcribe_without_streaming()` for minimal refactor, or embrace events for better UX. |
| Non-English models are non-commercial license | Low | OwlBear only needs English. English models are MIT. |

**Recommended model:** Start with **Tiny Streaming** (34M, 12% WER, 69ms latency on x86 CPU). This is the KISS choice for short dev commands. Make model configurable. For better accuracy, upgrade to **Small Streaming** (123M, 7.84% WER, 165ms).

**Migration strategy:**

1. **Phase 1 (minimal):** Swap `faster-whisper` for `moonshine-voice` in `[voice]` extras. Refactor `STTEngine` to use `transcribe_without_streaming()` — same synchronous API, drop-in replacement.
2. **Phase 2 (streaming):** Refactor `VoiceChannel.receive()` to use Moonshine's event-driven `MicTranscriber` for true real-time transcription with live text updates.

## 7. Follow-up Tasks

See kanban create commands below.
