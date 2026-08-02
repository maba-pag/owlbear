---
id: 1979
title: 'Bootstrap DN-003: Replace task runtime with graph-linked jobs and receipts'
status: archived
priority: high
created: 2026-07-22T01:05:46.251445+02:00
updated: 2026-07-24T16:11:56.232810+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-003
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1977
  - 1978
  - 2000
  - 2001
  - 2002
  - 2003
  - 2004
  - 2005
  - 2006
  - 2007
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-003` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-003` modules, interfaces, risks, and
    `PROOF-003`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-003` and `PROOF-003`, verified
    through Kanban queries and artifact inspection.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-003|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-003` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Purpose-specific job, attempt, finding, receipt, request, supersession, invalidation, transaction, recovery, and health models provide one graph-aware runtime with no copied specification truth.
- Modules: `MOD-001`, `MOD-009`
- Produces: `IF-003`
- Consumes: `IF-001`, `IF-002`
- Risks: `RISK-002`, `RISK-003`, `RISK-006`
- Proof: `PROOF-003`
- Delivery dependencies: `DN-001`, `DN-002`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise public job, claim, completion, invalidation, transaction, recovery, and health operations with focused downstream impact; only clock, process identity, and temporary filesystem may replace layers below `PROOF-003`.

[[2026-07-22T22:08:58+02:00]]
## Shape Notes
- Readiness: DN-001 #1977 and DN-002 #1978 are archived completed. The admitted `replace-delivery-pipeline` revision loads at digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `change_health` has no findings. Focused predecessor proof (`test_jobs.py`, `test_admission.py`, `test_historical_admission_fixtures.py`) passed 32 tests.
- Current-source grounding: DN-002 provides strict `ChangeRevision`, immutable six-kind receipt storage, shape-only `JobGeneration`, and atomic receipt-plus-generation publication. The live bootstrap workspace has no native operational jobs, so DN-003 owns the first explicit work-plane materialization. Legacy `engine.py`, `models.py`, `storage.py`, `request_models.py`, and `dispatch.py` remain the bootstrap carrier; DN-003 adds one transport-free native facade beside them rather than extending or deleting that state machine.
- Approved packet DAG: #2000 contracts -> #2001 stores/OCC -> #2002 transaction recovery -> #2003 claims/attempts; #2003 -> #2004 purpose-specific completion/receipt validity and #2005 scoped requests; #2004 + #2005 -> #2006 invalidation/corrective work -> #2007 indexed health/history. #1979 depends on #2000-#2007 and remains the collect aggregate until all descendants archive.
- Module map: #2000 deepens native job/receipt contracts and exports; #2001 owns contained work stores; #2002 owns the generalized transaction coordinator and admission handoff; #2003-#2007 own lifecycle, completion, requests, invalidation, and health behind the native facade. No packet may create live workspace runtime data.
- Invariant map: authority references without copied normative truth -> #2000; immutable job kind with orthogonal claims/blocks/staleness/disposition -> #2003/#2004, owner #2004; atomic graph/job/request/receipt/activity mutation and recoverable crash state -> #2002; immutable attempts/findings/receipts -> #2001/#2003/#2004, owner #2001; only current valid predecessor evidence releases work -> #2004; minimum descendant invalidation and typed corrective routing -> #2006; scoped decision/action requests -> #2005; deterministic bounded projections and corruption health -> #2007.
- Coverage map: REQ-008 -> #2006; REQ-009 -> #2003/#2004/#2007; REQ-015 -> #2005; REQ-016 -> #2001/#2002; REQ-023 -> #2007. NEG-001 -> #2000; NEG-002 -> #2003/#2004; NEG-010 -> #2004/#2006. KEEP-006 -> #2003/#2005/#2007; KEEP-007 -> #2001/#2002/#2007. IF-003 is produced across #2000-#2007; PROOF-003 is exercised through the public native facade, with store-level checks supplementary only.
- Exclusions: dispatch waves, readiness selection, global writer compatibility/leases, and proof checkout stay in DN-004; agent behavior stays in DN-006 through DN-008 and DN-014; MCP cutover stays in DN-009; Cockpit stays in DN-010/DN-011; caller cutover and legacy deletion stay in DN-012. Native request resolution returns typed design re-entry instead of mutating authority.
- Complexity waiver: eight children exceed the usual 3-6 guideline because contracts, single-record containment/OCC, multi-record crash recovery, attempt lifecycle, kind-specific completion/validity, request resolution, invalidation closure, and indexed scale/health each require a distinct primary proof and failure domain.
- Challenge and approval: `shaper-challenger` returned `decision: pass` with no blocking finding. Non-blocking refinements were incorporated by distinguishing supplementary store proof from integrated facade proof, crediting #2007 in REQ-009 coverage, and naming activity participation in #2002/#2003. The user explicitly selected `Approve and create` for this exact eight-packet graph.
- Board audit before closure: #2000 is the only dependency-ready build task; #2001-#2007 are blocked by the intended DAG. All children share parent #1979, change/digest/node identity, bounded scope, objective AC, and proof bundles. Recalled shaping memories were assessed in one complete batch before release.

[[2026-07-23T11:26:51+02:00]]
## Shape Notes
- Repair mode: user-authorized connected material reshape for #1979 and #2002-#2007 after #2002 proved the original transaction packet depended on request/activity producers placed downstream. Current source, admitted DN-003 authority, and archived #2000/#2001/#2008/#2009 were checked.
- Architecture decision: #2002 supplies the reusable transaction kernel and admission publication. #2003 owns attempt/activity transactions; #2004 owns finish/receipt/activity transactions; #2005 owns request/job-link transactions; #2006 owns invalidation/supersession transactions; #2007 owns assembled projections and health. This is legal packet refinement inside existing `IF-003` failure semantics, so delivery authority and digest remain unchanged.
- Invariant correction: `REQ-016` atomicity is covered jointly by #2002 (kernel/admission), #2003 (job/activity), #2004 (completion/receipt/activity), #2005 (request/job links), and #2006 (invalidation/corrective work). #2007 inspects manifests and resulting store integrity. The original row assigning the complete mutation to #2002 is historical and no longer operative.
- Dependency Closure Map: #2002 consumes current admission/receipt behavior plus archived #2001 job storage; #2003 consumes #2002; #2004 and #2005 consume #2003 and its transitive closure; #2006 consumes #2004 and #2005; #2007 consumes #2006. No remaining packet requires a sibling or descendant producer.
- Instruction repair: `w-task-decomposition` now requires and validates a Dependency Closure Map; `w-spec-shaping` passes it to challenge; `shaper-challenger` fails forward references; `test_shaper_interaction_contract.py` preserves the contract.
- Challenge and proof: shaper-challenger returned pass, with concrete participant-shape proof required for #2002. Focused contract suite passed 17 tests; skill/agent validators, Markdown lint, and diff check passed.
- Board route: aggregate remains in `collect` behind #2002-#2007. The connected leaf contracts are repaired and audited separately before release.

[[2026-07-24T16:11:56+02:00]]
## Collect Notes
- Classification: aggregate bootstrap projection for authoritative `DN-003` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml` at delivery digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`.
- Intent source: latest Shape Notes and graph `DN-003`, `IF-003`, and `PROOF-003`. The approved packet DAG assigns contracts, stores/OCC, transactions/recovery, attempts/claims, completion/receipt validity, requests, invalidation, and indexed health/history across packets #2000 through #2007.
- Child and dependency coverage: direct packet tasks #2000 through #2007 are parented by #1979 and archived completed; nested leaves #2008 through #2020 are archived completed under aggregates #2001 and #2003. Predecessor nodes #1977 and #1978 are archived completed. The aggregate dependency gate reports `ok`.
- Invariant map: latest Verify Notes across the leaves cover authority projection without copied normative truth; contained immutable job, finding, attempt, and receipt records; OCC and recoverable transactions; claim start/finalization/expiry recovery; currentness and code-history classes; scoped runtime requests; exact completion and replay; supersession and minimum invalidation closure; deterministic indexed query/history and corruption health.
- Tested revision: `e83e839b9153685399ea922ff01873298ffa424a`.
- Aggregate normal-path proof: at that SHA, `uv run pytest -q` over `test_jobs.py`, `test_attempts.py`, `test_findings.py`, `test_change_receipts.py`, `test_runtime_transaction.py`, `test_native_runtime.py`, `test_runtime_requests.py`, `test_invalidation.py`, and `test_runtime_query.py` passed 186 tests in 7.48 seconds. Two multiprocessing fork deprecation warnings were non-failing.
- AC-1: satisfied by the approved packet DAG, consistent `change:replace-delivery-pipeline` and `node:DN-003` task identity, parent links, and dependency audit.
- AC-2: satisfied by descendant module/interface ownership recorded in latest Verify Notes and by the bounded `PROOF-003` suite; no material expansion into dispatch, agents, MCP cutover, Cockpit, or legacy deletion was introduced.
- AC-3: satisfied because all direct and nested descendants are archived completed with latest PASS evidence, the dependency gate is clear, and current-HEAD aggregate proof exercises the public job, claim, completion, invalidation, transaction, recovery, request, and health boundaries.
- Residual decisions and requests: none; no resolved request records exist for this aggregate and no current Required Follow-up remains.
- Archive rationale: the completed descendants and SHA-linked aggregate proof satisfy `DN-003`, `IF-003`, `PROOF-003`, and all aggregate acceptance criteria.
