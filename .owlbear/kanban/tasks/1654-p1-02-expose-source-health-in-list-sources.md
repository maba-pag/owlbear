---
id: 1654
title: 'P1-02: Expose source health in list_sources'
status: review
priority: needed
created: 2026-05-18T03:11:18.823946+02:00
updated: 2026-05-18T14:24:07.954750+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on:
  - 1651
ac:
  - 'AC-1: `SourceInfo` TypedDict includes keys `last_refreshed_at: str | None`, `last_checked_at:
    str | None`, `last_error: str | None`, `enabled: bool`, `fetch_method: str`'
  - 'AC-2: `list_sources` response dict maps the 5 new fields from the corresponding
    `KnowledgeSource` model attributes for each source returned'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-18T14:24:07.954750+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Expand `SourceInfo` TypedDict and `list_sources` MCP tool response with 5 health fields.

**Out-of-scope:** `config` field (URL/endpoint leak risk per brief). `enrich` field (processing config, not health per brief D5). Refresh logic (O2). Source removal (O4).

## Context

Current `SourceInfo` has 4 keys: `id`, `name`, `source_type`, `scope`. Needs 5 additional keys from `KnowledgeSource`: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`.

`list_sources` currently builds response dicts with only the 4 existing keys. Must add the 5 new keys mapping from `KnowledgeSource` attributes.

Depends on #1651 because `last_checked_at` must exist in the model before it can be exposed.

[[2026-05-18T13:29:37+02:00]]
## Research

### Gate Checklist
1. **Validity** — Sound; standard field-exposure pattern
2. **Env audit** — No existing mechanism exposes health fields
3. **Prior art** — Same file maps 4 fields with identical TypedDict→dict pattern (L108–115, L1409–1415)
4. **Feasibility** — Zero blockers. Dep #1651 complete; all 5 target fields exist in `KnowledgeSource` model
5. **Arch fit** — MCP server owns TypedDict contract; no new imports or wiring
6. **Approach** — Add 5 fields to `SourceInfo` TypedDict, add 5 key-value pairs to dict comprehension. All primitives (`str | None`, `bool`, `str`) — direct attribute access
7. **Testing** — Extend `test_list_sources.py` (new keys + correct mapping) and `test_outputschema.py` (schema properties + types)

### Classification
T1 — Autonomous. Mechanical field expansion, established pattern, no decisions.

### No research doc
Trivial implementation with clear AC and no trade-offs. No follow-up tasks needed — ready for TDD.

[[2026-05-18T13:53:20+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expose health fields in list_sources response |
| Interface clarity | PASS | AC specifies exact field names, types, and mapping source |
| Dependency correctness | PASS | #1651 archived — last_checked_at field exists in model |
| Module layering | PASS | MCP server reads from knowledge model (correct direction) |
| TDD compliance | PASS | Standard pipeline; test-writer processes at todo |
| KISS/YAGNI | PASS | Minimal scope — 5 key-value pairs added to existing pattern |
| Premise challenge | PASS | Health exposure required for Cockpit source monitoring |
| Pattern consistency | PASS | Same TypedDict→dict pattern as existing 4 fields (L108–116, L1409–1422) |
| Security surface | PASS | config field deliberately excluded (leak risk per brief); only metadata exposed |
| Single domain | PASS | scope:mcp-knowledge only; consolidation-test #1655 covers cross-domain family |

### Challenge Results
- Challenger: reconsider (0.74)
- Findings: (1) interface characterization — correctly identifies this as public MCP contract growth, not zero-interface work; (2) existing tests don't cover new fields — expected, TDD pipeline handles this; (3) AC-1 is shape declaration — still mechanically testable by test-writer
- Architect response: Override to APPROVE. Accept framing correction (interface growth acknowledged). No AC refinement needed — exact field names/types are sufficient for test derivation. No consolidation-test gap (existing #1655). No architectural defect found.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Advanced to todo. Behavioral TDD — test-writer will derive TypedDict shape tests and response mapping assertions from AC.

[[2026-05-18T14:08:38+02:00]]
## Test-Writer Notes
- Test file: tests/test_list_sources_1654.py
- Classes: TestFromAC_SourceInfoShape, TestFromAC_SourceInfoOutputSchema, TestFromAC_ListSourcesHealthMapping
- Tests per category: happy 13, edge 4, error 0, boundary 3
- Total: 30 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests | Class |
|----|-------|-------|
| AC-1 TypedDict shape (presence + type) | 10 | TestFromAC_SourceInfoShape |
| AC-1 output schema (5 new fields) | 7 | TestFromAC_SourceInfoOutputSchema |
| AC-2 response mapping (per-field + None/False/empty/multi) | 13 | TestFromAC_ListSourcesHealthMapping |

[[2026-05-18T14:20:17+02:00]]
## Builder Notes
- Implementation: Added 5 health fields to SourceInfo and list_sources response mapping in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Approach: Surgical TypedDict + response-shape expansion only; no API flow changes or additional logic.
- RED verification (quality-runner): tests/test_list_sources_1654.py -> 30 failed before implementation (all TestFromAC_* classes)
- GREEN verification (quality-runner): tests/test_list_sources_1654.py -> 30 passed, 0 failed
- Lint (quality-runner): clean for serve/mcp-knowledge/src/ and tests/test_list_sources_1654.py
- Coverage (quality-runner scoped): module owlbear_mcp_knowledge.server at 28% in scoped run (task tests target a narrow list_sources/SourceInfo contract in a large module)
- Durable module baseline check pre-change: serve/mcp-knowledge/tests/test_list_sources.py -> 17 passed, 1 failed
- Durable module check post-change: serve/mcp-knowledge/tests/test_list_sources.py -> 17 passed, 1 failed (same existing failure: TestFromAC_ListSources::test_calls_list_all_via_asyncio_to_thread)
- Commit: f06a3339 feat: expose source health in list_sources (#1654, builder)
- Evidence summary: AC-1 satisfied by SourceInfo keys/types and schema reflection; AC-2 satisfied by direct field mapping from KnowledgeSource attributes for each returned source.
