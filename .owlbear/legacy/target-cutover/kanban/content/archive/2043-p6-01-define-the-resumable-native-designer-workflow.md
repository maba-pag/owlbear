---
id: 2043
title: 'P6-01: Define the resumable native designer workflow'
status: archived
priority: high
created: 2026-07-25T14:28:48.796665+02:00
updated: 2026-07-25T14:36:54.567026+02:00
tags:
  - phase-6
  - scope:agent
  - designer
  - workflow
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-001
  - interface:IF-006
parent: 1982
depends_on: []
ac:
  - 'AC-1: Given `/ideate` rough input or `/design` with a change identity, `w-design-session`
    selects or creates one native change session, reads its existing intent, design,
    decisions, and delivery authority before writing, and preserves confirmed authority
    across resume; artifact inspection verifies both entry paths and resume ordering.'
  - 'AC-2: Given one unresolved material product or architecture choice, the workflow
    asks one `askQuestions` decision containing status quo, options, tradeoffs, risks,
    recommendation, and confidence, while repository-answerable facts route to read-only
    evidence gathering; workflow inspection verifies the decision contract.'
  - 'AC-3: Given confirmed scope, the workflow preserves Product Promise, accepted
    exclusions, canonical evidence states, qualified memory use, and adaptive architecture
    review while producing complete modular delivery authority; inspection maps `REQ-001`
    and `KEEP-001 | KEEP-002 | KEEP-003 | KEEP-008 | KEEP-009` to named stages and
    outputs.'
  - 'AC-4: Given unresolved material authority, non-pass challenge, failing baseline,
    failed validation, or absent approval, the workflow keeps the revision draft and
    forbids `admit_change`; given complete pass evidence, it invokes `validate_change`
    before `admit_change` with the current digest and records returned receipt, generation,
    and job identities.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-001`. Resolve normative behavior from `DN-005`, `IF-006`, `REQ-001`, `KEEP-001`, `KEEP-002`, `KEEP-003`, `KEEP-008`, `KEEP-009`, and `PROOF-004`; this record is not specification authority.

## Outcome
Define one `w-design-session` workflow for native change selection or creation, durable authority updates, one-question decisions, specialist evidence, validation, challenge, baseline, approval, admission, and interruption resume.

## Envelope
In: the workflow skill and its direct loading contract.

Out: agent and prompt wiring, runtime code, setup or seed changes, OpenSpec deletion, frontier planning, and product implementation.

Proof guidance: inspect the assembled workflow against canonical admission models and public change-tool declarations; no model-response substitute proves this packet.

[[2026-07-25T14:35:16+02:00]]
## Builder Notes
Implemented the canonical native Specification workflow in `share/skills/w-design-session/SKILL.md`; no agent, prompt, runtime, setup, seed, or durable-test surface changed.

### AC Evidence
- AC-1: Steps 1-2 route `/ideate` and `/design` to one `change_id`, require `show_change` plus all four semantic authority parts before mutation, preserve confirmed authority, and resume at the earliest unresolved gate.
- AC-2: Steps 4-5 investigate repository facts through read-only evidence and permit exactly one `askQuestions` material decision with status quo, options, tradeoffs, risks, recommendation, and confidence before stopping.
- AC-3: Steps 3-7 preserve Product Promise and accepted exclusions, canonical evidence states, corroborated qualified memory, adaptive architecture review, and complete modular obligations/contracts/nodes authority.
- AC-4: Steps 8-9 require digest-bound challenge, baselines, structured evidence, validation, explicit approval, and a second successful validation before identical-evidence `admit_change`; every failed or stale gate keeps the draft and creates no jobs, while success records receipt, generation, and plan-job identities.

### Validation
- `uv run python .owlbear/scripts/validate_skills.py` — pass.
- `git diff --check -- share/skills/w-design-session/SKILL.md` — pass.
- Editor diagnostics — none.
- `uv run pytest -q tests/test_agent_ecosystem_validation.py` — 7 passed; one unrelated live-registry failure because existing `collector.agent.md` declares generic task tools removed by archived DN-009. No failure references the new skill.
- `builder-challenger` — pass; no findings.

[[2026-07-25T14:36:36+02:00]]
## Verify Notes
Verified builder revision `dd328c058f9210a533582ec78306a1c08842d1a9` independently against admitted DN-005, IF-006, PROOF-004, REQ-001, and KEEP-001/002/003/008/009.

### AC Evidence
- AC-1: Steps 1-2 share one native `change_id`, select or create from both entries, require `show_change` and all semantic authority reads before mutation, preserve confirmed authority, and resume at the earliest unresolved gate.
- AC-2: Steps 4-5 route repository facts to read-only evidence and permit exactly one structured `askQuestions` material choice before stopping.
- AC-3: Steps 3-7 explicitly own the Product Promise and accepted exclusions, four canonical evidence states, corroborated qualified memory, adaptive architecture, and complete modular delivery authority.
- AC-4: Steps 8-9 fail closed on challenge, baseline, validation, approval, or digest defects; they validate immediately before identical-evidence `admit_change` and report persisted receipt, generation, and plan-job identities.

### Proof
- `git show --check dd328c058f9210a533582ec78306a1c08842d1a9` — pass.
- `uv run python .owlbear/scripts/validate_skills.py` — pass.
- `uv run pytest -q tests/test_agent_ecosystem_validation.py -k 'not declared_owlbear_mcp_tools_exist_in_live_registries'` — 7 passed.
- Editor diagnostics — none.
- Full ecosystem live-registry check remains blocked by pre-existing generic tool declarations in `collector.agent.md`; this does not touch or exercise the new skill and belongs to later admitted agent migration work.
- `verifier-challenger` — pass; documentation-only slice has sufficient evidence and no current follow-up.

[[2026-07-25T14:36:54+02:00]]
## Collect Notes
Archived the leaf after confirming complete Builder and Verify Notes, committed implementation revision `dd328c058f9210a533582ec78306a1c08842d1a9`, committed verification record `6292cae4faf3950117d3980d2833a9ed1acf981f`, all four AC mappings, passing skill validation, seven applicable ecosystem regressions, clean diagnostics, and both mandatory challenger passes. The known full-suite registry mismatch is unrelated existing agent migration work and does not invalidate the isolated workflow authority.
