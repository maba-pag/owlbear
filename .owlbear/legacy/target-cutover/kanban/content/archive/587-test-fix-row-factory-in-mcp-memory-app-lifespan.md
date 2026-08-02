---
id: 587
title: 'Test: Fix row-factory in mcp-memory app_lifespan'
status: archived
priority: medium
created: 2026-04-03 18:05:59.647500+02:00
updated: 2026-04-04 03:01:22.329989+02:00
started: 2026-04-03 18:06:10.376927+02:00
completed: 2026-04-04 03:01:12.872338+02:00
tags:
- scope:agents
- phase-2
- test
class: standard
archival_reason: completed
archival_refs: []
---

TDD RED phase for #586.

AC:
- [ ] Test that app_lifespan yields an AppContext whose conn.row-factory is sqlite3.Row
- [ ] Test exercises production lifespan path (not test-helper _make_conn)
- [ ] Test fails before the fix (conn.row-factory defaults to None when not explicitly set)
- [ ] Uses tmp_path or in-memory DB via OWLBEAR_MEMORY_DB_PATH env var override to avoid disk side effects
- [ ] ruff clean

[[2026-04-03]] Fri 18:51
## Test-Writer Notes
- Test file: tests/test_row-factory_mcp_memory_587.py
- Classes: TestFromAC_AppLifespanRowFactory
- Tests per category: happy 2, boundary 2
- Total: 4 tests, all FAIL
- ruff: clean
- Commit: 51728e2

AC coverage: all 5 AC lines covered
- conn.row-factory check: test_row-factory_is_sqlite3_row, test_row-factory_is_not_none (AssertionError before fix)
- Production lifespan path: all 4 tests use app_lifespan directly, not _make_conn
- Fails before fix: confirmed (4 FAIL via pytest run)
- tmp_path env var override: all 4 tests use monkeypatch.setenv + tmp_path
- ruff: clean

[[2026-04-03]] Fri 19:15
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear-mcp_memory/server.py (+1 line)
- Fix: added conn.row-factory = sqlite3.Row after sqlite3.connect()
- Tests: 4 passed, server.py 100% coverage
- Lint: ruff clean
- Commit: 72c41da

[[2026-04-03]] Fri 19:40
## Review Evidence

### Test Results
- pytest: 4 passed, 0 failed (tests/test_row-factory_mcp_memory_587.py)

### Lint
- ruff: All checks passed! (packages/mcp-memory/ + test file)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| app_lifespan yields AppContext with conn.row-factory == sqlite3.Row | test_row-factory_is_sqlite3_row | Yes — `is sqlite3.Row` exact identity check | COVERED |
| conn.row-factory must not be None (boundary) | test_row-factory_is_not_none | Yes — AssertionError if row-factory is None | COVERED |
| Production lifespan path, not _make_conn | All 4 tests use `async with app_lifespan(MagicMock())` directly | Yes — would fail if _make_conn substituted | COVERED |
| Tests fail before fix | Confirmed by test-writer commit 51728e2 (all FAIL) | N/A — RED phase requirement | COVERED |
| tmp_path env override (AC4) | All 4 tests: `monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db"))` | Yes — would write to disk if missing | COVERED |
| ruff clean | "All checks passed!" | N/A | COVERED |

#### Security Review
- No hardcoded secrets. Single-line attribute assignment `conn.row-factory = sqlite3.Row`.
- No injection, path traversal, insecure deserialization, or new dependencies.
- Clean.

#### Test Integrity — TestFromAC Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_row-factory_is_sqlite3_row | No change | PRESERVED |
| test_row-factory_is_not_none | No change | PRESERVED |
| test_get_knowledge_returns_list_of_dicts_via_production_lifespan | No change | PRESERVED |
| test_list_entries_returns_list_of_dicts_via_production_lifespan | No change | PRESERVED |

Builder only touched server.py (+1 line, commit 72c41da). Test file unchanged from test-writer commit 51728e2.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `is sqlite3.Row` identity check + dict content checks (id, category, content fields) |
| Negative/error-path coverage | STRONG | RED phase: absent row-factory raises ValueError in dict(row); test_row-factory_is_not_none guards the None case |
| Mutation reasoning | STRONG | Remove fix line returns row-factory=None — test_row-factory_is_sqlite3_row fails immediately |
| Test independence | STRONG | monkeypatch + tmp_path per-test fixtures; no shared mutable state |
| Descriptive names | STRONG | Names describe scenario and expected outcome |

#### Data Safety
No LLM output, no races, no multi-step operations, no unbounded input. Clean.

#### Implementation-Aware Gaps
Fix is one line: `conn.row-factory = sqlite3.Row` at server.py L79 (after sqlite3.connect, before PRAGMAs — correct placement per AC).
- `get_knowledge` and `list_entries` use `dict(row)` — tested via production lifespan.
- `set_approval_state` and `mark_for-deletion` use `r[0]` tuple indexing — unaffected by row-factory, no gap.
- `migrate.py` has its own connection — unaffected.
No untested paths in scope.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
None.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| app_lifespan yields AppContext whose conn.row-factory is sqlite3.Row | server.py L79: conn.row-factory = sqlite3.Row; 4 tests pass | test_row-factory_is_sqlite3_row | PASS |
| Test exercises production lifespan path (not _make_conn) | All 4 tests open `async with app_lifespan(MagicMock()) as ctx` | All 4 tests | PASS |
| Test fails before fix | Test-writer confirmed 4 FAIL before builder commit | All 4 tests | PASS |
| Uses tmp_path + env override | monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db")) in all 4 tests | All 4 tests | PASS |
| ruff clean | All checks passed! | N/A | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-03]] Fri 19:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal bug fix; no API/convention change |
| 2 | Docstrings | Yes | Updated | app_lifespan step (c): added row-factory = sqlite3.Row note |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- packages/mcp-memory/src/owlbear-mcp_memory/server.py (docstring only) - commit 233a1dd

### Scratch Files Cleaned
- None
