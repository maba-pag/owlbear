---
id: 2048
title: 'P7-02: Expose the frontier planner and independent plan reviewer'
status: archived
priority: high
created: 2026-07-25T15:09:33.441773+02:00
updated: 2026-07-25T15:25:20.533152+02:00
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
archival_reason: completed
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

[[2026-07-25T15:24:40+02:00]]
## Verifier Notes

### Tested Commit
`c311d5dec5570627658f1d55d88066fd3c479c0c`

### Intent And Scope
Verified the native planner/reviewer declarations, orchestrator planner dispatch edge, structured planner-result handoff, existing ND3 enforcement registration, and derived WIRING update. No engine/MCP semantics, proof scenarios, setup/seed files, downstream delivery roles, or Specification authority changed.

### Commit Integrity
`git diff --quiet c311d5dec5570627658f1d55d88066fd3c479c0c -- <seven product paths>` passed. The builder commit contains exactly those seven product paths plus the #2048 task record.

### Commands And Observations
- Affected agent validator - pass.
- Affected/direct skill validator - pass.
- Existing ecosystem and write-guard regressions excluding the documented unrelated collector live-registry mismatch - 57 passed in 0.45s.
- Public `FinishPlanParams` and `finish_plan` tool boundary inspected: planner-owned fields exactly match `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, `impact_closure`, `node_plan`, `build_job_ids`, and `accept_job_id`; orchestration supplies native dispatch identity and `finished_at`.
- Unfiltered focused suite has one pre-existing failure from legacy task tools on `collector.agent.md`; no planner declaration adds an unavailable native tool.

### AC-to-Evidence Map
- AC-1 PASS: Planner requires `w-frontier-planning`, accepts only serialized engine-started context, has bounded read/query/request capabilities, delegates only planner-challenger and Explore, cannot finish or edit authority, and exposes the exact workflow disposition interface.
- AC-2 PASS: Planner challenger is DMI-false ND3, exposes only read/search tools, enforces `deny-writes.py`, and requires all six source-grounded review rows without approval or lifecycle authority.
- AC-3 PASS: Orchestrator installs planner in executable frontmatter and body. Workflow forwards only the successful start result, preserves all native identity, passes planner-owned fields unchanged to public `finish_plan`, releases requests before a fresh pick, and prohibits orchestrator-authored plans or requests.
- AC-4 PASS: WIRING agrees with executable required-reading, delegation, native ownership, and hard-control declarations; validators report no drift.

### Challenger
`verifier-challenger`: pass. It found all ACs closed at the tested commit, no scope drift, and no unresolved follow-up.

### Required Follow-up
None.

[[2026-07-25T15:25:20+02:00]]
## Collector Notes

### Aggregate Intent
Leaf packet #2048 exposes the native planner and independent reviewer, installs orchestrator dispatch, and preserves public lifecycle ownership at admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

### Closure Evidence
- No descendant tasks.
- Builder implementation commit: `c311d5dec5570627658f1d55d88066fd3c479c0c`.
- Verifier evidence commit: `dd8b9da897b7029b63bc4bd8e7d24338d109b0ac`.
- Affected agent and skill validators pass.
- Existing ecosystem/write-guard regressions: 57 passed; the sole unfiltered failure is the documented unrelated collector live-registry mismatch.
- Builder and verifier challengers both passed.
- All four ACs are mapped to committed executable declarations and direct public-schema evidence.

### Archive Readiness
Complete. Downstream executable planner scenarios remain independently owned by #2049 and #2050; they do not block this leaf packet's declared outcome.
