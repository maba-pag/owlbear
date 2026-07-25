---
id: 2057
title: 'P9-03: Install the independent node acceptor workflow'
status: verify
priority: high
created: 2026-07-25T17:19:45.152185+02:00
updated: 2026-07-25T18:08:40.438167+02:00
tags:
  - phase-9
  - scope:agent
  - acceptor
  - orchestrator
  - read-only
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-002
  - interface:IF-009
parent: 1985
depends_on:
  - 2056
ac:
  - 'AC-1: `w-node-acceptance` rehydrates only successful `start_job` identity, engine
    checkout, admitted node authority, current plan, packet receipts, and exact-SHA
    proof; it requires replacements and before/after tracked state, then returns one
    complete `AcceptorSuccess | AcceptanceRejected | AcceptanceBlocked` disposition.'
  - 'AC-2: The `acceptor` agent has no edit or lifecycle tools, uses the read-only
    write guard and tracked-diff check, executes proof only in the engine checkout
    or scratch, and cannot pick, start, finish, release, or approve authored tracked
    changes; agent validation and WIRING inspection prove the boundary.'
  - 'AC-3: `w-orchestration` maps `AcceptorSuccess` fields unchanged to `finish_accept`,
    `AcceptanceRejected` fields unchanged to `reject_accept`, and `AcceptanceBlocked`
    with unchanged identity to `release_job`; orchestrator exposes the acceptor and
    rejection tool, halts after one job, and does not classify findings or assemble
    evidence.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-002`. Resolve behavior from REQ-006, WF-004, IF-009, NEG-003, NEG-009, RISK-008, and PROOF-007.

## Outcome
Install one hard-read-only acceptor role, its exact-commit workflow, and deterministic orchestrator routing.

## Envelope
In: workflow, agent declaration, write guard, orchestrator mapping, agent validation, and WIRING.

Out: runtime/MCP semantics, auditor work, setup/seed propagation, and Cockpit.

[[2026-07-25T18:08:40+02:00]]
## Builder Notes
- Added `w-node-acceptance` as the single procedure for one engine-started exact-commit accept job. It rehydrates only successful execution identity, engine checkout, admitted target, current plan, packet receipts, and exact-SHA proof; records allowed replacements and tracked state before/after every command; confines proof to checkout/scratch; and emits one complete `AcceptorSuccess`, `AcceptanceRejected`, or `AcceptanceBlocked`.
- Added `acceptor.agent.md` with read/search/proof execution and read-only native queries only. It has no edit, commit, pick, start, finish, reject, release, recovery, request mutation, or approval tools; `deny-writes.py` guards edit APIs and mandatory tracked-state evidence rejects proof-command writes or later-cleaned authored changes.
- Updated `w-orchestration` to dispatch exactly one successful accept start result, preserve execution identity, and map acceptor-owned fields unchanged to `finish_accept`, `reject_accept`, or `release_job`. The orchestrator does not execute proof, classify findings, plan correction, assemble evidence, alter replacements, or supplement dispositions.
- Added the acceptor delegate and public rejection tool to `orchestrator.agent.md`; updated WIRING role, required-skill, delegation, and hard-control rows.
- AC-1: workflow defines complete exact authority/receipt/proof rehydration, replacements, tracked-state evidence, and all three exhaustive dispositions.
- AC-2: frontmatter plus workflow enforce no edit/lifecycle surface, hard edit guard, checkout/scratch proof, before/after tracked diff, and no approval of authored changes.
- AC-3: orchestration explicitly forwards each success/rejection field unchanged and releases blocked work with unchanged identity; it processes one started job before replanning and owns none of the acceptance judgment.
- Validation: all 18 agents pass `validate_agents.py`; all skills pass `validate_skills.py`; explicit lint over five owned files passed; 37 relevant ecosystem/write-guard tests passed; executable YAML/text inspection proved forbidden-tool absence, hook attachment, delegate/tool reachability, exact mapping language, and WIRING rows. The full live-registry ecosystem assertion remains independently broken by pre-existing `collector.agent.md` declarations for removed task tools and was excluded without changing that unrelated role. Builder challenger decision: pass.

### Required Follow-up
None.
