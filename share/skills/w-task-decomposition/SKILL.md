---
name: w-task-decomposition
description: "Workflow: Task decomposition — shaper-owned decomposition into atomic child tasks with dependency graphs"
user-invocable: false
---

# Task Decomposition

Break complex shape work into atomic kanban child tasks with explicit dependency graphs, parent intent preservation, and collector-ready aggregate gates.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Break features into atomic tasks.
- Draft AC using `h-ac-quality` rules.
- Assign priorities and dependency graphs.
- Route build-ready child tasks directly to `build`; leave only unresolved shaping work at `shape`.
- Preserve parent/EPIC intent or Brief links so collector can verify aggregate fulfillment later.

### Out of Scope

- Shape approval — shaper.
- Implementation — builder.
- Verification — verifier.
- Creating mandatory test-only pairs.

## Step 0 — Setup

Read `h-ac-quality` skill and use it as the authoritative AC validation checklist while drafting task acceptance criteria.

Use this workflow after shaper has claimed the parent task with `start_work`. `start_work` returns the task body, making a separate `show_task` call redundant. If `start_work` fails, stop; a `ToolError` means the task is blocked, already claimed, or missing.

**Knowledge pre-flight:** After claiming, call `recall_memory(agent="shaper")` to load reviewed entries. Apply returned entries as context. If the call fails or returns empty, proceed normally.

**Execution mode:** Shaper owns decomposition directly. Create child tasks only after material user decisions are resolved; do not ask for approval on purely mechanical splitting when the parent intent and constraints are already clear.

## Step 1 — Read the Plan

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

If the parent task body contains a `## Brief` or `## Problem` section (Brief artifact, produced by ideation), use it to derive scope, investment tier, and approach constraints for decomposition. Include `Brief: see parent #{id}` reference in each child task body.

When the parent contains an approved ideation Brief, shaper sequences or splits Brief requirements but does not delete them. If a Brief requirement cannot fit one atomic task, split it across tasks. If a Brief requirement appears invalid, conflicting, or impossible, surface that conflict in Shape Notes instead of dropping the requirement.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 1a — Single-Task Shortcut

Before decomposition, detect whether the request is exactly one follow-up task with no dependency graph or multi-domain split required.

If yes, use the shortcut flow:

- Skip Step 1b, Steps 2–4, and Step 7.
- Continue with Steps 5, 5a, and 6.
- Preserve parent metadata where provided: title, parent ID, and tags.
- Status routing: create build-ready tasks with `status="build"`; use `shape` only when the follow-up still needs shaping. Normalize old `todo`, `backlog`, `research`, `in-progress`, `review`, `docs`, and `done` requests to `build` only after shaping makes the task build-ready.
- Naming: no phase-based `P{phase}-{nn}` prefix in shortcut mode. Use the parent-provided title directly.
- TDD pairing is not used.
- Return the created task ID explicitly in your response message (for downstream linking and parent-child follow-up operations).

Typical shortcut cases: "fix off-by-one", "delete stale docs", "shaper calibration".

## Step 1b — Source-Read & Symbol Capture Guard

Apply this step when the input plan, parent task, or brief references existing codebase modules or symbols that will appear in AC text.

This step may be skipped only for greenfield requests with no existing code references.

1. Identify target source files from parent context (plan text, parent task, brief, or referenced module paths).
2. Read each target source file before drafting AC.
3. Extract and record referenced symbols that may be cited in AC text:
    - function signatures and return types
    - enum or union values
    - component names
    - token names
4. During AC drafting, cross-check each AC line against the recorded symbols.
5. If an AC references a function return type, enum value, or component/token name, ensure it exactly matches the source-defined symbol.

Do not continue to Step 2 until this guard is complete when triggered.

### good_example — symbol guard applied

- Parent task references `computeSignal` and card status enums in an existing UI module.
- Shaper reads the module first, records `computeSignal(...): CardSignal` and `CardSignal = "dr-pending" | "blocked" | "claimed" | "deps-unmet" | "ready" | "unknown"`.
- Shaper drafts AC lines that use only those exact symbols and values.

### bad_example — source-read skipped

- Shaper drafts AC from memory and writes `computeSignal` returns an object with `state`.
- Shaper also lists statuses as `green/yellow/red/gray/stale`.
- AC is factually incorrect because symbol references were not validated against source.

## Step 2 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

## Step 3 — Decompose into Atomic Tasks

Each task must be:

- **Single responsibility:** one module, one function, one config
- **Domain scoped:** one primary domain per task (see `r-architecture-standards` domain taxonomy). Multi-domain tasks must be split.
- **Testable:** clear pass/fail criterion
- **Small:** ~2 hours of focused work max
- **Self-contained proof:** each task names the proof mode the builder/verifier should use, but does not require a separate test-writing task.

### Task Complexity Budget

Draft tasks to fit this budget before creating them:

- **AC target:** 3 acceptance criteria or fewer.
- **AC hard cap:** 5 acceptance criteria. If a task needs more, split it.
- **High-proof budget:** at most 2 AC lines that likely require multi-case proof, browser/runtime proof, concurrency proof, rollback proof, migration proof, or broad downstream-impact proof.
- **Proof-mode budget:** one primary proof mode per task. Split when a task needs more than one of: unit/static proof, integration proof, E2E/browser proof, data-safety/rollback proof, migration/downstream regression proof.
- **Failure-domain budget:** one failure-domain family per task. Split algorithm changes, config semantics, persistence, event/activity logging, rollback/atomicity, UI layout, accessibility, and documentation into separate tasks unless one is a trivial consequence of the other.

Use an explicit `Complexity waiver:` note only when splitting would make the work less verifiable. The waiver must name the budget exceeded and why the task is still expected to finish inside one pipeline pass.

### Mandatory Split Triggers

Split the planned task when any trigger applies:

- More than 5 AC lines, or more than 3 AC lines with broad surface words such as "dashboard", "coherent experience", "end-to-end", or "all surfaces".
- More than 2 likely high-proof AC lines.
- More than one primary proof mode is needed.
- More than one failure-domain family is present.
- A proof artifact would be created only in `.owlbear/scratch/`, or the responsible agent cannot write the final tracked location. Create a separate builder-owned promotion/proof task with a concrete tracked deliverable, or choose a proof path the responsible agent can own.
- A behavior-changing refactor changes existing semantics used by neighboring durable tests. Add a downstream-impact scan to the task body, or split the migration/update work into its own task.
- An AC line combines behavior plus safety recovery, such as success-path emission and rollback-on-emit-failure. Split success behavior from failure recovery unless the recovery proof is one small smoke assertion.

Ordering heuristic:

1. Model/schema tasks first (data structures)
2. Shared model/schema tasks before callers
3. Integration proof after unit components
4. CLI/UI tasks last (depend on core logic)

## Durability Principles

When drafting AC for planned tasks:

- Validate each AC block against `h-ac-quality` (authoritative checklist) before task creation.
- Apply the Task Complexity Budget before AC quality validation; clear wording does not make an oversized task acceptable.
- AC defines behaviors and interfaces, not file paths or implementation details.
- File paths are allowed for proof artifacts or process deliverables when the path itself is the acceptance surface; avoid prescribing production implementation locations.
- AC must be understandable without reading the codebase first.
- Every task must include explicit scope boundaries (in-scope and out-of-scope).
- No implementation prescriptions: describe WHAT must be true, not HOW to code it.

## Step 4 — Build Dependency Graph

Build an explicit dependency graph:

- Shape/context tasks depend on nothing (or prior schema)
- Implementation tasks depend on prerequisite shape/context tasks when they exist
- Schema, CRUD, agent, CLI layers form a natural hierarchy
- Cross-phase dependencies only when strictly necessary
- Every dependency references a concrete task ID
- Do not create ceremonial test → implementation dependency chains

## Step 5 — Assign Priority and Tags

- **Priority:** count dependents (`high` if 3+, `medium` if 1-2, `low` otherwise)
- **Tags (decomposition mode):** always `phase-{n}` + `scope:{domain}` + at least one category tag
- **Tags (shortcut mode):** preserve parent-provided tags verbatim; do not add phase tags unless they are already part of the parent scope

See `r-project-standards` for the full priority scheme and tag taxonomy.

## Step 5c — Assign Proof Guidance

Add a short `Proof guidance:` line to each task body. This is guidance for builder/verifier, not a routing field.

| Signal | Guidance |
|--------|----------|
| Docs/process-only change with no executable behavior change | `no executable proof expected; cite changed artifact` |
| Change validated by pre-existing named checks | `run named focused check: {command}` |
| Narrow behavior change | `run focused behavior check or import/config smoke` |
| Shared/core-path change | `run focused check plus downstream-impact scan` |
| UI/browser change | `run package-local frontend check; add screenshot only if visual framing matters` |

## Step 5a — Validate Planned Tasks

Before creating any task, validate every planned task:

- **Reject `TEMP-*` titles** — placeholder artifacts, not legitimate tasks.
- **Reject empty bodies** — no AC or scoped content means the task is invalid.
- **Reject oversized tasks** — no task may exceed the Task Complexity Budget unless it has a `Complexity waiver:` note.
- **Reject scratch-only proof** — if required proof can only live in `.owlbear/scratch/`, split or add a tracked-artifact deliverable owned by an agent that can write it.
- **Reject hidden downstream impact** — behavior-changing refactors must name affected durable suites/consumers or include a downstream-impact scan task.
- **Reject proof-artifact-only tasks unless the artifact itself is the product deliverable** — proof should support the change, not become a fake task.

If a planned task fails: refine the title and body or stop. Never create a placeholder task.

## Step 5b — User Decision Gate

Ask the user only for material product, architecture, scope, or trade-off choices. Do not ask for approval on mechanical decomposition when the parent intent, constraints, and dependencies are already clear.

When a material choice exists, present exactly one decision item with status quo, problem, options with pros/cons/risks/confidence, recommendation, and expected outcome. On approval, revise the planned tasks and proceed to Step 6. On rejection or unresolved scope, stop without creating tasks and leave the parent in `shape` or block it through `create_request` per `r-pipeline-protocol`.

## Step 6 — Create Tasks

**Decomposition naming convention only:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

**Shortcut naming:** preserve the parent-provided title verbatim (no phase prefix).

Create each build-ready child via `create_task` with title, `status="build"`, priority, tags, depends_on, `ac`, body (supporting context including `Proof guidance:`), and `parent={parent_id}`. Use `status="shape"` only for a child whose scope still requires later shaping.

Do not create consolidation-test tasks automatically. If aggregate verification is needed, express it as parent/EPIC collect criteria or a normal shaped task with its own product-facing purpose.

**Parent completion gate:** For parent/EPIC decomposition, create or route the aggregate parent at `collect` after adding all required child IDs as dependencies via `edit_task(id={parent_id}, add_dep=[...])`. This parks the parent behind child completion; dependency filtering keeps collector from receiving the parent while any required child is still active.

Group by dependency layer (independent first, then dependents). Record created task IDs for the report.

In shortcut mode, report the created task ID as a top-level result line (for example, `Created follow-up task: #{id}`).

Include the planning summary in the parent task's `end_work` note.

## Step 7 — Visualize Dependencies

Produce a Mermaid diagram showing task relationships. Arrows: dependency toward dependent.

## Step 8 — Advance

**Post-task reflection:** Before advancing, write 3-5 bullets on problems faced, workarounds applied, patterns discovered. Skip if nothing notable. Use `save_memory(title=..., content=..., categories=[...], confidence=0.8, source_agent="shaper")` for each notable finding.

For aggregate parent/EPIC tasks with no direct implementation work, put the parent in `collect` after child dependencies are attached. If creating a new aggregate parent, pass `status="collect"` to `create_task`; if shaping an existing parent, use `end_work(outcome="success", move_to="collect")`. For a parent that still owns direct implementation AC, create build-ready children instead of sending the aggregate parent to build.

Return Channel A using shaper's normal verdict format: `APPROVED #{id} -> collect` for aggregate parents parked behind children, `APPROVED #{id} -> build` for directly buildable parents, or `REFINE` / `BLOCK` when decomposition exposes unresolved scope or decisions.

## Output Template

Append decomposition details inside shaper's `## Shape Notes` section:

```
### Decomposition: {name}
- Tasks created: {N}
- Dependency layers: {M}
- Phase: {phase}

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| {id} | {title} | {priority} | {deps} | {tags} |

### Dependency Graph
{Mermaid diagram}
```

## Verification Checklist

- [ ] Announced decomposition plan and expected count
- [ ] Every task has proportional proof guidance
- [ ] No task has multiple responsibilities
- [ ] Every task fits the Task Complexity Budget or has a `Complexity waiver:` note
- [ ] No task mixes multiple proof modes without being split
- [ ] No task mixes multiple failure-domain families without being split
- [ ] Refactor tasks name downstream-impact scope or create a separate scan/update task
- [ ] Sequence numbers unique and zero-padded (decomposition mode only)
- [ ] Priority reflects blocking potential
- [ ] Tags include `phase-{n}` + category (decomposition mode only)
- [ ] No cycles in dependency graph
- [ ] Parent task has `depends_on` pointing to required children when it is an aggregate/EPIC gate
- [ ] Mermaid diagram matches task list (decomposition mode only)
- [ ] Total 20 tasks or fewer
- [ ] AC describes "done", not "how"
- [ ] AC meets durability principles (behavior/interface-first, codebase-independent clarity, explicit scope boundaries, no HOW prescriptions)
- [ ] Shortcut mode returns created task ID in response message
- [ ] No `TEMP-*` titles or empty bodies created

## Known Pitfalls

- **Creating proof-only tasks:** Do not create test-only/proof-only tasks unless the proof artifact is itself the product deliverable.
- **Cross-phase dependencies:** These create long dependency chains that block parallelism. Use only when strictly necessary.
- **Placeholder tasks:** Never create tasks with vague titles or empty bodies — they accumulate as board noise.
- **Broad AC piles:** Many clear AC lines can still create an unclear task when they require different proof modes or failure domains. Split by proof burden, not just by wording quality.
- **Scratch-only proof:** A scratch artifact is not a durable acceptance deliverable. Plan a tracked proof location and responsible owner before task creation.
- **Body content in `create_task`:** Keep AC concise. For complex multi-line AC, use the temp-file pattern (see `h-mcp-kanban`).
