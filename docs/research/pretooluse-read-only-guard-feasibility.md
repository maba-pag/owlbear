# PreToolUse Read-Only Guard Feasibility Analysis

> **Owning task:** #211 — Add preToolUse read-only guard hook to reviewer agent
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #211 proposes adding a PreToolUse hook to `reviewer.agent.md` that denies
write-tool execution via `permissionDecision: "deny"`. The hook was scoped as
"Phase 2" depending on #209 (Stop hooks). #209 was invalidated (.90 confidence)
because Stop hook `systemMessage` doesn't reach pipeline agents at session end.
The viability research explicitly unblocked #211 since PreToolUse fires mid-session
and uses a structurally different mechanism (`permissionDecision` vs `systemMessage`).

**Question:** Is PreToolUse `permissionDecision: "deny"` reliable for the reviewer
subagent? Is the effort justified given the existing `tools:` restriction?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (4/1/2026) | https://code.visualstudio.com/docs/copilot/customization/hooks | .95 — PreToolUse I/O, permissionDecision schema |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — agent-scoped hooks, subagent behavior |
| OwlBear #86 parent research | `docs/research/agent-scoped-hooks-pipeline-enforcement.md` §4 C5 | 1.0 — original assessment at .65 |
| OwlBear viability research | `docs/research/stop-hook-multi-agent-viability.md` | 1.0 — #209 invalidation; explicit #211 unblock |
| OwlBear AC correction (#213) | `docs/research/hook-ac-command-execution-model.md` | 1.0 — corrected AC model |
| OwlBear #210 research | `docs/research/posttooluse-lint-guard-feasibility.md` | .90 — subagent routing concerns |
| nWave DES research | `docs/research/nwave.md` §3.3 | .75 — PreToolUse enforcement pattern precedent |

## 3. Analysis

### 3.1 PreToolUse Deny vs Stop Hook SystemMessage

| Concern | Stop hook (#209) | PreToolUse deny (#211) |
|---------|------------------|-----------------------|
| Fires when | Session end (agent terminated) | Before each tool call (agent active) |
| Mechanism | `systemMessage` (data plane) | `permissionDecision` (control plane) |
| Deadlock risk | Yes — parallel subagents | No — per-tool, no cross-agent state |
| Platform enforcement | No — message only | Yes — blocks tool execution |
| Subagent verified? | No — message goes to orchestrator chat | No — plausible but unverified |

The docs state `permissionDecision: "deny"` "blocks tool execution" and priority
rules apply: "deny > ask > allow." This is a platform-level gate, not a message the
agent must receive. However, no empirical verification exists for subagent context.

### 3.2 Defense-in-Depth Value Assessment

| Layer | Mechanism | Write tools blocked | Terminal writes? |
|-------|-----------|--------------------|-----------------|
| Primary | `tools:` restriction | All (not granted) | N/A — terminal granted for test/lint |
| Secondary | PreToolUse hook | 3 declarative tools | No — cannot intercept shell commands |

**Terminal bypass (challenger finding C1):** The reviewer's `tools:` list includes
`execute/runInTerminal` for running pytest and ruff. This is a wider write vector
than the 3 file-edit tools the hook guards. The hook cannot intercept terminal
writes. Removing terminal would cripple the reviewer's core function (test execution).

The hook defends against the most common accidental write path — declarative
file-edit tools that an LLM would use if it ignores its read-only instructions.
Terminal writes require deliberate command construction, making accidental bypass
less likely but not impossible.

### 3.3 Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `permissionDecision` unverified for subagents | Moderate | Sequence after #210 empirical spike |
| Terminal bypass not covered | Moderate | Document as known limitation; reviewer instructions are primary guard |
| Tool-name list incomplete/stale | Low | Add static validation test; review on VS Code updates |
| Preview API may change | Low | Script is ~20 LOC; trivial to update |
| `multi_replace_string_in_file` name unverified in stdin | Low | Verify during implementation |

## 4. Recommendation (.65 confidence)

**Proceed with implementation**, but with two sequencing adjustments:

1. **Soft-depend on #210's empirical routing spike.** The #210 research created a
   task to verify hook output routing in subagent context. PreToolUse shares the
   same hook infrastructure. Results from that spike inform whether
   `permissionDecision` works as expected for pipeline agents.
2. **Add a complementary static test** that validates the reviewer's `tools:` list
   excludes write tools. This catches misconfiguration at commit time with zero
   runtime overhead and no preview API dependency.

The hook is low-effort (~20 LOC script + 3-line YAML), low-risk, and provides a
meaningful secondary guard against the most common accidental write path. The terminal
bypass is a known limitation documented here, not a blocker.

Challenge: reconsider — confidence in original: .55. Challenger identified terminal
bypass (C1), unverified subagent routing (C2), and unjustified confidence inflation
(C3). Revised confidence from .80 to .65; adopted sequencing recommendation (A3);
incorporated static test alternative (A1) as complementary task.

## 5. Follow-up Tasks

No new tasks created — #211 already exists with corrected AC. Research validates
the existing AC is sound. Two complementary tasks created at `ideation`:

```
kanban\kanban-md.exe create "Add static test: reviewer tools list excludes write tools" --priority important --status ideation --tags "scope:agents,test,type:test" --body "## Context\nSee docs/research/pretooluse-read-only-guard-feasibility.md §3.2 and §4.\nChallenger alternative A1: static validation catches tools-list misconfiguration at commit time.\n\n## Acceptance Criteria\n- [ ] Add test in tests/ that parses reviewer.agent.md YAML frontmatter\n- [ ] Assert tools list does not contain create_file, replace_string_in_file, multi_replace_string_in_file, or create_directory\n- [ ] Test runs in existing test suite (uv run pytest)"
```

Note: #211 should be soft-sequenced after the PostToolUse empirical routing spike
(created by #210 research) to avoid repeating #209's multi-cycle invalidation.
