---
name: orchestration
description: "Orchestration workflow: plan → dispatch → loop. Mechanical dispatch loop for the orchestrator agent."
user-invocable: false
---

# Orchestration Workflow

The orchestrator is a mechanical dispatch loop. It asks the planner for a dispatch list,
runs all tasks in parallel, then re-plans from fresh board state. The board is the state
machine — subagents move their own tasks, and the planner reads reality each cycle.

## Context budget

The orchestrator maintains constant-size context:

- **No board state.** The planner reads the board each cycle. You never call `kanban-md list` or `kanban-md show`.
- **No signal interpretation.** Subagents return a short Channel A diagnostic line. You check only: did the agent return normally, or did it error/crash? You do not parse verdicts or route based on signals.
- **No retry tracking state — except stale_retried and sequential_remaining.** If an agent crashes, you retry once in another wave. If it crashes again, you note the failure and pass it to the planner in the next cycle. The planner sees the task hasn't moved and handles it.
- **Stale-retried tracking.** When the planner's dispatch includes a `retry_hint` for a task, add that task ID to a `stale_retried` set. Pass these IDs in the failure context so the planner can block them if they remain stale. Clear an ID when the task moves to a new status.
- **Rate-limit sequential counter.** Track `sequential_remaining` (integer, starts at 0). When a rate-limit crash triggers sequential mode, set this to 3. Decrement by 1 after each sequential dispatch. When it reaches 0, resume parallel waves.
- **Prior cycle results discarded.** After each plan→dispatch cycle, all results are gone. The next cycle starts fresh with only the scope filter, crash failure IDs, and `stale_retried` IDs from the current cycle.

## Signal contracts

See agent-common → **Inter-agent communication protocol** for the full Channel A/B spec.

**Planner → Orchestrator:** JSON with `dispatch` array (extract `(id, agent)` tuples,
priority-sorted). If `dispatch` is empty, report to the user that nothing is
dispatchable and stop.

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
when the planner dispatches the task in the next cycle **without** a `retry_hint`
— that signals the task moved and is no longer stale.

Receive the JSON plan. If `dispatch` is empty, report to the user that nothing is
dispatchable and stop.

## Configuration

| Setting | Value | Notes |
| --- | --- | --- |
| **Wave size** | 4 | Max parallel dispatches per wave. Single source of truth — all wave-batching rules derive from this. |

## Step 2 — Dispatch

Dispatch the `dispatch` array in **parallel waves** (wave size defined in Configuration
above). Take tasks in the order the planner provided (priority order). For each wave:

1. Issue up to **wave-size** `runSubagent` calls in
   a **single parallel tool-call block** — one task per call.
2. Wait for all calls in the wave to complete.
3. Handle errors — including rate-limit detection (see below).
4. Move to the next wave (remaining tasks, up to wave-size each).

### Wave assembly

The planner provides a priority-sorted flat list. You assemble it into waves using
agent-type compatibility. The goal is: **minimum wave count, maximum tasks dispatched,
no compatibility violations.**

**Agent-type compatibility rules:**

| Agent type | Category | May share wave with | Never with |
| --- | --- | --- | --- |
| auditor | restricted | light flex | builders, heavy flex, other auditors* |
| builder | restricted | light flex, heavy flex | auditors, other builders* |
| researcher, writer, architect, kanban-planner, curator | light flex | any | — |
| reviewer, test-writer | heavy flex | builders, other flex | auditors |

\* Same-type exclusion is relaxed during consolidation (step 6) for solo waves only. Builders and auditors still never share a wave.

**Safety criterion:** light flex agents never modify source/test files and never run the test suite → cannot interfere with the auditor's full-suite run.

**Assembly algorithm — four-bucket, minimize wave count:**

**Phase 1 — Draft the wave plan before dispatching:**

1. Separate into four buckets: **auditors**, **builders**, **light flex**, **heavy flex**. Keep priority order within each.
2. **Auditor waves.** One auditor per wave. Fill remaining slots (up to wave-size) with light flex, priority order.
3. **Builder waves.** One builder per wave. Fill remaining slots with light flex first (if any remain), then heavy flex, priority order.
4. **Overflow waves.** Remaining light + heavy flex → new waves (up to wave-size), priority order.
5. **Periodic curator runs.** Every fifth cycle (in cycles 5, 10, 15...) → add a curator agent to the last wave with a remaining slot. If all waves are full, skip the curator for this cycle.
6. **Consolidation.** DEACTIVATED TEMPORARILY. SKIP THIS STEP. Collect all solo-task waves of the same restricted type (solo-builder waves, solo-auditor waves). Merge each group into combined waves (up to wave-size), relaxing the same-type exclusion within each group. Never mix builders and auditors in one wave. Priority order preserved.
7. **Drop rule.** Any wave with exactly one task where that task is **not** an auditor → drop. Deferred to next cycle. **Exception:** if dropping would eliminate all non-auditor waves, keep the first one.

**Phase 2 — Execute the plan:**

8. Dispatch waves in order as drafted. No further reordering.

#### Worked example

**Input (priority order):** #862 (reviewer), #780 (reviewer), #920 (test-writer), #947 (researcher), #910 (auditor), #788 (writer), #781 (writer), #728 (writer), #853 (builder), #934 (builder), #521 (builder), #556 (builder), #733 (builder), #775 (builder)

Buckets: auditors=[#910], builders=[#853,#934,#521,#556,#733,#775], light=[#947,#788,#781,#728], heavy=[#862,#780,#920]

Step 2 — auditor waves (fill with light):
```
Wave 1: #910 (auditor), #947 (researcher), #788 (writer), #781 (writer)  ← 1+3 light (full)
```
Light remaining: [#728]

Step 3 — builder waves (fill with remaining light, then heavy):
```
Wave 2: #853 (builder), #728 (writer), #862 (reviewer), #780 (reviewer)  ← 1+1 light+2 heavy (full)
Wave 3: #934 (builder), #920 (test-writer)                               ← 1+1 heavy
Wave 4–7: #521, #556, #733, #775 (builders)                              ← solo each
```

Step 4 — overflow: nothing remaining.

Step 5 — Not a cycle mod 5 → no curator.

Step 6 — consolidation: Waves 4–7 are four solo-builder waves → merge into one wave:
```
Wave 4: #521 (builder), #556 (builder), #733 (builder), #775 (builder)   ← 4 builders (full)
```

Step 7 — drop rule: no solo non-auditor waves remain → nothing dropped.

**Final plan — 4 waves, 14 tasks.** 0 deferred.

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
4. Once the sequential minimum is satisfied, **resume parallel dispatch**.

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

The hint is a single line
(≤120 tokens) summarizing the prior failure — it gives the agent targeted context
without restating AC or procedures.

**Exception — curator:** The curator's prompt does not include a task ID:

```
runSubagent("curator", "Curate: Periodic curation", "Curation")
```

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

Note: auditors share waves only with **light flex** agents — never with builders, heavy flex, or other auditors. See wave assembly rules above.

**Error handling:** If a subagent errors (crash, timeout, no response):

1. **Check for rate-limit errors first.** If the error message contains
   "rate-limited", "rate_limited", or "rate limits", follow the **rate-limit
   sequential fallback** procedure above instead of the normal retry flow.
2. For non-rate-limit errors: retry the same dispatch **once**.
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

The loop continues until the planner has nothing to dispatch.
**Do not stop for any reason other than an empty plan.**

## Output format

Announce each cycle and wave briefly during execution:

```
Cycle 1 (Plan): Dispatching planner with scope '{filter}'...
Cycle 1 (Wave 1/3): #101 (architect), #103 (builder), #105 (reviewer)
Cycle 1 (Wave 2/3): #110 (test-writer), #112 (researcher)
Cycle 1 (Done): 4/5 succeeded, 1 crashed (#112)
```

At end of session:

```
Session complete:
  Completed: #101, #103, #105, #110
  Failed: #112 (crashed twice)
  Cycles: 2
```

## Self-critique checklist

Before reporting session complete:

- [ ] Planner was dispatched with the user's scope filter (not a hardcoded filter)
- [ ] Every task in `dispatch` was dispatched (none silently dropped)
- [ ] Waves respect wave-size limit from Configuration (unless in sequential mode)
- [ ] Wave assembly uses agent-type compatibility rules (auditor + light flex only, max 1 builder per wave except consolidated waves, heavy flex excluded from auditor waves)
- [ ] ONE task per subagent call — no batching multiple tasks into one call
- [ ] Dispatch prompts contained ONLY task IDs — except `retry_hint` lines for stale retries
- [ ] Errors retried exactly once — no infinite retry loops (rate-limit retries follow sequential fallback)
- [ ] Rate-limit sequential fallback applied correctly (≥ 3 sequential dispatches, reset on new cycle)
- [ ] Failure context passed to planner on next cycle — failures not silently dropped
- [ ] `manage_todo_list` updated at every step transition
- [ ] I did not stop the loop early for any reason — only an empty plan should end the session
