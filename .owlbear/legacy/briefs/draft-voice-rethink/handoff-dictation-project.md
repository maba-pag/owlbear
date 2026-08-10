# Offline Dictation Tool — Project Input

> This document is the output of an OwlBear ideation session (Voice Interaction Rethink, April 2026).
> It serves as the input file for a new project's ideation — defining requirements, constraints,
> landscape findings, and open design questions for a standalone offline dictation tool.

## Problem

No offline, end-to-end dictation tool exists that meets all of these constraints:
- Works fully offline (steady-state; one-time model download acceptable)
- Runs on corporate Windows without admin access (user-space install only)
- Handles the full dictation pipeline: activation → microphone capture → speech-to-text → text insertion
- Works in VS Code (editor buffers + Copilot Chat input — the primary target)

Windows Win+H is deactivated by corporate policy (and is cloud-backed regardless). Talon is overkill and expensive ($120/yr). whisper.cpp and Vosk are STT engines only (no text injection). Dragon needs admin. Existing VS Code voice extensions are unmaintained or cloud-backed.

## Desired Outcomes

1. **Press a hotkey, speak, text appears in VS Code.** Editor buffers, Copilot Chat input, askQuestions input. Offline. No admin.
2. **Accuracy and latency that make dictation preferable to typing for prose.** Target: <500ms latency, 1s acceptable, 2s triggers rethink. Accuracy must handle technical vocabulary reasonably.
3. **Daily-usable, not demo-ware.** Abandoned-after-a-week is failure. Must handle corrections, punctuation, and the reality of hybrid input (dictate prose, type code tokens).

## Hard Constraints

| Constraint | Detail |
|-----------|--------|
| Offline STT | Transcription engine runs locally. No cloud speech services. |
| No admin | User-space installs only (pip, uv, portable binaries). No MSI, no UAC. |
| Corporate Windows | Locked-down enterprise laptop. EDR/DLP may interfere with audio stack. |
| No persistent recordings | No audio files saved. Transcripts not persisted beyond the active editing session. |
| User IS InfoSec | Constraints are self-imposed. No external approval gate — but constraints are real. |

## Landscape Findings (from OwlBear ideation M3)

### Ecosystem Evaluation

| Tool | Offline | No Admin | End-to-End | VS Code | Verdict |
|------|---------|----------|-----------|---------|---------|
| Win+H | No | Yes | Yes | Yes | Deactivated by corporate policy; also cloud-backed |
| Talon | Yes | Yes | Yes | Yes | Overkill, expensive, steep curve |
| whisper.cpp | Yes | Yes | STT only | Needs wrapper | Best bare engine, no injection |
| Vosk | Yes | Yes | STT only | Needs wrapper | Lower accuracy |
| VS Code Voice ext | Yes | Yes | Partial | Yes | Unmaintained |
| Dragon | Yes | Needs admin | Yes | Yes | $300+, needs admin |
| Moonshine | Yes | Yes | STT only | Needs wrapper | Streaming, VAD, proven in OwlBear v2 |

**Conclusion:** Building is required. No drop-in solution exists.

### Text Injection Options

| Method | Reliability | Latency | VS Code | Notes |
|--------|------------|---------|---------|-------|
| VS Code Extension API (`TextEditor.edit()`) | Highest | ~10-50ms | Editor only | Native, cleanest for editor buffers |
| Clipboard + Ctrl+V | High | ~50-200ms | Everywhere | Overwrites clipboard; clunky for rapid dictation |
| SendKeys / pyautogui | Low | Variable | Sometimes | Slow, unreliable in some apps |
| Windows UI Automation | Medium | ~50-100ms | Yes | Complex, needs Python bindings |
| `executeCommand('type')` | Unknown | Unknown | Chat (maybe) | Unvalidated for Copilot Chat — needs spike |

### STT Engine Assessment: Moonshine

OwlBear v2 built and tested a Moonshine STT integration. Key facts:
- **Written and unit-tested**, but **unvalidated on the target Windows hardware**
- Streaming transcription (not fixed 30s windows)
- Built-in VAD (Silero) — knows when you start/stop speaking
- 123M params, ~165ms latency benchmark (non-Windows)
- Lazy-loading ONNX model
- Emits NDJSON: `{"type":"partial","text":"..."}` → `{"type":"transcript","text":"...","final":true}`
- Python API via `moonshine-voice` (PyPI, user-space installable)

**Reuse assessment:** The SttRunner and TranscriptJsonListener classes are directly reusable. The surrounding OwlBear voice infrastructure (VoiceChannel, VoiceProcessManager, bidirectional protocol) was designed for a different use case and should NOT be reused — design the dictation protocol fresh.

## Open Design Questions

These are product-level questions the new project's ideation should resolve:

### 1. Form Factor
- VS Code extension (TypeScript) that spawns a Python STT subprocess?
- Standalone system-tray app (Electron/Tauri/Python) with global hotkey?
- Pure Python CLI tool with clipboard injection?
- Combination?
- Does it need to work outside VS Code at all?

### 2. Activation Model
- Push-to-talk (hold key = listening, release = commit) — trust-safe default
- Toggle (press to start, press to stop) — better for longer sessions
- Configurable? Both?
- How does activation interact with focus/target locking?

### 3. Text Insertion for Copilot Chat
- `executeCommand('type')` might work for Chat input — **needs a validation spike**
- Clipboard + paste is the pragmatic fallback
- Is clipboard-based insertion acceptable UX for Chat specifically?

### 4. Dictation UX Requirements (from end-user voice analysis)
- **Auto-punctuation** — critical for prose; must handle periods, commas, question marks
- **Structural commands** — "new line", "new paragraph" at minimum
- **Corrections** — Ctrl+Z should undo last dictation segment, not character-by-character
- **Streaming partials** — show transcription in progress (builds trust, enables early correction)
- **Target locking** — dictation should insert into the context that was active at activation, not follow focus changes
- **Escape to cancel** — discard current dictation without inserting

### 5. Privacy Architecture
- No audio persistence beyond transient buffer
- No transcript logging (flag: OwlBear's voice code had transcript leakage via malformed-JSON logging, stderr, error journal — design the new project clean)
- Explicit session scoping with hard timeout (120s suggested)
- Push-to-talk as default ensures mic is only active during explicit user action

### 6. Kill Criteria (validate before committing to full build)
- **Can Moonshine run on the target machine?** (Python 3.12+ available, ONNX runtime works)
- **Can sounddevice/PortAudio capture microphone?** (EDR may block audio capture)
- **What's the actual latency on Windows?** (<500ms = go, 500ms-1s = acceptable, >2s = rethink engine)
- **Can a VS Code extension insert into Copilot Chat?** (spike `executeCommand('type')`)
- If any of the first three fail, the project is blocked until resolved.

## Technology Candidates

### STT Engines (rank order for this use case)
1. **Moonshine** — streaming, VAD, proven code exists, Python API
2. **whisper.cpp** — fastest CPU inference, excellent accuracy, but C++ (needs Python bindings or subprocess)
3. **Vosk** — lightweight, fast, but lower accuracy
4. **faster-whisper** — CTranslate2-optimized Whisper, Python API, good balance

### Delivery Mechanisms
- VS Code extension (TypeScript) — best for VS Code-only target
- Python package (uv-installable) — STT subprocess regardless of delivery
- System tray app (Tauri/Electron) — if expanding beyond VS Code
- Pure CLI — simplest but worst UX for dictation

## Relationship to OwlBear

This project is **not** an OwlBear feature. It's a standalone tool that may consume OwlBear services (MCP servers, knowledge base) in the future, but has no dependency on OwlBear.

OwlBear's voice code (`serve/voice/`, orchestrator voice modules) will be removed as part of a separate cleanup task. Research docs from the voice development may be archived as reference for this project.

## Research Archive

The following OwlBear voice I/O research documents have been archived to `research-archive/` for reference by the new dictation project (moved from `.owlbear/research/`, task #746):

| File | Content |
|------|---------|
| `voice-addon-architecture.md` | Voice addon architecture design |
| `voice-addon-stt-moonshine.md` | Moonshine STT integration for voice addon |
| `voice-channel-import.md` | Voice channel import/adapter patterns |
| `voice-io.md` | Voice I/O subsystem overview |
| `ideation-panel-handbook.md` | Ideation panel integration handbook |
| `voice-process-manager.md` | Voice process manager design |
| `voice-protocol-models.md` | Voice protocol data models |
| `voice-stdio-protocol.md` | Voice stdio protocol specification |
| `voice-tts-kokoro-pyttsx3.md` | TTS evaluation: Kokoro and pyttsx3 |
| `moonshine-streaming.md` | Moonshine streaming transcription research |
| `moonshine-vs-whisper.md` | Moonshine vs Whisper comparison |
| `voicechannel-adapter.md` | VoiceChannel adapter design research (task #63) |
