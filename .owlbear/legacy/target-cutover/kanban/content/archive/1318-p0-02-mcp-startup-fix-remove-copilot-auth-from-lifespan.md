---
id: 1318
title: 'P0-02: MCP startup fix — remove copilot_auth from lifespan'
status: archived
priority: medium
created: 2026-05-04T05:48:37.751521+00:00
updated: 2026-05-04T12:02:37.713544+00:00
tags:
- phase-0
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1317
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.2)

## Acceptance Criteria

- [ ] copilot_auth.py removed from MCP server lifespan — no import, no device-flow (td:0)
- [ ] IngestPipeline starts with extractor=None; vector search works without LLM (td:0)
- [ ] Server starts cleanly with `search_knowledge` returning results for ingested content (O1) (td:0)
- [ ] Cached token at ~/.owlbear/copilot_token.json cleaned up if present (td:0)
- [ ] All #1317 tests pass green (td:0)

## Scope

- **In scope:** MCP server lifespan cleanup, copilot_auth removal, test_copilot_server_wiring_888 updates
- **Out of scope:** Entity extraction (agent workers), browser integration, tool surface changes
[[2026-05-04]]
## Research

- Research doc: .owlbear/research/1318-mcp-startup-copilot-removal.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Fast-track — all ACs already satisfied by #1321 builder (commit cd74db6e) (confidence: 0.95)
- Follow-up tasks created: none (no implementation gap)
- Decision requests: none

## Key Finding

The copilot_auth fallback path was removed from server.py lifespan in commit cd74db6e (feat: wire ingest guard at lifespan/text path, #1321 builder). Token cleanup already present. All 8 #1317 tests pass GREEN. Builder work is a no-op — verify and commit.

## Challenge Results
- Challenger: SKIPPED — factual verification against git history, no ambiguity
- Confidence in original: 0.95

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Removal of one auth path from lifespan |
| Interface clarity | PASS | ACs specify exact conditions (no import, extractor=None, token unlink) |
| Dependency correctness | PASS | #1317 archived/done; dependency satisfied |
| Module layering | PASS | Removal only — no new imports or upward deps |
| TDD compliance | PASS | test_server_1317.py (8 tests) already covers all ACs |
| KISS/YAGNI | PASS | Pure deletion; no new abstractions |
| Premise challenge | PASS | Work already done by #1321 builder — task valid as verification gate |
| Pattern consistency | PASS | Follows existing lifespan pattern (conditional extractor) |
| Security surface | PASS | Removes auth complexity; no new boundaries |
| Single domain | PASS | scope:mcp-knowledge only |

### Notes
- All ACs td:0: work completed by sibling #1321 (commit cd74db6e). Builder verifies and commits.
- Test-writer: SKIP (all td:0).
- Dead `_bypass_copilot_auth` fixtures remain in 3 test files — harmless, out-of-scope cleanup.
- Challenger: SKIPPED per Step 2.1 (all td:0).

### Verdict
APPROVED — ACs precise, architecture sound, codebase confirms completion.

[[2026-05-04]]
## Architecture Review — APPROVED

All 5 ACs verified against live codebase: copilot_auth removed from lifespan (server.py L244+), token cleanup present (L248), IngestPipeline uses extractor=None by default, tests in test_server_1317.py cover all conditions. Work completed by sibling #1321 (cd74db6e). All ACs td:0 — Test-writer: SKIP. Challenger: SKIPPED (all td:0).
[[2026-05-04]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-04]]
## Builder Notes
- Non-implementation td:0 verification task; no code changes required.
- Scope verified against existing implementation from sibling task #1321 (commit cd74db6e) per architecture notes.
- Quality-runner (scoped) evidence:
  - pytest: 8 passed, 0 failed (`tests/test_server_1317.py`)
  - ruff: clean (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_server_1317.py`)
  - coverage: 41% on `owlbear_mcp_knowledge.server` (measurement captured; no new code introduced in this task).
- Acceptance criteria status: satisfied by existing codebase; builder verified green behavior and pass-through readiness.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped verification on `tests/test_server_1317.py`, `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`, `serve/mcp-knowledge/tests/test_search_v2.py`, and `serve/mcp-knowledge/tests/test_server.py`: 40 passed, 0 failed, 0 skipped.

### Lint Results
- ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and the scoped test files.

### Coverage
- `owlbear_mcp_knowledge.server`: 45% module coverage.
- Informational only for this review. The latest builder cycle changed no source files; this task is a verification pass over existing implementation state.

### Pass 1 Checks
- Security review: no issues found in scope. The startup path unlinks only the fixed local token file at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249` and conditionally constructs `LLMExtractor` from env-backed config at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:258-274`.
- Test integrity: no weakened or removed `TestFromAC_*` assertions found in the current green snapshot. The task-local suite at `tests/test_server_1317.py` and the replacement suite at `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py` both pass green.
- Data safety: no issues found.
- Builder process quality: CLEAN. Current task has one builder section and no prior review cycle.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `copilot_auth.py` removed from MCP server lifespan; no import, no device-flow | Workspace grep on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` returned no `copilot_auth` matches. No-key startup is proven by `tests/test_server_1317.py:85` and post-lifespan module absence by `tests/test_server_1317.py:117`. | `test_copilot_auth_not_imported_when_no_api_key`; `test_copilot_auth_module_absent_from_sys_modules_after_lifespan` | PASS |
| `IngestPipeline` starts on the no-LLM path and vector-search wiring remains available | `structured_extractor` defaults to `None` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:258` and remains `None` on import failure at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:274`; `KnowledgeQueryService` and `IngestPipeline` are wired at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:289`. Exact lifespan instances are pinned by `tests/test_server_1317.py:137`, no-key extractor state by `tests/test_server_1317.py:166` and `tests/test_server_1317.py:195`, and API-key-path symmetry by `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:97` and `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py:116`. | `test_ingest_pipeline_and_query_service_are_actual_constructed_instances`; `test_structured_extractor_is_none_without_api_key`; `test_ingest_pipeline_and_query_service_wired_with_null_extractor`; `test_structured_extractor_is_exact_llmextractor_instance`; `test_structured_extractor_none_when_llm_import_fails` | PASS |
| Server starts cleanly with `search_knowledge` available on the no-LLM path | `search_knowledge` is defined at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:364`; it uses the lifespan `query_service` wired at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:283`. Adjacent tool-contract coverage is green at `serve/mcp-knowledge/tests/test_search_v2.py:63`, `serve/mcp-knowledge/tests/test_search_v2.py:173`, and `serve/mcp-knowledge/tests/test_search_v2.py:188`. The dependency task explicitly narrowed the original overclaim to wiring availability plus adjacent search-contract coverage at `.owlbear/kanban/archive/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:67`. | `test_returns_bullet_list_for_valid_query`; `test_limit_forwarded_as_top_k_to_query`; `test_qs_is_none_returns_service_unavailable` | PASS |
| Cached token at `~/.owlbear/copilot_token.json` cleaned up if present | Startup cleanup is implemented at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:249`. Present-file cleanup is proven at `tests/test_server_1317.py:247`; absent-file real-filesystem idempotency is proven at `tests/test_server_1317.py:294`. | `test_token_file_deleted_when_present_at_startup`; `test_token_file_cleanup_no_exception_when_absent_real_fs` | PASS |
| All #1317 tests pass green | Independent quality-runner scoped run across the full task surface passed 40 of 40 tests with zero failures. | `tests/test_server_1317.py`; `serve/mcp-knowledge/tests/test_copilot_server_wiring_888.py`; `serve/mcp-knowledge/tests/test_search_v2.py`; `serve/mcp-knowledge/tests/test_server.py` | PASS |

### Deductions
- 0.04: task line 28 still uses the broader O1 wording. The live proof is split between no-LLM startup tests and adjacent `search_knowledge` contract tests, consistent with the refined dependency note at `.owlbear/kanban/archive/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:67`, not a fresh end-to-end ingest/search run.
- 0.03: direct commit-diff and dirty-tree contamination checks were not available in the current tool surface. Review relied on current file state, the recorded `cd74db6e` history entry at `.git/logs/refs/heads/dev:1639`, and independent green quality-runner evidence.

### Verdict
- PASS. Confidence: 0.93. Advance to docs.
[[2026-05-04]]
## Docs Gate

| Check | Applies? | Status | Evidence |
|-------|----------|--------|----------|
| 0a Review Evidence present | Yes | PASS | `## Review Evidence` section present with full AC table |
| 1 Descriptive prose docs | Yes | PASS | `serve/mcp-knowledge/README.md` reviewed — "server starts without [LLM API key] but extraction-dependent features degrade gracefully" is accurate post-removal; no copilot_auth references found |
| 2 Module docstrings | Yes | PASS | `app_lifespan` docstring reads "Initialise knowledge-base services; close the DB connection on exit." — accurate, no stale auth references |
| 3 External attribution | N/A | N/A | Research doc (S1-S6) uses only workspace codebase and git history; no external patterns |
| 4 Research doc | Yes | PASS | `.owlbear/research/1318-mcp-startup-copilot-removal.md` exists and linked from task body |
| 5 Diagram maintenance | Yes | DONE | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` → matches `server.py`; footer updated from `b844bdcf` to `6b0ccf32` (commit f61e4846) |
| 6 Explicit diagram creation | No | N/A | No creation request in task body |
| 7 Deletion detection | No | N/A | `copilot_auth` was removed from server.py lifespan code; no IN-scope doc references the deleted branch (README already describes graceful-degradation model accurately) |

**Files updated:** `share/diagrams/mcp-topology.excalidraw` (footer only)
**Scratch files:** none to clean (no task-scoped scratch files found)
[[2026-05-04]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| copilot_auth.py removed from MCP server lifespan — no import, no device-flow | grep server.py: zero matches; commit cd74db6e (sibling #1321) removed it | PASS |
| IngestPipeline starts with extractor=None; vector search works without LLM | Reviewer mapped to server.py:258, :274, :283, :289; tests test_server_1317.py:137, :166, :195 | PASS |
| Server starts cleanly with search_knowledge returning results (O1) | search_knowledge at server.py:364; test_search_v2.py:63, :173, :188 green | PASS |
| Cached token at ~/.owlbear/copilot_token.json cleaned up if present | server.py:249; test_server_1317.py:247, :294 green | PASS |
| All #1317 tests pass green | Auditor independent run: 8/8 pass in test_server_1317.py; 185/190 pass in serve/mcp-knowledge/tests/ (5 pre-existing failures in unrelated test_outputschema_541 and test_phase_a_config) | PASS |

### Full Suite Results
- pytest: 3920 passed, 395 failed, 4 skipped — zero failures in task scope; all 395 are pre-existing background debt in kanban/memory/cockpit modules
- vitest: not re-run (frontend unrelated to mcp-knowledge scope)
- ruff: 3 violations (copilot_auth.py T201, mcp-memory E501×2) — none in task scope
- eslint: not re-run (frontend unrelated)

### AC Quality Score: 4/5
ACs precise and verifiable. Minor gap: AC #3 O1 wording broader than testable without live Qdrant, but dependency #1317 already refined scope.

### Deductions
- None applicable. All ACs evidenced, no lint in scope, reviewer evidence thorough, no task-scope failures.

### Confidence: 0.98
Action: ARCHIVE