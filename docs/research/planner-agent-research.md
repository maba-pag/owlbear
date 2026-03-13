# Planner Agent: Board Reading + Wave Planning — Research

> **Owning task:** #680 — Planner agent: board reading + wave planning
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

The orchestrator currently performs all cognitive work in-context: reading the full board, building dependency DAGs, running 5 gate checks per task, and planning execution waves. This is the primary cause of context overflow (#663 class of failures). Should a separate planner agent own this work, and what should its output contract look like?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| AutoGen SelectorGroupChat + PlanningAgent | <https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/selector-group-chat.html> | .85 — Dedicated PlanningAgent breaks tasks → assigns to specialists → checks progress |
| CrewAI AgentPlanner | <https://docs.crewai.com/concepts/planning> | .80 — Separate LLM planning call before execution; plan injected into task descriptions |
| Conductor DAG + topological dispatch | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | .90 — DAG → topological levels → wave dispatch (already studied, see [conductor research](conductor-orchestrator-superpowers-research.md)) |
| OwlBear orchestrator.agent.md | `.github/agents/orchestrator.agent.md` | .95 — Steps 1-5 are the exact scope to extract |

## 3. Analysis

### 3.1 Is a separate planner agent sound?

All three frameworks separate planning from execution. The orchestrator never holds the full task list — it receives a structured plan and mechanically dispatches.

| Pattern | How planning is separated | Context stays bounded? |
|---------|--------------------------|----------------------|
| **AutoGen PlanningAgent** | Dedicated agent produces numbered `agent: task` assignments; SelectorGroupChat routes based on these | Yes — worker agents see only their slice |
| **CrewAI AgentPlanner** | `planning=True` triggers a separate LLM call pre-execution; plan added to each task desc | Yes — crew agents see plan excerpt, not full board |
| **Conductor** | DAG builder → topological sort → wave[] array → loop dispatches each level | Yes — orchestrator loop is O(1) per wave |
| **OwlBear (current)** | Orchestrator does everything: read board → build DAG → gate check → plan waves → dispatch | **No** — full board + all task bodies in context |

**Verdict (.90 confidence):** Extracting planning to a subagent is the standard pattern. OwlBear is the outlier by doing it in-context.

### 3.2 What moves from orchestrator to planner?

| Orchestrator step | Moves? | Rationale |
|-------------------|--------|-----------|
| Step 1: Read Board State | **YES** | `kanban-md list` + `kanban-md show` output is the largest context consumer |
| Step 2: Build Dependency Graph | **YES** | DAG construction is cognitive work on board data |
| Step 3: Gate Checks (5 gates) | **YES** | Gate evaluation reads task bodies — heavy context |
| Step 4: Plan Execution Waves | **YES** | Grouping into waves is the planner's core output |
| Step 5: Initialize Progress Tracker | **PARTIAL** | Wave plan comes from planner; `manage_todo_list` stays in orchestrator (UI concern) |
| Step 6: Dispatch Wave | No | Orchestrator mechanically dispatches from plan |
| Step 7: Monitor and Advance | No | Pipeline tracking stays in orchestrator |
| Step 8: Handle Failures | No | Retry/escalate stays in orchestrator |

### 3.3 Planner output contract

The planner returns a fixed-format plan the orchestrator mechanically parses. Based on AutoGen's `agent: task` pattern and Conductor's wave array:

```
WAVE_PLAN
  WAVE 1:
    #{id} {agent_name} "{one-line AC summary}"
    #{id} {agent_name} "{one-line AC summary}"
  WAVE 2:
    #{id} {agent_name} "{one-line AC summary}"
  BLOCKED:
    #{id} "{reason — which dependency is unmet}"
  SKIPPED:
    #{id} gate:{gate_name} "{reason — what failed}"
END_PLAN
```

**Design rationale:**
- Line-oriented, grep-parseable — orchestrator doesn't need an LLM to read it
- Agent name is explicit — orchestrator doesn't need to infer dispatch target
- AC summary is one line — orchestrator sees only what it needs for the dispatch prompt
- BLOCKED/SKIPPED sections give the orchestrator complete awareness without re-reading tasks

### 3.4 Planner tool requirements

| Tool | Purpose | Needed? |
|------|---------|---------|
| `kanban-md list --compact` | Read board overview | **YES** |
| `kanban-md show {id}` | Read task details, AC, deps | **YES** |
| `kanban-md edit {id} --append-body --timestamp` | Write wave plan as audit trail | **YES** |
| `kanban-md move` | Change task status | **NO** — orchestrator moves tasks |
| `agent` / `runSubagent` | Dispatch subagents | **NO** — planner only plans |
| File edit tools | Write code | **NO** — planner is read-only on code |

### 3.5 Planner writes plan to kanban notes

The planner appends its wave assignment to each dispatched task's body:

```
kanban\kanban-md.exe edit {id} --append-body "Wave plan: wave {n}, agent: {agent_name}" --timestamp
```

This is auditable (timestamped), non-destructive (append-only), and persists the plan beyond the planner's context window. AutoGen's PlanningAgent and CrewAI's AgentPlanner both inject plan context into task descriptions — `--append-body` is the kanban-md equivalent.

### 3.6 Naming: planner vs kanban-planner

The existing `kanban-planner` agent handles **task creation and decomposition**. The new planner handles **wave scheduling and dispatch planning**. These are distinct roles:

| Agent | Role | Inputs | Outputs |
|-------|------|--------|---------|
| `kanban-planner` | Create tasks from requirements | Feature desc, plan doc | `kanban-md create` commands |
| `planner` | Schedule existing tasks into waves | Board state, scope filter | Structured wave plan |

**Recommendation (.85 confidence):** Name the new agent `planner` (not `wave-planner` or `scheduler`). The existing `kanban-planner` retains its name. The orchestrator dispatches `planner` for wave planning and `kanban-planner` for task creation — no ambiguity.

## 4. Recommendation (.90 confidence)

Create `planner.agent.md` that owns Steps 1-5 of the current orchestrator. The planner:

1. Receives a scope filter from the orchestrator (tag, status, etc.)
2. Reads the board via `kanban-md list` + `kanban-md show`
3. Builds DAG, runs 5 gate checks, groups into waves (max 4 tasks per wave)
4. Returns the `WAVE_PLAN` structured output
5. Writes wave assignment as `--append-body` note to each dispatched task

The orchestrator's Steps 1-5 are replaced with a single `runSubagent("planner", ...)` call. The orchestrator then mechanically parses the plan and dispatches waves.

**Risk:** Planner context overflow on very large boards (50+ tasks). **Mitigation:** Scope filter limits the planner's input (e.g., `--status todo,in-progress --tag phase-3`). The planner also uses `--compact` output to minimize token consumption.

## 5. Follow-up Tasks

Commands below — presented for review, NOT executed.

```
kanban\kanban-md.exe create "Create planner.agent.md with board reading and wave planning" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 680 --body "Create .github/agents/planner.agent.md that reads the board, builds the dependency DAG, runs 5 gate checks, and returns a structured WAVE_PLAN output. Tools: kanban-md list/show/edit only. No move, no agent dispatch, no file editing. Output contract uses the WAVE_PLAN format from docs/planner-agent-research.md §3.3. Writes wave assignment to task body via --append-body --timestamp.\n\nAC:\n- [ ] planner.agent.md exists with persona, critical_rules, workflow, output_format, boundaries\n- [ ] Uses WAVE_PLAN structured output format\n- [ ] Only has kanban-md read + edit tools (no move, no agent, no file tools)\n- [ ] Writes wave assignment to each dispatched task via --append-body"

kanban\kanban-md.exe create "Rewrite orchestrator Steps 1-5 as single planner dispatch" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --depends-on 680 --body "Replace orchestrator.agent.md Steps 1-5 with a single runSubagent('planner', ...) call. The orchestrator receives the WAVE_PLAN output and mechanically dispatches waves. Remove kanban-md list and kanban-md show from orchestrator's workflow (planner does that). Add planner to orchestrator's agents list.\n\nAC:\n- [ ] Steps 1-5 removed from orchestrator.agent.md\n- [ ] New Step 1: dispatch planner with scope filter\n- [ ] New Step 2: parse WAVE_PLAN output, create progress tracker\n- [ ] Orchestrator never calls kanban-md list or kanban-md show\n- [ ] planner added to orchestrator's agents list in frontmatter"

kanban\kanban-md.exe create "Tests for planner output contract" --priority needed --tags "scope:copilot,agent,test,phase-agent-arch" --depends-on 680 --body "Write test cases validating the planner's WAVE_PLAN output contract. These are prompt-level tests (format validation), not Python unit tests.\n\nAC:\n- [ ] Test: WAVE_PLAN contains at least one WAVE section when dispatchable tasks exist\n- [ ] Test: BLOCKED section lists tasks with unmet dependencies and includes reason\n- [ ] Test: SKIPPED section lists tasks that fail gate checks with gate name and reason\n- [ ] Test: each task line in a WAVE includes #{id}, agent name, and one-line summary\n- [ ] Test: WAVE_PLAN is empty (no waves) when all tasks are blocked"
```
