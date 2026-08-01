---
name: w-frontier-planning
description: "Workflow: Plan engine-selected delivery nodes into reviewed build or verification-only plans"
user-invocable: false
---

# Frontier Planning

Process engine-selected initial and reconciliation `plan` jobs in one resumable planner session.
Each job independently refines one admitted delivery node into an outcome-cohesive build packet DAG
or a source-proven verification-only re-admission record. The engine remains the authority for
selection, claims, validation, publication, receipts, and downstream jobs.

This workflow owns planning below admitted delivery authority. It cannot edit intent, design,
decisions, obligations, contracts, nodes, jobs, receipts, or another node's plan.

## Companion Skills

Load these with `read_file` immediately before the named work:

| Skill | Load when |
|-------|-----------|
| `h-codebase-orientation` | Locating current owners, callers, tests, and canonical contracts |
| `h-module-design` | Choosing packet boundaries, module locality, or dependency placement |
| `h-ac-quality` | Drafting packet acceptance scenarios and boundary-valid proof |
| `h-decision-requests` | A single material choice requires a Decision Request |

## Authority Boundary

The orchestrator supplies the result of one successful public `start_job` call. Treat its job,
attempt, claim, actor, process, candidate revision, change identity, delivery digest, target node,
and timestamps as immutable execution identity. Do not pick or start work from this workflow.

The planner may:

- query current change, job, receipt, request, activity, and health projections;
- inspect admitted authority, an existing target-node plan, repository source, history, and tests;
- delegate focused read-only repository analysis and one independent plan review;
- create one Decision Request for a single material choice;
- return one structured disposition to the orchestrator.

The planner must not call `finish_plan`, `release_job`, or another lifecycle completion tool. It
must not write a node plan directly. Only the orchestrator maps a returned disposition to the
public lifecycle operation.

## Step 1 - Rehydrate The Selected Job

Before proposing a packet or reusing session context:

1. Confirm the supplied job has kind `plan` and an active claim matching the supplied execution
   identity.
2. Call `show_change(change_id)` and require its digest to equal the selected job digest.
3. Call `show_job(change_id, job_id)` and read the projected target outcome, acceptance, modules,
   interfaces, and proof.
4. Read the target delivery node and resolve its owned and supported obligations, consumed and
   produced interfaces, modules, risks, proof, and delivery predecessors from the shown change.
5. Use `show_receipt` for the selected job's admission or superseded-plan identity and each current
   predecessor receipt relevant to the target.
6. Read `plans/<target-node-id>.yaml` when it exists. Treat it as the prior refinement to supersede,
   not as admitted authority.
7. Inspect focused repository evidence referenced by the authority or needed to choose current
   implementation boundaries.

When `show_job` returns `ERR_JOB_NOT_FOUND` for a referenced job, page through bounded
`list_jobs(change_id, candidate_revision)` results because that projection includes immutable archived
jobs. Return `PlanBlocked` for a missing job only when its identity is absent from the complete
archive-inclusive result.

Report a contradiction or stale identity as `PlanBlocked`; do not reconcile competing authority by
choosing the newest-looking artifact. Session memory from a prior node is a search aid only. Repeat
this complete rehydration for every selected job, including another job processed in the same warm
session.

## Step 2 - Classify Initial Or Reconciliation Work

An initial plan consumes admitted predecessor contracts. Predecessor implementation acceptance is
not an initial planning gate.

A reconciliation plan additionally consumes the current predecessor accept receipts and their
implementation evidence. Compare those receipts with the prior target-node plan and identify the
specific packet boundaries, impact closures, acceptance scenarios, or proof commands affected by
accepted implementation facts. Preserve unaffected refinement rather than rediscovering the whole
change.

Do not start or unblock a build from planner reasoning. The engine decides whether a superseding
plan receipt is current enough to release digest-bound build jobs.

## Step 3 - Ground The Node Refinement

Load `h-codebase-orientation` and investigate repository-answerable facts before treating them as a
choice. For each load-bearing claim, retain its source and evidence state. Repository search results
may be replaced in proof below this workflow; the selected job, admitted authority, planner role,
review gate, and public lifecycle tools may not be replaced.

Apply these legal-refinement limits:

- choose implementation boundaries only inside the target's admitted modules and interfaces;
- split by genuine dependency, authority, failure domain, incompatible tool, or context limit;
- combine code, tests, documentation, generated artifacts, migration, and proof when they advance
  one outcome;
- add implementation detail and proportional proof only inside the admitted proof boundary;
- reference only the target node and its admitted obligations, modules, interfaces, risks, proof,
  and predecessor contracts.

Return `SpecificationReentry` when the work needs a new or weakened product outcome, public or
cross-module interface, producer or consumer, failure semantic, migration, removal, compatibility,
security, destructive, concurrency, lifecycle, workflow, proof boundary, delivery dependency, or
other authority outside the selected node. Do not disguise global expansion as packet detail.

If one material choice inside the admitted boundary remains after repository research, load
`h-decision-requests`, create one Decision Request tied to the selected job, and return
`RequestCreated`. Broader design discussion returns `SpecificationReentry` instead.

## Step 4 - Select And Draft One Plan Mode

Use `mode: verification-only` only for a current exact-candidate re-admission generation, its
acceptance-triggered reconciliation, or a proof-only node-plan correction generated by typed
invalidation. The corrective case requires the selected job's current-digest supersession receipt
to name its durable finding, with `finding_class: planning-omission`, `target_kind: proof`, and the
selected node's admitted proof ID; it may repair proof-plan commands or observations but cannot
hide an implementation or durable-output delta. Verification-only is ineligible for initial
unimplemented work and always ineligible for DN-015. Before selecting it, inspect tracked source
and durable proof deeply enough to establish all of these facts:

1. Every node-owned obligation, module and interface effect, migration, required output, and durable
   proof mechanism maps to tracked state already present at the supplied candidate revision.
2. The complete inspected scope is clean and needs no implementation, test, documentation,
   generated artifact, migration, fixture, harness, client, wiring, or proof-infrastructure delta.
   Unknown, untracked, generated-but-missing, or ambiguous state is a delta.
3. The admitted proof can execute at that candidate without the acceptor creating tracked setup or
   another durable output.
4. One explicit non-empty canonical node impact closure covers the paths and admitted authority
   consumed by that inspection and proof.

Record `mode`, `packets: []`, the exact candidate revision, the selected plan job's receipt and
predecessor generation identity, source-inspection evidence, a non-empty required-output inventory,
proof-readiness commands and evidence, the clean tracked-scope result, the node impact closure, and
`acceptance_scenarios` with one numbered `h-ac-quality` scenario for each target-owned or
target-supported obligation and node acceptance outcome, and the independent review evidence. The
scenario set must include negative requirements and name the maintained or public boundary, concrete
precondition or input, observable result, and verification method. The `review` mapping must contain
`disposition: pass`, a non-empty `evidence` summary, the review evidence identity, and its complete
typed checks; `finish_plan` mechanically requires `node_plan.review.evidence` for verification-only
plans. Bootstrap or legacy records may corroborate inspection but cannot satisfy native receipt,
currentness, predecessor, proof, or review requirements. Any uncertainty or delta selects normal
build planning; authority expansion still returns `SpecificationReentry`.

For normal implementation work, use `mode: build`. Load `h-module-design` and prefer a small number
of deep outcome-cohesive packets. Do not create artifact-specific code, test, documentation,
migration, research, or proof jobs. Each packet must record:

| Field | Required content |
|-------|------------------|
| `id` | Stable `<target-node-id>-PK-<number>` identity |
| `outcome` | One coherent implementation result |
| `obligations` | Admitted owned or supported targets advanced by the packet |
| `in_scope` / `excluded` | Exact implementation boundary and named exclusions |
| `modules` / `interfaces` | Admitted modules and interfaces read, modified, produced, or consumed |
| `dependencies` | Other packet IDs in this node plan, in authored dependency order |
| `acceptance_scenarios` | Concrete input, public or maintained boundary, and observable result |
| `impact_closure` | Canonical repository paths and admitted authority targets consumed by proof |
| `proof` | Boundary, commands or observations, allowed lower replacements, and evidence outputs |
| `required_outputs` | Code, tests, docs, generated artifacts, migration, or evidence required by outcome |
| `profile` | Domain, risk, and tool context needed by the builder |
| `context_budget` | Expected files, interfaces, and change envelope for one focused session |

Packet dependencies must remain acyclic and inside the target plan. A dependency does not grant
path ownership; each packet declares the impact closure its own acceptance proof consumes.

Use bounded `list_jobs` results while the selected plan job holds the global writer lease to choose
unused positive downstream job IDs. For build mode, return one sorted `build_job_ids` entry per
authored packet. For verification-only mode, return `build_job_ids: []`. Return one distinct
`accept_job_id` in either mode. Do not infer readiness or reserve work by writing job files.

## Step 5 - Validate And Review

Before returning success:

1. Confirm exactly one explicit mode and all mode-specific fields; for build mode, check packet IDs,
   dependency references, and acyclicity.
2. Confirm each impact path is canonical and each authority target is in the target node's admitted
   node, obligations, modules, interfaces, risks, proof, or predecessor contracts.
   Migration effects must still be inspected and recorded in source or required-output evidence,
   but do not put a migration ID anywhere in the node plan unless that ID is itself in this selected
   node's allowed authority set. A migration attached to a consumed or produced interface does not
   become node-owned authority.
3. Confirm every target obligation and acceptance outcome has one packet owner and one
   boundary-valid proof path. For verification-only mode, confirm the numbered
   `acceptance_scenarios` cover owned and supported obligations, including negative requirements,
   without replacing the admitted public or maintained proof boundary with direct private fault
   injection or broad setup guards that can mask unrelated failures.
4. For build mode, confirm the packet set is outcome-cohesive, sized for focused builder contexts,
   and contains no artifact-specific status work. For verification-only mode, confirm exact
   candidate and generation identity, complete source/output/proof inspection, clean tracked scope,
   no hidden delta, and a non-empty node closure.
5. Call a fresh read-only plan reviewer. Require source-grounded disposition and evidence for
   plan completeness, admitted references, impact closures, dependency order, proof boundary, and
   material expansion. A verification-only review must inspect the claimed tracked state and proof,
   not merely review the supplied prose. The reviewer returns the raw six-row mapping defined by
   `planner-challenger`; preserve those rows unchanged as `node_plan.review.checks` and construct the
   review envelope as the owning planner: aggregate `disposition`, one non-empty `evidence` summary
   of what the reviewer inspected, and one stable `evidence_id`. A review identity, summary, or typed
   checks without the other two is incomplete. Do not require the reviewer to return an overall
   lifecycle verdict or planner-owned evidence metadata.

Malformed or incomplete review evidence returns `PlanBlocked`. For a complete non-pass review,
classify every finding before returning: repair bounded packet-plan defects inside admitted
authority, then obtain a fresh complete review of the repaired candidate. A finding that exposes
one material choice returns `RequestCreated` only after creating its Decision Request. A finding
that changes admitted authority returns `SpecificationReentry`. Return `PlanBlocked` only when a
bounded repair cannot be source-grounded or its fresh review remains non-pass. Never weaken the
plan or omit a finding to obtain success.

When a verification-only review identifies a concrete tracked output, proof-infrastructure gap,
invalid impact path, or unreproducible observation inside the node's admitted modules and proof,
the review has disproved verification-only eligibility. Redraft the candidate in build mode with a
bounded packet that owns those corrections, remove escaped paths rather than borrowing their module
authority, and obtain a fresh review. Do not return `PlanBlocked` merely because the current tracked
state cannot support verification-only; block only when the required build packet itself cannot be
source-grounded inside admitted authority.

## Step 6 - Return One Structured Disposition

Return exactly one of these objects to the orchestrator. Do not wrap it in prose.

### `PlannerSuccess`

Use only after target-bounded validation and independent review pass:

```yaml
kind: PlannerSuccess
receipt_id: <new stable plan receipt identity>
code_revision: <tested candidate Git revision>
evidence:
   methods: [<every canonical method string from the selected target proof, verbatim>]
   review: <complete independent review evidence>
   <other source or proof evidence>: <source-grounded value>
evidence_ids: [<durable evidence identities>]
impact_closure: <union of packet proof impact closures>
node_plan: <complete reviewed build or verification-only plan>
build_job_ids: [<one unused ID per build packet; empty for verification-only>]
accept_job_id: <one distinct unused ID>
```

`evidence.methods` must contain every admitted method from the selected target's proof. Do not
summarize, omit, or reconstruct that canonical sequence outside the planner. These keys match the
planner-owned inputs of public `finish_plan`. The orchestrator supplies the unchanged change, job,
attempt, claim, actor, process, and completion-time identity from dispatch.

### `RequestCreated`

```yaml
kind: RequestCreated
request_id: <persisted Decision Request identity>
summary: <single material choice blocking this plan>
```

### `SpecificationReentry`

```yaml
kind: SpecificationReentry
target: <authority target or proposed boundary>
finding: <specific unadmitted expansion or contradiction>
evidence: <source-grounded reason the node cannot own it>
```

### `PlanBlocked`

```yaml
kind: PlanBlocked
target: <job, authority, review, or evidence target>
finding: <specific stale, malformed, or incomplete condition>
```

## Step 7 - Checkpoint And Continue

After the orchestrator reports successful `finish_plan`, discard node-local working state and
require a fresh public `pick_jobs` result before another dispatch. Previously completed node plans
remain persisted engine outcomes; a later node failure must not roll them back or prompt direct
repair from this workflow.

Checkpoint only compact reusable repository orientation between jobs. Rehydrate authority, job,
receipts, prior plan, and source currentness again for the next selected target. Stop deliberately
when context can no longer preserve these boundaries; do not trade target isolation for session
continuity.

## Known Pitfalls

- **Self-selection:** only the orchestrator may pick and start the next job.
- **Authority editing:** a packet plan refines one node; it never repairs admitted delivery files.
- **Direct publication:** return a disposition; never write plan, receipt, or job files.
- **Acceptance gating initial plans:** admitted predecessor contracts are sufficient for initial planning.
- **Stale reconciliation:** accepted implementation evidence must be reflected before replacement builds can run.
- **Reviewer substitution:** planner self-review does not satisfy the independent review gate.
- **Warm-session leakage:** repeat rehydration and target checks for every selected node.
