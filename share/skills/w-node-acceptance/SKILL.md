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
2. The result contains the engine-created proof checkout and read-only authority sidecar. Its root,
   commit, and authority digest identify the candidate source and lifecycle snapshot; never
   substitute the shared worktree, live authority tree, or another checkout.
3. `show_change(change_id)` matches the selected delivery digest. Resolve only the target node's
   admitted outcome, obligations, interfaces, risks, acceptance contract, and proof.
4. `show_job(change_id, job_id)` matches the supplied target, active claim, current plan identity,
   packet set, and exact candidate revision.
5. The authority sidecar's current `plans/<target-node-id>.yaml` matches the selected node-plan digest
   and complete packet DAG. Its receipt records and `show_receipt` confirm every required packet
   receipt is current, successful, descended from the plan, and tied to the exact candidate revision.
6. The admitted proof boundary, methods, allowed lower replacements, and durable evidence outputs are
   complete enough to execute without creating tracked harness or changing authority.

Return `AcceptanceBlocked` for stale, malformed, incomplete, contradictory, unsafe, or unavailable
execution identity, checkout, authority, plan, receipt, or proof. Do not pick, start, refresh, repair,
release, or finish work.

## Step 2 - Fix The Read-Only Proof Envelope

Before running proof, record:

- the exact checkout root and candidate SHA;
- the authority sidecar root and digest;
- the admitted node outcome and acceptance contract;
- the current plan and packet receipt identities;
- each proof command or observation and its expected boundary;
- every lower-layer replacement, including why the admitted proof permits it;
- `git rev-parse --verify HEAD`, which must equal the supplied candidate SHA;
- `git status --porcelain=v1 --untracked-files=no` and `git diff --binary HEAD --` for tracked index
   and worktree state in the checkout.

Run commands only with the engine checkout as working directory. Temporary diagnostics, generated
configuration, or replacement fixtures must live under `.owlbear/scratch/` in that checkout and must
not stand in for the production boundary being accepted. Never execute proof in the shared worktree.

## Step 3 - Execute Exact-Commit Acceptance

Exercise the node's assembled public or maintained boundary at the supplied SHA. Compare the
observed behavior with the admitted node contract, current packet receipts, and proof methods. Keep
command, exit status, relevant output, environment facts, and replacement identities as evidence.

The hard terminal guard rejects Git state mutation and explicit filesystem-write commands before
execution. After every proof command and before returning a disposition, recapture
`git rev-parse --verify HEAD`, `git status --porcelain=v1 --untracked-files=no`, and
`git diff --binary HEAD --`. `HEAD` must still equal the supplied candidate SHA, and tracked index
and worktree state must be byte-identical to the baseline. Any tracked product, test, documentation,
graph, plan, job-authority, or evidence change is a rejection; do not inspect a modified result as
approval evidence and do not repair or remove the change.

Classify each failed acceptance claim as exactly one immutable `Finding` using the admitted classes:
`implementation-defect`, `unforeseeable-discovery`, `planning-omission`, or `scope-change`. For every
finding, name its source attempt/job, admitted target kind and identity, concrete detail, and evidence.
Use the admitted corrective route rules to return one matching invalidation with exact supersession
identity and the minimum corrective jobs. The acceptor classifies observed evidence; the orchestrator
must not classify findings or assemble evidence.

For packet implementation and packet-local proof routes, set `CorrectiveRouteRequest.packet_id` to the
finding's exact packet target ID. Do not infer a sibling packet from job order or substitute another
admitted packet. Other corrective route targets must omit `packet_id`.

Use this canonical PROOF-007 routing matrix. The route target is input to `plan_corrective_route`; it
does not replace the finding's admitted target kind and identity.

| Observed failure | Finding class | Finding target | Route target | Minimum result |
| --- | --- | --- | --- | --- |
| Planned packet behavior fails | `implementation-defect` | `packet` and packet ID | `packet-implementation` | one `build-repair` build job |
| Required local harness is absent from the admitted node plan | `planning-omission` | `proof` and proof ID | `packet-proof-plan` | one `node-plan-revision` plan job |
| Admitted proof permits replacement of its maintained boundary | `planning-omission` | `proof` and proof ID | `admitted-design-authority` | `design-reentry` and no runtime job |
| A required packet receipt is stale or superseded | `implementation-defect` | `receipt` and receipt ID | `packet-dependency` | one `node-plan-revision` plan job |

If the plan names a valid harness or assembled boundary but the implementation omits or substitutes it,
classify that implementation as `packet-local-proof` and return one `build-repair` job. Do not convert
missing or defective admitted authority into local implementation work.

## Step 4 - Return One Disposition

Return exactly one object. Preserve the supplied execution identity outside the object; the
orchestrator supplies it unchanged to the selected lifecycle operation.

### `AcceptorSuccess`

Use only when the exact commit satisfies the complete node contract and tracked state is unchanged:

Return canonical receipt evidence, not a prose or shorthand proof summary. Preserve exact values and
field names from current authority; never paraphrase, expand an ID into a record, truncate a record,
or append context to an authority string.

| Evidence field | Exact value |
|---|---|
| `methods` | complete ordered `proof.method` |
| `authority.delivery_digest` | current delivery digest |
| `authority.target_node_id` | target node ID |
| `authority.proof` | proof ID string, not the proof record |
| `authority.node_contract` | complete target `DeliveryNode` model, under this exact key |
| `authority.modules` | ordered target module ID list, not module records |
| `authority.interfaces` | sorted produced and consumed interface ID list, not interface records |
| `authority.migrations` | sorted migration ID list derived from interfaces and owned migrations |
| `authority.risks` | ordered target risk ID list, not risk records |
| `plan.node_plan_digest` | selected job's exact node-plan digest |
| `plan.packet_ids` | ordered packet ID list; empty for verification-only |
| `assembled_proof.boundary` | exact unmodified `proof.boundary` |
| `assembled_proof.durable_outputs` | complete ordered `proof.durable_outputs` |
| each assembled result | `command`, integer `exit_code: 0`, and non-empty string `result` |
| `checkout.candidate_sha` | exact supplied candidate SHA |
| tracked `before` and `after` | candidate `head` plus empty-string `status` and `diff` |
| `packet_receipts` | ordered complete packet receipt identities; empty for verification-only |
| `replacements` | complete replacement list, limited to `proof.allowed_replacements` |
| `changed_surfaces` | exactly the returned `impact_closure` |
| `reconciliation` | graph-ordered `{target_node_id, plan_job_id}` rows for direct dependents |

Copy `plan.node_plan_digest` directly from the supplied started job; never retype, recompute, or
copy it from prose, a displayed plan, or prior session context. Before returning success, compare
the complete scalar byte-for-byte with the started job's `node_plan_digest` and return
`AcceptanceBlocked` if they differ. Apply the same direct-copy check to `code_revision`,
`checkout.candidate_sha`, `authority.delivery_digest`, and `authority.target_node_id`.

For verification-only plans, additionally require `plan.receipt_id` equal to the current plan
receipt, `plan.packet_ids: []`, and `packet_receipts: []`. Never encode clean state as the word
`clean`.

```yaml
kind: AcceptorSuccess
receipt_id: <new stable accept receipt identity>
code_revision: <exact tested candidate SHA>
evidence: <assembled proof, packet receipt closure, replacements, and before/after tracked state>
evidence_ids: [<durable evidence identities>]
impact_closure: <admitted paths and authority targets exercised by acceptance>
reconciliation_plan_job_ids: [<one plan job ID per direct dependent node in canonical graph order>]
```

Build `reconciliation_plan_job_ids` from every delivery node whose `dependencies` contains the
accepted target, in the order those nodes appear in current delivery authority. For each direct
dependent, use bounded `list_jobs` results to reuse its sole current-digest, pending, unclaimed plan
job ID; choose one unused positive ID only when no such plan job exists. A claimed or ambiguous
current plan identity returns `AcceptanceBlocked`. Do not omit a direct dependent based on impact,
readiness, or whether acceptance changed its predecessor set.

These fields map unchanged to `finish_accept`.

Before returning success, record `evidence.reconciliation` as one ordered
`{target_node_id, plan_job_id}` row per direct dependent. Require its row count to equal the number
of graph nodes whose `dependencies` contains the accepted target, require the target sequence to
equal those nodes in authority order, and derive `reconciliation_plan_job_ids` from the row IDs
without filtering or reordering. A missing, duplicate, extra, or mismatched row returns
`AcceptanceBlocked`; do not let an inferred "primary" dependent stand in for the complete set.

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
