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
- Route build-ready child tasks directly to `build`; do not create `shape` staging tasks.
- Preserve parent/EPIC intent or Brief links so collector can verify aggregate fulfillment later.

### Out of Scope

- Shape approval — shaper.
- Implementation — builder.
- Verification — verifier.
- Creating mandatory test-only pairs.

## Step 0 — Setup

Read `h-ac-quality` skill and use it as the authoritative AC validation checklist while drafting task acceptance criteria.

Use this workflow after shaper has claimed the parent task with `start_work` when a parent task ID exists. `start_work` returns the task body, making a separate `show_task` call redundant. If `start_work` fails, stop; a `ToolError` means the task is blocked, already claimed, or missing. For free-text ideas with no parent task ID, do not create a temporary `shape` task; shape the idea directly into routed outputs or stop without board mutation if it remains unresolved.

**Knowledge pre-flight:** After claiming, call `recall_memory(agent="shaper")` to load reviewed entries. Apply returned entries as context. If the call fails or returns empty, proceed normally.

**Execution mode:** Shaper owns decomposition directly. Create child tasks only after material user decisions are resolved; do not ask for approval on purely mechanical splitting when the parent intent and constraints are already clear.

**Status discipline:** Shaper-created tasks never rely on the `create_task` default. Pass `status="build"` for every build-ready leaf task and `status="collect"` for every aggregate parent/EPIC. `shape` is reserved for user-created intake and tasks rejected back from later pipeline stages.

## Step 1 — Read the Plan

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

If the parent task body contains a `## Brief` or `## Problem` section (Brief artifact, produced by ideation), use it to derive scope, investment tier, and approach constraints for decomposition. Include `Brief: see parent #{id}` reference in each child task body.

When the parent contains an approved ideation Brief, shaper sequences or splits Brief requirements but does not delete them. If a Brief requirement cannot fit one atomic task, split it across tasks. If a Brief requirement appears invalid, conflicting, or impossible, surface that conflict in Shape Notes instead of dropping the requirement.

### Brief Readiness Gate

Before decomposition, confirm the source provides four load-bearing elements:

1. **Product outcome and invocation:** what the user receives and the concrete journey, command,
    endpoint, or interaction that delivers it.
2. **Existing-system fit and authority:** the owning architecture, public interface conventions,
    and canonical sources for external or generated contracts.
3. **Normal-path proof:** the assembled boundary that must work and which lower dependency may be
    replaced without bypassing that boundary.
4. **Completion and change contract:** what makes the work complete and what existing behavior is
    retained, migrated, removed, or explicitly deferred.

For a narrow follow-up, these elements may be established by the existing task and nearby source;
they do not require a formal Brief section. For a multi-domain feature or external integration,
missing material elements are not implementation details. Resolve one material user decision at a
time through Step 5b, or stop without creating tasks. Do not turn an unresolved product or contract
choice into builder discretion.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 1a — Single-Task Shortcut

Before decomposition, detect whether the request is exactly one follow-up task with no dependency graph or multi-domain split required.

If yes, use the shortcut flow:

- If the request is truly greenfield with no existing or external contract, skip Steps 1b, 2–4, and 7.
- If the request touches existing modules, generated interfaces, external contracts, or an approved
    Brief, complete Step 1b, the Change Module Map, and the Deep Module Check before applying the rest
    of the shortcut.
- Continue with Steps 5, 5a, and 6.
- Preserve parent metadata where provided: title, parent ID, and tags.
- Status routing: create build-ready tasks with `status="build"`. If the follow-up still needs shaping, ask/refine instead of creating a `shape` task. Normalize old `todo`, `backlog`, `research`, `in-progress`, `review`, `docs`, and `done` requests to `build` only after shaping makes the task build-ready.
- Naming: no phase-based `P{phase}-{nn}` prefix in shortcut mode. Use the parent-provided title directly.
- TDD pairing is not used.
- Return the created task ID explicitly in your response message (for downstream linking and parent-child follow-up operations).

Typical shortcut cases: "fix off-by-one", "delete stale docs", "shaper calibration".

## Step 1b — Source And Contract Authority Guard

Apply this step when the input plan, parent task, or brief references existing codebase modules,
generated interfaces, external APIs, schemas, protocols, or symbols that will appear in AC text.

This step may be skipped only for greenfield requests with no existing or external contract.

1. Follow `h-project-orientation`. Regenerate the indexes, search them narrowly,
   and identify target source files and contract authorities from parent context. Authorities may
    include generated operation inventories, schemas, official documentation, verified production
    observations, and existing public CLI or API surfaces.
2. Read each local source and the smallest sufficient external evidence before drafting AC.
3. Extract and record referenced symbols and claims that may be cited in AC text:
    - function signatures and return types
    - enum or union values
    - component names
    - token names
    - generated operation or command names
    - external field names and envelope variants
    - observed-versus-assumed behavior
4. Record each load-bearing external claim in `## Shape Notes` with authority, evidence state
    (`observed`, `documented`, or `assumed`), and confidence.
5. During AC drafting, cross-check each literal and behavioral claim against the recorded authority.
6. If a load-bearing claim remains assumed, create a build-ready probe/research prerequisite only
    when its evidence method and tracked output are concrete; otherwise resolve it through the user
    decision gate. Do not create dependent implementation tasks first.
7. If the Brief or requested AC contradicts a canonical source, stop and surface the contradiction.
    Do not invent an alias, fallback, or fixture contract to make both appear true.

Do not continue to Step 2 until this guard is complete when triggered.

### Change Module Map

For brownfield work, record the verified working model in `## Shape Notes` before choosing task
boundaries. Greenfield work records planned modules and marks current responsibility as `new`.

| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|--------|------------------------|----------------|------------------|-------------|
| {source path or package} | {verified responsibility or new} | {add, modify, remove, read-only} | {none, changed, new, removed} | {task ID or pending} |

Rules:

- Read each mapped source module; indexes and Semble may locate it but cannot verify it.
- Include modules that own changed behavior or interfaces. Do not list every transitive dependency.
- Assign one owning task once decomposition is concrete.
- Builders record justified deviations. Interface, ownership, architecture, or scope deviations return
    to shape instead of silently rewriting the map.
- Verifiers compare actual changed modules and interface impact with the map.

### good_example — symbol guard applied

- Parent task references `computeSignal` and card status enums in an existing UI module.
- Shaper reads the module first, records `computeSignal(...): CardSignal` and `CardSignal = "dr-pending" | "blocked" | "claimed" | "deps-unmet" | "ready" | "unknown"`.
- Shaper drafts AC lines that use only those exact symbols and values.

### bad_example — source-read skipped

- Shaper drafts AC from memory and writes `computeSignal` returns an object with `state`.
- Shaper also lists statuses as `green/yellow/red/gray/stale`.
- AC is factually incorrect because symbol references were not validated against source.

### good_example — generated and external contract grounded

- Brief requests a generated alert operation through an assembled runtime context.
- Shaper records the generated operation inventory as authority for the callable name, production
    samples as bounded authority for envelope fields, and the existing CLI tree as authority for
    command hierarchy.
- Tasks are not created until operation visibility plus invocation has one owner and one
    assembled-context proof.

## Step 2 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

## Step 3 — Decompose into Atomic Tasks

### Deep Module Check

Apply `r-architecture-standards` before selecting module and task boundaries:

- Prefer cohesive modules that hide substantial functionality behind a small stable interface.
- Do not create forwarding wrappers, one-function modules, or speculative adapters merely to satisfy
    "single responsibility."
- Split when responsibilities, change reasons, failure domains, or proof modes genuinely diverge.
- Apply the Deletion Test: if deleting a proposed module only removes forwarding code while its
    complexity stays in callers, inline it or deepen it.
- Favor locality: a likely behavior change should require understanding and editing as few module
    boundaries as practical.

Each task must be:

- **Single outcome responsibility:** one coherent product or integration outcome; module or function
    count alone does not justify splitting an invariant across tasks.
- **Domain scoped:** one primary domain per task (see `r-architecture-standards` domain taxonomy). Multi-domain tasks must be split.
- **Outcome cohesive:** deliver or prove one coherent behavior within that domain. Do not split solely by artifact type when that leaves a final "wire everything together" task; shared contracts may be prerequisites, while the aggregate parent owns the cross-domain outcome.
- **Testable:** clear pass/fail criterion
- **Small:** ~2 hours of focused work max
- **Self-contained proof:** each task names the proof mode the builder/verifier should use, but does not require a separate test-writing task.

### Product Invariant Map

Before choosing task boundaries, map every load-bearing product invariant to one owning task and one
cross-boundary proof. Write the final map in `## Shape Notes` so shaper-challenger, verifier, and
collector can inspect it.

| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|-------------------|-------------|----------------------|-----------------------------|
| {observable promise} | {one task} | {assembled boundary} | {proof; lower dependency that may be replaced} |

Rules:

- Every invariant has exactly one owner, even when several tasks contribute prerequisites.
- The owning task's AC observes the invariant through its normal assembled boundary.
- A mock or injected dependency may replace only a layer below the boundary being proved.
- If decomposition leaves a final "wire everything together" task or no owner for a boundary, redraw
    the task shape before creation.
- Prefer roughly 3–6 outcome-cohesive tasks for a major feature. This is a fragmentation warning,
    not a hard cap; exceed it when distinct failure domains and proof modes genuinely require it.

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

- Context/discovery tasks depend on nothing (or prior schema) and are created only when build-ready
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
- **Reject orphaned invariants** — every invariant-map row names one owning task and that task has a
    normal-path AC.
- **Reject boundary-bypassing proof** — proof guidance must not replace the callable, command,
    workflow, or assembled context whose behavior the AC claims.
- **Reject unjustified fragmentation** — a major feature with more than six tasks must explain in
    Shape Notes which distinct failure domains or proof modes require the additional split.

If a planned task fails: refine the title and body or stop. Never create a placeholder task.

## Step 5b — User Decision Gate

Ask the user only for material product, architecture, scope, or trade-off choices. Do not ask for approval on mechanical decomposition when the parent intent, constraints, and dependencies are already clear.

When a material choice exists, present exactly one decision item with status quo, problem, options with pros/cons/risks/confidence, recommendation, and expected outcome. On approval, revise the planned tasks and proceed to Step 6. On rejection or unresolved scope, stop without creating new tasks; for an existing parent, leave it in `shape` or block it through `create_request` per `r-pipeline-protocol`.

## Step 6 — Create Tasks

**Decomposition naming convention only:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

**Shortcut naming:** preserve the parent-provided title verbatim (no phase prefix).

Create each build-ready child via `create_task` with title, `status="build"`, priority, tags, depends_on, `ac`, and body (supporting context including `Proof guidance:`). If an existing parent task ID is available, include `parent={parent_id}`. If there is no existing parent and aggregate closure is needed, create the child tasks first, then create the aggregate parent with `status="collect"` and `depends_on=[child_ids]`, then set each child `parent={aggregate_id}` via `edit_task`.

Do not create consolidation-test tasks automatically. If aggregate verification is needed, express it as parent/EPIC collect criteria or a normal shaped task with its own product-facing purpose.

**Parent completion gate:** For parent/EPIC decomposition with an existing parent, route the aggregate parent to `collect` after adding all required child IDs as dependencies via `edit_task(id={parent_id}, add_dep=[...])`. For a new aggregate parent, create it directly with `status="collect"` and `depends_on=[child_ids]`. This parks the parent behind child completion; dependency filtering keeps collector from receiving the parent while any required child is still active.

Group by dependency layer (independent first, then dependents). Record created task IDs for the report.

In shortcut mode, report the created task ID as a top-level result line (for example, `Created follow-up task: #{id}`).

Include the planning summary in the parent task's `end_work` note.

## Step 6a — Audit Created Board State

After every task-creation batch, call `list_tasks(ids=[...])` for all created and routed IDs before returning or advancing the parent. Verify:

- Every build-ready leaf task is in `build`.
- Every aggregate parent/EPIC is in `collect`.
- No shaper-created task is in `shape` unless the user explicitly requested raw manual intake.
- Every aggregate parent/EPIC depends on all required child IDs.
- Every child task points to the aggregate parent when a parent exists.

If a status is wrong, correct it immediately with `move_task` before final output. If a dependency or parent link is wrong, correct it with `edit_task`. Do not return an approval while the board state contradicts the intended routing.

## Step 7 — Visualize Dependencies

Produce a Mermaid diagram showing task relationships. Arrows: dependency toward dependent.

## Step 8 — Advance

**Post-task reflection:** Before advancing, write 3-5 bullets on problems faced, workarounds applied, patterns discovered. Skip if nothing notable. Use `save_memory(title=..., content=..., categories=[...], confidence=0.8, source_agent="shaper")` for each notable finding.

Call `shaper-challenger` after Step 6a, when concrete task IDs, statuses, dependencies, AC, and aggregate routing are visible. If the challenger finds a correctable issue, edit/move the created tasks and repeat Step 6a before final approval. Do not use the challenger only on a rough pre-creation plan.

For aggregate parent/EPIC tasks with no direct implementation work, put the parent in `collect` after child dependencies are attached. If creating a new aggregate parent, pass `status="collect"` to `create_task`; if shaping an existing parent, use `end_work(outcome="success", move_to="collect")`. For a parent that still owns direct implementation AC, create build-ready children instead of sending the aggregate parent to build.

Return Channel A using shaper's normal verdict format: `APPROVED #{id} -> collect` for aggregate parents parked behind children, `APPROVED #{id} -> build` for directly buildable parents, or `REFINE` / `BLOCK` when decomposition exposes unresolved scope or decisions.

## Output Template

Append decomposition details inside shaper's `## Shape Notes` section:

```
### Brief Readiness
- Product outcome and invocation: {source or decision}
- Existing-system fit and authority: {sources}
- Normal-path proof: {assembled boundary}
- Completion and change contract: {retained, migrated, removed, deferred}

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|-------|-----------|----------------|------------|
| {claim} | {source} | {observed|documented|assumed} | {value} |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|--------|------------------------|----------------|------------------|-------------|
| {module} | {responsibility or new} | {change} | {impact} | {task ID} |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|-------------------|-------------|----------------------|-----------------------------|
| {invariant} | {task ID} | {boundary} | {proof and allowed replacement} |

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
- [ ] Brief readiness gate passed or material gaps were resolved interactively
- [ ] Brownfield modules were located through `h-project-orientation` and verified from source
- [ ] Change Module Map records responsibility, planned change, interface impact, and owning task
- [ ] Proposed module boundaries pass the depth, locality, and Deletion Test diagnostics
- [ ] External/generated contract claims record authority, evidence state, and confidence
- [ ] Every product invariant has exactly one owning task and one normal-path proof
- [ ] Mocks or injected dependencies replace only layers below the boundary being proved
- [ ] Every task has proportional proof guidance
- [ ] No task has multiple responsibilities
- [ ] Every child is outcome-cohesive within its domain; no integration-only cleanup task remains
- [ ] Every task fits the Task Complexity Budget or has a `Complexity waiver:` note
- [ ] No task mixes multiple proof modes without being split
- [ ] No task mixes multiple failure-domain families without being split
- [ ] Refactor tasks name downstream-impact scope or create a separate scan/update task
- [ ] Sequence numbers unique and zero-padded (decomposition mode only)
- [ ] Priority reflects blocking potential
- [ ] Tags include `phase-{n}` + category (decomposition mode only)
- [ ] No cycles in dependency graph
- [ ] Parent task has `depends_on` pointing to required children when it is an aggregate/EPIC gate
- [ ] Created/routed task statuses were verified with `list_tasks(ids=[...])`
- [ ] No shaper-created task remains in `shape` unless explicitly requested as raw manual intake
- [ ] Shaper-challenger reviewed concrete created/routed task IDs after the status audit
- [ ] Mermaid diagram matches task list (decomposition mode only)
- [ ] Total 20 tasks or fewer
- [ ] More than six tasks for a major feature has a fragmentation rationale in Shape Notes
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
