# S6 Cutover Inventory and Consequences

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** What current state is worth preserving, what should resume, and what rollback remains honest when the redesigned pipeline replaces the current native pipeline?
> **Status:** Approved clean cutover; exact current job positions will not migrate.

## 1. Context and Question

The target changes the meaning and projection of work, removes current job controls, introduces
per-change writable worktrees, and replaces the globally serialized writer model. Treating every
current job as resumable target work would therefore carry obsolete execution mechanics across the
boundary. The cutover must preserve authority and evidence without mistaking historical status for
current intent.

The user-owned consequence is whether a bounded stopped-dispatch cutover may restart unfinished work
from its reviewed meaning rather than preserving exact current job positions. Store transforms,
snapshot manifests, and transaction mechanics remain agent-owned.

## 2. Sources Studied

| Source | Relevant fact | Confidence |
|---|---|---|
| `.owlbear/changes/replace-delivery-pipeline/` | One loaded change has many admitted revisions, plans, and immutable receipts | High |
| `.owlbear/kanban/jobs/` and `dispatch/coordination.yaml` | 254 jobs: 253 pending, one superseded, no claims; current digest has 30 jobs, 29 pending; no writer or readers | High |
| `.owlbear/kanban/requests/pending/` | Five unresolved request records belong to obsolete digest `3f6c6562...` and contain test content | High |
| `serve/kanban/src/owlbear_kanban/workspace.py` | Native authority, runtime, proof, and legacy-snapshot roots are explicitly separated | High |
| `serve/kanban/src/owlbear_kanban/jobs.py` | Job records persist claims, attempts, evidence, receipts, disposition, and OCC state | High |
| `serve/kanban/src/owlbear_kanban/attempts.py` | Attempt events are immutable append-only lifecycle evidence | High |
| `serve/kanban/src/owlbear_kanban/receipt.py` | Receipts bind proof to change digest, impact closure, and code history | High |
| `serve/kanban/src/owlbear_kanban/snapshot.py` | Existing snapshots hash every file and require an explicit disposition for active items | High |
| `serve/kanban/src/owlbear_kanban/finalization.py` | Existing finalization rejects claims, writers, requests, stale authority, stale code, and unclassified records | High |
| `setup/init.py` | Consumer setup creates native store roots but has no migration for the redesigned schema | High |

## 3. State Inventory

### Preserve as durable history

- Change intent, design, decisions, delivery authority, and every admitted revision.
- Receipts, findings, attempt events, request records and resolutions, and activity history.
- Exact Git revisions referenced by accepted evidence while repository retention permits it.
- A verified pre-cutover snapshot manifest and immutable cutover receipt.

These records explain what was promised, tried, accepted, superseded, or interrupted. They remain
read-only audit evidence after cutover; they do not automatically create target work items.

### Reintroduce from reviewed meaning

- The unfinished `replace-delivery-pipeline` change, using the approved S1-S6 strategic record as its
  current semantic parent.
- Any other genuinely unfinished change identified at cutover, outcome by outcome, after confirming
  that its meaning is still wanted.
- Open user decisions only when they still affect current reviewed meaning.

For every reintroduced change, each preserved C1-C3 commitment must be classified as reintroduced,
explicitly superseded by a named S1-S6 decision, or explicitly dropped under the authority required
by its provenance. No commitment may become historical merely because the old execution graph does.

Reintroduction creates target work items and fresh execution jobs. It does not preserve current job
IDs, priorities, claims, stage labels, or stale requests.

### Reconstruct or discard

- Proof checkouts and generated worktrees are recreated from retained Git revisions.
- Empty coordination state is discarded and recreated under per-change writer coordination.
- Current pending jobs are not migrated as active jobs; their source files remain in the snapshot.
- Obsolete test requests are historical records, not user blockers.

## 4. Operational Cutover Story

1. Stop the orchestration chat so no new dispatch begins.
2. Inventory every unfinished change, outcome, and C1-C3 commitment. Classify each as reintroduced,
   completed history, explicitly dropped, or superseded by named authority. Fail closed on anything
   unclassified.
3. Require zero active claims and writers, exact expected authority and code revisions, and no pending
   request whose delivery digest equals the current admitted digest. Stale-digest requests remain
   preserved history but do not block cutover.
4. Create and verify an immutable snapshot of current authority and runtime stores. Keep source paths
   untouched until the snapshot hashes and manifest agree.
5. Install the target code and initialize its stores in one bounded publication step. Do not dual-
   write old and target schemas.
6. Reintroduce approved unfinished meaning as target changes and work items. For this repository,
   `replace-delivery-pipeline` starts from the S1-S6 result rather than 29 pending current jobs.
7. Verify Cockpit, orchestration, per-change worktree creation, evidence lookup, and interrupted-task
   recovery before dispatch resumes.
8. Publish a cutover receipt bound to the source snapshot, target schema, authority revision, and code
   revision. Resume orchestration only after that receipt exists.

Expected downtime is the bounded snapshot, publication, and smoke-verification interval. Existing
evidence remains readable throughout from the immutable snapshot; active dispatch does not.

Consumer repositories follow the same one-time rule. A target runtime that detects a pre-cutover
native store without a valid cutover receipt refuses all mutations and directs the operator through
snapshot, classification, and target initialization. Installation never silently upgrades or ignores
consumer in-flight meaning.

## 5. Failure and Recovery

### Before the cutover receipt exists

Restore the exact source snapshot and previous code revision regardless of how far staging,
publication, or smoke verification progressed. Remove incomplete target state and retry only after
re-inventory. The absent receipt is the durable signal that target authority never became active.

### After the cutover receipt exists

The target is authoritative and dispatch may resume. The source snapshot still permits restoration,
but rollback stops being lossless once target decisions, commits, attempts, or evidence exist. Such
progress must be abandoned or deliberately reintroduced into the old system. There is no
bidirectional compatibility layer and no promise that old tools can interpret target state.

### Historical evidence unavailable

Fail closed for any reintroduced outcome whose required receipt or Git revision cannot be verified.
Preserve the record, return the affected meaning to Design or fresh proof, and continue unrelated
work.

## 6. Alternatives and Consequences

**Migrate exact job positions.** This appears continuous but gives 253 pending records target
authority they do not deserve, including stale revisions and controls explicitly removed by S5. It
requires compatibility logic for little user value and risks resuming obsolete work.

**Run old and target pipelines in parallel.** This reduces one-time downtime but creates two writers,
two readiness interpretations, and ambiguous receipts. Honest reconciliation would cost more than the
bounded outage and weaken the exact-authority guarantees retained from the current system.

**Snapshot history and reintroduce reviewed meaning.** This preserves every inspectable record while
giving only current intent operational authority. The cost is a brief dispatch stop and loss of exact
job-position continuity. Given zero active claims and almost entirely pending work, it is the smallest
credible risk today.

## 7. Decision, Confidence, And Limits

**Decision:** Use one clean, receipt-bound cutover. Preserve the entire current pipeline as a
verified read-only snapshot, reintroduce only reviewed unfinished meaning, and provide lossless
rollback until the cutover receipt activates the target, provided no target progress has followed.
Apply the same fail-closed cutover to consumer repositories. Do not dual-write, retain old mutation
APIs, or migrate pending jobs as target work.

The user confirmed that no work is currently dispatched outside this design chat and authorized the
necessary sensible break needed to restore forward progress. The cutover must therefore avoid a
compatibility phase, repeated reconsideration of stale jobs, or additional user ceremony unless new
evidence exposes a material consequence not covered by S1-S6.

**Confidence:** High on the state classification and current repository conditions. High that the
existing snapshot/finalization pattern is reusable in principle. Medium on cutover duration until the
target schema and smoke checks exist.

**Limits:** The inventory is a 2026-08-02 snapshot. Cutover must repeat it and stop if claims, writers,
current requests, new changes, or unclassified records appear. This document does not choose target
schema names or publication transactions.