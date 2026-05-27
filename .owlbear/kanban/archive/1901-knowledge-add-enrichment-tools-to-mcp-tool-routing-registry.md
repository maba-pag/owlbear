---
id: 1901
title: 'Knowledge: add enrichment tools to MCP_TOOL_ROUTING registry'
status: archived
priority: needed
created: 2026-05-27T18:18:59.181169+02:00
updated: 2026-05-27T23:12:23.528119+02:00
tags:
  - knowledge
  - layer-4
parent:
depends_on:
  - 1895
  - 1902
ac:
  - 'MCP_TOOL_ROUTING in protocols/registry.py contains 3 new entries: knowledge_enrichment_claim_batch
    → EnrichmentStore.claim_batch, knowledge_enrichment_store → EnrichmentStore.submit_extractions,
    knowledge_enrichment_retry → EnrichmentStore.reset_failed'
  - '3 enrichment tool functions renamed in server.py: get_next_batch → knowledge_enrichment_claim_batch,
    store_enrichment → knowledge_enrichment_store, retry_failed_enrichment → knowledge_enrichment_retry;
    all 3 new names appear in live MCP tool registry; __all__ updated to match'
  - 'Dead bare-function definition of retry_failed_enrichment (~L331) and its redundant
    post-def registration (~L585-587) removed; only one definition per renamed tool
    remains (subsumes #1903)'
  - knowledge-enricher.agent.md tools allowlist and prose references updated to 
    new names
  - 'No old enrichment tool names (get_next_batch, store_enrichment, retry_failed_enrichment)
    remain in docs: serve/mcp-knowledge/README.md, share/skills/h-knowledge-ops/SKILL.md,
    share/skills/w-knowledge-enrichment/SKILL.md, share/prompts/kb-enrich.prompt.md'
  - 'All workspace test files importing renamed enrichment symbols from owlbear_mcp_knowledge.server
    updated to new names; affected: test_store_enrichment_phase1_1892.py, test_get_next_batch_1891.py;
    pytest collection succeeds on both'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Add the 4 enrichment tools to MCP_TOOL_ROUTING in protocols/registry.py and rename them to follow the knowledge_enrichment_* convention.

## Tools to Add

| Current name | Proposed registry name |
|---|---|
| get_next_batch | knowledge_enrichment_claim_batch |
| get_consolidation_candidates | knowledge_enrichment_consolidation_candidates |
| store_enrichment | knowledge_enrichment_store |
| retry_failed_enrichment | knowledge_enrichment_retry |

## Context

These tools are currently not in MCP_TOOL_ROUTING and don't follow the knowledge_* prefix convention used by all other tools. See .owlbear/research/knowledge-mcp-tool-rename.md for context from #1895.

## Notes

Renaming also requires updating knowledge-enricher.agent.md allowlist.

[[2026-05-27T21:11:52+02:00]]


## Research Findings

**Scope correction:** Only 3 tools exist (not 4). `get_consolidation_candidates` was retired per CP1 design decision — the SAME_AS consolidation pipeline no longer exists.

**Corrected tools:**

| Current name | Proposed registry name | Routing value |
|---|---|---|
| get_next_batch | knowledge_enrichment_claim_batch | EnrichmentStore.claim_batch |
| store_enrichment | knowledge_enrichment_store | EnrichmentStore.submit_extractions |
| retry_failed_enrichment | knowledge_enrichment_retry | EnrichmentStore.reset_failed |

**Prerequisite:** `retry_failed_enrichment` bypasses the Protocol (raw SQL). A new `EnrichmentStore.reset_failed()` method is needed before it can be cleanly routed.

**Bug found:** `retry_failed_enrichment` is defined twice in server.py (L331 bare + L591 @mcp.tool) — dead code to clean up.

Research doc: .owlbear/research/enrichment-tools-registry.md

[[2026-05-27T21:12:40+02:00]]
## Research
- Research doc: .owlbear/research/enrichment-tools-registry.md
- Sources: 6 studied, 4 high-relevance
- Key finding: Only 3 tools exist (not 4) — get_consolidation_candidates retired per CP1
- Prerequisite identified: EnrichmentStore.reset_failed() Protocol method needed for retry tool
- Bug found: duplicate retry_failed_enrichment definition in server.py
- Follow-ups: #1902 (Protocol method), #1903 (duplicate fix)
- Recommendation: reduce scope to 3 tools, sequence after Protocol method addition (confidence: 0.85)

[[2026-05-27T21:24:20+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: register + rename 3 enrichment tools to match MCP_TOOL_ROUTING convention |
| Interface clarity | PASS | AC enumerates exact renames, live registry assertion, dead code removal, doc surface |
| Dependency correctness | PASS | Added #1902 as dependency (EnrichmentStore.reset_failed must exist before routing can reference it); #1895 already archived |
| Module layering | PASS | Registry is in protocols/, MCP server dispatches to Protocol methods — no upward imports |
| TDD compliance | PASS | Proof bundle: smoke; test-writer writes rename verification |
| KISS/YAGNI | PASS | Mechanical rename + registry addition, mirrors completed #1895 |
| Premise challenge | PASS | Registry docstring mandates all tools be registered; enrichment tools are not — fix is legitimate |
| Pattern consistency | PASS | Follows knowledge_* prefix convention established by #1895 renames |
| Security surface | PASS | No new system boundaries; same functions, new names |
| Single domain | PASS | Knowledge domain only (enrichment module) |

### Naming Convention Note
All 3 tools use `knowledge_enrichment_` prefix (not bare `knowledge_`). This sub-prefix groups enrichment-specific tools distinctly from the 8 core tools, following the `KnowledgeModule.ENRICHMENT` module identity in registry.py.

### Impact Surface
| File | Changes |
|------|---------|
| serve/knowledge/src/owlbear_knowledge/protocols/registry.py | +3 entries in MCP_TOOL_ROUTING |
| serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | 3 function renames, __all__ update, dead code removal (~L331 + ~L585-587) |
| share/agents/knowledge-enricher.agent.md | allowlist (L9) + prose refs (L17, L32, L69, L81) |
| share/skills/h-knowledge-ops/SKILL.md | section headers (L80, L99, L111) + body refs |
| share/skills/w-knowledge-enrichment/SKILL.md | tool table (L24-26) + body refs (L42, L99, L116, L138-140) |
| share/prompts/kb-enrich.prompt.md | tool references |
| serve/mcp-knowledge/README.md | tool table (L29-30) |
| tests/test_store_enrichment_phase1_1892.py | import rename |
| tests/test_get_next_batch_1891.py | import rename |

### Design Diverge
- Trigger: skipped — single approach, no design alternatives for a mechanical rename

### Challenge Results
- Challenger: block (confidence 0.29)
- Issues raised: (1) prerequisite sequencing, (2) AC2 wording precision, (3) missing prompt surface, (4) no live MCP registry assertion
- Architect response: ACCEPTED and revised — (1) added #1902 as dependency, (2) split dead-code removal into separate AC3, clarified tool registration mechanism in AC2, (3) added kb-enrich.prompt.md to AC5 doc surface, (4) added live MCP registry check to AC2
- Override justification: challenger recommended block due to Protocol dependency; resolved by adding #1902 as depends_on — task won't be picked up until Protocol method exists

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Rationale: Behavior unchanged — only names change. Mirrors #1895 (7-tool rename, smoke bundle, successful completion). Smoke tests verify new names registered and callable.
- Existing proof scope: N/A
- Test-writer: PROCEED

### Dependency Restructuring
- Added #1902 (EnrichmentStore.reset_failed Protocol method) as dependency — blocks until Protocol method exists
- Removed parent=1901 from #1902 (was incorrectly structured as child)
- #1903 (duplicate fix) subsumed by AC3; removed parent, noted as merged

### Verdict: APPROVE
### Action Taken: AC refined (6 verifiable lines), proof bundle set to smoke, dependency on #1902 added, #1903 subsumed. Task blocked on #1902 completion before test-writer picks it up.

[[2026-05-27T22:25:09+02:00]]
## Test-Writer Notes
- Test file: tests/test_enrichment_tools_registry_1901.py
- Class: TestFromAC_EnrichmentToolRename
- Proof bundle: smoke — one smoke test per AC line
- Total: 6 tests, all FAIL (RED confirmed)

**Tests per category (smoke):**
| Test | AC | Failure reason |
|------|----|----------------|
| test_ac1_mcp_tool_routing_has_three_enrichment_entries | AC1 | MCP_TOOL_ROUTING missing new keys (returns None) |
| test_ac2_new_function_names_callable_and_in_all | AC2 | AttributeError: no attribute knowledge_enrichment_claim_batch |
| test_ac3_dead_bare_retry_definition_removed | AC3 | 'def retry_failed_enrichment' still in server.py source |
| test_ac4_agent_file_allowlist_uses_new_names | AC4 | New name not in agent.md allowlist |
| test_ac5_doc_files_contain_no_old_enrichment_names | AC5 | get_next_batch still in README.md |
| test_ac6_affected_test_files_use_new_import_names | AC6 | New symbol not in test_get_next_batch_1891.py |

**AC coverage:**
| AC | Test |
|----|------|
| AC1 — registry entries | test_ac1 |
| AC2 — server renames + __all__ | test_ac2 |
| AC3 — dead code removed | test_ac3 |
| AC4 — agent file updated | test_ac4 |
| AC5 — docs updated | test_ac5 |
| AC6 — test files updated | test_ac6 |

[[2026-05-27T22:46:33+02:00]]
## Builder Notes
- Implementation:
  - serve/knowledge/src/owlbear_knowledge/protocols/registry.py
  - serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  - serve/mcp-knowledge/README.md
  - share/agents/knowledge-enricher.agent.md
  - share/skills/h-knowledge-ops/SKILL.md
  - share/skills/w-knowledge-enrichment/SKILL.md
  - share/prompts/kb-enrich.prompt.md
  - tests/test_get_next_batch_1891.py
  - tests/test_store_enrichment_phase1_1892.py
- Approach: Added 3 enrichment entries to MCP_TOOL_ROUTING, renamed the 3 enrichment MCP tool callables to knowledge_enrichment_* names, removed the duplicate retry function definition, updated tool registration + __all__, and synchronized all AC-listed doc/agent/test import surfaces.
- RED verification (quality-runner, scoped): tests/test_enrichment_tools_registry_1901.py -> 0 passed / 6 failed (all TestFromAC checks failed before implementation).
- GREEN verification (quality-runner, scoped):
  - tests/test_enrichment_tools_registry_1901.py + tests/test_get_next_batch_1891.py + tests/test_store_enrichment_phase1_1892.py + tests/test_knowledge_tool_rename_1895.py
  - Result: 82 passed, 0 failed, 0 skipped
  - Lint: clean (ruff clean on touched Python files + relevant tests)
- Coverage evidence:
  - Scoped run on touched modules reported: owlbear_mcp_knowledge.server 42%, owlbear_knowledge.protocols.registry 100% (overall 37%).
  - Full mode attempt timed out in quality-runner environment and auto-fell back to scoped run; smoke proof bundle evidence was captured via passing scoped tests + lint.
- AC6 evidence: both affected renamed test files executed successfully in GREEN run (collection and execution succeeded).
- Builder fix applied during verification: moved Mapping import in registry.py into TYPE_CHECKING block to satisfy ruff TC003.
- Commit: 66e9c023

### Post-task Reflection
- Duplicate retry tool definition in server.py was a real dead-code hotspot; consolidating to one renamed definition reduced ambiguity and matched AC intent.
- Surface renames were safest when synchronized across registry, MCP server exports, agent allowlist, docs, and importing tests in one pass.
- quality-runner full mode timeout is a recurring cost sink; scoped smoke evidence remained reliable for this task's verification bundle.

[[2026-05-27T22:49:32+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1901 -> todo | AC2 and AC4 are under-proven by weak task-test assertions despite implementation appearing compliant.

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC2 — renamed functions must appear in live MCP tool registry and `__all__` | Task test only validates callability + `__all__`; it does not assert live MCP registry membership for the 3 enrichment tools, so AC2 can pass with stale registry wiring. | `tests/test_enrichment_tools_registry_1901.py` test_ac2 checks only `callable(...)` and `server.__all__` (lines 45-54). No registry introspection call exists there. Existing registry-proof pattern exists in `tests/test_knowledge_tool_rename_1895.py` (`_registered_tool_names` + registry assertions, lines 59-66 and 92-113). | todo |
| 2 | AC4 — allowlist and prose references updated to new names | Task test checks only one positive (`knowledge_enrichment_claim_batch`) and one negative (`get_next_batch`); it does not verify the other two renamed tools or old-name absence across all three mappings, so AC4 is not fully proven. | `tests/test_enrichment_tools_registry_1901.py` test_ac4 assertions are limited to lines 67-68. AC4 requires full rename surface in `share/agents/knowledge-enricher.agent.md`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add AC2 assertions that live MCP registry contains `knowledge_enrichment_claim_batch`, `knowledge_enrichment_store`, `knowledge_enrichment_retry` and excludes old enrichment names. | tests/test_enrichment_tools_registry_1901.py | Finding #1; AC2 text requires live registry proof. |
| 2 | test-writer | Strengthen AC4 assertions to verify all three new enrichment names are present and all three old names are absent in allowlist/prose surface. | tests/test_enrichment_tools_registry_1901.py, share/agents/knowledge-enricher.agent.md | Finding #2; current test covers only 1/3 rename pair. |

## Observations
- Direct code checks support implementation correctness for AC1–AC6 surfaces: registry mappings are present in `serve/knowledge/src/owlbear_knowledge/protocols/registry.py`; MCP tool registration/export uses renamed enrichment functions in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`; old enrichment names are absent from AC5 doc files.
- No security-sensitive regression indicators were found in this rename-only scope.

[[2026-05-27T22:53:56+02:00]]
## Test-Writer Notes
- Retry cycle: reviewer FAILed AC2 and AC4 for under-proven assertions.
- Test file: tests/test_enrichment_tools_registry_1901.py
- Class: TestFromAC_EnrichmentToolRename
- Commit: 37437fe6

**Gaps filled (4 new tests added to existing class):**

| Test | AC | Reviewer gap |
|------|----|--------------|
| test_ac2_new_enrichment_names_in_live_mcp_registry | AC2 | Missing live registry introspection for all 3 new enrichment names |
| test_ac2_old_enrichment_names_absent_from_live_mcp_registry | AC2 | Missing old-name exclusion check in live registry |
| test_ac4_all_new_enrichment_names_in_agent_allowlist | AC4 | Only 1/3 new names checked; now all 3 verified |
| test_ac4_all_old_enrichment_names_absent_from_agent_allowlist | AC4 | Only 1/3 old names checked; now all 3 verified |

**Total: 10 tests, all PASS against current implementation.**
**Lint: clean (ruff 0 violations).**

**Builder skip: test-only retry — all new assertions already satisfied by committed implementation (66e9c023). Advancing directly to review.**

[[2026-05-27T22:57:18+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1901 -> docs | AC mapped to code and evidence sufficient.

| AC Line | Code Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC1 | `serve/knowledge/src/owlbear_knowledge/protocols/registry.py:87-89` maps `knowledge_enrichment_claim_batch`→`EnrichmentStore.claim_batch`, `knowledge_enrichment_store`→`EnrichmentStore.submit_extractions`, `knowledge_enrichment_retry`→`EnrichmentStore.reset_failed`. | `tests/test_enrichment_tools_registry_1901.py:59-65` asserts all 3 routing entries and values. | PASS |
| AC2 | Renamed tool defs at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:122,182,331`; live FastMCP registration at `:584-592`; exports in `__all__` at `:601-603`. | Baseline callable/export checks at `tests/test_enrichment_tools_registry_1901.py:67-77`; live registry inclusion/exclusion checks at `:127-149` (`_registered_tool_names` at `:46-52`). Test-writer retry note reports 10/10 PASS with lint clean. | PASS |
| AC3 | Single renamed retry definition remains at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:331` with single tool registration `:590-592`; no `def retry_failed_enrichment(` remains. | `tests/test_enrichment_tools_registry_1901.py:79-84` asserts old def string absent and exactly one `def knowledge_enrichment_retry`. | PASS |
| AC4 | Agent allowlist/prose updated in `share/agents/knowledge-enricher.agent.md` (tools/prose refs at `:9,17,29,32,33,35,69,81`), with old names absent. | Full 3-name allowlist coverage added at `tests/test_enrichment_tools_registry_1901.py:157-182` (all new present, all old absent). | PASS |
| AC5 | No old enrichment names found in required docs: `serve/mcp-knowledge/README.md`, `share/skills/h-knowledge-ops/SKILL.md`, `share/skills/w-knowledge-enrichment/SKILL.md`, `share/prompts/kb-enrich.prompt.md` (targeted grep checks returned no matches for old names). | `tests/test_enrichment_tools_registry_1901.py:93-108` iterates those exact four files and asserts absence of `get_next_batch`, `store_enrichment`, `retry_failed_enrichment`. | PASS |
| AC6 | Updated imports use renamed symbols in `tests/test_get_next_batch_1891.py:37` and `tests/test_store_enrichment_phase1_1892.py:28`; old imported symbols are absent. | `tests/test_enrichment_tools_registry_1901.py:110-119` asserts both affected files reference new symbols; builder scoped GREEN run reports affected tests executed successfully with collection/execution success. | PASS |

- Builder evidence consistency: prior reviewer AC2/AC4 proof gaps are explicitly closed by test-writer retry additions (`tests/test_enrichment_tools_registry_1901.py:127-149` and `:157-182`), with no contradictory evidence found.
- Safety/security check: rename-and-routing scope only; no new dependency, auth, secret, injection, or external-boundary regressions observed.

## Observations
- No non-blocking issues requiring follow-up were identified in this cycle.
- Independent quality rerun was not required because builder/test-writer evidence was complete and internally consistent for a smoke proof bundle.

[[2026-05-27T22:59:46+02:00]]
## Docs Gate

**Verdict: PASS → done**

### Checklist

**Item 1: README Verification**
- Convention mapping: `serve/knowledge/src/**` → `serve/knowledge/README.md`; `serve/mcp-knowledge/src/**` + `serve/mcp-knowledge/README.md` → `serve/mcp-knowledge/README.md`; `share/**` → `share/README.md`, `share/WIRING.md`
- `serve/knowledge/README.md`: no enrichment tool names referenced (library-level README covers public Python API exports, not MCP routing); no impact.
- `serve/mcp-knowledge/README.md`: **task-caused gap found and fixed** — `knowledge_enrichment_retry` was missing from the tool table despite being implemented, registered, and in `__all__`. Added row with docstring-sourced description. Commit: 4a671935.
- Pre-existing: `get_consolidation_candidates` row still present (retired per CP1 before this task); added TODO marker for follow-up.
- `share/README.md` / `share/WIRING.md`: grep confirms no old or new enrichment tool name references — no impact.

**Item 2: External Attribution**
N/A — no external sources used; task was a mechanical rename of internal tool names to match registry conventions.

**Item 3: Research Doc**
Research doc `.owlbear/research/enrichment-tools-registry.md` exists and is linked from the task body (Research Findings section). Verified.

**Item 4: Deletion Detection**
Old names (`get_next_batch`, `store_enrichment`, `retry_failed_enrichment`) removed from all AC5 doc surfaces; confirmed by reviewer grep evidence and AC5 test assertions. No orphaned references remain in mapped READMEs.

### Files Updated
- `serve/mcp-knowledge/README.md` — added `knowledge_enrichment_retry` row; added TODO for stale `get_consolidation_candidates` entry

### Scratch Cleanup
- `.owlbear/scratch/1901-pytest-output.txt` — deleted

[[2026-05-27T23:12:23+02:00]]
## Audit

### Regression Detection
quality-runner full report: 660 passed, 3 failed, 0 skipped, lint clean.
3 failures in test_engine_end_work.py (create_dr→create_request naming mismatch) — pre-existing, last touched by unrelated commits (414444b9, c2d46412). No task-caused regressions.

### Intent Verification
All changed files stay within knowledge domain: registry.py, server.py (mcp-knowledge), README.md (mcp-knowledge), agent file, prompt, skills, and related test imports. Purpose matches stated task: mechanical rename of 3 enrichment tools to knowledge_enrichment_* convention + registry addition. No extraneous scope.

### Architect Quality
Score: 5/5 — AC lines are specific (exact mappings, file targets, old/new names), complete (6 verifiable lines covering registry, server, dead code, agent, docs, tests), and produced a clean implementation path. Challenger engaged, dependency added, design review thorough.

### Commit Integrity
- Builder: 66e9c023 (implementation + test import renames)
- Test-writer retry: 37437fe6 (strengthened AC2/AC4 assertions per reviewer feedback)
- Doc-writer: 4a671935 (README gap fix)
All commits verified present and containing expected files.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
