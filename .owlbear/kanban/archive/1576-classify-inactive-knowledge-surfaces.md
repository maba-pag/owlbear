---
id: 1576
title: Classify inactive knowledge surfaces
status: archived
priority: important
created: 2026-05-14T18:47:54.230692+00:00
updated: 2026-05-15T18:25:15.441641+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
  - research
parent:
depends_on:
  - 1556
  - 1557
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Context:
Knowledge module audit found that the active MCP surface is intentionally narrow, but the codebase still contains several older or inactive knowledge paths: bookmark workflows, legacy consolidation, scope transfer implementation/stubs, duplicate inter-doc builder concepts, inactive plain functions that used to be tools, Copilot token utilities, and docs/handbook text that may describe outdated result shapes or operational defaults.

This is not a runtime blocker. It should run after the core source identity and manual enrichment persistence repairs so cleanup does not destabilize activation work.

Objective:
Produce a complete classification inventory of inactive knowledge surfaces, verify follow-up tasks capture all classified actions, and confirm user-facing docs are current.

Proof bundle: skip

Acceptance Criteria:
- [ ] Classification inventory in `.owlbear/research/classify-inactive-knowledge-surfaces.md` covers: inactive server.py functions (11), library modules (9), schema tables (2), and package exports/optional deps — each classified as exactly one of keep, retire, or document-as-stub.
- [ ] Follow-up tasks #1582 (retire dead code — functions, modules, imports, exports, optional dep), #1583 (drop bookmarks/consolidations schema tables), and #1584 (label deferred stubs) exist in the board and their scope matches the classification matrix.
- [ ] Deferred stubs `llm_extractor.py`, `inter_doc_graph_builder.py`, and `list_entities` function are classified as document-as-stub, not retire — preserved for future work (#875, StructuredExtractor dependency).
- [ ] `h-knowledge-ops` handbook reviewed and confirms it documents only the 8 active MCP tools — no updates needed.
- [ ] No user-facing knowledge docs or skills reference inactive tools (bookmark, scope transfer, consolidate) as operational.

Out of scope:
- Source identity repair (#1556).
- Manual enrichment graph persistence repair (#1557).
- New source lifecycle design (#1558).
- Full KB ingestion.
- Actual code deletion or schema migration (follow-ups #1582, #1583).
- Stub labeling implementation (follow-up #1584).

---

Audit refinement — inactive surfaces must be checked before re-exposure:
Several plain async functions remain in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` but are not active MCP tools. Some of them still use `asyncio.to_thread(...)` around SQLite-backed stores or connection work (`list_entities`, bookmark helpers, scope sync/import/export paths). They should not be re-exposed as tools until thread ownership and return contracts are reviewed.

Audit refinement — scope transfer is lossy and should be retire-by-default:
`scope_transfer.py` copies only `documents`, `document_status`, `chunks`, `entities`, and `edges`, and its import helpers omit current schema fields such as `documents.source_id`, `entities.importance`, `edges.document_id`, chunk enrichment/consolidation fields, and status `error`. It also omits source/bookmark/source-page/consolidation tables entirely.

Audit refinement — bookmark and legacy consolidation surfaces are retire-or-redesign:
Bookmark code remains present but inactive; `bookmarks.content_hash` exists in schema/model while the current bookmark pipeline/store do not populate or use it. Legacy consolidation is also inactive, but MCP lifespan wires `ConsolidationService(conn, make_text_completion_fn())` with a completion function that returns an empty string.

## Research

### Key Findings
Inventoried 11 inactive functions in server.py and 6+ inactive library modules. Classified each as:
- **Retire (9 functions, 5 modules):** bookmark_source, list_bookmarks, update_bookmark_tags, import_scope, export_scope, sync_from_global, sync_to_global, consolidate_knowledge + bookmark_pipeline.py, bookmark_store.py, consolidation.py, copilot_auth.py, scope_transfer.py
- **Document-as-stub (3):** list_entities (pending thread-safety), llm_extractor.py (future #875), inter_doc_graph_builder.py (needs StructuredExtractor)
- **Keep (4):** knowledge_stats helpers, benchmark.py, content_safety.py

### Trade-off Matrix
See `.owlbear/research/classify-inactive-knowledge-surfaces.md` §3.

### Follow-up Tasks
- #1582 — Retire dead code (functions + modules + imports)
- #1583 — Drop bookmarks/consolidations schema tables
- #1584 — Label deferred stubs

### Attribution
h-knowledge-ops handbook already correct — no doc updates needed.
2026-05-15T16:40:16+00:00
## Architecture Review

**Verdict:** APPROVED (after REFINE) — AC rewritten, proof bundle set, pass-through tag added.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (orig): Inventory and classify | Vague — no artifact path, no enumeration of surface categories, no verification method | Rewritten: names artifact path, counts, classification enum, verification by inspection |
| AC-2 (orig): Preserve deferred stubs | Implicit quantifier — "intentionally deferred" not enumerated | Rewritten: names the 3 specific stubs and their future-work references |
| AC-3 (orig): Remove or label dead paths | Conflates classification (this task) with implementation (follow-ups #1582/#1584) | Replaced: follow-up task existence + scope-match verification |
| AC-4 (orig): Update docs | Reasonable but lacked verification target | Rewritten: names specific handbook, states 8-tool count, verification by inspection |
| AC-5 (orig): Don't change enrichment model | Guard rail, not independently verifiable | Replaced: no inactive tools referenced as operational in docs/skills |

### Architecture Notes

- Task is a classification/research gate — produces no testable Python code. All code changes delegated to follow-ups #1582 (retire code), #1583 (drop tables), #1584 (label stubs).
- Dependencies #1556 and #1557 both archived/completed — gate satisfied.
- Research document `.owlbear/research/classify-inactive-knowledge-surfaces.md` is thorough: covers 11 inactive server.py functions, 9 library modules, 2 schema tables, package exports, and optional deps.
- Classifications verified against codebase: all retire-targets have zero active callers (confirmed via Explore subagent). Stub classifications reference real future work (#875, StructuredExtractor).
- `h-knowledge-ops` handbook documents only the 8 active MCP tools — no stale references found.

### Dependency Analysis

- #1556 (source identity): archived/completed ✓
- #1557 (enrichment persistence): archived/completed ✓
- Follow-ups #1582, #1583, #1584 depend on #1576 — will unblock on completion.

### Proof Bundle

`skip` — classification/research output only, no testable code changes.

### Challenge

SKIPPED — proof bundle is `skip`.
2026-05-15T17:02:46+00:00
## Test-Writer Notes
- Non-implementation task (tagged `research`, `type:cleanup`) — no tests applicable.
- Proof bundle: `skip` — classification/research output only, no testable Python interfaces.
- Passing through to builder.
2026-05-15T17:09:18+00:00
## Builder Notes
- Implementation: no code changes (classification/research pass-through task).
- Proof routing: `Proof bundle: skip` + Test-Writer Notes explicitly marked non-implementation.
- AC evidence:
  - Inventory artifact exists and covers required categories/counts in `.owlbear/research/classify-inactive-knowledge-surfaces.md`:
    - inactive `server.py` functions: 11 (matrix §3.1)
    - library modules: 9 (matrix §3.2)
    - schema tables: 2 (matrix §3.3)
    - package exports + optional deps: included (matrix §3.4)
    - each item assigned exactly one class: keep / retire / document-as-stub.
  - Follow-up tasks verified and scope-aligned:
    - #1582: retire dead code/functions/modules/imports/exports/optional dep
    - #1583: drop bookmarks + consolidations schema tables
    - #1584: label deferred stubs
  - Deferred stubs explicitly classified as document-as-stub:
    - `llm_extractor.py`
    - `inter_doc_graph_builder.py`
    - `list_entities` function
  - `h-knowledge-ops` reviewed: documents only the 8 active MCP tools; inactive tools are not presented as operational.
  - User-facing guidance check: no docs/skills found that describe bookmark/scope-transfer/consolidate as active MCP operations.
- Tests/lint: not applicable for this task (`Proof bundle: skip`, no implementation changes).
- Commit: not required (no files modified).
2026-05-15T17:29:21+00:00
## Review Evidence
- Verdict: FAIL
- FAIL signal: FAIL #1576 -> in-progress | AC-5 is not satisfied; serve/knowledge/README still presents inactive bookmark/scope/consolidation surfaces as current public API, contradicting the research doc and builder note.
- AC coverage summary:
  - AC-1: PASS by inspection. The classification matrix covers 11 server.py functions, 9 library modules, 2 schema tables, and package exports/optional deps in `.owlbear/research/classify-inactive-knowledge-surfaces.md`.
  - AC-2: PASS by inspection. Follow-up tasks #1582, #1583, and #1584 exist and their scopes match the matrix.
  - AC-3: PASS by inspection. `llm_extractor.py`, `inter_doc_graph_builder.py`, and `list_entities` are classified as document-as-stub.
  - AC-4: PASS by inspection. `share/skills/h-knowledge-ops/SKILL.md` documents only the 8 active MCP tools.
  - AC-5: FAIL. The task AC requires no user-facing knowledge docs or skills to reference inactive bookmark/scope-transfer/consolidation surfaces as operational, but `serve/knowledge/README.md` still advertises `BookmarkStore`, `ConsolidationService`, `import_scope`, and `export_scope` as key exports and states that all 23+ public modules are importable.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-5 | The proof packet claims the user-facing docs are current, but the knowledge package README still presents inactive bookmark/scope/consolidation surfaces as current public API. This contradicts both the builder note and the research document's "no doc changes needed" conclusion, so the task cannot pass. | AC: `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:38`; contradictory builder note: `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:138`; contradictory research claim: `.owlbear/research/classify-inactive-knowledge-surfaces.md:74`; stale doc surface: `serve/knowledge/README.md:50`, `serve/knowledge/README.md:55`, `serve/knowledge/README.md:57` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update the user-facing knowledge package README so it no longer presents retired bookmark/scope/consolidation surfaces as current public exports, or explicitly mark them as inactive/deferred if that is the intended public contract. | `serve/knowledge/README.md` | `serve/knowledge/README.md:50`, `serve/knowledge/README.md:55`, `serve/knowledge/README.md:57` |
| 2 | builder | Correct the task proof packet after the doc surface is fixed: amend the research/task notes so they no longer claim "no doc changes needed" or "no docs/skills found" while contradictory README content exists. | `.owlbear/research/classify-inactive-knowledge-surfaces.md`, `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md` | `.owlbear/research/classify-inactive-knowledge-surfaces.md:74`, `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:138` |

## Observations
- The rest of the classification work appears sound on direct inspection: the research matrix matches the current code surface for the 11 non-tool server functions, 9 library modules, 2 schema tables, the retired exports in `serve/knowledge/src/owlbear_knowledge/__init__.py`, and the `copilot` optional dependency in `serve/knowledge/pyproject.toml`.
- Follow-up tasks #1582, #1583, and #1584 are scoped consistently with the matrix, and `share/skills/h-knowledge-ops/SKILL.md` plus `serve/mcp-knowledge/README.md` correctly reflect the 8 active MCP tools.
2026-05-15T17:36:57+00:00
## Builder Notes
- Scope: resolved reviewer finding on AC-5 by correcting user-facing knowledge documentation and proof narrative consistency.
- Files changed:
  - `serve/knowledge/README.md`
  - `.owlbear/research/classify-inactive-knowledge-surfaces.md`
- Fixes applied:
  - Removed inactive surfaces from operational `Module groups` exports in package README (`BookmarkStore`, `ConsolidationService`, `import_scope`, `export_scope`).
  - Replaced broad operational claim with explicit statement that bookmark/scope-transfer/consolidation surfaces are not part of the operational contract.
  - Updated research §3.5 to remove the stale "No doc changes needed" claim and record the README correction.
- Quality evidence:
  - quality-runner (scoped): `test_paths=[]`, `lint_paths=["serve/knowledge/README.md", ".owlbear/research/classify-inactive-knowledge-surfaces.md"]`
  - Result: tests passed `0`, failed `none`; lint `clean: true`, violations `none`; markdownlint exit `0`.
- Commit:
  - `51ac41f9` — `docs: correct inactive knowledge surface contract notes (#1576, builder)`
- AC mapping:
  - AC-5 now satisfied: user-facing knowledge docs/skills no longer present bookmark/scope-transfer/consolidation as operational surfaces.
  - Prior AC-1..AC-4 remain unchanged and previously evidenced.
2026-05-15T17:47:47+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1576 -> docs | AC mapped to code and evidence sufficient.
- Builder proof check: Proof bundle is `skip`, and the builder supplied scoped quality-runner lint evidence for the only edited files with clean results at `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:176-177`.
- AC evidence map:

| AC Line | Code / Artifact Evidence | Proof Check | Status |
|---|---|---|---|
| AC-1 | `.owlbear/research/classify-inactive-knowledge-surfaces.md:26`, `:42`, `:56`, `:63` contain the classification matrix sections for inactive server functions, library modules, schema tables, and package exports / optional deps. Direct inspection of those sections shows the required inventory categories and exact-one-of classifications. | Artifact exists and matches the task contract at `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:34`. | PASS |
| AC-2 | Follow-up tasks exist and their scopes align with the matrix: `.owlbear/kanban/tasks/1582-retire-bookmark-scope-consolidation-dead-code-from-knowledge-module.md:26`, `:30`, `:32`; `.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md:26-27`; `.owlbear/kanban/tasks/1584-label-deferred-knowledge-stubs-llm-extractor-inter-doc-graph-builder-list-entiti.md:27-29`. | Task scopes match the parent AC at `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:35`. | PASS |
| AC-3 | Deferred stub classifications are explicit in `.owlbear/research/classify-inactive-knowledge-surfaces.md:30`, `:50`, and `:51` for `list_entities`, `llm_extractor.py`, and `inter_doc_graph_builder.py`. | These match the preserve-as-stub contract at `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:36`. | PASS |
| AC-4 | `share/skills/h-knowledge-ops/SKILL.md:13`, `:25`, `:38`, `:48`, `:58`, `:66`, `:84`, and `:96` define the eight active MCP tool entries; `share/skills/h-knowledge-ops/SKILL.md:129` states only documented tools are agent-callable. | Handbook remains current and satisfies `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:37`. | PASS |
| AC-5 | `serve/knowledge/README.md:48-55` now lists only active module groups, and `serve/knowledge/README.md:57-59` explicitly says inactive bookmark, scope-transfer, and consolidation surfaces are not part of the operational contract. The research note now records that correction at `.owlbear/research/classify-inactive-knowledge-surfaces.md:74-77`. Targeted searches found no inactive operational references in `serve/mcp-knowledge/README.md` or `share/skills/h-knowledge-ops/SKILL.md`. | This resolves the prior review finding and satisfies `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:38`. | PASS |

- Blocking findings: none.

## Observations
- This remains a documentation / research classification task with no executable code delta. Builder evidence was sufficient and internally consistent, so no independent quality-runner rerun was needed.
- The earlier contradiction between the knowledge package README and the proof narrative is resolved by the doc fix in commit `51ac41f9` and the updated research note at `.owlbear/kanban/tasks/1576-classify-inactive-knowledge-surfaces.md:179-181`.
2026-05-15T17:56:38+00:00
## Docs Gate

**Verdict:** PASS

**Item 1 — README Verification:** PASS. `serve/knowledge/README.md` module groups table contains only active exports. Retired symbols (`BookmarkStore`, `ConsolidationService`, `import_scope`, `export_scope`) are absent (grep: zero matches). Explicit disclaimer added confirming inactive surfaces are not part of the operational contract. LLM editorial: coherent, no contradictions.

**Item 2 — External Attribution:** N/A — classification/research task used internal codebase sources only.

**Item 3 — Research Doc:** PASS — `.owlbear/research/classify-inactive-knowledge-surfaces.md` exists, complete, and linked from task body. §3.5 updated to record the README correction.

**Item 4 — Deletion Detection:** N/A — no source files deleted in this task; deletions delegated to follow-ups #1582, #1583, #1584.

**Scratch cleanup:** N/A — no `.owlbear/scratch/1576-*` files found.

Files updated: none (builder's `serve/knowledge/README.md` edit in commit `51ac41f9` is correct and complete; no further doc edits required).
2026-05-15T18:25:15+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 6423 passed (4602 Python + 1821 frontend), 258 failed (pre-existing background failures), ruff clean\n- Task #1576 changed only 2 documentation files (serve/knowledge/README.md, .owlbear/research/classify-inactive-knowledge-surfaces.md). No code changes; zero regressions attributable to this task.\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (changed files are knowledge domain docs; research artifact and follow-up tasks all within knowledge scope)\n- purpose match: PASS (classification inventory produced, 3 follow-up tasks created matching matrix, README doc surface corrected after reviewer finding)\n- extraneous scope: none\n- research task verification: PASS (doc exists at .owlbear/research/classify-inactive-knowledge-surfaces.md; follow-ups #1582, #1583, #1584 at research status with dep on #1576)\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC was rewritten from vague originals to specific, verifiable lines naming artifact paths, counts, classification enum, exact stub identifiers, and handbook tool count. AC-5 was clear enough to catch the README gap on review. Minor gap: AC-5 scope (\"user-facing knowledge docs\") could have explicitly named serve/knowledge/README.md to prevent the initial miss, but the AC was sufficient for the reviewer to catch it.\n\n### Commit Integrity\n- upstream commit presence: PASS (9f35f7d8 \"docs: correct inactive knowledge surface contract notes (#1576, builder)\" touches only 2 doc files)\n- commit format: correct (type: docs, task ref #1576, agent attribution)\n- kanban commit packaging: pending (Step 6)\n\n### Deduction Breakdown\n- Intent mismatch: 0\n- Evidence integrity: 0\n- Lint violations: 0\n- AC quality (4/5 > 3): 0\n- Missing reviewer evidence: 0\n- Regression failures: 0\n- Total deductions: 0\n\n### Confidence: 1.00\n### Action: archive