# Voice Code Removal — OwlBear Cleanup

## Investment Tier: Scratch

## Problem
OwlBear v2 carries a voice subsystem (STT, TTS, subprocess protocol, VoiceChannel, VoiceProcessManager) that was designed as a bidirectional voice channel but will never be completed. Voice dictation has been determined to be a separate product concern, not an OwlBear feature. The code is dead weight: unwired, adding dependency mass, and falsely implying OwlBear has voice capabilities.

## Outcomes
1. All voice code, dependencies, and documentation references removed from OwlBear. Success: `serve/voice/` directory gone, orchestrator voice modules gone, no voice deps in any pyproject.toml or uv.lock.
2. Tests referencing voice code removed or updated. Success: test suite passes with no voice-related skips or errors.
3. README and documentation updated to remove voice references. Success: no mention of voice features in user-facing docs.

## Approach
Surgical removal. Delete directories, remove dependency entries, update docs, verify tests pass.

### Removal Scope
- `serve/voice/` — entire directory (STT, TTS, main.py, pyproject.toml)
- `serve/orchestrator/src/owlbear/voice/` — all voice modules (channel.py, process.py, protocol.py, etc.)
- `tests/test_voice_*.py` — all voice test files
- Voice dependencies from workspace pyproject.toml and uv.lock
- Voice references in README.md and any other user-facing docs
- `.owlbear/research/voice-*.md` and related research docs — archive or delete (research has value as historical reference in the new project)

### Preservation
- Research docs (`voice-*.md`, `moonshine-*.md`) may be useful to the new dictation project. Consider moving to a handoff archive before deletion.

## Scope
**In:** All voice code, voice deps, voice tests, voice doc references.
**Out:** Non-voice code. Orchestrator infrastructure that isn't voice-specific. Research docs (optional archive first).

## Risks & Mitigations
- Risk: Accidentally removing shared infrastructure used by voice AND other modules. Mitigation: Check imports before deleting; the voice I/O modules are well-isolated in their own directories.
- Risk: Accidentally deleting ideation voice agents/skills (ideation-architect, ideation-critic, etc.) which share the word "voice" but are completely unrelated. Mitigation: Only delete from `serve/voice/`, `serve/orchestrator/src/owlbear/voice/`, and `tests/test_voice_*.py`. Never touch `share/agents/`, `share/skills/`, or `share/instructions/`.
- Risk: Losing useful research. Mitigation: Archive research docs to the new project folder before deleting.

## Key Decisions
- Voice is not an OwlBear feature — it's a separate product (decided in Voice Interaction Rethink ideation).
- TTS is permanently dead — not deferred, removed.
- Research docs may be preserved as reference for the new dictation project.
