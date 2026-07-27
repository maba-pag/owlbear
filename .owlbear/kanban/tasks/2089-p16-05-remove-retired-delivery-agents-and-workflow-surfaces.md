---
id: 2089
title: 'P16-05: Remove retired delivery agents and workflow surfaces'
status: collect
priority: high
created: 2026-07-27T08:39:38.469917+02:00
updated: 2026-07-27T11:11:57.939914+02:00
tags:
  - phase-16
  - scope:agent
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T5
  - module:MOD-003
  - module:MOD-009
parent: 1989
depends_on: []
ac:
  - 'AC-1: Given the installed prompt, agent, skill, instruction, and orchestrator
    inventories, the exposed delivery roles are native design, plan, build, accept,
    audit, and graph-aware orchestration with purpose-specific job tools.'
  - 'AC-2: Given a lookup for shape, verify, collect, OpenSpec, opsx, or generic task-authority
    entry surfaces, the installed ecosystem exposes no dispatchable prompt, agent,
    skill, instruction, or tool grant for that workflow.'
  - 'AC-3: Given native builder, acceptor, auditor, and orchestrator write attempts,
    the installed hooks preserve their scoped path, tracked-write, commit-ownership,
    and read-only proof restrictions.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The installed agent ecosystem and write guards expose the native design, plan, build, accept, audit, and orchestration workflow without dispatchable shape/verify/collect or OpenSpec authority.

## Scope
In scope: MOD-003 and MOD-009 agents, prompts, skills, instructions, wiring, tool declarations, hooks, and seed hook equivalents.

Out of scope: Python/MCP/FastAPI runtime deletion, setup behavior, distribution documentation, and live-board retirement.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, REQ-017, MIG-002/MIG-003 consumer inventories, RISK-005, KEEP-007, and completed IF-006 through IF-010.

Proof guidance: validate assembled agent/prompt/skill/instruction/hook inventories and native role write-guard behavior; use artifact validation rather than durable source-string absence tests.

[[2026-07-27T11:09:27+02:00]]
## Builder Notes

Implemented the MOD-003/MOD-009 native-only ecosystem cutover.

- AC-1: exact artifact inventory now contains 13 native/neutral agents; `/ideate` and `/design` route to designer, `/orchestrate` routes to graph-aware orchestrator, and orchestration exposes only purpose-specific native pick/start/finish/reject/release/recovery tools.
- AC-2: removed shaper, verifier, collector, their task-era challengers, builder-challenger, `/shape`, OpenSpec/task-decomposition/task-repair workflows, generic task protocol/handbook, and every generic task MCP grant from retained agents. Reconciled native request, reviewer, commit, memory, test-curation, universal instruction, and wiring authorities.
- AC-3: preserved builder session/lint hooks and packet-scoped commit authority; acceptor/auditor retain hard read-only edit and terminal guards; build-reviewer remains hard read-only; orchestrator has no edit or terminal grant and only exact native lifecycle tools. Removed the shaper-only guard and matching obsolete test from dev and seed.

Proof:
- `uv run python .owlbear/scripts/validate_agents.py` -> PASS (13 agents)
- `uv run python .owlbear/scripts/validate_skills.py` -> PASS
- changed-Python Ruff check -> all checks passed
- `uv run pytest -q tests/test_agent_ecosystem_validation.py tests/test_write_guard_hooks.py tests/test_lint_changed_hook.py` -> 55 passed, 3 existing asyncio deprecation warnings
- `git diff --check` -> clean
- builder-challenger independent review -> pass; it reran validators and 55 focused tests

A broader optional run exposed one pre-existing obsolete assertion in `tests/test_deny_code_writes.py` that expects storage tests removed by #2088. It is unrelated to #2089 and is left for the later test-cleanup packet.

[[2026-07-27T11:11:57+02:00]]
## Verify Notes

PASS at exact builder commit `269b6bf9d94e34e8f18e1b9bee018ada168ca9ac`.

- AC-1: committed artifact inventory is exactly 13 native/neutral agents with native design, plan, build, accept, audit, and orchestration roles; prompt routes and purpose-specific job tools are parsed and asserted by the regression suite.
- AC-2: committed inventories contain no retired agent, `/shape` prompt, generic task authority skill, or generic task tool grant. Native delegation is orchestrator -> planner/builder/acceptor/auditor and builder -> build-reviewer; neutral Memory/Knowledge/Test roles remain.
- AC-3: builder session/lint hooks and packet commit governance remain; acceptor/auditor retain `deny-writes.py --terminal-read-only`; build-reviewer remains hard read-only; orchestrator has no edit/terminal grants and only purpose-specific lifecycle tools.

Exact-commit evidence:
- complete path set matches #2089 scope
- no post-commit drift on owned implementation paths
- agent and skill validators pass
- focused artifact/live-registry/write-guard/lint-hook proof: 55 passed, 3 existing deprecation warnings
- verifier-challenger: pass; confirmed historical briefs/research/archive references are non-dispatchable and optional obsolete storage-test failure is outside this task

No verifier patch was needed.
