# Security Stance — macOS Compatibility

## Position

**Option A — Python hooks.** This is the only approach that eliminates implementation drift as a class of vulnerability. Options B and C both maintain dual implementations of permission guards, and drift between those implementations is a privilege escalation vector that compounds with every maintenance change.

These hooks are security controls. They enforce the principle of least privilege for agents — preventing a doc-writer from modifying source code, preventing a test-writer from touching production files, preventing read-only agents from writing at all. A guard that works on one platform but is stale on another is worse than no guard: it creates a false sense of security.

## Risk Assessment

### Option A — Python hooks

| Risk | Severity | Mitigation |
|------|----------|------------|
| One-time translation bugs during port | HIGH (temporary) | Parameterized equivalence tests against both .ps1 and .py for identical inputs/outputs |
| Python `json.loads()` has different edge cases than `ConvertFrom-Json` | MEDIUM | Malformed-input test suite: truncated JSON, empty stdin, BOM, binary garbage — all must produce `{}` |
| `python` command not found on PATH | MEDIUM | Use `uv run python` — guaranteed by prerequisite, consistent with MCP server patterns |
| Transition window with no working guards on macOS | LOW (dev only) | Complete full port before syncing to main; dev branch is single-developer, acceptable risk |

### Option B — Bash + PowerShell dual

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Implementation drift** — deny-list or write-tools list diverges between .ps1 and .sh | **CRITICAL** (permanent) | Manual review discipline (insufficient — humans miss this) |
| JSON parsing fragility in bash | HIGH | Requires `jq` dependency or hand-rolled parsing; both are weaker than native JSON support |
| Double maintenance burden — every guard change requires two edits | HIGH | No effective mitigation without automated equivalence testing |
| New tool names added to write_tools in one script but not the other | **CRITICAL** | A new VS Code write tool that's blocked on Windows but allowed on macOS = platform-specific privilege escalation |
| Bash regex vs PowerShell regex behavioral differences | MEDIUM | Different regex engines may produce different matches for edge-case paths |

### Option C — Python dispatcher

| Risk | Severity | Mitigation |
|------|----------|------------|
| All of Option B's drift risks | **CRITICAL** | Inherits dual-script maintenance |
| Dispatcher failure → guard bypass | HIGH | Must fail closed (deny by default), but adds complexity to verify |
| Platform detection bugs (e.g., WSL reports as Linux but has PowerShell) | MEDIUM | Edge cases in `sys.platform` or `os.name` branching |
| Additional indirection layer obscures guard behavior | MEDIUM | Harder to audit what actually runs |

## Compliance Implications

These hooks implement **access control for automated agents** — a defense-in-depth layer. While not subject to formal compliance frameworks, they serve the same purpose as RBAC in multi-user systems: limiting each agent's blast radius to its intended scope.

Any approach that allows guards to silently diverge between platforms violates the principle that access controls must be consistently enforced. Option B's drift risk is the equivalent of having different ACL rules on production vs staging and hoping they stay synchronized manually.

## Least-Privilege Recommendations

1. **Single implementation per guard.** Python hooks eliminate the possibility of platform-specific privilege differences. One codebase, one test suite, one behavior.

2. **`uv run python` as command resolver.** Agent `command:` fields must use `uv run python .owlbear/hooks/{script}.py`. This is platform-agnostic, consistent with MCP server invocation patterns, and guaranteed by OwlBear's prerequisites.

3. **Bug-for-bug fidelity in the port.** The Python hooks must replicate existing PowerShell behavior exactly, including known quirks (permissive regex matching in path guards). Security improvements to path matching are a separate tracked change with their own AC and tests.

4. **Retire .ps1 files after validation.** The port is only complete when the old PowerShell scripts are deleted. Keeping both alive recreates Option B's drift problem. The dual state must be temporary and bounded.

5. **Fail-open parity testing.** Every guard currently fails open on parse error (`catch → output {} → exit 0`). The Python equivalents must exhibit identical behavior for the same failure modes. A dedicated test suite must cover: empty stdin, truncated JSON, invalid UTF-8, BOM-prefixed input.

6. **Complete port before main sync.** The sync-to-main workflow is manual dispatch. Do not sync until all 7 hooks are ported, all agent `command:` fields are updated, and equivalence tests pass. A half-ported state on main means consumer projects on macOS have agents running without guards.

## Warnings

1. **Pre-existing regex weakness.** `deny-src-writes.ps1` and `deny-scratch-only-writes.ps1` use `(^|/)` prefix patterns that match the target directory anywhere in the path, not just root-relative. `foo/tests/bar.py` passes the `tests/` guard. This is a pre-existing issue, not introduced by the port, but it should be tracked as a follow-up security hardening task.

2. **Fail-open by design.** All guards currently fail open on any error (JSON parse failure, missing tool_input, empty paths). This is a deliberate trade-off — don't block the agent if the hook mechanism itself breaks — but it means a bug in the hook system results in unrestricted writes, not a denial. This design choice carries forward to the Python port.

3. **New write tools.** If VS Code introduces new write tool names beyond the current six (`create_file`, `replace_string_in_file`, `multi_replace_string_in_file`, `apply_patch`, `create_directory`, `editFiles`), every guard must be updated. With Python hooks, this is one update per guard. With dual scripts, it's two — and missing one is a platform-specific bypass.

## Confidence

**High.** The core analysis — that implementation drift in security guards is a critical risk, and single-implementation eliminates it — is straightforward and well-supported by the codebase evidence. The Critic loop refined the position on translation risk mitigation and operational transition concerns but did not challenge the fundamental ranking of approaches.
