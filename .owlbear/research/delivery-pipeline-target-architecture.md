# Delivery Pipeline Target Architecture

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** What is the smallest architecture that implements the accepted S1-S6 policies without retaining obsolete lifecycle mechanics?
> **Status:** Revised after independent architecture challenge.

## 1. Architectural Invariants

- Change authority preserves commitment provenance, outcomes, acceptance meaning, and current solution
  direction; execution records never redefine them.
- Work items are the user-facing identity. Jobs are immutable transformations and technical trace.
- Stage, readiness, attention, and progress are derived facts, not manually moved board fields.
- One independent review closes each distinct claim. Reviews do not become duplicate board stages.
- Requests block only their semantic target and true dependents.
- One change has one writable worktree and one writer; different changes may write concurrently.
- Exact reviewed commits remain the integrated commits on the change branch.
- Current pipeline state is snapshotted at cutover; target stores receive reviewed meaning, not stale
  job positions.

## 2. Runtime Topology

`serve/kanban` remains the domain owner. MCP and Cockpit are adapters. Shared skills describe how an
agent performs an engine-selected transformation; they do not own state transitions.

## 3. Authority and Durable State

Extend `change.py` rather than create a parallel specification store:

| Authority | Purpose |
|---|---|
| **Commitment** | C1-C5 class, provenance, statement, status, and superseding authority |
| **Outcome** | Immutable ID, user-facing result, protected commitments, observable acceptance, dependencies |
| **Solution direction** | Current architecture, interfaces, migration, risks, and outcome composition claims |
| **Task plan** | Reviewed tasks and proof under one outcome or admitted change-level composition claim |

Outcome replaces DeliveryNode as the semantic graph node. Plan jobs target outcomes or change-level
assembly claims; accepted plans create task identities beneath that scope; build jobs target tasks. An outcome ID is never reused or
renamed. Merge, split, removal, and replacement create new IDs plus supersession links, so old
requests, findings, and activity retain a durable referent.

Add `work_items.py` as a projection module, not another mutable lifecycle store. A work-item identity
is the immutable change or outcome ID, including superseded identities retained for history. It derives:

- stage: Design, Planning, Implementation, Assembly, or Completed;
- attention: user action, agent activity, waiting, or none;
- readiness and blocked dependency slice;
- reviewed-task progress and the next meaningful action; and
- links to commitments, requests, tasks, receipts, findings, and activity.

Attempts, findings, requests, receipts, activity, and supersession remain immutable durable evidence.
Stage transitions are reconstructed from admitted authority and that evidence, so board state cannot
drift from engine truth.

C4 revisions persist rationale in solution authority and project as non-blocking semantic updates.
Completion summaries derive satisfied commitments, accepted deviations, and known limits from current
authority and receipts. Neither creates a request or checkpoint.

## 4. Execution and Assurance

Replace target job kinds with three transformations:

| Job | Claim closed by its receipt |
|---|---|
| **plan** | One outcome or change assembly has an independently challenged task plan and proof approach |
| **build** | One task is implemented, deterministically proved, and independently reviewed at an exact commit |
| **assembly** | Multiple reviewed pieces satisfy one explicitly declared composition claim |

An assembly job exists only when solution authority or an independently accepted task-plan receipt
declares a composition claim that narrower build reviews cannot prove. Acceptance and Audit no longer
exist as automatic top-level jobs. Reviewer evidence is nested under the transformation attempt; a
successful receipt is emitted only after that review.

Remove `priority`, `cancelled`, per-job Cancel, and owner-impersonating Release from target models and
adapters. Keep expiry recovery and add guarded `recover_interrupted_task` for a known-dead session.
Dispatch orders ready jobs by dependency topology then stable creation identity.

## 5. Correction and Blocking

Keep finding class as diagnosis and add one shared return level:

- `implementation-attempt`: repair or restart the same reviewed task;
- `task-plan`: revise tasks or proof inside the same admitted plan scope;
- `solution-plan`: revise agent-owned architecture while preserving C1-C3 meaning; or
- `design`: resume collaboration because protected meaning may change.

Every reviewer returns acceptable, repair, restart, or one of the earlier return levels. The engine
invalidates only affected receipts and semantic dependents. A request records its commitment and
work-item target; readiness computes its dependency closure. Design re-entry remains pending until
revised authority is reviewed and admitted, not merely when its chat opens.

Repair retains the same reviewer. Restart or return to earlier authority gets a fresh reviewer. One
focused evidence response is allowed; unresolved disagreement goes to one isolated arbiter for that
concrete claim, whose disposition is final for the attempt.

## 6. Change Workspaces and Dispatch

Replace `dispatch/coordination.yaml` with one OCC-guarded record per change. It binds the active job,
attempt, claim, last reviewed commit, branch, worktree path, and integration target. A separate
capacity ledger enforces the global execution limit across chats without serializing changes.

A new `ChangeWorkspaceManager` owns one warm branch/worktree per unfinished change:

- create from the configured or discovered project integration target;
- serialize plan/build/assembly mutation inside that change;
- permit different change records to hold writers concurrently;
- keep repair in the same worktree and commit directly onto the change branch;
- on restart, preserve the rejected head under an immutable attempt ref, return the change branch to
  its last reviewed commit, and recreate the worktree there; and
- remove it after integration or terminal abandonment, preserving Git history and attempt evidence.

`ProofCheckoutManager` remains the read-only exact-commit boundary for independent review and
assembly proof. Per-task writable worktrees remain out of scope.

Integration forbids rebase, squash, and cherry-pick. Under an integration lock, the manager merges
the current target into the change branch. A conflict or interaction emits a finding and returns to
solution planning. Its accepted revision declares a change-level composition claim and task plan
before Assembly becomes ready. The target advances by CAS only to the reviewed merge commit. Task
SHAs remain unchanged ancestors; receipt currentness checks the merge result and affected paths.

Portfolio dispatch must evaluate current authority per change, filter jobs by that change, admit at
most one writer from each change, and respect a global execution limit. The orchestration chat owns
the repeated pick/start/dispatch/finalize loop; the board observes it.

## 7. Adapters and Cockpit

Expose domain queries before mutation APIs:

- `list_work_items(change_id?, stage?, attention?)` for the global portfolio;
- `show_work_item(work_item_id)` for semantic detail and linked task progress;
- `list_work_item_activity(work_item_id)` for correction and execution history; and
- `list_semantic_updates(work_item_id)` plus `show_completion_summary(work_item_id)`; and
- existing technical job, attempt, finding, request, receipt, and health queries for trace.

MCP lifecycle tools become plan/build/assembly completion and typed correction operations. Cockpit
removes Priority, Cancel, Release claim, accept, and audit controls. Interrupted-task recovery is
available only when the runtime proves the prior session is dead.

Preserve `NativeShell`, product navigation, `WorkspaceHeader`, responsive spacing, PDS components,
and the existing dashboard visual language. Allow no selected change for the portfolio route. Replace
the job board inside the current page with the accepted dense work-item hierarchy; load semantic
detail on selection and technical trace on demand. Work detail absorbs the separate primary
Specification and Requests workflows; Activity and Evidence become trace views.

## 8. Cutover Boundary

Build slices 1-5 as dormant target modules while the current pipeline remains the bootstrap executor.
They write no target state and remove no current exports. A one-time cutover service then:

1. verifies no claims/writers and classifies every unfinished change, outcome, and C1-C3 commitment;
2. snapshots and hashes current authority/runtime stores;
3. switches adapters, initializes target stores, and reintroduces classified authority;
4. runs runtime, Cockpit, worktree, and evidence smoke checks; and
5. publishes the receipt that activates target mutation.

Target code refuses mutation when it detects a pre-cutover store without that receipt. No dual-write,
old mutation adapter, or pending-job migration exists.

After receipt activation, a fresh canary change proves Design through integration using only target
runtime. This redesign is preserved bootstrap history; the canary is the self-hosting proof.

## 9. Implementation Slices

1. **Authority and projection:** commitment/outcome authority, work-item derivation, dependency and
   attention predicates, and projection tests.
2. **Execution kernel:** dormant three-kind target jobs, review evidence, receipts, typed returns, and
  scoped blocking; current bootstrap surfaces remain active.
3. **Isolation and portfolio dispatch:** per-change coordination, warm worktree manager, cross-change
   scheduling, exact-commit review checkout, and crash recovery.
4. **Transport:** MCP and HTTP work-item queries plus target lifecycle/correction commands.
5. **Cockpit:** global nullable selection, dense portfolio/detail views inside the existing dashboard,
   technical trace drill-down, and high-volume responsive proof.
6. **Cutover and activation:** snapshot/reintroduction, adapter switch, obsolete-surface removal,
   workflow adoption, consumer upgrade, and fresh-canary self-hosting proof.

Each slice receives deterministic validation and one independent review of its distinct claim. Before
coding, the complete dependency-ordered task plan receives the mandatory intent-to-proof challenge.

## 10. Proof Boundaries

- Model tests cover every stage, attention, dependency, correction, and assembly derivation.
- Runtime tests prove two changes may write concurrently while one change never has two writers.
- Git tests prove restart refs, unchanged task SHAs, merge CAS, and consumer-neutral targets.
- Contract tests prove removed controls and job kinds disappear across Python, MCP, HTTP, and React.
- Cockpit tests render large mixed-change portfolios at desktop and mobile sizes without overflow.
- Cutover tests inject failure before every publication boundary and prove receipt-gated recovery.
- One fresh canary completes under target runtime and reads bootstrap evidence.

## 11. Recommendation, Confidence, And Limits

**Recommendation:** Replace the current execution lifecycle at cutover rather than wrap it. Reuse its
deep guarantees: exact authority, immutable evidence, OCC transactions, proof checkout, invalidation,
and fail-closed snapshots. Add only semantic authority, work-item projection, per-change isolation,
and the three-claim execution lifecycle required by S1-S6.

**Confidence:** High in domain boundaries and removals because they follow accepted policy and current
source ownership. Medium in exact authority serialization and worktree naming until task planning.

**Limits:** This architecture does not choose field names, branch-name encoding, pagination limits,
or UI component decomposition. Those are implementation decisions unless they expose a new material
consequence.