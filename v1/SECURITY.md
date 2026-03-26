# OwlBear Security

## Shell Execution

### Design context

OwlBear is an autonomous AI development system. Its agents **need** shell access to
run builds, tests, linters, git commands, and other developer tooling.
`TerminalToolset.run_command()` passes LLM-provided command strings to
`asyncio.create_subprocess_shell()` — this is by design, not a bug.

The fundamental tension: any system that grants an LLM shell execution cannot
fully prevent command injection through input filtering alone. The shell language
is too expressive — there are unbounded ways to express the same operation
(flag rewriting, encoding, alternate tools, chaining, variable expansion).

### CommandSafetyGuard — defense-in-depth, not a security boundary

`CommandSafetyGuard` (`owlbear.core.command_guard`) maintains a regex blocklist
of dangerous command patterns (e.g. `rm -rf /`, `git push --force`, bare `pip install`).
This is a **defense-in-depth** layer that catches accidental or naive dangerous commands.

**It is not a security boundary.** Known bypass vectors include:

- **Base64 encoding:** `echo cm0gLXJmIC8K | base64 -d | bash`
- **Alternate tools:** `find / -delete`, `python -c "import shutil; shutil.rmtree('/')"`,
  `powershell -c "Remove-Item -Recurse -Force C:\"`
- **Command chaining:** `innocent-cmd ; dangerous-cmd` or `innocent-cmd && dangerous-cmd`
- **Environment variable expansion:** `$PATH` manipulation, indirect execution

The blocklist helps — it blocks the obvious cases and signals to the LLM that certain
commands are forbidden. But it cannot be made comprehensive against an adversarial input.

## Mitigations

OwlBear uses a layered defense model. No single layer is sufficient; together they
provide meaningful risk reduction.

### 1. Approval gate (primary control)

`run_command` is gated by `ApprovalPolicy` rules in the default configuration.
Every shell command execution triggers an approval prompt — the user must explicitly
approve before the command runs. This is the primary security control.

- **Slack channel:** Block Kit approval buttons with the full command visible
- **CLI channel:** Plain text prompt with yes/no/approve-all options
- **Per-session pre-grants:** Users can `approve all run_command` to skip repeated
  prompts within a single session, accepting the risk for that session

Implementation: `ApprovalGateToolset` (`owlbear.safety.gate`) wraps tool calls
and checks `ApprovalPolicy` (`owlbear.safety.policy`) before execution.

### 2. CommandSafetyGuard regex blocklist (defense-in-depth)

Catches common dangerous patterns before they reach the approval gate. Registered
as a `PRE_TOOL_USE` hook, so it fires even if the approval gate is misconfigured
or disabled. Raises `BlockedCommandError` on match.

Default blocked patterns:

- `rm -rf /` and variants
- `git push --force`
- Bare `pip install` (must use `uv` or `uv run pip`)
- `format C:` / `del /S /Q` (Windows destructive ops)
- `sudo rm`

See `owlbear.core.command_guard.DEFAULT_BLOCKED_COMMANDS` for the current list.

### 3. Workspace confinement (sandbox_path)

`TerminalToolset` validates the `working_dir` parameter through `sandbox_path()`
(`owlbear.paths`), which enforces that the resolved working directory stays within
`workspace_root`. This prevents LLM-directed path traversal in the `cwd` argument.

`sandbox_path` rejects null bytes, resolves symlinks, and checks `is_relative_to`
against the root. It raises `PermissionError` on escape attempts. The same utility
is shared by `FileToolset`, `KnowledgeToolset`, `RefreshOrchestrator`, and
`IngestPipeline`.

Note: workspace confinement restricts where commands *start* but does not prevent
a command from accessing paths outside the workspace (e.g. `cat /etc/passwd`).
The approval gate remains the control for command *content*.

## Future Considerations

### Allowlist mode

An allowlist approach — only permitting pre-approved command prefixes — would
provide a stronger security boundary than the current blocklist.

**Pros:**

- Fail-closed: unknown commands are denied by default
- Much harder to bypass than regex blocklists
- Could be scoped per-project (e.g. a Python project allows `uv`, `pytest`, `ruff`, `git`)

**Cons:**

- Significantly limits agent autonomy and capability
- Maintenance burden: every new tool the agent needs requires an allowlist update
- Shell features like pipes, redirects, and subshells are hard to allowlist cleanly
- Risk of over-restriction leading to user frustration and workarounds

**Current decision:** Not implemented. The approval gate provides sufficient control
for OwlBear's current deployment model (single-user, laptop-resident). Allowlist mode
should be reconsidered if OwlBear is deployed in multi-user or unattended production
environments where the approval gate cannot be relied upon.

## References

- `docs/security-audit.md` — Full security audit with all findings (SEC-01 through SEC-04)
- `src/owlbear/tools/terminal.py` — TerminalToolset implementation
- `src/owlbear/core/command_guard.py` — CommandSafetyGuard blocklist
- `src/owlbear/safety/policy.py` — ApprovalPolicy rules
- `src/owlbear/safety/gate.py` — ApprovalGateToolset enforcement
- `src/owlbear/paths.py` — `sandbox_path()` utility
