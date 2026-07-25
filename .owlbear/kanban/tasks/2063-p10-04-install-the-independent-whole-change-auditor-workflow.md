---
id: 2063
title: 'P10-04: Install the independent whole-change auditor workflow'
status: verify
priority: high
created: 2026-07-25T19:53:37.879721+02:00
updated: 2026-07-25T20:50:33.307752+02:00
tags:
  - phase-10
  - scope:agent-config
  - auditor
  - orchestrator
  - read-only
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-004
  - interface:IF-014
parent: 1986
depends_on:
  - 2062
ac:
  - 'AC-1: The shipped auditor role accepts only an orchestrator-started audit result
    with engine checkout, has read, query, and proof capabilities but no lifecycle
    or tracked-write capability, uses the terminal read-only hook, and loads the whole-change
    audit workflow; validators and wiring inspection show declaration and derived
    map agreement.'
  - 'AC-2: The workflow rehydrates matching change, job, checkout, accepted-node receipt
    set, Product Promise, accepted decisions, migrations and removals, admitted workflows,
    request state, IF-014, PROOF-008, allowed lower replacements, and before and after
    Git state; stale, incomplete, contradictory, unsafe, or unavailable authority
    returns `AuditBlocked` without mutation.'
  - 'AC-3: The workflow defines `AuditorSuccess` fields mapped unchanged to `finish_audit`
    and `AuditRejected` fields mapped unchanged to `reject_audit`; cross-node integration
    and implemented migration absence use `implementation-defect` with `whole-change-integration`,
    admitted authority or proof omission uses `planning-omission` with `admitted-design-authority`,
    and a tracked edit cannot pass.'
  - 'AC-4: `w-orchestration` dispatches only the engine-selected auditor with the
    complete start and checkout result and maps `AuditorSuccess` to `finish_audit`,
    `AuditRejected` to `reject_audit`, and `AuditBlocked` to unchanged-identity `release_job`
    and halt; malformed output uses crash recovery, and the orchestrator performs
    no proof, classification, evidence assembly, or correction.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-004`. Resolve behavior from REQ-007, WF-005, IF-014, NEG-003, NEG-009, RISK-008, RISK-009, PROOF-008, and the shipped acceptor precedent.

## Outcome
Install the hard-read-only auditor role, whole-change audit workflow, and exact orchestrator disposition routing.

## Envelope
In: engine-started audit identity and checkout, native read queries, admitted whole-change authority, success/rejection/blocked dispositions, orchestration mapping, write guard, and derived wiring.

Out: runtime semantics, Cockpit, setup, cutover, and complete-system proof.

Proof guidance: run agent and skill validators plus ecosystem and write-guard regressions; inspect exact orchestration mappings.

[[2026-07-25T20:50:33+02:00]]
## Builder Notes

Implemented the independent whole-change auditor and adopted/repaired the interrupted task-local candidate work.

### Changed Files
- `share/agents/auditor.agent.md`: proof-capable, lifecycle-free auditor with native read queries and terminal read-only hook.
- `share/agents/orchestrator.agent.md`: executable auditor delegation and `reject_audit` grant.
- `share/skills/w-whole-change-audit/SKILL.md`: whole-change authority rehydration, PROOF-008 execution, exact dispositions, and corrective classification matrix.
- `share/skills/w-orchestration/SKILL.md`: exact auditor dispatch and success/rejection/blocked lifecycle routing.
- `share/WIRING.md`: derived agent, skill, delegation, and hard-control maps.

### AC Evidence
- AC-1: Auditor accepts only the serialized engine-started audit result and checkout; its allowlist contains read/query/proof tools, no edit or lifecycle tools, and the terminal read-only hook. Agent/skill validators pass and WIRING matches executable declarations.
- AC-2: Workflow explicitly rehydrates matching change/digest, job and active identity, engine checkout, Product Promise, accepted decisions, migrations/removals, admitted workflows, current accepted-node receipts, native request state, IF-014, PROOF-008, allowed lower replacements, and before/after Git state. Unsafe or missing authority returns `AuditBlocked`.
- AC-3: `AuditorSuccess` and `AuditRejected` fields map unchanged to public MCP signatures. Cross-node integration, implemented migration/removal absence, stale acceptance, and tracked auditor edits use `implementation-defect` with `whole-change-integration`; admitted authority/proof omission uses `planning-omission` with `admitted-design-authority`.
- AC-4: Orchestrator dispatches only its engine-selected auditor with complete start/checkout context; maps success to `finish_audit`, rejection to `reject_audit`, and blocked to unchanged-identity `release_job`; malformed output follows recovery and orchestration cannot perform audit proof or classification.

### Proof
- `uv run python .owlbear/scripts/validate_agents.py`: PASS, all 19 agents.
- `uv run python .owlbear/scripts/validate_skills.py`: PASS.
- Focused ecosystem, write-guard, non-doc guard, and MCP interaction suite excluding one known unrelated registry assertion: 80 passed.
- Live MCP registry probe: every auditor query tool and the new orchestrator `reject_audit` grant resolve.
- Public `finish_audit`, `reject_audit`, and `release_job` signatures inspected and match workflow mappings.
- Editor diagnostics: none on all five changed files.
- Builder challenger: pass, no blocking defects.

The unexcluded ecosystem run had 46 passes and one pre-existing unrelated collector legacy-tool registry mismatch; no broad registry migration was included in this task.
