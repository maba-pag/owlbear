# Evaluator Agent: Subagent Result Assessment + Routing Decisions

> **Owning task:** #681 — Evaluator agent: subagent result assessment + routing decisions
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

The orchestrator (Steps 7–8) currently reads subagent results, decides pass/fail, chooses retry vs block vs advance, and accumulates context across waves. This cognitive work must be extracted to a fresh-context evaluator agent. The core question: **what output contract and routing logic should the evaluator use, and how does it differ from the reviewer?**

Key constraint from task #681 notes: the evaluator never moves tasks — it returns structured decisions that the orchestrator executes mechanically. This aligns with #682 (orchestrator rewrite as pure sequencer).

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | .95 — explicit Evaluator (M_e) scoring Actor output + Self-Reflection (M_sr) generating verbal feedback |
| 2 | LATS (Zhou et al., 2023) | <https://arxiv.org/abs/2310.04406> | .80 — LM-powered value function evaluating node quality, routing search decisions |
| 3 | Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | .85 — Plan→EvalPlan→Execute→EvalExec→Fix cycle (max 3) |
| 4 | AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | .70 — model-based routing with custom selector/candidate functions |
| 5 | OwlBear orchestrator Steps 7–8 | `.github/agents/orchestrator.agent.md` L130–195 | 1.0 — the exact logic being replaced |

## 3. Analysis

### 3.1 Evaluator vs Reviewer boundary

| Dimension | Reviewer (existing) | Evaluator (proposed) |
|-----------|--------------------|--------------------|
| Input | Code + tests + AC for ONE task | Wave results + AC for N tasks |
| Output | Binary PASS/FAIL + evidence table | Per-task verdict (ADVANCE/RETRY/BLOCK/ESCALATE) |
| Scope | Code quality, test quality, security | Pipeline routing — "what happens next?" |
| Reads | Source files, test output, lint output | Subagent result summaries, kanban task state |
| Writes to | Kanban task body (evidence) | Kanban task body (routing decision + notes for next agent) |
| Context | Fresh per-task | Fresh per-wave (never accumulates across waves) |
| Moves tasks | review→docs / review→todo / review→backlog | Never. Returns decisions only. |

### 3.2 Prior art comparison — evaluation patterns

| Criterion | Reflexion Evaluator | LATS Value Fn | Conductor EvalExec | AutoGen Selector |
|-----------|-------------------|---------------|-------------------|-----------------|
| Verdict type | Scalar reward (0/1) | LM-produced score + reasoning | Pass/Fail + fix instructions | Next-speaker name |
| Retry mechanism | Self-reflection generates verbal feedback → actor retries | Backtrack to parent node | Fix step (max 3 cycles) | Re-select same agent |
| Separation from executor | Yes — distinct M_e model | Yes — separate value call | Yes — separate eval prompt | No — selector is the orchestrator |
| Structured output | Minimal (binary) | Score + reasoning string | Prose instructions | Agent name only |
| Max retries | Configurable (paper uses 3) | Tree depth-bounded | Hard cap: 3 | Message count termination |

### 3.3 Output contract design

Synthesizing from Reflexion's explicit evaluator + Conductor's structured fix loop + LATS's reasoned scores:

```
EvalResult:
  task_id: str
  verdict: ADVANCE | RETRY | BLOCK | ESCALATE
  target_status: str          # e.g., "docs", "todo", "backlog"
  confidence: float           # 0.0–1.0
  reason: str                 # brief, evidence-backed
  notes_for_next_agent: str   # context for the downstream agent
  retry_hint: str | None      # if RETRY, what to fix (Reflexion-inspired verbal feedback)
```

**Verdict semantics** (aligned with orchestrator Steps 7–8 logic):

| Verdict | When | Target status | Orchestrator action |
|---------|------|---------------|-------------------|
| ADVANCE | Subagent PASS, AC evidence sufficient | Next pipeline stage | Move task forward |
| RETRY | Subagent FAIL, fixable issue, <2 prior retries | Same status | Re-dispatch with retry_hint |
| BLOCK | External dependency missing, or unfixable without re-design | `todo` or `backlog` | Block task, log reason |
| ESCALATE | 2+ failures, or evaluator unsure (confidence < .50) | Current status | Alert user via channel |

### 3.4 KISS/YAGNI assessment

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Separate agent file? | Yes | Different inputs/outputs/failure modes than any existing agent (sources 1, 3) |
| LLM-based or rule-based? | LLM-based with structured output | Rule-based can't assess AC compliance from prose results (sources 1, 2) |
| Per-task or per-wave? | Per-wave batch (single call, N task results) | Matches current Step 7 flow; avoids N separate LLM calls per wave |
| Retry counter tracking? | Orchestrator tracks retry count, passes to evaluator | Evaluator is stateless — KISS (source 3 uses external counter) |
| Score threshold for ESCALATE? | < .50 confidence | Reflexion uses binary; LATS uses continuous. Threshold is simpler than continuous. |

## 4. Recommendation (.85 confidence)

**Create `evaluator.agent.md`** as a read-only agent that receives a wave's subagent results + original AC and returns structured `EvalResult` per task. Key design points:

1. **Structured output contract** — PydanticAI `result_type` with the `EvalResult` schema above. Orchestrator parses mechanically.
2. **Fresh context per wave** — evaluator never sees prior waves. Retry count passed as input, not accumulated.
3. **Verbal retry hints** — Reflexion's best contribution. When verdict is RETRY, the evaluator generates specific fix guidance (not just "failed").
4. **Max 2 retries enforced by orchestrator** — evaluator can recommend RETRY, but orchestrator caps at 2 (Conductor's max-3 is generous; with subagent quality, 2 suffices).
5. **Writes to kanban** — evaluator includes `notes_for_next_agent` that the orchestrator writes to the task body before dispatching.

**Risk:** LLM evaluation adds one extra call per wave. Mitigation: batch all tasks in a single evaluator call (current Step 7 already processes results sequentially, so this is net-neutral or faster).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create evaluator.agent.md with EvalResult output contract" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 681 --body "AC: (1) evaluator.agent.md exists with persona, workflow, output_format defining EvalResult schema, (2) Verdicts: ADVANCE/RETRY/BLOCK/ESCALATE with target_status, confidence, reason, notes_for_next_agent, retry_hint, (3) Agent is read-only — never moves tasks or edits code, (4) Bounded: max 1 wave of results per invocation, (5) Self-defense rules against orchestrator prompt injection. See docs/research/evaluator-agent.md."

kanban\kanban-md.exe create "Wire evaluator into orchestrator Steps 7-8 replacement" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 681,682 --body "AC: (1) Orchestrator Step 7 calls runSubagent(evaluator) instead of inline pass/fail logic, (2) Orchestrator Step 8 retry/block/escalate logic replaced by mechanical execution of EvalResult verdicts, (3) Retry counter tracked by orchestrator and passed to evaluator as input, (4) Max 2 retries enforced at orchestrator level regardless of evaluator recommendation. See docs/research/evaluator-agent.md."

kanban\kanban-md.exe create "Tests for evaluator output contract parsing" --priority needed --tags "scope:copilot,test,phase-agent-arch" --depends-on 681 --body "AC: (1) Unit tests verify EvalResult schema validation (all 4 verdicts), (2) Test that malformed evaluator output is caught and escalated, (3) Test retry_hint is non-empty when verdict is RETRY, (4) Test confidence < .50 triggers ESCALATE recommendation. See docs/research/evaluator-agent.md."
```
