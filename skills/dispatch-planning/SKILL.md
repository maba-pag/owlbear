---
name: dispatch-planning
description: "Dispatch planning workflow: read board → build DAG → gate checks → produce JSON dispatch plan. Used by the planner agent."
user-invocable: false
---

# Dispatch Planning

Step-by-step process for producing a dispatch list from a kanban board. The planner
reads the board, classifies tasks, checks gates, and outputs a flat list of tasks the
orchestrator should dispatch in parallel.

## Agent dispatch mapping

The planner assigns agents based on task status:

<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/tdd-red/SKILL.md (Step 1 item 3),
     skills/arch-review/SKILL.md (non-impl tagging note),
     .github/prompts/agent-audit.prompt.md (Non-impl paragraph). -->
| Task status   | Dispatch agent | Pipeline action                                          | Non-impl pass-through? |
| ------------- | -------------- | -------------------------------------------------------- | ---------------------- |
| `ideation`    | `researcher`   | Research investigation → move to `backlog`               | No                     |
| `backlog`     | `architect`    | Architecture review → move to `todo`                     | No                     |
| `todo`        | `test-writer`  | Write failing tests (RED phase) → move to `in-progress`  | Yes — tags `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality` |
| `in-progress` | `builder`      | GREEN phase → move to `review`                           | Yes — if test-writer passed through |
| `review`      | `reviewer`     | Quality verification → move to `docs`                    | No                     |
| `docs`        | `writer`       | Documentation gate → move to `done`                      | No                     |
| `done`        | `auditor`      | Exit gate verification → archive                         | No                     |

**Non-implementation tasks:** Tasks tagged `research`, `docs`, `type:config`,
`type:docs`, `test`, `type:test`, `agent`, or `quality` still flow through the standard
pipeline (`todo → test-writer → in-progress → builder`). The test-writer recognizes
them and passes them through without writing tests (see tdd-red skill, Step 1a). This
keeps the dispatch table simple and avoids special-case routing. The architect is
responsible for tagging tasks correctly during backlog → todo approval.

### Non-status-triggered agents

Some agents are dispatched by condition rather than status:

| Agent            | Trigger condition                                                              | Dispatched by   |
| ---------------- | ------------------------------------------------------------------------------ | ---------------- |
| `kanban-planner` | Task body contains "Needs decomposition" (set by architect or any agent), OR orchestrator user explicitly requests it | Planner includes in dispatch list |
| `curator`        | Every 5th orchestration cycle (periodic, see orchestration skill Step 2)       | Orchestrator directly (not via planner) |

**Kanban-planner dispatch:** When the planner's Board Scan finds a task whose body
contains the marker `Needs decomposition:` (typically set by the architect during
review, or by any agent that encounters a task too complex for a single
`kanban-md create`), include it in the dispatch list with `"agent": "kanban-planner"`.
The kanban-planner reads the task, produces a decomposition plan, executes the
`kanban-md create` commands (autonomous mode when planner-dispatched), and returns.
The task itself is not moved — the kanban-planner creates child tasks at `ideation`
and the parent may be closed or split depending on the plan.

---

## Command Recipes

The planner uses exactly these commands. No improvisation — no `rg` on frontmatter, no
`Get-ChildItem` on task files, no foreach loops over individual `show` calls. All board
data comes from `kanban-md.exe` commands that respect server-side filtering (claim
timeout, dependency resolution, block flags).

### Recipe 0 — Decision and action requests

Run before the Board Scan. Check for resolved decision requests and action requests:

```powershell
Get-ChildItem docs/decisions/pending/*.md -EA SilentlyContinue | Select-Object -ExpandProperty FullName
```

For each file found, read frontmatter. **Type detection:** if the `completed:` field is
present, treat as an action request; otherwise treat as a decision request
(backwards-compatible — files without `request_type` default to decision).

For **decision requests**: if `approved: true`:

1. **Write decision summary to task body.** Read the `decision:` and `notes:` fields
   from the file. Append a `## Decision Resolved` section to the task body:

   ```powershell
   kanban\kanban-md.exe edit {id} -a "## Decision Resolved\nChosen: {decision}\nUser notes: {notes}\nSource: docs/decisions/resolved/{filename}" -t
   ```

   For **action requests** with `completed: true`, also extract the `## User findings`
   section (if present) and include it in the summary. This ensures the user's
   observations reach downstream agents via the task body.

2. **Unblock the task:** `kanban\kanban-md.exe edit {id} --unblock`
3. **Move the file** to `docs/decisions/resolved/`.

Before applying the 5-day auto-resolve, read the
`impact_tier` field from the file frontmatter. If `impact_tier: 3`, skip the 5-day
timer — the decision stays pending indefinitely until the user manually sets
`approved: true`. Missing `impact_tier` defaults to T2; `impact_tier: 1` in a pending
file should not exist in practice (T1 outcomes are autonomous) but if encountered is
treated as T2. If `impact_tier` is 2 (or absent) and `approved: false` and older than
5 days, auto-resolve: set `approved: auto`, unblock, and move to
`docs/decisions/resolved/`.

For **action requests**: if `completed: true`, unblock the task and move the file to
`docs/decisions/resolved/`. If `completed: false` and older than 5 days,
auto-resolve: set `completed: auto`, unblock, and move. Note: `completed: auto`
signals the user action was not manually confirmed. `impact_tier` does not apply to
action requests — they always use the 5-day auto-resolve.

Track unresolved counts by tier for the `pending` field in the JSON output:
`{"decisions_t2": N, "decisions_t3": N, "actions": N}`. `decisions_t2` = pending T2
or untiered decision requests; `decisions_t3` = pending T3 decision requests;
`actions` = pending action request files.

### Recipe 1 — Board Scan

**One terminal call.** Produces a classified, sorted, gate-checked candidate list in
~1.3K tokens (tested on an 850-task board, 46 dispatchable candidates).

```powershell
$pr=@{critical=0;needed=1;important=2;'nice-to-have'=3;someday=4}
$sr=@{done=0;docs=1;review=2;'in-progress'=3;todo=4;backlog=5;ideation=6}
$raw = kanban\kanban-md.exe list --json --unblocked --not-blocked --unclaimed `
  --status ideation,backlog,todo,in-progress,review,docs,done {scope} 2>&1 | Out-String
$tasks = $raw | ConvertFrom-Json
if (-not $tasks) { '(empty)'; return }
$tasks | Sort-Object {$pr[$_.priority]},{$sr[$_.status]} | ForEach-Object {
  $w=@()
  # NON_IMPL_TAGS — authoritative list. See also: tdd-red SKILL.md Step 1a, agent-audit.prompt.md
  $nonImpl = @('research','docs','type:config','type:docs','test','type:test','agent','quality')
  if ($_.status -eq 'in-progress' -and $_.body -notmatch '## Test-Writer Notes' -and
      -not ($_.tags | Where-Object { $_ -in $nonImpl })) {$w+='TW:MISSING'}
  if ($_.status -in @('todo','in-progress','review','docs','done') -and
      $_.body -notmatch '(?m)^\s*(-\s|\d+\.\s)') {$w+='AC:MISSING'}
  if ($_.body -match 'Needs decomposition:') {$w+='DECOMP'}
  if ($_.body -match '## Architecture Review') {$w+='ARCH:REVIEWED'}
  $t=if($_.tags){"($($_.tags -join ','))"}else{''}
  $x=if($w){" [!$($w -join ',')]"}else{''}
  "#$($_.id) $($_.status)/$($_.priority) $($_.title) $t$x"
}
"---"
"$($tasks.Count) candidates"
```

**What the `--unblocked --not-blocked --unclaimed` triple does:**

- `--unblocked` → all `depends_on` tasks at terminal status (done or archived). **= Gate 2.**
- `--not-blocked` → no explicit `--block` flag set. These flags are orthogonal — see
  kanban-md skill Pitfalls.
- `--unclaimed` → not claimed, or claim expired per `claim_timeout` in `config.yml`.
  **= Gate 6.** Never manually inspect `claimed_by`/`claimed_at` timestamps — this
  flag handles claim expiry server-side.

**What the PowerShell layer adds:**

- Dual-key sort: priority rank (critical first) → pipeline proximity (done first,
  ideation last). **= Step 5 ordering.**
- `TW:MISSING` flag: `in-progress` task without `## Test-Writer Notes`. **= Gate 4.**
  Exempt: tasks tagged with any non-impl pass-through tag (`research`, `docs`, `type:config`,
  `type:docs`, `test`, `type:test`, `agent`, `quality`) — these tasks pass through the
  test-writer without tests, so missing notes indicate a TW skip, not a pipeline violation.
- `AC:MISSING` flag: `todo+` task without bullet (`- `) or numbered (`1. `) AC items.
  **= Gate 5.** Not flagged for ideation/backlog — those tasks don't need AC yet
  (the researcher/architect adds it).
- Tags inline for scope/category context.
- `ARCH:REVIEWED` flag: task body contains `## Architecture Review` section. **= Gate 3 exemption.** Tasks with this marker have already had atomicity evaluated by the architect.

**What remains for LLM reasoning (no terminal commands needed):**

- Gate 3 (atomicity): scan titles for "and" joining unrelated concerns — skip for tasks marked `[!ARCH:REVIEWED]` (architect already evaluated atomicity).
- DECOMP routing: tasks flagged `[!DECOMP]` dispatch to `kanban-planner` regardless of status.
- 20-task dispatch cap: take top entries from the already-sorted list.
- Stale-task handling: cross-reference orchestrator failure context with output.

**Scope translation** — replace `{scope}` with flags from the orchestrator:

| Orchestrator scope | Substitute for `{scope}` |
| ------------------ | ------------------------ |
| `"tag:phase-3"`    | `--tag phase-3`          |
| `"all"` or omitted | _(nothing — the default `--status` covers all active statuses)_ |

### Recipe 2 — Stale-task body read

**Conditional.** Run only when the orchestrator reports first-stale tasks that need a
`retry_hint`. Read the last agent note section to extract a ≤120 char summary:

```powershell
foreach ($id in {stale_ids}) { "===TASK $id==="; kanban\kanban-md.exe show $id; "===END===" }
```

### Terminal call budget

| Scenario | Calls | Notes |
| -------- | ----- | ----- |
| Normal cycle | 1–2 | Recipe 0 + Recipe 1 |
| With stale tasks | 2–3 | + Recipe 2 for retry_hint extraction |
| Previous approach | 20+ | Individual `show` calls, foreach loops, `rg` on files |

## Step 1 — Receive scope and scan board

The orchestrator passes a scope filter and optional failure context from the previous
cycle.

### Check pending decision and action requests

Run **Recipe 0** (Decision and action requests). Process any resolved requests before
scanning. Recipe 0 distinguishes T2 (auto-resolvable after 5 days when `impact_tier` is
2 or absent) from T3 (permanently pending — `impact_tier: 3` decisions skip the 5-day
timer and require explicit user approval). Count unresolved files by tier for the
`pending` field in the JSON output.

### Board Scan

Run **Recipe 1** (Board Scan) with the orchestrator's scope filter substituted for
`{scope}`. This single command produces the full candidate list — sorted by priority
and pipeline proximity, with gate markers for Gates 2, 4, 5, and 6 already applied.

If the scan returns `(empty)`, output `{"dispatch":[]}` and stop.

**Failure context:** If the orchestrator reports tasks that failed in the previous cycle,
note them. Failures come in two flavors:

- **Crash failures:** Agent crashed twice. Note the ID — these tasks are dispatched
  normally (the planner does not special-case them beyond awareness).
- **Stale-retried IDs:** Tasks that were dispatched with a `retry_hint` last cycle but
  still haven't moved. If a task appears in `stale_retried` AND is still in the Board
  Scan output at the same status, it has failed twice — **block it** with reason
  `STALE — retried with hint, still unchanged`.

**First-stale detection (guided retry):** If a task appears at the same status it was
dispatched from last cycle (it hasn't moved) and is NOT in the `stale_retried` list from
the prior cycle, it is first-stale. Instead of blocking it immediately:

1. Run **Recipe 2** (Stale-task body read) for the stale task IDs.
2. Find the **last** agent note section — look for the final occurrence of any of these
   headings: `## Builder Notes`, `## Review Evidence`, `## Test-Writer Notes`,
   `## Audit`, or `## Handoff`.
3. Extract a single-line summary (≤120 chars) of the prior failure from that section.
   Focus on what went wrong or what blocked progress.
4. Include the task in `dispatch` with a `retry_hint` field containing that summary.

The orchestrator tracks which tasks were retried with hints (`stale_retried` IDs) and
passes them back next cycle. If the task is still stale after the retry, the planner
blocks it on the second cycle.

## Step 2 — Apply gates and build dispatch list

Parse the Board Scan output from Step 1. Each line is a candidate task. The scan has
already applied Gates 2 and 6 via server-side filters, and flagged Gates 4 and 5 via
markers. Apply the remaining gates and build the dispatch list.

### Gate checks

All tasks in the Board Scan output have already passed Gates 2 and 6. Check the
remaining gates on each candidate:

**Gate 1 — Status gate:**
Task status must match a dispatchable status in the agent dispatch mapping above.
All statuses in the mapping are dispatchable. _(Always passes for Board Scan output
since the `--status` filter enforces this.)_

**Gate 2 — Dependency gate:** ✅ **Handled by Board Scan.**
The `--unblocked` flag ensures all `depends_on` tasks are at terminal status (done or
archived). No manual dependency checking needed.

**Gate 3 — Atomicity gate:**
Title describes a single responsibility. Red flag: the word "and" joining unrelated
concerns (e.g., "Implement parser and update config"). Related concerns joined by "and"
are fine (e.g., "Read board and build DAG" — both are planning sub-steps).
**Exemption:** Tasks marked `[!ARCH:REVIEWED]` in the Board Scan output are exempt from
this heuristic — the architect already evaluated atomicity during backlog review.

**Gate 4 — TDD gate (safety net):**
Check the Board Scan output for `[!TW:MISSING]` marker. This appears on `in-progress`
tasks whose body lacks `## Test-Writer Notes`. If the marker is present → exclude the
task from dispatch (it reached `in-progress` without proper test-writer processing).
As a fallback, a linked test task in `done` status also satisfies this gate.
**Exemption:** Tasks tagged with any non-impl pass-through tag (`research`, `docs`,
`type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`) are exempt from
this gate — they pass through the test-writer without tests, so missing notes indicate
a TW skip, not a pipeline violation.

**Gate 5 — Clarity gate:**
Check the Board Scan output for `[!AC:MISSING]` marker. This appears on `todo+` tasks
whose body lacks bullet (`- `) or numbered (`1. `) acceptance criteria. If the marker
is present → exclude the task from dispatch.
This gate does NOT apply to `ideation` or `backlog` tasks — those don't need AC yet
(the researcher/architect adds it during their pipeline stage).

**Gate 6 — Claim gate:** ✅ **Handled by Board Scan.**
The `--unclaimed` flag excludes tasks with active claims. It respects `claim_timeout`
from `kanban/config.yml` — claims older than the timeout are treated as expired and DO
appear in the scan. Never manually inspect `claimed_by`/`claimed_at` fields.

### Gate failure remediation

For each task excluded by **Gate 3** (atomicity) or **Gate 4** (TDD), record a
`gate_warnings` entry. Gate 5 is excluded from this collection — its failures are
content gaps (missing AC), not process violations, and populating warnings for every
incomplete task would produce false-positive noise.

**Format:**

```json
{"id": 102, "gate": "Gate 3", "reason": "Title contains 'and' joining unrelated concerns: implement parser and update config"}
```

**Fields:**

- `id` — task ID (int)
- `gate` — one of `"Gate 3"` or `"Gate 4"` (string)
- `reason` — short description of why the gate failed (string, ≤ 120 chars)

`gate_warnings` is always emitted — use an empty array when no Gate 3/4 exclusions
occurred. This keeps the planner stateless: the orchestrator receives a deterministic
signal every cycle without needing to diff board state.

**Rejected alternative — auto-move back:**
Auto-moving failed tasks to an earlier status was considered but rejected. It creates
feedback loops (tasks could oscillate between statuses), violates the planner's
read-only constraint (the planner never mutates board state), and adds remediation
complexity outside the planner's responsibility. Gate failures are surfaced as warnings
only; human or orchestrator decides how to act on them.

### Filter and prioritize

From the gate-passing tasks, build the dispatch list:

1. **Priority ordering:** The Board Scan output is already sorted by: (1) priority rank
   (critical → someday), (2) pipeline proximity (done → ideation). Take tasks in the
   order they appear.

2. **Batch size cap:** Max 20 tasks per dispatch list. If more qualify, take the top 20
   from the sorted list. The rest are silently deferred to the next planning cycle.

**No deconfliction needed.** The planner produces a priority-sorted flat list. The
orchestrator handles parallel batching and agent-type compatibility when grouping tasks
into concurrent dispatches — the planner does not need to know about batching strategy.

## Step 3 — Output JSON plan

Produce JSON as the final response. No prose preamble, no narrative, no markdown tables.

Format (with gate failures):

```json
{"dispatch":[{"id":101,"agent":"architect"},{"id":103,"agent":"builder","retry_hint":"Review FAIL: missing coverage on parser module"}],"gate_warnings":[{"id":102,"gate":"Gate 3","reason":"Title has unrelated concerns joined by 'and'"}],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}
```

Format (no gate failures):

```json
{"dispatch":[{"id":101,"agent":"architect"}],"gate_warnings":[],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}
```

<good example why="Single-line JSON object with `dispatch` and `gate_warnings` fields. Agent names from mapping.">
{"dispatch":[{"id":849,"agent":"architect"},{"id":850,"agent":"researcher"},{"id":854,"agent":"architect"},{"id":851,"agent":"architect"},{"id":843,"agent":"auditor"},{"id":536,"agent":"writer"},{"id":541,"agent":"reviewer"},{"id":549,"agent":"builder"},{"id":544,"agent":"test-writer"},{"id":774,"agent":"architect"},{"id":772,"agent":"architect"},{"id":853,"agent":"architect"}],"gate_warnings":[],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}
</good example>
<bad example why="Includes prose and markdown, not a single-line JSON object.">
```json
excluded the gate failures, and I’m finalizing the capped 20-task dispatch list now.{"dispatch":[{"id":849,"agent":"architect"},{"id":850,"agent":"researcher"},...,{"id":853,"agent":"architect"}]}
```
</bad example>

**Fields:**

- `dispatch` — Array of `{id, agent}` objects. Priority-sorted (highest first).
  Agent name from the dispatch mapping. No AC summary — subagents read their own AC.
  - `retry_hint` (optional string, ≤120 chars) — present only on first-stale tasks
    retried with guided context. Summarizes the prior failure extracted from the task
    body's last agent note section. Omit for normal dispatches.
- `gate_warnings` — Always-present array of `{id, gate, reason}` objects for tasks
  excluded by Gate 3 or Gate 4. Empty array when no failures. Each object: `id` (int),
  `gate` (one of `"Gate 3"` or `"Gate 4"`), `reason` (string, ≤ 120 chars).
- `pending` — Always-present object with counts of unresolved requests from Recipe 0.
  Format: `{"decisions_t2": N, "decisions_t3": N, "actions": N}`. `decisions_t2` = pending
  T2 or untiered decision requests (auto-resolvable after 5 days); `decisions_t3` = pending
  T3 decision requests (never auto-resolve — require explicit user approval); `actions` =
  unresolved action request files. All zero when no pending requests.

**Rules:**

- Output MUST be a single JSON object on one line (no pretty-printing)
- Fields: `dispatch`, `gate_warnings`, and `pending` (all required)
- Empty dispatch array is fine: `{"dispatch":[],"gate_warnings":[],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}`
- Gate names do not appear in `dispatch` entries; gate failures surface only via `gate_warnings`
- If more than 20 tasks pass gates, include only the top 20 by priority

---

## Self-critique checklist

Before outputting:

- [ ] Board Scan (Recipe 1) was used — not individual `show` calls or `rg`/`Get-ChildItem` on task files
- [ ] Board Scan used triple filter `--unblocked --not-blocked --unclaimed` (claim timeout handled by kanban-md)
- [ ] Scope filter from orchestrator was substituted into `{scope}` placeholder
- [ ] No foreach loops over individual `show` calls (batch only via Recipe 2 for stale tasks)
- [ ] Total terminal calls ≤ 3
- [ ] All 6 gate checks accounted for (Gates 2+6 by filter, Gates 4+5 by markers, Gates 1+3 by reasoning)
- [ ] No task with `[!TW:MISSING]` or `[!AC:MISSING]` marker in `dispatch`
- [ ] Batch does not exceed 20 tasks
- [ ] Agent names match the dispatch mapping
- [ ] Failure context from orchestrator was checked for stale tasks and stale_retried IDs
- [ ] First-stale tasks have `retry_hint` extracted from task body; second-stale tasks excluded
- [ ] Recipe 0 checked both `approved: true` (decisions) and `completed: true` (actions); pending counts computed by type
- [ ] Output is a single-line JSON object with `dispatch`, `gate_warnings`, and `pending` fields
- [ ] `gate_warnings` populated for every Gate 3/4 exclusion; empty array if none
- [ ] No prose preamble or narrative in the output
- [ ] No `kanban-md move` commands were run
- [ ] No subagents were dispatched
- [ ] No source/test files were edited
