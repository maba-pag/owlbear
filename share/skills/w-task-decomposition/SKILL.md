---
name: w-task-decomposition
description: "Workflow: Task decomposition — break features into atomic TDD-paired tasks with dependency graphs"
user-invocable: false
---

# Task Decomposition

Break complex features into atomic, test-driven kanban tasks with explicit dependency graphs and priority assignments.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Break features into atomic tasks.
- Draft AC using `h-ac-quality` rules.
- Create consolidation-test tasks when two or more implementation siblings exist.
- Assign priorities and dependency graphs.
- Route tasks to `backlog` (or `research` for researcher follow-ups).

### Out of Scope

- Architecture evaluation — architect (`w-arch-review`).
- AC quality validation — architect/challenger (`w-arch-review`, `challenger`).
- Implementation — builder (`w-tdd-green`).
- Test writing — test-writer (`w-tdd-red`).
- Moving tasks to `todo` — architect (`w-arch-review`).

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.
Read `h-ac-quality` skill and use it as the authoritative AC validation checklist while drafting task acceptance criteria.

**Claiming:** When **orchestrator-dispatched** (parent task ID provided), claim the parent task via `start_work` — it returns the task body, making a separate `show_task` call redundant. When **user-invoked**, read the task via `show_task` without claiming.

**Execution mode:** Determined by the caller's prompt prefix (mirrors `planner.agent.md` three-tier convention):

- **`Plan and create: #{id} — ...`** → dispatch mode: execute `create_task` calls directly and report created IDs.
- **`Plan: ...`** → user mode: present planned breakdown → `askQuestions` approval → create on approve. See Step 5b.
- **No prefix detected** → fallback: if pipeline markers are present, abort with an error asking the caller to use `Plan and create:` prefix; otherwise default to user mode.

## Step 1 — Read the Plan

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

If the parent task body contains a `## Brief` or `## Problem` section (Brief artifact, produced by ideation), use it to derive scope, investment tier, and approach constraints for decomposition. Include `Brief: see parent #{id}` reference in each child task body.

When the parent contains an approved ideation Brief, the planner sequences or splits Brief requirements but does not delete them. If a Brief requirement cannot fit one atomic task, split it across tasks. If a Brief requirement appears invalid, conflicting, or impossible, surface that conflict in the planning note instead of dropping the requirement.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 1a — Single-Task Shortcut

Before decomposition, detect whether the request is exactly one follow-up task with no dependency graph or TDD-paired implementation split required.

If yes, use the shortcut flow:

- Skip Step 1b, Steps 2–4, and Step 7.
- Continue with Steps 5, 5a, 5b (user mode only), and 6.
- Preserve caller metadata verbatim where provided: title, parent ID, and tags.
- Status routing: caller should specify target status (for example, "at backlog" or "at research"). Default is `backlog`; researcher follow-ups use `research`; never create `todo` (normalize caller-requested `todo` to `backlog`, or `research` for researcher follow-ups).
- Naming: no phase-based `P{phase}-{nn}` prefix in shortcut mode. Use caller-provided title directly.
- TDD pairing is not required in shortcut mode (single follow-up tasks are not feature implementation decompositions).
- Return the created task ID explicitly in your response message (for downstream linking and parent-child follow-up operations).

Typical shortcut cases: "fix off-by-one", "delete stale docs", "architect calibration".

## Step 1b — Source-Read & Symbol Capture Guard

Apply this step when the input plan, parent task, or brief references existing codebase modules or symbols that will appear in AC text.

This step may be skipped only for greenfield requests with no existing code references.

1. Identify target source files from caller context (plan text, parent task, brief, or referenced module paths).
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
- Planner reads the module first, records `computeSignal(...): CardSignal` and `CardSignal = "dr-pending" | "blocked" | "claimed" | "deps-unmet" | "ready" | "unknown"`.
- Planner drafts AC lines that use only those exact symbols and values.

### bad_example — source-read skipped

- Planner drafts AC from memory and writes `computeSignal` returns an object with `state`.
- Planner also lists statuses as `green/yellow/red/gray/stale`.
- AC is factually incorrect because symbol references were not validated against source.

## Step 2 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

## Step 3 — Decompose into Atomic Tasks

Each task must be:

- **Single responsibility:** one module, one function, one config
- **Domain scoped:** one primary domain per task (see `r-architecture-standards` domain taxonomy). Multi-domain tasks must be split.
- **Testable:** clear pass/fail criterion
- **Small:** ~2 hours of focused work max
- **Self-contained TDD:** each implementation task carries its own RED→GREEN cycle through the pipeline (test-writer writes RED, builder implements GREEN). Do not create separate test-only tasks paired with implementation tasks — this deadlocks the pipeline because test-only tasks can never pass the builder/reviewer green-test gates. When test design is complex, create a preceding **research** task instead (delivers findings to `.owlbear/research/`, not test code).

### Task Complexity Budget

Draft tasks to fit this budget before asking the architect to refine them:

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
2. Test tasks before their implementation counterparts
3. Integration tests after unit components
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

- Research depends on nothing (or prior schema)
- Implementation depends on its research task (when one exists)
- Schema, CRUD, agent, CLI layers form a natural hierarchy
- Cross-phase dependencies only when strictly necessary
- Every dependency references a concrete task ID
- Do not create test → implementation dependency chains — each task carries its own TDD cycle

## Step 5 — Assign Priority and Tags

- **Priority:** count dependents (critical if 3+, needed if 1-2, important otherwise)
- **Tags (decomposition mode):** always `phase-{n}` + `scope:{domain}` + at least one category tag
- **Tags (shortcut mode):** preserve caller-provided tags verbatim; do not add phase tags unless the caller explicitly provided them

See `r-project-standards` for the full priority scheme and tag taxonomy.

## Step 5c — Assign Proof Bundle

Assign one proof bundle to every planned task before creation.

**Selection guide:**

| Signal | Likely bundle |
|--------|---------------|
| Docs/process-only change with no executable behavior change | `skip` |
| Change validated by pre-existing named tests only | `existing` |
| Narrow behavior change needing a small focused test slice | `smoke` |
| New/changed behavior requiring full task-scoped TDD proof | `behavioral` |
| High-risk/core-path change requiring full-suite scrutiny | `critical` |

If the bundle is `existing`, capture proof boundaries as `Existing proof scope:` using a glob or explicit file list.

## Step 5a — Validate Planned Tasks

Before creating any task, validate every planned task:

- **Reject `TEMP-*` titles** — placeholder artifacts, not legitimate tasks.
- **Reject empty bodies** — no AC or scoped content means the task is invalid.
- **Reject oversized tasks** — no task may exceed the Task Complexity Budget unless it has a `Complexity waiver:` note.
- **Reject scratch-only proof** — if required proof can only live in `.owlbear/scratch/`, split or add a tracked-artifact deliverable owned by an agent that can write it.
- **Reject hidden downstream impact** — behavior-changing refactors must name affected durable suites/consumers or include a downstream-impact scan task.
- **Reject test-artifact-only tasks with `behavioral`/`critical` bundle** — tasks whose sole deliverable is a test file deadlock the pipeline (builder can't make tests green without implementation). Use a research task for complex test design, and let the implementation task carry the TDD cycle.

If a planned task fails: refine the title and body or stop. Never create a placeholder task.

## Step 5b — Approval (user mode only)

Skip this step if invoked in dispatch mode (`Plan and create:` prefix) — proceed directly to Step 6.

In shortcut mode, present a simplified single-task approval payload inline:

- One follow-up summary line: title, priority, status, tags
- No task table, no Mermaid dependency graph, no phase summary (decomposition-only artifacts)

Then call `askQuestions` with two options:

- "Approve — create follow-up task"
- "Reject — cancel"

On approve, proceed to Step 6. On reject, stop without creating tasks.

In decomposition mode, present the planned breakdown inline in the chat:

- Task list table (title, priority, dependencies, tags)
- Dependency graph (Mermaid)
- Summary: total count, dependency layers, phase

Call `askQuestions` with two options:

- "Approve — create all {N} tasks"
- "Reject — cancel without creating tasks"

**On approve:** proceed to Step 6.
**On reject:** stop, report cancellation to the user. Do NOT call `create_task`.

## Step 6 — Create Tasks

**Decomposition naming convention only:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

**Shortcut naming:** preserve the caller-provided title verbatim (no phase prefix).

Create each task via `create_task` with title, priority, tags, depends_on, `ac`, `proof_bundle`, body (supporting context only), and `parent` when provided by the caller (shortcut mode). Do not embed `Proof bundle: {value}` as a body line. If `{value}` is `existing`, include `Existing proof scope: {glob-or-file-list}` in the body. Do not pass `status` to `create_task`; tasks are created at `BoardConfig.entry_status`.

- Decomposition mode default status: `research`; create and leave at entry status.
- Shortcut mode status: caller-provided status, default `backlog` (or `research` for researcher follow-ups). For `backlog`, create first, then call `move_task(id={created_id}, status="backlog")`.
- Never create or move tasks to `todo`. `todo` is architect-gated and only reached via `backlog -> todo` promotion.

When decomposition mode yields two or more implementation tasks (excluding test tasks) under a common parent, create exactly one consolidation-test task after creating the implementation siblings:

- Title pattern: `consolidation test: {feature name}`
- Tags: include `consolidation-test`
- `depends_on`: all sibling implementation task IDs
- Status: `backlog` via create, then `move_task(id={created_id}, status="backlog")`

**Parent completion gate:** After creating the consolidation test, add its ID as a dependency on the parent task via `edit_task(id={parent_id}, add_dep=[{consolidation_id}])`. This ensures the parent shows `dep_status: blocked` until all child work is verified, and prevents the parent from being prematurely moved to `done`.

Group by dependency layer (independent first, then dependents). Record created task IDs for the report.

In shortcut mode, report the created task ID as a top-level result line (for example, `Created follow-up task: #{id}`).

If dispatched with a parent task ID, include the planning summary in your `end_work` note.

## Step 7 — Visualize Dependencies

Produce a Mermaid diagram showing task relationships. Arrows: dependency toward dependent.

## Step 8 — Advance

If dispatched with a parent task ID, advance via `end_work` to release the claim and move status.

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to parent task body (if dispatched with parent ID):

```
## Planning
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
- [ ] Every task carries its own RED→GREEN TDD cycle (no separate test-only tasks)
- [ ] No task has multiple responsibilities
- [ ] Every task fits the Task Complexity Budget or has a `Complexity waiver:` note
- [ ] No task mixes multiple proof modes without being split
- [ ] No task mixes multiple failure-domain families without being split
- [ ] Refactor tasks name downstream-impact scope or create a separate scan/update task
- [ ] Sequence numbers unique and zero-padded (decomposition mode only)
- [ ] Priority reflects blocking potential
- [ ] Tags include `phase-{n}` + category (decomposition mode only)
- [ ] No cycles in dependency graph
- [ ] Parent task has `depends_on` pointing to the consolidation test (completion gate)
- [ ] Mermaid diagram matches task list (decomposition mode only)
- [ ] Total 20 tasks or fewer
- [ ] AC describes "done", not "how"
- [ ] AC meets durability principles (behavior/interface-first, codebase-independent clarity, explicit scope boundaries, no HOW prescriptions)
- [ ] Shortcut mode returns created task ID in response message
- [ ] No `TEMP-*` titles or empty bodies created

## Known Pitfalls

- **Splitting RED and GREEN into separate tasks:** Do not create test-only tasks paired with implementation tasks — this deadlocks the pipeline (test-only tasks can never pass green-test gates). Each implementation task carries its own RED→GREEN cycle. Use research tasks for complex test design.
- **Cross-phase dependencies:** These create long dependency chains that block parallelism. Use only when strictly necessary.
- **Placeholder tasks:** Never create tasks with vague titles or empty bodies — they accumulate as board noise.
- **Broad AC piles:** Many clear AC lines can still create an unclear task when they require different proof modes or failure domains. Split by proof burden, not just by wording quality.
- **Scratch-only proof:** A scratch artifact is not a durable acceptance deliverable. Plan a tracked proof location and responsible owner before task creation.
- **Body content in `create_task`:** Keep AC concise. For complex multi-line AC, use the temp-file pattern (see `h-mcp-kanban`).
