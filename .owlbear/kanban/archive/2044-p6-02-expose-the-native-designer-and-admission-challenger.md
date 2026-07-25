---
id: 2044
title: 'P6-02: Expose the native designer and admission challenger'
status: archived
priority: high
created: 2026-07-25T14:28:55.328794+02:00
updated: 2026-07-25T14:44:05.239644+02:00
tags:
  - phase-6
  - scope:agent
  - designer
  - challenger
  - prompt
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-002
  - interface:IF-006
parent: 1982
depends_on:
  - 2043
ac:
  - 'AC-1: The `designer` agent requires `w-design-session`, can ask one user question,
    edit current change authority, inspect source, use `list_changes | show_change
    | validate_change | admit_change`, and delegate only declared read-only specialists
    including `designer-challenger`; validators and frontmatter/body audit verify
    the runtime contract.'
  - 'AC-2: The `designer-challenger` agent is read-only and returns one source-grounded
    `{disposition, evidence}` entry for each declared requirement, workflow, interface,
    migration, risk, proof, and node using only `pass | warning | error`; its contract
    forbids admission approval and tracked writes.'
  - 'AC-3: Invoking `/ideate` enters discovery mode and invoking `/design` enters
    or resumes direct design mode through the same `designer` agent and `w-design-session`
    authority; prompt and wiring inspection proves both entries share one change identity
    and neither routes to an OpenSpec handoff.'
  - 'AC-4: `share/WIRING.md` and executable frontmatter agree on designer required
    reading, designer-to-challenger delegation, prompt entries, tools, and read-only
    enforcement; agent and skill validators report no loading, delegation, or tool
    drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-002`. Resolve normative behavior from `DN-005`, `IF-006`, `MOD-003`, `MIG-003`, and `PROOF-004`; this record is not specification authority.

## Outcome
Expose one native designer role, one read-only admission challenger, and shared `/ideate` and `/design` entries over the designer workflow.

## Envelope
In: designer and challenger agents, prompt entries, exact native tool grants, direct loading and delegation declarations, and `share/WIRING.md`.

Out: setup or seed propagation, OpenSpec deletion, planner or builder roles, runtime changes, and product implementation.

Proof guidance: run ecosystem validators and derive the prompt, agent, skill, delegate, tool, and hook graph from executable declarations.

[[2026-07-25T14:42:26+02:00]]
## Builder Notes
Exposed the native Specification surface with `designer`, hard-read-only `designer-challenger`, shared `/ideate` and `/design` prompt entries, and synchronized `share/WIRING.md`. No setup, seed, runtime, OpenSpec deletion, planner, builder, or product implementation surface changed.

### AC Evidence
- AC-1: `designer.agent.md` requires `w-design-session`; grants `askQuestions`, source reads/search, authority edit tools, and exact native `list_changes | show_change | validate_change | admit_change`; delegates only `designer-challenger` and built-in read-only Explore; role rules constrain writes to the selected Specification authority, focused research, and scratch.
- AC-2: `designer-challenger.agent.md` exposes only read/search/web tools plus `deny-writes.py`, has no admission or edit capability, and requires exactly one source-grounded `{disposition, evidence}` for every declared requirement, workflow, interface, migration, risk, proof, and node using only `pass | warning | error`, without overall approval.
- AC-3: Both prompts select `agent: designer`; `/ideate` enters discovery and `/design` enters direct/resume mode over `w-design-session`, one native identity, and no OpenSpec handoff.
- AC-4: `share/WIRING.md` records the roles, required skills, both prompt entries, delegation, Explore caller, and deny-write hook consistently with executable declarations.

### Validation
- `uv run python .owlbear/scripts/validate_agents.py` — pass, all 14 agent files conform.
- `uv run python .owlbear/scripts/validate_skills.py` — pass.
- `uv run pytest -q tests/test_agent_ecosystem_validation.py -k 'not declared_owlbear_mcp_tools_exist_in_live_registries' tests/test_write_guard_hooks.py tests/test_deny_non_doc_writes.py` — 57 passed.
- `git diff --check` for all five product artifacts — pass.
- Editor diagnostics — none.
- Full live-registry regression remains pre-existing failure on `collector.agent.md` generic task tools removed by DN-009; the four designer tools are present in the shipped native registry.
- `builder-challenger` — pass; no findings.

[[2026-07-25T14:43:48+02:00]]
## Verify Notes
Verified committed builder revision `c56e86ce843fd69a365cafe37ede3dc294feeaa4` against DN-005, IF-006, MOD-003, MIG-003, and the executable ecosystem contracts.

### AC Evidence
- AC-1: Committed `designer` requires `w-design-session`, has the user-question, source inspection, authority edit, and exact four native change tools, and aligns its frontmatter/body delegation to `designer-challenger` plus Explore with a narrow current-Specification write boundary.
- AC-2: Committed `designer-challenger` has no mutation or admission tools, uses the hard deny-write hook, requires complete typed per-entity challenge evidence, and explicitly cannot approve admission.
- AC-3: Both committed prompts select `designer` and `w-design-session` in discovery/direct modes over one native session; neither contains an OpenSpec command or handoff.
- AC-4: Committed `share/WIRING.md` agrees on roles, prompt entries, required loading, delegation, and read-only hook.

### Proof
- `git show --check c56e86ce843fd69a365cafe37ede3dc294feeaa4` — pass.
- Agent validator — all 14 agents conform.
- Skill validator — pass.
- Applicable ecosystem and write-guard regressions — 57 passed.
- Editor diagnostics — none for all five artifacts.
- Known collector generic-tool live-registry mismatch is unrelated existing migration state outside this packet.
- `verifier-challenger` — pass; no follow-up.

[[2026-07-25T14:44:05+02:00]]
## Collect Notes
Archived after confirming committed builder revision `c56e86ce843fd69a365cafe37ede3dc294feeaa4`, verifier record `44f527cbc6844262d17d14764d2bb18175cf9c8e`, complete AC mappings, passing agent/skill validators, 57 applicable ecosystem and hard-guard regressions, clean diagnostics, and both mandatory challenger passes. The unrelated collector generic-tool registry mismatch remains outside this packet.
