# SessionStart Context Injection Hook (Phase 4)

> **Owning task:** #590 — Add SessionStart context injection hook to pipeline agents
> **Date:** 2026-04-04 **Status:** Complete
> **Parent research:** `docs/research/agent-scoped-hooks.md` §3.2

## 1. Context and Question

Validation pass on #590 AC. Parent research (#37) recommends a SessionStart hook at
.70 confidence for injecting git branch and recent commits into pipeline agent sessions.
This doc validates feasibility, identifies the SessionStart-vs-SubagentStart routing
ambiguity for subagent-only agents, and proposes an AC revision with a verification step.

## 2. Sources Studied

| # | Source | Location/URL | Relevance |
|---|--------|-------------|-----------|
| 1 | VS Code hooks docs (4/1/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — SessionStart I/O schema, `additionalContext` output, agent-scoped hooks format |
| 2 | Parent research (#37) | `docs/research/agent-scoped-hooks.md` §3.2 | 1.0 — lifecycle hook evaluation, .70 confidence for SessionStart |
| 3 | Phase 3 research (#589) | `docs/research/pretooluse-test-writer-path-guard.md` | .90 — recent hook implementation pattern, challenger findings |
| 4 | `scripts/hooks/deny-writes.ps1` | In-repo: Phase 2 pattern | 1.0 — stdin JSON reading, JSON output format, error handling |
| 5 | `scripts/hooks/lint-changed.ps1` | In-repo: Phase 2 pattern | 1.0 — established PowerShell hook patterns |

## 3. Analysis

### 3.1 Codebase Validation

| Prerequisite | Status | Evidence |
|-------------|--------|----------|
| `chat.useCustomAgentHooks: true` | Enabled | `.vscode/settings.json` line 60 |
| Phase 2 deployed and working | Yes | `deny-writes.ps1` (reviewer), `lint-changed.ps1` (builder) |
| Target agents have no SessionStart hook | Confirmed | builder, test-writer, doc-writer frontmatter |
| `scripts/hooks/` directory exists | Yes | 2 scripts already present |

### 3.2 SessionStart Routing for Subagents (Key Risk)

Pipeline agents (builder, test-writer, doc-writer) are `user-invocable: false` —
always invoked as subagents. The docs say SessionStart fires "when a new agent session
begins." The docs explicitly state Stop hooks "are also treated as SubagentStop" for
custom agents, but make NO parallel statement for SessionStart.

| Evidence | Interpretation |
|----------|---------------|
| Agent-scoped hooks "run when agent is active, including as subagent" | Scope is confirmed for subagents |
| PreToolUse/PostToolUse work on subagent-only agents (proven) | Tool-use events fire for subagents ✅ |
| Stop → SubagentStop documented explicitly | Duality exists for Stop, unconfirmed for SessionStart |
| SubagentStart input includes `agent_type` | Fires on the PARENT, not the subagent |

**Assessment (.60 confidence):** SessionStart likely fires for subagent sessions (each
subagent gets its own conversation context), but this is unverified. Impact if wrong:
hook silently does nothing — agents proceed without extra context (status quo). No
harm, no blocking, no security implications.

### 3.3 Implementation Approach Comparison

| Approach | Scope | Pros | Cons | KISS |
|----------|-------|------|------|------|
| **A: Agent-scoped SessionStart** | 3 agents | Per-agent control, follows AC, established frontmatter pattern | Unverified subagent routing | High |
| B: Workspace `.github/hooks/` | All agents | One config file | Fires for all 14 agents (noise for read-only agents) | Medium |
| C: SubagentStart on orchestrator | All subagents | Verified event for subagents | All subagents get context, logic concentration | Low |
| D: UserPromptSubmit | All prompts | Fires on every user prompt | Fires repeatedly, not once per session | Low |

**Recommendation: Option A with SubagentStart fallback.** If TDD verification shows
SessionStart doesn't fire for subagent sessions, swap to SubagentStart in agent
frontmatter (same script, different event name — 1 YAML line change per agent).

### 3.4 Script Design

Following `deny-writes.ps1` / `lint-changed.ps1` patterns:

```
Input:  stdin JSON { "source": "new", "cwd": "...", ... }
Output: { "hookSpecificOutput": { "hookEventName": "SessionStart",
          "additionalContext": "Branch: main | Commits: abc Fix X | def Add Y | ghi Refactor Z" } }
Error:  {} (non-blocking)
```

| Design choice | Rationale |
|---------------|-----------|
| Read stdin with `[Console]::In.ReadToEnd()` | Prevents buffering deadlock (established pattern) |
| `git branch --show-current 2>$null` | 10ms, silent on failure |
| `git log --oneline -3 --no-decorate 2>$null` | 20ms, clean output, silent on failure |
| Return `{}` on any failure | Non-blocking: agents proceed without extra context |
| Pipe-separated one-liner output | Minimizes injected token count (~20 tokens) |

**Performance:** ~30ms total. Well under 5-second AC requirement and 30-second default
timeout.

### 3.5 Agent Frontmatter Changes

Builder already has `hooks:` with PostToolUse. Adding SessionStart:

```yaml
hooks:
  SessionStart:
    - type: command
      command: powershell -NoProfile -NonInteractive -File scripts/hooks/session-context.ps1
  PostToolUse:
    - type: command
      command: powershell -NoProfile -NonInteractive -File scripts/hooks/lint-changed.ps1
```

Test-writer and doc-writer have no `hooks:` key yet — add a new section.

### 3.6 Dependencies

No dependency on Phase 3 (#589). The SessionStart hook and PreToolUse guard use
different scripts, different events, and different output schemas. Can be implemented
independently.

## 4. Recommendation (.72 confidence)

**Challenge:** FALLBACK — challenger subagent not available in researcher toolset.
**Codebase exploration** found the SessionStart-subagent routing ambiguity (§3.2).

Proceed with implementation using agent-scoped SessionStart hooks as specified in AC.
The approach follows the established hook pattern (Phases 1-2) and the script is ~25 LOC.
The key risk (SessionStart not firing for subagents) is low-impact and verifiable during
TDD RED phase.

**Proposed AC Additions:**
- Add verification step: during TDD RED, confirm SessionStart hook output appears in
  Chat Hooks output channel when a subagent is dispatched
- If SessionStart doesn't fire, change event from `SessionStart` to `SubagentStart`
  (same script, 1 YAML line per agent)

**Tier classification:** T1 — Autonomous. Incremental hook addition to established
pattern. No new capabilities, no architecture changes, no security implications.

## 5. Follow-up Tasks

No new follow-up tasks required. #590 is the implementation task. Existing #591
(doc-writer path guard, Phase 5) remains valid at `someday` priority.
