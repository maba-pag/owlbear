# Architect — Voice Interaction Rethink

## Architectural Stance

**Build a VS Code extension that spawns OwlBear's Moonshine STT as a long-lived Python subprocess and inserts text via the Extension API.** The NDJSON stream between the two is the architectural boundary. The existing v2 voice channel, TTS, and brainstorm code stays dormant.

This is Option B from the context — refined through five Critic cycles to honestly separate what's proven from what needs validation.

## Structural Reasoning

### Why a VS Code extension (not OwlBear pipeline, not standalone tool)

1. **Dictation is an input method, not a pipeline feature.** It operates at keystroke granularity — hotkey, speak, text appears. OwlBear's orchestrator operates at task granularity. Forcing dictation through the orchestrator pipeline (Option A) couples a simple input method to a complex process model with no benefit. The orchestrator should not know about dictation.

2. **VS Code is the only hard target.** The brief's scope refinement explicitly narrows to VS Code. This eliminates the OS-wide text injection problem entirely. The Extension API provides `TextEditor.edit()` for editor buffers and `executeCommand('type', {text})` for focused inputs. No clipboard hacking, no SendKeys, no UI Automation.

3. **No existing tool meets all constraints.** Talon is overkill and paid ($120/yr). whisper.cpp and Vosk are STT-only (no injection pipeline). Win+H is cloud-backed. VS Code Voice extension is unmaintained. Dragon needs admin. Every option fails on at least one hard constraint.

4. **A standalone Python tool with clipboard injection (Option C) is strictly worse** for a VS Code-only target. Clipboard-paste overwrites user clipboard, can't distinguish editor from Chat, and adds a hotkey daemon that duplicates what VS Code keybindings already provide.

### Two-component architecture

```
┌──────────────────────────────────────┐
│  VS Code Extension (TypeScript)      │
│  • Keybinding: configurable hotkey   │
│  • Status bar: ready/listening/idle  │
│  • Spawns long-lived subprocess      │
│  • Reads NDJSON from stdout          │
│  • Insert: TextEditor.edit() for     │
│    editor; executeCommand('type')    │
│    for focused inputs (Chat, etc.)   │
│  • Ghost text preview from partials  │
└────────────┬─────────────────────────┘
             │ stdin: NDJSON commands
             │ stdout: NDJSON events
┌────────────▼─────────────────────────┐
│  owlbear-voice CLI (Python)          │
│  • `uv run owlbear-voice listen`     │
│  • Moonshine STT + VAD              │
│  • Mic capture start/stop/cancel     │
│  • NDJSON event output               │
│  • Heartbeat for liveness            │
└──────────────────────────────────────┘
```

### Subprocess protocol (dictation-specific, not the v2 bidirectional protocol)

**Outbound (subprocess → extension, stdout NDJSON):**

| Type | Payload | When |
|------|---------|------|
| `status` | `{"state": "ready"}` | Model loaded, waiting for commands |
| `status` | `{"state": "listening"}` | Mic active, capturing audio |
| `status` | `{"state": "idle"}` | Mic stopped, process alive |
| `heartbeat` | `{}` | Every 5s for liveness detection |
| `partial` | `{"text": "...", "line_idx": N}` | In-progress transcription |
| `transcript` | `{"text": "...", "line_idx": N, "final": true}` | Committed line |
| `error` | `{"code": "...", "message": "..."}` | Error condition |

**Inbound (extension → subprocess, stdin NDJSON):**

| Command | Effect |
|---------|--------|
| `start` | Begin mic capture; emit `status:listening` |
| `stop` | Finalize in-progress line, emit final `transcript`, emit `status:idle` |
| `cancel` | Discard in-progress line without emitting `transcript`, emit `status:idle` |

Three explicit commands, not a toggle. This avoids state inversion after crash/restart and distinguishes commit (stop) from discard (cancel).

### What's reused from v2

| Component | Reuse | Notes |
|-----------|-------|-------|
| `SttRunner` | Direct | Mic → STT → NDJSON. Core engine. |
| `TranscriptJsonListener` | Direct | NDJSON event serialization. |
| VAD / lazy-load patterns | Direct | Already in SttRunner. |
| VoiceProcessManager patterns | Informational | Restart budget, NDJSON parsing — useful as reference but not imported. |
| VoiceChannel adapter | Not used | ChannelPlugin interface is irrelevant for dictation. |
| TTS pipeline (Kokoro/pyttsx3) | Not used | Explicitly out of scope. |
| Protocol state machine | Not used | Bidirectional semantics; dictation protocol is simpler. |

Honest reuse: ~40-50% of the voice codebase by volume. The STT leaf is directly reusable. The orchestrator-side voice infrastructure stays dormant.

### Scope recommendation to Mediator

The brief's success criteria include "askQuestions inputs." This target should be dropped — askQuestions is a project-specific interactive tool that OwlBear has explicitly decided not to adopt, not a text input surface for dictation. Amended targets:

- **Editor buffers** — proven via `TextEditor.edit()`
- **Copilot Chat input** — high-confidence via `executeCommand('type')`, needs a 1-hour spike to validate
- **askQuestions** — dropped

## Key Trade-offs

| Cost | Benefit |
|------|---------|
| New TypeScript/extension capability required | Native text insertion without clipboard hacking |
| Python dependency chain is heavy (ONNX, sounddevice, moonshine-voice) | Fully offline, no admin, user-space install |
| VS Code-only — no system-wide dictation | Eliminates the OS-wide input injection problem |
| v2 voice channel investment doesn't pay off here | Sunk cost; keeping simpler architecture is cheaper long-term |
| CLI `listen` command must be built (currently a stub) | Clean subprocess contract enables future consumers |
| Copilot Chat insertion needs validation spike | No other approach has a better answer for Chat |

## Warnings

1. **Copilot Chat insertion is unvalidated.** `executeCommand('type', {text})` is the highest-probability path but has not been tested against Copilot Chat's webview input. A 1-hour spike should validate this before committing to the extension approach. Fallback: clipboard-paste for Chat specifically.

2. **Windows STT latency is unverified.** The SttRunner is tested via mocks, not actual mic+model on the target corporate Windows machine. Moonshine is designed for edge devices, so latency should be acceptable, but this needs empirical validation.

3. **Audio stack on locked-down Windows.** `sounddevice` depends on PortAudio. If corporate policy blocks audio APIs or PortAudio DLLs, the entire approach fails. This is a hard environmental dependency.

4. **Target discovery for non-editor surfaces.** The extension needs to determine what has focus (editor vs. Chat vs. other panel) to choose the right insertion method. This is VS Code API work that's straightforward for editors but needs investigation for webview-hosted inputs.

5. **First-run experience matters.** Model download (~100-200MB), Python environment setup, and audio stack initialization all happen on first use. The extension must handle this gracefully with progress notifications, not silent hangs.

## Confidence

**0.78**

The architectural direction is sound and no alternative is stronger. Remaining uncertainty is in two empirical questions (Chat insertion, Windows latency) and implementation scope (CLI build, extension development), not structural flaws.
