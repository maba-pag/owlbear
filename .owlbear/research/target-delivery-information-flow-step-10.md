# Target Delivery Information Flow — Step 10: Select Frontier Work

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should admitted ready work become an agent launch without model scheduling,
> orphaned ownership, unnecessary transactions, or writer capacity spent on read-only Planning?

## 1. Status Quo And Evidence

Current orchestration lists work items, queries each change frontier, manually chooses stable order,
creates claim identities, calls `start_job`, and launches Planner or Builder. `PortfolioDispatcher`
already chooses the first ready job per change in stable cross-change order, but it reserves a
workspace writer before a runtime attempt exists and does so for Planning as well as writing work.

Target Cockpit and MCP recovery call `TargetRuntime.recover_interrupted_task`. They prove the owner
process dead and return its active attempt to pending, but do not release matching
`PortfolioCoordinator` writer ownership. `ChangeWorkspaceManager.restart` releases writers only for
a reviewed restart path. The guard is not trustworthy: runtime expects a numeric local OS PID while
orchestration currently invents `process_id` as an opaque runtime identity.

## 2. Decision D1 — Recoverable Staged Preparation

Do not add a cross-store atomic acquisition transaction. Crashes are expected and already have a
typed recovery path; making selection, runtime state, workspace ownership, and external agent launch
one transaction would add complexity without making the launch side effect atomic.

Prepare each selected job in this order:

1. deterministically select current dependency-ready work under execution capacity;
2. create and start the runtime attempt, establishing its job, claim, and owner identities;
3. for `build` only, acquire the change writer keyed to that exact attempt and return its recorded
   coordination; Planning and assembled verification remain read-only and take no writer slot;
4. return one complete launch package and invoke the named agent.

Starting the attempt first ensures every later writer reservation has a recoverable claim identity.
Replace process-liveness recovery with explicit exact-claim removal through Cockpit or orchestration
after a failed launch. For Build, first reconcile the workspace: preserve a clean committed attempt
head under its recovery ref, reset to the last completed boundary, then return the attempt to pending
and release its matching writer. A dirty, ambiguous, or mismatched workspace retains custody and
publishes repair attention. Recovery with no writer remains valid for Planning or failure before
workspace acquisition. Any late completion from the removed claim is stale. The operator owns
stopping a still-running invocation before removing its claim.

Derive active-claim age from the existing attempt start and surface long-idle claims in Cockpit and
frontier diagnostics. This is attention only: age never proves death, expires ownership, or removes a
claim. Exact removal remains an explicit operator action after checking the invocation.

Agent invocation remains an external side effect. Failure before launch or a lost invocation uses
the same exact-claim removal; no OS PID, lease proof, dispatch log, pause state, compensation ledger,
or synthetic completion is required. Current runtime attempt and coordination state are sufficient.

## 3. Information Contract

Input is current admitted portfolio state plus configured execution, writer, and role policy; the
caller supplies no job, identity, priority, timestamp, or capacity judgment. Selection uses stable
runtime facts only. The worker receives no portfolio listing or Design conversation.

## 4. Decision D2 — One Active Claim Per Change

Run independent changes in parallel, but allow only one active plan, build, or assembly claim per
change. Every claim consumes one configured global agent-execution slot. Only build consumes one
global writer slot and the change's exclusive writer ownership; Planning and assembled verification
read the exact warm branch head without reserving either writer resource.

Keep execution and writer capacity separate. When writer capacity is full, an eligible Planning
claim from another inactive change may still use an execution slot. Stable selection skips changes
with an active claim or revision-pending `design` status and orders eligible jobs by runtime topology
and creation identity. Add no user priority, balancing score, or model judgment: all eligible
admitted work is intended to run.

This sacrifices same-change planning parallelism to keep one exact source baseline, avoid plans
racing a changing warm branch, and make claim removal unambiguous. It does not reduce concurrency
across unrelated changes. Confidence: high.

## 5. Decision D3 — One Acquisition Operation

Add one purpose-built mutating operation, `acquire_frontier_work()`. It refreshes every admitted
runtime, excludes ineligible changes, applies D2 capacity and stable ordering, ensures each selected
change's warm workspace and exact source head, creates fresh attempt, claim, and owner identities,
starts the runtime attempt, and acquires writer custody only for build. Serialize this critical
section portfolio-wide through the existing coordinator lock; release it before returning packages
or launching agents. A failed partial preparation uses D1 recovery before another acquisition.

Return one bounded launch package per successful claim:

- exact change, authority, job, attempt, claim, and owner identities plus reviewer role/model policy;
- named worker role: Planner for `plan`, Builder for `build`, or Build Reviewer in assembled-
   verification mode for `assembly`;
- work-item, plan-scope, task, predecessor, return, and resume locators already present on the job;
- exact warm source root, branch, head, admitted integration-target identity, and last-reviewed boundary;
- writer custody only when the worker may write.

Do not include portfolio inventory, intent or design prose, commitment bodies, prior review history,
generated summaries, or evidence the worker can resolve through its scoped read tools. Planner gets
the exact source context read-only without writer custody.

Keep `list_frontier` for Cockpit, diagnostics, and direct domain composition. Keep `start_job` inside
the transport-free runtime. Remove `list_work_items`, per-change `list_frontier`, manual identity
creation, `start_job`, and workspace joins from the Orchestrator's normal tool sequence. A lost tool
response leaves exact active claims removable through D1; add no acquisition ledger or replay batch.

Each acquisition refresh also returns bounded integration-ready change IDs separately from worker
launch packages. Revision-pending changes are never Integration-ready. A completed change becomes
ready when either its reviewed change head or admitted contract digest differs from the latest
completed package. IDs create no claim, attempt, or capacity reservation. The Orchestrator invokes
`integrate_ready_change(change_id)` for each ID; it revalidates readiness under its locks and serializes CAS.

## 6. Decision D4 — Thin Invocation Adapter

Retain the Orchestrator only because VS Code currently exposes custom-agent invocation through an
agent tool rather than a deterministic Python API. It calls `acquire_frontier_work()`, launches each
package's named worker in parallel, forwards typed transition instructions unchanged to their lifecycle
operations, refreshes acquisition, and reports a Design return or fail-closed tool error.

Cockpit must derive attention for revision-pending changes, outcome returns to `design`,
reason/request blocks, long-idle active claims, and Integration-ready changes. Repeated retries and
ready unclaimed work remain ordinary frontier diagnostics, not attention.
The user resolves the condition and explicitly invokes Design, Orchestration, or integration as
appropriate; no daemon, notification record, or automatic scheduler is implied.

Remove source search, file reading, terminal, `Explore`, portfolio interpretation, scheduling,
identity construction, and evidence reconstruction from the role. It does not decide what to build,
which ready job matters more, whether a review is correct, or how a correction should route. Runtime
and typed worker output own those decisions. If VS Code gains deterministic custom-agent launch,
replace this adapter with a normal controller rather than preserving a model role by convention.

## 7. Step Completion

Step 10 is decided. One acquisition operation deterministically prepares at most one active claim per
change under separate execution and writer capacities. A thin Orchestrator launches the returned
packages; exact claim removal recovers failed launches. Step 11 receives one active read-only Plan
claim with exact authority and source context.