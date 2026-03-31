# Fresh-Context Retry for Builder Agent

> **Owning task:** #266 — Add fresh-context retry to builder agent
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The builder agent is the most failure-prone pipeline agent due to its edit operations. After 2 failed attempts in the same context, error output and dead-end reasoning pollute the conversation, degrading retry quality. The question: **what should the Fix-Attempt subagent look like, what context does it need, and how does it integrate with the builder's TDD workflow?**

Prerequisite: Decision request `docs/decisions/pending/228-fresh-context-retry.md` recommends threshold=2 (Option A). This research assumes that threshold is approved and focuses on implementation design.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — coordinator/worker pattern, context isolation, nesting depth 5 |
| S2 | Reflexion (Shinn et al., 2023) | https://arxiv.org/abs/2303.11366 | .90 — verbal reinforcement: evaluator generates verbal feedback for retry |
| S3 | SupaConductor Evaluate-Loop | https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers | .80 — Execute→Evaluate→Fix cycle (max 3), separate evaluator agent |
| S4 | OwlBear subagent-nesting-architecture.md | docs/research/subagent-nesting-architecture.md | .95 — threshold=2 recommendation, assign mode, tool requirements |
| S5 | OwlBear evaluator-agent.md | docs/research/evaluator-agent.md | .85 — retry_hint pattern, RETRY verdict with verbal feedback |
| S6 | OwlBear builder.agent.md | agents/builder.agent.md | 1.0 — current builder tools, workflow, retry rules |

## 3. Analysis

### 3a. Context isolation benefit (S1, S2, S3)

| Aspect | Same-context retry | Fresh-context subagent |
|--------|-------------------|----------------------|
| Context pollution | High — error output, failed diffs, dead-end reasoning accumulate | None — clean slate |
| Approach diversity | Low — anchored by prior attempts (S2: "anchoring bias") | High — fresh perspective unconstrained by prior failures |
| Startup cost | None — immediate | Medium — subagent initialization (~2-5s) |
| Prior art | Standard retry loop | Reflexion self-reflection (S2), Conductor Fix step (S3), VS Code coordinator/worker (S1) |

VS Code docs confirm: "each worker agent has a clean context and appropriate permissions for its specific job" (S1). Conductor uses a separate Fix step after evaluation failure — max 3 fix cycles (S3). Reflexion generates "verbal reflections" (natural language feedback about what went wrong) — this maps to our `retry_hint` pattern.

### 3b. Fix-Attempt subagent design

| Design dimension | Recommendation | Confidence | Rationale |
|-----------------|---------------|------------|-----------|
| Tool mode | Assign | .85 | Same as builder minus kanban ops — prevents scope creep (S4) |
| Nesting level | L2 (orchestrator→builder→fix-attempt) | .90 | Within VS Code max depth 5 (S1) |
| Context input | Structured: test errors + source files + retry_hint | .85 | Reflexion shows verbal feedback improves repair quality (S2) |
| Output contract | Structured text: FIXED/FAILED + files changed + evidence | .80 | Aligns with Channel A signal convention |
| Max internal retries | 1 | .80 | fix-attempt gets one shot — it IS the fresh perspective |

### 3c. Tool requirements

The fix-attempt subagent needs builder-equivalent tools minus kanban management:

| Tool | Purpose | Required |
|------|---------|----------|
| `execute/runInTerminal` | Run pytest, ruff | Yes |
| `execute/getTerminalOutput` | Read test results | Yes |
| `execute/awaitTerminal` | Wait for test completion | Yes |
| `execute/killTerminal` | Clean up terminals | Yes |
| `read/readFile` | Read source and test files | Yes |
| `edit/editFiles` | Apply fixes | Yes |
| `edit/createFile` | Create new files if needed | Yes |
| `search` | Find related code | Yes |
| `vscode/memory` | Access repo conventions | Yes |
| `owlbear-kanban/*` | Board operations | No — builder handles all kanban |

### 3d. Input contract

The builder constructs a dispatch prompt with:

```
Fix-Attempt: #{task_id}
Test file: {test_file_path}
Source files: {comma-separated source paths}
Retry hint: {what went wrong and what to try differently}
Error summary: {condensed test output — failures only, max 500 tokens}
```

The retry_hint follows Reflexion's verbal feedback pattern (S2) — not just "tests failed" but "TypeError on line 45: `append()` received dict instead of ModelMessage. Try adding TypeAdapter validation." This targeted feedback is the key differentiator.

### 3e. Integration with builder workflow

Current flow (tdd-workflow skill):
```
Step 3: Read tests → Step 4: Implement (GREEN) → Step 7: Verify
```

Proposed flow with fresh-context retry:
```
Step 3: Read tests → Step 4: Implement → Step 7: Verify
  ↓ (if verify fails, retry count < 2)
  Same-context retry: diagnose → fix → verify again
  ↓ (if 2nd verify fails)
  Construct retry_hint from error output
  Delegate to fix-attempt subagent
  ↓ (subagent returns FIXED/FAILED)
  FIXED: run final verify, continue to Step 8
  FAILED: BLOCK task, report to orchestrator
```

### 3f. Escalation path

| fix-attempt result | Builder action |
|-------------------|---------------|
| FIXED + tests pass | Continue to Step 8 (commit + advance) |
| FIXED + tests still fail | BLOCK task — both builder and fix-attempt failed |
| FAILED | BLOCK task — report diagnosis to orchestrator via Channel B |

## 4. Recommendation (.80 confidence)

Create a `fix-attempt.agent.md` with assign-mode tools, and update the builder's tdd-workflow skill to delegate after 2 failures. Key design:

1. **Assign mode** — 9 tools (builder tools minus kanban). Prevents fix-attempt from touching the board.
2. **Structured input** — test file + source files + retry_hint + error summary. No conversation history from the builder.
3. **One-shot** — fix-attempt gets a single attempt. If it also fails, builder blocks the task.
4. **Verbal retry_hint** — Reflexion-inspired, specific guidance about what failed and what to try (not generic "tests failed").

**Risk:** Builder must correctly construct the retry_hint. Mitigation: builder includes raw error output alongside the hint — fix-attempt can diagnose independently if the hint is unhelpful.

**Dependency:** Decision request `228-fresh-context-retry.md` must be approved (Option A) before implementation proceeds.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create fix-attempt.agent.md with assign-mode tools" --priority needed --status ideation --tags "scope:agents,phase-2" --body "AC:\n1. fix-attempt.agent.md with persona, tools (assign: 9 tools - builder tools minus kanban), workflow\n2. user-invocable: false, disable-model-invocation: true\n3. Output contract: FIXED/FAILED + files_changed + evidence\n4. Input contract: task_id, test_file, source_files, retry_hint, error_summary\n5. Max 1 internal retry\n6. Never touches kanban board\nSee docs/research/fresh-context-retry-builder.md"

kanban\kanban-md.exe create "Add fix-attempt delegation to builder tdd-workflow" --priority needed --status ideation --tags "scope:agents,phase-2" --depends-on 266 --body "AC:\n1. tdd-workflow skill updated: after 2nd verify failure, construct retry_hint and delegate to fix-attempt subagent\n2. Builder agents array updated to include fix-attempt\n3. Retry_hint includes specific error info (Reflexion-style verbal feedback)\n4. Builder handles fix-attempt result: FIXED continues to commit, FAILED blocks task\n5. Builder still caps at 2 retries total (same-context + fresh-context = 2 total attempts after initial)\nSee docs/research/fresh-context-retry-builder.md"

kanban\kanban-md.exe create "Tests for fix-attempt delegation flow" --priority needed --status ideation --tags "scope:agents,test,phase-2" --depends-on 266 --body "AC:\n1. Unit tests verify retry_hint construction from error output\n2. Test fix-attempt input contract validation\n3. Test builder delegates after exactly 2 failures (not 1, not 3)\n4. Test FIXED result triggers final verify + continue\n5. Test FAILED result triggers BLOCK\n6. Test fix-attempt never receives kanban tools\nSee docs/research/fresh-context-retry-builder.md"
```
