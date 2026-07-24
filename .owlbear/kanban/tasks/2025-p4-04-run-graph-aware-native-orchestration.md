---
id: 2025
title: 'P4-04: Run graph-aware native orchestration'
status: verify
priority: high
created: 2026-07-24T16:54:49.020973+02:00
updated: 2026-07-24T19:31:10.907650+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - orchestration
  - integration
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-004
  - mcp
  - bridge
  - interface:IF-015
  - risk:RISK-013
parent: 1980
depends_on:
  - 2022
  - 2023
  - 2024
ac:
  - 'AC-1: Given `KANBAN_DIR` and an admitted `change_id`, the assembled MCP server
    registers native tools `pick_jobs | start_job | finish_shape | finish_build |
    finish_accept | finish_audit | release_job | recover_expired_claims`; contract
    inspection proves their strict schemas and stable parameter/domain diagnostic
    mapping.'
  - 'AC-2: Given eligible `shape | build` jobs, the bridge pick/start/purpose-specific
    finish/release/recovery calls return the frozen DispatchRuntime/IF-003 outcomes;
    replay, non-owner, stale-authority, stale-lease, conflict, crash, and strict-expiry
    cases preserve the asserted job/event/coordination mutation boundaries.'
  - 'AC-3: Given an eligible `accept | audit` job and resolvable candidate commit,
    `start_job` returns its claim/event plus contained checkout context at the canonical
    SHA; setup failure leaves it unclaimed, rejected start removes the prepared root,
    and exact active-claim replay reuses the same context without a second worktree.'
  - 'AC-4: Given a claimed `accept | audit` job, finish removes its checkout before
    receipt creation, while release and expired recovery clear matching claim/coordination
    state and request idempotent cleanup; a residual checkout yields typed orphan
    evidence, finish creates no receipt, and unrelated proof roots remain unchanged.'
  - 'AC-5: The maintained PROOF-014 scenario sends `shape | build | accept | audit`
    profile calls from fresh `pick_jobs` waves through a replaced subagent runner,
    finalizes one structured attempt per job, exercises rate-limit and crash recovery,
    and replans current state; ecosystem inspection shows the native contract is installed
    while `pick_tasks` remains the explicit bootstrap default pending DN-012.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-004-PK-004`. Resolve normative behavior from `DN-004`, `IF-004`, `IF-005`, `IF-015`, `RISK-013`, `PROOF-014`, accepted `DEC-025`/`DEC-026`, and design §§8.6/9.5/14/16/18; this record is not specification authority.

## Outcome
Expose the closed native work bridge through the existing OwlBear Kanban MCP server and install the graph-aware orchestration contract beside the bootstrap task carrier. The native loop consumes a fresh plan, starts one typed attempt, dispatches its assigned profile, finalizes through the purpose-specific tool, recovers typed failures, and replans without interpreting prose. DN-012 later makes that loop the sole production route and removes the legacy carrier atomically.

## Module Map

### Bootstrap MCP bridge
Extend the existing `owlbear_mcp_kanban` lifespan and models; do not add a second server or transport. Assemble one `DispatchRuntime` per requested admitted `change_id` from the canonical project layout rooted at `KANBAN_DIR`: native work under the Kanban root, sibling `changes/` authority, repository history from the workspace repository, the configured positive claim-expiry policy, and IF-005 under `.owlbear/scratch/proof/`. Malformed parameters use the server's stable MCP error envelope; dispatch, lifecycle, and checkout diagnostics remain structured result data.

Register only these native bridge tools: `pick_jobs`, `start_job`, `finish_shape`, `finish_build`, `finish_accept`, `finish_audit`, `release_job`, and `recover_expired_claims`. Reuse frozen IF-003 request/result types and `DispatchRuntime`; do not add native lifecycle semantics or expose change, admission, request, evidence, health, or history operations owned by DN-009.

For `shape | build`, `start_job` returns the strict dispatch start outcome. For `accept | audit`, it prepares IF-005 at `candidate_revision` before claim creation and returns checkout root/path, canonical commit, and manifest with the dispatch outcome. Setup failure creates no claim. Start rejection removes the prepared checkout. Exact active-claim replay returns the same checkout context without rematerializing. Finish cleans before creating an accept/audit receipt and refuses finalization when cleanup leaves a health path. Release and expired-claim recovery clear matching lifecycle/coordination authority and perform idempotent cleanup; residual state remains a typed orphan finding, not a stranded claim.

### Orchestrator contract during bootstrap
Add the native `pick_jobs` plan/start/profile/finalize/recover procedure to `orchestrator.agent.md`, `w-orchestration`, `/orchestrate`, and `share/WIRING.md` as an explicitly non-default bootstrap capability. Preserve the operative `pick_tasks` builder/verifier/collector carrier required by design §9.5 until DN-012's atomic cutover; do not alias legacy tasks into native jobs or let one loop consume the other's state. The native contract routes assigned profiles `shaper | builder | acceptor | auditor` mechanically; DN-008 and DN-014 still own final acceptor/auditor role bodies. PROOF-014 replaces only the subagent runner while proving profile dispatch and never claims those downstream role implementations exist.

DN-012 owns the activation/removal delta: make native orchestration the sole `/orchestrate` route, remove `pick_tasks` and builder/verifier/collector stage routing, and prove absence under PROOF-009. This packet must leave that future switch mechanically identifiable in the agent/skill/prompt wiring without implementing it early.

## Envelope
In: narrow `serve/mcp-kanban` IF-015 adapters/models/lifespan tests; the minimum IF-005 read/replay/cleanup-result deepening needed for composite starts; native orchestration contract additions to the existing orchestrator agent, `w-orchestration`, `/orchestrate`, and `share/WIRING.md`; durable PROOF-014 scenarios over real MCP registration, DispatchRuntime stores, temporary Git checkouts, and a replaced subagent runner.

Out: activation of native orchestration as the default; removal of the bootstrap task carrier; DN-009 change/admission/request/evidence/health/history APIs; Cockpit surfaces; final shaper/builder/acceptor/auditor role implementation; a second MCP server, direct Python runner, native-to-legacy adapter, or new `dispatch_runtime.py`.

## Prior Rejection Evidence
The previous builder found that `DispatchRuntime` and IF-005 existed but no public native tool transport was reachable from the VS Code orchestrator. Global design re-entry produced approved DEC-025/DEC-026, IF-015, RISK-013, and re-admission `admission-b56fedd21a54`. Archived #2022-#2024 provide the verified IF-004/IF-005 substrate. The repaired packet assigns DN-004's omitted MOD-002 bridge obligation here while preserving the design §9.5 carrier until DN-012; it neither expands DN-004 nor duplicates DN-009/DN-012.

[[2026-07-24T19:17:56+02:00]]
## Shape Notes

Repair classification: material authority re-entry followed by a local task repair. The prior builder rejection correctly identified that the VS Code orchestrator could not reach transport-free `DispatchRuntime`; no product files were changed by that attempt.

User decisions DEC-025 and DEC-026 selected one narrow DN-004 MCP work bridge and enriched its existing `start_job` operation for `accept | audit` proof checkout context. Authority now defines IF-015, RISK-013, composite checkout-before-claim ordering, exact active-claim replay, rejected-start cleanup, finish-before-receipt cleanup, release/recovery cleanup, and DN-009 completion/supersession. The final revision `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca` is admitted by `admission-b56fedd21a54`; baseline evidence records 979 Kanban tests, 456 MCP-Kanban tests, and 12 agent ecosystem validations passing.

Replaced the complete operative task body and AC instead of appending stale instructions. The packet now owns DN-004's omitted MOD-002/IF-015/RISK-013 bridge implementation, names the exact eight native tools, concrete runtime assembly, strict result mapping, IF-005 composite start/replay/cleanup behavior, and assembled PROOF-014 scenario. Broader DN-009 APIs, downstream acceptor/auditor role bodies, Cockpit, and cutover remain out.

Resolved the challenger bootstrap-carrier finding by installing native orchestration as an explicitly non-default contract while preserving `pick_tasks` builder/verifier/collector routing as the operative design §9.5 carrier. DN-012 owns activation of native-only routing and legacy absence proof; the two loops must not alias or consume each other's state.

Failure-key resolution: `missing-public-native-transport` is closed by IF-015 and the MOD-002 packet scope; `proof-checkout-unreachable` is closed by DEC-026 composite `start_job`; `premature-carrier-cutover` is closed by the non-default bootstrap wiring and explicit DN-012 activation boundary. Archived #2022-#2024 supply verified IF-004/IF-005 prerequisites. Final shaper-challenger decision: pass; no remaining task repair requested. Board route: build with parent #1980 and dependencies #2022/#2023/#2024 unchanged.

[[2026-07-24T19:31:10+02:00]]
## Builder Notes

- Change envelope: native IF-015 work bridge only: MCP runtime assembly and strict adapters, IF-005 checkout composition in existing DispatchRuntime, MCP contract snapshot, and non-default bootstrap wiring. No second transport, no DN-009 APIs, Cockpit work, role-body implementation, native-to-legacy adapter, or DN-012 carrier cutover.
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/src/owlbear_kanban/proof_checkout.py`, `share/agents/orchestrator.agent.md`, `share/skills/w-orchestration/SKILL.md`, `share/prompts/orchestrate.prompt.md`, and `share/WIRING.md`.
- Change Module Map deviations: none. `DispatchRuntime` gained the minimum IF-005 composition because it already owns start/finish/release/recovery coordination; MCP remains a thin typed adapter.
- Proof selected: no new durable tests. Existing MCP registry, server lifespan, annotation, dispatch-runtime, proof-checkout, and ecosystem wiring tests cover the public boundaries; the changed registry snapshot is required deployment-contract maintenance.
- Commands run: `uv run ruff check` on all four touched Python modules passed; focused MCP, dispatch, checkout, and wiring suite passed with 66 tests; `validate_agents.py` and `validate_skills.py` passed.
- AC-to-evidence map:
  - AC-1: exact eight native tools registered with strict Pydantic parameter models; MCP surface and annotations covered by focused tests.
  - AC-2: typed adapters delegate to frozen DispatchRuntime results; dispatch regression suite passed.
  - AC-3: accept/audit start composes exact-commit checkout before claim, reuses an existing checkout on replay, and removes newly prepared checkout after rejected start; focused dispatch and checkout suites passed.
  - AC-4: accept/audit finish cleans before finalization; release and expired recovery request idempotent cleanup and preserve orphan diagnostics; focused dispatch and checkout suites passed.
  - AC-5: orchestrator agent, workflow, prompt, and derived wiring define explicit bootstrap-only native dispatch while retaining `pick_tasks` as default; ecosystem validation passed.
- Current failure-key resolutions: `missing-public-native-transport` resolved by closed IF-015 MCP tools; `proof-checkout-unreachable` resolved by composite `start_job`; `premature-carrier-cutover` resolved by explicit non-default wiring.
- Builder-challenger: pass. It found no concrete blocker and independently ran focused MCP/dispatch/checkout and wiring tests.
- Follow-up risks: native bridge is deliberately temporary; DN-009 must supersede it and DN-012 owns atomic carrier cutover and legacy absence proof.
