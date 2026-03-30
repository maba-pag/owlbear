# Stop Commit Guard Hooks — Phase 1 Implementation Research

> **Owning task:** #209 — Add stop commit guard hooks to builder and writer agents
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #209 (from #86 §6) calls for adding `stop` hooks to builder and writer agents that
remind them to commit before session end. The original research (#86, 2026-03-29) proposed
a prompt-injection format (`prompt:` key in YAML). However, the VS Code hooks API has
since been documented with a **command-execution model** (updated 2026-03-25). This
research validates the correct implementation approach against the current API.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical hook spec, JSON command format |
| VS Code Custom Agents docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — `hooks` frontmatter field, agent-scoped format |
| OwlBear hooks research (#86) | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` | 1.0 — parent research, proposed candidates |
| OwlBear agent-md-format (#4) | `docs/research/agent-md-format.md` §3, §7 | .85 — hooks field listed in frontmatter spec |

## 3. Analysis — API Model Change

### 3.1 Original Research vs Current API

| Dimension | #86 Research (2026-03-29) | Current VS Code API (2026-03-25) |
|-----------|--------------------------|----------------------------------|
| Hook format | `prompt:` text injection | `type: command` + `command:` shell execution |
| Event names | lowerCamelCase (`stop`) | PascalCase (`Stop`) — VS Code auto-converts |
| Enforcement | Soft only (prompt nudge) | Exit code 2 blocks; `decision: "block"` in Stop |
| JSON I/O | None | stdin JSON input, stdout JSON output |
| Loop prevention | Not needed (one-shot prompt) | `stop_hook_active` field prevents infinite re-fires |
| Blocking capability | None | Stop hook can prevent session end with `decision: "block"` |

**Key finding (.95 confidence):** The #86 research's YAML examples (using `prompt:` and
`when:` keys) do not match the current VS Code hooks API. The correct format requires
`type: command` entries that execute shell commands and return structured JSON.

### 3.2 Implementation Approaches

| Approach | Description | Pros | Cons | Confidence |
|----------|-------------|------|------|------------|
| A: Script file | PowerShell script in `scripts/hooks/` reads stdin JSON, checks git status, returns blocking JSON | Testable, handles `stop_hook_active`, produces correct JSON | Adds a script file to maintain | .85 |
| B: Inline command | Single-line PowerShell in `command:` field | No extra files | Hard to read, no `stop_hook_active` check, fragile escaping | .50 |
| C: Non-blocking systemMessage | Script returns `systemMessage` warning but does not block | Matches original "reminder" intent, no risk of infinite loops | Agent can still ignore it | .70 |

### 3.3 Stop Hook Contract

From the VS Code docs, the Stop hook:

- Fires when agent session ends (or when a subagent completes, for agent-scoped hooks)
- Receives `stop_hook_active: true` on re-fires (must check to prevent infinite loops)
- Returns `decision: "block"` + `reason:` to prevent the agent from stopping
- Blocked agents continue running and consume premium requests

## 4. Recommendation (.85 confidence)

**Use Approach A (script file)** with a blocking stop hook. This is stronger than the
original "reminder" intent — it actually prevents the session from ending with uncommitted
work. The `stop_hook_active` safeguard prevents infinite loops.

**Script location:** `scripts/hooks/stop-commit-guard.ps1`

**Frontmatter format (both agents):**

```yaml
hooks:
  Stop:
    - type: command
      windows: "powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1"
```

**Required setting:** `"chat.useCustomAgentHooks": true` in `.vscode/settings.json`
(confirmed not yet present).

**AC updates needed for #209:**

1. Event name: `Stop` (PascalCase), not `stop`
2. Hook format: `type: command` + script, not `prompt:` text
3. New deliverable: `scripts/hooks/stop-commit-guard.ps1`
4. Add `stop_hook_active` loop-prevention check in script

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Update #86 research doc to reflect command-execution hook model" --priority nice-to-have --status ideation --tags "docs,hooks,scope:agents" --body "## Context\nThe VS Code hooks API (updated 3/25/2026) uses command-execution model, not prompt-injection.\ndocs/research/agent-scoped-hooks-pipeline-enforcement.md §3.2 and §4 contain incorrect YAML examples.\n\n## Acceptance Criteria\n- [ ] Update YAML examples in §3.2 and §4 to use type: command format\n- [ ] Update §3.3 constraint table: hooks now support blocking via exit code 2\n- [ ] Note PascalCase event names (Stop, PreToolUse, PostToolUse)\n- [ ] Keep the recommendation matrix conclusions unchanged (just fix format)"
```

## 6. Impact on #209 AC

The current #209 AC is implementable with these corrections:

| AC Item | Current Wording | Correct Interpretation |
|---------|-----------------|----------------------|
| Add `stop` hook to builder | `stop` key in frontmatter | `Stop:` (PascalCase) with `type: command` entry |
| "reminds the builder to run git status" | Prompt injection | Script that checks git status, blocks if uncommitted |
| Add to writer.agent.md | Same as builder | Same script, same frontmatter |
| `chat.useCustomAgentHooks: true` | Correct as-is | Confirmed required, not yet in settings.json |
| Verify YAML parses correctly | Correct as-is | Validate with VS Code diagnostics view |
