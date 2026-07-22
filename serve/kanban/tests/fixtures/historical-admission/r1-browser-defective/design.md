# Implementation Contract: Graph-Authoritative Delivery

> **Change ID:** `r1-browser-defective`
> **Owning intake:** #1968
> **State:** Approved, pending admission
> **Authority:** This file owns technical realization. Product intent belongs in `intent.md`; material choices belong in `decisions.yaml`; stable identities and delivery ownership belong in `graph.yaml`.

## 1. Design Goals

The replacement must make these properties true by construction:

1. One durable change revision owns product intent, decisions, architecture, delivery obligations, interface edges, migration, risk, and proof.
2. Admission occurs before Kanban implementation and certifies layered delivery completeness for one exact revision.
3. Kanban remains the implementation control surface, but jobs reference graph authority instead of copying it.
4. The global graph is complete at delivery level; bounded node shaping adds implementation packets without changing admitted delivery obligations.
5. Every visible Kanban column names an agent transformation: `shape`, `build`, `accept`, or `audit`.
6. Builders retain warm context while a mandatory read-only reviewer challenges their packet.
7. Node acceptance and final change audit are independent, read-only over tracked files, exact-revision gates.
8. Findings create immutable corrective jobs and superseding receipts rather than moving cards backward or rewriting history.
9. Shared-worktree tracked mutations are serialized.
10. OpenSpec and the old task-authoritative pipeline disappear completely at cutover.

## 2. System Model

The control plane has four distinct responsibilities behind one `owlbear-kanban` facade.

```text
Authority plane                         Work plane
.owlbear/changes/<change-id>/           .owlbear/kanban/
  intent.md                               jobs/
  design.md                               archive/
  decisions.yaml                          requests/
  graph.yaml                              activity.jsonl
  receipts/
        |                                      |
        +------------ owlbear-kanban ----------+
                         |
                 MCP and Cockpit adapters
                         |
     designer | shaper | builder | acceptor | auditor | orchestrator
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
  graph.yaml
  receipts/
    <receipt-id>.yaml
```

The four root files are the editable authority. `receipts/` is engine-generated, immutable evidence rather than a fifth authored specification.

### 3.1 `intent.md`

Owns the problem, actors, Product Promise, normal workflows, visible failure behavior, scope, exclusions, preserved behavior, success conditions, assumptions, and technically-done-but-wrong outcomes.

### 3.2 `design.md`

Owns current-system evidence, architecture, module ownership, control/data flow, contract authorities, interfaces, lifecycle, migration/removal, safety, rejected alternatives, risks, and proof boundaries.

### 3.3 `decisions.yaml`

Owns material user decisions and supersession. Every option records pros, cons, risks, recommendation, rationale, and confidence. Runtime implementation questions do not enter this file unless their resolution changes intent, design, delivery obligations, compatibility, security, or proof meaning.

### 3.4 `graph.yaml`

Owns stable identities and relationships in two logical namespaces:

- delivery-authority root sections: `requirements`, `negative_requirements`, `preserved_behaviors`, `workflows`, `modules`, `interfaces`, `migrations`, `risks`, `proofs`, and `nodes`;
- `execution`: per-node packet plans created by successful shape jobs.

A shape job may write only its delivery node's `execution.node_plans` entry. Any change to `delivery`, `intent.md`, `design.md`, or accepted decisions requires global design re-entry and re-admission.

### 3.5 Receipts

Receipts are immutable YAML records with a versioned discriminated schema. Core receipt kinds are:

- `admission`: certifies one delivery digest and records deterministic diagnostics, semantic challenge, baseline commands, user approval, and limits;
- `shape`: certifies one node plan digest and the complete packet DAG for a delivery node;
- `build`: certifies one packet contract, commit, changed paths, proof, inline-review result, and predecessors;
- `accept`: certifies one delivery node against its node plan, build receipts, proof boundary, and tested code revision;
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
4. `delivery`: the delivery-authority root sections named in §3.4, excluding `state`, `admission`, `authority`, and `execution` metadata.

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
- the canonical `execution.node_plans[<node-id>]` packet DAG.

Packet refinement changes only the affected node plan digest. It cannot change the admitted delivery digest.

### 4.3 Receipt validity

A receipt is valid when:

- its schema is supported;
- its target exists;
- every referenced predecessor receipt is valid;
- its delivery and node-plan digests equal current values;
- no later supersession invalidates it;
- its code revision is the tested commit or a permitted descendant with no touched-boundary change;
- its evidence satisfies the target proof contract.

The engine computes validity; agents do not infer it from prose.

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

A delivery node is independently shapeable and independently acceptable. It owns one coherent delivery result and all cross-boundary obligations necessary to prove that result. Nodes split when ownership, dependency order, failure domain, proof environment, or agent context materially differs. They do not split by file type or framework layer alone.

### 5.3 Completeness rule

Every admitted obligation has one accountable delivery owner and one proof path. Shared prerequisites may serve several nodes, but observable completion has one owner. The graph includes explicit integration/proof nodes whenever code, fixtures, generated clients, environments, harnesses, or assembled workflows must be built before acceptance.

## 6. Node Shaping and Packet Plans

Admission creates one `shape` job per delivery node. A successful shape job atomically writes the node plan and creates its build jobs plus one dependency-gated `accept` job. A shape job receives:

- the complete current `ChangeRevision`;
- its target delivery node;
- predecessor receipts and relevant source state;
- repository and contract-authority tools;
- the node-shaping policy and independent shape reviewer.

The shape job creates the complete outcome-cohesive packet DAG for that node in one session.

### 6.1 Legal refinement

A packet plan may:

- choose implementation boundaries inside admitted modules and interfaces;
- split work by genuine dependency, authority, failure domain, incompatible tool, or context limit;
- combine production code, tests, documentation, generated artifacts, migration, and focused proof for one outcome;
- add implementation detail and proportionate proof commands inside the admitted proof boundary.

### 6.2 Illegal expansion

A shape job must return to global design when it discovers or proposes:

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
- proof boundary and commands/observations;
- required outputs such as code, tests, docs, generated artifacts, migration, or evidence;
- domain/risk/tool profile used to load builder skills;
- expected context/change-envelope budget.

## 7. Kanban Job Model

A Kanban card is one purpose-specific agent job. Its `kind` determines the board column and assigned agent:

| Kind | Agent transformation | Success receipt |
| --- | --- | --- |
| `shape` | Delivery node -> complete packet DAG | `shape` |
| `build` | Packet contract -> committed implementation and inline review | `build` |
| `accept` | Delivery node plus descendant receipts -> independent node verdict | `accept` |
| `audit` | Accepted delivery graph -> final product verdict | `audit` |

Archive is the universal terminal disposition, not a fifth agent-work column. A successful shape, build, accept, or audit job issues its purpose-specific receipt and moves to archive; the final audit receipt also closes the change. Cards never change kind or move backward. Dependency readiness, claim activity, pending requests, blocked state, staleness, cancellation, supersession, and failed attempts are properties or dispositions rather than columns.

### 7.1 Job record

Job files are structured YAML under `.owlbear/kanban/jobs/`; archived jobs move to `.owlbear/kanban/archive/`. A job stores only:

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

### 8.2 Delivery-node shaper

The shaper processes one `shape` job, writes only its node-plan namespace and resulting jobs, invokes a read-only shape reviewer, and either issues a shape receipt or returns a material discovery to the designer. It cannot change admitted delivery authority.

### 8.3 Builder

The builder processes one `build` job in the shared worktree. It:

- verifies the exact packet digest and change envelope before editing;
- implements all outputs needed for the packet outcome;
- chooses proportionate durable tests under the existing Rent Test;
- runs focused proof and commits owned paths;
- invokes a mandatory read-only build reviewer with system-generated authority, diff, changed paths, proof, and commit context;
- repairs concrete findings in the same session and re-runs review;
- issues a build receipt only after review passes.

The reviewer cannot edit files, choose product direction, or ask for generic extra tests. It reports typed findings against packet obligations, code, scope, and proof.

### 8.4 Acceptor

The acceptor processes one `accept` job after all required build receipts are valid. It is independent and cannot edit tracked files. The engine materializes the target commit in a disposable proof checkout. The acceptor may inspect code, execute commands, start services, create temporary scratch stores/fixtures, and capture logs/screenshots. It verifies:

- every delivery obligation and interface edge owned by the node;
- packet coverage and actual changed surfaces;
- the admitted assembled proof boundary;
- exact committed code revision and clean proof checkout;
- absence of stale or superseded prerequisites.

Pass creates an accept receipt. Failure creates typed findings and engine-generated corrective jobs. The acceptor never patches its own findings.

### 8.5 Auditor

The auditor processes the single `audit` job after every required node has a valid accept receipt. It is independent and read-only over tracked files. The engine materializes the target commit in a disposable proof checkout. The auditor executes all admitted normal workflows there, checks Product Promise and accepted decisions, confirms migration/removal and absence proofs, and verifies that no invalid or unresolved receipt/request remains. Pass creates the final audit receipt and closes the change mechanically. Failure creates typed findings and minimum corrective jobs.

### 8.6 Orchestrator

The orchestrator has no product authority. It obtains graph-aware waves from the engine and dispatches the assigned agent for each job. It never parses prose to route work.

- tracked-file-mutating `shape` and `build` jobs are globally serialized;
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
6. DN-012 removes the old pipeline from the product revision and consumer distribution. The external
  stable sibling carrier remains available only to dispatch and record DN-013's post-cutover native
  proof and bootstrap closure, then is retired from this change. No bootstrap loader, legacy receipt
  adapter, command alias, or compatibility mode enters the native runtime.

The admission receipt limit states that bootstrap task mutation is not atomic with receipt creation.
Task creation is idempotent by `(change_id, delivery_digest, delivery_node_id, packet_id)` and dispatch
is forbidden until the complete projection audit passes. A partial projection is repaired or removed
before work starts; it never weakens the admitted graph.

## 10. Invalidation, Findings, and Corrective Jobs

Findings are structured and target requirements, interfaces, migrations, risks, workflows, delivery nodes, packets, proofs, receipts, or code revisions.

| Finding class | Corrective route |
| --- | --- |
| Packet implementation or local proof defect | New `build` repair job |
| Packet boundary/dependency/proof-plan defect within admitted node | New `shape` revision job for that node |
| Product, interface, migration, risk, architecture, or delivery-proof defect | Global `/design` re-entry and re-admission |
| Node integration defect after valid packets | New build-owned integration/repair packet through node shape correction |
| Whole-change integration defect within admitted obligations | Corrective node shape/build jobs, then re-accept and re-audit |

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

During `/design`, live user choices use `askQuestions` and are written directly to `decisions.yaml`. Runtime requests live under `.owlbear/kanban/requests/{pending,resolved}/`. A resolution that changes material authority routes to `/design`; local implementation/action resolutions unblock only the dependent job slice.

## 12. Shared Worktree and Commit Contract

- The orchestrator dispatches no overlapping tracked-file writers.
- A shape or build job starts from a recorded clean or explicitly bounded base commit.
- Builders may coexist with unrelated user modifications while implementing when scoped ownership remains unambiguous.
- Acceptance and audit use a disposable read-only checkout of the exact tested commit under `.owlbear/scratch/proof/<job-id>/`; unrelated shared-worktree changes neither block nor influence proof.
- The proof checkout uses the workspace's normal toolchain and environment while isolating tracked files. Reused caches and external services are recorded when they affect evidence.
- Proof-checkout creation, containment, and deletion are engine-owned and crash-safe. Orphaned proof checkouts are health findings and safe cleanup targets.
- Each successful shape/build/accept/audit job owns one logical scoped commit containing its durable control-plane files and, for builders, product files.
- Inline reviewers are read-only and do not commit.
- Acceptance/audit receipts record the tested commit, commands, environment-relevant facts, replacements, outputs, and result.
- Control-plane-only receipt commits may follow the tested code commit; the receipt records the tested code SHA explicitly.
- A later descendant remains valid only when the invalidation engine proves no changed path or authority target intersects the receipt boundary. Otherwise proof is stale.

## 13. `owlbear-kanban` Internal Design

The package remains the transport-free facade, but the current large `engine.py` is replaced by cohesive owners rather than extended.

```text
owlbear_kanban/
  engine.py              # Thin facade and transaction coordination
  models/
    change.py            # ChangeRevision and authority metadata
    graph.py             # Delivery graph and node plans
    job.py               # Purpose-specific jobs and projections
    evidence.py          # Attempts, findings, receipts, validity
    request.py           # Change/job-scoped requests
  stores/
    change.py            # Four-file package load and canonical digest
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

## 14. MCP Contract

The MCP server exposes intent-level tools rather than generic file-like task mutation:

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
- `finish_shape`
- `finish_build`
- `finish_accept`
- `finish_audit`
- `release_job`

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
- `show_receipt`

Generic `create_task`, `edit_task`, `move_task`, arbitrary status transitions, parent mutation, and OpenSpec tools are removed. Shape and corrective transactions are the only ways implementation jobs enter the board.

## 15. Cockpit Product Experience

Kanban remains the default operational surface.

### 15.1 Board

Columns are `Shape`, `Build`, `Accept`, and `Audit`. Cards show projected graph title/outcome plus operational signals:

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
- node packet plans after shaping;
- admission diagnostics and receipt;
- jobs, attempts, findings, receipts, and exact tested commits;
- invalidation/supersession chain;
- final audit result.

### 15.3 Requests and history

The existing request-resolution interaction is retained and expanded with pros, cons, risks, recommendation, and confidence. Activity/session views join jobs to graph targets. Legacy history is an immutable inventory, not an executable board.

### 15.4 Frontend constraints

- Preserve PDS, current accessibility, keyboard, focus, SSE invalidation, filtering, conflict handling, and responsive shell behavior.
- Use list/outline views as the mobile baseline; graph visualization is an enhancement, never the only way to inspect or navigate work.
- Support at least hundreds of graph nodes/jobs through incremental loading or virtualization.
- Never encode status by color alone.
- Verify desktop and mobile with Playwright, screenshots, and nonblank/layout checks.

## 16. Atomic Cutover

The replacement is developed behind the current repository but is not shipped in mixed mode.

At cutover:

1. Stop pipeline dispatch and require no active claims.
2. Generate a manifest of every active OpenSpec change, Kanban task, archive record, pending/resolved request, and relevant evidence.
3. Require an explicit disposition for every active item: `reintroduce-native`, `completed-history`, `dropped`, or `superseded`.
4. Move the old stores into a versioned immutable legacy snapshot and verify manifest hashes.
5. Install an empty native change/job store plus this change's accepted final receipt history.
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
- supersession and corrective-job minimality;
- snapshot manifest and disposition completeness;
- MCP and Cockpit response contracts.

### 17.2 Historical regression fixtures

The original defective and corrected browser lifecycle, workspace repair/removal, memory purge integration, and memory lifecycle clean-build plans become structured fixtures. Each defective form must fail with stable diagnostics before work exists; each corrected form must admit.

### 17.3 Generic anti-overfitting coverage

Use table-driven and property-based cases for dangling IDs, cycles, disconnected obligations, duplicate owners, interface omissions, migration gaps, risk dispositions, proof authorization, stale digests, superseded receipts, invalid exceptions, and random valid DAGs.

### 17.4 End-to-end scenarios

- rough `/ideate` entry -> resumed `/design` -> decision -> challenge -> admission;
- admitted graph -> shape jobs -> packet DAG -> build with inline review -> node acceptance -> final audit;
- build defect -> corrective build job -> re-accept;
- packet-boundary defect -> corrective shape job -> new packets -> re-accept;
- delivery-contract defect -> global re-design -> re-admission -> precise invalidation;
- pending action/decision request -> resolution -> resumed job;
- crash/expired claim/transaction recovery;
- dirty worktree blocks acceptance/audit;
- legacy snapshot and fresh native startup;
- Cockpit desktop/mobile change, board, request, finding, and receipt workflows.

## 18. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Native framework recreates OpenSpec with more code | Implement only the four-file authority, graph validation, jobs, receipts, and closure required by this product; no plugin schema system or generic apply layer |
| Delivery graph becomes an enormous speculative plan | Seal product/interface/proof obligations only; defer implementation packets to bounded node shaping |
| Local shaper hides global expansion | Namespace and reference enforcement plus independent shape review; any new delivery edge forces re-admission |
| Agent/session cost explodes | One shape and accept job per delivery node; outcome-cohesive packets; inline packet review; no artifact-specific statuses |
| Shared worktree contaminates proof | Single writer for implementation, disposable exact-SHA proof checkouts for accept/audit, scoped commits, stale-boundary detection |
| Receipt/job files drift from graph | Jobs carry references/digests only; engine projects contracts and health-scans every reference |
| Corrective jobs create board noise | Immutable history with latest-valid-chain default and grouped finding-set corrections |
| Deterministic validation creates false confidence | Admission receipt states limits; independent source-grounded challenge and executable baselines remain mandatory |
| Final audit again discovers missing infrastructure | Every proof mechanism must have a shape/build owner before admission; auditor is tracked-file read-only |
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
