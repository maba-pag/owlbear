# Context — Voice Interaction Rethink

## Problem

v2 has voice infrastructure (Moonshine STT, Kokoro/pyttsx3 TTS) but it's not wired up — the CLI entry point is a stub, VoiceChannel isn't instantiated, and there's no invocation mechanism. Before investing in completing the wiring, we need to rethink: is OwlBear-specific voice I/O the right approach?

The STT component (microphone → text) is not OwlBear-specific. It's a system-wide utility that could type into any input field on any program. Existing solutions may already do this better:

- Windows Win+H (built-in dictation, cloud-backed)
- whisper.cpp (excellent local STT)
- Vosk (good local STT)
- Talon (power voice control, system-wide)
- Windows Speech Recognition (built-in)

The TTS side (agent speaks responses) and the brainstorm mode (open-ended streaming conversation) are more OwlBear-flavored but could also be generic utilities.

## Desired Outcomes

1. Determine if a system-wide local STT solution already covers the voice-to-text need
2. If yes: decide whether to replace OwlBear STT, separate it, or keep it as-is
3. Evaluate whether the TTS/brainstorm features are worth completing in v2
4. If voice I/O is worth keeping: define the minimal viable wiring to make it usable
5. Consider whether voice should be a separate project entirely

## Tier

Low-medium complexity research. High impact on scope reduction if STT can be replaced.

## Landscape

**v1 approach:** Moonshine STT + pyttsx3 TTS. VoiceChannel with two modes (quick, brainstorm). CLI commands: listen, speak, brainstorm. End-to-end functional.

**v2 current state:** Better components (Kokoro TTS, VAD-equipped STT) but zero wiring. CLI stub prints a string.

**v2 voice agents:** architect-voice, critic-voice, etc. are opinionated consultants for ideation — unrelated to voice I/O infrastructure.

**Constraints:** Corporate Windows laptop. No admin access for system-wide installations. Must work offline.
