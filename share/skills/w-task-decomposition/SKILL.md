---
name: w-task-decomposition
description: "Workflow: Task decomposition — shaper-owned decomposition into atomic child tasks with dependency graphs"
user-invocable: false
---

# Task Decomposition

Draft and commit atomic Kanban graphs with explicit dependencies, parent intent preservation, and
collector-ready aggregate gates. The calling shaper workflow owns user review and approval.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Break features into atomic tasks.
- Draft AC using `h-ac-quality` rules.
- Assign priorities and dependency graphs.
- Route build-ready child tasks directly to `build`; do not create `shape` staging tasks.
- Preserve parent/EPIC intent or Brief links so collector can verify aggregate fulfillment later.

### Out of Scope

- User-facing review and graph approval — `w-spec-shaping` or `w-task-repair`.
- Implementation — builder.
- Verification — verifier.
- Creating mandatory test-only pairs.

## Step 0 — Setup

Read `h-ac-quality` skill and use it as the authoritative AC validation checklist while drafting task acceptance criteria.

Use this workflow after shaper has claimed the parent task with `start_work` when a parent task ID exists. `start_work` returns the task body, making a separate `show_task` call redundant. If `start_work` fails, stop; a `ToolError` means the task is blocked, already claimed, or missing. For free-text ideas with no parent task ID, do not create a temporary `shape` task; shape the idea directly into routed outputs or stop without board mutation if it remains unresolved.

**Execution mode:** The caller selects one phase:

- `draft` — produce a complete provisional graph and maps without Kanban mutation;
- `commit` — create or update the exact user-approved graph, then audit concrete board state.

This workflow does not ask the user questions or authorize its own graph. In spec mode,
`w-spec-shaping` resolves decisions, runs shaper-challenger on the complete draft, and obtains user
approval before calling the commit phase. In repair mode, `w-task-repair` determines whether explicit
instructions authorize autonomous commit or material expansion requires user review.

**Status discipline:** Shaper-created tasks never rely on the `create_task` default. Pass `status="build"` for every build-ready leaf task and `status="collect"` for every aggregate parent/EPIC. `shape` is reserved for user-created intake and tasks rejected back from later pipeline stages.

## Step 1 — Read and Classify the Planning Source

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

When the input is a native OpenSpec change, use `openspec status --change <name> --json` to resolve
the active schema and concrete artifact paths. Read all existing planning artifacts reported by the
CLI. For stock `spec-driven`, apply this authority model:

| Artifact | Shaper use | Authority |
|----------|------------|-----------|
| `proposal.md` | Preserve problem, full Product Promise, user value, scope, impact, material user decisions, accepted exclusions, and assumptions | Product intent; active user decisions require explicit agreement to supersede |
| `specs/**/*.md` | Derive observable behavior and acceptance boundaries from capability requirements and scenarios | Normative product behavior |
| `design.md` | Reuse grounded architecture, contract evidence, trade-offs, risks, and migration constraints | Technical plan, subject to source and contract verification |
| `tasks.md` | Mine candidate outcomes, ordering, and proof ideas | Advisory only; never board shape or execution metadata |

Do not flatten the package into a synthetic Brief or require OwlBear-specific frontmatter. The
shaper writes the final Kanban graph after reconciling the whole package with current source. It may
merge, split, reorder, rename, or reject OpenSpec task suggestions. Record material departures and
their reasons in `## Shape Notes`; do not silently change Proposal intent or normative Specs.

Treat Proposal's full active Product Promise as scope authority. Every stated outcome must appear in
the task graph. An omission is valid only when Proposal records the user's explicit accepted
exclusion; do not reinterpret unowned omitted work as a later phase, deferral, or smaller first slice.
Run a post-shaping Product Promise check against the concrete task layout before approval.

### Product Promise Coverage Map

Include this map in the provisional graph and final Shape Notes:

| Product Promise item or accepted exclusion | Planning authority | Owning task or aggregate condition | Proving AC or outcome |
|---------------------------------------------|--------------------|------------------------------------|-----------------------|

- Give each active Product Promise item one owning task or a named aggregate completion condition
    and identify the acceptance criterion or observable outcome that proves it.
- Record an accepted exclusion with its proposal or explicit user-decision authority; exclusions do
    not receive an implementation owner.
- Split a Promise item across rows only when distinct tasks own independently testable outcomes.
- Do not label an unowned active item as deferred, later, implicit, or covered by the parent.
- An active item without an owner and proving AC or outcome blocks graph challenge and approval.

### Planning Readiness Gate

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
they do not require a formal planning package. For a multi-domain feature or external integration,
missing material elements are not implementation details. Resolve one material user decision at a
time through the calling shaping workflow, or stop without creating tasks. Do not turn an unresolved
product or contract choice into builder discretion.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 2 — Single-Task Shortcut

Before decomposition, detect whether the request is exactly one follow-up task with no dependency graph or multi-domain split required.

If yes, use the shortcut flow:

- If the request is truly greenfield with no existing or external contract, skip Steps 3–6 and 13.
- If the request touches existing modules, generated interfaces, external contracts, or an approved
    Brief, complete Step 3, the Change Module Map, and the Deep Module Check before applying the rest
    of the shortcut.
- Continue with Steps 7 through 9. In draft phase, return through Step 10; in commit phase, continue to Step 11.
- Preserve parent metadata where provided: title, parent ID, and tags.
- Status routing: create build-ready tasks with `status="build"`. If the follow-up still needs shaping, ask/refine instead of creating a `shape` task. Normalize old `todo`, `backlog`, `research`, `in-progress`, `review`, `docs`, and `done` requests to `build` only after shaping makes the task build-ready.
- Naming: no phase-based `P{phase}-{nn}` prefix in shortcut mode. Use the parent-provided title directly.
- TDD pairing is not used.
- Return the created task ID explicitly in your response message (for downstream linking and parent-child follow-up operations).

Typical shortcut cases: "fix off-by-one", "delete stale docs", "shaper calibration".

## Step 3 — Source And Contract Authority Guard

Apply this step when the input plan, OpenSpec package, parent task, or Brief references existing codebase modules,
generated interfaces, external APIs, schemas, protocols, or symbols that will appear in AC text.

This step may be skipped only for greenfield requests with no existing or external contract.

1. Follow `h-codebase-orientation`. Use existing indexes or source search narrowly and identify
    target source files and contract authorities from parent context. Authorities may
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
7. If the planning source or requested AC contradicts a canonical source, stop and surface the contradiction.
    Do not invent an alias, fallback, or fixture contract to make both appear true.

Do not continue to Step 4 until this guard is complete when triggered.

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

## Step 4 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

## Step 5 — Decompose into Atomic Tasks

### Deep Module Check

Apply `h-module-design` before selecting module and task boundaries:

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
- **Domain scoped:** one primary domain per task. Use the consuming project's local architecture map
    or instructions for domain ownership; multi-domain tasks must be split.
- **Outcome cohesive:** deliver or prove one coherent behavior within that domain. Do not split solely by artifact type when that leaves a final "wire everything together" task; shared contracts may be prerequisites, while the aggregate parent owns the cross-domain outcome.
- **Testable:** one clear pass/fail outcome.
- **Small:** ~2 hours of focused work max
- **Self-contained proof:** name the proof mode without creating a test-writing task.

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
- Every required operation and proof has an executor whose agent authority permits it. When the
    executor must be the user or an explicitly invoked workflow, represent that dependency as
    `type:user-action` with a planned Action Request before routine dispatch.
- A mock or injected dependency may replace only a layer below the boundary being proved.
- If decomposition leaves a final "wire everything together" task or no owner for a boundary, redraw
    the task shape before creation.
- Prefer roughly 3–6 outcome-cohesive tasks for a major feature. This is a fragmentation warning,
    not a hard cap; exceed it when distinct failure domains and proof modes genuinely require it.

### Dependency Closure Map

Before approving task boundaries, prove that each task can satisfy its AC from current source, its
own outputs, and its transitive predecessors. Write the final map in `## Shape Notes` beside the
Product Invariant Map.

| Task | Load-Bearing Input Or Mutation Participant | Producer Or Current-Source Authority | Required Predecessor |
|------|--------------------------------------------|--------------------------------------|----------------------|
| {task key} | {contract, store, record, interface, or operation} | {task key or verified source} | {task key or none} |

Rules:

- Include each contract, store, record type, interface, and mutation participant required by the
    task's AC, normal-path proof, or failure recovery.
- For each input, record its typed source or explicit predecessor output, including field shape,
    stable result/error literals, and the operation that supplies it. A prose mention, unstructured
    placeholder, test fixture, or inferred convention is not an available input.
- A producer must be verified current source, an explicit output owned by the consuming task, or a
    transitive predecessor with that output in its AC. A sibling, descendant, or predecessor that
    merely names the topic makes the graph unrealizable and blocks approval.
- Shared infrastructure may be a predecessor, but the task that introduces an operation's records
    owns that operation's atomic mutation and recovery proof unless admitted authority assigns a
    different owner.
- For each multi-record or cross-writer operation, name every mutation participant plus the shared
    serialization, lock, OCC, or transaction authority. Separate private locks do not prove a
    shared race boundary. Missing coordination ownership blocks approval.
- Cross-check each Product Invariant Map owner against this map. Naming an invariant owner is
    insufficient when that owner's dependency closure cannot supply the assembled proof boundary.
- Derived or transitive inputs still appear in the map; do not rely on the absence of a graph cycle
    as proof that the dependency direction is correct.

### Implementation Availability Gate

After the Dependency Closure Map is complete and before graph challenge, attempt to disconfirm each
task's readiness through one cheapest source check:

1. Resolve each AC input, output field, enum/error literal, and proof-boundary value to its canonical
   declaration or to a predecessor AC that creates that declaration.
2. Resolve each write, replacement, append, index update, and recovery action to its mutation owner
   and shared concurrency boundary.
3. Confirm the task's focused proof can construct its inputs without inventing a schema, protocol,
   ordering rule, repository query, or fixture-only contract.
4. Reject the task graph when any value or participant remains untyped, prose-only, owned by a
   sibling/descendant, or dependent on separate locks that do not serialize the claimed race.

Record the source check and result in the Dependency Closure Map. Scenario closure, coherent AC
wording, and an acyclic graph do not waive this gate.

### Scenario Closure Map

For persistence, transactions, concurrency, recovery, migration, security, external integration, or
other high-risk behavior, enumerate the finite scenario classes before deciding that a task is
small. Write the final map in `## Shape Notes`.

| Task | Risk Boundary | Input Or State Classes | Failure / Recovery / Race Classes | Owning AC |
|------|---------------|------------------------|-----------------------------------|-----------|
| {task key} | {public operation or artifact} | {equivalence classes} | {finite scenario classes} | {AC} |

Rules:

- Name behaviorally distinct input, failure, recovery, race, and conflict classes; do not hide them
  behind broad phrases such as "all failures" or "concurrent processes".
- Split a cross-product of two or more independent high-risk axes unless splitting would bypass the
    public boundary. A waiver must still enumerate the complete matrix.
- The map defines behavior, not test count; one boundary proof may cover several classes.

### Task Complexity Budget

| Dimension | Budget |
|-----------|--------|
| AC | Target 3; hard cap 5 |
| High-proof AC | At most 2 |
| Proof mode | One primary mode |
| Failure domain | One family |
| High-risk scenarios | One primary matrix; no independent-axis cross-product |

Use an explicit `Complexity waiver:` note only when splitting would make the work less verifiable. The waiver must name the budget exceeded and why the task is still expected to finish inside one pipeline pass.

### Mandatory Split Triggers

Split when the budget is exceeded or when:

- a reusable stateful primitive and its consumer need independent failure proof;
- proof has no durable, writable owner;
- required work is outside the agent's authority and no user action owns it;
- changed semantics require a separate downstream migration or regression proof;
- success behavior and substantial safety recovery have different proof burdens.

Ordering heuristic:

1. Model/schema tasks first (data structures)
2. Shared model/schema tasks before callers
3. Integration proof after unit components
4. CLI/UI tasks last (depend on core logic)

## Durability Principles

When drafting AC for planned tasks:

- Validate each AC block against `h-ac-quality` (authoritative checklist) before task creation.
- Apply the Task Complexity Budget first; clear AC does not make an oversized task acceptable.
- Every task must include explicit scope boundaries (in-scope and out-of-scope).
- Name a path only when that path or artifact is the acceptance surface; do not prescribe production
    locations, test files, test counts, or one-test-per-AC proof.

## Step 6 — Build Dependency Graph

Build an explicit dependency graph:

- Context/discovery tasks depend on nothing (or prior schema) and are created only when build-ready
- Implementation tasks depend on prerequisite shape/context tasks when they exist
- Schema, CRUD, agent, CLI layers form a natural hierarchy
- Cross-phase dependencies only when strictly necessary
- In draft phase, every dependency references a stable provisional key; in commit phase, replace it
    with the concrete task ID and verify the link
- Do not create ceremonial test → implementation dependency chains

## Step 7 — Assign Priority and Tags

- **Priority:** follow `r-pipeline-protocol` § Task Metadata: use `medium` by default, `high` for a
    current blocker or strong dependency fan-out, and `low` only for explicitly non-urgent cleanup
    or later work.
- **Tags (decomposition mode):** always `phase-{n}` + `scope:{domain}` + at least one category tag
- **Tags (shortcut mode):** preserve parent-provided tags verbatim; do not add phase tags unless they are already part of the parent scope

## Step 8 — Assign Proof Guidance

Add a short `Proof guidance:` line to each task body. This is guidance for builder/verifier, not a routing field.

| Signal | Guidance |
|--------|----------|
| Docs/process-only change with no executable behavior change | `no executable proof expected; cite changed artifact` |
| Config, deletion, wording, or local wiring change covered by existing validation | `no durable test expected; run the cheapest existing focused check` |
| Change validated by pre-existing named checks | `run named focused check: {command}` |
| Narrow behavior change with no uncovered recurrence risk | `run focused behavior check or import/config smoke; no durable test expected` |
| Shared/core-path change | `run focused check plus downstream-impact scan` |
| UI/browser change | `run package-local frontend check; add screenshot only if visual framing matters` |

## Step 9 — Validate Planned Tasks

Before creating any task, validate every planned task:

- **Reject `TEMP-*` titles** — placeholder artifacts, not legitimate tasks.
- **Reject empty bodies** — no AC or scoped content means the task is invalid.
- **Reject oversized tasks** — no task may exceed the Task Complexity Budget unless it has a `Complexity waiver:` note.
- **Reject scratch-only proof** — if required proof can only live in `.owlbear/scratch/`, split or add a tracked-artifact deliverable owned by an agent that can write it.
- **Reject hidden downstream impact** — behavior-changing refactors must name affected durable suites/consumers or include a downstream-impact scan task.
- **Reject proof-artifact-only tasks unless the artifact itself is the product deliverable** — proof should support the change, not become a fake task.
- **Reject test-prescriptive proof** — do not turn AC into one test each or require new durable tests
    when an existing check or transient observation proves the boundary.
- **Reject ownerless execution** — every required operation and proof must fit the responsible
    agent's authority or be represented by a user-action request with explicit returned evidence.
- **Reject unjustified fragmentation** — a major feature with more than six tasks must explain in
    Shape Notes which distinct failure domains or proof modes require the additional split.

Reject the graph unless every owning gate above passes: Product Promise coverage, Product Invariant
ownership and normal-path proof, Dependency Closure and Implementation Availability, Scenario
Closure, Task Complexity, and B4 boundary-valid proof. This is fail-closed: an uncovered active
Product Promise, an input or mutation participant unavailable through current source or transitive
predecessors, or an unenumerated independent high-risk scenario axis is a rejection condition, not
missing documentation. Do not treat Step 9 as a weaker summary of those requirements.

If a planned task fails: refine the title and body or stop. Never create a placeholder task.

## Step 10 — Return The Provisional Graph

In draft phase, stop here and return the complete provisional graph to the calling workflow. Use
stable provisional keys, such as `T1`, `T2`, and `EPIC`, wherever concrete task IDs do not yet exist.
Include every applicable field and map in the Output Template so challenge and user review receive
the complete graph contract.

Do not create or edit Kanban tasks in draft phase.

## Step 11 — Commit An Approved Graph

Enter this step only in commit phase. The caller must supply either:

- the user-approved graph from `w-spec-shaping`; or
- a complete non-material repair authorized by `w-task-repair`.

If the supplied graph differs materially from the draft that was approved or explicitly prescribed,
stop and return control to the caller. Do not normalize expansion by creating extra tasks.

Every approved graph entry must declare exactly one commit identity:

- **Create:** a stable provisional key with no existing task ID.
- **Update:** one concrete existing task ID. Titles or provisional keys alone never identify an
    existing task.

Before the first write, resolve all update IDs and the existing aggregate parent into one explicit
mutation set. Claim every not-already-claimed existing task in deterministic ID order and use the
records returned by `start_work` as the update baseline. If an ID is missing, appears more than once,
maps ambiguously, or was not part of the approved graph, call `end_work(outcome="release")` for each
claim acquired in this invocation and stop without mutation. Do not add an existing task to the
mutation set after writes begin.

**Decomposition naming convention only:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

**Shortcut naming:** preserve the parent-provided title verbatim (no phase prefix).

Commit in dependency-layer order and replace provisional dependency keys with concrete IDs:

1. For each **create** entry, call `create_task` with title, explicit `status`, priority, tags,
    resolved `depends_on`, `ac`, body including `Proof guidance:`, and `parent` when already known.
2. For each **update** entry, make the existing task exactly match the approved title, body, AC,
    priority, tags, parent, and resolved dependencies. Use `edit_task` for replacements and exact
    add/remove deltas, including removal of stale tags or dependency links. Preserve fields outside
    the approved graph contract. Do not route an update with `move_task`; Step 12 closes its claim
    and applies the approved status through `end_work` after the field audit passes.
3. If there is no existing parent and aggregate closure is needed, create the aggregate with
    `status="collect"` and `depends_on=[child_ids]`, then set each child `parent={aggregate_id}` via
    `edit_task`.

An existing task omitted from the approved graph remains unchanged. Task archival or deletion is
outside this commit contract; if faithful commit would require either, stop and return to the caller
for explicit approval instead of silently removing the task.

Do not create consolidation-test tasks automatically. If aggregate verification is needed, express it as parent/EPIC collect criteria or a normal shaped task with its own product-facing purpose.

**Parent completion gate:** For parent/EPIC decomposition with an existing parent, route the aggregate parent to `collect` after adding all required child IDs as dependencies via `edit_task(id={parent_id}, add_dep=[...])`. For a new aggregate parent, create it directly with `status="collect"` and `depends_on=[child_ids]`. This parks the parent behind child completion; dependency filtering keeps collector from receiving the parent while any required child is still active.

Record every created and updated task ID for the report.

In shortcut mode, report the created task ID as a top-level result line (for example, `Created follow-up task: #{id}`).

Designate one history target before mutation: the existing aggregate parent, or otherwise the
updated or created task that represents the approved outcome. The history target receives the full
planning summary; every other updated task receives a concise `## Shape Notes` reference to that
summary and its approved route.

### Partial Commit Containment

If the first mutating call fails, apply the universal read-only effect check. When the check proves
that no write occurred, call `end_work(outcome="release")` for every claim acquired in this
invocation and return the tool failure without containment. When the write occurred or its absence
cannot be established, treat the graph as partially committed and continue below.

If any create, edit, read, correction, or lifecycle-close operation fails after the first board
write, stop normal mutation. Do not attempt rollback: created IDs have no transactional inverse,
and best-effort restoration can hide or compound divergence.

1. Inspect every known created, updated, parent, and already-closed ID with `list_tasks(ids=[...])`
    and `show_task` where reachable. Record the failed operation and concrete partial state.
2. For each still-claimed existing task, call `end_work(outcome="block",
    block_reason="PARTIAL_GRAPH_COMMIT: {failure and recovery owner}", note="## Shape Notes\n...")`
    so containment releases its claim. For each already-closed existing task and each created task,
    set the same recovery block with `edit_task(block_reason=...)`.
3. If a containment operation also fails, follow the universal tool-failure retry limit, record the
    exact unreconciled ID and operation, and continue containment for the remaining affected IDs.
4. Return the failed operation, created IDs, updated IDs, current statuses and links, containment
    results, and exact recovery action to the caller. Do not report approval or continue to another
    graph mutation.

## Step 12 — Audit And Close Committed Board State

After the field-mutation batch and before closing any claimed task, call `list_tasks(ids=[...])` for
all created, updated, and routed IDs. Use it to verify set completeness, statuses, priorities, tags,
dependencies, parent links, and claim state. Then call `show_task(id=...)` for every graph entry and
compare its full title, body, AC, priority, tags, dependencies, parent, and status with the approved
graph. At this pre-close audit, a claimed existing task may retain its source status; every other
approved field must already match. A list projection is not evidence for body or AC.

Correct a pre-close mechanical field or link mismatch with `edit_task`. Correct a created task's
status with `move_task`. Re-read every corrected task with `show_task` before proceeding. A mismatch
that cannot be corrected mechanically enters Partial Commit Containment.

After the pre-close audit passes, close every claimed existing task in deterministic ID order:

- If its approved status differs from its current status, call
    `end_work(outcome="success", move_to={approved_status}, note={shape_notes})`.
- If it is already in the approved status, call
    `end_work(outcome="release", note={shape_notes})`.

The history target's note contains the full planning summary. Each other updated task's note records
the history target, its approved status, and that its graph-owned fields passed the pre-close audit.
Every claimed task must receive exactly one successful `end_work` call in this phase.

Finally, repeat `list_tasks(ids=[...])` and `show_task(id=...)` for every graph entry. Verify:

- Every build-ready leaf task is in `build`.
- Every aggregate parent/EPIC is in `collect`.
- No shaper-created task is in `shape` unless the user explicitly requested raw manual intake.
- Every aggregate parent/EPIC depends on all required child IDs.
- Every child task points to the aggregate parent when a parent exists.
- Every created and updated task's title, approved body content, AC, priority, tags, dependencies,
    parent, and status match the approved graph, with no stale approved-field values or links.
- Required Shape Notes follow the approved body content without replacing or weakening it.
- Every existing task claimed by this workflow is now unclaimed.

A final mismatch or remaining claim enters Partial Commit Containment. Do not return an approval
while the board state contradicts the intended routing.

## Step 13 — Visualize Dependencies

Produce a Mermaid diagram showing task relationships. Arrows: dependency toward dependent.

## Step 14 — Return The Board Audit

Apply the universal memory qualification gate from `owlbear-system.instructions.md`. Save only a
specific, non-obvious, reusable fact that would have improved this work if known at the start; task
notes, ordinary problems, and workarounds do not qualify by themselves.

Do not run a second substantive shaper-challenger review after creation. `w-spec-shaping` challenges
the complete provisional graph before user approval. After creation, audit only whether the concrete
board faithfully represents that approved graph. If material divergence is discovered, stop and
return to the caller instead of editing new scope into the board.

Step 12 has already routed and released every existing parent and update. Do not perform another
lifecycle mutation while returning the board audit. For a parent that still owns direct
implementation AC, create build-ready children instead of sending the aggregate parent to build.

Return the concrete task IDs, status/dependency audit, and any mechanical correction to the calling
workflow. For a standalone graph, identify the created task that represents the approved outcome
as the task-history target. The caller produces the human-facing summary and required task history.

## Output Template

Append decomposition details inside shaper's `## Shape Notes` section:

Include the Product Promise Coverage Map block when the planning source defines an active Product
Promise or accepted exclusions. Omit that block for standalone tasks and repairs with no Product
Promise authority.

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

### Product Promise Coverage Map
| Product Promise item or accepted exclusion | Planning authority | Owning task or aggregate condition | Proving AC or outcome |
|---------------------------------------------|--------------------|------------------------------------|-----------------------|
| {item or exclusion} | {authority} | {task, condition, or excluded} | {AC, outcome, or exclusion authority} |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|--------|------------------------|----------------|------------------|-------------|
| {module} | {responsibility or new} | {change} | {impact} | {task ID} |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|-------------------|-------------|----------------------|-----------------------------|
| {invariant} | {task ID} | {boundary} | {proof and allowed replacement} |

### Dependency Closure Map
| Task | Load-Bearing Input Or Mutation Participant | Producer Or Current-Source Authority | Required Predecessor |
|------|--------------------------------------------|--------------------------------------|----------------------|
| {task ID} | {input or participant} | {task ID or source} | {task ID or none} |

### Scenario Closure Map
| Task | Risk Boundary | Input Or State Classes | Failure / Recovery / Race Classes | Owning AC |
|------|---------------|------------------------|-----------------------------------|-----------|
| {task ID} | {boundary} | {classes} | {classes} | {AC} |

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
