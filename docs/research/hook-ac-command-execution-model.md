# Fix #210 and #211 AC to Use Command-Execution Hook Model

> **Owning task:** #213 — Fix #210 and #211 AC to use command-execution hook model
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Tasks #210 (PostToolUse lint guard) and #211 (PreToolUse read-only guard) were created
from the #86 parent research before the hooks API model was corrected for #209. Their AC
still references the outdated prompt-injection model: YAML tool gating via `tool ==`
conditions, `edit/editFiles` tool set names, and "injecting a prompt" as the mechanism.

**Question:** What should the corrected AC be, per the VS Code hooks API (3/25/2026)?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (3/25/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical spec |
| VS Code Hooks FAQ — tool names | (same page, §FAQ) | .90 — confirms VS Code tool names (`create_file`, `replace_string_in_file`) |
| OwlBear #209 remediation research | `docs/research/stop-commit-guard-defect-remediation.md` | 1.0 — confirmed `command:` model, established precedent |
| OwlBear #86 parent research §4 | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` | 1.0 — original candidates C1 (PostToolUse) and C5 (PreToolUse) |

## 3. Analysis — AC Defects

### 3.1 Defects in #210 AC (PostToolUse lint guard)

| AC line | Defect | Correct model |
|---------|--------|---------------|
| "gated on `tool == 'edit/editFiles' ...`" | No YAML gating exists; `edit/editFiles` is a tool set reference, not a stdin `tool_name` | Script reads `tool_name` from stdin JSON; actual names are `create_file`, `replace_string_in_file`, `multi_replace_string_in_file` |
| "injecting a prompt to run `uv run ruff check`" | Prompt injection is not how hooks work | Script executes ruff directly; returns lint results via `systemMessage` or blocks with exit code 2 |

### 3.2 Defects in #211 AC (PreToolUse read-only guard)

| AC line | Defect | Correct model |
|---------|--------|---------------|
| "gated on `tool == 'edit/editFiles' ...`" | Same: no YAML gating, wrong tool names | Script reads `tool_name` from stdin; filters for `create_file`, `replace_string_in_file`, `multi_replace_string_in_file` |
| "injecting a stop-and-return reminder" | Wrong mechanism | PreToolUse returns `hookSpecificOutput` with `permissionDecision: "deny"` to hard-block tool execution |

### 3.3 Common defect: `command:` key

Both tasks' AC must require the `command:` key (cross-platform default), not `windows:`
alone. The `windows:` key is an OS-specific override that requires `command:` as fallback.
This was established by the #209 remediation (Defect 1).

## 4. Corrected AC

### #210 — PostToolUse lint guard (builder)

```
- [ ] Add PostToolUse hook to agents/builder.agent.md frontmatter: type: command,
      command: key pointing to scripts/hooks/lint-changed.ps1
- [ ] Script reads tool_name from stdin JSON; runs ruff only for file-edit tools
      (create_file, replace_string_in_file, multi_replace_string_in_file)
- [ ] On lint errors: returns systemMessage with ruff output (or blocks via exit code 2)
- [ ] On non-edit tools or clean lint: returns empty JSON {}
- [ ] chat.useCustomAgentHooks setting must already be enabled (prerequisite from #209)
- [ ] Hook YAML must not conflict with existing Stop hook from Phase 1
- [ ] Agent file parses as valid YAML frontmatter
```

### #211 — PreToolUse read-only guard (reviewer)

```
- [ ] Add PreToolUse hook to agents/reviewer.agent.md frontmatter: type: command,
      command: key pointing to scripts/hooks/deny-writes.ps1
- [ ] Script reads tool_name from stdin JSON; filters for write tools
      (create_file, replace_string_in_file, multi_replace_string_in_file)
- [ ] On write tool match: returns hookSpecificOutput with permissionDecision: "deny"
      and permissionDecisionReason explaining reviewer is read-only
- [ ] On non-write tools: returns empty JSON {}
- [ ] chat.useCustomAgentHooks setting must already be enabled (prerequisite from #209)
- [ ] Hook must not conflict with existing tools: restrictions in reviewer.agent.md
- [ ] Agent file parses as valid YAML frontmatter
```

## 5. Follow-up Tasks

No new tasks needed — #213 itself is the AC-update task. The corrected AC has been
applied directly to #210 and #211 via `kanban-md edit`.
