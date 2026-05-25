---
id: 1869
title: 'Cockpit: delegate decision resolution to kanban resolve_decision()'
status: done
priority: important
created: 2026-05-25T00:20:42.926678+02:00
updated: 2026-05-25T05:43:10.825173+02:00
tags:
  - scope:cockpit-backend
  - boundary-audit
parent: 1865
depends_on:
  - 1868
ac:
  - routes/decisions.py resolve endpoint body delegates to resolve_decision 
    imported from owlbear_kanban.decisions (aliased as kanban_resolve_decision 
    to avoid name collision with route function)
  - _rewrite_response and _append_response_section function definitions are 
    absent from routes/decisions.py
  - Imports YAML (ruamel.yaml), StringIO (io), canonical_summary, and 
    move_to_resolved are absent from routes/decisions.py
  - Imports parse_dr and YAMLError remain in routes/decisions.py (used by 
    list_pending_decisions and resolved-path fallback)
  - TypeError/ValueError/YAMLError raised by kanban_resolve_decision are caught 
    and re-raised as HTTPException(status_code=422, detail="Invalid decision 
    file format")
  - All tests in tests/test_cockpit_decisions_api.py pass without modification 
    (behavioral equivalence proof)
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace inline file-lifecycle code in `routes/decisions.py` resolve endpoint (lines 195–222) with a single call to `owlbear_kanban.decisions.resolve_decision(pending_path, req.response, engine, notes=req.notes, resolved_by="cockpit-api")`. Remove now-unused helpers `_rewrite_response` and `_append_response_section` from the route module. Keep HTTP-layer concerns (id validation, 404 checking, error→HTTPException mapping) in Cockpit. Depends on the kanban resolve_decision task above.

[[2026-05-25T04:54:56+02:00]]
## Research

T1 refactoring — no alternatives, implementation path is unambiguous.

**Key findings:**
1. `resolve_decision()` function proven via 28 tests (task #1868, archived)
2. Name collision: route function is also `resolve_decision` — use import alias `kanban_resolve_decision`
3. Parse errors (TypeError/ValueError/YAMLError) must still be caught at HTTP layer — kanban propagates them
4. ConcurrencyError from kanban function handled by global exception handler → 409
5. Remove helpers `_append_response_section`, `_rewrite_response` and unused imports (`YAML`, `StringIO`, `canonical_summary`, `move_to_resolved`)
6. Keep `parse_dr` and `YAMLError` imports (used by `list_pending_decisions` and resolved-path fallback)
7. Minor error message text change (path.name includes `.md`) — tests assert on status codes/envelope, not message text

**Research doc:** `.owlbear/research/cockpit-resolve-delegation.md`
**Confidence:** 0.92
**Follow-ups:** None — this task IS the implementation task; advances to backlog for architecture review.

[[2026-05-25T05:15:43+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace inline code with delegation call |
| Interface clarity | PASS | kanban resolve_decision() signature matches route needs; AC enumerates inputs/outputs |
| Dependency correctness | PASS | #1868 archived (complete) — kanban resolve_decision() exists and tested |
| Module layering | PASS | Cockpit (higher) delegates to kanban (lower); no upward imports |
| TDD compliance | PASS | Existing test suite covers endpoint behavior; proof bundle = existing |
| KISS/YAGNI | PASS | Removes duplication, no new abstractions |
| Premise challenge | PASS | Justified refactoring — inline code is exact duplicate of kanban module |
| Pattern consistency | PASS | Same import pattern as existing parse_dr/canonical_summary usage |
| Security surface | PASS | No new boundaries; input validation stays at HTTP layer |
| Single domain | PASS | Cockpit backend only (removing code, delegating down) |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| kanban_resolve_decision parse | Malformed YAML in DR file | TypeError/ValueError/YAMLError | Yes — caught, re-raised as 422 | Clear error |
| kanban_resolve_decision stale | DR already resolved between exists-check and call | ConcurrencyError | Yes — global handler → 409 | Retry prompt |
| kanban_resolve_decision task edit | Task file missing | FileNotFoundError | Yes — silently caught inside kanban | None |

### Design Diverge
- Trigger: skipped — T1 refactoring with unambiguous implementation path (no competing approaches)

### Challenge Results
- Challenger: reconsider (0.66)
- Findings: (1) no persisted AC, (2) AC wording vague, (3) 422 mapping not tested in existing suite
- Architect response: accepted items 1-2 — wrote precise AC lines. Item 3 rebutted: the 422 path for malformed DR is marked `# pragma: no cover` in current code (never tested even before refactoring); adding coverage is scope creep for a delegation task. Existing suite proves behavioral equivalence at the HTTP contract level.

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: existing
- Existing proof scope: tests/test_cockpit_decisions_api.py
- Test-writer: SKIP (bundle existing)

### Verdict: APPROVE
### Action Taken: Wrote AC lines, set proof_bundle=existing, advanced to todo.

[[2026-05-25T05:15:48+02:00]]
Architecture review complete. Wrote 6 mechanically-verifiable AC lines, set proof_bundle=existing with scope tests/test_cockpit_decisions_api.py. Challenger reconsider addressed by persisting AC and rebutting scope-creep concern on untested 422 path.

[[2026-05-25T05:17:00+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: tests/test_cockpit_decisions_api.py
- Passing through to builder.

[[2026-05-25T05:27:13+02:00]]
## Builder Notes
- Implementation: `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- Approach: Replaced inline resolve lifecycle logic in the resolve endpoint with one delegated call to `kanban_resolve_decision(...)`, while preserving HTTP-layer concerns (id validation, pending/resolved existence checks, duplicate-submit 404 behavior for cockpit-originated resolves, and 422 mapping for malformed decision files).
- Files changed:
  - `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- AC alignment:
  - Resolve endpoint now delegates through `resolve_decision` imported as `kanban_resolve_decision`.
  - Removed `_rewrite_response` and `_append_response_section` from route module.
  - Removed unused imports `YAML`, `StringIO`, `canonical_summary`, and `move_to_resolved`.
  - Kept `parse_dr` and `YAMLError` imports for pending list + resolved-path fallback/parse handling.
  - Preserved TypeError/ValueError/YAMLError -> HTTP 422 (`Invalid decision file format`) mapping.
- Tests (proof bundle: existing): quality-runner scoped run on `tests/test_cockpit_decisions_api.py` passed with no failures.
- Coverage: `owlbear_cockpit.routes.decisions` = 91%.
- Lint: clean (ruff clean after import-order fix).
- Commit: `620a33bc` — feat: delegate cockpit decision resolve to kanban (#1869, builder)

[[2026-05-25T05:37:22+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1869 to docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:15 and 136-175 import `resolve_decision` as `kanban_resolve_decision` and delegate the endpoint body through that single call with `notes=req.notes` and `resolved_by="cockpit-api"`. | tests/test_cockpit_decisions_api.py:898, 1237, 1331, 1487, 1503, 1521, 1541 exercise resolve registration, response shape, duplicate-submit handling, and immediate lifecycle effects through the route surface. | PASS |
| 2 | Direct inspection of serve/cockpit/src/owlbear_cockpit/routes/decisions.py:1-185 shows no `_rewrite_response` or `_append_response_section` definitions remain in the route module. | Structural refactor item; behavioral proof remains covered by the existing resolve lifecycle tests cited for AC 1 and AC 6. | PASS |
| 3 | The import block at serve/cockpit/src/owlbear_cockpit/routes/decisions.py:7-15 omits YAML, StringIO, canonical_summary, and move_to_resolved. | Structural cleanup item under the existing-proof refactor; no contradictory evidence in the named proof surface. | PASS |
| 4 | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:11, 14, 106-107, 151-154, 176-183 retain and use `parse_dr` and `YAMLError` for pending listing and resolved-path parse fallback. | tests/test_cockpit_decisions_api.py:1487, 1503, 1521 depend on the resolved-path fallback behavior for second-submit routing. | PASS |
| 5 | serve/cockpit/src/owlbear_cockpit/routes/decisions.py:176-183 catches TypeError, ValueError, and YAMLError from `kanban_resolve_decision` and re-raises HTTP 422 with detail `Invalid decision file format`; resolved-path malformed fallback remains mapped the same at 151-154. | No task-local malformed-resolve assertion exists in the named existing-proof file; architecture review explicitly accepted this path as a defensive code guard for this delegation refactor. | PASS |
| 6 | Builder notes report a quality-runner scoped pass on tests/test_cockpit_decisions_api.py, 91% coverage for owlbear_cockpit.routes.decisions, and clean lint; direct inspection of the touched file is consistent with that report. | tests/test_cockpit_decisions_api.py:898, 913, 924, 958, 975, 987, 998, 1011, 1237, 1331, 1382, 1487, 1503, 1521, 1541 are a strong existing proof surface for this refactor and would fail on the main route-level regressions. | PASS |
- Builder evidence sufficiency: sufficient and internally consistent; no independent quality-runner rerun was required.
- Safety and security check: no new dependency or input surface was introduced; HTTP-layer validation and exception mapping remain in Cockpit.
- Focused validation: editor diagnostics report no errors in serve/cockpit/src/owlbear_cockpit/routes/decisions.py.

## Observations
- Residual risk only: the malformed pending decision file to HTTP 422 path remains code-inspected rather than directly executed by the named existing-proof suite. Task history shows architecture review accepted that tradeoff for this refactor, so it is not a blocking finding on this cycle.

[[2026-05-25T05:43:10+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A — no update needed | Changed file `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` maps to `serve/cockpit/README.md`. Grep for `_rewrite_response`, `_append_response_section`, `move_to_resolved`, `canonical_summary`, `resolve_decision`, and `decisions.py` in README returned zero matches. Task is a pure internal refactoring (delegation) — public HTTP endpoint contract is unchanged; no README content is stale or inaccurate. |
| 2 | External attribution | No | N/A — no external attribution needed | T1 refactoring; task body explicitly states "no alternatives, implementation path is unambiguous." No external sources influenced implementation. |
| 3 | Research doc | Yes | N/A — linked | Research doc `.owlbear/research/cockpit-resolve-delegation.md` confirmed present. Task body references it explicitly: "Research doc: `.owlbear/research/cockpit-resolve-delegation.md`". |
| 4 | Deletion detection | No | N/A — no deletion impact | No source files were deleted. Two private helper functions (`_rewrite_response`, `_append_response_section`) were removed from within `decisions.py`; these were never referenced in any documentation. Grep in README and README-consumer.md returned zero matches for all removed symbols. |

### Verification Layers
- Layer 1 — grep structural: Searched `serve/cockpit/README.md`, `README.md`, and `README-consumer.md` for all removed symbols and internal function names — zero matches in all files. Public endpoint paths (`POST /api/decisions/{id}/resolve`) appear only in copilot-instructions.md endpoint table, which lists paths only — not implementation internals — and is unchanged.
- Layer 2 — LLM editorial: Task is a behavioral-equivalence refactoring; the public API contract is identical before and after. No documentation anywhere describes the removed private helpers or the previous inline implementation. No coherence issues introduced.

### Files Updated
- None

### Scratch Files Cleaned
- None found for task #1869
