---
id: 2048
title: 'P7-02: Expose the frontier planner and independent plan reviewer'
status: verify
priority: high
created: 2026-07-25T15:09:33.441773+02:00
updated: 2026-07-25T15:23:09.582728+02:00
tags:
  - phase-7
  - scope:agent
  - planner
  - challenger
  - orchestrator
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-002
  - interface:IF-007
parent: 1983
depends_on:
  - 2047
ac:
  - 'AC-1: `planner.agent.md` requires `w-frontier-planning`, receives only the orchestrator-supplied
    started job, uses read-only repository plus native query/request tools, delegates
    only declared read-only specialists, cannot call `finish_plan` or edit admitted
    authority, and returns the exact structured workflow disposition; agent validation
    and frontmatter/body audit verify the runtime contract.'
  - 'AC-2: `planner-challenger.agent.md` is hard read-only and returns one source-grounded
    disposition/evidence row for packet completeness, admitted references, impact
    closure, dependency order, proof boundary, and material expansion, with no approval
    or lifecycle tools; hook and declaration audit verify the restriction.'
  - 'AC-3: `orchestrator.agent.md` installs planner in the subagent allowlist and
    `w-orchestration` passes the engine-owned start context to planner, maps planner
    Success fields unchanged into public `finish_plan`, maps a planner-created request
    disposition to `release_job` followed by a fresh pick, and never constructs node
    plans itself; assembled declaration inspection verifies the handoff.'
  - 'AC-4: `share/WIRING.md` agrees with executable declarations on planner skill
    loading, planner-to-challenger delegation, orchestrator-to-planner dispatch, native
    tools, and hard read-only enforcement; ecosystem validators verify no drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-002`. Resolve normative behavior from `DN-006`, `IF-007`, `MOD-003`, `RISK-007`, `RISK-011`, and `PROOF-005`; this record is not specification authority.

## Outcome
Expose the native planner and hard-read-only plan reviewer, and complete the orchestrator handoff from engine-owned start context to structured planner result and public lifecycle completion.

## Envelope
In: planner and reviewer agents, orchestrator allowlist, `w-orchestration` native planner handling, exact existing native tools, and `share/WIRING.md`.

Out: engine or MCP contracts, planner proof scenarios, setup/seed propagation, builder/acceptor/auditor roles, and Specification edits.

Proof guidance: derive role loading, delegation, tools, structured result routing, request release, and write denial from executable declarations; validators must agree with WIRING.

[[2026-07-25T15:23:09+02:00]]
## Builder Notes

### Change Envelope
Added the native planner and independent plan reviewer declarations, installed planner in the orchestrator allowlist, defined exact planner-disposition routing in `w-orchestration`, registered the depth-three challenger in existing structural enforcement, and synchronized `share/WIRING.md`. No engine, MCP, proof-scenario, setup/seed, builder/acceptor/auditor, or Specification changes.

### Files Changed
- `share/agents/planner.agent.md`
- `share/agents/planner-challenger.agent.md`
- `share/agents/orchestrator.agent.md`
- `share/skills/w-orchestration/SKILL.md`
- `share/skills/h-agent-structure/SKILL.md`
- `.owlbear/scripts/validate_agents.py`
- `share/WIRING.md`

### Change Module Map Deviations
None. The structural handbook and validator are the established direct owners of ND3 registration required by the new planner-to-reviewer nesting edge.

### Proof Selected
Executable frontmatter/body validation, exact parsed declaration assertions, public `FinishPlanParams` comparison, existing ecosystem/write-guard regressions, focused Ruff, and repository pre-commit hooks. Durable-test delta is zero because existing maintained validators and controls already protect this declarative behavior.

### Commands Run
- `uv run python .owlbear/scripts/validate_agents.py share/agents/planner.agent.md share/agents/planner-challenger.agent.md share/agents/orchestrator.agent.md` - pass.
- `uv run python .owlbear/scripts/validate_skills.py share/skills/h-agent-structure share/skills/w-orchestration share/skills/w-frontier-planning` - pass.
- Parsed YAML/text #2048 declaration audit - PASS.
- `uv run ruff check .owlbear/scripts/validate_agents.py` - pass.
- `uv run pre-commit run --files <task-owned paths>` - pass after expected EOF normalization.
- `uv run pytest -q tests/test_agent_ecosystem_validation.py -k 'not declared_owlbear_mcp_tools_exist_in_live_registries' tests/test_write_guard_hooks.py tests/test_deny_non_doc_writes.py` - 57 passed.
- The unfiltered focused suite produced the same 57 passes plus one known unrelated live-registry failure from legacy task tools declared by `collector.agent.md`; no planner tool was missing.
- `git -C ../owlbear diff --exit-code -- share/skills/h-agent-structure/SKILL.md` - pass; sibling active install untouched.

### AC-to-Evidence Map
- AC-1: Planner frontmatter requires `w-frontier-planning`, grants only read/search and native query/request capabilities, delegates exactly planner-challenger and Explore, excludes edit and lifecycle completion tools, and its body accepts only orchestrator-started context and returns the four exact workflow dispositions. Agent validator and parsed declaration audit pass.
- AC-2: Reviewer frontmatter exposes only read/search tools, attaches `deny-writes.py`, has no agents or lifecycle tools, and is registered as DMI-false ND3. Its output contract has all six required source-grounded rows. Agent validator and write-guard regressions pass.
- AC-3: Orchestrator frontmatter/body installs planner. `w-orchestration` forwards only the complete successful `start_job` result, passes all eight planner-owned fields unchanged to public `finish_plan`, releases `RequestCreated` before a fresh `pick_jobs`, and prohibits constructing requests or node plans. Direct comparison with public `FinishPlanParams` and declaration audit pass.
- AC-4: WIRING records both roles, required skills, both delegation edges, native ownership, and reviewer hard-read-only enforcement. Ecosystem and skill validators pass.

### Challenger
`builder-challenger`: pass. It independently reviewed all seven files and reran agent validation, skill validation, and 57 focused ecosystem/write-guard tests.

### Follow-up Risks
None within this packet. Initial-frontier and reconciliation executable scenarios remain owned by downstream #2049 and #2050.
