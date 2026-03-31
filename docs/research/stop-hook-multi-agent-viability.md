# Stop Hook Multi-Agent Viability Analysis

> **Owning task:** #209 — Add stop commit guard hooks to builder and writer agents
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #209 was blocked after its 2nd architecture review. The blocking Stop hook
model creates deadlock when parallel subagents share a working tree — agent A's
Stop hook sees agent B's uncommitted files and blocks, and vice versa.

The architect posed four questions before re-entry:

1. Is `systemMessage` a supported Stop hook return type?
2. Does `systemMessage` reach the agent before session termination?
3. Is a soft reminder valuable for pipeline-only agents with commit instructions?
4. Should Stop hooks be scoped to user-invocable agents only?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical hook spec, Stop output schema, systemMessage semantics |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — agent-scoped hooks, SubagentStop behavior |
| OwlBear agent-common.instructions.md | `instructions/agent-common.instructions.md` §Commit discipline | 1.0 — existing commit enforcement |
| OwlBear #86 hooks research | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` | 1.0 — parent research, candidate matrix |

## 3. Analysis

### Q1: Is `systemMessage` a supported Stop hook return?

**Yes.** The VS Code docs define a common output format for all hooks:

```json
{ "continue": true, "stopReason": "...", "systemMessage": "..." }
```

`systemMessage` is: "Warning message displayed to the user" — available on all
8 hook types including Stop. This is separate from `hookSpecificOutput` which
has `decision`/`reason` for Stop hooks.

### Q2: Does `systemMessage` reach the agent before termination?

**No.** The docs state: "`systemMessage` displays a warning to the user in the
chat, regardless of other decisions." Without `decision: "block"`, the agent
session ends immediately. The message appears in the chat panel *after* the
agent has stopped — the agent never sees it.

Only `decision: "block"` + `reason` keeps the agent running and injects the
reason into the agent's conversation as guidance for what to do next.

| Return shape | Agent continues? | Agent sees it? | User sees it? |
|-------------|------------------|----------------|---------------|
| `{}` (empty) | No | N/A | No |
| `{ systemMessage: "..." }` | No | No | Yes (post-mortem) |
| `{ decision: "block", reason: "..." }` | Yes | Yes (reason) | Yes |

### Q3: Is a soft reminder valuable for pipeline-only agents?

**No (.90 confidence).** Three compounding factors:

1. **SubagentStop semantics.** The docs confirm: "When scoped to a custom agent,
   the Stop hook is also treated as SubagentStop." Pipeline agents (builder,
   writer) are dispatched as subagents — their Stop hook fires as SubagentStop.
   The `systemMessage` appears in the orchestrator's chat panel, where no human
   is watching.

2. **Orchestrator reads Channel A/B, not chat.** The orchestrator reads task
   bodies (`kanban-md show`) and subagent return text. It does not parse chat
   panel warnings. A `systemMessage` from a subagent's Stop hook is invisible
   to the orchestration loop.

3. **Agent-common already mandates commits.** `agent-common.instructions.md`
   §Commit discipline explicitly requires builder and writer to commit before
   handoff. The 4-agent commit table (test-writer, builder, writer, auditor)
   is the primary enforcement. A post-mortem chat warning adds no enforcement.

### Q4: Should Stop hooks target user-invocable agents only?

**Yes, in principle — but no current candidates (.85 confidence).**

| Agent | User-invocable? | Produces commits? | Stop hook useful? |
|-------|----------------|-------------------|-------------------|
| orchestrator | Yes | No | No — dispatches subagents |
| kanban-planner | Yes | No | No — creates tasks only |
| curator | Yes | No | No — memory/doc operations |
| builder | No (pipeline) | Yes | **Deadlocks** in parallel |
| writer | No (pipeline) | Yes | **Deadlocks** in parallel |

The three user-invocable agents don't produce code commits. The two agents that
commit (builder, writer) run as subagents in parallel dispatch. No current agent
is both user-invocable AND commit-producing.

### Impact on #210 and #211

Neither #210 nor #211 shares the deadlock problem:

| Task | Hook type | Deadlock risk? | Depends on #209 for... |
|------|-----------|----------------|------------------------|
| #210 | PostToolUse | No — fires per-tool, not per-session | `chat.useCustomAgentHooks` setting only |
| #211 | PreToolUse | No — fires per-tool, not per-session | `chat.useCustomAgentHooks` setting only |

The `chat.useCustomAgentHooks` setting is already present in `.vscode/settings.json`
(added during #209's builder pass). Tasks #210 and #211 can proceed by removing
their dependency on #209.

## 4. Recommendation (.90 confidence)

**Cancel #209 as currently scoped.** The blocking Stop hook model is incompatible
with parallel subagent dispatch. The non-blocking `systemMessage` alternative
doesn't reach agents or the orchestrator. Current commit discipline enforcement
via instructions is sufficient — hooks add complexity without adding enforcement.

**Unblock #210 and #211.** Remove their `depends_on: [209]` — the settings
prerequisite is already met. Neither task has the multi-agent deadlock concern.

**Future-proof.** If an interactive user-facing coding agent is added later, a
Stop commit guard is appropriate — create a new task at that time, scoped to the
specific agent. Don't build the infrastructure now (YAGNI).

**Clean up #209 artifacts.** The existing script and test file should be removed:
- `scripts/hooks/stop-commit-guard.ps1` (implements the deadlocking model)
- `tests/test_stop_commit_guard_hooks.py` (23 tests for the invalidated model)
- `hooks:` sections in `agents/builder.agent.md` and `agents/writer.agent.md`

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Remove #209 stop commit guard artifacts (script, tests, hooks YAML)" --priority nice-to-have --status ideation --tags "scope:agents,hooks,type:build" --body "## Context\nSee docs/research/stop-hook-multi-agent-viability.md for full analysis.\n#209 blocking Stop hook model is incompatible with parallel subagent dispatch. Artifacts from the invalidated implementation should be removed.\n\n## Acceptance Criteria\n- [ ] Delete scripts/hooks/stop-commit-guard.ps1\n- [ ] Delete tests/test_stop_commit_guard_hooks.py\n- [ ] Remove hooks: section from agents/builder.agent.md YAML frontmatter\n- [ ] Remove hooks: section from agents/writer.agent.md YAML frontmatter\n- [ ] Verify both agent files still parse with valid YAML frontmatter\n- [ ] Verify test suite passes without the deleted test file"
kanban\kanban-md.exe create "Unblock #210 and #211: remove depends_on #209" --priority nice-to-have --status ideation --tags "scope:agents,hooks,type:build" --body "## Context\nSee docs/research/stop-hook-multi-agent-viability.md §3 Q4.\nThe chat.useCustomAgentHooks setting (the only real prerequisite from #209) is already present in .vscode/settings.json. #210 and #211 can proceed independently.\n\n## Acceptance Criteria\n- [ ] Remove depends_on: [209] from kanban/tasks/210-*.md frontmatter\n- [ ] Remove depends_on: [209] from kanban/tasks/211-*.md frontmatter\n- [ ] Verify both tasks are no longer blocked in kanban-md list --blocked"
```
