# Security Stance — Critic Debate Log

## Initial Position

**Option A (Python hooks) is the only defensible choice.** The hook scripts are permission guards — they enforce write boundaries for agents. Implementation drift between dual scripts (Option B) is a privilege escalation vector that compounds over time. A Python dispatcher (Option C) inherits all of B's drift risks plus new failure modes. Python hooks give single-source-of-truth, no new dependencies, and testability within the existing pytest infrastructure.

---

## Cycle 1 — Fail-Open Behavior Under New Runtime

**Critic challenge:** You dismiss the fail-open on JSON parse error as a "known trade-off," but every guard currently catches parse failures and outputs `{}` (allowing the write). If Python's `json.loads()` has different failure modes than PowerShell's `ConvertFrom-Json` — encoding issues, truncated stdin on macOS pipes, BOM handling — you could introduce NEW silent failures that don't exist in the PowerShell version. The Python port might create fail-open paths that the PowerShell guards never had.

**Response:** Valid. The fail-open design is inherited, not introduced by the port. But the Critic is right that `json.loads()` and `ConvertFrom-Json` have different edge cases. PowerShell's `ConvertFrom-Json` tolerates trailing commas and single-quoted strings; Python's `json.loads()` does not. Conversely, Python handles UTF-8 stdin naturally on macOS while PowerShell uses .NET's `Console.In` encoding.

**Position update:** The test suite must include malformed-input cases — truncated JSON, empty stdin, BOM-prefixed input, binary garbage — and assert that every case produces `{}` (fail-open, matching current behavior). This is not optional; it's a security-critical parity requirement.

---

## Cycle 2 — One-Time Translation Risk

**Critic challenge:** You claim "single source of truth eliminates drift," but you're CREATING drift by introducing a new Python implementation alongside the existing PowerShell one. The .ps1 scripts are tested and working. The .py scripts are unproven. During the transition, you have two implementations, and any translation bug in the Python version is a permission guard bypass. You're trading future drift for immediate translation risk.

**Response:** This is the strongest challenge. The one-time translation risk is real and concentrated. Mitigations:

1. **Parameterized cross-platform tests.** The same test inputs run against both the .ps1 and .py implementations, asserting identical outputs. This catches translation bugs before deployment.
2. **Bug-for-bug fidelity.** The Python port must replicate existing behavior exactly, including known quirks (e.g., the permissive regex in `deny-src-writes` that matches `tests/` anywhere in path, not just root-relative). Security improvements are a separate change.
3. **Retire .ps1 after validation.** Once the Python hooks pass equivalence tests on both platforms, the .ps1 files are removed entirely. They do not stay in the repo as a parallel implementation. This is the critical difference from Option B — the dual state is temporary and bounded.

**Position update:** Added explicit requirement that .ps1 retirement is part of the port, not a follow-up. The port is only complete when the old scripts are deleted. Added bug-for-bug fidelity requirement.

---

## Cycle 3 — Command Field and Python Resolution

**Critic challenge:** The agent `command:` fields currently use `powershell -NoProfile -NonInteractive -File`. You propose `python .owlbear/hooks/deny-writes.py`. But will `python` resolve correctly on all platforms? On macOS, `python` may not exist (only `python3`). On Windows, `python3` doesn't exist. If the command fails to resolve the interpreter, the hook doesn't run — and a hook that doesn't run is a guard that doesn't guard.

**Response:** Legitimate concern. The command must use a resolver that's guaranteed present. Options:

- `python` — unreliable on macOS (may not exist or may point to system Python 2.7 on older installs)
- `python3` — doesn't exist on Windows
- `uv run python` — guaranteed by OwlBear's prerequisite. `uv` is required, and `uv run python` resolves the project's pinned Python version. This is already the pattern used for MCP server commands in `mcp.json`.

**Position update:** The command field must use `uv run python .owlbear/hooks/{script}.py`. This is consistent with existing MCP patterns and guarantees interpreter resolution on both platforms. Added as a hard requirement.

---

## Cycle 4 — Pre-Existing Regex Weaknesses

**Critic challenge:** `deny-src-writes.ps1` uses `(^|/)tests/` which matches `tests/` anywhere in the path. `src/tests/test.py` passes this guard — it contains `tests/` as a component. Same issue in `deny-scratch-only-writes.ps1` with `(^|/)\.owlbear/scratch/`. If you port these to Python, do you fix these bugs or replicate them? Fixing changes behavior. Replicating preserves a known weakness that could be exploited via path manipulation.

**Response:** The port must replicate existing behavior exactly — bug-for-bug. Mixing security fixes into a platform port creates two dimensions of change that make equivalence testing meaningless. However, the pre-existing regex weaknesses should be documented as follow-up security issues.

Realistically, the exploitation risk is low: VS Code sends absolute or workspace-relative paths, and an agent would need to craft a write to a path like `something/tests/malicious.py` to exploit the permissive match. The guards are defense-in-depth against agent misbehavior, not against a determined attacker with filesystem control.

**Position update:** No change to core position. Added pre-existing issue documentation to recommendations.

---

## Cycle 5 — Transition Window Exposure

**Critic challenge:** During the port, macOS has no working guards. The .ps1 scripts can't run, and the .py scripts aren't ready. Agents on macOS operate without permission guards during this window. If a developer is using macOS for OwlBear development during the transition, agents can write anywhere.

**Response:** Valid operational concern, but bounded. The dev branch on macOS is the developer's own machine — no shared system at risk. The real exposure would be a consumer project pulling a half-ported state from main. Mitigations:

1. The sync-to-main workflow is manual dispatch. Don't sync until the port is complete.
2. The port should be done hook-by-hook but the entire set should be completed before any PR to main.
3. During the transition on dev, the developer can avoid running pipeline agents that require guards (researcher, doc-writer, test-writer, etc.) or accept the risk on their own machine.

**Position update:** Added recommendation that the port must be completed fully before syncing to main. The transition window is acceptable on dev (single-developer machine) but not on main (consumer-facing).

---

## Exit

After 5 cycles, the position is hardened. The core stance (Option A, Python hooks) survived all challenges with refinements rather than reversals. Key refinements added:
- Malformed-input test cases for fail-open parity
- Bug-for-bug fidelity requirement
- .ps1 retirement as part of the port (not follow-up)
- `uv run python` as the command resolver
- Pre-existing regex issues documented as follow-up
- Full port completion before main sync
