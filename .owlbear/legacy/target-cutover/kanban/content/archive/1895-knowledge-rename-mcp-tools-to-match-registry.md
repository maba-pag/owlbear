---
id: 1895
title: 'Knowledge: rename MCP tools to match registry'
status: archived
priority: medium
created: 2026-05-27T11:05:45.483741+02:00
updated: 2026-05-27T21:05:24.784086+02:00
tags:
  - knowledge
  - layer-4
parent:
depends_on:
  - 1894
ac:
  - '7 @mcp.tool functions in server.py renamed per matrix: search_knowledge→knowledge_search,
    list_sources→knowledge_sources_list, get_stats→knowledge_stats, ingest_document→knowledge_ingest,
    knowledge_register_source→knowledge_sources_register, remove_source→knowledge_sources_delete,
    refresh_source→knowledge_sources_refresh; __all__ updated to match'
  - 'Collision resolved: _legacy_graph_stats exists as a callable in module namespace
    (unconditional assert — no fallback branch); get_stats→knowledge_stats registered
    as @mcp.tool (covered by AC1 registry check)'
  - 'Agent tools: allowlists and prose references in knowledge-enricher.agent.md and
    knowledge-ingestor.agent.md use new tool names'
  - 'No old tool names remain in docs: serve/mcp-knowledge/README.md, share/skills/h-knowledge-ops/SKILL.md,
    setup/setup-guide.md, share/skills/w-knowledge-enrichment/SKILL.md, share/prompts/kb-enrich.prompt.md,
    README.md'
  - 'All workspace test files importing renamed symbols from owlbear_mcp_knowledge.server
    updated to new names; affected suites: test_search_provenance.py, test_register_source_1890.py,
    test_remove_source_1889.py, test_ingest_document_coordinator_1893.py, test_mcp_knowledge_read_tools_1881.py,
    test_mcp_knowledge_lifespan_1888.py, test_persistence_source_wiring.py; pytest
    collection succeeds on all 7 files'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Rename exposed MCP tool functions to match MCP_TOOL_ROUTING names in protocols/registry.py.

See `.owlbear/research/knowledge-mcp-tool-rename.md`

## Renames (full set — 7 total)

| Current | Target |
|---------|--------|
| search_knowledge | knowledge_search |
| list_sources | knowledge_sources_list |
| get_stats | knowledge_stats |
| ingest_document | knowledge_ingest |
| knowledge_register_source | knowledge_sources_register |
| remove_source | knowledge_sources_delete |
| refresh_source | knowledge_sources_refresh |
| knowledge_entity_lookup | _(already correct)_ |

## Impact Surface

| File | Changes |
|------|---------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 7 function renames |
| `share/agents/knowledge-enricher.agent.md` | allowlist: get_stats, search_knowledge |
| `share/agents/knowledge-ingestor.agent.md` | allowlist: get_stats, ingest_document, list_sources, refresh_source, search_knowledge |
| `serve/mcp-knowledge/README.md` | tool table |
| `share/skills/h-knowledge-ops/SKILL.md` | KNOWLEDGE_TOOLS_EXCLUDE example list |
| `setup/setup-guide.md` | example env value |

## Notes

This is a breaking change for MCP consumers. Requires coordinated agent tool-allowlist update across all agent configs that reference these tools. Must be a single atomic commit.

Enrichment tools (get_next_batch, get_consolidation_candidates, store_enrichment, retry_failed_enrichment) are NOT in the registry — separate follow-up task.

[[2026-05-27T18:19:10+02:00]]
## Research

Key findings: Task body listed 3 renames but registry requires 7. Updated task body with complete rename matrix.

Trade-off matrix: .owlbear/research/knowledge-mcp-tool-rename.md

Impact: 7 function renames in server.py, 2 agent allowlists, 3 doc files. Must be atomic commit (breaking change).

Follow-up: #1901 (enrichment tools not in registry — separate scope).

Confidence: 0.90 — mechanical rename, clear target state from registry.

[[2026-05-27T18:31:40+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: rename 7 MCP tool functions to match registry |
| Interface clarity | PASS | AC enumerates all 7 renames with exact source→target |
| Dependency correctness | PASS | #1894 archived (dup of completed #1881); underlying work done |
| Module layering | PASS | Renames within MCP server layer; no architectural changes |
| TDD compliance | PASS | Proof bundle: smoke — test-writer writes rename verification |
| KISS/YAGNI | PASS | Mechanical find-and-replace, no new abstractions |
| Premise challenge | PASS | Registry defines naming convention; tools don't match; fix is legitimate |
| Pattern consistency | PASS | Aligns with MCP_TOOL_ROUTING naming convention |
| Security surface | PASS | No new system boundaries; same functions, new names |
| Single domain | PASS | Knowledge domain only |

### Naming Collision (builder guidance)
`get_stats` must become `knowledge_stats` per registry. But `knowledge_stats` already exists at L1209 as a non-tool legacy helper (returns formatted string from graph_store.get_counts()). Resolution: rename legacy helper to `_legacy_graph_stats` or remove it (slated for removal in #1900 anyway). The `_knowledge_stats_bridge` resource and `knowledge_stats_resource` helper are unaffected (different names).

### Expanded Impact Surface
Challenger identified additional consumers beyond original 6 files:
- `share/skills/w-knowledge-enrichment/SKILL.md` — references `get_stats` (L26, L34, L160)
- `share/prompts/kb-enrich.prompt.md` — references `get_stats` (L26)
- `README.md` — references `knowledge_register_source`, `refresh_source` (L106)
- Agent prose sections (not just allowlists) reference tool names

All now covered in AC4.

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Rationale: Behavior unchanged — only names change. Smoke tests verify new names registered and callable. Existing behavioral tests (with updated imports) prove behavior preserved. Builder updates test imports as part of making codebase compile.
- Existing proof scope: N/A
- Test-writer: PROCEED (smoke tests)

### Design Diverge
- Trigger: skipped — single approach, no design alternatives for a mechanical rename

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Issues raised: (1) AC wording, (2) incomplete impact surface, (3) proof bundle under-argued, (4) collision handling, (5) external consumer impact
- Architect response: ACCEPTED and revised — expanded AC to enumerate all renames, added collision resolution AC, expanded impact surface to 9 files (from 6), kept smoke bundle (behavior unchanged; only names change; blast radius is wide but shallow)
- Override justification for smoke: The change is purely mechanical rename. No logic change, no new codepaths, no new failure modes. `behavioral` would require the test-writer to write comprehensive behavioral tests that ALREADY EXIST under old names. The builder will fix existing test imports as part of making the codebase compile.

### Verdict: APPROVE
### Action Taken: AC refined (4 verifiable lines), proof bundle set to smoke, impact surface expanded, naming collision guidance added. Advancing to todo.

[[2026-05-27T18:32:11+02:00]]
Architecture review complete. AC refined from 3 vague lines to 4 verifiable criteria. Proof bundle: smoke. Key findings: naming collision with existing knowledge_stats helper (guidance added), impact surface expanded to 9 files (from 6). Challenger accepted — all issues addressed in revised AC and body.

[[2026-05-27T18:37:09+02:00]]
## Test-Writer Notes

- Test file: `tests/test_knowledge_tool_rename_1895.py`
- Proof bundle: `smoke` — one smoke test per AC line
- Classes: `TestFromAC_ToolRenames`, `TestFromAC_KnowledgeStatsCollision`, `TestFromAC_AgentAllowlists`, `TestFromAC_DocRefs`
- Tests by category: happy=0, edge=0, error=0, boundary=0, smoke=6
- Total: 6 tests, all FAIL ✓, lint clean ✓

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 — 7 @mcp.tool renamed; __all__ updated | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all` |
| AC2 — non-tool knowledge_stats helper privatised/removed | `test_knowledge_stats_is_registered_mcp_tool` |
| AC3 — agent allowlists/prose use new names | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names` |
| AC4 — no old names in 6 doc files | `test_doc_files_contain_no_old_tool_names` |

Failure evidence (quality-runner scoped): pytest exit 1, ruff exit 0.

[[2026-05-27T18:44:18+02:00]]
## Builder Notes
- Implementation: renamed 7 MCP tool exports in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` to match registry (`knowledge_search`, `knowledge_sources_list`, `knowledge_stats`, `knowledge_ingest`, `knowledge_sources_register`, `knowledge_sources_delete`, `knowledge_sources_refresh`), updated `__all__`, and resolved name collision by renaming the legacy non-tool helper `knowledge_stats` to `_legacy_graph_stats`.
- Non-code impact updates: updated all required references in `share/agents/knowledge-enricher.agent.md`, `share/agents/knowledge-ingestor.agent.md`, `serve/mcp-knowledge/README.md`, `share/skills/h-knowledge-ops/SKILL.md`, `setup/setup-guide.md`, `share/skills/w-knowledge-enrichment/SKILL.md`, `share/prompts/kb-enrich.prompt.md`, and `README.md`.
- Tests (quality-runner, scoped): `tests/test_knowledge_tool_rename_1895.py` -> 6 passed, 0 failed, 0 skipped.
- Lint (quality-runner, scoped): clean after ordering fix for `__all__` (`RUF022`).
- Coverage (quality-runner scoped report): module `owlbear_mcp_knowledge.server` reported 21% (smoke-bundle task; no behavioral logic expansion).
- Commit: `36ab9091` (`feat: rename knowledge MCP tools to registry names (#1895, builder)`).

[[2026-05-27T18:52:00+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: todo
- Summary: Direct inspection shows the implementation is aligned with the acceptance criteria, but the proof packet is insufficient on AC1 and AC3. Review rejects for stronger task-scoped tests.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The smoke proof only checks `server.__all__` membership and does not prove that the six renamed MCP tools besides `knowledge_stats` are registered under their new names. A broken implementation could keep legacy registry names while exporting new aliases and still pass. | `tests/test_knowledge_tool_rename_1895.py:75`, `tests/test_knowledge_tool_rename_1895.py:81`, `tests/test_knowledge_tool_rename_1895.py:84`, `tests/test_knowledge_tool_rename_1895.py:100`, `tests/test_knowledge_tool_rename_1895.py:109`; current code defines renamed tools at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:860`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1004`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1056`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1152`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1240`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1287` | todo |
| 2 | AC3 | The agent-file proof is absence-only. It never asserts that the expected new tool names are present in allowlists and prose, so the tests would still pass if those references were deleted entirely. | `tests/test_knowledge_tool_rename_1895.py:127`, `tests/test_knowledge_tool_rename_1895.py:130`, `tests/test_knowledge_tool_rename_1895.py:135`, `tests/test_knowledge_tool_rename_1895.py:138`; current files show required new names at `share/agents/knowledge-enricher.agent.md:9`, `share/agents/knowledge-enricher.agent.md:38`, `share/agents/knowledge-enricher.agent.md:40`, `share/agents/knowledge-ingestor.agent.md:8`, `share/agents/knowledge-ingestor.agent.md:33` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add task-scoped assertions that the MCP tool registry contains all seven renamed tool names and excludes the seven legacy tool names, not just `__all__` membership. | `tests/test_knowledge_tool_rename_1895.py` | Finding 1 |
| 2 | test-writer | Add positive assertions for the expected new tool names in `knowledge-enricher.agent.md` and `knowledge-ingestor.agent.md` allowlists and prose so deletion-only regressions fail. | `tests/test_knowledge_tool_rename_1895.py`, `share/agents/knowledge-enricher.agent.md`, `share/agents/knowledge-ingestor.agent.md` | Finding 2 |

## Observations
- Direct file inspection indicates the builder implementation itself is consistent with the AC: renamed `@mcp.tool` functions exist in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:860`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1004`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1056`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1152`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1240`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1287`; the legacy helper was privatised at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1209`; whole-word stale-name searches over the required agent and documentation files returned no matches.
- Builder evidence was otherwise sufficient for review: scoped tests reported 6 passed, scoped lint was clean, and no contradictory evidence was found.
- Non-blocking: `RegisteredSourceResult` still mentions `knowledge_register_source` in an internal docstring at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:512`. This is outside AC4's required doc set but is worth cleaning up when the file is next touched.

[[2026-05-27T18:56:35+02:00]]
## Test-Writer Notes
- Retry: added 4 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: `tests/test_knowledge_tool_rename_1895.py`
- Commit: `9b2cb8d9`

**New tests added (gap-fill only):**

AC1 gap — MCP registry checks (2 new):
- `TestFromAC_ToolRenames.test_new_tool_names_in_mcp_registry` — all 7 new names in live MCP registry (not just `__all__`)
- `TestFromAC_ToolRenames.test_old_tool_names_absent_from_mcp_registry` — all 7 old names absent from registry

AC3 gap — positive presence assertions (2 new):
- `TestFromAC_AgentAllowlists.test_enricher_agent_has_expected_new_tool_names` — `knowledge_search`, `knowledge_stats` present in enricher
- `TestFromAC_AgentAllowlists.test_ingestor_agent_has_expected_new_tool_names` — `knowledge_ingest`, `knowledge_search`, `knowledge_sources_list`, `knowledge_sources_refresh`, `knowledge_stats` present in ingestor

Total: 10 tests, all PASS (was 6; +4 retry). Lint clean.

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all`, `test_new_tool_names_in_mcp_registry` ✦, `test_old_tool_names_absent_from_mcp_registry` ✦ |
| AC2 | `test_knowledge_stats_is_registered_mcp_tool` |
| AC3 | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names`, `test_enricher_agent_has_expected_new_tool_names` ✦, `test_ingestor_agent_has_expected_new_tool_names` ✦ |
| AC4 | `test_doc_files_contain_no_old_tool_names` |

✦ = new in retry

[[2026-05-27T19:03:38+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Summary: Second review cycle still lacks sufficient proof for AC2. Direct inspection suggests the implementation is aligned, but the task-scoped test packet does not directly prove the helper-collision requirement.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | The only AC2 test proves that `knowledge_stats` is present in the MCP registry, but it never asserts that the pre-existing non-tool `knowledge_stats` helper was renamed to a private symbol or removed. The AC can still be violated without failing the current suite because the proof never inspects the colliding helper symbol itself. | `tests/test_knowledge_tool_rename_1895.py:125-137`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1209` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2 and the retry proof expectation so the review can require a direct check on the collision surface itself (public helper symbol absent or explicitly privatized in `server.py`) instead of inferring it from registry membership alone. | `tests/test_knowledge_tool_rename_1895.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Finding 1 |

## Observations
- AC1 proof is now materially stronger: the retry added live MCP registry assertions for all seven new names and for absence of all seven legacy names in `tests/test_knowledge_tool_rename_1895.py:84-109`.
- Direct file inspection still supports the builder implementation: renamed MCP tool functions are present in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:860`, `:904`, `:1004`, `:1056`, `:1152`, `:1240`, and `:1287`; the legacy helper is currently private at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1209`; and the registry names align with `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:77-84`.
- Agent and doc surfaces inspected for this review showed no remaining legacy tool names in the AC4 document set, and the expected new names are present in the two agent files.
- I did not dispatch `quality-runner` for an independent rerun because the builder/test-writer execution evidence was internally consistent; the blocking issue is proof sufficiency on AC2, not contradictory runtime evidence.

[[2026-05-27T19:05:11+02:00]]
## Architecture Review (re-review cycle 3)

### Context
Reviewer routed to backlog after 2nd review cycle because AC2 proof was insufficient — test only checked MCP registry membership, not the collision surface directly.

### AC2 Refinement
Old: \"Existing non-tool knowledge_stats helper (L1209) renamed to private or removed to resolve collision\"
New: \"Collision resolved: pre-existing non-tool knowledge_stats helper privatised as _legacy_graph_stats (assert callable exists in module) OR removed entirely (assert no public non-tool knowledge_stats symbol in module namespace); get_stats→knowledge_stats registered as @mcp.tool\"

This gives the test-writer two concrete assertions:
1. `hasattr(server, '_legacy_graph_stats')` and `callable(server._legacy_graph_stats)` — proves privatization happened
2. `knowledge_stats` in MCP tool registry — proves the renamed tool took the public name (already tested)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS | AC2 now specifies exact symbol to assert |
| Dependency correctness | PASS | #1894 archived |
| Module layering | PASS | Unchanged |
| TDD compliance | PASS | Test-writer will add 1 assertion for collision proof |
| KISS/YAGNI | PASS | Minimal refinement |
| Pattern consistency | PASS | Unchanged |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED (add collision-surface assertion)

### Challenge Results
- Challenger: SKIPPED — re-review cycle; only AC2 wording changed per reviewer direction

### Verdict: APPROVE
### Action Taken: AC2 refined to require direct collision-surface assertion (_legacy_graph_stats existence). Advancing to todo for test-writer to add the missing proof.

[[2026-05-27T19:09:14+02:00]]
## Test-Writer Notes
- Retry: added 1 test for reviewer AC2 gap. Passes against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: `tests/test_knowledge_tool_rename_1895.py`
- Commit: `3082dfaf`

**New test added (gap-fill only):**

AC2 gap — collision-surface direct assertion (1 new):
- `TestFromAC_KnowledgeStatsCollision.test_collision_helper_privatised_or_removed` — asserts `_legacy_graph_stats` exists and is callable in the module namespace, OR no public non-tool `knowledge_stats` attribute remains; proves privatization was performed (not just inferred from registry membership).

Total: 11 tests, all PASS (was 10; +1 retry). Lint clean.

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all`, `test_new_tool_names_in_mcp_registry`, `test_old_tool_names_absent_from_mcp_registry` |
| AC2 | `test_knowledge_stats_is_registered_mcp_tool`, `test_collision_helper_privatised_or_removed` ✦ |
| AC3 | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names`, `test_enricher_agent_has_expected_new_tool_names`, `test_ingestor_agent_has_expected_new_tool_names` |
| AC4 | `test_doc_files_contain_no_old_tool_names` |

✦ = new in retry

[[2026-05-27T19:36:20+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Summary: Third review cycle still lacks sufficient AC2 proof. The retry test treats MCP registry membership as evidence that no public non-tool `knowledge_stats` symbol remains in the module namespace, but those are different surfaces and can diverge.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | `test_collision_helper_privatised_or_removed` does not directly prove the "removed entirely / no public non-tool `knowledge_stats` symbol in module namespace" branch. Its fallback sets `public_shadow_exists` only when `knowledge_stats` is missing from the registry, so a broken state with a later public helper shadowing the module symbol while the MCP tool remains registered would still pass. | `tests/test_knowledge_tool_rename_1895.py:150`, `tests/test_knowledge_tool_rename_1895.py:155`, `tests/test_knowledge_tool_rename_1895.py:157`; tool registration surface at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1152`; collision surface at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1209`; prior review cycles at `.owlbear/kanban/tasks/1895-knowledge-rename-mcp-tools-to-match-registry.md:162` and `.owlbear/kanban/tasks/1895-knowledge-rename-mcp-tools-to-match-registry.md:213` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC2 retry-proof contract into a direct module-namespace check that fails if a public non-tool `knowledge_stats` symbol remains, even when the MCP registry still contains the renamed tool, then return the task to test-writer with that explicit proof expectation. | `tests/test_knowledge_tool_rename_1895.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Finding 1 |

## Observations
- AC1 proof is now sufficient: the task-scoped tests directly inspect live MCP registry names at `tests/test_knowledge_tool_rename_1895.py:89` and `tests/test_knowledge_tool_rename_1895.py:102`, matching the routing registry at `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:77`, `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:78`, `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:79`, `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:80`, `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:81`, `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:82`, and `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:84`, and the exported names in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:748`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:860`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1004`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1056`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1152`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1240`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1287`.
- AC3 proof is now sufficient: positive-presence assertions at `tests/test_knowledge_tool_rename_1895.py:193` and `tests/test_knowledge_tool_rename_1895.py:209` align with the current agent files at `share/agents/knowledge-enricher.agent.md:9`, `share/agents/knowledge-enricher.agent.md:38`, `share/agents/knowledge-enricher.agent.md:40`, `share/agents/knowledge-ingestor.agent.md:8`, and `share/agents/knowledge-ingestor.agent.md:33`.
- AC4 proof is adequate for this smoke bundle: the task-scoped doc sweep at `tests/test_knowledge_tool_rename_1895.py:240` and `tests/test_knowledge_tool_rename_1895.py:249` covers the six required files, and sampled updated references are present at `serve/mcp-knowledge/README.md:21`, `serve/mcp-knowledge/README.md:23`, `serve/mcp-knowledge/README.md:24`, `serve/mcp-knowledge/README.md:26`, `serve/mcp-knowledge/README.md:27`, `serve/mcp-knowledge/README.md:31`, `share/skills/h-knowledge-ops/SKILL.md:244`, `share/skills/w-knowledge-enrichment/SKILL.md:26`, `share/prompts/kb-enrich.prompt.md:26`, and `README.md:106`.
- I did not dispatch `quality-runner` for an independent rerun because the builder and test-writer execution evidence was internally consistent; the blocking issue is assertion design, not contradictory runtime evidence.

[[2026-05-27T19:38:18+02:00]]
## Architecture Review (re-review cycle 4)

### Context
Reviewer routed to backlog after 3rd review cycle. AC2 test has an OR-branch logic flaw: `public_shadow_exists` checks `"knowledge_stats" not in registered`, which is always False (MCP tool IS registered under that name), making the "removed entirely" fallback path unreachable. The test passes regardless of whether `_legacy_graph_stats` exists.

### AC2 Refinement
Old: "Collision resolved: pre-existing non-tool knowledge_stats helper privatised as _legacy_graph_stats (assert callable exists in module) OR removed entirely (assert no public non-tool knowledge_stats symbol in module namespace); get_stats→knowledge_stats registered as @mcp.tool"

New: "Collision resolved: _legacy_graph_stats exists as a callable in module namespace (unconditional assert — no fallback branch); get_stats→knowledge_stats registered as @mcp.tool (covered by AC1 registry check)"

Rationale: The builder chose privatisation (confirmed at server.py:1209). Eliminating the OR branch removes the source of all 3 review failures — the test-writer need only write:
```python
assert hasattr(server, "_legacy_graph_stats")
assert callable(server._legacy_graph_stats)
```
No registry membership inference, no conditional logic, no fallback paths.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS | AC2 now specifies single unconditional assertion |
| TDD compliance | PASS | Test-writer replaces flawed test with 2-line direct check |
| KISS/YAGNI | PASS | Simpler proof than previous |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Test-writer: PROCEED (rewrite test_collision_helper_privatised_or_removed as unconditional assert)

### Challenge Results
- Challenger: SKIPPED — re-review cycle 4; only AC2 proof contract simplified per 3 consecutive reviewer findings on same surface

### Verdict: APPROVE
### Action Taken: AC2 refined to unconditional _legacy_graph_stats assertion (eliminated OR branch causing test-logic flaw). Advancing to todo for test-writer to rewrite the single flawed test.

[[2026-05-27T19:40:27+02:00]]
## Test-Writer Notes
- Retry (cycle 4): replaced flawed `test_collision_helper_privatised_or_removed` with `test_collision_helper_privatised` — unconditional `hasattr`/`callable` check on `_legacy_graph_stats`, no OR-branch.
- Builder skip: test-only retry, all 11 tests green against current impl.
- Commit: `684bc895`

**What changed (gap-fill only):**

AC2 gap — unconditional collision-surface assertion (1 replaced):
- `TestFromAC_KnowledgeStatsCollision.test_collision_helper_privatised` — asserts `hasattr(server, "_legacy_graph_stats")` and `callable(server._legacy_graph_stats)` unconditionally; eliminates OR-branch tautology from prior cycle.

Total: 11 tests, all PASS. Lint clean.

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all`, `test_new_tool_names_in_mcp_registry`, `test_old_tool_names_absent_from_mcp_registry` |
| AC2 | `test_knowledge_stats_is_registered_mcp_tool`, `test_collision_helper_privatised` |
| AC3 | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names`, `test_enricher_agent_has_expected_new_tool_names`, `test_ingestor_agent_has_expected_new_tool_names` |
| AC4 | `test_doc_files_contain_no_old_tool_names` |

[[2026-05-27T19:47:12+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Summary: Task-local smoke proof now covers the narrowed acceptance criteria, but the rename is not integrated across adjacent durable consumers. A scoped quality-runner check on representative root suites failed during collection because those suites still import removed public symbols from `owlbear_mcp_knowledge.server`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The public tool rename is incomplete across downstream callers. Four active root suites fail during collection because they still import removed server symbols, and additional durable suites still contain old imports. This leaves the workspace proof surface broken outside `tests/test_knowledge_tool_rename_1895.py`. | quality-runner collection failures in `tests/test_search_provenance.py` for `search_knowledge`, `tests/test_register_source_1890.py` for `knowledge_register_source`, `tests/test_remove_source_1889.py` for `remove_source`, and `tests/test_ingest_document_coordinator_1893.py` for `ingest_document`; additional stale imports in `tests/test_mcp_knowledge_read_tools_1881.py:293`, `tests/test_mcp_knowledge_read_tools_1881.py:395`, `tests/test_mcp_knowledge_read_tools_1881.py:632`, and `tests/test_mcp_knowledge_lifespan_1888.py:497`; replacement exports are `knowledge_search` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:807`, `knowledge_sources_list` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:851`, `knowledge_sources_register` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:951`, `knowledge_ingest` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1003`, `knowledge_stats` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1099`, and `knowledge_sources_delete` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1233` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Expand the task impact surface to include all durable workspace consumers of the renamed MCP tool symbols, and route concrete updates for the stale root suites before this rename task returns to review. | `tests/test_search_provenance.py`, `tests/test_register_source_1890.py`, `tests/test_remove_source_1889.py`, `tests/test_ingest_document_coordinator_1893.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, `tests/test_mcp_knowledge_lifespan_1888.py` | Finding 1 |

## Observations
- Task-local proof is now adequate for the narrowed acceptance-criteria surface: registry assertions in `tests/test_knowledge_tool_rename_1895.py:89` and `tests/test_knowledge_tool_rename_1895.py:102`, collision proof in `tests/test_knowledge_tool_rename_1895.py:140`, positive agent assertions in `tests/test_knowledge_tool_rename_1895.py:186` and `tests/test_knowledge_tool_rename_1895.py:202`, and doc sweep in `tests/test_knowledge_tool_rename_1895.py:242` align with the current renamed exports and private helper in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:696`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:807`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:851`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:951`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1003`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1099`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1155`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1186`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1233`.
- Direct inspection of the agent files remains consistent with AC3: `share/agents/knowledge-enricher.agent.md:9`, `share/agents/knowledge-enricher.agent.md:38`, `share/agents/knowledge-enricher.agent.md:40`, `share/agents/knowledge-ingestor.agent.md:8`, and `share/agents/knowledge-ingestor.agent.md:33` use the renamed tool names.
- Local IDE diagnostics report no errors in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` or `tests/test_knowledge_tool_rename_1895.py`; the blocker is adjacent durable-suite breakage, not the task-local implementation or smoke file.

[[2026-05-27T19:49:37+02:00]]
## Architecture Review (re-review cycle 5)

### Context
Reviewer routed to backlog after 4th review cycle. Task-local smoke proof is now adequate (AC1–AC4), but the rename broke 6 durable test suites that import old symbols directly from `owlbear_mcp_knowledge.server`. The task body states "Must be a single atomic commit" — updating downstream test imports is in scope.

### AC5 Addition
Added: "All workspace test files importing renamed symbols from owlbear_mcp_knowledge.server updated to new names; affected suites: test_search_provenance.py, test_register_source_1890.py, test_remove_source_1889.py, test_ingest_document_coordinator_1893.py, test_mcp_knowledge_read_tools_1881.py, test_mcp_knowledge_lifespan_1888.py; pytest collection succeeds on all 6 files"

Specific renames needed in tests:
- `search_knowledge` → `knowledge_search` (test_search_provenance, test_mcp_knowledge_read_tools_1881 ×8)
- `list_sources` → `knowledge_sources_list` (test_mcp_knowledge_read_tools_1881 ×5, test_mcp_knowledge_lifespan_1888 ×1)
- `get_stats` → `knowledge_stats` (test_mcp_knowledge_read_tools_1881 ×6)
- `ingest_document` → `knowledge_ingest` (test_ingest_document_coordinator_1893 ×1)
- `knowledge_register_source` → `knowledge_sources_register` (test_register_source_1890 ×1)
- `remove_source` → `knowledge_sources_delete` (test_remove_source_1889 ×1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same rename concern; test imports are part of the breaking-change surface |
| Interface clarity | PASS | AC5 enumerates all 6 files and specifies collection-success proof |
| TDD compliance | PASS | Test-writer adds collection-success assertion for AC5 |
| KISS/YAGNI | PASS | Mechanical find/replace in test imports |

### Proof-Bundle Validation
- Final bundle: smoke
- Test-writer: PROCEED (add AC5 collection-success test)

### Challenge Results
- Challenger: SKIPPED — re-review cycle 5; adding missing impact surface identified by reviewer evidence

### Verdict: APPROVE
### Action Taken: AC5 added requiring all durable test suites to use new import names. Builder guidance: mechanical import rename in 6 test files (~22 import occurrences). Advancing to todo.

[[2026-05-27T19:51:53+02:00]]
test-writer crashed once (model_not_supported error); releasing claim before retry

[[2026-05-27T20:21:15+02:00]]
## Test-Writer Notes
- Retry (cycle 5 — re-claim after crash): AC5 test was committed in prior attempt (`4b164963`); reclaimed, verified state, advancing.
- Test file: `tests/test_knowledge_tool_rename_1895.py`
- Classes: `TestFromAC_ToolRenames`, `TestFromAC_KnowledgeStatsCollision`, `TestFromAC_AgentAllowlists`, `TestFromAC_DocRefs`, `TestFromAC_DurableSuiteImports`
- Tests by category: smoke=12 (no happy/edge/error/boundary — smoke bundle)
- Total: 12 tests — 11 PASS (AC1–AC4), 1 FAIL (AC5) ✓
- ruff: clean ✓

**AC5 gap-fill (new in this cycle):**
- `TestFromAC_DurableSuiteImports.test_all_affected_suites_collect_without_error` — subprocess `pytest --collect-only` on all 6 durable suites; fails now (4 suites have stale imports: `test_search_provenance.py`, `test_register_source_1890.py`, `test_remove_source_1889.py`, `test_ingest_document_coordinator_1893.py`); will pass after builder updates stale imports.

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all`, `test_new_tool_names_in_mcp_registry`, `test_old_tool_names_absent_from_mcp_registry` |
| AC2 | `test_knowledge_stats_is_registered_mcp_tool`, `test_collision_helper_privatised` |
| AC3 | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names`, `test_enricher_agent_has_expected_new_tool_names`, `test_ingestor_agent_has_expected_new_tool_names` |
| AC4 | `test_doc_files_contain_no_old_tool_names` |
| AC5 | `test_all_affected_suites_collect_without_error` |

Builder guidance: Fix stale imports in 6 test files (~22 occurrences):
- `test_search_provenance.py`: `search_knowledge` → `knowledge_search`
- `test_register_source_1890.py`: `knowledge_register_source` → `knowledge_sources_register`
- `test_remove_source_1889.py`: `remove_source` → `knowledge_sources_delete`
- `test_ingest_document_coordinator_1893.py`: `ingest_document` → `knowledge_ingest`
- `test_mcp_knowledge_read_tools_1881.py`: `search_knowledge` → `knowledge_search` (×8), `list_sources` → `knowledge_sources_list` (×5), `get_stats` → `knowledge_stats` (×6)
- `test_mcp_knowledge_lifespan_1888.py`: `list_sources` → `knowledge_sources_list` (×1)

[[2026-05-27T20:29:55+02:00]]
## Builder Notes
- Implementation: updated stale durable-suite imports to renamed MCP tool symbols in `tests/test_search_provenance.py`, `tests/test_register_source_1890.py`, `tests/test_remove_source_1889.py`, `tests/test_ingest_document_coordinator_1893.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, and `tests/test_mcp_knowledge_lifespan_1888.py`.
- Fix detail: replaced old server imports with new symbols aliased to existing local names (for example, `knowledge_search as search_knowledge`) so test behavior remained unchanged while import compatibility was restored.
- Tests: quality-runner scoped run on `tests/test_knowledge_tool_rename_1895.py` -> 12 passed, 0 failed, 0 skipped.
- Lint: quality-runner scoped ruff on task test + all 6 affected durable suites -> clean (0 violations).
- Coverage: quality-runner reported `overall_pct: none` / `modules: []` for this smoke-bundle scoped verification (no coverage modules requested).
- Commit: `25f1e407` (`fix: align durable imports with knowledge tool renames (#1895, builder)`).

### Post-task Reflection
- problems_faced: AC5 failure was import-collection breakage in adjacent durable suites, not task-local tool logic.
- workarounds_applied: import aliasing to new names avoided large and risky call-site churn.
- patterns_discovered: breaking MCP rename tasks need durable-suite import reconciliation to keep workspace collection healthy.
- time_sinks: multiple prior cycles focused on AC proof sufficiency before the integration-surface gap was surfaced.
- quality_gaps: smoke verification proved collection/test outcomes and lint cleanliness, but did not produce a coverage percentage in this final scoped run.

[[2026-05-27T20:35:15+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Summary: The rename remains incomplete across workspace test consumers. A direct workspace scan found an additional root test file still importing the removed `ingest_document` symbol outside AC5's enumerated six-suite proof surface, so the acceptance surface is still incomplete on this review cycle.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC5 | AC5's "all workspace test files" impact surface is still incomplete. `tests/test_persistence_source_wiring.py` directly imports removed `ingest_document`, but the task-scoped AC5 proof only collects the six files listed in `_AFFECTED_SUITES`, so the proof packet can pass while an adjacent durable consumer remains stale. | stale direct import at `tests/test_persistence_source_wiring.py:29`; replacement export is `knowledge_ingest` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:702` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1003`; AC5 proof scope is limited at `tests/test_knowledge_tool_rename_1895.py:270` and `tests/test_knowledge_tool_rename_1895.py:279` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Expand AC5 and the task-scoped proof surface to include `tests/test_persistence_source_wiring.py` and any other direct server-import consumers of the renamed symbols, then return the task to test-writer/builder for the import update and proof refresh. | `tests/test_persistence_source_wiring.py`, `tests/test_knowledge_tool_rename_1895.py` | Finding 1 |

## Observations
- Builder and test-writer evidence is otherwise internally consistent on the currently scoped surface: AC1 is backed by renamed exports in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:695`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:807`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:851`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:951`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1003`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1099`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1186`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1233`, with matching registry/export checks at `tests/test_knowledge_tool_rename_1895.py:77`, `tests/test_knowledge_tool_rename_1895.py:83`, `tests/test_knowledge_tool_rename_1895.py:91`, and `tests/test_knowledge_tool_rename_1895.py:104`.
- AC2 and AC3 proof is adequate on the narrowed task surface: `_legacy_graph_stats` exists at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1155`; agent references align at `share/agents/knowledge-enricher.agent.md:9`, `share/agents/knowledge-enricher.agent.md:35`, `share/agents/knowledge-enricher.agent.md:37`, `share/agents/knowledge-ingestor.agent.md:8`, `share/agents/knowledge-ingestor.agent.md:33`, and `share/agents/knowledge-ingestor.agent.md:45`, with matching tests at `tests/test_knowledge_tool_rename_1895.py:127`, `tests/test_knowledge_tool_rename_1895.py:142`, `tests/test_knowledge_tool_rename_1895.py:172`, `tests/test_knowledge_tool_rename_1895.py:180`, `tests/test_knowledge_tool_rename_1895.py:188`, and `tests/test_knowledge_tool_rename_1895.py:204`.
- AC4 proof is adequate for the named doc set: the task-scoped sweep is at `tests/test_knowledge_tool_rename_1895.py:244`, with sampled updated references at `serve/mcp-knowledge/README.md:21`, `serve/mcp-knowledge/README.md:24`, `serve/mcp-knowledge/README.md:26`, `serve/mcp-knowledge/README.md:27`, `serve/mcp-knowledge/README.md:31`, `share/skills/h-knowledge-ops/SKILL.md:226`, `share/skills/w-knowledge-enrichment/SKILL.md:23`, `share/prompts/kb-enrich.prompt.md:26`, and `README.md:106`.
- I did not dispatch `quality-runner` for an independent rerun because the blocker is a concrete missed adjacent consumer discovered in static review, not contradictory builder execution evidence.

[[2026-05-27T20:38:45+02:00]]
## Architecture Review (re-review cycle 6)

### Context
Reviewer routed to backlog after 5th review cycle. Found `tests/test_persistence_source_wiring.py` (RED-phase test for #1320) still imports removed `ingest_document` at L29. This is the only remaining stale consumer — comprehensive workspace scan confirmed no other files import old symbols from `owlbear_mcp_knowledge.server`.

### AC5 Refinement
Expanded the affected-suites list from 6 to 7 files, adding `test_persistence_source_wiring.py`. Collection-success proof must now cover all 7.

Builder guidance: Apply same aliasing pattern as other fixes — `from owlbear_mcp_knowledge.server import knowledge_ingest as ingest_document` in `tests/test_persistence_source_wiring.py:29`. Also update task-scoped test `_AFFECTED_SUITES` list to include the 7th file.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same rename concern; stale import is part of breaking-change surface |
| Interface clarity | PASS | AC5 now enumerates all 7 files |
| TDD compliance | PASS | Task-scoped test updated to collect all 7 |
| KISS/YAGNI | PASS | Single additional import alias |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Test-writer: PROCEED (expand _AFFECTED_SUITES to 7 files)

### Challenge Results
- Challenger: SKIPPED — re-review cycle 6; only expanding impact surface by 1 file per reviewer evidence

### Verdict: APPROVE
### Action Taken: AC5 expanded to 7 files (added test_persistence_source_wiring.py). Builder fixes 1 import + test-writer updates _AFFECTED_SUITES. Advancing to todo.

[[2026-05-27T20:41:28+02:00]]
## Test-Writer Notes
- Retry (cycle 6): expanded `_AFFECTED_SUITES` from 6 → 7 files by adding `tests/test_persistence_source_wiring.py` per architect AC5 refinement.
- Test file: `tests/test_knowledge_tool_rename_1895.py`
- Commit: `689f83f0`

**What changed (gap-fill only):**

AC5 gap — 7th durable suite added to collection-success proof (1 line changed):
- `TestFromAC_DurableSuiteImports._AFFECTED_SUITES` now includes `tests/test_persistence_source_wiring.py`
- `test_all_affected_suites_collect_without_error` now FAILs with `ImportError: cannot import name 'ingest_document'` for that file

**Quality-runner evidence (scoped):** 11 PASS, 1 FAIL (AC5 collection error on `test_persistence_source_wiring.py:29`), ruff: clean.

**Builder guidance:** Apply import alias in `tests/test_persistence_source_wiring.py:29`:
- `from owlbear_mcp_knowledge.server import knowledge_ingest as ingest_document`

Total: 12 tests — 11 PASS, 1 FAIL ✓. Lint clean ✓.

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1 | `test_new_tool_names_in_dunder_all`, `test_old_tool_names_absent_from_dunder_all`, `test_new_tool_names_in_mcp_registry`, `test_old_tool_names_absent_from_mcp_registry` |
| AC2 | `test_knowledge_stats_is_registered_mcp_tool`, `test_collision_helper_privatised` |
| AC3 | `test_enricher_agent_no_old_tool_names`, `test_ingestor_agent_no_old_tool_names`, `test_enricher_agent_has_expected_new_tool_names`, `test_ingestor_agent_has_expected_new_tool_names` |
| AC4 | `test_doc_files_contain_no_old_tool_names` |
| AC5 | `test_all_affected_suites_collect_without_error` (now covers 7 files) |

[[2026-05-27T20:45:21+02:00]]
## Builder Notes
- Implementation: updated [tests/test_persistence_source_wiring.py](tests/test_persistence_source_wiring.py) import to use the renamed MCP symbol (`knowledge_ingest as ingest_document`) so AC5’s final stale consumer is aligned.
- Tests (quality-runner, scoped): `tests/test_knowledge_tool_rename_1895.py` -> 12 passed, 0 failed, 0 skipped.
- Lint (quality-runner, scoped): clean for `tests/test_knowledge_tool_rename_1895.py` and `tests/test_persistence_source_wiring.py`.
- Coverage: `overall_pct: none`, `modules: none` (smoke-bundle scoped run without explicit coverage modules).
- Commit: `225fcef3` (`fix: align persistence wiring import with renamed tool (#1895, builder)`).
- Approach: minimal import alias update to preserve existing durable-test behavior while switching imports to the new public API.

### Post-task Reflection
- problems_faced: a single remaining durable suite outside the prior AC5 six-file set still imported a removed server symbol.
- workarounds_applied: used the established aliasing pattern (`new_name as old_local_name`) to avoid broad test-body churn.
- patterns_discovered: rename tasks need exhaustive durable-consumer sweeps, not only explicitly listed suites.
- time_sinks: repeated review loops occurred before the final adjacent consumer was surfaced.
- quality_gaps: smoke verification confirms collection/test correctness and lint, but scoped run still reports no coverage percentage.

[[2026-05-27T20:48:33+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1895 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:695` (`__all__`) and renamed tool defs at `:807`, `:851`, `:951`, `:1003`, `:1099`, `:1186`, `:1233`; names align with routing registry at `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:77-82,84` | `tests/test_knowledge_tool_rename_1895.py:77`, `:83`, `:91`, `:104` | PASS |
| AC2 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1099` (`knowledge_stats` tool) and `:1155` (`_legacy_graph_stats`) | `tests/test_knowledge_tool_rename_1895.py:127`, `:142` | PASS |
| AC3 | Renamed tool references present in `share/agents/knowledge-enricher.agent.md:9,35,37` and `share/agents/knowledge-ingestor.agent.md:8,33,45`; whole-word old-name scan across both files returned no matches | `tests/test_knowledge_tool_rename_1895.py:172`, `:180`, `:188`, `:204` | PASS |
| AC4 | Whole-word old-name scan over required docs (`serve/mcp-knowledge/README.md`, `share/skills/h-knowledge-ops/SKILL.md`, `setup/setup-guide.md`, `share/skills/w-knowledge-enrichment/SKILL.md`, `share/prompts/kb-enrich.prompt.md`, `README.md`) returned no matches | `tests/test_knowledge_tool_rename_1895.py:244` | PASS |
| AC5 | Seven affected suites now import renamed symbols/aliases: `tests/test_search_provenance.py:28`, `tests/test_register_source_1890.py:31`, `tests/test_remove_source_1889.py:33`, `tests/test_ingest_document_coordinator_1893.py:38`, `tests/test_mcp_knowledge_read_tools_1881.py:293,395,632`, `tests/test_mcp_knowledge_lifespan_1888.py:497`, `tests/test_persistence_source_wiring.py:29`; strict scan for direct old-name imports from `owlbear_mcp_knowledge.server` returned no matches in `tests/**/*.py` | `tests/test_knowledge_tool_rename_1895.py:270`, `:280`, `:297` (collect-only over all 7 suites) | PASS |

## Observations
- Builder evidence is internally consistent with current repo state (scoped quality-runner reported `tests/test_knowledge_tool_rename_1895.py` 12/12 pass and scoped lint clean).
- Focused diagnostics check (`get_errors`) over `server.py`, the task suite, and all seven AC5 durable suites reported no IDE errors.
- Independent quality-runner rerun was not dispatched because the provided evidence was complete and non-contradictory for this smoke-bundle rename task.

[[2026-05-27T20:52:12+02:00]]
## Docs Gate

### Item 1: README Verification
- **`serve/mcp-knowledge/README.md`** — read fully. Layer 1: no old names present (grep clean across all 7 old names). Layer 2: tool table uses all new names (`knowledge_search`, `knowledge_sources_list`, `knowledge_stats`, `knowledge_ingest`, `knowledge_sources_register`, `knowledge_sources_delete`, `knowledge_sources_refresh`). Coherent and audience-appropriate. ✓
- **`share/skills/h-knowledge-ops/SKILL.md`** — Layer 1: no old names; section headers use new names (`### knowledge_search`, `### knowledge_ingest`, `### knowledge_sources_list`, etc.). Layer 2: decision tree and recipes are internally consistent with new names. ✓
- **`share/skills/w-knowledge-enrichment/SKILL.md`** — Layer 1: no old names; references `knowledge_stats` correctly. ✓
- **`share/prompts/kb-enrich.prompt.md`** — Layer 1: no old names; `knowledge_stats` confirmed at L26. ✓
- **`setup/setup-guide.md`** — Layer 1: no old names; `KNOWLEDGE_TOOLS_EXCLUDE` example uses `knowledge_ingest` (L182). ✓
- **`README.md`** — Layer 1: no old names; `knowledge_sources_register`, `knowledge_sources_refresh` present at L106. ✓
- **`share/agents/knowledge-enricher.agent.md`** — Layer 1: allowlist and prose use `knowledge_search`, `knowledge_stats` (new names). ✓
- **`share/agents/knowledge-ingestor.agent.md`** — Layer 1: allowlist and prose use `knowledge_ingest`, `knowledge_search`, `knowledge_sources_list`, `knowledge_sources_refresh`, `knowledge_stats` (all new names). ✓

**Doc-index drift (task-caused):** Builder updated all AC4 docs but did not regenerate `.owlbear/doc-index.md`. Old section headers from `h-knowledge-ops/SKILL.md` (`### search_knowledge`, `### ingest_document`, `### list_sources`, `### refresh_source`, `### get_stats`) remained in the index. Regenerated and committed at `d68801cc`.

### Item 2: External Attribution
N/A — mechanical rename aligned to internal registry. No external sources.

### Item 3: Research Doc
Task body references `.owlbear/research/knowledge-mcp-tool-rename.md` — linkage confirmed in task body. ✓

### Item 4: Deletion Detection
No source files deleted. No orphaned references found in any documentation target. ✓

### Scratch Cleanup
No `1895-*` scratch files found. ✓

### Files Updated
- `.owlbear/doc-index.md` — regenerated to reflect renamed SKILL.md section headers; commit `d68801cc`

[[2026-05-27T21:05:24+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 5717 passed, 132 failed (cross-domain); domain-scoped (mcp-knowledge): 223 passed, 8 failed
- Pre-task baseline comparison: same domain had 10 failed + 23 errors BEFORE task; task improved state (23 collection errors resolved, net -2 failures)
- Task-scoped tests: 12/12 PASS
- Lint violations: 8 in serve/knowledge/ (outside task scope, pre-existing)
- regression verdict: PASS (no new regressions; pre-existing failures from other incomplete tasks)

### Intent Verification
- scope alignment: PASS (all changes within knowledge MCP domain: server.py renames, agent allowlists, doc references, durable-suite import fixes, doc-index regen)
- purpose match: PASS (7 MCP tool renames to match registry naming convention, collision resolved, downstream consumers updated)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
Original AC (3 lines) missed collision surface (AC2), durable-suite import impact (AC5), and additional doc consumers. Required 6 review cycles with progressive AC refinement. Architect responded well to each rejection with targeted refinements, but the initial gap in impact analysis caused significant pipeline churn.

### Commit Integrity
- upstream commit presence: PASS (builder: 36ab9091, 25f1e407, 225fcef3; test-writer: 7f47fe4e, 9b2cb8d9, 3082dfaf, 684bc895, 4b164963, 689f83f0; doc-writer: d68801cc; all properly attributed with #1895 and role)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
- AC quality score 3: -0.03
- No other deductions

### Confidence: 0.97
### Action: archive
