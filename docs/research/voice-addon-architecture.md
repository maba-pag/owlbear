# Voice Addon Architecture

> **Owning task:** #30 — Research voice addon architecture
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

v1 integrated voice as a `ChannelPlugin` (moonshine-voice STT + pyttsx3 TTS + sounddevice mic capture). v2 treats voice as a separate system. This research evaluates whether a lightweight addon integration makes sense, what models to use, and what the interface between owlbear and voice should look like.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Moonshine Voice | <https://github.com/moonshine-ai/moonshine> | .95 | Streaming STT, 26-245M params, 34-269ms latency, built-in VAD+diarization, MIT (English) |
| OpenAI Whisper | <https://github.com/openai/whisper> | .80 | Reference STT, 39M-1.5B params, batch-only, 30s fixed window, MIT |
| Kokoro TTS | <https://github.com/hexgrad/kokoro> | .85 | 82M param neural TTS, Apache-2.0, high quality, requires espeak-ng+torch |
| Piper TTS (piper1-gpl) | <https://github.com/OHF-Voice/piper1-gpl> | .70 | Fast local neural TTS, C++ core, **GPL-3.0** (license change from original MIT), looking for maintainers |
| Silero VAD | <https://github.com/snakers4/silero-vad> | .80 | VAD, <1ms/chunk, MIT, 2MB model, built into Moonshine |
| v1 voice module | `v1/src/owlbear/voice/` | .90 | Prior art — ChannelPlugin, STT/TTS/StreamingSTT wrappers, brainstorm mode |
| v1 voice-io research | `docs/research/voice-io.md` | .85 | Prior research — recommended faster-whisper+pyttsx3 (v1 later switched to moonshine) |

## 3. Analysis

### 3.1 STT Model Comparison

| Criterion | Moonshine Small Streaming (.90) | Whisper small.en via faster-whisper (.70) | Whisper tiny.en (.55) |
|-----------|-------------------------------|----------------------------------------|---------------------|
| Params | 123M | 244M | 39M |
| WER | 7.84% | 8.59% | 12.81% |
| Latency (live, 5s phrase) | 165ms | ~2000ms | ~280ms |
| Streaming | Yes (incremental cache) | No (30s fixed window) | No |
| Built-in VAD+diarization | Yes | VAD via Silero addon | No |
| RAM footprint | ~300MB | ~2GB | ~1GB |
| Dependency weight | onnxruntime (~50MB) | ctranslate2 (~200MB) or torch (~2GB) | torch (~2GB) |
| License | MIT (English) | MIT | MIT |

**Verdict (.90):** Moonshine dominates for live voice. Sub-200ms latency, streaming support, built-in VAD, smallest footprint. v1 already validated this choice.

### 3.2 TTS Model Comparison

| Criterion | Kokoro (.80) | pyttsx3 (.60) | Piper (.50) |
|-----------|-------------|--------------|-------------|
| Quality | Near-human, expressive | Robotic but clear | Good neural quality |
| Params | 82M | N/A (system engine) | 16-60M per voice |
| Dependencies | torch+espeak-ng | pywin32/espeak | ONNX Runtime, espeak-ng |
| RAM | ~500MB (torch loaded) | ~10MB | ~100MB |
| License | Apache-2.0 | MIT | **GPL-3.0** |
| Maintenance | Active | Low activity | Looking for maintainers |
| Streaming | Generator-based | Sync runAndWait() | Streaming via C++ API |

**Verdict (.75):** Kokoro for quality; pyttsx3 for KISS. Piper's GPL-3.0 license is a concern for an MIT project. Recommend Kokoro as primary with pyttsx3 as zero-dep fallback.

### 3.3 Integration Architecture

| Architecture | Coupling | KISS | Resource isolation | Latency | Score |
|-------------|---------|------|-------------------|---------|-------|
| **A. Standalone process, stdio pipes** | Low | High (.85) | Full (separate process) | ~10ms IPC | .85 |
| **B. MCP server (voice-as-tool)** | Low | Medium (.70) | Full | ~50ms JSON-RPC | .70 |
| **C. In-process ChannelPlugin** (v1) | High | High (.80) | None (shared event loop) | ~0ms | .65 |
| **D. Fully independent app** | Zero | Highest (.90) | Full | N/A (no integration) | .50 |

**Analysis:**

- **A (stdio pipes):** Owlbear spawns a voice process. Voice process captures mic, runs STT, sends text lines on stdout. Owlbear sends TTS text on stdin. Clean separation. Process crash doesn't take down owlbear. KISS: just line-delimited JSON over stdio.
- **B (MCP server):** Voice registers as an MCP tool server. Owlbear calls `voice.listen()` and `voice.speak()` as tools. Heavier protocol but aligns with the broader MCP ecosystem. Overkill for a simple bidirectional pipe.
- **C (in-process):** v1 approach. Tight coupling, shared memory, torch/onnxruntime loaded in main process. Model crash or OOM affects owlbear. Simpler code but worse isolation.
- **D (fully independent):** Voice is a separate app with its own UI. No integration with owlbear. User manually switches between voice app and owlbear. Lowest value.

**Verdict (.85):** Option A — standalone process with stdio pipes. Owlbear spawns it, voice sends transcribed text lines, owlbear sends text to speak. Process isolation keeps ML model failures contained. v1's in-process approach wasn't wrong for an MVP, but v2 should isolate the heavy ML workload.

### 3.4 Resource Assessment (Laptop: 16GB RAM, 8-core CPU)

| Component | RAM | CPU (idle) | CPU (active) | Battery impact |
|-----------|-----|-----------|-------------|---------------|
| Moonshine Small Streaming | ~300MB | ~0% | 10-20% (during speech) | Low — only active during utterance |
| Kokoro TTS | ~500MB (torch) | ~0% | 15-25% (during synthesis) | Low — synthesis is brief |
| pyttsx3 TTS | ~10MB | ~0% | <5% | Negligible |
| Silero VAD (always-on) | ~50MB | 1-2% | 1-2% | Minimal |
| **Total (Moonshine+Kokoro)** | **~850MB** | **1-2%** | **25-45%** | **Moderate during use** |
| **Total (Moonshine+pyttsx3)** | **~350MB** | **1-2%** | **10-20%** | **Low** |

Moonshine+pyttsx3 is the minimal config (~350MB, negligible idle cost). Kokoro adds ~500MB but massive quality improvement. Both are workable on a 16GB laptop.

### 3.5 Worth It Assessment

| Factor | Standalone voice app | Integrated addon | Verdict |
|--------|---------------------|-----------------|---------|
| User workflow | Alt-tab to voice app, copy text | Seamless — speak and owlbear acts | Addon wins |
| Development effort | Zero (just use existing tools) | Medium (~2-3 tasks) | Standalone wins |
| Maintenance burden | Zero | Low (stdio protocol is stable) | Standalone wins slightly |
| Value to user | Low (manual copy) | High (voice as channel) | Addon wins clearly |

**Verdict (.80):** Worth building as a lightweight addon. The stdio interface is simple enough (~100 LOC each side) that the development cost is low relative to the UX gain.

## 4. Recommendation (.85 confidence)

**Build voice as a standalone Python process that owlbear spawns and communicates with via line-delimited JSON on stdio.**

- **STT:** Moonshine Voice (Small Streaming, English) — validated by v1, best latency
- **TTS primary:** Kokoro (82M, Apache-2.0) — near-human quality, permissive license
- **TTS fallback:** pyttsx3 — zero-dep offline fallback for when torch is unavailable
- **Interface:** Line-delimited JSON on stdin/stdout. Messages: `{"type":"transcript","text":"..."}` outbound, `{"type":"speak","text":"..."}` inbound
- **Lifecycle:** Owlbear spawns voice process on demand (`subprocess.Popen`), monitors health, kills on shutdown. Voice process is optional — owlbear works fine without it
- **Package:** Separate `owlbear-voice` package in the uv workspace (optional dependency)

**Risks:**
- Moonshine non-English models use community license (non-commercial) — English-only for now
- Kokoro requires espeak-ng system package on Windows (installer available)
- torch dependency for Kokoro adds ~2GB disk; pyttsx3 fallback avoids this

## 5. Follow-up Tasks

1. Implement voice addon stdio protocol

Priority rationale: `nice-to-have` because it unlocks integration but does not block core non-voice workflows.
Dependencies: none.
One-line AC: define and implement line-delimited JSON transcript/speak protocol between owlbear and the voice process.
Create command:

```powershell
kanban\kanban-md.exe create "Implement voice addon stdio protocol" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nDefine and implement the line-delimited JSON protocol between owlbear and the voice addon process.\n\n## Acceptance Criteria\n- [ ] Protocol spec: message types (transcript, speak, status, error)\n- [ ] Voice process reads stdin for speak commands, writes stdout for transcriptions\n- [ ] Owlbear side: spawn, health-check, graceful shutdown\n- [ ] Unit tests for protocol serialization/deserialization\n\n## Context\nSee docs/research/voice-addon-architecture.md"
```

Created task ID: `#49`.

2. Implement voice addon STT with Moonshine

Priority rationale: `nice-to-have` because voice input is an enhancement and can ship incrementally.
Dependencies: none.
One-line AC: build streaming STT with Moonshine and emit transcript JSON lines on stdout.
Create command:

```powershell
kanban\kanban-md.exe create "Implement voice addon STT with Moonshine" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nBuild the STT component of the voice addon using moonshine-voice.\n\n## Acceptance Criteria\n- [ ] MicTranscriber-based streaming STT with VAD\n- [ ] Outputs transcript lines as JSON on stdout\n- [ ] Configurable model arch and language\n- [ ] Lazy model loading on first activation\n- [ ] Unit tests with mocked moonshine-voice\n\n## Context\nSee docs/research/voice-addon-architecture.md. Port patterns from v1/src/owlbear/voice/streaming_stt.py"
```

Created task ID: `#50`.

3. Implement voice addon TTS with Kokoro + pyttsx3 fallback

Priority rationale: `nice-to-have` because spoken output improves UX but is not required for base text workflows.
Dependencies: none.
One-line AC: build TTS pipeline with Kokoro as primary and pyttsx3 fallback for no-torch environments.
Create command:

```powershell
kanban\kanban-md.exe create "Implement voice addon TTS with Kokoro + pyttsx3 fallback" --priority nice-to-have --status ideation --tags phase-3,scope:voice --body "## Objective\nBuild the TTS component with Kokoro as primary and pyttsx3 as fallback.\n\n## Acceptance Criteria\n- [ ] Kokoro TTS: generate audio from text, play via sounddevice\n- [ ] pyttsx3 fallback when torch/kokoro not installed\n- [ ] Reads speak commands from stdin JSON\n- [ ] Configurable voice and speed\n- [ ] Unit tests with mocked dependencies\n\n## Context\nSee docs/research/voice-addon-architecture.md"
```

Created task ID: `#51`.

4. Create owlbear-voice workspace package

Priority rationale: `nice-to-have` because package scaffolding enables clean workspace boundaries for later voice implementation.
Dependencies: none.
One-line AC: scaffold a dedicated workspace package for voice runtime dependencies and entry point.
Create command:

```powershell
kanban\kanban-md.exe create "Create owlbear-voice workspace package" --priority nice-to-have --status ideation --tags phase-3,scope:voice,config --body "## Objective\nScaffold the owlbear-voice package as a uv workspace member.\n\n## Acceptance Criteria\n- [ ] pyproject.toml with moonshine-voice, kokoro, sounddevice deps\n- [ ] Optional extras: [kokoro] for quality TTS, base has pyttsx3 only\n- [ ] Entry point script for voice process\n- [ ] Package importable from owlbear workspace\n\n## Context\nSee docs/research/voice-addon-architecture.md and docs/research/monorepo-tooling.md"
```

Created task ID: `#52`.
