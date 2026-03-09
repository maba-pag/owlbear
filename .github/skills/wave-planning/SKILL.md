---
name: wave-planning
description: "Wave planning workflow: read board → build DAG → gate checks → produce WAVE_PLAN. Also covers EVALUATE mode for assessing subagent results. Used by the planner agent."
---

# Wave Planning

Step-by-step process for planning execution waves from a kanban board and evaluating
subagent results. The planner operates in two modes: PLAN and EVALUATE.

## Agent dispatch mapping

The planner assigns agents based on task status:

| Task status   | Dispatch agent | Pipeline action                                           |
| ------------- | -------------- | --------------------------------------------------------- |
| `backlog`     | `architect`    | Architecture review → move to `todo`                      |
| `todo`        | `test-writer`  | Write failing tests (RED phase) → move to `in-progress`   |
| `in-progress` | `builder`      | GREEN phase → move to `review`                            |
| `review`      | `reviewer`     | Quality verification → move to `docs`                     |
| `docs`        | `writer`       | Documentation gate → move to `done`                       |
| `done`        | `auditor`      | Exit gate verification → archive                          |

Tasks in `ideation` are never dispatched directly. `ideation` tasks need
research first (orchestrator routes to `researcher`).

---

## PLAN mode

### Step 1 — Receive scope

The orchestrator passes a scope filter: a tag, status, ID range, or `"all"`.

Apply the filter to `kanban\kanban-md.exe list --compact`. Examples:

- Tag filter: `kanban\kanban-md.exe list --compact --tag phase-3`
- Status filter: `kanban\kanban-md.exe list --compact --status todo,review`
- All: `kanban\kanban-md.exe list --compact`

If the scope returns 0 tasks, output an empty WAVE_PLAN (no waves) and stop.

### Step 2 — Read board

For each candidate task from Step 1, run:

```
kanban\kanban-md.exe show {id}
```

Extract from each task: title, status, priority, tags, `depends_on` list, blocked
state, and acceptance criteria.

Use `manage_todo_list` to track progress through the remaining steps.

**Context budget:** If the scope contains more than 20 tasks, prioritize by: (1) critical
and needed priority first, (2) tasks closest to `done` in the pipeline (docs > review >
todo > backlog). Read details for the top 20 only — report the rest as SKIPPED with
gate: `scope_overflow`.

### Step 3 — Build DAG

Construct a dependency graph from task metadata:

- **Nodes** = in-scope tasks
- **Edges** = `depends_on` relationships (directed: dependency → dependent)

Classify each task:

| Classification | Condition                                                                        |
| -------------- | -------------------------------------------------------------------------------- |
| **Ready**      | All `depends_on` tasks are in `done` status AND task is not blocked              |
| **Blocked**    | At least one `depends_on` task is NOT `done`, or task has `--block` set          |
| **External**   | Has `depends_on` pointing to tasks outside the current scope that are not `done` |

External-blocked tasks go to the BLOCKED section with the out-of-scope dependency noted.

### Step 4 — Gate checks

For each **ready** task (not blocked, not external), run all 5 gate checks. A task must
pass ALL gates to enter a wave. Any failure → SKIPPED with the gate name and reason.

**Gate 1 — Status gate:**
Task status must match a dispatchable status in the agent dispatch mapping above.
Tasks in `ideation` fail this gate. Tasks in `in-progress` are dispatched to the builder.

**Gate 2 — Dependency gate:**
ALL tasks in `depends_on` must be in `done` status. No exceptions.

**Gate 3 — Atomicity gate:**
Title describes a single responsibility. Red flag: the word "and" joining unrelated
concerns (e.g., "Implement parser and update config"). Related concerns joined by "and"
are fine (e.g., "Read board and build DAG" — both are planning sub-steps).

**Gate 4 — TDD gate (safety net):**
For `in-progress` implementation tasks (not research, docs, test, or config), verify that
the task body contains `## Test-Writer Notes` (written by the test-writer during RED
phase). If present → gate passes. If absent → something went wrong (task reached
`in-progress` without the test-writer running). Block the task and flag the anomaly.
As a fallback, a linked test task in `done` status also satisfies this gate.
Skip for non-implementation tasks.

This gate catches tasks that reached `in-progress` without proper test-writer processing
(e.g., manually moved tasks). When the pipeline works correctly, this gate is redundant
— which is by design (belt-and-suspenders).

**Gate 5 — Clarity gate:**
Task body contains non-empty acceptance criteria with at least one `- [ ]` checkbox.
Tasks with empty or missing AC fail this gate.

### Step 5 — Wave grouping

Group all gate-passing tasks into execution waves:

- **Wave 1:** Tasks whose ALL dependencies are already `done` (no in-scope predecessors)
- **Wave N+1:** Tasks whose dependencies are satisfied by completions in Wave N or earlier
- **Within a wave:** Tasks are independent — they can run in parallel
- **Max 4 tasks per wave.** If more than 4 tasks qualify for the same wave, split them
  across consecutive waves, prioritizing by: (1) `critical` > `needed` > `important`,
  (2) tasks that unblock the most downstream dependents

### Step 6 — Annotate

For each task that appears in a WAVE (not BLOCKED, not SKIPPED), write the wave
assignment to the task body as an audit trail:

```
kanban\kanban-md.exe edit {id} --append-body "Wave {n}, agent: {agent_name}" --timestamp
```

This is non-destructive (append-only) and persists beyond the planner's context window.

### Step 7 — Output WAVE_PLAN

Produce the structured WAVE_PLAN output as the final response. Format:

```
WAVE_PLAN
WAVE 1:
  #{id} {agent_name} "{one-line AC summary}"
  #{id} {agent_name} "{one-line AC summary}"
WAVE 2:
  #{id} {agent_name} "{one-line AC summary}"
BLOCKED:
  #{id} "{reason — which dependency is unmet or why blocked}"
SKIPPED:
  #{id} gate:{gate_name} "{reason — what failed}"
END_PLAN
```

**Rules:**

- `WAVE_PLAN` and `END_PLAN` are the opening and closing delimiters
- Each `WAVE N:` header is followed by indented task lines
- Task lines: `#{id} {agent_name} "{one-line summary}"` — agent name from the dispatch mapping
- `BLOCKED:` section lists tasks with unmet dependencies or explicit blocks
- `SKIPPED:` section lists tasks that failed gate checks, with the gate name
- If no tasks are dispatchable, output `WAVE_PLAN` / `END_PLAN` with only BLOCKED/SKIPPED sections
- Gate names in SKIPPED: `status`, `dependency`, `atomicity`, `tdd`, `clarity`, `scope_overflow`

---

## EVALUATE mode

When dispatched with a prompt starting with "Evaluate wave:", switch to EVALUATE mode.
You receive raw Channel A signals from subagents and produce per-task routing verdicts.

### Step 1 — Parse dispatch prompt

Extract pipeline stage, per-task Channel A signals, and retry counts.

### Step 2 — Read AC for each task

Run `kanban-md show {id}` to read the full acceptance criteria. Do not rely on the
orchestrator's summary.

### Step 3 — Assess each AC line

Check every AC line against the subagent's signal for specific evidence (test names,
file paths, command output). Track: MET / NOT MET / PARTIAL.

### Step 4 — Produce per-task verdict

Apply verdict semantics:

| Verdict    | When                                                                      | Orchestrator action                   |
| ---------- | ------------------------------------------------------------------------- | ------------------------------------- |
| `ADVANCE`  | AC evidence sufficient, confidence >= .80                                 | Proceed to next pipeline stage        |
| `RETRY`    | Fixable failure, `retry_count` below 2                                    | Re-dispatch with `retry_hint` context |
| `BLOCK`    | Unfixable without redesign, missing prerequisite, or external dependency  | Report to user                        |
| `ESCALATE` | 2+ prior failures (`retry_count >= 2`) OR confidence < .50               | Alert user, pause task                |

**ADVANCE** requires confidence >= .80. Below .80 does not advance.
**RETRY** requires a non-empty `retry_hint` — specific verbal feedback for the next attempt.
**ESCALATE** is the safety valve. Never let a task cycle endlessly.

### Step 5 — Append notes to task body

```
kanban-md edit {id} -a "## Planner Evaluation\n{notes}" -t
```

Add context for the downstream agent.

### EVALUATE output format

Per task:

```
## Evaluation: #{id} — {title}

### AC Assessment
| AC Line | Evidence | Status |
|---------|----------|--------|
| {line}  | {evidence or "NO EVIDENCE"} | MET / NOT MET / PARTIAL |

### Verdict
- task_id: {id}
- verdict: ADVANCE | RETRY | BLOCK | ESCALATE
- target_status: {next status}
- confidence: {0.0-1.0}
- reason: {one-line, evidence-backed}
- notes_for_next_agent: {context for downstream agent}
- retry_hint: {required when verdict=RETRY}
```

Wave summary:

```
## Wave Summary
- Tasks evaluated: {N}
- ADVANCE: {count}
- RETRY: {count}
- BLOCK: {count}
- ESCALATE: {count}
```

### EVALUATE examples

**Bad — rubber-stamp with no evidence:**

```
Builder output looks complete. Tests pass. ADVANCE.
```

No AC assessment table, no per-line evidence, no confidence score. This is the failure
mode evaluation exists to prevent.

**Bad — RETRY without retry_hint:**

```
- verdict: RETRY
- retry_hint:
```

The builder has no guidance on what to fix. `retry_hint` must be specific.

**Good — evidence-based ADVANCE:**

```
### AC Assessment
| AC Line                       | Evidence                                                       | Status |
| ----------------------------- | -------------------------------------------------------------- | ------ |
| OAuth device flow implemented | `test_device_flow_initiates` passes, `auth.py` L24-48         | MET    |
| Token refresh on 401          | `test_refresh_on_401` passes, retry logic at `client.py` L67  | MET    |
| Credentials stored in keyring | `test_keyring_store` + `test_keyring_retrieve` pass            | MET    |

### Verdict
- verdict: ADVANCE
- confidence: .92
- reason: All 3 AC lines met with specific test evidence and code references
- notes_for_next_agent: Focus review on token refresh edge cases
```

**Good — evidence-based RETRY with specific hint:**

```
### AC Assessment
| AC Line                             | Evidence                                 | Status  |
| ----------------------------------- | ---------------------------------------- | ------- |
| Pydantic model validates all fields | `test_config_validation` passes          | MET     |
| Invalid config raises ConfigError   | NO EVIDENCE — no test for invalid input  | NOT MET |

### Verdict
- verdict: RETRY
- confidence: .55
- reason: AC line 2 has no test — invalid config path untested
- retry_hint: Add test that passes invalid config values and asserts ConfigError is raised.
```

**Good — ESCALATE after retry exhaustion:**

```
### Verdict
- verdict: ESCALATE
- confidence: .30
- reason: retry_count=2, CDP attach fails consistently — likely environment issue
- notes_for_next_agent: Human investigation needed — two prior attempts failed identically.
```

---

## Self-critique checklist

Before outputting:

- [ ] Scope filter was applied — not reading the entire board unfiltered (unless scope is "all")
- [ ] Every candidate task was read with `kanban-md show {id}` (not just list output)
- [ ] DAG was built — tasks classified as ready, blocked, or external
- [ ] All 5 gate checks were run on every ready task
- [ ] No task in a WAVE failed any gate check
- [ ] Waves respect dependency ordering — Wave N+1 depends only on Wave N or earlier
- [ ] No wave exceeds 4 tasks
- [ ] Agent names in WAVE lines match the dispatch mapping
- [ ] BLOCKED section includes all tasks with unmet dependencies and reasons
- [ ] SKIPPED section includes all gate-failed tasks with gate name and reason
- [ ] Wave annotations written to task bodies via `--append-body --timestamp`
- [ ] Output uses WAVE_PLAN format, not prose or markdown tables
- [ ] No `kanban-md move` commands were run
- [ ] No subagents were dispatched
- [ ] No source/test files were edited
