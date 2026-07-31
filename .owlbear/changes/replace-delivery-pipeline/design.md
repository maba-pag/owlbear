# Implementation Contract: Graph-Authoritative Delivery

> **Change ID:** `replace-delivery-pipeline`
> **Owning intake:** #1968
> **Authority state:** Canonical state and admission receipt are declared in `delivery/nodes.yaml`.
> **Authority:** This file owns technical realization. Product intent belongs in `intent.md`; material choices belong in `decisions.yaml`; stable identities and delivery ownership belong in `delivery/`.

## 1. Design Goals

The replacement must make these properties true by construction:

1. One durable change revision owns product intent, decisions, architecture, delivery obligations, interface edges, migration, risk, and proof.
2. Admission ends Specification and certifies layered delivery completeness for one exact revision before Delivery work exists.
3. Specification and Delivery are peer product phases backed by one transactional control-plane core.
4. The admitted graph is complete at delivery-node level; bounded frontier planning either adds implementation packets or, for a proven exact-candidate re-admission case, publishes a verification-only plan without changing admitted obligations.
5. Every visible Delivery column names an agent transformation: `plan`, `build`, `accept`, or `audit`.
6. Builders retain warm context while a mandatory read-only reviewer challenges their packet.
7. Node acceptance and final change audit are independent, read-only over tracked files, exact-revision gates.
8. Findings create immutable corrective jobs and superseding receipts rather than moving cards backward or rewriting history.
9. Shared-worktree tracked mutations are serialized.
10. OpenSpec and the old task-authoritative pipeline disappear completely at cutover.

## 2. System Model

The control plane has four distinct responsibilities behind one `owlbear-kanban` facade.

```text
Authority plane                         Work plane
.owlbear/changes/<change-id>/           .owlbear/native/
  intent.md                               jobs/
  design.md                               archive/
  decisions.yaml                          requests/
  delivery/                               activity.jsonl
  plans/
  receipts/
        |                                      |
        +------------ owlbear-kanban ----------+
                         |
                 MCP and Cockpit adapters
                         |
    designer | planner | builder | acceptor | auditor | orchestrator
```

### 2.1 Authority plane

The authority plane is Git-tracked and human-reviewable. It contains the current product and technical truth plus immutable receipts. Agents do not copy its normative content into jobs.

### 2.2 Work plane

The work plane contains purpose-specific Kanban jobs, claims, blocks, pending requests, attempts, and activity. A job points to one authoritative target and semantic digest. It is not a task specification.

### 2.3 Evidence plane

Attempts and transient telemetry remain operational. Findings and successful receipts are durable, structured, target-specific evidence. A receipt is valid only when its authority digest, predecessor receipts, proof boundary, and code revision remain current.

### 2.4 Git plane

The repository uses one shared implementation worktree. The orchestrator dispatches at most one tracked-file-mutating job in a wave. Acceptance and audit do not overlap a writer and execute in disposable read-only checkouts of exact committed revisions under `.owlbear/scratch/proof/<job-id>/`. Git history remains product-code history; OwlBear adds exact authority and proof references rather than a second source-control system.

## 3. Native Change Package

```text
.owlbear/changes/<change-id>/
  intent.md
  design.md
  decisions.yaml
  delivery/
    obligations.yaml
    contracts.yaml
    nodes.yaml
  plans/
    <node-id>.yaml
  receipts/
    <receipt-id>.yaml
```

The three prose/decision roots plus the three files under `delivery/` are editable Specification authority. `plans/` contains post-admission Delivery refinements. `receipts/` is engine-generated immutable evidence.

### 3.1 `intent.md`

Owns the problem, actors, Product Promise, normal workflows, visible failure behavior, scope, exclusions, preserved behavior, success conditions, assumptions, and technically-done-but-wrong outcomes.

### 3.2 `design.md`

Owns current-system evidence, architecture, module ownership, control/data flow, contract authorities, interfaces, lifecycle, migration/removal, safety, rejected alternatives, risks, and proof boundaries.

### 3.3 `decisions.yaml`

Owns material user decisions and supersession. Every option records pros, cons, risks, recommendation, rationale, and confidence. Runtime implementation questions do not enter this file unless their resolution changes intent, design, delivery obligations, compatibility, security, or proof meaning.

### 3.4 `delivery/`

Owns stable Specification identities and relationships in three physical files:

- `obligations.yaml`: requirements, negative requirements, preserved behaviors, and workflows;
- `contracts.yaml`: modules, interfaces, migrations, risks, and proofs;
- `nodes.yaml`: delivery nodes and dependency edges.

The loader joins these files into one canonical logical `DeliveryGraph`; physical file boundaries do not affect semantic identity.

### 3.5 `plans/`

Each `<node-id>.yaml` contains one post-admission packet DAG. A planner may write only the target node's plan file through the per-node transaction. Any change to `delivery/`, `intent.md`, `design.md`, or accepted decisions requires Specification re-entry and re-admission.

A node plan has one discriminated mode. `build` contains one or more packets. `verification-only`
contains zero packets and the exact candidate revision, re-admission generation identity, source
inspection, required-output inventory, admitted-proof readiness, clean tracked-scope result, and
node-level impact closure that establish the eligibility contract in §6.4. Empty packets without
that complete mode-specific evidence are invalid.

### 3.6 Receipts

Receipts are immutable YAML records with a versioned discriminated schema. Core receipt kinds are:

- `admission`: certifies one delivery digest and records deterministic diagnostics, semantic challenge, baseline commands, user approval, and limits;
- `plan`: certifies one node plan digest and either the complete packet DAG or the complete
  verification-only eligibility record for a delivery node;
- `build`: certifies one packet contract, commit, changed paths, proof, inline-review result, and predecessors;
- `accept`: certifies one delivery node against its node plan, required build receipts when packets
  exist, proof boundary, and tested code revision;
- `audit`: certifies the complete change against all delivery nodes, workflows, accepted decisions, and tested code revision;
- `supersession`: invalidates named receipts and identifies corrective findings/jobs.

## 4. Semantic Identity and Digests

Stable IDs are human-readable and unique within a change:

- requirements: `REQ-###`;
- negative requirements: `NEG-###`;
- preserved behaviors: `KEEP-###`;
- decisions: `DEC-###`;
- workflows: `WF-###`;
- interfaces: `IF-###`;
- migrations: `MIG-###`;
- risks: `RISK-###`;
- proofs: `PROOF-###`;
- delivery nodes: `DN-###`;
- packets: `<node-id>-PK-###`.

Jobs retain a globally monotonic numeric ID for board ergonomics and reference `change_id`, target ID, job kind, and digest.

### 4.1 Delivery digest

`delivery_digest` is SHA-256 over one UTF-8 canonical JSON envelope with sorted mapping keys, compact separators, JSON-mode validated scalar values (dates/times as ISO 8601 strings and enums as values), and these fields:

1. `intent`: `intent.md` normalized to LF and one trailing newline;
2. `design`: `design.md` normalized to LF and one trailing newline;
3. `decisions`: the accepted material decision records in stable decision-ID order;
4. `delivery`: the canonical joined delivery-authority sections named in §3.4, excluding physical wrapping and admission metadata.

Normalization standardizes UTF-8, LF endings, deterministic mapping keys, and trailing newline. Any authority edit creates a new digest. There is no compatibility promise between digests.

`delivery-v1` decodes Markdown as strict UTF-8 without a byte-order mark, converts CRLF and CR to LF,
removes trailing line breaks, and appends one LF while preserving every other character. YAML is
strictly parsed and converted to JSON-mode scalar values. Accepted decisions are sorted by decision
ID; all other sequences retain authored order. The canonical envelope is serialized with recursively
sorted mapping keys, compact separators, UTF-8 characters unescaped, and non-finite numbers rejected.
These semantics are equivalent to Python `json.dumps(envelope, sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False).encode("utf-8")` before SHA-256.

### 4.2 Node plan digest

`node_plan_digest` is SHA-256 over:

- the current `delivery_digest`;
- the canonical delivery-node contract;
- the canonical `plans/<node-id>.yaml` packet DAG.

Packet refinement changes only the affected node plan digest. It cannot change the admitted delivery digest.

### 4.3 Receipt validity

A receipt is valid when:

- its schema is supported;
- its target exists;
- every referenced predecessor receipt is valid;
- its delivery and node-plan digests equal current values;
- no supersession receipt names it in `invalidated_receipt_ids`;
- its code revision satisfies the typed impact-closure contract below;
- its evidence satisfies the target proof contract.

The engine computes validity; agents do not infer it from prose.

#### 4.3.1 Receipt impact closure

Each non-admission receipt freezes one typed `impact_closure` at issuance. The closure contains:

- `paths`: a non-empty sorted set of canonical repository-relative POSIX selectors, where a trailing `/` denotes a
  tree and its absence denotes one file;
- `authority_targets`: a sorted set of stable IDs whose semantic authority the proof consumed.

The reserved selector `/` denotes the complete repository tree. Other selectors reject a leading slash, `.`, `..`,
empty segments, backslashes, NUL, and repository escape. A tree selector matches the named tree and its descendants;
a file selector matches only that path. Plan and build receipts copy the closure from their canonical packet
contract. An accept receipt uses the canonical union of its node-plan packet closures in `build` mode and the
explicit node-level verification closure in `verification-only` mode. An audit receipt uses `/` plus the active
change-authority targets. Receipt issuance fails when the required closure is missing, malformed, empty, or cannot
be derived without ambiguity. Changed paths and receipt diffs are evidence, not authority for widening or narrowing
the frozen closure.

A packet may consume a predecessor receipt's paths and authority targets only by copying that predecessor's complete
canonical closure into its own closure and rerunning the predecessor proof it supersedes. This evidence dependency
does not transfer product ownership. Partial overlap remains stale; a packet cannot preserve predecessor evidence by
naming only the path it intends to edit.

#### 4.3.2 Code-revision currency

The engine owns a repository-history protocol with two deterministic operations: resolve whether the tested commit
and candidate commit exist and whether the latter descends from the former; then return the NUL-delimited Git
name-status changes between them with rename and copy detection enabled. Paths are decoded and normalized through
the same repository-relative POSIX validator as impact-closure selectors. Both source and destination paths of a
rename or copy participate in intersection.

Code-revision evaluation returns these stable results:

- `CURRENT` when candidate and tested commits are identical;
- `CURRENT` when candidate is a descendant and no changed path intersects the frozen closure;
- `ERR_RECEIPT_CODE_REVISION_MISSING` when either commit cannot be resolved;
- `ERR_RECEIPT_CODE_REVISION_NOT_DESCENDANT` when candidate is not a descendant;
- `ERR_RECEIPT_CODE_PATH_STALE` when a changed path intersects the closure;
- `ERR_RECEIPT_CODE_HISTORY_UNAVAILABLE` when history output is malformed, undecodable, path-unsafe, or otherwise
  cannot prove non-intersection.

Unknown and ambiguous history is stale. The repository protocol classifies revisions only; DN-004 separately owns
creation and cleanup of disposable proof checkouts. Authority-target currency remains owned by delivery-digest,
node-plan-digest, predecessor, and explicit invalidation evaluation; Git history does not synthesize authority changes.

#### 4.3.3 Predecessor and supersession closure

Complete currentness evaluates predecessor receipt IDs in authored order with memoization. Missing predecessors,
invalid predecessors, and cycles return `ERR_RECEIPT_PREDECESSOR_MISSING`, `ERR_RECEIPT_PREDECESSOR_INVALID`, and
`ERR_RECEIPT_PREDECESSOR_CYCLE`, respectively, with the blocking receipt ID. A supersession receipt contains a
non-empty sorted `invalidated_receipt_ids` set and its corrective finding/job identities. Any such reference returns
`ERR_RECEIPT_SUPERSEDED` for the named receipt regardless of receipt ID order or `issued_at`; timestamps are evidence,
not causal ordering. Repeated evaluation of a shared predecessor returns the same immutable projection.

When a successor receipt's closure fully covers a predecessor receipt's closure, currentness still evaluates the
predecessor's schema, authority, node-plan digest, supersession state, and recursive predecessors but does not reuse
the predecessor's code-revision result; the successor proof now owns that complete evidence boundary. This rule also
applies prospectively during `finish_build`: the engine evaluates the candidate build closure against its plan receipt
before issuing the build receipt. Full coverage permits the packet's intended descendant changes, while partial
coverage or an uncovered stale predecessor returns `ERR_RECEIPT_PREDECESSOR_INVALID`. Without this prospective check,
a packet commit would invalidate the plan receipt whose closure authorized the same paths and no tracked build could
finish.

Graph dependency gates apply the same rule to the complete accepted dependency set. Reconciliation publication,
dependent build start, and terminal-audit assembly resolve accepted nodes in canonical authority order: direct
dependencies retain the node's authored `dependencies` sequence, while dependent and terminal-node enumeration retain
`DeliveryGraph.nodes` order. A current, causally downstream accepted dependency may suppress only the code-currency
evaluation of an earlier accepted dependency whose complete closure it covers; the covered receipt and every other
currentness dimension remain required. Partial coverage, coverage from an unrelated sibling, a missing acceptance, or
more than one current accept job for the same dependency remains fail-closed. This keeps a dependent build eligible
after a later accepted dependency has intentionally changed and re-proved shared paths while preserving the authored
acceptance identities for every direct graph dependency.

## 5. Delivery Graph

The admitted delivery graph is complete before implementation work enters Kanban. It models general obligations, not historical incident-specific fields.

### 5.1 Required entities

- product requirements and negative requirements;
- preserved behaviors and accepted exclusions;
- normal workflows and observable results;
- modules and contract authorities;
- changed interfaces with producer, consumer, contract, owner, failure semantics, migration disposition, and proof;
- migrations/removals with ordered steps, consumer inventory, compatibility disposition, deletion owner, and absence proof;
- risks with scenario families and dispositions;
- proof contracts with boundary, executor capability, setup, allowed replacements, commands/observations, and durable outputs;
- delivery nodes with owned obligations, affected modules/interfaces, dependencies, acceptance, and proof ownership.

### 5.2 Delivery node boundary

A delivery node is independently plannable and independently acceptable. It owns one coherent delivery result and all cross-boundary obligations necessary to prove that result. Nodes split when ownership, dependency order, failure domain, proof environment, or agent context materially differs. They do not split by file type or framework layer alone.

### 5.3 Completeness rule

Every admitted obligation has one accountable delivery owner and one proof path. Shared prerequisites may serve several nodes, but observable completion has one owner. The graph includes explicit integration/proof nodes whenever code, fixtures, generated clients, environments, harnesses, or assembled workflows must be built before acceptance.

## 6. Frontier Planning and Packet Plans

Admission creates one initially plan-ready `plan` job record per delivery node because admission has
already sealed every predecessor contract. The planner consumes these jobs in stable topological
order so predecessor plans inform dependent plans without making predecessor implementation a gate.
Authority currentness, pending requests, claims, terminal disposition, and the global writer lease
remain dispatch gates.

One resumable planner may process several engine-selected plan-ready jobs in a warm session, but
each job independently validates, challenges, and atomically writes only its node plan before
creating either one build job per packet plus one dependency-gated `accept` job, or no build jobs
plus one `accept` job for an eligible verification-only plan. A plan job receives:

- the complete current `ChangeRevision`;
- its target delivery node;
- predecessor receipts and relevant source state;
- repository and contract-authority tools;
- the node-planning policy and independent plan reviewer.

After each atomic completion, the planner obtains a fresh engine plan. A failed node publishes no partial plan and does not roll back previously completed nodes.

The initial plan receipt records the admitted predecessor contracts it consumed. A packet build job
becomes ready only when its plan receipt remains current, every authored packet dependency is
current, and every predecessor delivery node has a current accept receipt. `finish_accept`
atomically issues the predecessor receipt, marks each dependent plan reconciliation-required, and
creates or releases its corrective `plan` job. The dependent build remains blocked until that job
publishes a superseding plan receipt based on the accepted implementation evidence. Invalidation of
a predecessor accept receipt invalidates the dependent reconciled plan/build closure. Final audit
does not participate in this release and cannot mutate a plan.

### 6.1 Legal refinement

A packet plan may:

- choose implementation boundaries inside admitted modules and interfaces;
- split work by genuine dependency, authority, failure domain, incompatible tool, or context limit;
- combine production code, tests, documentation, generated artifacts, migration, and focused proof for one outcome;
- add implementation detail and proportionate proof commands inside the admitted proof boundary.
- partition one unchanged proof case set into bounded commands when an enforced runner limit prevents
  one process from completing; every partition must run at the same exact revision with zero exit,
  and the combined evidence must record the limit name and configured bound, exact revision, each
  partition's selector, collected case identities, and exit status, plus the expected and observed
  aggregate case identities demonstrating complete coverage without deselection or boundary replacement.

### 6.2 Illegal expansion

A plan job must return to interactive Specification when it discovers or proposes:

- a new or weakened product outcome;
- a new public or cross-module interface edge;
- a changed producer, consumer, contract authority, or failure semantic;
- a migration, removal, compatibility, security, destructive, concurrency, or lifecycle obligation absent from delivery authority;
- a new normal workflow or proof boundary;
- a dependency on an unadmitted delivery result;
- an unresolved material assumption.

The engine refuses a node plan whose references exceed the delivery node contract. The designer updates authority, obtains user decisions, re-runs admission, and invalidates affected jobs/receipts.

### 6.3 Packet contract

Each packet records:

- stable ID and outcome;
- delivery obligations advanced;
- in-scope and excluded work;
- modules and interfaces read/modified/produced/consumed;
- dependencies on packet or accepted-node receipts;
- acceptance scenarios;
- typed impact closure plus proof boundary and commands/observations;
- required outputs such as code, tests, docs, generated artifacts, migration, or evidence;
- domain/risk/tool profile used to load builder skills;
- expected context/change-envelope budget.

The planner must validate and canonicalize each packet impact closure before publishing its node plan. Packet
dependencies do not imply path ownership: a packet names the paths and authority targets its own proof consumes.
When a packet changes a path inside a predecessor receipt closure, the planner either includes and reruns that
predecessor's complete closure under §4.3.3 or returns Specification re-entry; it never treats an overlapping accepted
predecessor as current through a narrower local proof.

### 6.4 Verification-only re-admission contract

Verification-only planning is a narrow re-admission and self-hosting projection-refresh path, not a
second implementation mechanism. It is eligible only when all of the following are proven for the
plan job's exact candidate revision and current delivery digest:

1. The job belongs to the current re-admission generation or its acceptance-triggered reconciliation;
  an initial implementation plan for unimplemented work is ineligible.
2. Source-grounded inspection maps every node-owned obligation, module/interface effect, migration,
  required output, and durable proof mechanism to tracked state already present at that candidate.
3. The inspected tracked scope is clean at the candidate, requires no implementation, test,
  documentation, generated-artifact, migration, or proof-infrastructure delta, and has one explicit
  non-empty impact closure. Unknown, untracked, generated-but-missing, or ambiguous state is a delta.
4. The admitted proof can execute at the candidate without an acceptor creating tracked setup,
  harnesses, fixtures, clients, wiring, or other durable outputs.
5. The independent plan reviewer confirms the evidence and the absence of hidden delivery expansion.
  Existing bootstrap or legacy records may corroborate inspection but cannot satisfy any native
  receipt, proof, currentness, or predecessor requirement.

The published plan records `mode: verification-only`, `packets: []`, the exact candidate revision,
generation identity, evidence above, and its node-level impact closure. `finish_plan` fails closed on
any missing or mismatched field, creates no build jobs, creates exactly one accept job, and issues a
normal plan receipt. The accept job has no build-job predecessors, but it remains gated by the plan
receipt and predecessor-node acceptance rules. Its independent read-only acceptor executes the full
admitted node proof in a disposable checkout of that exact candidate and issues the new-digest accept
receipt only on success.

Any needed tracked change, missing output, unavailable durable proof mechanism, candidate mismatch,
uncertain scope, failed plan review, or failed acceptance routes to normal packet planning and build
ownership. Verification-only planning never converts historical records into native receipts, never
authorizes acceptor edits, and never weakens proof commands, boundary, outputs, reconciliation, or
receipt currentness. `finish_accept` performs the same dependent-plan reconciliation and invalidation
transitions for either plan mode.

DN-016 and DN-015 remain mandatory build-plus-accept terminal nodes. Their native-store handoff,
board retirement, snapshot/finalization outputs, and commits do not exist at the admitted candidate,
so neither can satisfy verification-only eligibility.

## 7. Kanban Job Model

A Kanban card is one purpose-specific agent job. Its `kind` determines the board column and assigned agent:

| Kind | Agent transformation | Success receipt |
| --- | --- | --- |
| `plan` | Delivery node -> complete packet DAG | `plan` |
| `build` | Packet contract -> committed implementation and inline review | `build` |
| `accept` | Delivery node plus descendant receipts -> independent node verdict | `accept` |
| `audit` | Accepted delivery graph -> final product verdict | `audit` |

Archive is the universal terminal disposition, not a fifth agent-work column. A successful plan, build, accept, or audit job issues its purpose-specific receipt and moves to archive; the final audit receipt also closes the change. Cards never change kind or move backward. Dependency readiness, claim activity, pending requests, blocked state, staleness, cancellation, supersession, and failed attempts are properties or dispositions rather than columns.

### 7.1 Job record

Job files are structured YAML under the configured native work root's `jobs/` directory; archived
jobs move to its `archive/` directory. Fresh native workspaces use `.owlbear/native`, while the
self-hosting handoff copies typed native records there from the mixed `.owlbear/kanban` carrier. A
job stores only:

- numeric job ID, kind, priority, timestamps;
- `change_id`, authority digest, target ID, optional node-plan digest;
- predecessor receipt requirements;
- claim and block metadata;
- pending request IDs;
- latest attempt/finding/receipt references;
- supersession/cancellation disposition.

Title, outcome, acceptance, modules, interfaces, and proof are projected from authority when the job is read. They are never copied into the job file.

### 7.2 Attempts and activity

Claims and attempts remain append-only operational events. A failed or crashed attempt does not mutate the graph. A later attempt may claim the same open job until success, cancellation, or supersession. Successful jobs and rejected acceptance/audit attempts create durable receipts/findings.

### 7.3 Native job start contract

`JobRecord.disposition` is the strict enum `pending | cancelled | superseded`; only `pending` is
startable. Unknown values are malformed persisted state, not future-compatible terminal states.

The transport-free `NativeRuntime.start_job(StartJobRequest)` boundary accepts caller-supplied job,
attempt, claim, actor, process, and claim-timestamp identity plus the candidate code revision needed
for receipt-currentness evaluation. The runtime loads the authoritative `ChangeRevision`, current
job and predecessor jobs, their required receipts, pending-request state, and the existing attempt
identity from its stores; callers do not supply readiness projections or mutate stores directly.

`StartJobResult` contains either the updated stored job plus its immutable `started` event, or one
`StartJobDiagnostic` with a stable code from:

- `ERR_START_AUTHORITY_STALE`;
- `ERR_START_PREDECESSOR_INVALID`;
- `ERR_START_REQUEST_PENDING`;
- `ERR_START_TERMINAL`;
- `ERR_START_ACTIVE_CLAIM`;
- `ERR_START_IDENTITY_CONFLICT`.

Diagnostics retain optional lower-layer code and target fields as evidence, but those values do not
replace the public start code. Eligibility checks run in the order listed above: authority, complete
predecessor receipt currentness in authored predecessor-job order, pending requests, terminal
disposition, then active claim identity. An eligible start atomically replaces the job with
`claim_id` and `attempt_id` and creates sequence-one `started` event data at the supplied timestamp.
Replay with the same active attempt, claim, actor, process, and claim-timestamp identity returns the
stored job/event. A different active claim or attempt pointer, or only one populated pointer, returns
`ERR_START_ACTIVE_CLAIM`; when both pointers match but actor, process, or claim timestamp differs,
replay returns `ERR_START_IDENTITY_CONFLICT`. Neither branch appends another event.

### 7.4 Native job finalization contract

Every schema-version-one `AttemptEvent` carries required `claim_id` alongside attempt, job, actor,
process, and timestamp identity. Sequence-one `started` events copy it from `StartJobRequest`;
sequence-two `released` and `failed` events copy it from their finalization request. Persisted event
data with missing or empty `claim_id` returns `ERR_ATTEMPT_EVENT_IDENTITY_INVALID` rather than being
compatibility-migrated.

`NativeRuntime.release_job` and `NativeRuntime.fail_job` clear only matching active job pointers and
atomically append their immutable sequence-two event. Once those pointers are clear, replay compares
job, attempt, claim, kind, actor, process, timestamp, detail, and evidence against the stored event.
The same identity returns the existing job/event without mutation. A request that differs only by
claim returns the operation-specific `ERR_RELEASE_NON_OWNER` or `ERR_FAIL_NON_OWNER`; it never returns
the existing outcome or appends another event. This completed-event ownership check precedes the
no-active-pointer check. More generally, when a sequence-two event belongs to the requested job and
attempt, any mismatch in claim, kind, actor, process, timestamp, detail, or evidence returns the
operation-specific non-owner diagnostic. Cleared pointers return the operation-specific
no-active-claim diagnostic only when the requested job and attempt have no sequence-two outcome.

### 7.5 Native expired-claim recovery contract

`NativeRuntime` receives required positive `claim_expiry: timedelta` as stable injected policy. Zero
or negative duration is rejected at construction. Native recovery does not load legacy
`BoardConfig.pipeline.claim_timeout` and callers cannot override expiry per request.

`RecoverExpiredClaimsRequest` contains supplied timezone-aware `recovered_at`, `actor_id`, and
`process_id`. `NativeRuntime.recover_expired_claims(request)` first completes pending runtime
transactions, then reads active jobs in ascending job-ID order. It resolves each active claim from
the job's claim and attempt pointers plus its sequence-one `started` event. Missing or inconsistent
pointers, event identity, or claim timestamp produce `ERR_RECOVERY_IDENTITY_INVALID` for that job.

A claim is expired only when `recovered_at` is strictly later than the started-event timestamp plus
`claim_expiry`; equality remains active. Recovery atomically clears the matching job pointers,
keeps disposition `pending`, sets `updated_at` to the supplied recovery time, and appends one
sequence-two `crashed` event. The event retains the active job, attempt, and claim identity, records
the recovery request actor/process/time, uses detail `claim expired`, and carries no evidence IDs.

`RecoverExpiredClaimsResult` contains recovered job/event pairs and per-job diagnostics, each ordered
by job ID. A transaction destination conflict produces `ERR_RECOVERY_CONFLICT` for only that job and
does not undo earlier recovered jobs. Non-expired jobs and jobs already resolved by release or fail
produce neither an outcome nor a diagnostic.

An exact repeated request returns the existing crash job/event outcomes without duplicate events.
This replay is discovered from persisted job `updated_at` plus matching sequence-two crash events, so
a newly assembled runtime reaches the same result without in-memory state or a separate recovery
index. A later retry changes the job timestamp and therefore is not mistaken for the earlier replay.

## 8. Agent Architecture

### 8.1 Designer

The user-facing designer owns one resumable pre-Kanban session. `/ideate` creates/selects a change and enters discovery mode; `/design` creates/selects the same session directly. The designer:

- persists confirmed intent and decisions as they occur;
- researches repository facts instead of asking the user;
- delegates focused external research, architecture review, interface audit, threat/risk review, and proof analysis to fresh read-only specialists;
- asks one material decision at a time with options, pros, cons, risks, recommendation, and confidence;
- produces the complete delivery graph;
- runs deterministic validation, an independent admission challenge, and baseline commands;
- presents the complete change and requests explicit admission approval.

The designer may write only the current change authority, focused research, and scratch diagnostics. It does not implement product code or create Kanban work before admission.

### 8.2 Frontier planner

The resumable planner processes engine-selected initial or reconciliation `plan` jobs from the
current frontier. For each node it writes only that node's plan and resulting jobs, invokes a
read-only plan reviewer, and either issues a plan receipt or returns a material discovery to the
designer. It cannot change admitted delivery authority. After a predecessor acceptance receipt, the
engine marks dependent plans reconciliation-required and blocks their builds until the planner
publishes superseding plans against accepted implementation evidence. One material choice creates a
Decision Request; broader design discussion re-enters Specification.

For a re-admission projection refresh, the planner may instead publish the verification-only form in
§6.4. It owns source inspection and eligibility evidence, but it does not certify implementation;
the fresh acceptor remains the only owner of the new-digest node verdict.

### 8.3 Builder

One fresh top-level builder invocation processes exactly one `build` job in the shared worktree.
It cannot pick or start a subsequent job before returning its structured lifecycle result. It:

- verifies the exact packet digest and change envelope before editing;
- implements all outputs needed for the packet outcome;
- chooses proportionate durable tests under the existing Rent Test;
- runs focused proof and commits owned paths;
- invokes a mandatory read-only build reviewer with system-generated authority, diff, changed paths, proof, and commit context;
- repairs concrete findings in the same session and re-runs review;
- issues a build receipt only after review passes.

The reviewer cannot edit files, choose product direction, or ask for generic extra tests. It reports typed findings against packet obligations, code, scope, and proof.

### 8.4 Acceptor

The acceptor processes one `accept` job after all required build receipts are valid, or after an
eligible verification-only plan has established that no build receipts are required. It is independent
and cannot edit tracked files. The engine materializes the target commit in a disposable proof checkout.
The acceptor may inspect code, execute commands, start services, create temporary scratch stores/fixtures,
and capture logs/screenshots. It verifies:

- every delivery obligation and interface edge owned by the node;
- packet coverage and actual changed surfaces;
- the admitted assembled proof boundary;
- exact committed code revision and clean proof checkout;
- absence of stale or superseded prerequisites.

Pass creates an accept receipt. Failure creates typed findings and engine-generated corrective jobs. The acceptor never patches its own findings.

Successful acceptance also makes dependent plans reconciliation-required and blocks their builds
until superseding plan receipts exist. It does not wait for final audit.

### 8.5 Auditor

The auditor processes the single `audit` job after every required node has a valid accept receipt. It is independent and read-only over tracked files. The engine materializes the target commit in a disposable proof checkout. The auditor executes all admitted normal workflows there, checks Product Promise and accepted decisions, confirms migration/removal and absence proofs, and verifies that no invalid or unresolved receipt/request remains. Pass creates the final audit receipt and closes the change mechanically. Failure creates typed findings and minimum corrective jobs.

### 8.6 Orchestrator

The orchestrator has no product or scheduling authority. The engine's graph-aware `pick_jobs`
result selects each eligible job and assigned profile; the orchestrator invokes that profile once
for that job and maps its structured result to the matching engine lifecycle operation. It never
parses prose to route work, and an invoked agent cannot repick or continue into another job.

- tracked-file-mutating `plan` and `build` jobs are globally serialized;
- `accept` and `audit` never overlap a writer;
- read-only nested specialists/reviewers may run inside the owning session;
- claims expire and are recoverable;
- structured results finalize attempts through engine tools;
- the loop stops only when no dispatchable job remains or the user intervenes.

### 8.7 Retired roles

The standalone verifier, verifier-challenger, collector, OpenSpec agents/skills/prompts, and advisory task decomposition are removed. Current healthy behavior is redistributed to the builder's inline reviewer, independent node acceptor, final auditor, designer challenge, and deterministic engine gates.

## 9. Admission

Admission is a layered change-level operation, not a file-presence check.

### 9.1 Deterministic validation

Stable diagnostics reject at least:

- uncovered requirements, negative requirements, preserved behaviors, or design obligations;
- incomplete interface producer/consumer/contract/owner/failure/proof fields;
- incomplete migration/removal ordering, consumer inventory, deletion, or absence proof;
- missing destructive/concurrent/security/lifecycle/compatibility risk dispositions;
- proof mechanisms with no build-capable owner;
- acceptance/audit as the first owner of tracked harness, fixture, generated client, or wiring;
- dependency cycles, dangling references, unreachable workflows, or disconnected delivery nodes;
- proof that replaces the boundary it claims to exercise;
- authority conflicts or unresolved material decisions;
- node scope exceeding declared modules/interfaces or proof boundary;
- stale digests or unsupported exceptions.

The canonical proof model makes the two proof-ownership checks structural: `Proof.owner` resolves only to a delivery
node, and deterministic validation requires that node to own the proof and precede each node that consumes it.
Acceptance and audit are job stages, not delivery-node identities, so they cannot satisfy `Proof.owner`; tracked proof
infrastructure therefore has a build-capable node owner before either read-only stage runs.

Diagnostics contain code, severity, target ID, evidence, detail, and remediation.

### 9.2 Repository-grounded challenge

A fresh read-only challenger compares authority with current source, generated/public contracts, normal workflows, module ownership, and plausible omissions. It returns one disposition per requirement, interface, migration, material risk, proof, workflow, and node. Free-form `pass` is invalid.

### 9.3 Baselines

The designer runs proportionate clean baselines before admission: affected package builds/typechecks, generated-contract checks, focused tests, and the cheapest existing normal-boundary smoke needed to establish current feasibility. Baselines are evidence about the starting system, not proof of unimplemented behavior.

### 9.4 User approval

The user approves product intent, accepted exclusions, material decisions, architecture, delivery-node boundaries, and known limits. The user is not asked to certify graph mechanics. Approval is recorded in the admission receipt against the delivery digest.

### 9.5 One-time bootstrap admission and carrier

This replacement is the only change that cannot enter through the native engine it creates. Its
bootstrap uses the current pipeline as a disposable execution carrier under these constraints:

1. The tested baseline is an exact clean `owlbear-dev` commit. The current pipeline executable is a
  separately clean `../owlbear` checkout synced from that development lineage. MCP processes run
  code from the sibling checkout while their cwd, authority, Kanban, memory, knowledge, and product
  paths remain in `owlbear-dev`.
2. The designer applies `delivery-v1`, deterministic graph checks, the repository-grounded challenge,
  clean baseline evidence, and explicit user approval without relying on the not-yet-built admission
  engine.
3. The designer writes one immutable
  `receipts/admission-<delivery-digest-prefix>.yaml` record with `schema_version`, `kind`, `receipt_id`,
  `change_id`, `delivery_digest`, `issued_at`, tested baseline SHA, carrier source and sync SHAs,
  deterministic diagnostics, one challenge disposition per graph entity, baseline commands/results,
  user approval, bootstrap projection policy, and known limits. The receipt is written before any
  implementation task is created.
4. Each delivery node is projected into the current Kanban as one graph-referencing aggregate plus
  bounded packet work shaped through the existing pipeline. Projection records carry `change_id`,
  delivery-node ID, and delivery digest; copied operational acceptance text is non-authoritative and
  may not add, weaken, or supersede graph obligations. Dependencies preserve the admitted delivery
  DAG. Any authority edit makes the projection stale and stops dispatch until a new admission receipt
  and projection exist.
5. Existing builder, verifier, challenger, and collector records provide bootstrap execution evidence;
  they do not become native receipts and cannot certify the replacement's final Product Promise.
  The native historical replay, full workflow, independent node acceptance, and whole-change audit
  in DN-013 and DN-014 must re-prove the assembled system at an exact commit before cutover.
6. DN-012 removes the old pipeline from the product revision and consumer distribution and proves the
  public cutover and typed native-store handoff commands against populated and fresh temporary
  repositories. The current workspace's legacy board remains external bootstrap-carrier state only
  long enough to dispatch and record DN-013's native proof and leave every legacy projection,
  including the root, released and ready for terminal disposition. The engine then selects DN-016's
  normal build job. Its claim and global writer holder are the only permitted live lifecycle
  identities while every other native process stops. The builder invokes IF-017 to copy the complete
  typed inventory into `.owlbear/native`, verify exact hashes and identities, and write a prepared
  handoff record. An isolated maintenance probe starts with `OWLBEAR_WORK_ROOT=.owlbear/native` but
  exposes only read-only parity and activation checks; normal MCP, Cockpit, and orchestration mutation
  remains disabled. IF-017 publishes immutable activation only after destination parity and unchanged
  source hashes plus launch readiness pass. The same atomic activation publishes retained
  `.owlbear/native-root.yaml` outside both lifecycle stores. Before activation, selector absence
  preserves the existing `.owlbear/kanban` startup default, including for a fresh consumer; setup and
  seed do not pre-create `.owlbear/native` or the selector. This default applies only while the
  retained destination is absent; `.owlbear/native` without the selector is transitional or corrupt
  state and blocks startup, so selector loss cannot silently rebind processes to source. After
  activation, one MOD-001 resolver
  shared by setup, MCP, and
  Cockpit startup resolution validates the selector and chooses exactly `.owlbear/native`; malformed,
  unsafe, conflicting, or destination-inconsistent state fails startup without source fallback or a
  second lifecycle-store read. Environment configuration may select a root only when no activation
  selector exists and must not override an activated selector. A destination-only completion runtime suppresses expiry
  recovery and unrelated mutation while DN-016 `finish_build` completes; normal processes then start
  on the destination for independent acceptance. Post-activation recovery is destination-only. No
  runtime hot-swap or jobless lease is required. Source
  copies remain inert input to finalization. IF-018 sets `terminal_plan_prerequisite: true` and
  declares itself the terminal plan prerequisite;
  dispatch resolves its producer DN-016 and consumer DN-015 from the admitted interface graph rather
  than a hardcoded node pair. The engine selects DN-015's `build` job only from the retained root, and the
  orchestrator invokes one builder with explicit finalization approval. That builder runs the
  finalizer, verifies the immutable manifest and hashes, writes the finalization receipt, removes
  active legacy board and workspace-local sibling-carrier activation state, and commits those tracked
  changes. The separately clean sibling checkout remains on `main`. Native build finalization
  records the commit through the retained root without touching a legacy task. A distinct `accept`
  job then verifies the exact commit in a disposable read-only checkout before issuing the DN-015
  accept receipt through that same root. No later legacy lifecycle mutation occurs. No bootstrap
  loader, legacy receipt adapter, command alias, or compatibility mode enters the native runtime or
  consumer distribution.
7. Before any re-admission that depends on verification-only plans, the current carrier implements
    the minimum missing native capability under DN-003: discriminated plan validation, zero-build job
    publication with one accept job, non-empty node-level closure/currentness, exact-candidate accept
    evidence, replay/transaction behavior, and focused runtime tests. DN-004/IF-015 then proves the
    unchanged `finish_plan` operation transports an empty `build_job_ids` tuple without a new tool or
    lifecycle alias. These carrier records are supporting implementation evidence only. Re-admission
    at the resulting candidate creates the new native plan and accept receipts; no carrier record is
    imported or promoted.

  The planning omission that triggered this re-entry was observed at candidate
  `2578367095d004b2ebcb00bca890560dc24c34ba`: DN-001's packet-owned implementation and tests were
  present, its 27 public loader tests passed, and builder job 59 returned
  `SpecificationReentry/planning-omission` because no scoped tracked delta or commit existed to build.
  That source inspection identified DN-003/IF-003 and PROOF-003 as the minimum bootstrap owner;
  DN-004/IF-015 and PROOF-014 own only proof that the unchanged MCP operation transports and coordinates
  the result. Candidate `be82c31005d41ccd888af8a1d90b33a817b51d0c` now implements the missing carrier
  capability and focused runtime proof. These carrier results are supporting implementation evidence,
  not native receipts or final certification.

8. Before the re-admission following the DN-002 planning re-entry, the current carrier implements the
   minimum DN-003 receipt-currentness correction: packet target validation admits the complete canonical
   closure of a consumed predecessor receipt, and `finish_build` applies §4.3.3 successor coverage to the
   prospective build receipt before evaluating its plan predecessor. Focused runtime tests prove that a
   fully covering packet can finish after intended descendant changes, while partial overlap and uncovered
   predecessor drift remain mutation-free failures. The carrier commit is supporting bootstrap evidence only;
   the new digest must independently plan and accept DN-003, and any DN-002 packet that overlaps DN-001 must
   rerun the complete DN-001 proof boundary.

The admission receipt limit states that bootstrap task mutation is not atomic with receipt creation.
Task creation is idempotent by `(change_id, delivery_digest, delivery_node_id, packet_id)` and dispatch
is forbidden until the complete projection audit passes. A partial projection is repaired or removed
before work starts; it never weakens the admitted graph.

## 10. Invalidation, Findings, and Corrective Jobs

Findings are structured and target requirements, interfaces, migrations, risks, workflows, delivery nodes, packets, proofs, receipts, or code revisions.

| Finding class | Corrective route |
| --- | --- |
| Packet implementation or local proof defect | New `build` repair job |
| Packet boundary/dependency/proof-plan defect within admitted node | New `plan` revision job for that node |
| Product, interface, migration, risk, architecture, or delivery-proof defect | Global `/design` re-entry and re-admission |
| Node integration defect after valid packets | New build-owned integration/repair packet through node plan correction |
| Whole-change integration defect within admitted obligations | Corrective node plan/build jobs, then re-accept and re-audit |

The invalidation engine computes affected descendants from graph and receipt dependencies. It appends a supersession receipt, marks old receipts invalid, cancels or supersedes stale open jobs, and creates the minimum new corrective jobs. Prior records remain immutable. The Cockpit defaults to the latest valid chain but exposes full history.

Late work is classified explicitly:

- `implementation-defect`: planned obligation implemented incorrectly;
- `unforeseeable-discovery`: evidence unavailable at admission despite adequate grounding;
- `planning-omission`: obligation was knowable but absent;
- `scope-change`: user-approved change after admission.

Only `planning-omission` counts against the primary redesign success metric.

## 11. Decision and Action Requests

Requests remain structured but no longer depend only on task IDs. A request records:

- request ID, kind, title, summary, body, agent, timestamps;
- `change_id`, authority digest, optional job ID and graph target ID;
- decision options with label, pros, cons, risks, recommendation, confidence, and rationale;
- exact evidence/resume condition for actions;
- structured resolution and resulting invalidation disposition.

During `/design`, live user choices use `askQuestions` and are written directly to `decisions.yaml`.
Runtime requests live under the configured native work root's `requests/{pending,resolved}/`
directories. A resolution that changes material authority routes to `/design`; local
implementation/action resolutions unblock only the dependent job slice.

## 12. Shared Worktree and Commit Contract

- The orchestrator dispatches no overlapping tracked-file writers.
- A plan or build job starts from a recorded clean or explicitly bounded base commit.
- Builders may coexist with unrelated user modifications while implementing when scoped ownership remains unambiguous.
- Acceptance and audit use a disposable read-only checkout of the exact tested commit under `.owlbear/scratch/proof/<job-id>/`; unrelated shared-worktree changes neither block nor influence proof.
- The proof checkout uses the workspace's normal toolchain and environment while isolating tracked files. Reused caches and external services are recorded when they affect evidence.
- Proof-checkout creation, containment, and deletion are engine-owned and crash-safe. Orphaned proof checkouts are health findings and safe cleanup targets.
- Each successful plan/build/accept/audit job owns one logical scoped commit containing its durable control-plane files and, for builders, product files.
- Inline reviewers are read-only and do not commit.
- Acceptance/audit receipts record the tested commit, commands, environment-relevant facts, replacements, outputs, and result.
- Control-plane-only receipt commits may follow the tested code commit; the receipt records the tested code SHA explicitly.
- A later descendant remains current only when the receipt evaluator proves that repository-history paths do not
  intersect the receipt's frozen impact closure. Delivery and node-plan digests plus explicit invalidation separately
  classify authority-target changes. Missing, ambiguous, malformed, unsafe, or non-descendant history is stale.

## 13. `owlbear-kanban` Internal Design

The package remains the transport-free facade, but the current large `engine.py` is replaced by cohesive owners rather than extended.

```text
owlbear_kanban/
  engine.py              # Thin facade and transaction coordination
  models/
    change.py            # ChangeRevision and authority metadata
    graph.py             # Joined delivery graph and isolated node plans
    job.py               # Purpose-specific jobs and projections
    evidence.py          # Attempts, findings, receipts, validity
    request.py           # Change/job-scoped requests
  stores/
    change.py            # Modular package load and canonical digest
    job.py               # Active/archive job storage and OCC
    receipt.py           # Immutable receipt storage
    request.py           # Pending/resolved request storage
    activity.py          # Append-only operational events and sessions
  admission.py           # Deterministic validation and receipt assembly
  invalidation.py        # Dependency closure, supersession, corrective jobs
  dispatch.py            # Readiness, claims, writer compatibility, waves
  transitions.py         # Purpose-specific job completion transactions
  health.py              # Change/graph/job/receipt/request integrity
  snapshot.py            # One-time legacy snapshot and inventory
  storage_io.py          # Atomic writes, locks, containment, fsync
```

No caller mutates stores independently. Engine transactions validate references, write temp files, fsync, rename atomically where possible, append activity, and return structured projections. Multi-file operations use a transaction manifest and deterministic recovery so a crash cannot leave a receipt without its job/graph update.

The self-hosting bootstrap initially implemented `shape` vocabulary in DN-003/DN-004 and the IF-015
MCP bridge. DEC-033 and MIG-004 made that work stale: DN-003 replaced job, receipt, request, and
transaction discriminators; DN-004 replaced dispatch profiles and `finish_shape` with
`finish_plan`; DN-009 exposes only the corrected assembled API. No `shape` compatibility alias or
dual registration survives re-admission or cutover.

## 14. MCP Contract

The MCP server exposes intent-level tools rather than generic file-like task mutation:

DN-004 first exposes the minimum native work bridge needed by the VS Code orchestrator:
`pick_jobs`, `start_job`, purpose-specific finish operations, `release_job`, and expired-claim
recovery. These tools are thin strict adapters over `DispatchRuntime`; they add no authority or
alternate lifecycle semantics. DN-009 then completes the control plane with change, admission,
request, evidence, health, history, and remaining read surfaces. This split preserves one MCP
transport for agents while avoiding a DN-004/DN-009 bootstrap cycle.

For `plan | build`, the bridge `start_job` result is the strict dispatch start result. For
`accept | audit`, the adapter first prepares IF-005 at the requested candidate commit, then starts
the claim and returns the strict dispatch result plus the contained checkout path, canonical commit,
and manifest path. Checkout setup failure creates no claim. A rejected start removes the prepared
checkout. The matching finish, release, and expired-claim recovery adapters clean the checkout
idempotently; a residual checkout is a typed health finding and forbids a valid accept or audit
receipt. This composition does not change IF-003 or add another MCP operation.

### Change/design tools

- `list_changes`
- `show_change`
- `validate_change`
- `admit_change`

### Work tools

- `list_jobs`
- `show_job`
- `pick_jobs`
- `start_job`
- `finish_plan`
- `finish_build`
- `finish_accept`
- `reject_accept`
- `finish_audit`
- `reject_audit`
- `release_job`
- `recover_expired_claims`

### Request tools

- `create_request`
- `list_requests`
- `show_request`

Resolution remains user/Cockpit controlled.

### Health/history tools

- `change_health`
- `work_health`
- `list_activity`
- `list_attempts`
- `list_findings`
- `show_finding`
- `show_receipt`

Generic `create_task`, `edit_task`, `move_task`, arbitrary status transitions, parent mutation, and OpenSpec tools are removed. Plan and corrective transactions are the only ways implementation jobs enter Delivery.

## 15. Cockpit Product Experience

Specification and Delivery are peer top-level surfaces. Changes defaults to the current Specification revision; Delivery defaults to current executable work and its evidence.

### 15.1 Board

Columns are `Plan`, `Build`, `Accept`, and `Audit`. Cards show projected graph title/outcome plus operational signals:

- change and delivery-node identity;
- priority and job kind;
- dependency readiness;
- claim/session age;
- pending request or explicit block;
- current/stale/superseded authority digest;
- latest finding and attempt count;
- receipt state.

Cards are filtered/grouped by change, delivery node, domain, risk, job kind, readiness, block, and owner. Manual drag between columns is removed because job purpose is immutable. User actions are prioritize, cancel, release claim, inspect, and resolve request.

### 15.2 Changes

A Changes view lists draft, admitted, executing, accepted, abandoned, and superseded changes. Change detail exposes:

- Product Intent and decisions;
- implementation design and named authorities;
- delivery graph with requirement/interface/migration/proof overlays;
- node packet plans after planning;
- admission diagnostics and receipt;
- jobs, attempts, findings, receipts, and exact tested commits;
- invalidation/supersession chain;
- final audit result.

### 15.3 Requests and history

The existing request-resolution interaction is retained and expanded with pros, cons, risks, recommendation, and confidence. Activity/session views join jobs to graph targets. Legacy history is an immutable inventory, not an executable board.

Memory and Ideas remain unchanged peer utilities through the shell and routing rebuild. DN-011 proves route and core-workflow continuity but does not expand either utility or make it Specification, Delivery, or execution authority.

### 15.4 Frontend constraints

- Preserve PDS, current accessibility, keyboard, focus, SSE invalidation, filtering, conflict handling, and responsive shell behavior.
- Use list/outline views as the mobile baseline; graph visualization is an enhancement, never the only way to inspect or navigate work.
- Support at least hundreds of graph nodes/jobs through incremental loading or virtualization.
- Never encode status by color alone.
- Verify desktop and mobile with Playwright, screenshots, and nonblank/layout checks.

## 16. Atomic Cutover

The replacement is developed behind the current repository but is not shipped in mixed mode.

For the self-hosting replacement, DN-012 completes and fixture-proves the product, distribution,
typed native-store handoff, and carrier cutover below without mutating the board that still carries
DN-013. DN-013 then proves the complete native workflow. Once every legacy projection is released and
ready for terminal disposition, the engine selects a mandatory DN-016 build. Its sole writer claim
copies and verifies the complete native inventory under `.owlbear/native` and records immutable
source/destination hashes while every other native process is stopped. An isolated destination probe
runs in sealed read-only maintenance mode; activation is durable only after parity and unchanged-source
plus launch-readiness checks pass. A destination-only completion runtime finishes DN-016 with expiry
recovery and unrelated mutation suppressed; normal processes start afterward for read-only acceptance.
Post-activation recovery never returns to the source. This is an offline restart boundary, not an in-process work-root
mutation or jobless operation. The old native copies become inert carrier content before DN-015
planning or dispatch. DN-015's engine-selected build job then runs the
fixture-proven finalizer against that board,
verifies the immutable manifest and content hashes, writes the finalization receipt, removes active
legacy board and workspace-local sibling activation state, and commits the evidence without deleting
the separately clean sibling checkout. Native build finalization binds that commit
to the job through the retained root; a separate read-only accept job verifies the exact commit in a
disposable checkout and issues the node receipt through the same root. The operation is final and
cannot dispatch or record more legacy work. Future consumer cutovers use `.owlbear/native` directly
without this one-time carrier exception.

At cutover:

1. Stop pipeline dispatch and require no active claims.
2. Generate a manifest of every active OpenSpec change, Kanban task, archive record, pending/resolved request, and relevant evidence.
3. Require an explicit disposition for every active item: `reintroduce-native`, `completed-history`, `dropped`, or `superseded`.
4. Move the old stores into a versioned immutable legacy snapshot and verify manifest hashes.
5. Install an empty native change/job store plus accepted final receipt history for fresh consumers;
  for this self-hosting workspace only, DN-016 instead copies the complete live typed inventory under
  IF-017 before the legacy carrier is retired.
6. Remove OpenSpec package installation, config, generated prompts/skills, routing, tests, exclusions, docs, and source directories from active product paths.
7. Remove old task models, APIs, statuses, agents, skills, hooks, Cockpit mutations, and compatibility loaders.
8. Switch MCP, Cockpit, setup, seed, docs, and tests to the new contracts in the same release.
9. Run full regression, four incident replays, native end-to-end workflow, clean setup in a fixture consumer, Cockpit browser proof, and legacy snapshot integrity.
10. Enable dispatch only after final cutover audit passes.

The new engine contains no reader or migration path for old execution records. The legacy snapshot is ordinary historical data outside active control-plane paths.

## 17. Test and Proof Strategy

### 17.1 Durable unit/contract coverage

- strict model validation and canonical hashing;
- graph reference, coverage, interface, migration, risk, proof, cycle, reachability, and scope invariants;
- job/receipt identity and validity;
- request resolution and invalidation;
- atomic multi-file transactions, locks, crash recovery, and path containment;
- graph-aware dispatch and writer compatibility;
- fail-closed verification-only eligibility, zero-build plan publication, exact-candidate acceptance,
  reconciliation, replay, and transaction behavior;
- supersession and corrective-job minimality;
- snapshot manifest and disposition completeness;
- MCP and Cockpit response contracts.

### 17.2 Historical regression fixtures

The original defective and corrected browser lifecycle, workspace repair/removal, memory purge integration, and memory lifecycle clean-build plans become structured fixtures. Each defective form must fail with stable diagnostics before work exists; each corrected form must admit.

### 17.3 Generic anti-overfitting coverage

Use table-driven and property-based cases for dangling IDs, cycles, disconnected obligations, duplicate owners, interface omissions, migration gaps, risk dispositions, proof authorization, stale digests, superseded receipts, invalid exceptions, and random valid DAGs.

### 17.4 End-to-end scenarios

- rough `/ideate` entry -> resumed `/design` -> decision -> challenge -> admission;
- admitted graph -> frontier plan jobs -> packet DAG -> build with inline review -> node acceptance -> final audit;
- build defect -> corrective build job -> re-accept;
- packet-boundary defect -> corrective plan job -> new packets -> re-accept;
- delivery-contract defect -> global re-design -> re-admission -> precise invalidation;
- pending action/decision request -> resolution -> resumed job;
- crash/expired claim/transaction recovery;
- dirty worktree blocks acceptance/audit;
- legacy snapshot and fresh native startup;
- Cockpit desktop/mobile change, board, request, finding, and receipt workflows.

## 18. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Native framework recreates OpenSpec with more code | Implement only the modular authority, graph validation, plans, jobs, receipts, and closure required by this product; no plugin schema system or generic apply layer |
| Delivery graph becomes an enormous speculative plan | Seal product/interface/proof obligations only; defer implementation packets to bounded Delivery planning |
| Local planner hides global expansion | Namespace and reference enforcement plus independent plan review; any new delivery edge forces re-admission |
| Agent/session cost explodes | One resumable frontier planner with atomic per-node outputs; outcome-cohesive packets; inline packet review; no artifact-specific statuses |
| Shared worktree contaminates proof | Single writer for implementation, disposable exact-SHA proof checkouts for accept/audit, scoped commits, stale-boundary detection |
| Receipt/job files drift from graph | Jobs carry references/digests only; engine projects contracts and health-scans every reference |
| Verification-only planning becomes a shortcut around missing work | Restrict it to exact-candidate re-admission generations; require complete source/output/proof inspection, independent plan review, a non-empty node closure, and full fresh acceptance; any uncertainty or delta requires build packets |
| Bootstrap records are mistaken for native certification | Permit them only as corroborating inspection evidence; require new-digest native plan and accept receipts created by the current engine |
| Corrective jobs create board noise | Immutable history with latest-valid-chain default and grouped finding-set corrections |
| Bootstrap MCP bridge becomes a duplicate control plane | Keep its tool list closed to native job pick/start/finish/release/recovery, prove exact schemas and error mapping in DN-004, and require DN-009/cutover absence proof for any residual bridge-only surface |
| Deterministic validation creates false confidence | Admission receipt states limits; independent source-grounded challenge and executable baselines remain mandatory |
| Final audit again discovers missing infrastructure | Every proof mechanism must have a plan/build owner before admission; auditor is tracked-file read-only |
| Big-bang cutover loses unfinished work | Immutable hash-verified snapshot plus explicit active-item disposition inventory |

## 19. Rejected Technical Directions

- Custom OpenSpec schema: retains external machinery while OwlBear owns semantics.
- Universal research/architecture/test/docs statuses: turns work kinds into mandatory handoffs.
- Fully pre-decomposed packet graph: creates speculative microtasks at large scale.
- Recursively expandable delivery graph: removes the point at which completeness can be certified.
- Separate reviewer job for every packet: doubles context initialization without improving the meaningful node-level gate proportionally.
- Acceptor patch authority: destroys independent acceptance.
- Backward status movement or in-place reopening: conflates attempts and makes old evidence appear current.
- Per-job worktrees: rejected by user in favor of serialized shared-worktree writers.
- Separate delivery package above Kanban: splits graph/job transactions across owners.
- Runtime compatibility mode: conflicts with atomic cutover and preserves the old path of least resistance.
