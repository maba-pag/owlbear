# PostToolUse Subagent Output Routing — Empirical Verification

> **Owning task:** #532 — Verify PostToolUse hook output routing in subagent context
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #210 (PostToolUse lint guard) depends on knowing which PostToolUse output
mechanisms reach the builder model in subagent context. The #210 feasibility
analysis recommended exit code 2 as the primary model-facing mechanism, but
this was theoretical. The #209 cycle proved docs-based routing assumptions are
unreliable. This task performed empirical verification via user-executed spike.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (4/2/2026) | code.visualstudio.com/docs/copilot/customization/hooks | .95 — PostToolUse I/O schema, exit codes |
| Chat Debug View (empirical) | VS Code Tool Call Debug Log observation | 1.0 — confirmed additionalContext routing |
| Hooks output channel (empirical) | GitHub Copilot Chat Hooks output channel logs | 1.0 — exit code classification, hook timing |
| OwlBear #210 feasibility | docs/research/posttooluse-lint-guard-feasibility.md | 1.0 — prior recommendation (exit code 2 primary) |
| OwlBear #209 viability | docs/research/stop-hook-multi-agent-viability.md | 1.0 — precedent for routing failures |

## 3. Empirical Results

### 3.1 Test Protocol

Two probe hooks added to builder.agent.md, fired during subagent file-edit task:

1. **Probe A:** Returns `additionalContext = "PROBE_ADDITIONAL_CONTEXT_532"` and
   `systemMessage = "PROBE_SYSTEM_MESSAGE_532"` for file-edit tool_names.
2. **Probe B:** Writes `"PROBE_EXIT2_532"` to stderr and exits with code 2.

Both probes used `powershell -NoProfile -Command "..."` one-liner invocation.
Observation: Chat Debug View, main chat panel, Hooks output channel.

### 3.2 Results Matrix

| Mechanism | Model-facing? | User-facing? | Hooks classification |
|-----------|:------------:|:------------:|:--------------------:|
| `additionalContext` | **YES** | No | Success |
| `systemMessage` | No (inferred, #209) | Yes | Success |
| Exit code 2 + stderr | **NO** (via `-Command`) | Yes (as warning) | NonBlockingError |
| `decision:block+reason` | Untested | Untested | — |

### 3.3 additionalContext — Confirmed Model-Facing

Chat Debug View Tool Call Debug Log shows the injected context in XML tags:

```xml
<PostToolUse-context>
PROBE_ADDITIONAL_CONTEXT_532
</PostToolUse-context>
```

This confirms the SubagentStart analogy: PostToolUse `additionalContext` targets
the active agent's conversation (the subagent when hook fires during subagent
session).

**Limitation (N=1):** Confirmed for `tool_name: create_file` only. Not tested
with `apply_patch` or for large payloads. Context position semantics (system
slot vs user turn) unknown.

### 3.4 Exit Code 2 — NOT Model-Facing via `-Command`

Hooks engine logged "NonBlockingError" (not "BlockingError"). Stderr appeared
as user-facing "Warning from Post-Tool Use hook" message. No Chat Debug View
entry.

**Critical qualification:** The probe used `powershell -Command "..."` one-liners.
PS 5.1 `exit 2` inside `-Command` mode may not propagate exit codes correctly.
#210 specifies `powershell -File scripts/hooks/lint-changed.ps1` — the `-File`
invocation mode handles exit codes differently and may correctly propagate exit
code 2. **This finding applies only to `-Command` invocation.**

**`-File` verification (#548):** A `.ps1` script exiting with code 2 via
`powershell -File` was also tested in subagent PostToolUse context. The hooks
engine again classified it as NonBlockingError. Exit code 2 is NOT model-facing
via either PS 5.1 invocation mode in this context.

### 3.5 PS 5.1 Stdin Parsing Pitfall

The initial hook script form caused PS 5.1 to interpret JSON stdin as code.
The corrected inline form (`([Console]::In.ReadToEnd() | ConvertFrom-Json)`)
resolves this. Root cause: PS 5.1 special handling of `$input` automatic
variable and `{...}` JSON at stdin start. The `-File` invocation mode (#210's
approach) avoids this entirely.

### 3.6 Tool Name Discovery: `apply_patch`

Hook invocation #0 logged `tool_name: "apply_patch"` for a file edit operation.
The builder uses `apply_patch` in addition to `create_file`,
`replace_string_in_file`, and `multi_replace_string_in_file`. **Task #210's
tool_name filter must include `apply_patch`** to capture all edit operations.

## 4. Recommendation (.80 confidence)

**`additionalContext` is the confirmed model-facing channel** for PostToolUse
output in subagent context. Empirically verified (N=1, `create_file` tool).

**For #210 (lint guard):** The current `systemMessage`-based design is valid
for its stated scope (user-facing monitoring). Two corrections needed:

1. Add `apply_patch` to the tool_name filter
2. Future model-facing upgrade should use `additionalContext`, not exit code 2

**Exit code 2:** NOT model-facing via either PS 5.1 invocation mode (`-Command`
or `-File`) in PostToolUse subagent context. Confirmed by #532 (`-Command`) and
#548 (`-File`). Exit code 2 is not a viable model-facing mechanism via hooks in
this context.

**`decision:block`+`reason`:** Untested. Lower priority since
`additionalContext` covers the non-blocking context injection use case.

Challenge: reconsider (.55 confidence in original). Accepted C1 (exit code 2
confounded by -Command vs -File), C2 (apply_patch gap), C3 partially (N=1,
lowered from .90 to .80), C4 (feasibility doc update). Rebutted C5
(decision:block is lower priority).

## 5. Follow-up Tasks

Created at `ideation`:

- **#546** — Add `apply_patch` to #210 lint guard tool_name filter (needed)
- **#547** — Add model-facing lint feedback via `additionalContext` (important, depends on #210)
- **#548** — Verify exit code 2 routing via `-File` invocation (nice-to-have)
