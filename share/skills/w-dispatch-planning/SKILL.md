---
name: w-dispatch-planning
description: "Workflow (ARCHIVED): Dispatch planning — reference design doc for NON_IMPL_TAGS and agent mapping"
user-invocable: false
---

> **ARCHIVED** — Superseded by pick_tasks MCP tool (#621) and w-orchestration direct integration (#622). Retained as design reference for NON_IMPL_TAGS authoritative list.

# Dispatch Planning

Read the kanban board, classify tasks by status, apply gate checks, and produce a priority-sorted JSON dispatch plan for the orchestrator.

## Agent Dispatch Mapping

The dispatcher assigns agents based on task status:

<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/w-tdd-red/SKILL.md (Step 1 item 3),
     skills/w-arch-review/SKILL.md (non-impl tagging note). -->

| Task status   | Dispatch agent | Pipeline action                                          | Non-impl pass-through? |
| ------------- | -------------- | -------------------------------------------------------- | ---------------------- |
| `research`    | researcher     | Research investigation, move to `backlog`                | No                     |
| `backlog`     | architect      | Architecture review, move to `todo`                      | No                     |
| `todo`        | test-writer    | Write failing tests (RED phase), move to `in-progress`   | Yes — tags `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, `type:user-action` |
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

**Planner dispatch:** When the board scan finds a task whose body contains `Needs decomposition:`, include it in the dispatch list with `"agent": "planner"`. The planner reads the task, decomposes it, and creates child tasks at `research` via `create_task`. The parent task is not moved — the planner creates children and the parent may be closed or split.

## Recipe 0 — Decision and Action Request Resolution

The **orchestrator** calls the scribe in resolve mode before invoking the dispatcher (see `w-orchestration` Step 0). By the time the dispatcher runs, all resolved DRs have been written to task bodies and tasks unblocked.

Scan `.owlbear/decisions/pending/` (excluding `.gitkeep`) to compute the `pending` output field:

```powershell
Get-ChildItem .owlbear/decisions/pending/*.md -EA SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' }
```

For each pending file, read frontmatter to classify: T2 (`impact_tier` 2 or absent — auto-resolvable after 5 days), T3 (`impact_tier: 3` — require explicit approval, never auto-resolve), or action request. Count by type for the `pending` output field.

## Recipe 1 — Board Scan

**One MCP call.** Produces a classified, sorted, gate-checked candidate list.

Call `list_tasks(status=["research","backlog","todo","in-progress","review","docs","done"], unblocked=true, unclaimed=true)`. The `unblocked=true` parameter excludes tasks where any `depends_on` dependency is not at terminal status (= Gate 2). The `unclaimed=true` parameter excludes currently claimed tasks (= Gate 6). Explicitly blocked tasks are excluded by the server automatically.

If the response is empty, output `{"dispatch":[]}` and stop.

**Sort** the returned array by dual-key: priority rank (critical=0, needed=1, important=2, nice-to-have=3, someday=4) first, then pipeline proximity (done=0, docs=1, review=2, in-progress=3, todo=4, backlog=5, research=6).

**Gate flags** — for each task, compute warning flags:

<!-- NON_IMPL_TAGS — authoritative list -->
- `TW:MISSING` — status is `in-progress`, body lacks `## Test-Writer Notes` section, and task has none of the non-impl pass-through tags: `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, `type:user-action`
- `AC:MISSING` — status is `todo`, `in-progress`, `review`, `docs`, or `done`, and body contains no bullet lines (lines starting `-` or `N.`)
- `DECOMP` — body contains `Needs decomposition:`
- `ARCH:REVIEWED` — body contains `## Architecture Review`

**Output each task as one line:** `#{id} {status}/{priority} {title} ({tags}) [!{flags}]` — omit `({tags})` if no tags, omit `[!{flags}]` if no flags. Finish with `---` and `N candidates`.

**Scope translation** — add `tag="{tag}"` parameter per orchestrator input:

| Orchestrator scope | Add parameter   |
| ------------------ | --------------- |
| `"tag:phase-3"`    | `tag="phase-3"` |
| `"all"` or omitted | _(nothing)_     |

## Recipe 2 — Stale-Task Body Read

**Conditional.** Run only when the orchestrator reports first-stale tasks needing a `retry_hint`:

Call `show_task(task_id="{id}")` for each stale task ID.

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

**Gate 2 — Dependency gate:** Handled by `unblocked=true` parameter.

**Gate 3 — Atomicity gate:** Title describes a single responsibility. Red flag: "and" joining unrelated concerns. **Exemption:** tasks marked `[!ARCH:REVIEWED]`.

**Gate 4 — TDD gate:** `[!TW:MISSING]` marker present = exclude. **Exemption:** tasks with non-impl pass-through tags.

**Gate 5 — Clarity gate:** `[!AC:MISSING]` marker = exclude. Does not apply to `research` or `backlog`.

**Gate 6 — Claim gate:** Handled by `unclaimed=true` parameter.

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

- [ ] Board scan used `unblocked=true, unclaimed=true` parameters (no manual dependency or claim checking)
- [ ] All 6 gates evaluated (4 automated, 2 manual)
- [ ] Dispatch list respects 20-task cap
- [ ] DECOMP tasks routed to planner, not status-based agent
- [ ] JSON output is single-line with no prose preamble
- [ ] `pending` field includes DR counts by tier
- [ ] Stale tasks handled: first-stale gets `retry_hint`, second-stale gets blocked
- [ ] Agent names match the dispatch mapping table

## Known Pitfalls

- **`unblocked` vs `unclaimed` parameters:** `unblocked=true` filters to tasks where all `depends_on` dependencies are at terminal status (Gate 2). `unclaimed=true` excludes currently claimed tasks (Gate 6). Both are required — omitting either passes tasks that should be gate-blocked.
- **Non-impl tag Gate 4 exemption:** Tasks with pass-through tags legitimately skip the test-writer. Missing `## Test-Writer Notes` on these tasks is expected, not a gate violation.
- **`AC:MISSING` on research/backlog:** These statuses don't need AC yet — the researcher/architect adds it. Don't flag them.
