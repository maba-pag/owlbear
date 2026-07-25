---
id: 2052
title: 'P8-02: Expose the native builder and read-only build reviewer'
status: verify
priority: high
created: 2026-07-25T16:14:20.905544+02:00
updated: 2026-07-25T16:34:14.676101+02:00
tags:
  - phase-8
  - scope:agent
  - builder
  - reviewer
  - orchestrator
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-002
  - interface:IF-008
parent: 1984
depends_on:
  - 2051
ac:
  - 'AC-1: In explicit native mode, `builder.agent.md` requires `w-packet-building`,
    accepts only orchestrator-supplied started build context, exposes existing edit,
    proof, commit, and native read tools, delegates to `build-reviewer`, cannot call
    native finish, release, start, or pick operations, and returns one workflow disposition;
    declaration audit verifies the contract while bootstrap task mode remains available.'
  - 'AC-2: `build-reviewer.agent.md` is hard read-only with `deny-writes.py`, a distinct
    model, no lifecycle or edit tools, and source-grounded rows for authority and
    packet obligations, diff and changed paths, proof, commit context, scope, and
    typed findings; hook and declaration audit verifies omitted context is malformed
    and the reviewer cannot repair its findings.'
  - 'AC-3: `w-orchestration` sends only the successful start result to builder, forwards
    `BuilderSuccess` fields unchanged to public `finish_build`, and maps `SpecificationReentry`,
    `CommitFailed`, or `BuildBlocked` to identity-preserving `release_job` plus halt
    and report; artifact inspection verifies no failed disposition issues a receipt
    or creates corrective work.'
  - 'AC-4: `share/WIRING.md`, `h-agent-structure`, and `validate_agents.py` agree
    with executable builder and reviewer loading, delegation, native tools, result
    routing, ND3 metadata, and write denial; ecosystem validators verify no drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-002`. Resolve normative behavior from `DN-007`, `IF-008`, `NEG-006`, `NEG-009`, `RISK-008`, and `PROOF-006`; this record is not specification authority.

## Outcome
Expose the native outcome builder and hard-read-only build reviewer, and complete the orchestrator handoff from engine-owned build start context to finish or fail-closed release.

## Envelope
In: builder and reviewer declarations, orchestrator allowlist and workflow routing, existing native tools, ND3 enforcement, and WIRING synchronization.

Out: runtime or MCP semantics, proof scenarios, acceptor or auditor roles, setup or seed propagation, and removal of legacy task mode during bootstrap.

Proof guidance: validate executable declarations, reviewer write denial, structured result routing, public tool schemas, and WIRING agreement.

[[2026-07-25T16:34:14+02:00]]
## Builder Notes

Implemented the native builder/reviewer/orchestrator role graph while preserving the current task-ID bootstrap mode.

### Change Envelope And Files
- `share/agents/builder.agent.md`: dual-mode input contract, `w-packet-building` required reading, native read-only control-plane tools, `build-reviewer` delegation, structured native output, and explicit absence of native lifecycle ownership.
- `share/agents/build-reviewer.agent.md`: new Claude Sonnet 5 ND3 hard-read-only reviewer with `deny-writes.py`, fixed authority/diff/proof/commit/scope rows, and canonical typed findings.
- `share/agents/orchestrator.agent.md` and `share/skills/w-orchestration/SKILL.md`: native builder dispatch and exact `BuilderSuccess` or fail-closed result routing.
- `share/skills/h-agent-structure/SKILL.md`, `.owlbear/scripts/validate_agents.py`, and `share/WIRING.md`: ND3, loading, delegation, hook, and inverse-map synchronization.

No runtime/MCP behavior, assembled proof scenario, acceptor/auditor role, setup/seed artifact, or bootstrap-task removal entered the diff.

### AC Evidence
- AC-1: A serialized successful native start result selects `w-packet-building`; a task ID retains `r-pipeline-protocol`. Builder delegates native commit review to `build-reviewer`, exposes all current native read projections, and has no `pick_jobs`, `start_job`, finish, release, or recovery tool. Native output is one workflow disposition.
- AC-2: `build-reviewer` uses a distinct model, `disable-model-invocation: false`, read-only tools, and `deny-writes.py`. Its complete mapping covers authority/packet, diff/paths, proof, commit context, scope, and findings; omitted or contradictory context is malformed, and it cannot edit, commit, delegate, or mutate lifecycle state.
- AC-3: Orchestration forwards only the complete successful start result. `BuilderSuccess` fields pass unchanged to `finish_build`; `SpecificationReentry`, `CommitFailed`, and `BuildBlocked` release the unchanged identity, halt, report, and create no receipt or corrective work. Malformed output uses crash recovery.
- AC-4: WIRING runtime/inverse/delegation/hook maps, the structural handbook, and validator ND3 registry all include `build-reviewer` and the new loading edge.

### Validation
- `validate_agents.py`: PASS, all 17 agents.
- `validate_skills.py`: passed.
- Ecosystem, write-guard, and non-doc-write tests excluding one unrelated broad registry assertion: 57 passed.
- Full 58-test set: 57 passed; the sole failure is pre-existing dirty `collector.agent.md` legacy tool-name corruption outside this task.
- Live source registry: all 11 newly added native builder read operations are registered. Legacy task tools intentionally remain for the external sibling bootstrap carrier.
- Direct structured declaration probe: passed delegation, model separation, deny hook, lifecycle-tool absence, structured routing, finish fields, and WIRING/ND3 synchronization.
- Path-scoped pre-commit: passed after final-newline normalization and identical rerun.
- VS Code diagnostics and `git diff --check`: clean.
- `builder-challenger`: `pass`; independently reran validators and the targeted suite.

Durable-test delta: zero. Existing validators and write-guard tests already own the structural and enforcement regressions.
