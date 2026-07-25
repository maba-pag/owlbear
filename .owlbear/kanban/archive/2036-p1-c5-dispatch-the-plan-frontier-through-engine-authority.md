---
id: 2036
title: 'P1-C5: Dispatch the plan frontier through engine authority'
status: archived
priority: high
created: 2026-07-25T02:46:52.874110+02:00
updated: 2026-07-25T08:53:41.428194+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-004
  - corrective
  - scope:core
  - scope:copilot
  - dispatch
  - orchestration
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2037
ac:
  - 'AC1: Given initially eligible plan jobs in unsorted storage order, `pick_jobs`
    returns stable delivery-node topological order with profile `planner`; build,
    accept, and audit entries retain their admitted profiles.'
  - 'AC2: Given concurrent starts, plan and build share one writer lease while accept
    and audit overlap no writer; conflicting starts return the stable coordination
    diagnostic without job or attempt mutation.'
  - 'AC3: Given one engine-selected job, the orchestrator invokes its assigned profile
    once, maps `Success | RateLimited | Crash` to the matching lifecycle operation,
    and returns before a repick; causal proof bypassing the returned disposition fails.'
  - 'AC4: Given a dependent build before reconciliation gates pass, `pick_jobs` omits
    it as predecessor-invalid; after the superseding plan receipt becomes current,
    the same query can select it without prose routing.'
  - 'AC5: After plan cutover, `orchestrator.agent.md` lists `ob-kanban/finish_plan`
    and not `finish_shape`; `w-orchestration` maps profile `planner` success to `finish_plan`
    and has no native `shaper` profile. Direct inspection and the assembled scenario
    verify both consumers.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Make the engine picker own plan/build/accept/audit topology, profiles, readiness, coordination, and one-invocation orchestration results.

## Scope
In scope: `DispatchRuntime` kinds, profiles, readiness, topological ordering, writer/readers at start, orchestration agent allowlist, workflow mapping, and selected-disposition-to-lifecycle-operation routing.

Out of scope: `DispatchRuntime._finish` participant-factory and holder-release transaction composition owned by #2039, MCP adapter names, planner implementation, and the complete DN-009 API.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-027; DEC-031; DEC-033; DN-004; MOD-003; IF-004; IF-015; PROOF-014.

Complexity waiver: the fifth AC closes the admitted production-orchestrator consumer edge inside the same assembled orchestration boundary.

Proof guidance: run dispatch topology/readiness/coordination checks and the assembled orchestrator scenario with only the selected runner replaced below that boundary.

[[2026-07-25T07:17:09+02:00]]
## Builder Notes
- Change envelope: align `DispatchRuntime` plan profile, the orchestrator tool allowlist, and `w-orchestration` success dispatch with `planner` and `finish_plan`; exercise the assembled native MCP scenario as the cheapest causal proof.
- Files probed: `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/tests/test_dispatch_runtime.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `share/agents/orchestrator.agent.md`, and `share/skills/w-orchestration/SKILL.md`.
- First proof failure: `DispatchRuntime.finish_plan` passed a coordination participant tuple to `NativeRuntime._finish`, whose current interface requires a participant callback.
- Blocking proof failure after a local probe: `server._finish_job` constructed generic `FinishJobRequest` for `finish_accept`, while `DispatchRuntime.finish_accept` requires `FinishAcceptRequest.reconciliation_plan_job_ids`.
- All probe edits were removed. The task returned to shape because its assembled proof required completion work outside the accepted task scope.
- Required shape repair: reconcile #2036 AC3 with the core completion and strict MCP adapter prerequisites before redispatch.

## Shape Notes
- Classification: prescribed connected split and dependency repair after the builder's assembled boundary exposed two independent prerequisite failure domains.
- #2039 exclusively owns `_finish` participant-factory and coordination-holder transaction composition. This task retains picker topology/profile/readiness/start coordination and selected-disposition routing.
- #2037 owns strict MCP request construction and delegation. Replaced the obsolete #2035 dependency with #2037, making #2039 transitive through #2037.
- Active chain: `#2039 -> #2037 -> #2036 -> #1983`.
- Failure key `#2036-AC3/accept-completion-prerequisite` resolves when #2039 supplies working completion composition and #2037 supplies strict `FinishAcceptRequest` construction; the existing assembled PROOF-014 scenario remains this task's causal discriminator.
- Shaper challenge validated the split's AC quality, current-source ownership, dependency closure, scenario closure, and boundary proof after task #2039 was materialized.

[[2026-07-25T08:09:07+02:00]]
## Shape Notes
- Rejection source: builder's assembled PROOF-014 scenario found a core participant-callback defect followed by a strict accept-request MCP defect. Classification: prescribed connected split/dependency repair; product behavior and admitted authority are unchanged.
- Created prerequisite #2039 for `DispatchRuntime._finish` participant-factory and holder-release transaction composition; carved that primitive out of this task's scope.
- Replaced obsolete dependency #2035 with #2037. #2037 depends on #2039, so this task's assembled orchestration proof receives both prerequisites in order.
- Failure key `#2036-AC3/accept-completion-prerequisite` is resolved by the live graph `#2039 -> #2037 -> #2036`; #1983 now depends on #2036 and remains parked behind the completed chain.
- Current-source checks: Python 3.14.6 imports and compiles all named modules; the assembled TestProof014 scenario executes and fails exactly where dispatch passes a tuple as native participant callback. This disconfirmed the challenger's temporary syntax concern.
- Shaper-challenger passed the materialized graph for readiness, authority, invariant ownership, dependency/scenario closure, boundary proof, and fidelity.
- Memory assessment: all recalled entries assessed; active-repository guidance applied.
- Resulting route: advance to build, dependency-gated until #2039 and #2037 archive.

[[2026-07-25T08:36:02+02:00]]
## Builder Notes
- Change envelope: `DispatchRuntime` plan profile and stable delivery-node topology ordering; existing focused runtime and assembled MCP proof; orchestrator native tool allowlist, `w-orchestration` disposition mapping, and the derived WIRING row.
- Files changed: `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/tests/test_dispatch_runtime.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `share/agents/orchestrator.agent.md`, `share/skills/w-orchestration/SKILL.md`, and `share/WIRING.md`.
- Change Module Map deviations: none. The required WIRING update was included because the orchestrator native-tool relationship changed.
- Implementation: `plan` entries now expose profile `planner`; `pick_waves` sorts eligible entries by a stable Kahn traversal of `DeliveryNode.dependencies`; the PROOF-014 audit fixture uses job 7 so acceptance-created reconciliation job 5 remains authoritative.
- Proof selected: focused runtime dispatch tests, exact assembled TestProof014 MCP scenario, reconciliation gate test, ecosystem validators and regression, scoped lint/format, diagnostics, whitespace diff, and builder challenge.
- Durable-test justification: added one maintained runtime test because storage-order-independent delivery topology is an observable shared dispatch contract and the prior suite did not distinguish it from incidental persistence ordering.
- Commands run: `uv run pytest -q serve/kanban/tests/test_dispatch_runtime.py` (9 passed); `uv run pytest -q serve/mcp-kanban/tests/test_mcp_surface_contract.py` (5 passed, including TestProof014); `uv run pytest -q serve/kanban/tests/test_native_runtime.py::test_build_start_reconciliation_gates_are_mutation_free` (1 passed); `uv run python .owlbear/scripts/validate_agents.py`; `uv run python .owlbear/scripts/validate_skills.py`; `uv run pytest -q tests/test_agent_ecosystem_validation.py` (8 passed; three unrelated Python 3.16 deprecation warnings); explicit `ruff check` and `ruff format --check`; `uv run lint` on all owned paths; `git diff --check`.
- AC-to-evidence map: AC1 is proved by `test_pick_waves_orders_plan_frontier_by_delivery_topology`, which reverses returned storage order and asserts ordered planner entries; AC2 is covered by the existing writer/readers and no-mutation runtime tests; AC3 is proved by the assembled MCP TestProof014 path through pick, start, one runner invocation, finish/release/recovery, unavailable-profile halt, and terminal events; AC4 is proved by `test_build_start_reconciliation_gates_are_mutation_free`; AC5 is proved by direct consumer edits plus agent and skill validators and `test_agent_ecosystem_validation.py`.
- Current failure-key resolution: `#2036-AC3/accept-completion-prerequisite` is fully closed by archived prerequisites #2039 and #2037 plus the passing assembled TestProof014 path; reconciliation job 5 is no longer overwritten by the acceptance fixture.
- Builder-challenger: pass. It independently ran the focused dispatch, MCP surface, and ecosystem suites with 22 passed and three unrelated warnings.
- Memory: assessed all 20 recalled entries; applied the active-workspace and refined-proof-scope guidance.
- Follow-up risks: none within this task scope; no changes were made to `_finish` composition, MCP adapter naming/contracts, planner implementation, or the complete DN-009 API.

[[2026-07-25T08:40:56+02:00]]
## Verify Notes
- Candidate reviewed: `ffd863aebf39636307fd59ddc319cff21d4aa948` (`feat: dispatch engine plan frontier (#2036, builder)`). Named authorities checked: task AC1-AC5, failure key `#2036-AC3/accept-completion-prerequisite`, `DispatchRuntime`, `TestProof014NativeMcpScenario`, the orchestrator allowlist, `w-orchestration`, and `share/WIRING.md`.
- Prerequisite boundaries: #2039 and #2037 are archived/completed. #2039 owns native completion participant composition; #2037 owns strict MCP `FinishAcceptRequest` construction and bridge delegation. Their scoped task records confirm no intrusion into #2036 picker or orchestration-consumer scope.
- Change Module Map: candidate changed only the mapped dispatch runtime, focused runtime/MCP proof, and required agent/skill/WIRING consumers. No candidate scope leakage found. Current worktree memory and `.vscode/mcp.json` churn is unrelated and untouched.
- AC1 PASS: `DispatchRuntime.pick_waves` maps `plan` to `planner` and applies stable delivery-node Kahn ordering. `test_pick_waves_orders_plan_frontier_by_delivery_topology` reverses storage order and passed in `uv run pytest -q serve/kanban/tests/test_dispatch_runtime.py` (9 passed). Build, accept, and audit profile mapping remains builder, acceptor, auditor.
- AC2 PASS: the same 9-test suite passed writer-versus-reader coordination checks. `test_writer_conflict_and_release_are_atomic` proves plan/build writer conflict is diagnostic and mutation-free; `test_readers_coexist_and_block_writer` proves accept/audit reader overlap and stable writer conflict.
- AC3 REJECT: exact `TestProof014NativeMcpScenario` passed, and does exercise real pick/start/finish/release/recovery MCP adapters with only the selected runner replaced below that boundary. It proves unavailable installed profile returns before claim/mutation and records one terminal event per attempt. But its test-local `dispatch_one` selects lifecycle operation in a direct match block and the assertions only compare scripted runner call order plus terminal kinds. A bypass that ignores the returned disposition and chooses lifecycle calls by attempt order could still satisfy those assertions. Therefore the proof does not establish engine-selected entry/profile feeds the runner exactly once and its returned `Success | RateLimited | Crash` causally selects exactly one matching lifecycle operation before repick. Failure key `#2036-AC3/accept-completion-prerequisite` is resolved by archived #2039/#2037; this is a distinct first verifier finding: `#2036-AC3/disposition-causality-negative-control`.
- AC4 PASS: `uv run pytest -q serve/kanban/tests/test_native_runtime.py::test_build_start_reconciliation_gates_are_mutation_free` passed (1 passed). Direct source inspection confirms `NativeRuntime._reconciliation_predecessors` returns `PREDECESSOR_INVALID` for active/missing/ambiguous predecessor state and currentness selects the superseding reconciliation receipt. No prose routing observed.
- AC5 PASS: direct inspection shows actual `orchestrator.agent.md` allowlist has `ob-kanban/finish_plan` and no `finish_shape`; `w-orchestration` uses native `planner`, no native `shaper`, maps success to `finish_plan`, and requires unavailable-profile halt before `start_job`; WIRING matches. `uv run python .owlbear/scripts/validate_agents.py`, `uv run python .owlbear/scripts/validate_skills.py`, and `uv run pytest -q tests/test_agent_ecosystem_validation.py tests/test_write_guard_hooks.py tests/test_deny_non_doc_writes.py` passed (58 passed; 3 unrelated Python 3.16 deprecation warnings).
- Checks run: exact TestProof014 (1 passed); full MCP contract suite (5 passed); focused dispatch suite (9 passed); exact reconciliation gate (1 passed); scoped ruff check and format check (passed); `git show --check ffd863aebf39636307fd59ddc319cff21d4aa948` (passed); current diff check (passed).
- Prior same-failure-key check: task history has no prior verifier rejection for `#2036-AC3/disposition-causality-negative-control`. The earlier builder rejection was the now-resolved MCP acceptance prerequisite, so protocol routes this first distinct proof failure to build rather than shape.
- Patches applied: none. The needed work is a durable proof strengthening, outside verifier patch-pass budget.
- Verifier-challenger result: pass for REJECT. It confirmed TestProof014 can false-green through attempt-order routing and that a negative control is a concrete accepted-contract build repair.

### Required Follow-up
1. In the existing `TestProof014NativeMcpScenario`, make the runner disposition the asserted causal input to exactly one lifecycle operation. Add a negative control that deliberately bypasses that returned disposition and demonstrably fails; do not replace pick/start/assembled MCP boundaries or mutate production contracts.
2. Prove no fresh `pick_jobs` occurs between selected disposition and the corresponding finish/release/recovery operation, and retain the missing-installed-profile no-claim/no-mutation proof.
3. Re-run exact TestProof014, the focused MCP and dispatch suites, AC4 gate proof, agent/skill validators plus ecosystem regressions, ruff/format, and `git show --check` before returning to verify.

- Final route: REJECT to build.

[[2026-07-25T08:48:25+02:00]]
## Builder Notes
- Change envelope: repair only `#2036-AC3/disposition-causality-negative-control` in `TestProof014NativeMcpScenario`; no production, MCP-contract, agent/skill/WIRING, or sibling-task changes.
- Files changed: `serve/mcp-kanban/tests/test_mcp_surface_contract.py` and the final task record.
- Change Module Map: no deviations. The existing native MCP scenario remains the proof owner; test-local ledger helpers observe rather than replace real `pick_jobs`, `start_job`, finish, release, and recovery boundaries.
- Proof repair: each exact `Success | RateLimited | Crash` runner object determines one operation. The ledger binds runner-object identity, derived operation, actual wrapped MCP call for the same attempt ID, persisted terminal event, and unchanged pick counter from disposition selection through terminal operation. The unavailable installed-profile halt still precedes claim and mutation.
- Negative control: a builder `Success` has a superficially valid `finish_build` and `succeeded` ledger entry but an observed `finish_plan` operation. The causal assertion fails, demonstrating that attempt-order or post-hoc routing cannot pass.
- Durable-test justification: retained and strengthened the existing assembled public MCP scenario because its regression risk is cross-boundary orchestration causality that is difficult to observe manually; no separate test artifact was added.
- Commands run: exact `TestProof014NativeMcpScenario` (2 passed); MCP contract suite (6 passed); dispatch runtime suite (9 passed); reconciliation gate (1 passed); agent and skill validators plus ecosystem regressions (58 passed, 3 unrelated Python 3.16 deprecation warnings); ruff check and format check; `git diff --check`; `git show --check f6f3926dc` and `git show --check ffd863aeb`.
- AC-to-evidence: AC1 and AC2 remain covered by the passing dispatch suite; AC3 is covered by the assembled native MCP scenario, observed-operation ledger, negative control, and no-repick assertion; AC4 is covered by the passing reconciliation gate; AC5 remains covered by validators and ecosystem regressions.
- Current failure-key resolution: `#2036-AC3/disposition-causality-negative-control` resolved by identity-bound runner dispositions, observed actual lifecycle operations keyed by attempt ID, persisted terminal results, pick-boundary records, and an executable attempt-order bypass rejection.
- Builder-challenger: pass. It independently exercised the bypass where expected ledger fields were retained but the actual observed operation differed, and confirmed that the negative control fails.

[[2026-07-25T08:51:59+02:00]]
## Verify Notes
- Candidate and repair reviewed: base `ffd863aebf39636307fd59ddc319cff21d4aa948`; proof repair `514e8c584a2c1aac2a6d5ddc4ff598f331175ea9`; prior rejection `f6f3926dc`. Named authorities checked: task AC1-AC5, DEC-027, DEC-031, DEC-033, DN-004, MOD-003, IF-004, IF-015, and PROOF-014.
- Latest Required Follow-up closed: `#2036-AC3/disposition-causality-negative-control`. Repair `514e8c584` strengthens only `TestProof014NativeMcpScenario` and the task record. It adds no production or agent-ecosystem drift; the accumulated changed modules remain the shaped dispatch runtime, focused runtime/MCP proofs, and required orchestrator/skill/WIRING consumers.
- Normal-path boundary exercised: exact TestProof014 uses real `server.pick_jobs`, `server.start_job`, and wrapped native `finish_*`, `release_job`, and `recover_expired_claims` MCP operations. Only the selected profile runner is replaced below that boundary. The selected engine entry/profile is passed to the runner once; the exact returned `Success | RateLimited | Crash` object is stored by identity in the lifecycle ledger and derives the lifecycle operation. Observed wrapped MCP calls are bound by attempt ID; each attempt has one start and one matching terminal release/recovery/finish event. `selected_pick == terminal_pick` proves no repick between disposition and lifecycle operation. Unavailable `acceptor` halts before claim or mutation, demonstrated by unchanged jobs and attempts.
- Causal negative control: `test_disposition_causality_rejects_attempt_order_bypass` deliberately provides a builder `Success` ledger with observed `finish_plan`; `_assert_disposition_causality` raises `AssertionError` on that operation mismatch, establishing failure from causality rather than fixture setup.
- Checks run: exact positive and negative TestProof014 scenarios: `2 passed`; focused dispatch, MCP contract, and exact reconciliation gate checks: `16 passed`; `validate_agents.py`: passed; `validate_skills.py`: passed; ecosystem/write-guard checks: `58 passed` with 3 unrelated Python 3.16 deprecation warnings; scoped `ruff check` and `ruff format --check`: passed; `git show --check 514e8c584`: passed.
- AC-to-evidence: AC1 stable planner topology/profile mapping and AC2 writer/reader coordination are covered by focused dispatch checks. AC3 is covered by the exact native-MCP positive ledger and executable attempt-order bypass. AC4 is covered by `test_build_start_reconciliation_gates_are_mutation_free`. AC5 is covered by direct allowlist/workflow/WIRING inspection plus agent and skill validators and ecosystem checks.
- Prior same-failure-key check: `f6f3926dc` is the first and only prior verifier rejection for `#2036-AC3/disposition-causality-negative-control`; this retry repairs and proves that exact key, so no repeated repair-cycle escalation applies.
- Memory: recalled verifier entries assessed for task `2036`.
- Patches applied by verifier: none.
- Verifier-challenger result: `pass`. It confirmed the repaired PROOF-014 binds returned-disposition identity, selected lifecycle operation, observed MCP operation, terminal events, and unchanged pick count; it also confirmed the executable attempt-order bypass fails and the repair remains test-only.
- Final route: PASS to collect.

[[2026-07-25T08:53:41+02:00]]
## Collect Notes
- Classification: leaf. Task #2036 has no child tasks, aggregate title/tags, or aggregate collect contract; its parent #1968 is not mutated.
- Current lifecycle evidence: newest `## Verify Notes` records PASS at `1af6e580b2685c02147baef07ed88f62577a2fe3`, reviewing implementation `ffd863aebf39636307fd59ddc319cff21d4aa948` and causal proof repair `514e8c584a2c1aac2a6d5ddc4ff598f331175ea9`. The prior `#2036-AC3/disposition-causality-negative-control` follow-up is explicitly closed; no later unresolved follow-up exists.
- Invariant / AC closure: AC1 stable plan topology and admitted profiles plus AC2 writer/read coordination are covered by focused dispatch checks. AC3 is covered by the exact native MCP scenario, identity-bound returned disposition, one selected runner invocation, no-repick ledger, and executable attempt-order bypass which raises on a mismatched terminal operation. AC4 is covered by the mutation-free reconciliation gate check. AC5 is covered by direct `orchestrator.agent.md`, `w-orchestration`, and `share/WIRING.md` inspection, agent/skill validators, and ecosystem checks; consumers use `planner` / `finish_plan`, retain no native `shaper` profile or `finish_shape` allowlist.
- Exact mapped change set: `ffd863aeb` changed the shaped dispatch runtime, focused runtime and MCP proof, `share/agents/orchestrator.agent.md`, `share/skills/w-orchestration/SKILL.md`, and `share/WIRING.md`; `514e8c584` strengthens only `serve/mcp-kanban/tests/test_mcp_surface_contract.py` and the task record. This aligns the WIRING, agent, and skill consumers with engine authority.
- Proof evidence: exact positive and negative PROOF-014 scenarios passed (2); focused dispatch, MCP contract, and reconciliation checks passed (16); agent and skill validators passed; ecosystem/write-guard checks passed (58; three unrelated Python 3.16 deprecation warnings); scoped ruff and formatting checks plus Git patch checks passed. The verifier challenger returned `pass` for the repaired causal proof.
- Dependency / request closure: dependency #2037 and prerequisite #2039 are archived `completed`; current dependency projection is `ok`. `list_requests` reports no pending or resolved structured requests for #2036.
- Workspace custody: the only task-owned dirty path before archive was the claimed task record; unrelated worktree changes remain untouched. Archive rationale: all ACs, current follow-up, prerequisites, consumers, proof evidence, and challenger review are closed.
