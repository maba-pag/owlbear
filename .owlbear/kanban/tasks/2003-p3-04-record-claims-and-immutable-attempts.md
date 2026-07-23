---
id: 2003
title: 'P3-04: Record claims and immutable attempts'
status: collect
priority: high
created: 2026-07-22T21:58:44.211108+02:00
updated: 2026-07-23T14:55:16.959947+02:00
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
ac:
  - 'AC-1: Given the stored packet graph, tasks #2010-#2019 are build leaves parented
    by #2003 with the approved dependency edges, admitted change/digest/node identity,
    bounded Scope, and named proof bundle; graph audit reports no missing edge or
    dependency cycle.'
  - 'AC-2: Collector archives #2003 only after every child is archived completed with
    Verify Notes and tested-revision evidence whose union covers attempt schema/storage,
    replacement and mixed-transaction recovery, complete receipt currentness, lifecycle
    ownership, expiry, retry, containment, concurrency, and replay.'
  - 'AC-3: Given the completed packet, ownership audit finds #2003 exports the attempt
    and receipt-currentness boundaries through its leaves, while downstream #2004
    alone owns assembled successful finish policy, `succeeded` event publication,
    receipt creation, and job archival; no product responsibility is duplicated.'
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
