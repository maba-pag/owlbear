---
name: w-node-acceptance
description: "Workflow: Independently accept or reject one delivery node at an exact commit"
user-invocable: false
---

# Node Acceptance

Prove one engine-started delivery node without authoring or repairing tracked work. Only the
orchestrator maps the returned disposition to `finish_accept`, `reject_accept`, or `release_job`.

## Step 1 - Rehydrate The Started Accept Job

Treat the serialized successful `start_job` result as immutable execution authority. Require all of:

1. The result contains an active `accept` job and started event with no diagnostic. Its change, job,
   attempt, claim, actor, process, candidate revision, and delivery digest identities agree.
2. The result contains the engine-created proof checkout. Its root and commit identify the candidate
   revision; never substitute the shared worktree or create another checkout.
3. `show_change(change_id)` matches the selected delivery digest. Resolve only the target node's
   admitted outcome, obligations, interfaces, risks, acceptance contract, and proof.
4. `show_job(change_id, job_id)` matches the supplied target, active claim, current plan identity,
   packet set, and exact candidate revision.
5. The current `plans/<target-node-id>.yaml` matches the selected node-plan digest and complete packet
   DAG. `show_receipt` confirms every required packet receipt is current, successful, descended from
   the plan, and tied to the exact candidate revision.
6. The admitted proof boundary, methods, allowed lower replacements, and durable evidence outputs are
   complete enough to execute without creating tracked harness or changing authority.

Return `AcceptanceBlocked` for stale, malformed, incomplete, contradictory, unsafe, or unavailable
execution identity, checkout, authority, plan, receipt, or proof. Do not pick, start, refresh, repair,
release, or finish work.

## Step 2 - Fix The Read-Only Proof Envelope

Before running proof, record:

- the exact checkout root and candidate SHA;
- the admitted node outcome and acceptance contract;
- the current plan and packet receipt identities;
- each proof command or observation and its expected boundary;
- every lower-layer replacement, including why the admitted proof permits it;
- `git status --porcelain=v1` and `git diff --binary` for tracked state in the checkout.

Run commands only with the engine checkout as working directory. Temporary diagnostics, generated
configuration, or replacement fixtures must live under `.owlbear/scratch/` in that checkout and must
not stand in for the production boundary being accepted. Never execute proof in the shared worktree.

## Step 3 - Execute Exact-Commit Acceptance

Exercise the node's assembled public or maintained boundary at the supplied SHA. Compare the
observed behavior with the admitted node contract, current packet receipts, and proof methods. Keep
command, exit status, relevant output, environment facts, and replacement identities as evidence.

After every proof command and before returning a disposition, recapture `git status --porcelain=v1`
and `git diff --binary`. Tracked state must be byte-identical to the baseline. Any tracked product,
test, documentation, graph, plan, job-authority, or evidence change is a rejection; do not inspect a
modified result as approval evidence and do not repair or remove the change.

Classify each failed acceptance claim as exactly one immutable `Finding` using the admitted classes:
`implementation-defect`, `unforeseeable-discovery`, `planning-omission`, or `scope-change`. For every
finding, name its source attempt/job, admitted target kind and identity, concrete detail, and evidence.
Use the admitted corrective route rules to return one matching invalidation with exact supersession
identity and the minimum corrective jobs. The acceptor classifies observed evidence; the orchestrator
must not classify findings or assemble evidence.

## Step 4 - Return One Disposition

Return exactly one object. Preserve the supplied execution identity outside the object; the
orchestrator supplies it unchanged to the selected lifecycle operation.

### `AcceptorSuccess`

Use only when the exact commit satisfies the complete node contract and tracked state is unchanged:

```yaml
kind: AcceptorSuccess
receipt_id: <new stable accept receipt identity>
code_revision: <exact tested candidate SHA>
evidence: <assembled proof, packet receipt closure, replacements, and before/after tracked state>
evidence_ids: [<durable evidence identities>]
impact_closure: <admitted paths and authority targets exercised by acceptance>
reconciliation_plan_job_ids: [<one unused plan job ID per affected dependent node>]
```

These fields map unchanged to `finish_accept`.

### `AcceptanceRejected`

Use when exact-commit proof, receipt closure, or tracked-state independence fails:

```yaml
kind: AcceptanceRejected
detail: <concise rejection summary>
evidence_ids: [<proof and tracked-state evidence identities>]
findings: [<complete immutable Finding objects>]
invalidation: <one typed invalidation with supersession and exact minimum corrective jobs>
```

These fields map unchanged to `reject_accept`. Do not patch, weaken acceptance, or add speculative
corrective work.

### `AcceptanceBlocked`

Use when the selected work cannot be judged without inventing or replacing missing execution or
proof authority:

```yaml
kind: AcceptanceBlocked
target: <job, checkout, authority, plan, receipt, proof, or evidence target>
finding: <specific stale, malformed, incomplete, contradictory, unsafe, or unavailable condition>
```

This disposition maps to `release_job` with the original execution identity unchanged.

## Step 5 - Stop

Stop after one disposition. Do not call lifecycle tools, clean the engine checkout, inspect another
job, retain authority as current for a later invocation, or approve any tracked change authored by
this role. The orchestrator and engine own lifecycle mutation, checkout cleanup, and the next plan.

## Known Pitfalls

- **Shared-worktree proof:** a valid command run outside the supplied checkout proves the wrong state.
- **Implicit replacement:** generated harness or mocked public boundary invalidates the claimed proof.
- **Cleanup as innocence:** reverting an acceptor-authored tracked change does not restore independence;
  reject and preserve the before/after evidence.
- **Helpful repair:** an acceptor reports corrective work but never edits the defect or authority.
- **Prose disposition:** lifecycle routing requires one complete structured object, not a narrative.
