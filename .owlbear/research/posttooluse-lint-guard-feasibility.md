# PostToolUse Lint Guard Feasibility Analysis

> **Owning task:** #210 — Add PostToolUse lint guard hook to builder agent (Phase 2)
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #210 proposes adding a PostToolUse hook to `builder.agent.md` that auto-runs
ruff after file edits. The hook was originally scoped as "Phase 2" depending on #209
(Phase 1 Stop hooks). However, #209 was invalidated (.90 confidence) because Stop
hook `systemMessage` doesn't reach pipeline agents at session termination. The
viability research explicitly recommended unblocking #210 since PostToolUse hooks
fire mid-session and don't share the Stop hook's deadlock or routing problems.

**Question:** Is the PostToolUse lint guard still feasible after #209's invalidation?
Does PostToolUse output reliably reach the builder agent in subagent context?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (4/1/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — canonical spec; PostToolUse I/O schema |
| OwlBear #86 parent research | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` §4 C1 | 1.0 — original feasibility at .75 |
| OwlBear viability research | `docs/research/stop-hook-multi-agent-viability.md` | 1.0 — #209 invalidation; explicit #210 unblock |
| OwlBear AC correction (#213) | `docs/research/hook-ac-command-execution-model.md` | 1.0 — corrected AC from prompt-injection model |
| OwlBear #374 arch review | kanban task body | .80 — confirms no hooks: section exists; flags AC line 6 |

## 3. Analysis

### 3.1 PostToolUse vs Stop Hook — Why #209's Failure Doesn't Apply

| Concern | Stop hook (#209) | PostToolUse (#210) |
|---------|------------------|--------------------|
| When it fires | Session end (agent terminated) | After each tool call (agent active) |
| Deadlock risk | Yes — parallel subagents block each other | No — per-tool, no cross-agent interaction |
| `systemMessage` reaches agent? | No — post-mortem, shown in orchestrator chat | Uncertain — fires mid-session but routing unverified |
| Exit code 2 reaches model? | Not applicable (Stop uses decision:block) | Yes — docs: "show error to model" |
| `additionalContext` | Not documented for Stop | Documented: "Extra context injected into the conversation" |

### 3.2 PostToolUse Output Mechanisms

| Mechanism | Documented behavior | Subagent routing verified? |
|-----------|--------------------|-----------------------------|
| Exit code 2 | "Stop processing and show error to model" | **Reliable** — docs unambiguous |
| `hookSpecificOutput.additionalContext` | "Extra context injected into the conversation" | **Unverified** for subagents |
| `systemMessage` | "Warning message displayed to the user" | **Unreliable** — user-facing, not model-facing |
| `decision: "block"` + `reason` | "Block further processing; reason shown to the model" | **Likely reliable** — reason explicitly model-facing |

### 3.3 Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Ruff on syntactically incomplete files (mid-edit) | Moderate | Block only on ruff errors, not syntax warnings; or use ruff exit code to distinguish |
| Shell spawn overhead for non-edit tools (~200-500ms/call on Windows) | Low | Script exits early on non-edit `tool_name`; overhead is per-spawn, not per-lint |
| Context window inflation from ruff output per edit | Low-Moderate | Truncate ruff output in script; limit to first N errors |
| `multi_replace_string_in_file` tool name unverified | Low | Verify tool name in PostToolUse stdin during implementation |
| Subagent output routing unverified | Moderate | Empirical spike recommended as first implementation step |

### 3.4 AC Assessment

| AC line | Status | Notes |
|---------|--------|-------|
| 1: PostToolUse hook in frontmatter | Valid | No hooks: section exists; clean addition |
| 2: Script reads tool_name, filters edits | Valid | Documented in VS Code PostToolUse input |
| 3: systemMessage with ruff output or exit 2 | **Needs revision** | Prefer exit code 2 (model-facing) over systemMessage (user-facing) |
| 4: Empty JSON on non-edit/clean | Valid | Standard no-op pattern |
| 5: chat.useCustomAgentHooks enabled | Valid | Already at .vscode/settings.json line 70 |
| 6: No conflict with Stop hook from Phase 1 | **Stale** | Phase 1 never shipped; no hooks: section exists |
| 7: Valid YAML frontmatter | Valid | Standard verification |

## 4. Recommendation (.75 confidence)

**Proceed with implementation** using exit code 2 as the primary lint-error mechanism.
This is the only output path the docs unambiguously confirm reaches the model in all
contexts. Avoid relying on `systemMessage` for lint results — it's user-facing and
routing to subagent models is unverified.

Recommended AC corrections:
- Line 3: Replace `systemMessage` with exit code 2 as primary, `additionalContext` as
  secondary (soft warnings)
- Line 6: Remove Phase 1 Stop hook reference — no hooks: section exists

The builder should verify PostToolUse subagent output routing empirically as the first
implementation step (minimal spike: fixed-string hook, one task, observe output) before
writing the full lint script. This prevents repeating #209's multi-cycle invalidation.

Challenge: reconsider — confidence in original: .55. Challenger identified unverified
subagent routing (C2), partial-file risk (C4), and unsupported confidence boost (C5).
Revised confidence from .85 to .75; adopted exit-code-2-primary approach (A2);
incorporated empirical verification recommendation (A1).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Verify PostToolUse hook output routing in subagent context" --priority needed --status ideation --tags "scope:agents,hooks,research,type:test" --body "## Context\nSee docs/research/posttooluse-lint-guard-feasibility.md section 3.2.\nThe #209 cycle proved that hook output routing assumptions must be verified empirically before building. PostToolUse additionalContext and systemMessage routing to subagent models is undocumented.\n\n## Acceptance Criteria\n- [ ] Add a minimal PostToolUse hook to builder.agent.md returning a fixed additionalContext string and a fixed systemMessage string\n- [ ] Run the builder agent on a throw-away task that edits a file\n- [ ] Document which output (additionalContext, systemMessage, neither, both) appears in the builder model context\n- [ ] Document which output (if any) appears in the orchestrator chat panel\n- [ ] Remove the test hook after verification\n- [ ] Update docs/research/posttooluse-lint-guard-feasibility.md with empirical findings"
```

## 6. Empirical Update (2026-04-02, task #532)

Task #532 completed empirical verification. Key corrections to this document:

- **Section 3.2 `additionalContext`:** Status changed from "Unverified" to
  **CONFIRMED model-facing** in subagent context. Chat Debug View shows content
  wrapped in `<PostToolUse-context>` XML tags.
- **Section 3.2 Exit code 2:** Status changed from "Reliable" to **NOT
  model-facing via `-Command` one-liners** on PS 5.1. Hooks engine classified
  as NonBlockingError. Behavior via `-File` invocation is untested (see #548).
- **Section 4 recommendation:** Exit-code-2-primary approach is **invalidated
  for `-Command` mode**. Use `additionalContext` as primary model-facing channel.
  The `-File` mode used by #210 may still propagate exit code 2 correctly.
- **New finding:** Builder uses `tool_name: "apply_patch"` for file edits.
  #210's tool_name filter must include `apply_patch` (see #546).

Full empirical results: `docs/research/posttooluse-subagent-output-routing.md`
