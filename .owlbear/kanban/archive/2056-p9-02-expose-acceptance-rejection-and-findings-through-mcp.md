---
id: 2056
title: 'P9-02: Expose acceptance rejection and findings through MCP'
status: archived
priority: high
created: 2026-07-25T17:19:35.872293+02:00
updated: 2026-07-25T18:02:07.518709+02:00
tags:
  - phase-9
  - scope:mcp-kanban
  - acceptance
  - findings
  - invalidation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-CORR-001
  - interface:IF-010
parent: 1985
depends_on:
  - 2055
  - 1981
ac:
  - 'AC-1: With exclusions unset, the live FastMCP registry exposes strict `reject_accept
    | list_findings | show_finding` schemas with mutation/read annotations and current
    native job identity fields; registry and source inspection show old task operations
    and compatibility aliases remain absent.'
  - 'AC-2: Public `reject_accept` forwards its validated payload to `DispatchRuntime.reject_accept`
    and returns the typed outcome; currentness, reference, conflict, cleanup, and
    transaction diagnostics map to stable JSON domain codes, while pre/post snapshots
    prove failed calls publish no partial state.'
  - 'AC-3: Public `list_findings` returns bounded cursor pages in stable finding order
    and `show_finding` returns one full `Finding`; a missing identity returns a stable
    not-found code without mutation.'
  - 'AC-4: An assembled MCP scenario starts a real accept job with engine proof checkout,
    rejects it, observes findings, supersession, minimum jobs, failed attempt and
    cleanup, then replays the same call; only temporary authority, work, and repository
    stores replace lower persistence.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; corrective IF-010 slice required by `WF-004` and `PROOF-007` for `DN-008`.

## Outcome
Expose strict public rejection and finding operations so read-only acceptors can reach the engine-owned corrective transaction.

## Envelope
In: `reject_accept`, `list_findings`, `show_finding`, schemas, annotations, errors, registry, and assembled MCP proof.

Out: new core semantics, acceptor role, Cockpit, request resolution, compatibility aliases, setup, and seed work.

[[2026-07-25T17:58:23+02:00]]
## Builder Notes
- Adopted the interrupted same-task MCP edits and completed the shaped transport-only envelope in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` and `server.py`.
- Added public `reject_accept`, `list_findings`, and `show_finding` operations with live registry exports, mutation/read annotations, strict current job identity fields, typed `Finding` and nested corrective invalidation schemas, JSON sequence adaptation, stable stale-cursor and missing-finding codes, and typed forwarding to `DispatchRuntime.reject_accept`.
- Updated the authoritative 25-tool deployment contract and added one durable assembled MCP proof. The proof uses copied temporary admitted authority, temporary work stores, the current repository as Git history, and a real `ProofCheckoutManager`; it exercises public plan/build/start/reject/query operations, exact request forwarding, supersession, minimum corrective work, failed attempt, reader release, cleanup, replay, bounded canonical finding pages, stable read errors, and byte-for-byte failure atomicity.
- AC-1: live registry/annotations and nested generated schema are asserted in `test_mcp_surface_contract.py`; removed task tools and aliases remain absent.
- AC-2: assembled forwarding spy plus valid and invalid public calls prove typed result/diagnostic behavior and no partial failed publication.
- AC-3: public two-page query proves stable finding order/cursors; stale and missing identities return stable JSON `ToolError` codes without mutation.
- AC-4: real accept proof checkout is created by the engine and removed only after the complete corrective transaction; replay is exact and failure preserves checkout and stores.
- Validation: full owning package `uv run pytest serve/mcp-kanban/tests -q --tb=short` passed 83 tests. Focused post-lint public boundary run passed 14 tests. Explicit `uv run lint` over all four owned source/test files passed every applicable hook. Builder challenger decision: pass.

### Required Follow-up
None.

[[2026-07-25T18:01:30+02:00]]
## Verify Notes
- Independently inspected builder commit `52f2c881` against the exact admitted authority: IF-010 requires strict purpose-specific MCP operations and stable failure codes without partial mutation; WF-004 requires typed findings, minimum corrective jobs, and invalidation; PROOF-007 requires an engine-created exact-commit disposable checkout with exact minimal correction and cleanup. The implementation and proof remain inside the shaped transport-only envelope.
- AC-1: confirmed live exported schema requires current change/job/attempt/claim/actor/process identities and references strict `Finding` plus nested `InvalidationParams`; all nested MCP models forbid extras, annotations match mutation/read semantics, and the 25-tool contract excludes old task operations.
- AC-2: confirmed validated inputs become a strict core `RejectAcceptRequest` and are forwarded to `DispatchRuntime.reject_accept`; public assembled proof observes the typed result, stable invalidation diagnostic, exact replay, and byte-identical failed state.
- AC-3: confirmed canonical bounded finding pagination, stable cursors, full immutable finding reads, stable stale/missing `ToolError` codes, and read-only error snapshots.
- AC-4: confirmed the assembled proof invokes exported MCP operations over real dispatch/native runtimes and engine-created proof checkout; only temporary authority/work/proof stores and repository history replace persistence. It observes supersession, one minimum corrective build job, failed attempt, reader release, cleanup, and replay.
- Independent validation: `uv run pytest serve/mcp-kanban/tests serve/kanban/tests/test_dispatch_runtime.py serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_invalidation.py serve/kanban/tests/test_proof_checkout.py -q --tb=short` passed 178 tests. Mechanical `load_change` assertion returned exact digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. VS Code diagnostics are clean for all four changed files. Verifier challenger decision: pass.

### Required Follow-up
None.

[[2026-07-25T18:02:07+02:00]]
## Collect Notes
- Confirmed the shaped leaf outcome is complete at builder commit `52f2c881` and independently verified at `777ea78d`; both stage notes have no required follow-up.
- Confirmed dependencies #2055 and #1981 are archived with `completed`, no pending structured requests exist, and collection changed no product or proof file.
- Closure evidence covers every AC: strict 25-tool live schema and annotations; typed public rejection forwarding with stable diagnostics and failed-call atomicity; bounded canonical finding pages plus full reads and stable read errors; and an assembled real proof-checkout rejection with exact minimum correction, cleanup, and replay.
- Final independent regression evidence is 178 passing MCP/core corrective-runtime tests at the verified descendant, with exact admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

### Required Follow-up
None.
