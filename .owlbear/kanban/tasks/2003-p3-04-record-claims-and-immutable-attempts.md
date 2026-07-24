---
id: 2003
title: 'P3-04: Record claims and immutable attempts'
status: collect
priority: high
created: 2026-07-22T21:58:44.211108+02:00
updated: 2026-07-24T13:14:30.380236+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - lifecycle
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004
  - type:shape
parent: 1979
depends_on:
  - 2002
  - 2010
  - 2011
  - 2012
  - 2013
  - 2014
  - 2015
  - 2016
  - 2017
  - 2018
  - 2019
  - 2020
ac:
  - 'AC-1: Given the stored packet graph, tasks #2010 through #2020 are build leaves
    parented by #2003 with approved dependency edges, admitted change/node identity,
    bounded Scope, and named proof bundle; graph audit reports no missing edge or
    dependency cycle.'
  - 'AC-2: Collector archives #2003 after tasks #2010 through #2020 are archived completed
    with Verify Notes and tested-revision evidence whose union covers attempt schema/storage,
    replacement and mixed-transaction recovery, impact closure, code currency, complete
    receipt currentness, lifecycle ownership, expiry, retry, containment, concurrency,
    and replay.'
  - 'AC-3: Given the completed packet, ownership audit finds #2003 exports attempt
    and receipt-currentness boundaries through its leaves, while downstream #2004
    alone owns assembled successful finish policy, `succeeded` publication, receipt
    creation, and job archival; product responsibility is not duplicated.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-004`

## Outcome
The DN-003-PK-004 packet delivers immutable attempt history, recoverable mixed job/event transactions, reusable receipt-currentness evaluation, and guarded start, release, failure, crash, and retry lifecycle behavior through bounded child tasks.

## Scope
In scope: aggregate closure for child tasks #2010-#2019; dependency, authority, ownership, scenario-closure, and proof audit across their contracts; and the downstream ownership boundary with task #2004.

Out of scope: direct product implementation; successful purpose-specific completion and receipt creation, owned by task #2004; findings and receipt listing, owned by task #2008; wave selection, writer leases, invalidation, corrective jobs, dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Task #2003 is a nested packet aggregate and owns no product implementation directly. Tasks #2010 and #2011 own the attempt contract and immutable history. Tasks #2012 and #2013 own recoverable OCC replacement and mixed job/event serialization. Tasks #2014-#2016 own the reusable receipt-currentness evaluator. Tasks #2017-#2019 own guarded start, owner release/failure, and expired-claim recovery.

Task #2004 consumes the exported attempt and receipt-currentness boundaries while owning assembled successful finish operations, the `succeeded` event, receipt publication, and job archival.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-015`, `REQ-016`, `NEG-002`, `NEG-010`, `IF-003`, `KEEP-007`, `RISK-002`, `RISK-003`, `PROOF-003`, design sections 2.2, 2.3, 4.2, 4.3, 6, 7.2, 8.6, 9.5, 12, 13, and 14, and accepted decisions `DEC-007` and `DEC-009` under `.owlbear/changes/replace-delivery-pipeline/`.

## Proof Guidance
This aggregate is collected only after every child is archived completed with Verify Notes and tested-revision evidence. Audit the stored child graph, then inspect the union of child proofs for immutable event contracts and storage, OCC replacement recovery, mixed-process serialization, all receipt-currentness classes, lifecycle ownership, boundary-time expiry, retry, path containment, and idempotent replay. Lower layers may use explicit temporary roots, clocks, process identities, and bounded Git histories, but must exercise each named public or module boundary.

[[2026-07-23T03:13:22+02:00]]
## Shape Notes
- Source and repair mode: user-approved connected material boundary repair for tasks 2001, 2003, and 2008, prompted by task 2008's builder rejection. This task received a local operative-contract replacement inside that approved boundary.
- Rejection resolution: the builder's claim that admitted authority was absent was false. `.owlbear/changes/replace-delivery-pipeline/` contains the admitted intent, design, decisions, graph, and admission receipt. Design sections 2.2, 2.3, and 7.2 place attempts with operational claim/lifecycle history rather than durable finding/receipt evidence.
- User decision: all attempt contracts and attempt storage move from task 2008 to this lifecycle owner. Supported event kinds are `started`, `released`, `failed`, `crashed`, and `succeeded`; this task emits the first four and task 2004 retains successful completion semantics.
- Planning artifacts: none revised. The task projection now matches existing admitted authority.
- Interrupted-layer adoption: adopted the current unstaged claim layer from the interrupted invocation; no conflicting hunk or staged task record existed.

### Readiness And Authorities
- Authorities: `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 2.2, 2.3, 7.2, 13, and 14, and accepted `DEC-007` and `DEC-009`.
- Readiness: task 2003 remains build-ready after task 2002; task 2004 remains its downstream successful-completion consumer.

### Change Module Map
| Owner | Responsibility | Interface impact |
|---|---|---|
| Task 2003 lifecycle/attempt owner | `AttemptEvent`, contained attempt storage, claim/start/release/fail/crash semantics | New public attempt parser/store and lifecycle facade |
| `jobs.py` | Native job references and records | Consumed, not reassigned |
| `storage_io.py` | Contained durable-write precedent | Reused internally |
| Task 2004 | Purpose-specific successful completion | Uses `succeeded`; unchanged dependency |

### Product Invariant Map
| Invariant | Boundary |
|---|---|
| Attempts remain append-only operational history | Public attempt store and lifecycle operations |
| Failed, crashed, or released attempts do not mutate graph or receipts | Lifecycle transaction proof |
| Retry preserves prior attempts and job purpose | Start after terminal attempt outcome |
| Findings and receipt listing remain outside this task | Task 2008 contract |

### Product Promise Coverage Map
| Promise | Coverage |
|---|---|
| Immutable attempt history and honest runtime dispositions | This task under `REQ-008` and `REQ-009` |
| Crash-safe contained publication | Task 2002 foundation under `REQ-016` |
| Successful receipt-producing completion | Task 2004, unchanged |

### Task And Dependency Changes
- Replaced stale Outcome, Scope, ownership, Authority, proof guidance, and AC with the complete attempt model/store plus lifecycle contract.
- Kept status `build`, parent 1979, dependency 2002, proof bundle, task count, and all unrelated edges unchanged.

### Challenge And Board Audit
- `shaper-challenger` decision: pass; authority, readiness, invariant ownership, boundary proof, fidelity, literals, and adjacent 2004 ownership all met.
- Release audit: task 2003 is `build`, parent 1979, depends on active task 2002, and is dependency-blocked as intended; task 2004 still depends on 2003.

[[2026-07-23T10:51:30+02:00]]
## Builder Notes
- Change envelope: task 2003 requires the native transaction coordinator and stores delivered by task 2002; expected attempt/lifecycle owner cannot be implemented before that foundation exists.
- Files changed: none.
- Change Module Map deviations: none; the mapped task 2003 owner depends on task 2002's delivered foundation.
- Proof selected: task dependency/readiness check before any code edit.
- Commands run: none; no product change was permitted.
- Builder-challenger result: initial pre-implementation challenge correctly returned `fail` because no implementation or evidence existed; it is not a completion claim.
- Follow-up risks: task 2003 was dispatched while dependency 2002 remains unresolved (`dep_status: blocked`). Re-dispatch only after task 2002 reaches a non-blocking completion state.

[[2026-07-23T11:28:27+02:00]]
## Shape Notes
- Repair classification: mechanical reroute inside the user-authorized connected repair. The builder changed no files and returned this task only because it was dispatched while dependency #2002 was unresolved.
- Contract audit: the existing operative body already owns the native append-only attempt/activity stream and atomically couples job claim changes with `started`, `released`, `failed`, and `crashed` events. Task #2004 remains the owner of the `succeeded` event during successful completion.
- Dependency closure: #2003 consumes archived #2001 stores through the transaction kernel now owned by build task #2002. It requires no request, completion, invalidation, or health producer.
- Route: restored to `build` with parent #1979 and dependency #2002 unchanged. It remains dependency-blocked and must not be dispatched until #2002 reaches non-blocking completion.

[[2026-07-23T12:20:29+02:00]]
## Builder Notes
- Change envelope: no product change; task 2003 requires the transaction coordinator owned by dependency 2002.
- Files changed: no product files.
- Change Module Map deviations: none; implementation was not started because the shaped route states this task must not be dispatched until dependency 2002 completes.
- Proof selected: board dependency projection and shaped dependency-closure note.
- Commands run: none; implementation is intentionally deferred.
- Builder-challenger result: not invoked because no DONE verdict is being proposed.
- Follow-up risk: task 2002 is currently in `shape`, so 2003 must be redispatched only after 2002 reaches a non-blocking completed status.

[[2026-07-23T14:55:16+02:00]]
## Shape Notes
- Repair mode: graph-only material repair re-entry for DN-003-PK-004 after repeated build/verify rejection exposed four independently variable high-risk axes in the former monolithic task. No product code or OpenSpec artifact changed.
- Planning authority: admitted change `replace-delivery-pipeline` at delivery digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `REQ-008`, `REQ-009`, `REQ-015`, `REQ-016`, `NEG-002`, `NEG-010`, `IF-003`, `KEEP-007`, `RISK-002`, `RISK-003`, `PROOF-003`; design sections 2.2, 2.3, 4.2, 4.3, 6, 7.2, 8.6, 9.5, 12, 13, and 14; accepted `DEC-007` and `DEC-009`.
- User decisions: preserve persisted `JobRecord.claim_id` and `attempt_id`; deepen `RuntimeTransaction` with recoverable OCC replacement participants; split schema, storage, transaction, receipt-currentness, and lifecycle proof domains; retain #1979 as top aggregate and #2004-#2007 as siblings; approve the ten-leaf graph and wording-only #2004 ownership clarification.
- Artifact reconciliation: no planning artifact revision was required because the selected architecture refines the admitted internal `IF-003` transaction/lifecycle design without changing product intent, normative behavior, migration, or exposed delivery interface.
- Readiness: exact hidden archive reads verified #2000, #2001, #2002, #2008, and #2009 as `archived` with `archival_reason: completed`. #2002 supplies the reusable immutable-participant transaction kernel and explicitly leaves later lifecycle participant plans and reopen hooks to downstream owners.

### Change Module Map
| Module | Planned change | Owning tasks |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/attempt.py` | Add immutable attempt contract and contained event history | #2010, #2011 |
| `serve/kanban/src/owlbear_kanban/runtime_transaction.py` | Add recoverable OCC replacement and mixed create/replace serialization | #2012, #2013 |
| `serve/kanban/src/owlbear_kanban/receipt.py` | Add local, Git-revision, predecessor, and supersession currentness evaluation | #2014, #2015, #2016 |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Add guarded start, owner release/failure, and expiry recovery facade | #2017, #2018, #2019 |
| `serve/kanban/src/owlbear_kanban/jobs.py` | Existing OCC job/claim authority consumed without ownership change | #2012, #2017-#2019 |
| Task #2004 finish boundary | Consume exported evaluator; own assembled success, receipts, and archival | #2004 |

### Product Invariant Map
| Invariant | Owner | Boundary and proof |
|---|---|---|
| Attempt events are immutable, contained, deterministic history | #2011 | Public `AttemptStore`; destination/path/failure matrix |
| One job replacement and one event recover as a complete pair | #2013 | Mixed transaction; interruption, process race, replay |
| Receipt currentness includes authority, proof, code, predecessor, and supersession | #2016 | Complete evaluator over #2014/#2015 prerequisites; finite graph matrix |
| Only eligible work gains one active claim and `started` event | #2017 | Public `start_job`; readiness/replay table |
| Only the owner can release or fail an active attempt | #2018 | Public owner-finalization operations |
| Strictly expired claims become one crash event and retryable work | #2019 | Public recovery across boundary times and reopen |
| Successful purpose-specific completion publishes `succeeded`, receipt, and archive | #2004 | Public finish/validity consumer boundary |

### Dependency Closure Map
- #2010 <- completed #2002; #2011 <- #2010.
- #2012 <- completed #2002; #2013 <- #2011 and #2012.
- #2014 <- completed #2002; #2015 <- #2014; #2016 <- #2014 and #2015.
- #2017 <- #2013 and #2016; #2018 <- #2017; #2019 <- #2017 and #2018.
- #2003 depends on completed #2002 plus every leaf #2010-#2019. #2004 remains downstream of #2003. No leaf depends on its aggregate and no dependency cycle exists.

### Scenario Closure Map
| Task | Finite scenario axis |
|---|---|
| #2010 | accepted kind mappings vs malformed identity/reference/sequence/kind/fields |
| #2011 | absent, byte-equal, byte-different, unsafe, and failed-write destinations |
| #2012 | expected, already-replaced, conflict, malformed/unsafe, and three interruption phases |
| #2013 | complete-pair recovery, same-expected-bytes process race, and replay |
| #2014 | kind, schema, target, digest, and proof-satisfaction classes |
| #2015 | exact, untouched descendant, touched descendant, non-descendant, and missing revision |
| #2016 | current chain, missing/invalid predecessor, cycle, supersession, and shared predecessor |
| #2017 | eligible, active, stale, invalid predecessor, pending request, terminal, and replay identities |
| #2018 | owner release/fail, non-owner, no-active-claim, and replay |
| #2019 | before, exactly at, and after expiry; reopen and repeated recovery |

### Product Promise Coverage Map
| Promise | Owner and proving outcome |
|---|---|
| Immutable operational attempt history | #2010/#2011 contracts and public store AC |
| Recoverable claim/event mutation | #2012/#2013 replacement and mixed-transaction AC |
| Complete reusable receipt currentness | #2014-#2016 evaluator AC |
| Guarded claim lifecycle and honest non-success dispositions | #2017/#2018 lifecycle AC |
| Crash recovery leaves work retryable without erasing history | #2019 recovery AC |
| Successful receipt-producing completion | Existing downstream #2004 Outcome and AC |

### Final Graph And Audit
- Created build leaves #2010-#2019 with packet identities `DN-003-PK-004-A` through `DN-003-PK-004-J`, explicit priorities, bounded Scope, three ACs each, and named proof bundles.
- Fragmentation rationale: ten leaves exceed the preferred 3-6 range because they isolate ten distinct failure domains and proof modes. Merging any adjacent pair would recreate independent schema/path/concurrency/crash/Git/graph/lifecycle matrix multiplication that caused the cost pause.
- Converted #2003 into a nested `collect` aggregate with parent #1979, dependencies #2002 and #2010-#2019, aggregate AC, `type:shape`, and `existing+challenge` proof.
- Clarified #2004 to consume the #2014-#2016 evaluator through #2003 while retaining its Outcome, AC-1 through AC-3, `build` status, parent #1979, dependency #2003, and assembled finish ownership.
- #1979 remains unchanged and #2004-#2007 remain direct siblings under it. MCP child and sibling queries matched the approved graph; `git diff --check` passed. `.vscode/mcp.json` is unrelated and excluded.
- Challenger: provisional graph passed authority, hierarchy, dependency closure, scenario closure, AC quality, module locality, receipt-validity coverage, Product Promise coverage, and acyclicity. Post-write challenge passed after exact current working-tree and hidden archive evidence corrected two search-access false negatives; final result `decision: pass` across readiness, authority, invariant ownership, dependency closure, scenario closure, boundary proof, and fidelity.
- Memory preflight closeout: all 19 recalled shaper entries were assessed for task #2003 before release.

## Operative Eleven-Leaf Graph Amendment
This section supersedes earlier ten-leaf inventories, receipt ownership maps, dependency maps, scenario maps, and fragmentation rationale.

### Ownership And Dependency Closure
Tasks #2010 and #2011 own attempt schema and immutable history. Tasks #2012 and #2013 own replacement and mixed job/event transactions. Tasks #2014, #2015, #2020, and #2016 own local currentness, frozen impact closures, Git code currency, and recursive/explicit-supersession currentness. Tasks #2017 through #2019 own start, release/failure, and expired-claim recovery. Task #2004 consumes the exported attempt/currentness boundaries and alone owns assembled successful finish, `succeeded`, receipt issuance, and job archival.

The receipt dependency chain is #2014 followed by #2015, then #2020, then #2016; #2016 also consumes #2014. Lifecycle task #2017 consumes #2013 and #2016. Parent #2003 depends on #2002 and leaf tasks #2010 through #2020. The receipt chain has no DN-004 dependency: DN-003 owns repository-history classification, while DN-004 later owns disposable proof-checkout lifecycle.

### Change Module Map Amendment
`receipt.py` ownership is #2014 local authority/proof currentness, #2015 typed impact closure and shared path validation, #2020 repository-history code currency, and #2016 predecessor/supersession closure. `jobs.py`, `runtime_transaction.py`, and `attempts.py` ownership remains with their prior leaves.

### Scenario Closure Amendment
- #2015: canonical/unsafe selectors, declared/undeclared targets, missing/malformed closure, shape/build copy, accept union, audit root, and immutable roundtrip.
- #2020: exact/missing/non-descendant commits, disjoint/intersecting descendants, rename/copy source and destination, malformed status/arity, decode/query failure, and unsafe history path.
- #2016: current chain, missing/non-current predecessor, cycle, explicit supersession reference, and shared predecessor.

### Invariant And Promise Coverage Amendment
Typed closure ownership is #2015; precise descendant currency is #2020; complete reusable receipt currentness is #2016; successful finish remains #2004. Together they satisfy `NEG-010`, `RISK-003`, `IF-003`, and `PROOF-003` without using `REQ-015` as receipt authority.

### Fragmentation Rationale
Eleven leaves exceed the preferred range because selector/issuance schema, repository-history classification, and recursive receipt-graph currentness have independent inputs and failure matrices. Merging those tasks would cross the single-proof and single-failure-domain budgets.

[[2026-07-23T18:16:46+02:00]]
## Shape Notes
- Material receipt repair approved by the user and passed final shaper-challenger review.
- Graph: eleven leaves; added #2020 (`DN-003-PK-004-K`) after #2015, and #2016 now consumes #2020. Parent dependency and ownership/scenario maps were updated.
- Availability: #2014/#2015/#2020/#2016 respectively own local currentness, typed impact closure, Git currency, and predecessor/explicit-supersession closure. #2004 alone owns assembled finish and receipt issuance.
- Remaining separate gaps: #2012/#2013 shared OCC authority and #2017-#2019 lifecycle result/expiry contracts are not certified ready by this repair. Aggregate remains `collect`.

[[2026-07-23T23:05:31+02:00]]
## Operative Connected OCC Map Correction

This correction supersedes earlier parent-map rows that say task #2012 consumes `jobs.py` without an ownership change. Record/schema/OCC-token authority remains in `jobs.py`; only the storage lock mechanism changes.

### Change Module Map Delta

| Module | Planned change | Owning tasks |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/storage_io.py` | Add `locked_roots(roots)` with descriptor-backed no-follow opens, canonical deduplication/order, shared `.storage.lock` identity, and partial-acquisition cleanup | #2012 |
| `serve/kanban/src/owlbear_kanban/jobs.py` | Preserve job record serialization and `ERR_JOB_OCC_STALE`; replace private `.jobs.lock` acquisition with the shared storage-root lock | #2012 for lock migration; #2017-#2019 consume through #2013 |
| `serve/kanban/src/owlbear_kanban/runtime_transaction.py` | Hold the same manifest/participant-root locks across prepare, replacement compare/publish, recovery, and cleanup | #2012; #2013 consumes for mixed plans |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Guarded start, owner release/failure, and expiry recovery facade; no lock primitive ownership | #2017, #2018, #2019 |

### Dependency Closure Map Delta

No edge changes are required. Task #2013 depends on #2012; task #2017 depends on #2013 and #2016; tasks #2018 and #2019 remain downstream of #2017. Therefore #2017 through #2019 cannot dispatch before #2012's shared-lock migration and #2013's mixed-plan composition are archived completed. At correction time #2017 through #2019 are unclaimed and dependency-blocked.

### Scenario Closure Map Delta

| Task | Added finite scenario axis |
|---|---|
| #2012 | canonical duplicate/multi-root acquisition; symlink root and lock rejection; partial-acquisition cleanup; controlled JobStore-first and transaction-first replacement contention with stable loser codes and preserved winner bytes |
| #2013 | mixed job/attempt complete-pair recovery, rival pair exclusion, and replay while consuming #2012's shared root lock |
| #2017-#2019 | lifecycle scenarios remain unchanged and consume the archived mixed transaction boundary; no direct lock-helper proof |

### Collision Audit

The connected repair owns planning records #2003 and #2012. Product-file collision is prevented by existing dependency edges rather than new sibling dependencies: #2013 and #2017 through #2019 remain blocked until their prerequisites archive. Unrelated `atomic_write` consumers do not write the JobStore-owned destination in #2012's proof and are outside this packet correction.

[[2026-07-23T23:12:58+02:00]]
## Shape Notes
- Connected repair set: #2003 and #2012. Parent mutation was required after challenge found that #2012's shared-lock repair contradicted the older parent maps.
- Classification: local connected planning repair under accepted architecture, not a material product decision. Design section 13 already assigns locks, containment, and fsync to `storage_io.py`; `REQ-016` requires concurrency-safe recoverable transactions.
- Parent changes: appended the Operative Connected OCC Map Correction. `storage_io.py` now owns `locked_roots`; #2012 owns the private-to-shared lock migration in `jobs.py` and shared-lock consumption in `runtime_transaction.py`; job record/OCC-token authority remains in `jobs.py`; #2013 retains mixed job/attempt pair semantics; #2017 through #2019 retain lifecycle facade ownership.
- Dependency audit: no edge changes. #2013 depends on #2012, #2017 depends on #2013 and #2016, and #2018/#2019 remain downstream. Live board evidence showed #2017 through #2019 unclaimed and dependency-blocked, so no in-flight file collision exists.
- Scenario correction: parent map now names canonical duplicate/multi-root lock acquisition, symlink root/lock rejection, partial-acquisition cleanup, controlled JobStore-first conflict, and controlled transaction-first stale OCC. #2013's complete-pair/rival-event/replay axis remains separate.
- Challenger chain: task-local shared-lock boundary and controlled ordering were added after the first challenge; parent maps were corrected after the second; binding AC-2 and AC-3 were split to require both writer orderings after the connected challenge. Final connected shaper-challenger decision: pass.
- Route: parent stays in `collect`, released and still dependency-blocked on unfinished children. #2012 separately advances to `build` after this parent record is committed.

[[2026-07-23T23:29:53+02:00]]
## Operative Mixed Participant Map Correction

This correction extends the current packet maps for task #2013 without changing graph edges or lifecycle ownership.

### Change Module Map Delta

| Module | Planned change | Owning tasks |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/jobs.py` | Preserve job schema, serialization, OCC token, and shared lock; add non-mutating replacement participant planning from a current token | #2013 for participant planning; #2012 retains lock migration; #2017-#2019 consume through #2013 |
| `serve/kanban/src/owlbear_kanban/attempts.py` | Preserve attempt schema and immutable store; add non-mutating canonical create-participant planning | #2010-#2011 for schema/storage; #2013 for participant planning |
| `serve/kanban/src/owlbear_kanban/runtime_transaction.py` | Compose planned replacement/create participants through existing commit, shared locks, recovery, conflict, and cleanup | #2012 primitive; #2013 mixed composition/proof |

### Dependency Closure Map Delta

No edge changes. #2013 depends on archived-completed #2011 and #2012. #2017 depends on #2013 and #2016, with #2018 and #2019 downstream, so lifecycle work remains gated on the mixed participant contract.

### Scenario Closure Map Delta

| Task | Added finite scenario axis |
|---|---|
| #2013 | current versus stale job-token planning; non-mutating attempt planning; interruption after job publication followed by complete recovery; two-process same-token rival pairs; byte-equivalent replay with one immutable event |

The participant factories expose canonical store-owned bytes and paths without moving job, attempt, transaction, or lifecycle policy ownership across modules.

[[2026-07-23T23:34:54+02:00]]
## Shape Notes
- Connected repair set: #2003 and #2013. Classification: local interface/AC repair under the accepted packet architecture; no dependency or product decision changed.
- Source finding: archived #2011 and #2012 provide immutable attempt storage and shared-lock replacement transactions, but canonical job/attempt participant bytes and paths remained private, so the prior #2013 AC did not identify a buildable mixed-plan boundary.
- Parent map correction: #2013 adds non-mutating `JobStore.replacement_participant` and `AttemptStore.create_participant` planning while job/attempt schema and storage ownership remain with #2010/#2011 and replacement/shared-lock primitives remain with #2012. `RuntimeTransaction` stays the generic mixed commit/recover owner.
- Dependency audit: no edge changes. #2013 depends on archived-completed #2011/#2012; #2017 remains gated on #2013 and #2016; #2018/#2019 remain downstream.
- Scenario map correction: current/stale job planning, non-mutating attempt planning, after-first-publication recovery, same-token rival pairs, and byte-equivalent replay are now finite #2013 axes.
- Challenger: final connected shaper-challenger decision pass; it confirmed canonical helper availability, no import cycle, real assembled boundaries, exact result codes, and no strict-subset overclaim.
- Route: #2003 remains collect, released and dependency-blocked on unfinished children. #2013 advances separately to build after this parent record is committed.

[[2026-07-24T03:03:15+02:00]]
## Operative Native Job Start Map Correction

This user-approved correction extends the packet maps for task #2017 without changing dependency edges or tasks #2018/#2019 ownership.

### Change Module Map Delta

| Module | Planned change | Owning tasks |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/jobs.py` | Preserve job serialization and OCC; migrate `disposition` to strict `pending | cancelled | superseded` and reject unsupported persisted values | #2017 for the schema migration |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Add public start request/result/diagnostics and assembled `NativeRuntime.start_job`; deepen the same facade with release/failure and expiry recovery | #2017 start; #2018 release/fail; #2019 expiry recovery |
| `serve/kanban/src/owlbear_kanban/__init__.py` | Export strict disposition and native start contracts | #2017 |
| `serve/kanban/tests/test_native_runtime.py` | Public assembled lifecycle proof | #2017, #2018, #2019 by owned scenario |

### Dependency Closure Map Delta

No edge changes. Task #2017 depends on archived-completed #2013 and #2016. Task #2018 depends on #2017. Task #2019 depends on #2017 and #2018. Therefore release/failure and expiry behavior remain gated on the strict start result and persisted identity established by #2017.

### Scenario Closure Map Delta

| Task | Added finite scenario axis |
|---|---|
| #2017 | strict disposition parsing; authority mismatch; predecessor job missing, receipt missing, and receipt non-current; pending request; cancelled and superseded; eligible atomic start; exact replay; replay identity conflict; different and inconsistent active-claim pointers |
| #2018 | owner release/fail and replay only; consumes #2017 start result without repeating eligibility guards |
| #2019 | expiry boundary and retry recovery only; consumes #2017 identity and #2018 finalization |

### Authority And Validation

Accepted `DEC-022`, design section 7.3, and `IF-003` own the strict disposition and dedicated start-result contract. The revised native authority is internally coherent at digest `ce87d37e9935c7dfbb07a52ad485a8ce4b3641d3b054ba72417b0d80577f1a82`; existing global `DV-010` re-admission debt remains assigned to DN-013/DN-014 under the bootstrap policy already recorded by archived task #2021.

[[2026-07-24T03:06:19+02:00]]
## Shape Map Repair Notes
- Applied the user-approved #2017 ownership delta to the parent Change Module Map, Dependency Closure Map, and Scenario Closure Map.
- Named ownership: #2017 migrates strict job disposition, creates the native start facade/models/exports, and owns public start scenarios; #2018 retains release/fail; #2019 retains expiry recovery.
- Dependency audit: no edge changes. #2017 remains gated on archived #2013/#2016; #2018 and #2019 remain downstream.
- Authority: DEC-022, design section 7.3, and IF-003. Revised authority is coherent at digest ce87d37e9935c7dfbb07a52ad485a8ce4b3641d3b054ba72417b0d80577f1a82 under the documented bootstrap admission policy.
- Validation: Kanban edit-contract tests passed (2 tests), diff check passed, amendments appear once, and #2017 has exactly eight independently verifiable AC.
- Route: #2003 stays in collect and remains dependency-blocked on unfinished lifecycle children.

[[2026-07-24T12:34:17+02:00]]
## Operative Finalization Replay Identity Map Correction

This user-approved correction extends the packet maps for #2018 without changing dependency edges or #2019 ownership.

### Change Module Map Delta

| Module | Planned change | Ownership |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/attempts.py` | Add required nonempty `AttemptEvent.claim_id` and stable identity diagnostics | #2018 bounded repair of archived #2010 event contract/parser |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Populate claim on started/released/failed events and partition exact, mismatched, cross-job, and absent-outcome replay | #2018 bounded repair of archived #2017 event construction plus #2018 finalization ownership |
| `serve/kanban/tests/test_attempts.py` | Public parser/serializer claim proof | #2018 bounded #2010 invariant repair |
| `serve/kanban/tests/test_native_runtime.py` | Public start/release/fail replay proof | #2018 |
| `serve/kanban/tests/test_runtime_transaction.py` | Adapt direct event fixture only | #2018; archived #2011 persistence/path-safety semantics unchanged |

`AttemptEvent` is already exported, so package exports do not change. Archived #2011 remains the immutable persistence/path-safety owner. #2019 remains the expiry-recovery owner.

### Dependency Closure Map Delta

No edge changes. #2018 remains after archived #2017, whose dependency chain includes archived #2010 and #2011. #2019 remains after #2017 and #2018 and consumes the durable claim identity established by #2018.

### Scenario Closure Map Delta

| Task | Added finite scenario axis |
|---|---|
| #2018 | claim parse/round-trip/missing/empty; started claim propagation; exact, active-pointer, and matching-pointer metadata-conflict start replay; exact finalization replay; same-job completed mismatch across claim/kind/actor/process/timestamp/detail/evidence; active non-owner; absent-outcome no-active; cross-job replay |
| #2019 | expiry and retry recovery only; consumes claim-bearing immutable history without redefining replay ownership |

### Authority And Validation

Accepted `DEC-023`, design section 7.4, reconciled design section 7.3, and `IF-003` own this strict event identity and replay partition. The revised authority loads without diagnostics at digest `5d7cf64e0317707ea78015e818f9e3a328b0c4239871edb5bf66014d71ae2552`; global re-admission remains assigned to DN-013/DN-014.

[[2026-07-24T12:34:17+02:00]]

[[2026-07-24T12:36:37+02:00]]
## Shape Map Repair Notes
- Applied the user-approved #2018 delta to the parent Change Module Map, Dependency Closure Map, and Scenario Closure Map.
- Ownership: #2018 repairs archived #2010 event identity/parser and archived #2017 event claim propagation; archived #2011 persistence/path safety and #2019 expiry ownership remain unchanged.
- Dependency audit: no edge changes. #2018 remains after archived #2017; #2019 remains after #2017/#2018.
- Authority: DEC-023, design sections 7.3/7.4, and IF-003 at validated digest 5d7cf64e0317707ea78015e818f9e3a328b0c4239871edb5bf66014d71ae2552.
- Mechanical correction: an accidental duplicate append during the board write was removed through canonical AgentView body replacement with before/after heading assertions; one approved amendment remains and prior history is preserved.
- Validation: edit-contract tests passed (2), diff check passed, one amendment remains on each task, and #2018 has exactly eight AC.
- Route: #2003 stays in collect and remains dependency-blocked on unfinished lifecycle children.

[[2026-07-24T13:13:54+02:00]]
## Operative Native Claim Recovery Map Correction

This user-approved correction extends the packet maps for task #2019 without changing dependency edges.

### Change Module Map Delta

| Module | Planned change | Ownership |
|---|---|---|
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Require positive injected claim expiry; add recovery request/result/diagnostics; complete pending transactions; sweep jobs by ID; validate active identity; enforce strict expiry; atomically crash expired attempts; replay persisted outcomes | #2019 |
| `serve/kanban/src/owlbear_kanban/__init__.py` | Export the native recovery contract | #2019 |
| `serve/kanban/tests/test_native_runtime.py` | Adapt the seven current runtime constructors and prove policy, time, ordering, diagnostics, mutation, reopen replay, and retry separation through the public facade | #2019 |
| Existing `jobs.py`, `attempts.py`, `runtime_transaction.py` | Reuse ordered inventory, claim-bearing immutable events, transaction recovery, participants, and conflict errors without behavior change | archived #2011/#2012/#2013/#2017/#2018 foundations; consumed by #2019 |

### Dependency Closure Map Delta

No edge changes. Task #2019 remains dependent on archived #2017 and #2018. Those tasks supply active start identity, claim-bearing immutable events, and finalization semantics. Task #2019 adds expiry recovery over those contracts and is the final unfinished lifecycle child blocking parent #2003.

### Scenario Closure Map Delta

| Owner | Added finite scenario axis |
|---|---|
| #2019 | positive, zero, and negative policy; aware, malformed, and naive request time; before, equal, and after expiry; ascending multi-job recovery; non-expired and release/fail no-op; inconsistent pointers; missing, mismatched, or invalid started event; per-job transaction conflict; exact same-instance and reassembled replay; later retry not mistaken for replay |

### Authority And Validation

Accepted `DEC-024`, design section 7.5, and `IF-003` own constructor policy, deterministic sweep, strict boundary, crash identity, diagnostics, and replay. The revised authority loads without diagnostics at digest `eaab0f2e46780f38b5df541d248fc54cb8a0483da1464f60f4d507c0f3cad617`; global re-admission remains assigned to DN-013/DN-014.

[[2026-07-24T13:14:30+02:00]]
## Shape Map Repair Notes
- Applied the user-approved #2019 native recovery delta to the parent Change Module Map, Dependency Closure Map, and Scenario Closure Map.
- Ownership: #2019 adds constructor-owned positive expiry, supplied-time deterministic sweep, per-job diagnostics, atomic crash events, exact persisted replay, exports, and focused public proof. Existing job, attempt, and transaction owners are reused unchanged.
- Dependency audit: no edge changes. #2019 remains after archived #2017/#2018 and is the final unfinished lifecycle child blocking #2003.
- Authority: DEC-024, design section 7.5, and IF-003 at validated digest eaab0f2e46780f38b5df541d248fc54cb8a0483da1464f60f4d507c0f3cad617.
- Validation: edit-contract tests passed 2; diff check passed; one operative amendment remains on each task; #2019 has exactly seven AC; dependencies and claims were audited.
- Route: #2003 stays in collect until #2019 completes.
