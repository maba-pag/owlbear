# Security Voice — Critic Debate Log

## Cycle 1

### Position Presented

Six-point security stance:
1. Push-to-talk mandatory (always-listening unacceptable)
2. VS Code Extension API over clipboard (stays "inside VS Code")
3. Corporate InfoSec pre-check as hard prerequisite
4. No transcript persistence (audio → text → inject → discard)
5. Dependency pinning for Moonshine/ONNX
6. Subprocess should not have network access (firewall rules)

### Critic Challenges

| # | Challenge | Severity |
|---|-----------|----------|
| 1 | **Trust boundary is wrong.** The architecture is Extension Host + subprocess + stdio pipe, not "inside VS Code." Claiming Extension API keeps data inside VS Code mischaracterizes the boundary. | Critical |
| 2 | **Network restriction unenforceable.** No admin = no firewall rules. Models auto-download at runtime. "Document the expectation" is not enforcement. | Moderate |
| 3 | **Supply chain scoped too narrowly.** pyproject.toml has floating ranges for pyttsx3, sounddevice, kokoro, soundfile — not just Moonshine/ONNX. | Moderate |
| 4 | **"No persistence" too narrow.** NDJSON messages, in-memory queues, editor buffers, Copilot Chat input — transcript touches many surfaces. "Inject then discard" is not accurate. | Moderate |
| 5 | **Push-to-talk underspecified.** Press-and-hold vs. toggle vs. hotkey have different accidental-capture properties. A label is not a security guarantee. | Moderate |
| 6 | **Destination risk absent.** Copilot Chat and askQuestions are cloud-connected — offline STT ≠ offline destinations. | Blind spot |
| 7 | **Subprocess environment unaddressed.** Spawn inherits full environment, stderr inherited, no env constraint. | Blind spot |
| 8 | **Shared-tier rollout trust absent.** Update provenance, review scope, revocation undefined. | Blind spot |

### Response

- **Accepted** challenges 1–5 and all blind spots. Trust boundary reframed to Extension Host + subprocess + stdio. Network restriction reframed as detection/documentation control. Supply chain broadened. Transcript lifecycle mapped comprehensively. Push-to-talk specified as toggle with visible indicator and auto-timeout. Destination risk, subprocess environment, and shared-tier concerns added.
- **No rejections** — all challenges were substantive.

Critic confidence: 0.56. Recommendation: Reconsider.

---

## Cycle 2

### Position Presented

Nine-point refined stance incorporating all Cycle 1 feedback:
1. Push-to-talk toggle with visible indicator, auto-timeout, VS Code-scoped kill
2. Trust boundary = Extension Host + subprocess + stdio (narrower than clipboard, not narrow)
3. Destination surfaces split: editor buffers (proven, local), Copilot Chat (cloud, unproven API), askQuestions (already rejected)
4. Transcript lifecycle mapped across controlled/VS Code/OS/native-library surfaces
5. Full dependency chain pinned (all packages, models, VSIX)
6. Network as documentation/detection control
7. Subprocess environment constrained
8. Corporate InfoSec pre-check with specific questions
9. Shared-tier rollout requirements

### Critic Challenges

| # | Challenge | Severity |
|---|-----------|----------|
| 1 | **Session integrity not protocol-verifiable.** No session ID in protocol. Stale messages indistinguishable from current after restart. | Critical |
| 2 | **Emergency stop shares failure domain with controller.** If extension host wedges, protocol-based stop is unenforceable. Single point of failure. | Critical |
| 3 | **Trust boundary inconsistent.** Position slides between "transport boundary" (pipe) and "data-handling boundary" (destinations). | Moderate |
| 4 | **Type validation doesn't cover valid-message flooding.** Unbounded queue + schema-valid floods. | Moderate |
| 5 | **Supply chain overclaims.** Floating ranges still in pyproject.toml. Model resolution is dynamic. Per-load integrity undefined. | Moderate |
| 6 | **TTS code ships even though out of scope.** Present in artifact chain = present attack surface. | Moderate |
| 7 | **askQuestions already contradicted by repo decisions.** Task 101 reversed. | Moderate |
| 8 | **Launch surface broader than env vars.** Working directory, cache dirs, temp paths, module search unaddressed. | Blind spot |
| 9 | **Revocation undefined for cached models/VSIX.** | Blind spot |
| 10 | **No acceptance threshold for residual OS risks.** | Blind spot |

### Response

- **Accepted** challenges 1, 3–7, and all blind spots. Session IDs added as protocol requirement. Trust boundary split into "transport boundary" and "data-handling boundary" with precise language. Queue bounded with age-out. Per-load model verification added. TTS deps flagged for optional-extras separation. askQuestions removed from scope entirely. Revocation mechanism defined. Residual risk acceptance conditioned on InfoSec approval + disk encryption.
- **Challenge 2 — partially accepted.** Extension host IS a single point of failure for protocol stop. Added orphan detection (parent PID monitoring) and hard timeout as compensating controls. Acknowledged defense-in-depth, not guarantee.

Critic confidence: 0.47. Recommendation: Reconsider.

---

## Cycle 3

### Position Presented

Restructured into seven sections (A–G) with precise boundary language:
- A: Capture Boundary with protocol enforcement, fail-safe kill (orphan detection + timeout), indicator integrity
- B: Two distinct boundaries (transport vs. data-handling)
- C: Comprehensive transcript lifecycle with acceptance threshold
- D: Full artifact chain (Python packages, model files, TTS deps, VSIX)
- E: Subprocess isolation (env, working dir, stderr, cache paths)
- F: Corporate policy with specific InfoSec questions
- G: Shared-tier distribution (provenance, sideloading, SECURITY.md, revocation)

### Critic Challenges

| # | Challenge | Severity |
|---|-----------|----------|
| 1 | **Copilot Chat contradiction unresolved.** Brief says offline + Chat. Position says Chat is cloud. Contradiction renamed, not resolved. | Critical |
| 2 | **Clipboard is a third boundary.** Enduser voice proposes clipboard for Chat injection. Position omits clipboard entirely. | Critical |
| 3 | **Control-plane / data-plane on single queue.** Dropping excess messages on a bounded queue could drop control signals (stop, timeout, crash). | Critical |
| 4 | **Deployment path not lock-enforced.** Code still says `pip install moonshine`. Floating ranges still in metadata. | Moderate |
| 5 | **Error journal as persistence surface.** Arbitrary message strings written to disk via str(exc) propagation — broader than voice pipeline. | Moderate |
| 6 | **User consent vs. corporate policy precedence undefined.** | Blind spot |
| 7 | **Hot-mic tolerance unquantified.** | Blind spot |
| 8 | **"Editor buffers are local-only" is an unexamined assumption.** | Blind spot |

### Response

- **Accepted** all challenges and blind spots.
- Chat contradiction resolved: **editor-buffer-only for initial deployment.** Chat is a separate cloud-connected feature, deferred.
- Clipboard-based Chat injection deferred with the Chat feature — reintroduces clipboard exposure risks.
- Control/data plane separation required as architectural constraint.
- Deployment path: `uv.lock` as only path, pip instructions removed.
- Error journal included in transcript persistence audit scope.
- Corporate policy precedence stated explicitly (corporate > user consent).
- Hot-mic tolerance quantified: maximum = hard timeout value (120s).
- Editor buffer trust reframed: same trust as typing into VS Code, which user has already accepted.

Critic confidence: 0.56. Recommendation: Reject.

---

## Cycle 4

### Position Presented

Final refinements layered onto the A–G structure:
- Copilot Chat explicitly deferred — editor-buffer-only for initial deployment
- Hot-mic worst case quantified at 120s
- Corporate policy precedence documented
- Error journal included in audit scope
- Lock file as sole installation path
- Editor buffer trust assumption explicitly stated

### Critic Challenges

| # | Challenge | Severity |
|---|-----------|----------|
| 1 | **120s timeout is a requirement, not a characterized worst case.** Protocol has no start-listen, stop-listen, timeout, or session ID. CLI is a stub. The ceiling is a target, not a property. | Critical |
| 2 | **Control-plane/data-plane argument built on hypothetical bounded queue.** Actual code has unbounded queue with no separation. | Moderate |
| 3 | **Transcript persistence surface still narrower than codebase reality.** Error journal + ACP client propagate str(exc) to disk — tested and asserted in tests. | Moderate |
| 4 | **Brief's success criteria still list Chat and askQuestions.** Product boundary not yet established in source-of-truth docs. | Blind spot |
| 5 | **Stderr inheritance moves persistence risk outside voice component.** | Blind spot |

### Response

- **Accepted** all. The 120s timeout, session IDs, and control/data separation are *requirements for implementation*, not properties of the current code. The security position identifies what must be built, not what exists. Transcript persistence audit scope expanded to include error journal, ACP client, and stderr inheritance chain. Brief amendment recommended as a deliverable of this security review.

Critic confidence: 0.64. Recommendation: Reject.

---

## Cycle 5 (Final)

Cycle 5 reached the hard cap. Critic raised three remaining challenges:
1. 120s timeout is still a design requirement, not implemented (critical) — **Accepted.** Position explicitly states this is a requirement, not current state.
2. Control/data separation argues against hypothetical future queue (moderate) — **Accepted.** Position identifies this as required architectural work.
3. Transcript persistence broader than voice pipeline (moderate) — **Accepted.** Audit scope includes error journal, ACP client, stderr chain.

Critic confidence: 0.64. Blind spots noted: brief's source-of-truth not yet amended, stderr persistence chain crosses component boundaries.

---

## Final Assessment

| Metric | Value |
|--------|-------|
| Cycles completed | 5 (hard cap) |
| Challenges received | ~28 across 5 cycles |
| Accepted | ~26 |
| Rejected | 0 |
| Held firm after challenge | 2 (push-to-talk mandatory — refined but never weakened; corporate InfoSec as blocking prereq — never wavered) |

### What Changed Through the Critic Loop

1. **Trust boundary precision:** "Inside VS Code" → "Extension Host + subprocess + stdio" → "Transport boundary (pipe) + data-handling boundary (destinations)" — three refinements.
2. **Destination scope:** Editor + Chat + askQuestions → Editor only (Chat deferred as cloud-connected, askQuestions removed per project decision).
3. **Push-to-talk:** Label → protocol-enforced sessions with session IDs, timeout, orphan detection, indicator integrity.
4. **Transcript persistence:** "No logs" → comprehensive lifecycle map across controlled/VS Code/OS/native surfaces with explicit acceptance threshold (disk encryption + InfoSec approval).
5. **Supply chain:** Moonshine/ONNX → full artifact chain (all Python deps, models with per-load verification, TTS deps as optional extras, VSIX bundle).
6. **Subprocess isolation:** "No network" → constrained environment, explicit working directory, captured stderr, documented detection controls.
7. **Corporate policy:** Generic "check with InfoSec" → six specific questions + precedence rule (corporate > user consent).
8. **Control architecture:** Single queue → separated control-plane/data-plane requirement.
9. **Error persistence:** Voice pipeline only → error journal + ACP client + stderr inheritance chain.

### What Was Held

- **Push-to-talk is mandatory.** Challenged on usability (hands-free), refined (toggle, not press-and-hold), but the core position — explicit user intent required for audio capture — was never weakened.
- **Corporate InfoSec approval is a blocking prerequisite.** Never wavered across 5 cycles. If they say no, the project stops.

### Residual Uncertainty

The position identifies what must be *built* (session IDs, timeout enforcement, control/data separation, audit of error paths) as distinct from what *exists* in code. This is appropriate for a design-phase security review. Implementation validation is a separate gate.
