---
id: 1953
title: 'P1-17: Preserve MCP exceptional-memory authority'
status: archived
priority: medium
created: 2026-07-17T04:53:51.213104+02:00
updated: 2026-07-17T05:35:19.112361+02:00
tags:
  - phase-1
  - scope:mcp-memory
  - api
  - authority
parent: 1958
depends_on:
  - 1952
ac:
  - 'AC-1: Given a contested, disputed, or stale persisted entry, invoking curate_memory
    with a mutable field rejects the mutation with ToolError and leaves the persisted
    entry unchanged.'
  - 'AC-2: Given the MCP memory server public tool inventory, no resolve-memory operation
    is registered and the existing save, list, read, recall, curate, delete, approve,
    and assess operations remain registered.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
The final agent tool boundary remains narrower than the human memory-domain capability: agents cannot rewrite or resolve exceptional entries.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirement: Human-only exceptional-state resolution

## Scope
- In scope: MCP memory curation policy and registered public tool inventory.
- Out of scope: canonical engine behavior, Cockpit routes, frontend behavior, and a new resolve tool.

## Accepted Sequencing
This task follows the permissive engine task. The temporary MCP authority expansion between those commits was explicitly accepted during shaping; this task must restore the final authority boundary before downstream Cockpit work begins.

Proof guidance: exercise the real MCP curation adapter and registered server inventory; the canonical engine remains below the boundary and must not be mocked away.

[[2026-07-17T05:33:05+02:00]]
## Builder Notes

Change envelope: restore the MCP memory adapter authority boundary for exceptional states; preserve the existing public tool inventory. Expected owners were `_update_entry()` in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` and the maintained MCP mutation proof in `tests/test_mutation_tools.py`. No server edit was needed because source inspection confirmed save, list, read, recall, curate, delete, approve, and assess are registered and no resolve operation exists.

Files changed:
- `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`
- `tests/test_mutation_tools.py`

Change Module Map deviations: none.

Implementation: `_update_entry()` now raises `ToolError` for `contested`, `disputed`, and `stale` entries before calling `MemoryEngine.edit()`. Added one parameterized real-engine regression covering all three states, asserting rejection and unchanged persisted entry.

Proof selected: focused adapter behavior plus public registry and static checks. Durable-test justification: the test protects a shared, authority-sensitive, data-preserving MCP boundary and exercises the real engine-backed adapter rather than mocks.

Commands run:
- `uv run pytest tests/test_mutation_tools.py -q -k 'curate_memory or exceptional_states'` -> `17 passed`
- `uv run pytest tests/test_assess_memories.py -q -k 'tool'` -> `12 passed`
- `uv run ruff check serve/mcp-memory/src/owlbear_mcp_memory/tools.py tests/test_mutation_tools.py` -> `All checks passed!`
- `uv run ruff format --check serve/mcp-memory/src/owlbear_mcp_memory/tools.py tests/test_mutation_tools.py` -> `2 files already formatted`

Builder-challenger result: `pass`; no concrete blockers reported.

Follow-up risk: the existing server inventory was verified by source and registry tests; no resolve-memory tool is introduced.

[[2026-07-17T05:34:32+02:00]]
## Verify Notes

Verdict: PASS

Evidence reviewed:
- Builder change envelope and proof claims for the MCP exceptional-memory authority boundary.
- Named planning authority: OpenSpec `expose-memory-lifecycle-in-cockpit`, including human-only exceptional-state resolution.
- AC-1: `_update_entry()` in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` rejects `CONTESTED`, `DISPUTED`, and `STALE` before `MemoryEngine.edit()`. The real-engine parameterized regression in `tests/test_mutation_tools.py` creates each state through `MemoryEngine`, invokes `curate_memory` with a mutable title, asserts `ToolError`, and confirms the persisted entry remains equal to its original value.
- AC-2: inspected `serve/mcp-memory/src/owlbear_mcp_memory/server.py`: the registered public inventory remains `save_memory`, `list_memories`, `read_memory`, `recall_memory`, `curate_memory`, `delete_memory`, `approve_memory`, and `assess_memories`; no resolve-memory operation is registered.

Change Module Map:
- Expected owners were `tools.py` and `tests/test_mutation_tools.py`; actual two-file diff matches with no deviations or public-interface expansion.

Normal-path boundary and replacements:
- The real MCP curation adapter was exercised with a real `MemoryEngine`; no mock or injection replaced the curation workflow or persistence boundary. The canonical engine stayed below the adapter boundary.

Checks run:
- `uv run pytest tests/test_mutation_tools.py -q -k 'curate_memory or exceptional_states'` - 17 passed.
- `uv run pytest tests/test_assess_memories.py -q -k 'tool'` - 12 passed.
- `uv run ruff check serve/mcp-memory/src/owlbear_mcp_memory/tools.py tests/test_mutation_tools.py` - all checks passed.
- `uv run ruff format --check serve/mcp-memory/src/owlbear_mcp_memory/tools.py tests/test_mutation_tools.py` - 2 files already formatted.
- `git diff --check` - clean.

Findings:
- Builder Notes named a non-existent package-local test path; the actual, task-owned regression is `tests/test_mutation_tools.py`. This is documentation-only and does not weaken proof because the actual real-engine test was inspected and run.
- No verifier patches applied.

Verifier-challenger result: pass. It found both AC directly covered, proof proportionate, and no scope drift or unresolved criteria.

Final route: PASS to collect.

[[2026-07-17T05:35:19+02:00]]
## Collect Notes

Classification: leaf. Task `#1953` has no child tasks and is a scoped implementation task under parent `#1958`, not an aggregate contract.

Leaf verification evidence: `## Verify Notes` records PASS with focused real-boundary proof: 17 mutation-tool tests passed, 12 assess-memory tool tests passed, Ruff lint passed, Ruff format check passed, and `git diff --check` was clean. Verifier-challenger returned pass and no verifier patches were required.

Invariant map coverage: verifier confirmed both acceptance criteria, the expected `tools.py` and `tests/test_mutation_tools.py` ownership, real `MemoryEngine` persistence coverage, unchanged public MCP inventory, and no resolve-memory operation.

Dependency and closure state: dependency `#1952` is satisfied; no children exist; no pending decision or action requests exist; no unresolved Required Follow-up, block, or residual decision state remains.

Archive rationale: verified leaf closure is complete, so archive as completed without re-reviewing implementation details.
