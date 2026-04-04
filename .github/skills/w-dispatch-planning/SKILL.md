---
name: w-dispatch-planning
description: "Workflow: Dispatch planning — read board, build DAG, gate checks, produce dispatch plan"
user-invocable: false
---

# Dispatch Planning

Read the kanban board, classify tasks by status, apply gate checks, and produce a priority-sorted JSON dispatch plan for the orchestrator.

## Agent Dispatch Mapping

The dispatcher assigns agents based on task status:

<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/w-tdd-red/SKILL.md (Step 1 item 3),
     skills/w-arch-review/SKILL.md (non-impl tagging note). -->

| Task status   | Dispatch agent | Pipeline action                                          | Non-impl pass-through? |
| ------------- | -------------- | -------------------------------------------------------- | ---------------------- |
| `ideation`    | researcher     | Research investigation, move to `backlog`                | No                     |
| `backlog`     | architect      | Architecture review, move to `todo`                      | No                     |
| `todo`        | test-writer    | Write failing tests (RED phase), move to `in-progress`   | Yes — tags `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality` |
| `in-progress` | builder        | GREEN phase, move to `review`                            | Yes — if test-writer passed through |
| `review`      | reviewer       | Quality verification, move to `docs`                     | No                     |
| `docs`        | doc-writer     | Documentation gate, move to `done`                       | No                     |
| `done`        | auditor        | Exit gate verification, archive                          | No                     |

**Non-implementation tasks:** Tasks tagged with pass-through tags still flow through the standard pipeline. The test-writer recognizes them and passes through without writing tests (see `w-tdd-red` Step 1a). The architect is responsible for tagging tasks correctly during backlog approval.

### Non-Status-Triggered Agents

| Agent   | Trigger condition                                                              | Dispatched by |
| ------- | ------------------------------------------------------------------------------ | ------------- |
| planner | Task body contains "Needs decomposition" (set by architect or any agent), OR user explicitly requests it | Dispatcher includes in dispatch list |
| curator | Every 5th orchestration cycle (periodic, see `w-orchestration` Step 2)         | Orchestrator directly (not via dispatcher) |

**Planner dispatch:** When the board scan finds a task whose body contains `Needs decomposition:`, include it in the dispatch list with `"agent": "planner"`. The planner reads the task, decomposes it, and creates child tasks at `ideation` via `create_task`. The parent task is not moved — the planner creates children and the parent may be closed or split.

## Recipe 0 — Decision and Action Request Resolution

The **orchestrator** calls the scribe in resolve mode before invoking the dispatcher (see `w-orchestration` Step 0). By the time the dispatcher runs, all resolved DRs have been written to task bodies and tasks unblocked.

Scan `docs/decisions/pending/` (excluding `.gitkeep`) to compute the `pending` output field:

```powershell
Get-ChildItem docs/decisions/pending/*.md -EA SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' }
```

For each pending file, read frontmatter to classify: T2 (`impact_tier` 2 or absent — auto-resolvable after 5 days), T3 (`impact_tier: 3` — require explicit approval, never auto-resolve), or action request. Count by type for the `pending` output field.

## Recipe 1 — Board Scan

**One terminal call.** Produces a classified, sorted, gate-checked candidate list.

```powershell
$pr=@{critical=0;needed=1;important=2;'nice-to-have'=3;someday=4}
$sr=@{done=0;docs=1;review=2;'in-progress'=3;todo=4;backlog=5;ideation=6}
$raw = kanban\kanban-md.exe list --json --unblocked --not-blocked --unclaimed `
  --status ideation,backlog,todo,in-progress,review,docs,done {scope} 2>&1 | Out-String
$tasks = $raw | ConvertFrom-Json
if (-not $tasks) { '(empty)'; return }
$tasks | Sort-Object {$pr[$_.priority]},{$sr[$_.status]} | ForEach-Object {
  $w=@()
  # NON_IMPL_TAGS — authoritative list
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

> **MCP equivalent:** `list_tasks(status=["ideation","backlog","todo","in-progress","review","docs","done"], unblocked=true, unclaimed=true)` — returns the same candidate set via MCP.

**What the `--unblocked --not-blocked --unclaimed` triple does:**

- `--unblocked`: all `depends_on` tasks at terminal status (= Gate 2)
- `--not-blocked`: no explicit block flag set (orthogonal to `--unblocked`)
- `--unclaimed`: not claimed or claim expired per `claim_timeout` in config (= Gate 6)

**What the PowerShell layer adds:**

- Dual-key sort: priority rank (critical first), then pipeline proximity (done first)
- `TW:MISSING` = Gate 4 violation
- `AC:MISSING` = Gate 5 violation
- `ARCH:REVIEWED` = Gate 3 exemption
- Tags inline for scope/category context

**Scope translation** — replace `{scope}` per orchestrator input:

| Orchestrator scope | Substitute |
| ------------------ | ---------- |
| `"tag:phase-3"`    | `--tag phase-3` |
| `"all"` or omitted | _(nothing)_ |

## Recipe 2 — Stale-Task Body Read

**Conditional.** Run only when the orchestrator reports first-stale tasks needing a `retry_hint`:

```powershell
foreach ($id in {stale_ids}) { "===TASK $id==="; kanban\kanban-md.exe show $id; "===END===" }
```

> **MCP equivalent:** `show_task(task_id="{id}")` per stale task.

### Terminal Call Budget

| Scenario | Calls |
| -------- | ----- |
| Normal cycle | 1–2 (Recipe 0 + Recipe 1) |
| With stale tasks | 2–3 (+ Recipe 2) |

## Step 1 — Receive Scope and Scan Board

The orchestrator passes a scope filter and optional failure context.

1. Run **Recipe 0** — count pending DRs by tier.
2. Run **Recipe 1** with the scope filter substituted. If empty, output `{"dispatch":[]}` and stop.
3. **Failure context:** Note crash failures and stale-retried IDs from the orchestrator.
4. **First-stale detection:** If a task appears at the same status it was dispatched from last cycle and is NOT in `stale_retried`:
   - Run **Recipe 2** to read task bodies.
   - Extract a single-line summary (120 chars max) from the last agent note section.
   - Include in dispatch with a `retry_hint` field.

## Step 2 — Apply Gates and Build Dispatch List

Parse board scan output. Gates 2 and 6 are already applied by server-side filters.

**Gate 1 — Status gate:** Status must match the agent dispatch mapping. Always passes for board scan output.

**Gate 2 — Dependency gate:** Handled by `--unblocked`.

**Gate 3 — Atomicity gate:** Title describes a single responsibility. Red flag: "and" joining unrelated concerns. **Exemption:** tasks marked `[!ARCH:REVIEWED]`.

**Gate 4 — TDD gate:** `[!TW:MISSING]` marker present = exclude. **Exemption:** tasks with non-impl pass-through tags.

**Gate 5 — Clarity gate:** `[!AC:MISSING]` marker = exclude. Does not apply to `ideation` or `backlog`.

**Gate 6 — Claim gate:** Handled by `--unclaimed`.

### Gate Failure Remediation

Record `gate_warnings` entries for Gate 3 and Gate 4 failures. No auto-moving — failures are surfaced as warnings only.

### Filter and Prioritize

Board scan output is pre-sorted. Take up to 20 tasks in order. Remainder deferred to next cycle.

## Step 3 — Output JSON Plan

Produce JSON as the final response. No prose, no markdown.

```json
{"dispatch":[{"id":101,"agent":"architect"},{"id":103,"agent":"builder","retry_hint":"Review FAIL: missing coverage"}],"gate_warnings":[{"id":102,"gate":"Gate 3","reason":"Unrelated concerns joined by 'and'"}],"pending":{"decisions_t2":0,"decisions_t3":0,"actions":0}}
```

## Output Template

Single-line JSON object:

```json
{"dispatch":[{"id":ID,"agent":"AGENT"}],"gate_warnings":[{"id":ID,"gate":"GATE","reason":"WHY"}],"pending":{"decisions_t2":N,"decisions_t3":N,"actions":N}}
```

## Verification Checklist

- [ ] Board scan used `--unblocked --not-blocked --unclaimed` triple (no manual dependency checking)
- [ ] All 6 gates evaluated (4 automated, 2 manual)
- [ ] Dispatch list respects 20-task cap
- [ ] DECOMP tasks routed to planner, not status-based agent
- [ ] JSON output is single-line with no prose preamble
- [ ] `pending` field includes DR counts by tier
- [ ] Stale tasks handled: first-stale gets `retry_hint`, second-stale gets blocked
- [ ] Agent names match the dispatch mapping table

## Known Pitfalls

- **`--unblocked` vs `--not-blocked`:** These are orthogonal flags. `--unblocked` checks `depends_on` resolution; `--not-blocked` checks the explicit block flag. Both are needed.
- **Non-impl tag Gate 4 exemption:** Tasks with pass-through tags legitimately skip the test-writer. Missing `## Test-Writer Notes` on these tasks is expected, not a gate violation.
- **`AC:MISSING` on ideation/backlog:** These statuses don't need AC yet — the researcher/architect adds it. Don't flag them.
- **Body content parsing in PowerShell:** Avoid `->` arrows and `--flag` patterns in any body text — they get parsed as CLI fragments.
