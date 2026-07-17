---
id: 1957
title: 'P1-21: Document memory lifecycle authority and recovery'
status: collect
priority: low
created: 2026-07-17T04:54:19.520889+02:00
updated: 2026-07-17T05:53:17.076461+02:00
tags:
  - phase-1
  - scope:docs
  - docs
  - memory
parent: 1958
depends_on:
  - 1952
  - 1953
  - 1954
ac:
  - 'AC-1: The maintained memory documentation states that exceptional edits preserve
    state, resolve returns contested, disputed, or stale entries to approved, first
    contest stores reporting-task provenance, dispute and resolve clear that provenance,
    confidence edits recompute score, and stale resolve resets only didnt_use_count.'
  - 'AC-2: The maintained MCP memory documentation states that curation of contested,
    disputed, and stale entries is rejected, no MCP resolve tool exists, and Cockpit
    is the human editing and resolution surface for those states.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Canonical memory documentation matches the shipped exceptional-edit, human-resolution, provenance, stale-recovery, and MCP authority contracts.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`

## Scope
- In scope: maintained memory core and MCP memory README lifecycle/tool documentation.
- Out of scope: implementation, frontend usage prose, unrelated documentation, and an MCP resolve operation.

Proof guidance: no executable proof expected; inspect the maintained artifacts against the implemented domain, HTTP, and MCP public surfaces and the OpenSpec capability.

[[2026-07-17T05:49:11+02:00]]
## Builder Notes

Change envelope: documentation-only updates to the maintained memory core and MCP memory READMEs for the lifecycle and authority contracts in AC-1 and AC-2.

Files changed:
- `serve/memory/README.md`
- `serve/mcp-memory/README.md`

Change Module Map deviations: none. The edits stay within the two mapped documentation artifacts.

Proof selected: maintained-artifact inspection against `serve/memory/src/owlbear_memory/engine.py` and `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`; no executable proof added because the task explicitly expects documentation inspection only.

Durable-test justification: no tests added; this change does not alter executable behavior.

Commands/checks run:
- `git diff --check -- serve/memory/README.md serve/mcp-memory/README.md` passed.
- Targeted searches confirmed the documented AC-1 lifecycle terms and AC-2 MCP authority terms.

Builder-challenger result: PASS. Confirmed stale resolve semantics, MCP absence of resolve, Cockpit human authority, and clean diff validation.

Follow-up risks: none identified.

[[2026-07-17T05:53:17+02:00]]
## Verify Notes

Verdict: PASS

Evidence reviewed:
- Compared `serve/memory/README.md` and `serve/mcp-memory/README.md` with the authoritative `openspec/changes/expose-memory-lifecycle-in-cockpit/specs/cockpit-memory-lifecycle/spec.md`.
- Checked `serve/memory/src/owlbear_memory/engine.py`: exceptional engine edits preserve state; `resolve()` moves contested, disputed, and stale entries to approved, clears `contested_by_task`, and resets only stale `didnt_use_count`; confidence edits recompute score; first factually-wrong assessment stores task provenance and a second task clears it on escalation to disputed.
- Checked `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` and `server.py`: curation rejects contested/disputed/stale entries and the registered MCP surface has no resolve tool.
- Checked `serve/cockpit/src/owlbear_cockpit/routes/memory.py`: Cockpit exposes the human resolution endpoint.

Named authorities checked:
- OpenSpec Cockpit memory lifecycle delta specification.
- Memory engine, MCP public tool registry, and Cockpit memory route.

Change Module Map deviations:
- None. Documentation remained in the two mapped maintained package READMEs.

Normal-path boundary exercised:
- Focused engine lifecycle tests exercised the documented transition and recovery behavior; MCP authority was inspected at its public registration boundary, and Cockpit resolution at its public route boundary.
- Replacements used below that boundary: none.

Checks run:
- `uv run pytest tests/test_memory_voting_scoring.py tests/test_confirmation_cycle.py -q` passed: 66 tests.
- `git diff --check -- serve/memory/README.md serve/mcp-memory/README.md` passed.
- README parent links were enumerated and resolve to the root README.

Findings and patch:
- Found one stale core README row claiming exceptional engine edits raise `TransitionError`. Patched it locally to state the implemented behavior: fields update while the exceptional state is preserved. This is necessary for AC-1 and does not alter MCP curation, which remains rejected for those states.

Verifier-challenger result:
- PASS. The challenge confirmed every AC is covered, proof is sufficient for documentation-only scope, and the local correction has no scope drift.

Final route: collect.
