# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for Change delivery. It projects semantic work
items from admitted Design authority, owns deterministic Planning and Build transitions, coordinates
bounded execution, publishes reviewed Change checkpoints, observes user-owned
pull-request acceptance, and projects recoverable completed history from current receipt-backed
runtime records. Completed history is informational and is not Delivery runtime authority.

**Use this guide when:** you need to extend or integrate the core Change authority, understand its
worktree and publication boundaries, or call its public stores and runtimes.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Embedded callers use its public stores, runtimes, and
`PortfolioApplication`; agent clients use the `owlbear-delivery-mcp` adapter documented in
[serve/delivery-mcp/README.md](../delivery-mcp/README.md). The adapter is the public tool and startup
configuration reference.

The main public areas are:

| Area | Contracts |
| --- | --- |
| Authored Specification | `DesignPackageStore` create, verified read, compare-and-swap revision, and checkpoint |
| Compilation and admission | Deterministic contract derivation, validation, package binding, and atomic runtime admission |
| Operational Delivery | Acquisition, typed contexts, transitions, host-loss settlement, and stopped-worker release |
| Work projection | Portfolio work items with dependency readiness, typed attention, requests, blocks, task progress, and bounded Delivery health diagnostics |
| Coordination | Per-Change writer custody under `runtime/coordination/changes`, one shared execution budget, warm worktrees, and reviewed source boundaries |
| Publication and acceptance | Change-branch checkpoints, draft pull-request reconciliation, review-repair preparation, finalization, exact-head merge approval (only through Cockpit's `approve-merge` route; no MCP tool approves), acceptance observation, and publication supersession |
| Completed history | Receipt-backed completed Change projections plus read-only Git-backed historical package search |
| Integration attention | Typed Integration attention and exact repair-claim recovery remain current public operations |

Planner/Builder settlements cover normal outcomes, completed timeouts, and
`ended-without-result` after the dispatch has returned and owned mutating work is settled. Delivery
records each claim's issuing VS Code window PID and process start time under
`.owlbear/delivery/runtime/changes/<change>/claim-issuers/<attempt>.json`. A later acquisition
settles a previous-session claim as engine-only `worker-host-lost` only after that exact window
process is gone, no worktree writes have occurred for 30 seconds, and no live same-user process has a
cwd or open file under the managed worktree or Git admin directory. Restarting the MCP server while
the window remains alive does not qualify. Before the guard passes, readiness reports
`worker-stall-wait`: `next_eligible_at` indicates the write guard; without a time, the prompt gives
active-process names or bounded scan detail. A user who confirms that a specific chat was stopped
may call `release_stuck_worker` once under the same guard. `ERR_DELIVERY_WORKER_ACTIVE` preserves
custody and files and returns a retry time for the write guard or process details otherwise. Idle
shells with no live child are ignored unless an open file is under a guarded path. Neither
`worker-host-lost` nor `worker-released-stuck` is sent through `settle_worker_invocation`; both count
as failed attempts in the same three-attempt episode and preserve work for same-task retry after
backoff. A lost or released Finalizer without a report receives an engine-authored
`finalizer-ended-without-report` diagnostic with unknown checks, not proof.

Assembly is not a live Delivery stage or public Change authority. Historical runtime captures may
still contain reducible Assembly metadata, and legacy completed-history records retain their
historical schema for validation. New Changes use sequential Planning and Build outcomes directly.

## Admission And Portfolio Freshness

Persisted Delivery authority is held by the canonical `contract.json`, `admission.json`,
`frontier.json`, and coordination records under `.owlbear/delivery/runtime/changes/`. The
`PortfolioApplication` runtime map is process-local actionable membership, not a second authority.

Before portfolio reads and direct Change runtime lookups, `PortfolioApplication` reconciles
persisted Change discovery. It retains an unchanged runtime, composes a runtime for a newly
discovered or replaced contract when the persisted evidence is actionable, and removes runtime
membership when persisted authority is removed. Frontier access remains read-through. A read-side
reconciliation does not publish authority, allocate worktrees, or rewrite a valid frontier.

Startup reads remote snapshots and local Change entries independently. A malformed snapshot, identity
mismatch, missing per-Change authority file, or Change-specific coordination failure is quarantined
as bounded health attention; valid sibling Changes remain available. Quarantined Changes stay visible
in status and health projections when a last-known view exists, but they are excluded from work-item
queues, claims, acquisition, and dispatch. Use the read-only `delivery_health()` operation through
the MCP adapter, or the Cockpit Delivery health section, to inspect the source, code, Change ID, and
bounded detail. Workspace, Git, configuration, and unsupported persisted-state failures remain
startup-fatal.

The operating projection exposes explicit status axes instead of inferring lifecycle from runtime
map membership: `admission`, `stage`, `actionable_runtime`, `diagnostic_code`, and
`diagnostic_detail`. Its active status population is built from verified package IDs plus persisted
discovery observations, including admitted observations and the unadmitted entries needed to keep
genuine Design packages visible. Completed history remains a separate surface.

| Persisted state | Portfolio projection |
| --- | --- |
| Genuinely unadmitted package | `admission=unadmitted`, `stage=design`, and `actionable_runtime=false`; it is included in `draft_design_change_ids`. |
| Admitted Planning Change, including `tasks: []` | A normal Change group with Planning progress labeled `Task plan not published`; it is not a draft Design entry. |
| Admitted Change explicitly returned to Design | `admission=admitted` and `stage=design`; it is included in `design_required_change_ids`, not the draft list. |
| Admitted Change without an actionable runtime | Admission remains visible with `actionable_runtime=false` and the generic `runtime_unavailable` diagnostic; it is never recast as unadmitted Design. |

The Delivery MCP operation inventory includes the read-only `delivery_health` projection. Current
runtime readers accept only the current persisted schema; older registered state is refused at
startup with `state-migration-required` and is migrated through `/upgrade-delivery`, while unknown
state is refused and diagnosed through `/repair-delivery`. `delivery_health` reports remote evidence plus local
reconciliation; it does not mutate or repair persisted state. `list_work_items` remains a pure list
and does not become a health response.

Current per-Change custody records live under `.owlbear/delivery/runtime/coordination/changes/`.
The sibling `.owlbear/delivery/runtime/claims/` namespace is reserved for acquisition, publication,
verification locks, and the acceptance reconciler's host-local round-robin cursor is stored under
`claims/acceptance-reconciliation/cursor.json`; the cursor is scheduling state, not Delivery
authority, and a missing or invalid cursor safely starts a new rotation. Recoverable runtime
transaction manifests live under
`.owlbear/delivery/runtime/transactions/`.

## Readiness And Finalization Diagnostics

`PortfolioApplication` captures action readiness for Change, Work Item card/detail, and finalization
context reads. `DeliveryReadiness` carries status, the existing operation and next-actor values,
execution eligibility, a stable reason code, finalization checks state, nullable observed basis,
and an optional retained attempt. Required workspace inspection is bounded; an inspection failure
is not evidence of a clean workspace. Finalization revalidates the workspace at its effect boundary.
Independently timed reads are not a global filesystem snapshot.

`get_change` and detail reads distinguish `kind="available"` semantic runtime data from
`kind="unavailable"` known but unreadable authority. Available data can still have unavailable
workspace readiness. `list_changes().unavailable_changes` retains unreadable entries separately
from normal groups. Unknown Changes remain errors; canonical parsing is unchanged.

`report_finalization_failure(ReportFinalizationFailure(...))` accepts only bounded structural
diagnostics bound to contract/frontier digests, candidate/reviewed heads, and diagnostic sequence.
The ASCII attempt key is idempotent: an identical replay returns its immutable original report,
even after the candidate changes, without moving the current pointer. New reports require current
basis and sequence. Custody reports also require the observed fingerprint and matching dirty paths.
There are no caller-supplied summaries, commands, logs, URLs, observer identities, or success proof.
Unresolved check identity and exit detail remain null.

Reports live under the injected runtime root at `finalization-reports/<change-id>/`, with a dedicated
per-Change lock, contained recoverable transactions, immutable history, and a current pointer.
The limits are 16 KiB per encoded report and 256 reports per Change; capacity does not evict replay
history. Missing storage means no prior report. Unsafe, corrupt, or inaccessible storage reports
`report-store-unavailable`, without a fallback location or automatic byte repair. Reports are
host-local and excluded from portable Delivery snapshots.

A current failed report does not veto an otherwise eligible retry, labelled `Retry verification`.
Changed candidate or contract makes it historical. Current successful finalization proof takes
precedence and retires only the matching pointer; failed retirement cannot undo success, and exact
finalization replay can reconcile it. Ordinary reads neither create reports nor retire pointers.

## Acceptance Evidence

Outcome acceptance items are authored as `AC-NNN: <statement>`. Delivery derives each criterion's
`acceptance_id` and a content `acceptance_version`; contracts admitted before authored identities keep
positional `OUT-NNN.NN` IDs. Builder results and finalization requests carry schema-2 observations
with a typed `result` (a command's verdict is derived from its exit status and expectation), the
criterion versions they cover, and machine-observed or human-confirmed provenance. One evaluator in
`evidence.py` gives each criterion the status of the last typed record covering it (`covered`,
`waived`, or `missing`). Without one it is `uncovered`, or `unknown` when the Change holds schema-1
observations, which count for nothing and are never relabeled.

`finalize_change` writes nothing and refuses with `ERR_DELIVERY_ACCEPTANCE_EVIDENCE` and bounded
`gaps` unless every criterion is covered or waived and the finalization-mode review echoes the
context's `basis_digest` and the request's ordered `observation_ids`. Carried task evidence counts, so
a fully covered Change finalizes with no new observation. The finalization context gives the Finalizer
and reviewer the same complete `semantics`, or a `semantics_refusal` that withholds it whole.

A waiver or person-only check is a Decision Request scoped by `applies_to` to criterion versions and
one procedure. Only the user answers it, in Cockpit; the MCP `answer` tool refuses it with
`ERR_DELIVERY_CONFIRMATION`. A `waived` or `human-confirmed` record cites it by `request_id` and
applies only when the request belongs to the outcome, holds the affirmative answer, and its scope
names every covered criterion version and the record's procedure.

**Trust boundary.** Delivery checks evidence structure and identity, not honesty. Receipt and basis
digests prove content integrity, not that a procedure ran, that its output was read, or that a
reviewer inspected the code. The fences catch honest agent mistakes; the independent finalization
review is the semantic check of the assembled Change.

## Configuration

The package reads no environment variables. Canonical MCP and Cockpit startup uses the tracked
project policy and optional host-local runtime settings below. Embedded callers may provide the
same typed configuration directly.

| File | Optional? | Fields and defaults | Ownership |
| --- | --- | --- | --- |
| `.owlbear/delivery/config.json` | Required for canonical MCP/Cockpit startup | `schema_version` must be `2`; `remote`, `target_branch`, and `github_repository` are required and have no loader defaults. `delivery_state_branch` defaults to `owlbear/delivery-state` and is written by setup. `setup/init.py` defaults `remote` to `origin`, uses `main` as the non-interactive target-branch fallback, suggests the current branch interactively, and infers `github_repository` from the configured remote. | Tracked project policy |
| `.owlbear/delivery/runtime/host.json` | Seeded and trackable | Shared baseline defaults: `execution_capacity` defaults to `3`, and `claim_timeout_seconds` defaults to `3600` (60 minutes). Setup preserves existing values on rerun. `schema_version` must be `1`; both values must be positive integers. | Tracked baseline configuration |
| `.owlbear/delivery/runtime/host.local.json` | Optional and ignored | Any subset of the three host settings may override the tracked baseline for one machine. The file may omit `schema_version`; supplied values must be positive integers, and unknown keys are rejected at startup. | Host-local override configuration |

`execution_capacity` is the maximum number of active Planner or Builder outcome claims across the
portfolio. Each acquired Change has exact per-Change writer custody; there is no separate global
`writer_capacity` admission limit. The tracked baseline allows three active claims:

```json
{"schema_version": 1, "execution_capacity": 3, "claim_timeout_seconds": 3600}
```

When upgrading an existing workspace, remove the obsolete `writer_capacity` field from
`.owlbear/delivery/runtime/host.json` and any `.owlbear/delivery/runtime/host.local.json` override
before starting Delivery. `setup/init.py` preserves an existing `host.json` on rerun, and startup
rejects the stale field instead of rewriting it. If no host-specific values are needed, recreate
`host.json` from the baseline above. Do not edit historical `capacity-ledger.json` data.

Put machine-specific execution or timeout changes in the ignored local overlay instead of editing the
tracked baseline:

```json
{"execution_capacity": 2, "claim_timeout_seconds": 1800}
```

An active Planner or Builder claim is checked lazily during the next acquisition
(`acquire_change_action()` or `acquire_frontier_work()`);
`claim_timeout_seconds` (3600 seconds by default) identifies elapsed claims but is not proof that a
worker stopped. `recover_claim` remains separate and refuses with
`ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED` without supported host exclusion. At the next acquisition,
Delivery settles a previous-session claim only when its recorded issuing window is gone and the
write/process guard passes. Until then readiness may report `worker-stall-wait` with a retry time or
process details; unsettled claims continue to consume shared capacity. The loader merges
`host.local.json` over `host.json` when the overlay exists; a timeout or caller confirmation alone
does not clear custody.

Native Orchestrator settlement is separate from unknown-worker recovery. An exact normally returned
invocation, or an actually ended timeout with owned mutation jobs settled, can release its execution
reservation through `settle_worker_invocation`. Builder handoff preserves the same task's work and
remains mutation-fenced; corroborated passive handoff and Finalizer attention do not count as live
execution. A timer expiring, disconnect or missing result does not qualify. See the
[operating guide](../../setup/operating-owlbear.md#correction-and-recovery) for retry and pause behavior.

`setup/init.py` creates the tracked project policy and seeds `host.json` with the defaults above. It
does not create `host.local.json`; create that ignored file only when this host needs overrides. The
loader still accepts an absent baseline or local file for older or manually managed workspaces.

### Portability And Recovery

Authored `intent.md` and `design.md` remain local drafts until admission. When a Change is admitted,
Delivery commits the verified `authority.json`, `design.md`, `intent.md`, and `manifest.json` to the
managed `owlbear/change/<change-id>` branch before opening its first draft pull request. A requirement
change on an admitted, nonterminal Change is Pause, revise the package, approve, then `admit_change`:
activation snapshots the revised package on the reviewed head, keeps the previous authority under
`revisions/<contract digest>-<frontier digest>/`, resumes the Change and returns only changed outcomes
to Planning. Completed, abandoned and merged Changes are immutable; further work starts a successor
Change.

Sparse semantic checkpoints are published to the configured `delivery_state_branch` at admission,
meaningful task or Outcome progress, finalization, and acceptance. The managed Change branch is
published to its reviewed head before a state checkpoint can reference that head; sparseness applies
to Delivery-state snapshots, not to reviewed Change-branch commits. State snapshots retain resumable
authority and terminal evidence, but never live claims, locks, capacity ledgers, process identifiers,
or local paths. A fresh clone can therefore recover the last published checkpoint and requeue
incomplete work.
The local `refs/owlbear/packages/*` refs remain useful package history, but are not a remote backup.

If the remote package branch, state snapshot, contract, or local state disagree, startup reports
bounded Delivery attention and does not choose a side silently. Do not copy hidden `.git` refs or
ignored runtime files between machines; restore from the normal remote branches and the configured
state branch.

## Dependencies

| Package | Purpose |
| --- | --- |
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public Delivery application, stores, and coordinators rather than
writing authority or runtime files directly.
