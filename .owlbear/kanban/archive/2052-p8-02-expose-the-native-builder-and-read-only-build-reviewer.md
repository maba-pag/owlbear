---
id: 2052
title: 'P8-02: Expose the native builder and read-only build reviewer'
status: archived
priority: high
created: 2026-07-25T16:14:20.905544+02:00
updated: 2026-07-25T16:37:36.014165+02:00
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
archival_reason: completed
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

[[2026-07-25T16:36:59+02:00]]
## Verify Notes

Independently verified builder commit `7d96d6bd1a46c86fd3f08fb44ca90007829b96d7` against current DN-007 authority, `w-packet-building`, public lifecycle signatures, and ecosystem structure. No patch was required and no prior Verify Notes or repeated failure key exists.

### Authority And Module Map
- Confirmed the dual-mode builder preserves task-ID bootstrap while a serialized successful build start selects only native packet workflow.
- Confirmed the reviewer is a distinct hard-read-only ND3 role and the orchestrator remains the sole lifecycle mutation owner.
- Confirmed all changed files match the shaped role, workflow, ND3, and WIRING owners; runtime/MCP behavior and proof scenarios remain untouched for later packets.

### AC Evidence
- AC-1: Builder requires `w-packet-building`, delegates to `build-reviewer`, exposes all current native read projections, and grants no native pick, start, finish, release, or recovery operation. Its native output is one exact workflow disposition.
- AC-2: Reviewer uses a distinct model, DMI false, read-only tools, and `deny-writes.py`; six fixed rows cover authority/packet, diff/paths, proof, commit context, scope, and canonical findings. Missing context is malformed and no repair capability exists.
- AC-3: Orchestration sends only the successful start result. Live `finish_build` confirms the exact five builder-owned success fields. All three non-success dispositions release unchanged identity, halt/report, and forbid receipt or corrective work; malformed output follows crash recovery.
- AC-4: Builder delegation, WIRING runtime/inverse/delegation/hook maps, the structural handbook, and validator ND3 registry agree on `build-reviewer`.

### Independent Proof
- `git show --check --stat --oneline 7d96d6bd1a46c86fd3f08fb44ca90007829b96d7`: passed.
- `validate_agents.py`: all 17 agents passed; `validate_skills.py`: passed.
- Ecosystem, write-guard, and non-doc-write checks excluding the unrelated broad registry assertion: 57 passed.
- Ownership-aware live-schema/declaration probe: exact finish/release signatures, delegation, model split, hard hook, lifecycle-tool absence, all four dispositions, and WIRING/ND3 synchronization passed.
- Path-scoped pre-commit: passed.
- Full broad set's only failure remains pre-existing dirty `collector.agent.md` legacy tool-name corruption. The 11 newly added native builder reads all resolve in the live dev registry; legacy task tools intentionally remain for the sibling bootstrap carrier.
- `verifier-challenger`: `pass`; no scope drift, unresolved follow-up, or evidence gap.

A first ad hoc probe incorrectly expected `w-orchestration` to duplicate the reviewer identity; labeled diagnosis showed all contract facts passed and only that Rule-of-Two premise was false. The corrected ownership-aware probe passed without code changes. Replacements: none.

[[2026-07-25T16:37:36+02:00]]
## Collect Notes

Classification: leaf. #2052 has no children or aggregate intent.

Latest Verify Notes record PASS at builder commit `7d96d6bd1a46c86fd3f08fb44ca90007829b96d7`, with verifier lifecycle commit `c79fc21fcae00394a7402b1392b29aa6302693d7`. Tied proof includes exact commit integrity, both ecosystem validators, 57 structural/write-guard tests, live finish/release signature comparison, declaration and hard-control assertions, WIRING/ND3 synchronization, and path-scoped pre-commit. The broad suite's only excluded failure is the unrelated pre-existing collector declaration; the modified builder's newly added native tools were verified live.

No child/dependency gate applies, no pending or resolved structured request exists, and all seven ecosystem deliverables are committed and clean. No current follow-up or residual decision remains. Archive as completed.
