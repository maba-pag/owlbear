# Shell Injection Risk Documentation and Mitigations

> **Owning task:** #493 — Document shell injection risk and add mitigations
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-01/SEC-04 from `docs/security-audit.md`: `TerminalToolset.run_command()` passes LLM-generated strings to `asyncio.create_subprocess_shell()`. The regex-based `CommandSafetyGuard` is fundamentally bypassable (double spaces, base64 encoding, alt tools, flag variations). What additional mitigations are practical given OwlBear's laptop-resident, shell-dependent architecture?

**Already mitigated** (verified in codebase):

- SEC-05: `run_command` now in default `approval_policy` (`config.py` L170)
- SEC-02: Working directory confinement with null-byte rejection + `is_relative_to` check (`terminal.py` L172-184)

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OpenAI Codex CLI — Security model | github.com/openai/codex (README § Security) | .90 |
| 2 | Claude Code — Security docs | code.claude.com/docs/en/security | .90 |
| 3 | Anthropic Bash Tool — Security section | platform.claude.com/docs/en/.../bash-tool § Security | .85 |
| 4 | Anthropic Computer Use — Security considerations | platform.claude.com/docs/en/.../computer-use § Security | .80 |
| 5 | Aider — Chat modes (no shell tool) | aider.chat/docs/usage/modes.html | .60 |

## 3. Analysis

### 3.1 How others handle LLM shell execution

| System | Shell execution model | Primary safety control | Secondary controls |
|--------|----------------------|----------------------|-------------------|
| **Codex CLI** | Full Auto: sandboxed shell | OS-level sandbox (macOS Seatbelt / Docker) | Network disabled, writes to workdir only, 3-tier approval |
| **Claude Code** | Bash tool with approval | Permission system (approve/allowlist) | Sandbox mode, command blocklist, injection classifier, write restriction |
| **Anthropic Bash Tool** | Developer implements | Docker/VM isolation (recommended) | Command filtering, ulimit, logging |
| **OpenHands** | Docker container sandbox | Complete container isolation | Network restrictions, resource limits |
| **Aider** | No shell execution tool | User runs commands manually | `--suggest-shell-commands` flag (suggestions only) |

**Key insight:** Every production system that allows LLM shell execution uses **approval gates as primary control** and treats blocklists as defense-in-depth only. The two strongest approaches are:

1. **Permission + sandbox** (Codex, Claude Code): user approves, OS enforces boundaries
2. **Complete isolation** (OpenHands): Docker container, no host access

### 3.2 Mitigation feasibility for OwlBear

| # | Mitigation | Effort | Impact | KISS-aligned | Practical? |
|---|-----------|--------|--------|-------------|-----------|
| M1 | Approval gate on `run_command` | Done | **Critical** | Yes | **Already shipped** |
| M2 | Expand blocklist patterns | Low | Low | Yes | Yes — defense-in-depth |
| M3 | Allowlist mode (config-driven) | Medium | High | Yes | Yes — opt-in for production |
| M4 | `subprocess_exec` instead of `_shell` | Medium | Medium | No | **Breaks pipes, redirects, env vars** |
| M5 | Document blocklist as non-boundary | Trivial | Clarity | Yes | Yes |
| M6 | Network isolation (firewall rules) | High | Medium | No | Complex on Windows |
| M7 | Docker sandbox | High | High | No | Not always available on laptops |
| M8 | Command injection classifier | High | Medium | No | Requires extra LLM call per command |

### 3.3 `subprocess_exec` vs `subprocess_shell` trade-off

| Criterion | `subprocess_shell` (current) | `subprocess_exec` (alternative) |
|-----------|------------------------------|--------------------------------|
| Shell injection risk | High (shell interprets metacharacters) | Low (no shell interpretation) |
| Pipe chains (`\|`) | Works | Broken — must implement manually |
| Redirects (`>`, `>>`) | Works | Broken |
| Environment expansion (`$VAR`) | Works | Broken |
| Glob expansion (`*.py`) | Works | Broken |
| Command chaining (`;`, `&&`) | Works | Broken |
| Agent usability | High (LLMs generate shell commands naturally) | Very low (requires arg splitting) |

**Verdict (.85 confidence):** Switching to `subprocess_exec` is impractical for OwlBear. LLM agents generate shell-idiomatic commands (pipes, redirects, globs) and breaking these degrades agent capability severely. Codex CLI and Claude Code both use shell execution and compensate with sandboxing + approval.

### 3.4 Allowlist mode design (recommended)

Modeled after Claude Code's allowlist pattern and Codex CLI's approval tiers:

- **Config field:** `command_allowlist: list[str] = []` — regex patterns for auto-approved commands
- **Behavior:** When non-empty, only commands matching an allowlist pattern skip the approval gate. All others require approval.
- **Examples:** `["^uv run pytest", "^uv run ruff", "^git (status|log|diff)", "^echo "]`
- **Integration:** `ApprovalPolicy.requires_approval()` checks allowlist before rule matching

This gives OwlBear Claude Code's "allowlist safe commands" pattern without requiring OS-level sandboxing.

## 4. Recommendation (.85 confidence)

**Priority-ordered mitigations:**

1. **M5 — Document blocklist as non-boundary** (trivial, immediate). Add docstring/comment to `CommandSafetyGuard` stating it is defense-in-depth, not a security boundary. The approval gate is the primary control.
2. **M2 — Expand blocklist patterns** (low effort). Cover common bypass variations: `rm -r -f`, `git push -f`, `python -m pip`, PowerShell equivalents. Still defense-in-depth.
3. **M3 — Allowlist mode** (medium effort, high impact). Config-driven allowlist of auto-approved command patterns. Most impactful new feature for production use.
4. **M4 — Reject** — `subprocess_exec` breaks agent usability, not practical.
5. **M6/M7 — Defer** — OS sandboxing is valuable but out of scope for a single task. Track as future work.

**Risk acceptance:** The combination of approval gates (M1, done) + expanded blocklist (M2) + allowlist mode (M3) + documented limitations (M5) matches the security posture of Claude Code and exceeds Aider. Full sandboxing (M7) remains the gold standard but is a larger infrastructure project.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Document CommandSafetyGuard as defense-in-depth (not security boundary)" --priority needed --tags "security,tools,docs" --body "Add docstring to CommandSafetyGuard class and DEFAULT_BLOCKED_COMMANDS clarifying that the blocklist is defense-in-depth only. The approval gate (run_command in approval_policy) is the primary security control. Update docs/security-audit.md SEC-04 with current status. See docs/research/shell-injection-mitigation.md M5."

kanban\kanban-md.exe create "Expand CommandSafetyGuard blocklist patterns" --priority needed --tags "security,tools" --body "Add bypass-resistant patterns to DEFAULT_BLOCKED_COMMANDS: rm -r -f, git push -f, python -m pip, PowerShell Remove-Item/rm equivalents, curl/wget (prompt injection vector per Claude Code). Still defense-in-depth, not a boundary. See docs/research/shell-injection-mitigation.md M2."

kanban\kanban-md.exe create "Implement command allowlist mode for approval policy" --priority important --tags "security,tools,config" --body "Add command_allowlist: list[str] config field. When non-empty, only commands matching an allowlist pattern skip the approval gate. Integrate with ApprovalPolicy.requires_approval(). Default empty (all commands gated). Examples: uv run pytest, git status, echo. Modeled after Claude Code allowlist pattern. See docs/research/shell-injection-mitigation.md M3."
```
