# Loop Detection Instruction Patterns for OwlBear Agents

> **Owning task:** #432 — Implement loop-detection pattern in agent instructions
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

OwlBear agents sometimes retry failed tool calls or commands indefinitely. The existing "max 2 retries" red flag in agent-common.instructions.md is the only guard. Task #432 asks: how should OwlBear adopt deer-flow's loop detection pattern given that OwlBear uses instruction-driven agents (no programmatic middleware)?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| deer-flow LoopDetectionMiddleware | github.com/bytedance/deer-flow → `backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py` | .95 — primary pattern: hash tool calls, warn at 3, force-stop at 5, sliding window |
| Microsoft AutoGen termination conditions | microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html | .85 — MaxMessageTermination, composable conditions, custom FunctionCallTermination |
| OwlBear agent-common.instructions.md | `instructions/agent-common.instructions.md` §Red flags, §Terminal discipline | 1.0 — existing "max 2 retries" rule, "no brute-force retries" |
| OwlBear stop-hook research (#209) | `docs/research/stop-hook-multi-agent-viability.md` | .90 — SubagentStop deadlock rules out stop-hook for pipeline agents |

## 3. Analysis

### Approach Comparison

| Criterion | Instruction rules | Stop hook | Programmatic middleware |
|-----------|------------------|-----------|----------------------|
| Applicability | All agents | User-invocable only | Not available (no runtime) |
| Implementation cost | ~0 LOC (markdown) | Python + config | Not feasible |
| Enforcement | Soft (LLM compliance) | Hard (blocks session) | Hard (strips tool calls) |
| Pipeline agents | Yes | No (SubagentStop issue) | N/A |
| Maintenance | Edit one file | Script + hooks config | N/A |
| KISS alignment | High | Medium | Low |

### deer-flow Pattern Details

deer-flow's `LoopDetectionMiddleware` (Apache-2.0):
- **Hash**: Normalize tool calls to `{name, args}`, sort, MD5 → 12-char hash
- **Track**: Sliding window of last 20 hashes per thread (LRU eviction at 100 threads)
- **Warn**: At 3 identical hash occurrences → inject HumanMessage: "you are repeating yourself"
- **Stop**: At 5 identical → strip `tool_calls` from AIMessage, force text output

### AutoGen Pattern Details

AutoGen's termination system (MIT):
- **MaxMessageTermination**: Hard message count limit
- **Composable**: `condition_A | condition_B` (OR), `condition_A & condition_B` (AND)
- **Stateful + resettable**: conditions track state, auto-reset between runs

### OwlBear Adaptation

OwlBear cannot use programmatic middleware (no runtime process). Stop hooks only work for user-invocable agents (per #209 research). **Instruction rules** are the only viable mechanism.

The existing rules are scattered and lack escalation structure:
- "max 2 retries" in red flags (line 204)
- "No brute-force retries. Maximum 2 attempts" in terminal discipline (line 249)
- No guidance on *what to do* after hitting the limit
- No distinction between retry categories (same command vs. same logical goal)

### Proposed Instruction Pattern: 3-Tier Escalation

Adapted from deer-flow's warn/stop thresholds to instruction-friendly language:

| Tier | Trigger | Action |
|------|---------|--------|
| 1 — Detect | Same tool call or command attempted twice | Read the error. Diagnose root cause. Change approach. |
| 2 — Adapt | Same *logical operation* failed with 2 different approaches | Reassess whether the operation is necessary. Consider skipping or deferring. |
| 3 — Stop | 3+ failed attempts at the same goal | Stop. Write what you tried in the task body. Move to handoff/blocked. |

This maps deer-flow's 3-warn/5-stop to OwlBear's tighter 2/3 limits — appropriate since instruction-based compliance is softer than programmatic enforcement.

### Category-Specific Limits

| Category | Max attempts | Examples |
|----------|-------------|----------|
| Exact same command | 1 retry | Same pytest flags, same grep query |
| Same logical operation, varied approach | 2 retries | Different flags, different search terms |
| Same goal, different operations | 3 total | Try grep, then semantic search, then read file |

## 4. Recommendation (.85 confidence)

**Instruction rules only** — no stop hook, no programmatic middleware.

Consolidate the scattered retry guidance into a single "Loop detection and retry discipline" section in agent-common.instructions.md with:
1. The 3-tier escalation model (detect → adapt → stop)
2. Category-specific retry limits table
3. Explicit "vary your approach" requirement after first failure
4. Mandatory handoff/block after tier 3

**Risk:** Instruction compliance is soft — LLMs can ignore rules under pressure. Mitigation: the reviewer and auditor agents check for loop patterns in Channel B notes, and the red flags section cross-references the new section.

**Why not stop hooks:** Per #209 research, stop hooks fire as SubagentStop for pipeline agents. The systemMessage never reaches the agent. Only `decision: "block"` works, but that terminates the session rather than injecting a retry warning.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Consolidate loop detection rules in agent-common.instructions.md" --priority needed --status ideation --tags "scope:agents,phase-2" --body "## Context\nConsolidate scattered retry guidance (red flags line 204, terminal discipline line 249) into a single 'Loop detection and retry discipline' section. Add 3-tier escalation model and category-specific retry limits per docs/research/loop-detection-instruction-patterns.md.\n\nSee docs/research/loop-detection-instruction-patterns.md for full analysis.\n\n## Acceptance Criteria\n- [ ] New section 'Loop detection and retry discipline' in agent-common.instructions.md\n- [ ] 3-tier escalation table (detect/adapt/stop) with concrete action per tier\n- [ ] Category-specific retry limits table (exact same command: 1 retry, same logical op: 2, same goal: 3 total)\n- [ ] Existing red flag 'max 2 retries' cross-references the new section\n- [ ] Terminal discipline 'No brute-force retries' cross-references the new section\n- [ ] Mandatory handoff/block after tier 3 with task body update requirement"
```

```
kanban\kanban-md.exe create "Add loop-pattern detection to reviewer checklist" --priority important --status ideation --tags "scope:agents,phase-2" --body "## Context\nThe reviewer agent should check for loop patterns when reviewing builder work. If Channel B notes show repeated identical attempts without approach variation, flag as a quality concern.\n\nSee docs/research/loop-detection-instruction-patterns.md §3 for analysis.\n\n## Acceptance Criteria\n- [ ] Reviewer code-review skill includes a check for repeated identical tool calls in builder notes\n- [ ] Reviewer flags builders that hit tier 3 without handoff as a quality gap"
```
