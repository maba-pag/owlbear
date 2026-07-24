---
id: 2025
title: 'P4-04: Run graph-aware native orchestration'
status: build
priority: high
created: 2026-07-24T16:54:49.020973+02:00
updated: 2026-07-24T16:54:49.020973+02:00
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
parent: 1980
depends_on:
  - 2022
  - 2023
  - 2024
ac:
  - 'AC-1: The graph-aware orchestrator dispatches each job and assigned profile only
    from one fresh `DispatchRuntime.pick_waves` result, starts it through `DispatchRuntime`,
    finalizes one structured attempt outcome, and replans after consuming the wave
    without interpreting prose.'
  - 'AC-2: Crash, expiry, rate limit, stale lease, checkout setup failure, cleanup
    failure, and orphan recovery use typed dispatch, lifecycle, or health outcomes;
    observed execution contains no overlapping writers and no `accept | audit` overlap
    with a writer.'
  - 'AC-3: The maintained PROOF-014 scenario crosses public dispatch planning/start/finalization/recovery
    and proof-checkout boundaries in a temporary repository, exercising `shape | build
    | accept | audit`, exact commit materialization, cleanup, and current-state replanning.'
  - 'AC-4: The orchestrator agent, workflow skill, prompt, and `share/WIRING.md` pass
    ecosystem validation and expose native job/profile routing only; they do not route
    legacy builder/verifier/collector task stages or copy normative graph contracts.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-004`. Resolve normative behavior from `DN-004`, `IF-004`, `IF-005`, `REQ-022`, `PROOF-014`, and design §§8.6-8.7/12; this record is not specification authority.

## Outcome
Replace task-board orchestration wiring with graph-aware native job execution. The orchestrator consumes fresh engine-selected waves, dispatches exact profiles, uses proof checkout for read-only proof jobs, finalizes typed attempts once, recovers, and replans.

## Envelope
In: orchestrator agent, `w-orchestration`, `/orchestrate`, `share/WIRING.md`, and durable PROOF-014 integration tests. Preserve ecosystem loading/structure rules. Out: shaper/builder/acceptor/auditor role implementation, MCP/Cockpit surfaces, and broad legacy deletion owned by later nodes.

Proof guidance: real public dispatch and checkout boundaries in a temporary repository; replace only clock and subagent runner as PROOF-014 permits.