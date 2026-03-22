---
name: orchestration
description: "Orchestration workflow: plan → dispatch → loop. Mechanical dispatch loop for the orchestrator agent."
---

# Orchestration Workflow

The orchestrator is a mechanical dispatch loop. It asks the planner for a dispatch list,
runs all tasks in parallel, then re-plans from fresh board state. The board is the state
machine — subagents move their own tasks, and the planner reads reality each cycle.

## Context budget

The orchestrator maintains constant-size context:

- **No board state.** The planner reads the board each cycle. You never call `kanban-md list` or `kanban-md show`.
- **No signal interpretation.** Subagents return a short Channel A diagnostic line. You check only: did the agent return normally, or did it error/crash? You do not parse verdicts or route based on signals.
- **No retry tracking state — except stale_retried and sequential_remaining.** If an agent crashes, you retry once immediately. If it crashes again, you note the failure and pass it to the planner in the next cycle. The planner sees the task hasn't moved and handles it.
- **Stale-retried tracking.** When the planner's dispatch includes a `retry_hint` for a task, add that task ID to a `stale_retried` set. Pass these IDs in the failure context so the planner can block them if they remain stale. Clear an ID when the task moves to a new status.
- **Rate-limit sequential counter.** Track `sequential_remaining` (integer, starts at 0). When a rate-limit crash triggers sequential mode, set this to 3. Decrement by 1 after each sequential dispatch. When it reaches 0, resume parallel waves.
- **Prior cycle results discarded.** After each plan→dispatch cycle, all results are gone. The next cycle starts fresh with only the scope filter, crash failure IDs, and `stale_retried` IDs from the current cycle.

## Signal contracts

See agent-common → **Inter-agent communication protocol** for the full Channel A/B spec.

**Planner → Orchestrator:** JSON with `dispatch` array (extract `(id, agent)` tuples,
priority-sorted) and `blocked` array (informational — report but don't act). If
`dispatch` is empty, report blocked tasks and stop.

**Subagent → Orchestrator:** Channel A diagnostic line. You do NOT parse this for
routing. Only check: did the agent return normally (success) or crash (failure)?
Subagents move their own tasks; the planner reads the board next cycle.

## Step 1 — Plan

Dispatch the planner with the user's scope filter and any failure context from
the previous cycle:

```
runSubagent("planner", "Plan: {scope_filter}", "Plan dispatch")
```

If there were failures from the previous cycle (crashes or stale retries):

```
runSubagent("planner", "Plan: {scope_filter}\n\nPrevious cycle: #{id} crashed twice; #{id2} stale, retried with hint", "Plan dispatch")
```

The failure context includes two categories:

- **Crash failures:** `#{id} crashed twice` — agent errored on both attempts.
- **Stale-retried IDs:** `#{id} stale, retried with hint` — task was dispatched with
  a `retry_hint` this cycle but hasn't moved. Pass these IDs so the planner can block
  them if they remain stale next cycle.

Track `stale_retried` IDs across cycles: when the planner's dispatch includes a
`retry_hint`, add that task ID to the stale_retried set. Clear an ID from the set
when the task moves to a new status (it's no longer stale).

Receive the JSON plan. If `dispatch` is empty (only blocked tasks), report the blocked
tasks to the user and stop.

If `blocked` mentions stale tasks (dispatched last cycle but unchanged), report
those to the user as potential issues.

## Configuration

| Setting | Value | Notes |
| --- | --- | --- |
| **Wave size** | 3 | Max parallel dispatches per wave. Single source of truth — all wave-batching rules derive from this. |

## Step 2 — Dispatch

Dispatch the `dispatch` array in **parallel waves** (wave size defined in Configuration
above). Take tasks in the order the planner provided (priority order). For each wave:

1. Issue up to **wave-size** `runSubagent` calls in a **single parallel tool-call
   block** — one task per call.
2. Wait for all calls in the wave to complete.
3. Handle errors — including rate-limit detection (see below).
4. Move to the next wave (remaining tasks, up to wave-size each).

### Wave assembly

The planner provides a priority-sorted flat list. You assemble it into waves using
agent-type compatibility. Walk the list top-to-bottom, filling each wave up to
wave-size. If an entry is incompatible with the current wave, skip it and try the
next entry. Skipped entries go into subsequent waves — never drop them.

**Agent-type compatibility rules:**

| Agent type | Multiple of same type in wave? | Never share wave with |
| --- | --- | --- | --- |
| architect, curator, kanban-planner, researcher, writer | yes | none |
| auditor | no | builder, reviewer, test-writer |
| builder | no | auditor |
| reviewer, test-writer | yes | auditor |

**Assembly algorithm:**
1. Walk the priority-sorted dispatch list top-to-bottom.
2. For each entry, check if it fits the current wave (compatibility + wave-size).
3. If it fits, add it. If not, skip it for a later wave.
4. When the current wave is full or no more entries fit, close it and start the next.
5. Repeat until all entries are assigned to waves.

In most cases, simple re-ordering within a priority tier is enough to fill waves
cleanly. If it doesn't work out, use smaller waves rather than dropping tasks.

After all waves from this plan complete, proceed to Step 3.

### Rate-limit sequential fallback

If any subagent crashes with a **rate-limit error** (the error message contains
"rate-limited", "rate_limited", or "rate limits"):

1. **Switch to sequential mode** for 3 subagent calls. Do not issue any
   more parallel calls in this wave.
2. **Retry the rate-limited subagent(s)** one at a time (one `runSubagent` call per
   tool-call block), waiting for each to complete before starting the next.
3. After finishing the current wave's retries, continue dispatching the remaining
   tasks from the plan **sequentially** (one at a time) until you have completed at
   least **3 sequential dispatches** total (counting from the moment you entered
   sequential mode, including the retries from step 2). If the current wave had
   fewer than 3 remaining dispatches, the sequential requirement carries into the
   next wave(s) within the same cycle.
4. Once the sequential minimum is satisfied,**resume parallel dispatch**.

The planner dispatch does not count toward the sequential minimum — it is always a
single call and is not affected by this rule.

**Dispatch prompt contains ONLY the task ID.** Subagents read their own AC via
`kanban\kanban-md.exe show {id}` in their skill Step 1. Never include AC text, file paths,
shell commands, pytest flags, or step-by-step procedures in the dispatch prompt.

**Exception — retry_hint:** When a dispatch entry includes a `retry_hint` field (set by
the planner for first-stale tasks), append it to the dispatch prompt:

```
runSubagent("builder", "Build: #103\nRetry context: Review FAIL: missing coverage on parser module", "Builder #103")
```

This is the sole exception to the ID-only dispatch rule. The hint is a single line
(≤120 chars) summarizing the prior failure — it gives the agent targeted context
without restating AC or procedures.

Example — 5 tasks dispatched in parallel waves:

Wave 1:
```
runSubagent("architect", "Architect Review: #101", "Architect #101")
runSubagent("builder", "Build: #103", "Builder #103")
runSubagent("reviewer", "Review: #105", "Reviewer #105")
```
[parallel — all return at once]

Wave 2:
```
runSubagent("test-writer", "Write tests: #110", "Test-writer #110")
runSubagent("researcher", "Research: #112", "Researcher #112")
```
[parallel — both return]

Note: the auditor runs the full test suite, so it goes in a solo wave (or with
non-pytest agents like architect, writer, researcher) — never alongside builder,
test-writer, or reviewer.

**Error handling:** If a subagent errors (crash, timeout, no response):

1. **Check for rate-limit errors first.** If the error message contains
   "rate-limited", "rate_limited", or "rate limits", follow the **rate-limit
   sequential fallback** procedure above instead of the normal retry flow.
2. For non-rate-limit errors: retry the same dispatch **once** immediately.
3. If it errors again, record the task ID as a failure. Do NOT retry a third time.

After all dispatches complete (including any retries), collect:

- **Successes:** tasks where the agent returned normally (regardless of what it said)
- **Failures:** tasks where the agent crashed twice

Update `manage_todo_list` with results.

## Step 3 — Loop

After all dispatches from Step 2 complete:

1. **Failures exist?** → Note them as failure context for the next planning cycle.
2. **Re-plan:** Go to Step 1. The planner reads fresh board state. Tasks that
   advanced are in their new status. Tasks that failed are unchanged (planner flags
   them as stale). Dependencies resolved by this cycle's successes unlock new tasks.
3. **Empty plan?** — If the planner returns an empty `dispatch` array:
   - If any tasks reached `done` during this session, dispatch the curator:
     ```
     runSubagent("curator", "Curate: session complete", "Curation")
     ```
   - Report final status to the user and stop.

The loop continues until the planner has nothing to dispatch.

## Self-critique checklist

Before reporting session complete:

- [ ] Planner was dispatched with the user's scope filter (not a hardcoded filter)
- [ ] Every task in `dispatch` was dispatched (none silently dropped)
- [ ] Waves respect wave-size limit from Configuration (unless in sequential mode)
- [ ] Wave assembly uses agent-type compatibility rules (auditor solo, scoped runners may share)
- [ ] ONE task per subagent call — no batching multiple tasks into one call
- [ ] Dispatch prompts contained ONLY task IDs — except `retry_hint` lines for stale retries
- [ ] Errors retried exactly once — no infinite retry loops (rate-limit retries follow sequential fallback)
- [ ] Rate-limit sequential fallback applied correctly (≥ 3 sequential dispatches, reset on new cycle)
- [ ] Failure context passed to planner on next cycle — failures not silently dropped
- [ ] `manage_todo_list` updated at every step transition
- [ ] Session summary reports all completed/blocked/failed tasks
