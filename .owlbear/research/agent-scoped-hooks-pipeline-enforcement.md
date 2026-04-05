# Agent-Scoped Hooks for Pipeline Enforcement

> **Owning task:** #86 — Evaluate agent-scoped hooks for pipeline enforcement (scoped AC)
> **Date:** 2026-03-29 (updated 2026-03-30) **Status:** Complete
>
> **Update note:** Revised sections 3.2, 3.3, and 4 to reflect the VS Code
> command-execution hook model (API updated 2026-03-25). See
> `docs/research/stop-commit-guard-hooks-phase1.md` §3.1 for the delta summary.

## 1. Context and Question

OwlBear's CI pipeline runs through 11 agents in a strict sequence
(`ideation → backlog → todo → in-progress → review → docs → done`). Enforcement of
quality gates, task-claiming discipline, and commit hygiene currently relies entirely on
agent instructions and human oversight. VS Code agent-scoped hooks (preview) offer a
mechanism to reinforce these behaviors automatically.

**Two distinct hook layers exist in OwlBear** (per architect's note in task #86):

| Layer | Location | Mechanism | Blocking? |
|-------|----------|-----------|-----------|
| **Internal HookRegistry** | `src/owlbear/core/hooks.py` | Python pub-sub; `HookEvent` enum + callbacks | Observational only — non-blocking by design (architecture-standards) |
| **VS Code agent-scoped hooks** | `.agent.md` frontmatter `hooks:` key + `.github/hooks/*.json` | Command execution at lifecycle events; structured JSON I/O | Exit code 2 blocks; Stop hook can block via `decision: "block"` |

These are different mechanisms serving different purposes. This document covers only the
VS Code layer. Do not conflate them; enforcing blocking behavior via VS Code hooks is not
aligned with the internal HookRegistry contract.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical hook spec; command-execution model |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 — hook field in .agent.md |
| OwlBear agent-md-format research (#4) | `docs/research/agent-md-format.md` §7 | 1.0 — prior hooks survey with examples |
| nWave-ai/nWave research (#589) | `docs/research/nwave.md` §3.3 | .75 — DES pre/postToolUse enforcement pattern |
| OwlBear agent-common.instructions.md | `instructions/agent-common.instructions.md` | 1.0 — current pipeline discipline model |

## 3. VS Code Hook Capabilities and Constraints

### 3.1 Hook Types

| Hook Type | Trigger | Typical Use |
|-----------|---------|-------------|
| `SessionStart` | New agent session begins | Initialize resources, log session start |
| `UserPromptSubmit` | User submits a prompt | Audit requests, inject system context |
| `PreToolUse` | Before a tool invocation executes | Block dangerous ops, require approval |
| `PostToolUse` | After a tool invocation completes | Run formatters, trigger follow-up checks |
| `PreCompact` | Before context is compacted | Export important context, save state |
| `SubagentStart` | Subagent is spawned | Track nested agent usage |
| `SubagentStop` | Subagent completes | Aggregate results, cleanup |
| `Stop` | Agent session ends | Commit guards, cleanup resources |

### 3.2 Hook Definition Format

Hooks are declared under the `hooks:` key in `.agent.md` YAML frontmatter (using
PascalCase event names) or in `.github/hooks/*.json` files:

```yaml
# agent-scoped (in .agent.md frontmatter)
hooks:
  PostToolUse:
    - type: command
      command: "./scripts/hooks/lint-changed.sh"
      windows: "powershell -NoProfile -File scripts/hooks/lint-changed.ps1"
  Stop:
    - type: command
      command: "./scripts/hooks/stop-commit-guard.sh"
      windows: "powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1"
```

Each hook entry must include:

- `type: command` (required): the only supported type.
- `command` (required): shell command to execute. OS-specific overrides via `windows`,
  `linux`, `osx` properties.
- `timeout` (optional, default 30s): max execution time in seconds.
- `cwd` (optional): working directory relative to repo root.

Hooks receive structured JSON on stdin (including `tool_name` for PreToolUse/PostToolUse)
and return JSON on stdout to influence agent behavior. Tool-name filtering is done in the
script, not via a `when` condition — hooks fire on all matching events for the event type.

### 3.3 Constraints and Limitations

| Constraint | Detail | Implication |
|------------|--------|-------------|
| **Preview feature** | Requires `chat.useCustomAgentHooks: true` for agent-scoped hooks; API may change | Not suitable for hard production guarantees |
| **Exit code 2 blocks** | Exit code 2 stops processing and shows stderr to the model as context | Hard blocking is now available for PreToolUse, PostToolUse, and Stop hooks |
| **PreToolUse can deny** | `permissionDecision: "deny"` in hook output blocks tool execution | Can block dangerous ops without stopping the entire session |
| **Stop hook can block** | `decision: "block"` in Stop hook output prevents session end; `stop_hook_active` prevents infinite loops | Can enforce commit discipline before session close |
| **Per-agent scope** | A hook in `builder.agent.md` does not fire for any other agent | Cannot create a cross-agent enforcement layer through this mechanism |
| **Context cost (systemMessage)** | Hook `systemMessage` output is shown to the user in chat | Lower cost than prompt injection — messages are one-off, not accumulated |
| **No tool-name filtering** | Hooks fire on all matching events; tool-name filtering must be done in the script via stdin JSON `tool_name` | Scripts must guard against irrelevant tool invocations to avoid noise |
| **Hook execution order** | Multiple entries in the same hook type fire in definition order; most restrictive decision wins | Keep hooks focused; compound blocking can be hard to debug |
| **Command execution** | Hooks execute shell commands and receive/return structured JSON | Can auto-run linters, check git status, query external state |

## 4. Pipeline Enforcement Candidates

### Candidate 1 — PostToolUse Lint Guard (builder)

**What it does:** After the builder edits a source file, run ruff automatically.

```yaml
# builder.agent.md
hooks:
  PostToolUse:
    - type: command
      command: "./scripts/hooks/lint-changed.sh"
      windows: "powershell -NoProfile -File scripts/hooks/lint-changed.ps1"
```

The script reads `tool_name` from stdin JSON and runs ruff only when the tool is a file
edit (`create_file`, `replace_string_in_file`, etc.). Returns `systemMessage` with lint
results or exit code 2 to block on errors.

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Runs ruff deterministically after each edit rather than relying on agent compliance |
| **Trade-offs** | Fires after every tool use; script must filter by `tool_name` to avoid running ruff on non-edit tools. Multiple edits trigger multiple runs. |
| **Failure modes** | Script incorrectly filters tool names; ruff fails on partial files mid-implementation; fires on documentation-only edits where ruff is irrelevant |
| **Effort** | Script (~40 LOC) + 3 lines in `builder.agent.md` frontmatter |
| **Confidence** | .75 |

### Candidate 2 — PreToolUse Kanban Claim Enforcement (all pipeline agents)

**What it does:** Before any write operation, check whether the agent has claimed the
task. Can deny tool execution via `permissionDecision`.

```yaml
# builder.agent.md (and other pipeline agents)
hooks:
  PreToolUse:
    - type: command
      command: "./scripts/hooks/check-claim.sh"
      windows: "powershell -NoProfile -File scripts/hooks/check-claim.ps1"
```

The script reads `tool_name` from stdin JSON, filters for write tools, then queries
`kanban-md` for the current claim. Returns `permissionDecision: "deny"` if unclaimed.

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Hard-blocks unclaimed writes by denying tool execution; addresses a real pipeline discipline gap |
| **Trade-offs** | Fires on every tool use; script must filter by tool name. Requires kanban-md query on every filtered invocation, adding latency. No way to know which task ID to check without session context. |
| **Failure modes** | Script cannot determine which task the agent is working on (no task ID in hook stdin). False denials if kanban-md query fails or returns stale data. |
| **Effort** | Script (~60 LOC) + 3 lines per agent in frontmatter |
| **Confidence** | .55 — low value due to missing task-ID context in hook stdin |

### Candidate 3 — Stop Commit Guard (builder, writer)

**What it does:** At session end, check `git status` and block session close if
uncommitted task-related files exist.

```yaml
# builder.agent.md
hooks:
  Stop:
    - type: command
      command: "./scripts/hooks/stop-commit-guard.sh"
      windows: "powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1"
```

The script checks `stop_hook_active` to prevent infinite loops. Runs `git status --short`,
and if uncommitted files exist, returns `decision: "block"` with a reason string.

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Hard-blocks session end with uncommitted work; deterministic check via `git status`, not a suggestion |
| **Trade-offs** | Fires for every session end; `stop_hook_active` guard prevents infinite loops. Blocked agents consume premium requests while continuing. |
| **Failure modes** | Script crashes (non-2 exit = warning, not block). Session may end mid-edit (crash) before hook fires. Agent may commit garbage to satisfy the guard. |
| **Effort** | Script (~30 LOC) + 3 lines in `builder.agent.md` (and optionally `writer.agent.md`) |
| **Confidence** | .85 — highest value-to-noise ratio; deterministic blocking |

### Candidate 4 — PostToolUse Test Coverage Reminder (builder)

**What it does:** After a terminal command, check if pytest was run and verify coverage.

```yaml
# builder.agent.md
hooks:
  PostToolUse:
    - type: command
      command: "./scripts/hooks/check-coverage.sh"
      windows: "powershell -NoProfile -File scripts/hooks/check-coverage.ps1"
```

The script reads `tool_name` from stdin JSON and filters for terminal tools. If the
terminal ran pytest, it parses coverage from output. Returns `systemMessage` if coverage
is below 90%.

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Deterministic coverage check after pytest runs, not a suggestion |
| **Trade-offs** | Fires after every tool use; script must filter for terminal tools, then parse whether pytest ran. Parsing terminal output is fragile. High complexity for the value. |
| **Failure modes** | Cannot reliably detect whether terminal ran pytest from `tool_response` alone; coverage output format varies. Script complexity high for marginal value. |
| **Effort** | Script (~50 LOC) + 3 lines, but creates a fragile, high-complexity hook |
| **Confidence** | .45 — too fragile for terminal output parsing |

### Candidate 5 — PreToolUse Read-Only Guard (reviewer)

**What it does:** Before a write tool fires in the reviewer’s context, deny execution.

```yaml
# reviewer.agent.md
hooks:
  PreToolUse:
    - type: command
      command: "./scripts/hooks/deny-writes.sh"
      windows: "powershell -NoProfile -File scripts/hooks/deny-writes.ps1"
```

The script reads `tool_name` from stdin JSON and returns
`permissionDecision: "deny"` for write tools (`create_file`,
`replace_string_in_file`, `multi_replace_string_in_file`).

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Hard-denies write tool execution; deterministic enforcement as defense-in-depth behind `tools:` restrictions |
| **Trade-offs** | The reviewer's `tools:` list in frontmatter already restricts write tools — this hook is redundant if tool restrictions are correct. Fires on all PreToolUse events; script must filter by tool name. |
| **Failure modes** | If the reviewer does not have write tools available, the hook fires but `tool_name` never matches a write tool (no risk, wasted processing). If write tools are accidentally granted, the hook is the right fallback. |
| **Effort** | Script (~20 LOC) + 3 lines in `reviewer.agent.md` |
| **Confidence** | .65 — useful as defense-in-depth only; primary enforcement is `tools:` restriction |

## 5. Recommendation Matrix

| Candidate | Hook Type | Agent | Value | Noise | Effort | Confidence | Recommendation |
|-----------|-----------|-------|-------|-------|--------|------------|----------------|
| C1: PostToolUse lint guard | PostToolUse | builder | High | Medium | Low | .75 | **Adopt (Phase 2)** |
| C2: PreToolUse claim enforcement | PreToolUse | all pipeline | Low | High | Medium | .55 | Skip |
| C3: Stop commit guard | Stop | builder, writer | High | Low | Low | .85 | **Adopt (Phase 1)** |
| C4: PostToolUse test coverage | PostToolUse | builder | Low | High | Low | .45 | Skip |
| C5: PreToolUse read-only guard | PreToolUse | reviewer | Medium | Low | Low | .65 | Adopt (Phase 2, defense-in-depth) |

### Recommended Path (.80 confidence)

**Enable hooks in two phases, starting with lowest-noise, highest-value hooks.**

**Phase 1 (MVP — stop hook only):**
- Add the stop commit guard to `builder.agent.md` and `writer.agent.md`
- Script-based check via `git status`; blocks session end with `decision: "block"`
- Catches the most common pipeline discipline failure: sessions that end without committing

**Phase 2 (selective postToolUse):**
- Add the PostToolUse lint guard to `builder.agent.md`; script filters by file-edit tools
- Optionally add the PreToolUse read-only guard to `reviewer.agent.md` as defense-in-depth
- Monitor context window usage; if context inflation becomes measurable, remove postToolUse hooks

**Skip permanently:**
- C2 (claim enforcement via PreToolUse): no task-ID context in hook stdin — cannot identify which task to check
- C4 (coverage check via PostToolUse): parsing terminal output for pytest results is fragile and high-complexity

## 6. Rollout Guidance

### Prerequisites

1. All agent files must be in `agents/*.agent.md` and tracked in git
2. Agents must be using correct tool names (no `todo` → `todos` regression — confirmed fixed by #36)
3. VS Code version must support `chat.useCustomAgentHooks` — verify in VS Code Copilot changelog
4. Team/user understands hooks execute shell commands — review scripts for safety before enabling

### Required Settings

Add to `.vscode/settings.json`:

```json
"chat.useCustomAgentHooks": true
```

This setting is a global opt-in for all agent-scoped hooks in the workspace. Without it,
all `hooks:` frontmatter blocks are silently ignored.

### Phased Adoption Plan

| Phase | Scope | Files Changed | Risk |
|-------|-------|--------------|------|
| Phase 1 | Enable stop hooks on builder + writer | `agents/builder.agent.md`, `agents/writer.agent.md`, `scripts/hooks/stop-commit-guard.ps1` | Very low — 1 script per session end |
| Phase 2 | Add PostToolUse lint guard on builder | `agents/builder.agent.md`, `scripts/hooks/lint-changed.ps1` | Low-medium — script must filter by tool name |
| Phase 3 | Add PreToolUse read-only guard on reviewer | `agents/reviewer.agent.md`, `scripts/hooks/deny-writes.ps1` | Very low — defense-in-depth |

Each phase should be merged separately and observed for:
- Unexpected context window inflation
- Hooks firing on unintended tool invocations
- Agents acting confused by conflicting prompt signals

### When Not to Use Hooks

Do not use VS Code agent-scoped hooks when:

1. **Hard blocking is needed but hooks cannot query the required state.** Exit code 2 and `permissionDecision: "deny"` now support hard blocking, but if the decision requires state that isn't available in hook stdin (e.g., which kanban task is active), hooks cannot help. Use `tools:` restrictions or agent instructions instead.
2. **Cross-agent enforcement is needed.** Hooks apply only to the agent that defines them. A hook on `builder.agent.md` does not fire when the orchestrator invokes a subagent. Use `instructions/agent-common.instructions.md` rules for cross-agent policy.
3. **Complex state queries are required.** Hooks can query external state (git, kanban-md) via script, but each query adds latency to every hook invocation. Keep checks fast (<5s) or use instructions instead.
4. **High-frequency tools are involved.** PostToolUse fires after every tool use. Script-based filtering by `tool_name` is cheap, but the shell spawn overhead adds up on high-frequency tools (e.g., read_file). Gate on the most specific event type and filter in script.
5. **The hook would duplicate existing instruction coverage.** If `agent-common.instructions.md` already covers the behaviour and the agent reliably follows it, a hook adds complexity without adding enforcement. Reserve hooks for behaviour that agents demonstrably forget.

## 7. Conclusion

VS Code agent-scoped hooks are a capable enforcement mechanism. They execute shell
commands at lifecycle events and support hard blocking (exit code 2, `permissionDecision:
"deny"`, Stop `decision: "block"`). They excel as commit guards (Stop hook) and targeted
mid-session automation for specific critical actions. They are not suitable for checks
requiring state unavailable in hook stdin, cross-agent policy, or high-frequency tools
where shell spawn overhead compounds.

**Adopt the stop commit guard (Phase 1) immediately.** It is the highest-value, lowest-cost
hook configuration available. Phase 2 (lint guard) adds value but requires script-based
tool-name filtering. Skip all candidates that depend on state unavailable in hook stdin.

The internal HookRegistry (`core/hooks.py`) remains the correct mechanism for
observational, structured event handling within OwlBear's Python runtime. VS Code hooks
complement it at the agent-conversation layer but must not be treated as equivalent.

## 8. Follow-up Tasks

| # | Title | Priority | Depends On | One-line AC |
|---|-------|----------|-----------|-------------|
| #209 | Add stop commit guard hooks to builder and writer agents (Phase 1) | nice-to-have | None | Stop hooks added to builder.agent.md and writer.agent.md; `chat.useCustomAgentHooks: true` set |
| #210 | Add PostToolUse lint guard hook to builder agent (Phase 2) | nice-to-have | #209 | PostToolUse hook on file edits added to builder.agent.md; no YAML conflicts |
| #211 | Add PreToolUse read-only guard hook to reviewer agent (Phase 2, defense-in-depth) | nice-to-have | #209 | PreToolUse hook on file writes added to reviewer.agent.md as secondary guard |
