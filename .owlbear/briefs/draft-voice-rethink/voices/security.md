# Security Voice — Offline Dictation on Corporate Windows Laptop

## Security Stance

**This tool is viable IF the deployment is scoped narrowly and corporate InfoSec approves.** The core design (offline STT → subprocess → VS Code editor) has a defensible trust boundary, but the current implementation has concrete gaps that must be closed before deployment. The biggest risks are not exotic attacks — they are ambient audio capture on a corporate machine, transcript leakage into log/error paths that already exist in code, and a supply chain with floating dependency ranges.

**Hard requirements before deployment:**
1. Push-to-talk with protocol-enforced capture sessions (not UI convention)
2. Editor buffers only as initial destination (Copilot Chat is cloud-connected — contradicts offline constraint)
3. Corporate InfoSec approval as a blocking prerequisite
4. Full audit of all log/error paths to prevent transcript persistence
5. Dependency pinning with hash verification across the entire artifact chain

## Risk Assessment

### R1: Ambient Audio Capture (CRITICAL)

A microphone-capturing process on a corporate laptop is inherently high-risk. Ambient conversations, meetings, proprietary discussions, and third-party confidential information can be captured.

**Always-listening with VAD is unacceptable.** Even though VAD filters non-speech, the raw audio stream flows through a Python process that could be compromised, crash-dumped, or EDR-captured. The blast radius of a compromised always-listening process is all ambient audio during the tool's lifetime.

**Required control — push-to-talk with protocol enforcement:**
- Toggle activation (explicit start, explicit stop) — not press-and-hold (undermines hands-free).
- The NDJSON protocol must include `start-listen` and `stop-listen` message types with unique session IDs. The extension generates the session ID; the subprocess echoes it in all transcript/partial messages. The extension rejects any transcript without a valid current session ID.
- Subprocess self-terminates audio capture after a configurable hard timeout (recommend 120s default). Sends `timeout-expired` with session ID.
- Visible on-screen mic indicator synchronized with actual subprocess state (via protocol ACKs), not UI intent. Indicator resets to inactive on subprocess crash/restart. Desync is a safety-critical bug.

**Hot-mic worst case:** If the extension host wedges, the subprocess continues capturing until hard timeout or orphan detection (parent PID gone). The maximum unintended hot-mic window equals the timeout value. This is residual risk, not zero risk. The 120s timeout is a design *requirement* — the current implementation does not yet enforce it.

### R2: Transcript Leakage into Persistent Storage (CRITICAL)

The current codebase has multiple paths where transcript content can leak into persistent storage:

- **Malformed-JSON logging:** `VoiceProcessManager` logs raw lines on parse failure — if a transcript is malformed, its content hits the log.
- **Stderr inheritance:** The subprocess inherits the parent's stderr. The STT runner writes exception text to stderr. If an exception contains transcript fragments, they reach the parent process's log output.
- **Error journal:** The orchestrator's error journal writes arbitrary message strings to disk with `str(exc)` propagation. This is a broader persistence surface than just the voice pipeline.
- **VS Code-managed surfaces:** Hot-exit/restore state, local history, and Output panel may persist transcript fragments. These are VS Code-managed and equivalent to the risk of typing into VS Code.
- **OS-managed surfaces:** Pagefile, crash dumps, audio-driver buffers, EDR telemetry. Cannot be mitigated by this tool. Accepted as residual risk IF (a) InfoSec has approved and (b) disk encryption is confirmed.

**Required controls:**
- All log/error paths in the voice pipeline must be audited — transcript content must never appear in log messages, error journal entries, or stderr output.
- VoiceProcessManager queue must be bounded (max size + age-out) with session-scoped messages only.
- Control-plane messages (status, error, ACKs) and data-plane messages (transcript, partial) must be separated — either on distinct channels or via priority queuing — so that queue bounding never drops control signals.

### R3: Destination Surface Trust (HIGH)

The brief's success criteria include editor buffers, Copilot Chat input, and askQuestions input. These have fundamentally different trust profiles:

| Destination | Offline? | Proven API? | Trust Level |
|-------------|----------|-------------|-------------|
| Editor buffers (`TextEditor.edit()`) | Yes | Yes | Same as typing — acceptable |
| Copilot Chat input | **No** — cloud-connected | **No** — no proven writable API | Contradicts offline constraint |
| askQuestions input | N/A | N/A — already rejected in project decisions (task 101) | Out of scope |

**Position: Editor buffers are the only destination for the initial offline dictation deployment.** Copilot Chat insertion is a separate, cloud-connected feature that requires its own risk assessment and explicit user consent to cloud transmission. If Chat insertion requires clipboard (likely, given no proven API), that reintroduces clipboard-exposure risks and creates a third IPC boundary that the current security model does not account for. The brief's success criteria should be amended to reflect this.

### R4: Supply Chain (HIGH)

The most likely actual attack vector. The dependency tree includes native code (ONNX runtime, PortAudio via sounddevice, Kokoro) that executes with user privileges.

**Current state is inadequate:**
- `pyproject.toml` uses floating version ranges for all voice dependencies.
- Code comments contain raw `pip install moonshine` instructions.
- Model files (Moonshine, Kokoro) auto-download at runtime from HuggingFace — silent, unaudited.
- TTS dependencies (pyttsx3, kokoro, soundfile) ship in the package even though TTS is out of scope — they are present attack surface.

**Required controls:**
- Lock file (`uv.lock`) is the only supported installation path. Committed, reviewed, hash-verified. Direct pip instructions removed from code.
- Model download is an explicit pre-download step, not silent runtime auto-download. Checksums stored in version-controlled code (not alongside models). Models verified on every load, not just first download — prevents cache tampering.
- TTS dependencies moved to optional extras (not installed by default for STT-only deployment).
- VS Code extension VSIX: sideloaded with documented build-from-source process. No marketplace distribution for initial deployment.

### R5: Subprocess Isolation (MEDIUM)

The subprocess runs with the user's full permissions. If compromised, it has access to everything the user can access.

**Current gaps:**
- Environment: full user environment inherited. Must constrain to minimum required variables (PATH, model cache path, temp path).
- Working directory: inherited. Must be set explicitly.
- Stderr: inherited to parent. Must be captured and filtered.
- No network restriction enforceable without admin access — this is a detection/documentation control, not prevention.

**Compensating controls:**
- Document that the subprocess should make zero network calls during steady-state.
- One-time model download should be a separate, auditable step.
- EDR monitoring (if available) for unexpected network connections.
- Subprocess orphan detection: monitor parent PID, self-terminate if parent exits.

## Compliance Implications

1. **Corporate AUP (Acceptable Use Policy):** Audio capture by user-space processes is almost certainly covered. Check before building.
2. **Data classification:** Voice transcripts of source code inherit the source code's classification — likely Internal/Confidential. Treat accordingly.
3. **EDR/DLP interaction:** CrowdStrike, Defender for Endpoint, or equivalent will likely detect and may block a Python process accessing the microphone API. This is not a bug — it's corporate policy enforcement. Do not circumvent.
4. **VS Code extension sideloading:** Some corporate policies restrict VS Code extension sources. Confirm sideloading is permitted.
5. **Audio capture audit requirements:** Some policies require audio capture to be logged. Confirm whether this applies (and note the tension with the no-transcript-persistence requirement).
6. **Disk encryption:** Residual OS-managed risks (pagefile, crash dumps) are acceptable only if disk encryption is confirmed. If disk is unencrypted, this is a hard veto.
7. **Corporate policy precedence:** Corporate policy ALWAYS takes precedence over user consent for corporate resources. If InfoSec prohibits audio capture, user consent is irrelevant. If InfoSec permits capture but prohibits cloud transmission, the user cannot consent to dictating into Copilot Chat. This precedence must be documented.

## Least-Privilege Recommendations

1. **Subprocess environment:** Minimum required variables only — no full environment inheritance.
2. **Capture window:** Time-bounded by hard timeout, session-scoped by protocol.
3. **Destination surface:** Editor buffers only for initial deployment — no clipboard, no Chat.
4. **Dependencies:** STT-only install (TTS as optional extras). Minimum functional dependency set.
5. **Extension permissions:** VS Code extension should request only the minimum required API surfaces (TextEditor, command registration, subprocess spawn). No file system access, no terminal access, no network access beyond what VS Code provides.
6. **Model cache:** Dedicated directory with explicit path, not shared Python cache.

## Warnings

1. **The brief's success criteria are internally inconsistent.** "Fully offline" and "Copilot Chat input" are in direct conflict. The security voice recommends amending the criteria to editor-buffer-only for offline dictation. Copilot Chat is a separate, cloud-connected feature.
2. **The current codebase already leaks transcript content into persistent storage** via malformed-JSON logging, stderr inheritance, and error journal propagation. These are not hypothetical risks — they are existing code paths.
3. **The 120s hard timeout is a design requirement, not an implemented control.** The current protocol has no start-listen, stop-listen, timeout, or session ID concepts. These must be built.
4. **EDR may kill this project entirely.** If corporate endpoint detection blocks the microphone access, that is the answer. Plan for this outcome.
5. **TTS code ships even though TTS is out of scope.** The artifact chain includes attack surface that provides no value for the STT-only use case.

## Confidence

**0.82** — Position is well-hardened through 5 Critic cycles. Remaining uncertainty is in how the implementation will close the gaps between the security requirements and the current codebase state. The threat model and controls are sound for a design-phase security review.
