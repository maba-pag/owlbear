# Architect — Critic Debate Log

## Cycle 1

**My position:** Option B (VS Code extension + STT subprocess) is the right approach. Extension API solves text injection, ~90% of v2 code is reusable, the CLI becomes the stable contract.

**Critic challenges:**
1. **(Critical)** Claimed Extension API natively reaches editor buffers, Copilot Chat, AND askQuestions — but only editor buffers are proven. askQuestions isn't even a text input surface.
2. **(Moderate)** "~90% reusable" overstates. The STT leaf is reusable; the orchestrator-side VoiceChannel, protocol state machine, and VoiceProcessManager encode bidirectional semantics that don't apply.
3. **(Moderate)** "Self-contained vsix" ignores the Python 3.12 + moonshine + ONNX dependency chain.
4. **(Moderate)** "Stable CLI contract" is undercut by the CLI being a non-functional stub.

**My response:**
- **Accepted** challenge 1 → dropped askQuestions from targets, flagged Copilot Chat as needing a validation spike.
- **Accepted** challenge 2 → narrowed reuse claim to ~40-50% (STT leaf only; orchestrator voice code is informational reference, not imported).
- **Accepted** challenge 3 → acknowledged two-phase packaging: vsix for extension, uv-managed Python for subprocess.
- **Accepted** challenge 4 → agreed CLI must be productized as the build target, not left as stub.

## Cycle 2

**My position:** Same direction, with narrowed reuse claims, honest packaging story, and askQuestions dropped.

**Critic challenges:**
1. **(Moderate)** CLI control plane is unbuilt — "process lifecycle is the control plane" understates the gap. SttRunner has explicit start/stop/close, not just kill.
2. **(Moderate)** NDJSON contract lives in orchestrator package, not voice package — cuts against clean separation claim.
3. **(Moderate)** Target surfaces still inconsistent with brief's stated success criteria.
4. **(Minor)** Dependency surface concerns (pip install message in STT code vs. uv workspace convention).

**My response:**
- **Accepted** challenge 1 → agreed CLI needs graceful shutdown (SIGTERM → stop() → close()), not just process kill.
- **Accepted** challenge 2 → clarified that dictation protocol uses the implicit NDJSON schema already in stt.py's TranscriptJsonListener, not the orchestrator's typed protocol module.
- **Rejected** challenge 3 → Architect's job is to recommend scope amendments. Position includes explicit recommendation to Mediator to amend brief.
- **Accepted** challenge 4 → noted but minor; uv handles installation.

## Cycle 3

**My position:** Same direction. Added graceful SIGTERM shutdown, clarified NDJSON source, explicit scope recommendation.

**Critic challenges:**
1. **(Moderate)** Copilot Chat claim still unsupported — workspace docs confirm editor insertion is proven, Chat is unproven.
2. **(Moderate)** `uv run owlbear-voice listen` doesn't exist — shouldn't claim it "works today."
3. **(Moderate)** "No inbound commands" is a different control model from what existing voice code proves. New boundary, not a simplification of a proven one.
4. **(Moderate)** Idle-state inference from "no events" conflates healthy silence with subprocess failure.

**Blind spots raised:**
- Subprocess per-utterance vs. long-lived? (affects model startup cost)
- Target discovery for non-editor surfaces absent.

**My response:**
- **Accepted** challenge 1 → downgraded Copilot Chat to "unvalidated, needs spike" with clipboard fallback.
- **Accepted** challenge 2 → corrected: STT engine works today, CLI is the build target.
- **Partially accepted** challenge 3 → acknowledged new boundary, but simpler-by-design is the architectural intent.
- **Accepted** challenge 4 → added heartbeat events (every 5s) to protocol for liveness.
- **Accepted** blind spots → subprocess is long-lived; target discovery flagged as design work.

## Cycle 4

**My position:** Same direction. Added heartbeat, explicit long-lived subprocess, honest evidence ratings.

**Critic challenges:**
1. **(Moderate)** Edge-triggered `toggle` can get inverted after crash/restart. Not deterministic enough.
2. **(Moderate)** `stop()` finalizes the active line (commit), but cancel (discard) also needed — one `toggle` command can't distinguish.
3. **(Moderate)** "STT engine works" is tested via mocks, not actual Windows mic+model.

**Blind spots raised:**
- askQuestions dropped without Mediator sign-off.
- Target-lock mechanism for non-editor surfaces absent.

**My response:**
- **Accepted** challenge 1 → replaced `toggle` with three explicit commands: `start`, `stop` (commit), `cancel` (discard). Deterministic, no state inversion.
- **Accepted** challenge 2 → `cancel` discards in-progress line without emitting `transcript`. Problem solved by the three-command protocol.
- **Accepted** challenge 3 → downgraded to "wrapper and protocol tested; Windows mic+model performance unverified."
- **Noted** blind spots → scope recommendation goes to Mediator; target discovery flagged as warning.

## Cycle 5

**My position:** Final. Three-command protocol (start/stop/cancel), honest evidence ratings, all challenges addressed.

**Critic challenges:**
1. **(Moderate)** Toggle concerns repeated from cycle 4 — already addressed by the three-command split.
2. **(Moderate)** "STT engine works" still overstated — same point, already downgraded.
3. **(Moderate)** Cancel/stop distinction needed — already resolved.

**Critic confidence:** 0.72 with "Reconsider" — but the remaining challenges were all already addressed in my cycle 4→5 refinements. The Critic continued finding moderate-severity issues but each was a design detail within the chosen architecture, not a reason to switch architectures.

## Final Assessment

- **Cycles completed:** 5
- **What changed:** Reuse claim narrowed (90% → 40-50%). Target surfaces amended (dropped askQuestions, flagged Copilot Chat). Protocol evolved from implicit lifecycle-as-control → single toggle → three explicit commands (start/stop/cancel) + heartbeat. Evidence ratings made honest (proven vs. unvalidated vs. build target). Packaging story made two-phase (extension + Python subprocess).
- **What I held:** Option B throughout. VS Code extension + STT subprocess is the right architecture. No other option has a stronger answer for the stated constraints. The architectural boundary (NDJSON stream between TypeScript extension and Python subprocess) is clean and decoupled.
- **Critic's strongest contribution:** Forcing the toggle → three-command evolution (cycle 4). A toggle would have been a real correctness bug in crash recovery. The explicit start/stop/cancel protocol is materially better.
- **Where I pushed back:** Scope amendment is the Architect's prerogative. askQuestions is not a legitimate dictation target regardless of what the brief currently says. The Mediator can override, but the recommendation stands.
