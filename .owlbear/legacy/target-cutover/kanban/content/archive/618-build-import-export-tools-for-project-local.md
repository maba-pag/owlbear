---
id: 618
title: Build import/export tools for project-local knowledge snapshots
status: archived
priority: medium
created: 2026-04-05T01:26:23.9739996+02:00
updated: 2026-04-06T08:38:34.3986225+02:00
started: 2026-04-06T08:38:34.3986225+02:00
completed: 2026-04-06T08:38:34.3986225+02:00
tags:
    - scope:mcp
    - phase-2
class: standard
---

## Summary

Add `import_scope` and `export_scope` MCP tools to mcp-knowledge for portable project-local knowledge at `.owlbear/knowledge/knowledge.db`. Import reads a portable SQLite file and ingests data into the global KB under a project-specific scope. Export dumps scoped data to a portable file.

## Context

Research #616 (docs/research/project-local-knowledge-source.md) recommends import/export as the portability mechanism rather than dual-stack live databases. This avoids Qdrant cold-start re-indexing, schema drift, and dual AppContext complexity.

## Acceptance Criteria

- [ ] AC1: `import_scope` tool reads `.owlbear/knowledge/knowledge.db` (or path from `OWLBEAR_LOCAL_KB_PATH`), ingests documents/entities/edges into global DB under `scope="project:{name}"`
- [ ] AC2: `import_scope` detects duplicate documents by content hash and skips them
- [ ] AC3: `export_scope` dumps all data for a given scope to a portable SQLite file
- [ ] AC4: Import path is sandboxed (uses existing `sandbox_path` utility — no path traversal)
- [ ] AC5: Auto-detect: if `.owlbear/knowledge/knowledge.db` exists and no explicit path given, use it

## Dependencies

- Depends on scope param exposure task (search_knowledge needs scopes param to query imported data)

## Notes

- Import opens a *read-only* connection to the source file, reads data, then ingests via existing IngestPipeline
- Export creates a new SQLite file with `init_db()` schema, then copies scoped rows
- Needs decomposition: planner should break into import tool + export tool + auto-detect + tests

[[2026-04-05]] Sun 13:06
## Research
- Research doc: .owlbear/research/import-export-knowledge-snapshots.md
- Sources: 8 studied, 5 high-relevance (.90+)
- Recommendation: Row-level SELECT+INSERT with new UUIDs, FK-ordered inserts, atomic transaction, content hash dedup, embed-not-reextract (confidence: .78)
- Follow-up tasks: none new needed; #618 itself needs planner decomposition per Notes section
- Decision requests: T3 (adds new MCP tools). No DR created (scribe unavailable). #616 research item #3 identified T3 requirement. User should approve before implementation.
- Dependency: #617 (scope param exposure) operationally needed for querying imported data; not a build dependency

## Challenge Results
- Challenger: proceed with amendments (confidence .82 revised to .78)
- Key challenges accepted: (1) FK mapping 6 relationships, ordered inserts required; (2) export preserves source scope, rewrite only on import; (3) LOC ~200-250 not ~120; (4) atomic transaction for import
- Tables: documents, chunks, entities, edges, document_status (IN); knowledge_sources, bookmarks, consolidations (OUT)

## Implementation Notes for Planner
- Insert order: documents, document_status, chunks, entities, edges
- 4 mapping dicts: doc_id_map, chunk_id_map, entity_id_map, edge_id_map
- New module: serve/knowledge/src/owlbear_knowledge/scope_transfer.py (~150 LOC)
- Tool wiring: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (~50 LOC)
- Decompose into: (1) scope_transfer module, (2) import_scope tool, (3) export_scope tool, (4) auto-detect, (5) tests

[[2026-04-05]] Sun 20:43
## AC Refinements (Architect)

**Original AC1** refined: `import_scope(path: str | None, project_name: str)` copies rows from tables `documents`, `document_status`, `chunks`, `entities`, `edges` into global DB under `scope="project:{project_name}"`. Insert order: documents → document_status → chunks → entities → edges (FK constraint order). Entire import wrapped in single transaction (all-or-nothing). New UUIDs generated, 4 mapping dicts maintained.

**Original AC3** refined: `export_scope(scope: str, output_path: str)` creates new SQLite with `init_db()` schema, copies matching rows from `documents`, `document_status`, `chunks`, `entities`, `edges`. Qdrant embeddings excluded (ephemeral — re-embedded on import).

**Original AC5** refined: If `path` is `None` and `.owlbear/knowledge/knowledge.db` exists, use it. If file doesn't exist and no path given, return `error: ` message per MCP convention.

**New AC6:** Source file validated before import: must be valid SQLite with `schema_version` table. Version mismatch or invalid file returns clear `error: ` message.

**MCP convention notes:** Both tools declare `ToolAnnotations`. Error strings use `error: ` prefix per MCP error convention.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Cohesive scope-transfer feature. Decomposition deferred to planner |
| Interface clarity | PASS (after refinement) | AC1/AC3/AC5 tightened: explicit table list, FK insert order, transaction semantics, tool signatures, error behavior |
| Dependency correctness | PASS | #617 needed for querying not building. No build deps |
| Module layering | PASS | scope_transfer.py in knowledge (core), tool wiring in mcp-knowledge. ALLOWED_IMPORTS permits this |
| TDD compliance | PASS | Planner will create paired test tasks |
| KISS/YAGNI | PASS | Row-level SELECT+INSERT is simplest viable approach |
| Premise challenge | PASS | No existing capability for scope-based KB portability |
| Pattern consistency | PASS | Follows MCP conventions: ToolAnnotations, AppContext, error prefix, sandbox_path, init_db, compute_content_hash |
| Security surface | PASS (after AC4+AC6) | Path sandboxing, read-only source, schema validation, parameterized queries |
| Single domain | PASS | Primary: mcp-knowledge. Core module is implementation support, not domain violation |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| import: open source | File not found | FileNotFoundError | AC5 | error message |
| import: open source | Not SQLite | sqlite3.DatabaseError | AC6 | error message |
| import: schema check | Incompatible version | — | AC6 | error message |
| import: FK insert | Integrity violation | IntegrityError | AC1 atomic txn | rollback, no partial state |
| import: embedding | Embedder unavailable | Various | Research notes | Rows imported but unsearchable |
| export: write file | Permission denied | PermissionError | Planner subtask AC | error message |
| export: no data | Empty scope | — | Planner subtask AC | Empty file or error |

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Prior challenge from research phase: proceed with amendments (.82 → .78)
- Architect response: accepted; incorporated FK ordering, LOC estimate, atomic txn into refined AC

### T3 Decision Verification
- DR: .owlbear/decisions/resolved/616-scope-params-import-export.md (approved: true, tier: 3)
- Covers Option C for #617 and #618. T3 requirement satisfied.

### Verdict: APPROVE
### Action: AC refined (AC1 table list + FK order + txn, AC3 explicit tables + Qdrant exclusion, AC5 error behavior, new AC6 schema validation). Advanced to todo for planner decomposition.

[[2026-04-05]] Sun 23:44
## Test-Writer Notes
- Test file: tests/test_scope_transfer_618.py
- Classes: TestFromAC_ScopeTransferModule, TestFromAC_ImportScopeHappyPath, TestFromAC_ImportScopeDedup, TestFromAC_ExportScope, TestFromAC_ImportScopeSandboxing, TestFromAC_ImportScopeAutoDetect, TestFromAC_ImportScopeSchemaValidation, TestFromAC_ImportScopeTransaction, TestFromAC_MCPToolWiring
- Tests per category: happy 11, edge 5, error 11, boundary 4
- Total: 45 tests, all FAIL
- ruff: clean
- AC coverage: AC1 ✓ (9 happy path + transaction), AC2 ✓ (4 dedup), AC3 ✓ (10 export), AC4 ✓ (3 sandbox), AC5 ✓ (4 auto-detect), AC6 ✓ (4 schema validation), MCP wiring ✓ (7)
- Note: Core functions tested as import_scope(src_path, project_name, dest_conn, *, workspace_root=None) and export_scope(scope, output_path, source_conn). Builder may adjust signatures.
- Commit: d833605

[[2026-04-06]] Mon 07:32
## Builder Notes

**Files changed (2):**
- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` (new, ~300 LOC) — core `import_scope` / `export_scope` functions
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — added `conn` field to `AppContext`, imported core functions, registered two MCP tools, added `Path` import, updated `__all__`

**Test results:** 45/45 passed, ruff clean, 96% coverage on scope_transfer.py

**Lint status:** Clean (`ruff check` passes on both files)

**Evidence summary:**
- RED verified: 45 FAILED before implementation  
- GREEN: 45 passed after implementation
- Ruff: 3 PLR/E501 violations fixed (helper function splitting + noqa: PLR0913 + line wrapping)
- Coverage: 96% — 6 uncovered lines are error-path branches (NULL doc_id continue, export exception handler, no-workspace-root-no-path edge case)

**AC coverage:**
- AC1 ✓ — documents/document_status/chunks/entities/edges copied with new UUIDs, FK ordering, atomic transaction (`with dest_conn:` → rollback on failure)
- AC2 ✓ — content-hash dedup: skips document + all child rows if hash already in dest under same scope
- AC3 ✓ — export_scope creates SQLite w/ init_db schema, copies scoped rows
- AC4 ✓ — sandbox_path called when workspace_root provided; PermissionError caught → error: prefix
- AC5 ✓ — path=None: checks OWLBEAR_LOCAL_KB_PATH env var, then auto-detects .owlbear/knowledge/knowledge.db relative to workspace_root; error: when not found
- AC6 ✓ — validates SQLite + schema_version table before opening; non-SQLite / missing table → error: prefix

**Commit:** 109fd00

[[2026-04-06]] Mon 07:57
## Review Evidence

### Tests
pytest: **45 passed, 0 failed, 0 skipped** (run independently via quality-runner)

### Lint
ruff: **clean** — 0 violations on `scope_transfer.py`, `server.py`, `test_scope_transfer_618.py`

### Coverage
`owlbear_knowledge.scope_transfer`: **96%** — 6 uncovered lines are all error/defensive branches (NULL doc_id continue, export exception handler, no-workspace-root-no-path path). All covered by quality-runner.

---

### Pass 1 — CRITICAL Checks

#### 5.0 TestFromAC AC-to-Test Coverage

| AC Line | Mapped Test Class | Would Fail If AC Violated? | Verdict |
|---------|------------------|---------------------------|---------|
| AC1 — 5 tables, FK order, atomic txn, new UUIDs | `TestFromAC_ImportScopeHappyPath` + `TestFromAC_ImportScopeTransaction` | Yes — row count assertions per table; drop-entities forces error + checks zero partial rows | COVERED |
| AC2 — content hash dedup | `TestFromAC_ImportScopeDedup` | Yes — strict count equality on re-import; separate test for child entity cascade | COVERED |
| AC3 — export SQLite with schema, scoped rows only | `TestFromAC_ExportScope` | Yes — scope exclusion verified (`other_count == 0`), `schema_version` table checked | COVERED |
| AC4 — path sandboxed via sandbox_path | `TestFromAC_ImportScopeSandboxing` | Yes — traversal + null-byte → `error:` prefix; valid path → no error | COVERED |
| AC5 — auto-detect + env var + error | `TestFromAC_ImportScopeAutoDetect` | Yes — row count + non-error for hits; `error:` prefix for miss | COVERED |
| AC6 — schema validation (schema_version table) | `TestFromAC_ImportScopeSchemaValidation` | Yes — non-SQLite, no-schema_version, missing file all return `error:` | COVERED |

No MISSING entries. No LAX entries.

#### 5.1 Security
- **Injection**: `export_scope` f-string SQL uses hardcoded `_TRANSFER_TABLES` (not user input) for table/column names; `scope` parameterized with `?`. Safe. `# noqa: S608` suppressions appropriate.
- **Path traversal**: `sandbox_path` enforces null-byte rejection and `is_relative_to` check. `import_scope` MCP tool hardcodes `workspace_root=Path.cwd()`, ensuring sandbox is always active in production.
- **Hardcoded secrets**: None found.
- **Deserialization**: No pickle/yaml/eval.
- **Input validation**: Path and project_name validated at MCP boundary; schema validated before open.
- **Secret leakage**: Error messages show file paths (acceptable for a local CLI tool).

**No OWASP Top 10 issues found.**

#### 5.2 TestFromAC Comparison
No `TestFromAC_*` modifications by builder detected. All 9 original test classes preserved verbatim. Builder only added implementation code; no test deletions, weakening, or skip/xfail additions.

#### 5.3 Test Quality — ADEQUATE
- Assertion specificity: STRONG — count comparisons, exact string prefix checks, scope isolation verified per-row.
- Error-path coverage: STRONG — every AC has at least one error-path test.
- Mutation resistance: ADEQUATE — count assertions (`== 1`, `== 0`) and `startswith("error: ")` would catch most mutations. `assert count >= 1` forms are present (lower bound), but compensated by explicit dedup tests.
- Test independence: **One concern** — `test_import_scope_tool_returns_error_prefix_when_no_file` in `TestFromAC_MCPToolWiring` tests the MCP wrapper using real `Path.cwd()` (hardcoded in MCP tool), creating an implicit dep on `.owlbear/knowledge/knowledge.db` not existing at CWD and `OWLBEAR_LOCAL_KB_PATH` not being set. File confirmed absent; test currently passes. Informational.
- Test names: STRONG — all descriptive.

Overall: **ADEQUATE** (no WEAK dimension).

#### 5.4 Data Safety
No LLM output persistence. Import wrapped in atomic transaction (`with dest_conn:`). No unbounded resource operations.

#### 5.5 Implementation-aware Test Gap Analysis
96% coverage. 6 uncovered lines explicitly identified by builder:
1. `continue` guard for NULL `doc_id` in `_insert_document_statuses` — defensive, no test needed
2. `except Exception as exc` in `export_scope` — error handler not tested
3. `"error: no source path given and no workspace root for auto-detect"` — exercised indirectly by env-var test but not as isolated unit test

None constitute a significant code path gap; all are defensive error-handling branches.

#### 5.7 Builder Process Quality
Single builder notes section. No loop patterns. Approach consistent with planner spec.

---

### Pass 2 — Informational

- **6.1** Source file opened as read-write (`sqlite3.connect`) in both `_validate_source` and `import_scope`. Notes spec said "read-only connection". Implementation only issues SELECT statements, so no functional issue. Consider `?mode=ro` URI in a follow-up.
- **6.1** `edge_id_map` noted in architect notes as the 4th mapping dict, but implementation generates edge UUIDs inline in `_insert_edges`. Functionally equivalent — edges have no FK children. Not a defect.
- **6.3** `test_import_scope_tool_returns_error_prefix_when_no_file` could be made environment-independent by patching `Path.cwd` in the test.

---

### AC Compliance Table

| AC | Evidence | Test | Status |
|----|----------|------|--------|
| AC1 — import 5 tables, FK order, atomic txn | `_do_import`: inserts in FK order, `with dest_conn:`, new UUIDs via `uuid4()` | `TestFromAC_ImportScopeHappyPath`, `TestFromAC_ImportScopeTransaction` | PASS |
| AC2 — content hash dedup | `existing_hashes` set; `skipped_doc_ids` cascades to chunks/entities/edges | `TestFromAC_ImportScopeDedup` | PASS |
| AC3 — export to SQLite | `export_scope` calls `init_db()`, WHERE scope=? filter, no Qdrant fields | `TestFromAC_ExportScope` | PASS |
| AC4 — sandbox_path | `sandbox_path(workspace_root, resolved_path)` when workspace_root set; PermissionError → error: | `TestFromAC_ImportScopeSandboxing` | PASS |
| AC5 — auto-detect | Env var → auto-detect → error; `_AUTO_DETECT_RELATIVE` path construction | `TestFromAC_ImportScopeAutoDetect` | PASS |
| AC6 — schema validation | `_validate_source`: file-exists + sqlite3 open + schema_version query | `TestFromAC_ImportScopeSchemaValidation` | PASS |

---

### Deductions
- 0 deductions (no FAIL conditions triggered)

### Verdict
**Confidence: .93 → PASS**

[[2026-04-06]] Mon 08:06
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | Two new MCP tools (`import_scope`, `export_scope`) added to mcp-knowledge. `copilot-instructions.md` is structural-only (5-line intro, no tool tables) — no update needed there. `serve/knowledge/README.md` module overview updated (see below). |
| 2 | Module docstrings | Yes | Verified | `scope_transfer.py`: module docstring ✓, `import_scope` docstring ✓, `export_scope` docstring ✓, `_validate_source` docstring ✓, `_do_import` docstring ✓. Private helpers (`_insert_*`) are unexported — no docstring required. MCP server tools `import_scope`/`export_scope` have inline docstrings ✓. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains `## Import/Export Knowledge Snapshots (Task #618)` section with 3 entries (Python sqlite3 docs, SQLite ATTACH, SQLite Backup API). No update needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified; changes are MCP tool registrations only. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/import-export-knowledge-snapshots.md` exists and is linked from task body (`[[2026-04-05]]` section). No follow-up tasks required per research conclusion. |

### Files Updated
- `serve/knowledge/README.md` — added `scope_transfer` row to Utilities table; updated module count from 22 to 23 (commit 46ee79d)

### Scratch Files Cleaned
- None (no `618-*` scratch files found)

[[2026-04-06]] Mon 08:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — 5 tables, FK order, atomic txn, new UUIDs | scope_transfer.py: _TRANSFER_TABLES tuple, _do_import with `with dest_conn:`, uuid4() calls; TestFromAC_ImportScopeHappyPath + TestFromAC_ImportScopeTransaction (45/45 pass) | PASS |
| AC2 — content hash dedup | scope_transfer.py:L185-L220 existing_hashes + skipped_doc_ids cascade; TestFromAC_ImportScopeDedup | PASS |
| AC3 — export to SQLite | scope_transfer.py: export_scope with init_db + scoped WHERE; TestFromAC_ExportScope | PASS |
| AC4 — sandbox_path | scope_transfer.py:L296-L300 sandbox_path call; TestFromAC_ImportScopeSandboxing | PASS |
| AC5 — auto-detect + env var | scope_transfer.py:L276-L294 env var then auto-detect then error; TestFromAC_ImportScopeAutoDetect | PASS |
| AC6 — schema validation | scope_transfer.py:L32-L51 _validate_source; TestFromAC_ImportScopeSchemaValidation | PASS |

### Test Results
- pytest (task-scoped): 45 passed, 0 failed, 0 skipped
- pytest (full suite): 3058 passed, 473 failed, 18 skipped — zero failures from #618 tests; all 473 failures are pre-existing from other tasks (voice scaffolding, session hooks, skill frontmatter, etc.)
- ruff: clean on all 3 deliverable files

### Reviewer Evidence
Detailed PASS verdict with AC-to-test coverage table, security review (no OWASP issues), test quality assessment (ADEQUATE, no WEAK dimensions), implementation-aware gap analysis. Trusted — spot-check confirmed.

### Commits Verified
| Commit | Type | Files | Agent |
|--------|------|-------|-------|
| d833605 | test | tests/test_scope_transfer_618.py | test-writer |
| 109fd00 | feat | scope_transfer.py, server.py | builder |
| 46ee79d | docs | serve/knowledge/README.md | doc-writer |

### Architect Quality: 4/5
AC was well-structured after refinement. FK ordering, transaction semantics, table list, and error behavior explicitly specified. Minor: AC1 original was vague until architect refined it. Minor gap: "read-only connection" spec not enforced (builder uses r/w but only SELECTs). Overall adequate — builder didn't need significant improvisation.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 6 PASS) — 0 deduction
- Lint violations: 0 — 0 deduction
- AC quality score 4 (above 3) — 0 deduction
- Reviewer evidence section: present, detailed, PASS — 0 deduction
- Full-suite failures in task scope: 0 — 0 deduction

### Confidence: .98
### Action: archive
