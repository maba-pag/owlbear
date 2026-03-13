# Orchestrator Rewrite: Pure Sequencer, Zero Cognitive Work

> **Owning task:** #682 — Orchestrator rewrite: pure sequencer, zero cognitive work
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

The orchestrator (361 lines, 10 workflow steps) currently performs all cognitive work in-context: reading the board, building DAGs, running gate checks, planning waves, interpreting subagent results, deciding retry/block/escalate. This causes context overflow and degradation over long sessions (#663 class). With planner (#680) and evaluator (#681) agents designed, the orchestrator can be stripped to a pure sequencer: plan → dispatch → evaluate → execute → loop.

**Core question:** Can the orchestrator be reduced to a mechanical loop that never reads the board, never interprets results, and never accumulates context — while remaining a VS Code Copilot `.agent.md` file (i.e., still an LLM agent, not code)?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | LangGraph Plan-and-Execute | <https://blog.langchain.com/planning-agents/> | .90 — canonical planner→executor→re-planner loop |
| 2 | Plan-and-Solve Prompting (Wang et al., 2023) | <https://arxiv.org/abs/2305.04091> | .80 — theoretical basis: divide task into subtasks, execute per plan |
| 3 | LLMCompiler (Kim et al., 2023) | <https://arxiv.org/abs/2312.04511> | .85 — Planner→Task Fetching Unit→Joiner; dispatcher is pure code |
| 4 | CrewAI Flows | <https://docs.crewai.com/concepts/flows> | .80 — event-driven `@start→@listen` pipeline; Flow class is a state machine, not an LLM |
| 5 | AutoGen SelectorGroupChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html> | .75 — PlanningAgent produces `agent: task` assignments; team infra dispatches mechanically |
| 6 | Conductor orchestrator | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | .85 — DAG→topological levels→dispatch→EvalExec→Fix cycle |
| 7 | Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | .80 — explicit Evaluator (M_e) separate from Actor; verbal feedback for retries |
| 8 | OwlBear planner research | `docs/planner-agent-research.md` | .95 — WAVE_PLAN output contract, tool set, scope filter design |
| 9 | OwlBear evaluator research | `docs/evaluator-agent-research.md` | .95 — EvalResult output contract, verdict routing, retry hints |

## 3. Analysis

### 3.1 Is a pure sequencer feasible in VS Code Copilot?

**Critical distinction:** In LangGraph/CrewAI/LLMCompiler, the orchestrator loop is *code* (Python state machine). In VS Code Copilot, the orchestrator is an *LLM agent* defined by `.agent.md`. It cannot be literal code — it must be a prompt that makes the LLM behave mechanically.

| Framework | Orchestrator is... | Loop is... | Subagent output format |
|-----------|-------------------|------------|----------------------|
| LangGraph Plan-and-Execute | Python StateGraph | Code (edges) | Structured (Pydantic) |
| LLMCompiler | Python Task Fetching Unit | Code (topological dispatch) | Variable-substituted text |
| CrewAI Flows | Python Flow class | Code (`@listen` decorators) | Pydantic BaseModel state |
| AutoGen SelectorGroupChat | Model-based selector | Code (while loop) | Chat messages |
| Conductor | Claude Code prompt | Prompt (max 3 fix cycles) | File-based JSONL |
| **OwlBear (proposed)** | **VS Code Copilot `.agent.md`** | **Prompt (tight loop instructions)** | **Structured text (WAVE_PLAN, EvalResult)** |

OwlBear's orchestrator is closest to Conductor's model: an LLM-driven loop with explicit step instructions. The difference from Conductor (and the improvement) is that OwlBear offloads planning and evaluation to separate subagents with fresh contexts, where Conductor does both inline.

**Verdict (.90 confidence):** Feasible. The LLM can follow a mechanical loop if the instructions are tight and there are no judgment calls to make. The key enabler is structured output contracts from planner and evaluator — the orchestrator never needs to *interpret*, only *parse and execute*.

### 3.2 What cognitive functions remain?

| Current orchestrator function | Moves to... | Remains? |
|-------------------------------|-------------|----------|
| Read board (`kanban-md list/show`) | Planner | **NO** |
| Build dependency DAG | Planner | **NO** |
| Run 5 gate checks | Planner (SKIPPED section) | **NO** |
| Plan execution waves | Planner (WAVE_PLAN) | **NO** |
| Interpret subagent pass/fail | Evaluator (EvalResult.verdict) | **NO** |
| Decide retry vs block vs escalate | Evaluator (EvalResult.verdict) | **NO** |
| Generate retry guidance | Evaluator (EvalResult.retry_hint) | **NO** |
| **Parse WAVE_PLAN text** | — | **YES** (mechanical) |
| **Parse EvalResult text** | — | **YES** (mechanical) |
| **Dispatch subagents (tool calls)** | — | **YES** (mechanical) |
| **Move tasks (kanban-md move)** | — | **YES** (mechanical) |
| **Track retry count** | — | **YES** (simple counter) |
| **Manage progress (todo list)** | — | **YES** (UI concern) |
| **Loop termination** | — | **YES** (no more waves = stop) |

All remaining functions are mechanical: parsing structured text, invoking tools, incrementing counters, calling subagents.

### 3.3 Context accumulation analysis

| Dimension | Current | Proposed | Bounded? |
|-----------|---------|----------|----------|
| Board state | Full `kanban-md list` + N × `show` output — grows with board size | Not in context (planner reads it) | **YES** |
| Task bodies / AC | Loaded per task for gate checks | Not in context (planner reads them) | **YES** |
| Subagent results | Accumulated across all waves | Per-wave only; discarded after evaluator processes | **YES** |
| Wave history | All prior wave results stay in context | Only current wave + EvalResult; planner re-reads board for next wave | **YES** |
| Retry context | Error messages accumulated | Retry count (integer) + evaluator's retry_hint (one line) | **YES** |

**Key insight from LangGraph and LLMCompiler (sources 1, 3):** The re-planning step gives the orchestrator a clean slate each iteration. OwlBear's planner serves the same function — each call produces a fresh WAVE_PLAN from current board state, not from accumulated history.

### 3.4 Tool reduction

| Tool category | Current | Proposed | Rationale |
|---------------|---------|----------|-----------|
| `agent` (dispatch) | Keep | Keep | Core function |
| `execute/*` (terminal) | Keep | Keep | Needed for `kanban-md move/edit` |
| `todo` (progress) | Keep | Keep | Progress tracking |
| `vscode/askQuestions` | Keep | Keep | Escalation to user |
| `vscode/memory` | Keep | Keep | Session context |
| `edit/*` (file editing) | Has | **Remove** | Orchestrator never edits code/files |
| `read/readFile` | Has | **Remove** | Planner reads tasks, not orchestrator |
| `search` | Has | **Remove** | No board/code search needed |
| `web` | Has | **Remove** | No web access needed |
| `microsoft/markitdown/*` | Has | **Remove** | No document conversion needed |
| `read/problems` | Has | **Remove** | Reviewer checks problems, not orchestrator |

Removing unused tools reduces prompt size and eliminates vectors for degradation.

### 3.5 New workflow sketch

```
Step 1: PLAN — dispatch planner with scope filter
  runSubagent("planner", "Plan: {scope_filter}")
  → Receives WAVE_PLAN (waves, blocked, skipped)

Step 2: TRACK — create progress checklist from plan
  manage_todo_list: Wave 1: #{ids} / Wave 2: #{ids} / ...

Step 3: DISPATCH — execute current wave (parallel)
  For each task in wave:
    kanban-md move {id} in-progress
    runSubagent({agent_name}, "{id} — {ac_summary}")
  All calls in single parallel tool-call block

Step 4: EVALUATE — dispatch evaluator with wave results
  runSubagent("evaluator", "Evaluate wave: {results_summary}")
  → Receives EvalResult per task

Step 5: EXECUTE — mechanically apply verdicts
  ADVANCE: kanban-md move {id} {target_status}
           If next agent needed → add to next dispatch batch
  RETRY:   If retry_count < 2 → re-dispatch with retry_hint
           Else → BLOCK
  BLOCK:   kanban-md edit {id} --block "{reason}"
  ESCALATE: askQuestions to alert user

Step 6: PIPELINE — advance through reviewer → writer
  For tasks that passed builder:
    Dispatch reviewers (parallel) → evaluate → execute
    Dispatch writers (parallel) → evaluate → execute

Step 7: LOOP
  If more waves in plan → go to Step 3
  If planner should re-assess (board changed) → go to Step 1
  If no more work → Final Report

Step 8: CURATE — fire-and-forget curator if tasks completed
```

### 3.6 Comparison with prior art patterns

| Pattern | Source | OwlBear equivalent |
|---------|--------|--------------------|
| Planner → Executor → Re-planner loop | LangGraph (1) | Planner → Dispatch → Evaluator → Loop to planner |
| DAG → topological dispatch → eval | LLMCompiler (3), Conductor (6) | WAVE_PLAN waves = topological levels |
| Evaluator separate from Actor | Reflexion (7) | Evaluator agent separate from builder |
| Verbal retry hints | Reflexion (7) | EvalResult.retry_hint |
| `@start → @listen` state machine | CrewAI Flows (4) | Workflow steps 1→2→3→...→7 |
| PlanningAgent + worker dispatch | AutoGen (5) | Planner + orchestrator dispatch |
| Max fix cycles (3) | Conductor (6) | Max retries (2) enforced by orchestrator |

## 4. Recommendation (.90 confidence)

Rewrite `orchestrator.agent.md` as a pure sequencer with 8 steps (plan → track → dispatch → evaluate → execute → pipeline → loop → curate). Key design decisions:

1. **Remove all cognitive instructions** — no board reading, no DAG building, no gate checks, no result interpretation. Replace with subagent calls.
2. **Remove unused tools** — strip file editing, search, web, markitdown, problems from the tools list. Keeps the orchestrator's prompt smaller and its action space constrained.
3. **Add planner + evaluator to agents list** — alongside existing agent roster.
4. **Constant-size context** — each wave's results are consumed by the evaluator and discarded. The planner re-reads the board each iteration. Nothing accumulates.
5. **Retry tracking stays in orchestrator** — simple counter, not cognitive work. Evaluator recommends RETRY; orchestrator increments counter and caps at 2.

**Risk:** The LLM may still try to interpret results or make judgment calls despite instructions. **Mitigation:** The evaluator returns explicit verdicts (ADVANCE/RETRY/BLOCK/ESCALATE) with target statuses — there is no ambiguity for the orchestrator to resolve. Add a critical_rule: "Never interpret subagent output. The evaluator already did that."

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Rewrite orchestrator.agent.md as pure sequencer" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 682 --body "Rewrite orchestrator.agent.md: replace 10-step cognitive workflow with 8-step mechanical loop (plan->track->dispatch->evaluate->execute->pipeline->loop->curate). Remove unused tools (edit/*, search, web, markitdown, read/problems, read/readFile). Add planner+evaluator to agents list. Add critical_rules: never read board (planner does), never interpret results (evaluator does), never edit files. See docs/orchestrator-rewrite-sequencer-research.md.\n\nAC:\n- [ ] Workflow is 8 steps: plan, track, dispatch, evaluate, execute, pipeline, loop, curate\n- [ ] No kanban-md list or kanban-md show in orchestrator workflow\n- [ ] No result interpretation logic — evaluator verdicts executed mechanically\n- [ ] Tools list reduced: no edit/*, search, web, markitdown\n- [ ] planner and evaluator in agents frontmatter\n- [ ] critical_rules include: no board reading, no result interpretation, no file editing\n- [ ] Context stays constant-size (nothing accumulates across waves)"

kanban\kanban-md.exe create "Create planner.agent.md with WAVE_PLAN output" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 680 --body "Create .github/agents/planner.agent.md per docs/planner-agent-research.md. Owns Steps 1-4 of old orchestrator. Returns structured WAVE_PLAN output. Tools: kanban-md list/show/edit only. No move, no agent dispatch, no file editing.\n\nAC:\n- [ ] planner.agent.md exists with persona, critical_rules, workflow, output_format, boundaries\n- [ ] Uses WAVE_PLAN structured output format (WAVE N / BLOCKED / SKIPPED sections)\n- [ ] Only has kanban-md read + edit tools\n- [ ] Writes wave assignment to each task via --append-body --timestamp"

kanban\kanban-md.exe create "Create evaluator.agent.md with EvalResult output" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 681 --body "Create .github/agents/evaluator.agent.md per docs/evaluator-agent-research.md. Returns structured EvalResult per task. Verdicts: ADVANCE/RETRY/BLOCK/ESCALATE with target_status, confidence, reason, notes_for_next_agent, retry_hint.\n\nAC:\n- [ ] evaluator.agent.md exists with persona, workflow, output_format, boundaries\n- [ ] EvalResult schema: task_id, verdict, target_status, confidence, reason, notes_for_next_agent, retry_hint\n- [ ] Read-only: never moves tasks, never edits code\n- [ ] Bounded: max 1 wave of results per invocation"

kanban\kanban-md.exe create "Integration test: orchestrator sequencer loop end-to-end" --priority needed --tags "scope:copilot,agent,test,phase-agent-arch" --depends-on 682 --body "Manually verify the orchestrator sequencer loop works end-to-end with planner and evaluator. Create 3 small tasks with dependencies, run orchestrator, verify: planner produces WAVE_PLAN, orchestrator dispatches without reading board, evaluator produces verdicts, orchestrator executes verdicts mechanically.\n\nAC:\n- [ ] Planner called once per re-plan cycle (not per task)\n- [ ] Orchestrator never calls kanban-md list or kanban-md show\n- [ ] Evaluator called once per wave completion\n- [ ] ADVANCE/RETRY/BLOCK verdicts all exercised\n- [ ] Context window does not grow across waves"
```

