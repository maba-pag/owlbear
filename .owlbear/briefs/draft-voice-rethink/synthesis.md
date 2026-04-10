# Synthesis — Voice Interaction Rethink

## Convergences

### 1. VS Code extension + Moonshine STT subprocess is the correct architecture
All three voices (Architect, End-User, Security) converge on this. A TypeScript extension spawning a long-lived Python subprocess with NDJSON IPC is the strongest path given the constraints. No voice proposed an alternative architecture.

### 2. No existing drop-in tool meets all constraints
All voices accept the landscape finding: every evaluated tool (Talon, whisper.cpp, Vosk, Win+H, Dragon, VS Code Voice ext) fails on at least one hard constraint (offline / no admin / end-to-end dictation / VS Code). Building is the only viable option.

### 3. Editor buffers via `TextEditor.edit()` are the proven, correct insertion target
All voices agree this is native, clean, and equivalent to typing. No objections, no caveats.

### 4. Existing v2 STT code (SttRunner, Moonshine, VAD) is directly reusable
Architect estimates ~40-50% reuse by volume. End-User assumes it. Security accepts the STT core but flags audit requirements on surrounding code paths. All agree the STT leaf is sound.

### 5. TTS, brainstorm mode, and askQuestions are correctly out of scope
All voices confirm. Architect and Security both independently recommend dropping askQuestions from success criteria (already rejected in project decisions). TTS stays dormant.

### 6. Windows STT latency must be empirically validated before committing
Architect (Warning 2), End-User (§9, Warning 2), and Security (R1 residual risk context) all flag that Moonshine benchmarks are non-Windows. End-User sets a 500ms target with 1s acceptable and 2s as a rethink trigger. All agree: benchmark first.

### 7. Push-to-talk as the default activation model
All voices prefer explicit activation over always-listening or VAD-triggered. Security is strongest here (R1: "always-listening with VAD is unacceptable"), End-User details the UX, Architect encodes start/stop/cancel as protocol primitives.

### 8. First-run experience requires explicit handling
Architect (Warning 5) and End-User (§8) both detail model download, audio stack init, and error states. Security requires model download to be a separate auditable pre-download step with checksum verification. All agree first-run cannot silently hang.

### 9. Audio stack on corporate Windows is a hard environmental dependency
Architect (Warning 3) and Security (R5, Compliance §3) both flag that PortAudio/sounddevice may be blocked by corporate EDR. Security frames this as potentially project-killing. All voices treat it as empirical risk to validate early.

## Disagreements

### D1: Copilot Chat as an initial deployment target
**Architect vs. End-User vs. Security**

- **Architect**: Include Chat as a target. Validate `executeCommand('type')` via a 1-hour spike. Fall back to clipboard-paste for Chat specifically if the spike fails. Chat insertion is unproven but not excluded.
- **End-User**: Include Chat as a target. Clipboard-save/restore is the pragmatic fallback and is "good enough" for daily use. Chat is arguably the *highest-value* target (natural language prompts are dictation's sweet spot).
- **Security**: **Exclude Chat from initial deployment.** Copilot Chat is cloud-connected — inserting dictated text into it contradicts the "fully offline" constraint. Chat introduces a third IPC boundary (clipboard) the security model doesn't account for. Chat requires its own risk assessment and explicit user consent to cloud transmission. Corporate policy precedence applies.

This is the sharpest disagreement. Two voices want Chat in; one voice says it fundamentally conflicts with the brief's offline constraint.

### D2: Push-to-talk mechanism — hold vs. toggle
**End-User vs. Security**

- **End-User**: Hold-to-talk default (hold = listening, release = commit). Toggle opt-in for longer sessions. Hold gives unambiguous activation state and is the trust-safe default.
- **Security**: Toggle activation (explicit start, explicit stop). Claims press-and-hold "undermines hands-free." Requires protocol-enforced session IDs, subprocess ACKs synchronized with the visible indicator, and a 120s hard timeout with subprocess self-termination.
- **Architect**: Encodes three explicit commands (start/stop/cancel) in the protocol but does not prescribe hold vs. toggle UX.

The tension is between UX trust (hold is unambiguous) and security trust (toggle enables session-scoped protocol enforcement and hands-free use). Both voices want explicit activation; they disagree on the default gesture.

### D3: Scope of security prerequisites before engineering begins
**Security vs. Architect/End-User**

- **Security**: Corporate InfoSec approval is a *blocking prerequisite* before building. EDR may kill the project. Compliance implications (AUP, data classification, sideloading policy, disk encryption) must be confirmed first. Transcript leakage audit is required before reusing existing code.
- **Architect**: Mentions empirical risks (latency, Chat insertion, audio stack) as validation spikes, not blockers. Does not mention InfoSec approval.
- **End-User**: Does not mention corporate approval or compliance. Treats latency benchmarking as the first engineering task.

Security frames corporate approval as gate-zero; the other voices frame empirical validation (latency, Chat API) as the first step. These are compatible if sequenced, but currently unsequenced.

### D4: Transcript leakage in existing code
**Security vs. Architect/End-User**

- **Security**: Identifies concrete existing code paths where transcript content leaks to persistent storage — malformed-JSON logging in VoiceProcessManager, stderr inheritance, error journal propagation. Calls these "not hypothetical — existing code paths" requiring audit before reuse.
- **Architect**: Does not mention transcript leakage. Treats SttRunner and TranscriptJsonListener as directly reusable.
- **End-User**: Does not address logging or persistence concerns.

Security is the only voice raising this. The claim is specific and code-grounded, not speculative.

### D5: TTS dependency removal
**Security vs. Architect**

- **Security**: TTS dependencies (pyttsx3, kokoro, soundfile) should be moved to optional extras and not installed for STT-only deployment. They are present attack surface with no value for the dictation use case.
- **Architect**: Notes TTS pipeline is "not used" but does not recommend removing or isolating the dependencies.
- **End-User**: Does not address.

Low-stakes disagreement on packaging, but Security's point is structurally sound — shipping unused native-code dependencies increases supply chain risk.

## Recommendation

**Build the VS Code extension + Moonshine STT subprocess architecture.** All voices converge on this as the only viable path. The two-component design (TypeScript extension ↔ NDJSON ↔ Python STT subprocess) is uncontested.

**Sequence the work as follows:**

1. **Gate 0 — Environmental validation** (before any feature code):
   - Benchmark Moonshine STT latency on the target Windows machine
   - Confirm PortAudio/sounddevice is not blocked by EDR
   - ⚠️ *Open tension (D3):* Security wants corporate InfoSec approval here too. User must decide whether InfoSec approval blocks engineering or runs in parallel.

2. **Gate 1 — CLI `listen` command**: Wire the existing SttRunner into a working `uv run owlbear-voice listen` subprocess with the NDJSON protocol. This is the last-mile gap identified in the landscape.
   - ⚠️ *Open tension (D4):* Security wants a transcript leakage audit of existing voice code before reuse. User must decide scope of audit.

3. **Gate 2 — VS Code extension MVP**: Editor-buffer dictation via `TextEditor.edit()`. Push-to-talk activation.
   - ⚠️ *Open tension (D2):* Hold-to-talk vs. toggle default. Must be decided before extension UX is built.

4. **Gate 3 — Chat insertion** (if approved):
   - ⚠️ *Open tension (D1):* Whether Copilot Chat is in scope at all for an "offline dictation" tool. Must be resolved before this gate.

**Target editor buffers only for initial deployment.** This is the only surface all three voices endorse without caveats. Chat insertion is the highest-value stretch goal but carries the sharpest disagreement.

**Confidence: 0.74**

All voices align on architecture and primary target. Score is pulled down by unresolved disagreements on Chat inclusion (D1), activation gesture (D2), and sequencing of corporate approval (D3) — all of which affect scope and feasibility of the final deliverable.

## Open Questions

1. **Copilot Chat: in or out for initial deployment?** (D1)
   Security says it contradicts the offline constraint because Chat transmits to the cloud. Architect and End-User both want it in with a clipboard fallback. User must decide whether "offline dictation" means the *transcription* is offline (Architect/End-User position) or that the *entire workflow including destination* is offline (Security position).

2. **Push-to-talk default: hold or toggle?** (D2)
   End-User advocates hold-to-talk for trust clarity. Security advocates toggle for hands-free use and protocol-enforced session scoping. Both are implementable — this is a UX policy decision, not a technical blocker.

3. **Is corporate InfoSec approval a blocker before engineering?** (D3)
   Security says yes — audio capture on a corporate machine requires explicit approval, and EDR may kill the project. Architect and End-User treat this as background context. User must decide: seek approval first, or build the proof-of-concept and seek approval before deployment?

4. **Transcript leakage audit scope?** (D4)
   Security identifies specific existing code paths (malformed-JSON logging, stderr, error journal) that persist transcript content. Should these be audited and fixed before reusing v2 voice code, or is this deferred to pre-deployment hardening?

5. **TTS dependency isolation?** (D5)
   Security recommends moving TTS deps to optional extras. Low urgency but affects supply chain posture. Decide during packaging work.
