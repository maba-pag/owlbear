# Stop Commit Guard Defect Remediation

> **Owning task:** #209 — Add stop commit guard hooks to builder and writer agents
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #209 was implemented (builder commit a0aa1ca, 23 tests passing) but two runtime
defects were discovered that prevent builder and writer agents from dispatching. This
research validates the defects against the VS Code hooks API (3/25/2026 spec) and
recommends a remediation path.

Prior research: `docs/research/stop-commit-guard-hooks-phase1.md` (Phase 1 approach),
`docs/research/agent-scoped-hooks-pipeline-enforcement.md` (parent #86 survey).

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical Stop hook I/O, command properties |
| VS Code Hooks docs — Hook command properties | (same page, §Hook command properties) | .95 — `command` vs `windows` semantics |
| VS Code Hooks docs — Stop output | (same page, §Stop output) | .95 — `hookSpecificOutput` wrapper for Stop |
| OwlBear Phase 1 research | `docs/research/stop-commit-guard-hooks-phase1.md` | 1.0 — original recommendation |
| OwlBear #86 research §4 Candidate 3 | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` | 1.0 — original Stop hook design |

## 3. Defect Validation

### Defect 1: `windows:` without `command:` — Confirmed (.90)

**Evidence from docs (2 sources):**

1. Hook command properties table: `command` = "Default command to run (cross-platform)";
   `windows` = "Windows-specific command override". The docs state: "Each hook entry must
   have `type: "command"` and at least one command property."
2. Every OS-specific example in the docs includes a base `command:` alongside `windows:`.
   The agent-scoped example uses only `command:` with no OS-specific keys.

The fallback chain is: OS-specific → `command`. If `command:` is absent and the platform
doesn't match `windows:`, VS Code has nothing to fall back to. Although this project is
Windows-only, the API contract expects `command:` as the base.

**Fix:** Replace `windows:` with `command:` in both agent files. No OS-specific override
needed for a Windows-only project.

### Defect 2: Global `git status` causes parallel-agent deadlock — Confirmed (.95)

**Evidence from docs + architecture (2 sources):**

1. VS Code docs: "When scoped to a custom agent, the Stop hook is also treated as
   `SubagentStop`." In the orchestrator pipeline, builder and writer are dispatched as
   subagents. Each agent's Stop hook fires independently when that agent finishes.
2. OwlBear's `agent-common.instructions.md` §Commit discipline: builder and writer both
   commit to the same repo. `git status --short` checks the **entire** working tree.

**Deadlock scenario:** Builder finishes → Stop hook fires → `git status --short` sees
writer's uncommitted files → blocks with `decision: "block"` → builder continues running
(consuming premium requests) → writer finishes → same: sees builder's now-in-progress
changes → both agents loop.

The `stop_hook_active` guard only prevents the hook from re-firing on itself. It does not
prevent cross-agent dirty-state interference.

### Defect 3 (new): Stop hook output format — Potential (.70)

The current script returns `{"decision":"block","reason":"..."}` at top level. However,
the VS Code Stop hook docs show the canonical output format as:

```json
{"hookSpecificOutput":{"hookEventName":"Stop","decision":"block","reason":"..."}}
```

The SubagentStop docs show `decision` at top level (no wrapper). Since agent-scoped Stop
hooks are "treated as SubagentStop", the top-level format may work. But the Stop-specific
docs use `hookSpecificOutput`. This ambiguity is a risk.

## 4. Options Analysis

| Option | Description | Deadlock safe? | Enforcement | Complexity | Confidence |
|--------|-------------|----------------|-------------|------------|------------|
| A: Fix `command:` + keep blocking | Fix defect 1 only, keep `decision: "block"` | No | Hard block | Low | .40 |
| B: Non-blocking `systemMessage` | Return `systemMessage` warning, no block | Yes | Soft reminder | Low | .85 |
| C: Remove hook entirely | Delete hooks, rely on agent instructions | Yes | None (agent compliance) | Lowest | .60 |
| D: Scoped git check per agent | Filter `git status` by agent-owned files | Yes | Hard block (scoped) | High | .30 |

**Option D is infeasible** because no file-to-agent mapping exists. The Stop hook stdin
provides `sessionId` but no list of files the agent modified.

**Option A leaves the deadlock unresolved** — fixing `command:` alone is insufficient.

**Option C removes all automated enforcement.** Agent instructions already say "commit
before handoff," but agents demonstrably forget (that's why the hook was requested).

**Option B is recommended (.85 confidence).** It delivers automated enforcement without
deadlock risk. The `systemMessage` appears in the agent's chat, reminding it to commit.
This matches the original #86 research intent ("reminder"), and KISS/YAGNI: a soft
reminder is sufficient when hard blocking is unsafe.

## 5. Recommended Changes

### Script: `scripts/hooks/stop-commit-guard.ps1`

- Keep `stop_hook_active` loop-prevention guard
- Keep `git status --short` check
- Replace `decision: "block"` with `systemMessage` output
- Use `hookSpecificOutput` wrapper (safest format per Stop hook docs)

Output when dirty:

```json
{"systemMessage":"Uncommitted changes detected. Run git add + git commit before ending."}
```

Output when clean or `stop_hook_active`: `{}`

### Agent files: `agents/builder.agent.md`, `agents/writer.agent.md`

```yaml
hooks:
  Stop:
    - type: command
      command: "powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1"
```

### Tests: `tests/test_stop_commit_guard_hooks.py`

- Update 4 assertions checking `windows:` → check `command:` instead
- Update behavioral test for dirty tree: expect `systemMessage` key instead of
  `decision: "block"`
- Remove/update assertions about `decision` and `reason` keys in script content

### AC revision for #209

Revised AC for the non-blocking `systemMessage` model:

1. Script exists, reads stdin JSON, checks `stop_hook_active`, runs `git status --short`
2. If dirty: returns JSON with `systemMessage` key (non-blocking reminder)
3. If clean: returns empty JSON `{}`
4. Builder frontmatter: `hooks.Stop` with `type: command`, `command:` key
5. Writer frontmatter: identical hooks section
6. `chat.useCustomAgentHooks: true` in `.vscode/settings.json`
7. Both agent files have valid YAML frontmatter

## 6. Impact on Downstream Tasks

| Task | Impact | Action needed |
|------|--------|---------------|
| #210 (PostToolUse lint guard) | Uses outdated prompt-injection AC wording | AC needs revision to match command-execution model |
| #211 (PreToolUse read-only guard) | Same outdated AC | AC needs revision |
| #212 (Update #86 research doc) | Still valid | No change |

#210 and #211 depend on #209. Their AC references "injecting a prompt" which is the old
model. The architect should update their AC during the next review pass.

## 7. Follow-up Tasks

```
kanban\kanban-md.exe create "Fix #210 and #211 AC to use command-execution hook model" --priority nice-to-have --status ideation --tags "docs,hooks,scope:agents" --body "## Context\nTasks #210 and #211 reference the outdated prompt-injection hook model. Their AC says 'injecting a prompt' but the VS Code hooks API (3/25/2026) uses command-execution with JSON I/O.\n\n## Acceptance Criteria\n- [ ] Update #210 AC: PostToolUse hook should use type: command + script, not prompt injection\n- [ ] Update #210 AC: tool filtering done in script via stdin tool_name, not YAML gating\n- [ ] Update #211 AC: PreToolUse hook should use type: command + script with permissionDecision\n- [ ] Both tasks use command: key (not windows: or bash:)"
```
