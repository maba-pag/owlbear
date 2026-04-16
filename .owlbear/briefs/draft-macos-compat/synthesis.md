# Synthesis — macOS Compatibility

## Convergences

### 1. Option A (Python hooks) is the recommended approach

All three panelists — Architect, End User, Security — independently arrived at Option A as the preferred solution. The reasoning differs by lens but reinforces:

- **Architect:** DRY is the decisive factor. One implementation per hook eliminates the permanent maintenance burden of dual scripts.
- **End User:** Language alignment delivers the best developer experience. Python hooks are debuggable, customizable, and comprehensible using the same toolchain as the rest of OwlBear.
- **Security:** Single implementation eliminates drift between platform-specific security guards as a class of vulnerability. Drift in permission hooks is a privilege escalation vector.

### 2. Option ranking: A > B > C

All panelists rank the options identically. Option B (bash + PowerShell dual) is the acceptable fallback if the brief amendment is rejected. Option C (Python dispatcher wrapping dual scripts) is universally last — it combines Python's startup cost with shell's divergence risk and adds a third component to debug.

### 3. Brief amendment is required for Option A

All three panelists explicitly flag that Option A conflicts with decision D2 ("native POSIX shell / bash") and outcomes O1 and O2 as currently written. All three recommend amending the brief rather than constraining the solution to comply with it.

### 4. `uv run python` as the command invocation

All panelists agree on `uv run python .owlbear/hooks/{name}.py` as the agent command format. This is platform-agnostic, consistent with existing MCP server patterns, avoids bare `python` ambiguity on macOS, and is guaranteed by OwlBear's prerequisites.

### 5. Migration scope is substantial regardless of option

All panelists acknowledge that any option touches 7 hook files, 19 agent `command:` fields, hook tests, setup/init.py, seed artifacts, and documentation. The migration cost is inherent to the problem, not to any particular solution.

### 6. Startup overhead is acceptable

Architect (~60–80ms), End User (~50–100ms), and Security (implicitly, by not flagging it) all agree that `uv run python` overhead is negligible against LLM inference latency (seconds per tool cycle).

### 7. JSON handling advantage of Python

Architect and End User both note that bash JSON parsing requires either `jq` (new dependency) or fragile string manipulation. Security flags this as a risk factor for Option B. Python's `json` stdlib is native and robust.

## Disagreements

### 1. Retirement timeline for .ps1 files — Security vs. Architect

- **Security** insists `.ps1` files must be deleted after validation. Keeping both alive recreates Option B's drift problem. The dual state must be "temporary and bounded."
- **Architect** emphasises the Windows consumer regression risk — existing projects with seeded `.ps1` hooks will break when agent commands change. Recommends clear migration documentation and potentially a staleness warning in init.py.

These positions are compatible in principle but create a **sequencing tension**: Security wants fast retirement; Architect wants a careful consumer migration path. The user must decide how aggressively to retire `.ps1` files and whether a transition period is warranted.

### 2. Translation risk severity — Security vs. Architect/End User

- **Security** rates one-time translation bugs as HIGH severity (temporary) and prescribes specific mitigation: parameterized equivalence tests, malformed-input test suite (truncated JSON, empty stdin, BOM, binary garbage).
- **Architect** and **End User** acknowledge translation risk but treat it as a standard testing concern, not elevated.

The disagreement is about emphasis, not direction. Security's prescribed mitigations are additive and do not conflict with the other stances.

## Recommendation

**Adopt Option A: rewrite all 7 PowerShell hooks as Python scripts.**

Amend D2 to: "Hook scripts use Python (platform-agnostic interpreter). No PowerShell dependency on macOS." Update O1 and O2 acceptance criteria to reference `.py` hooks instead of `.ps1`/`.sh` pairs.

Implementation sequence:
1. Port all 7 hooks to Python with parameterized equivalence tests (same inputs → same outputs vs. existing `.ps1` behavior).
2. Update all 19 agent `command:` fields to `uv run python .owlbear/hooks/{name}.py`.
3. Update `setup/init.py` to seed `.py` hooks and remove Windows-only terminal profiles from seeded settings.
4. Update documentation (setup-guide, sharing-guide) for macOS.
5. Retire `.ps1` files *(timing is an open question — see below)*.

**Confidence: 0.92** — All three panelists converge on the same option with reinforcing rationale. The remaining 0.08 reflects the unresolved brief amendment (user must approve) and the `.ps1` retirement sequencing tension.

## Open Questions

1. **Brief amendment approval.** D2 currently mandates bash. All three panelists recommend amending to Python. The user must explicitly approve this change before implementation can proceed. *(All panelists)*

2. **`.ps1` retirement timing.** Should `.ps1` files be deleted immediately after Python equivalence tests pass (Security's position), or retained temporarily with a deprecation/migration path for existing Windows consumers (Architect's concern)? The "no legacy, no backwards compatibility" principle favours fast retirement, but these are safety-gate hooks — a broken transition means agents running without write guards. *(Security vs. Architect)*

3. **Pre-existing regex weakness.** Security flags that `deny-src-writes.ps1` and `deny-scratch-only-writes.ps1` use `(^|/)` prefix patterns that match target directories anywhere in the path, not just root-relative. Should this be fixed during the port, or tracked as a separate hardening task? Security recommends "bug-for-bug fidelity" in the port with a follow-up task. *(Security)*

4. **Fail-open design carry-forward.** All current hooks fail open on error (JSON parse failure → `{}` → exit 0 → allow). Security flags this as a deliberate but risky design choice that carries forward to Python. Should this be revisited, or accepted as-is for the port? *(Security)*
