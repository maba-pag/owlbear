# Voice Interaction Rethink — Context

## Problem Statement (M1)

OwlBear v2 has voice infrastructure (Kokoro TTS, VAD-equipped STT) that is better-engineered than v1 but completely unwired — the CLI is a stub, VoiceChannel isn't instantiated, and there's no invocation path.

The primary use case is **hands-free dictation**: microphone → text into whatever has focus (VS Code, terminal, any input field). This is a system-level input concern, not an OwlBear-specific feature. OwlBear's STT component duplicates capability that should exist at the OS/utility level.

**Hard constraints:**
- Must work fully offline (no cloud STT — corporate policy)
- Corporate Windows laptop, no admin access
- Win+H dictation tested — cloud-backed, doesn't meet offline requirement

**Secondary concerns:**
- TTS (agent reads responses aloud) — nice-to-have, not the driver
- Brainstorm mode (streaming voice conversation) — not the primary scenario

**Core question:** Is there an existing offline local STT tool that handles dictation-into-any-app on a locked-down corporate Windows machine? If yes, OwlBear voice code is dead weight. If no, should OwlBear build a standalone dictation utility (not the rich bidirectional channel it was designed as)?

**Framing note (Critic-validated):** The v2 voice code was designed as a bidirectional voice channel (listen/speak/brainstorm), not a dictation utility. The user's actual need is simpler than what was built. Evaluate from the need, not the code. Sunk cost is not a factor in the decision.

**Unresolved:** OS-wide input injection (typing into arbitrary apps from a transcript) is a separate hard problem from transcription itself. Current v2 code stops at transcript text.

## Outcomes (M2)

1. **Working offline dictation into VS Code.** Success: press a hotkey, speak, text appears in the active VS Code context — editor buffer, Copilot Chat input, or askQuestions input. Fully offline (steady-state; one-time model download acceptable). User-space install only (uv/pip/portable, no MSI/admin).
2. **Evaluated shortlist of end-to-end dictation tools** (not bare STT engines). Success: written comparison of viable tools that handle the full pipeline (hotkey → mic → transcribe → insert text) and meet the constraints. With a recommendation.
3. **TTS and brainstorm mode explicitly dropped.** Not in scope for this Brief.

**Scope refinement (Critic-driven):**
- VS Code is the only hard target. System-wide "any app" is not required.
- This may mean a VS Code extension can solve it without OS-wide input injection.
- "End-to-end dictation tool" means the full pipeline, not just an STT engine.
- "No admin" = user-space installs OK (uv, pip, portable binaries). No MSI, no admin UAC.
- "Fully offline" = steady-state offline. One-time model or dependency download is acceptable.

## Landscape Summary (M3)

### Codebase State — Much more complete than expected

The v2 voice infrastructure is **~90% implemented**, not "completely unwired":
- **STT**: Moonshine (streaming, VAD, lazy-load, NDJSON output) — done
- **TTS**: Kokoro (primary) + pyttsx3 (fallback), factory pattern — done
- **Protocol**: 7 Pydantic message types, discriminated union — done
- **VoiceProcessManager**: subprocess lifecycle, restart budget, error handling — done + tested (23 tests)
- **VoiceChannel**: full ChannelPlugin adapter wrapping VoiceProcessManager — done + tested
- **Research**: 9 research docs covering architecture, STT, TTS, protocol, process management

**The only actual gap is the CLI main() stub** — no stdin loop, no backend instantiation, no orchestrator integration. This is last-mile wiring, not a rebuild.

### Ecosystem — No drop-in replacement meets all constraints

| Tool | Offline | No Admin | End-to-End Dictation | VS Code | Notes |
|------|---------|----------|---------------------|---------|-------|
| Win+H | No | Yes | Yes | Yes | Cloud-backed — hard constraint fail |
| Talon | Yes | Yes | Yes | Yes | Steep learning curve, $120/yr license, overkill |
| whisper.cpp | Yes | Yes | STT only (no injection) | Needs wrapper | Best bare STT engine |
| Vosk | Yes | Yes | STT only (no injection) | Needs wrapper | Lower accuracy than Whisper/Moonshine |
| VS Code "Voice" ext | Yes | Yes | Partial | Yes | Whisper-based, unmaintained, unclear injection |
| Dragon | Yes | Needs admin | Yes | Yes | $300+, overkill |

**Key finding**: No existing end-to-end offline dictation tool drops in and meets all constraints (offline + no admin + VS Code + dictation pipeline). Every option either needs cloud, needs admin, or is just an STT engine that still needs text injection.

### Text Injection Options (the hard part)

1. **Clipboard + Ctrl+V** — simplest, works everywhere, overwrites clipboard
2. **VS Code Extension API** — best for VS Code-only target, native `TextEditor.edit()`, but requires building an extension
3. **SendKeys / pyautogui** — character-by-character, slow, unreliable in some apps
4. **Windows UI Automation** — accessibility API, works but needs Python bindings

### Emerging Insight

Since VS Code is the only hard target, a **VS Code extension** that runs STT in a subprocess and inserts text via the editor API is the cleanest path. This avoids the OS-wide input injection problem entirely. The existing v2 Moonshine STT + subprocess architecture is directly reusable for this.
