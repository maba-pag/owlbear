# Architect Stance — Cross-Platform Hook System

## Position

**Approach A: Pure Python hooks.** Rewrite all 7 PowerShell hook scripts as Python. Agent command: `uv run python .owlbear/hooks/{hook}.py`. One implementation, one command, both platforms.

**Brief amendment required.** This position diverges from the current brief's bash-oriented outcomes. The Architect recommends amending D2, O1, and O2 — see below. If the user rejects the amendment, Approach B (bash + PowerShell dual with platform-conditional commands) is the viable alternative.

## Structural Reasoning

### 1. DRY — Single source of truth

The decisive factor. Approach B maintains two implementations of each hook (bash + PowerShell) — 14 scripts performing identical logic in two different languages. This is a permanent maintenance and correctness burden. Every hook change must be made twice and verified for behavioral equivalence. Approach A eliminates this: 7 Python scripts, one implementation each, works on all platforms.

### 2. Language alignment

OwlBear is a Python project. Python hooks are testable with pytest, lintable with ruff, and maintained by the same developers who write the rest of the system. Bash scripts require separate tooling and expertise. PowerShell scripts require a different separate tooling and expertise. Python hooks unify the toolchain.

### 3. VS Code command constraint — solved without platform branching

```yaml
# Approach A — one command, both platforms
hooks:
  PreToolUse:
    - type: command
      command: uv run python .owlbear/hooks/deny-writes.py
```

VS Code hooks DO support platform-conditional overrides (`windows:`, `linux:`, `osx:` properties — confirmed in project research). This makes Approach B possible without a dispatcher:

```yaml
# Approach B — platform branching required
hooks:
  PreToolUse:
    - type: command
      command: bash .owlbear/hooks/deny-writes.sh
      windows: powershell -NoProfile -NonInteractive -File .owlbear/hooks/deny-writes.ps1
```

But Approach A doesn't need the branching mechanism at all. The cleanest architecture is the one where the platform abstraction is unnecessary because the implementation is already platform-agnostic.

### 4. JSON handling robustness

Hook logic is fundamentally JSON-in / JSON-out with path inspection. Python's `json` stdlib is native and robust. Bash JSON parsing requires either `jq` (new dependency) or fragile `grep`/`sed` string manipulation — both are worse than Python for this use case.

### 5. Testability

- **Unit:** Import the Python module, call the processing function, assert output. No subprocess needed.
- **Integration:** `subprocess.run(["uv", "run", "python", ".owlbear/hooks/deny-writes.py"], input=json_bytes)` — works on all platforms.
- **Contrast with B:** Bash hooks are untestable on Windows without Git Bash/WSL. PowerShell hooks are untestable on macOS without PowerShell Core. Approach A avoids this asymmetry entirely.

### 6. Interpreter availability

`uv run python` guarantees the correct interpreter on all platforms. `uv` is a hard prerequisite — it manages Python installation and PATH resolution. No bare `python` ambiguity (macOS may lack `python`, only providing `python3`). Startup overhead (~60–80ms for uv + Python) is faster than current PowerShell invocation (~300–500ms) and negligible against LLM round-trip times.

## Key Trade-offs

| Factor | Approach A (Python) | Approach B (Dual) |
|--------|-------------------|-------------------|
| Implementations per hook | 1 | 2 |
| DRY violation | None | Permanent |
| Agent YAML complexity | No platform branching | `windows:` override per hook entry |
| JSON handling | `json` stdlib | `jq` dependency or string hacking |
| Test coverage | Full, all platforms | Partial per platform |
| Brief compliance | Requires amendment | Compliant as-is |
| Windows consumer regression | Yes (re-run init.py) | No |
| New dependency | None (Python already required) | `jq` on macOS (or fragile parsing) |
| Startup overhead | ~60–80ms (uv + Python) | ~5ms (bash) / ~300ms (PowerShell) |

## Warnings

### 1. Brief amendment is non-negotiable for this approach

The current brief specifies bash as the shell target and requires .ps1/.sh parity. Approach A replaces both with Python. If the user does not accept this amendment, Approach A cannot proceed — fall back to Approach B.

**Proposed amendments:**
- **D2:** "No PowerShell dependency on macOS. Hook scripts use Python (platform-agnostic interpreter)."
- **O1 acceptance test:** "Each Python hook script replaces its .ps1 predecessor. Parameterized tests verify same inputs produce same outputs. Zero `powershell` references in agent command fields."
- **O2:** "Seeded hook files are `.py`. `init.py` copies Python hooks, not PowerShell scripts."

### 2. Existing Windows consumers regress until they re-run init.py

Agents are live-loaded from the shared repo. When agent commands change from `powershell ... .ps1` to `uv run python ... .py`, existing consumer projects with `.ps1` hooks will have broken hook invocations. PreToolUse hooks are safety gates (write permission guards) — this is not a cosmetic failure.

**Mitigation:** Document the migration clearly. Consider adding a version check to init.py that warns when seeded hooks are stale. The "no legacy, no backwards compatibility" principle applies, but the safety-gate nature of these hooks warrants explicit communication.

### 3. `uv run` is in the hot path

Every hook invocation spawns `uv run python`. While measured overhead is acceptable (~60–80ms, faster than PowerShell), this adds a toolchain dependency to the latency-sensitive PreToolUse path. If uv is unavailable or misconfigured, all hooks fail silently. Ensure init.py validates uv availability during setup.

## Confidence

**0.82** — High confidence in the architectural superiority of Approach A. The DRY argument is decisive. Caveats are real but manageable: brief amendment, consumer migration, uv hot-path dependency. Approach B is the reasonable fallback if the brief amendment is rejected.
