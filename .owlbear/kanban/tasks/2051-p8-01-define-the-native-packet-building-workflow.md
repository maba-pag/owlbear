---
id: 2051
title: 'P8-01: Define the native packet-building workflow'
status: verify
priority: high
created: 2026-07-25T16:14:11.579317+02:00
updated: 2026-07-25T16:23:40.135528+02:00
tags:
  - phase-8
  - scope:agent
  - builder
  - workflow
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-001
  - interface:IF-008
parent: 1984
depends_on: []
ac:
  - 'AC-1: Given a successful public `start_job` result for a `build` job, `w-packet-building`
    requires current change, job, node plan, plan and predecessor receipts, and repository
    state to match its change, delivery digest, target, node-plan digest, and claim
    identity before edits; artifact inspection verifies ordered rehydration and fail-closed
    stale or malformed handling.'
  - 'AC-2: Given a current packet, `w-packet-building` uses one warm session under
    the existing writer claim, implements required outputs, runs proportionate proof,
    makes one scoped commit, and constructs reviewer context with authority, packet,
    diff, changed paths, proof, and commit identity; artifact inspection maps the
    procedure to `REQ-005`, `WF-003`, `IF-008`, and `NEG-006`.'
  - 'AC-3: Given `implementation-defect`, the workflow repairs the packet, commits,
    rebuilds reviewer context, and requires a fresh pass. Given `unforeseeable-discovery`,
    `planning-omission`, or `scope-change`, it returns `SpecificationReentry`; commit
    failure returns `CommitFailed`; malformed review returns `BuildBlocked`. Artifact
    inspection verifies these branches omit finish fields.'
  - 'AC-4: Given a fresh review pass, `w-packet-building` returns `BuilderSuccess`
    with `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, and `impact_closure`,
    while forbidding builder calls to finish, release, start, or pick operations;
    declaration inspection verifies orchestrator lifecycle ownership.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-001`. Resolve normative behavior from `DN-007`, `REQ-005`, `WF-003`, `IF-008`, and `PROOF-006`; this record is not specification authority.

## Outcome
Define the one-job packet-building procedure from engine-started authority through scoped commit, mandatory warm review, and one structured disposition.

## Envelope
In: one packet-building workflow, existing native query and lifecycle schemas, scoped-commit governance, and canonical finding taxonomy.

Out: agent declarations, orchestrator wiring, runtime semantics, new MCP operations, assembled PROOF-006 scenarios, acceptor or auditor work, and setup or seed propagation.

Proof guidance: inspect the workflow against admitted authority, public native schemas, scoped commit governance, and the four canonical finding classes.

[[2026-07-25T16:23:40+02:00]]
## Builder Notes

Implemented the canonical native packet-building workflow in `share/skills/w-packet-building/SKILL.md` without changing agent declarations, orchestrator wiring, runtime/MCP behavior, proof scenarios, or WIRING.

### AC Evidence
- AC-1: Step 1 requires the successful started build pair, exact active identity, current `show_change` and `show_job` projections, current target-node plan and digest, current plan/predecessor receipts, candidate repository state, and unambiguous path custody before edits. Stale, malformed, incomplete, or contradictory evidence returns `BuildBlocked`.
- AC-2: Steps 2 through 5 fix the admitted envelope, keep one warm engine-owned writer claim, implement all packet outputs, run boundary-valid proof, create one explicit-path scoped commit, and generate mandatory reviewer context containing authority, packet, diff, changed paths, proof, commit/custody, and prior findings.
- AC-3: Step 6 exhaustively maps `implementation-defect` to local repair plus repair commit, regenerated context, and fresh pass. `unforeseeable-discovery`, `planning-omission`, and `scope-change` return `SpecificationReentry`; commit failure returns `CommitFailed`; malformed review returns `BuildBlocked`. Only success carries finish fields.
- AC-4: `BuilderSuccess` returns exactly `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, and `impact_closure`. The authority boundary and Step 8 forbid builder pick, start, finish, release, and recovery calls and leave lifecycle mapping to the orchestrator.

### Validation
- `uv run python .owlbear/scripts/validate_skills.py`: passed.
- `uv run pre-commit run --files share/skills/w-packet-building/SKILL.md`: passed after the end-of-file hook normalized the final newline and the identical command was rerun.
- `uv run pytest -q tests/test_agent_ecosystem_validation.py -k 'not declared_owlbear_mcp_tools_exist_in_live_registries'`: 7 passed.
- Full `tests/test_agent_ecosystem_validation.py`: 7 passed and 1 unrelated failure from pre-existing dirty `share/agents/collector.agent.md` newline-prefixed Kanban tool declarations; #2051 changes no agent or registry.
- VS Code diagnostics: no errors.
- `git diff --check` on the owned workflow and task record: passed.
- `builder-challenger`: `pass`; no findings.

No deviation from the shaped Change Module Map. Memory recall and all ten returned entries were assessed; the active-repository entry prevented editing the sibling consumer checkout.
