# Voice Interaction Rethink — Decisions

## Investment Tier: Shared
Rationale: Affects v2 scope broadly, dictation utility could serve other OwlBear users, decision has downstream impact on packaging and project structure. User elevated from recommended Tool to Shared.

## D1: Copilot Chat — IN SCOPE
"Offline" means the STT engine is local. Where the transcribed text goes is the user's choice. Copilot Chat is a valid and high-value dictation target.

## D2: Activation Mode — Push-to-talk default, configurable
Not a priority decision. Default to push-to-talk. Make configurable if easy.

## D3: InfoSec — NON-ISSUE (user is corporate InfoSec)
Constraints are self-imposed and already baked into the design:
- No cloud STT (Moonshine chosen specifically for this)
- No audio recording/persistence beyond transient transcription
- Everything stays local
No external approval gate needed.

## D4: Transcript Audit — DEFERRED to pre-deployment hardening
Security-flagged code paths (malformed-JSON logging, stderr, error journal) will be audited before deployment, not before development.

## D5: TTS — REMOVE ENTIRELY
TTS will never be used. Not deferred — dead. Remove pyttsx3, kokoro, and all TTS code/dependencies. If building a VS Code extension, start clean (STT-only). If keeping the local module, minimize to STT-only.
