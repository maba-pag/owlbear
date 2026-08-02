---
id: 1018
title: 'P0-02: Tests for doc-index script (RED)'
status: archived
priority: medium
created: 2026-04-19 23:51:24.321480+00:00
updated: 2026-04-20 01:20:06.268504+00:00
tags:
- phase-0
- docs-currency
- docs-tooling
parent: 1016
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] Test file exists at `serve/tools/tests/test_doc_index.py`
- [ ] Tests cover: filesystem walk with exclusion list (`.owlbear/scratch/`, `.owlbear/research/`, `.owlbear/kanban/`, `tests/`, `node_modules/`, `.git/`)
- [ ] Tests cover: markdown output format — auto-generated header (`<!-- AUTO-GENERATED ... DO NOT EDIT -->`), `## <path>` file headers, backtick-wrapped heading bullets, `### Outbound links` sub-section
- [ ] Tests cover: outbound link extraction excludes code blocks
- [ ] Tests cover: diagram entries include `describes` field
- [ ] Tests cover: index is idempotent (same input produces same output)
- [ ] Tests cover: conditional regen (skip when index mtime > newest doc mtime)
- [ ] Tests cover: CLI entry point `doc-index` is resolvable
- [ ] All tests FAIL (RED phase — implementation does not exist yet)

## Files

- Creates: `serve/tools/tests/test_doc_index.py`, `serve/tools/tests/__init__.py`
- Reference: Brief section 4.3 (doc-index artifact), section 4.5 (index grammar)
[[2026-04-20]]
## Architecture Review

### AC Refinements (binding — supersedes original where conflicting)

1. **File naming fix:** Test file is `serve/tools/tests/test_doc_index_1018.py` (not `test_doc_index.py`) per `w-tdd-red` convention `test_{module}_{task_id}.py`.
2. **Exclusion list expanded:** Original had 6 items; stance-architect.md specifies 10+. Full list for tests: `.owlbear/scratch/`, `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/decisions/`, `.owlbear/briefs/`, `.owlbear/sources/`, `store/`, `tests/`, `node_modules/`, `.git/`, `dist/`, `build/`.
3. **Parser tests added:** Brief §4.5 specifies parser alongside generator; GREEN #1020 AC includes parser. RED must cover it: "Tests cover: index parser round-trip — parser extracts file entries, headings, and outbound links from well-formed index markdown."
4. **Target module path:** `owlbear_tools.doc_index` (following serve/* naming: `serve/kanban/` → `owlbear_kanban`, `serve/tools/` → `owlbear_tools`). Tests import from this path; since the package does not exist yet, tests will fail at collection (ImportError) — valid RED.
5. **Files section updated:** Creates `serve/tools/tests/test_doc_index_1018.py`, `serve/tools/tests/__init__.py`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Write failing tests only — one deliverable |
| Interface clarity | PASS (after refine) | Module path, exclusion list, parser coverage now explicit |
| Dependency correctness | PASS | No deps; GREEN #1020 correctly depends on this |
| Module layering | PASS | Tests only, no production code |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Tests scope matches Brief §4.3/§4.5 exactly |
| Premise challenge | PASS | doc-index is a deliberate Brief outcome (Outcome 1) |
| Pattern consistency | PASS | Follows serve/kanban/tests/ pattern; file naming fixed to _1018 suffix |
| Security surface | N/A | Test files, no system boundary |
| Single domain | PASS | docs-tooling only |

### Challenge Results
- Challenger: reconsider (confidence 0.50)
- Findings: (C1) exclusion list incomplete — ACCEPTED, expanded to 12 items; (C2) file naming — ACCEPTED, fixed to `_1018` suffix; (C3) no parser tests — ACCEPTED, added AC line; (C4) refinement too narrow — ACCEPTED, all 4 concerns now addressed; (C5) #1020 refs deleted `test_package_boundary.py` — noted for #1020 review, not #1018's scope
- Architect response: all 4 substantive concerns accepted and incorporated

### Downstream note for #1020 review
GREEN task #1020 AC references `tests/test_package_boundary.py` with `ALLOWED_IMPORTS` — verify this file exists when #1020 reaches backlog review.

### Verdict: APPROVE (after REFINE)
### Action Taken: Tightened AC (4 refinements), advanced to todo
[[2026-04-20]]
## Test-Writer Notes
- Test file: `serve/tools/tests/test_doc_index_1018.py`
- Support files: `serve/tools/tests/__init__.py`, `serve/tools/pyproject.toml` (workspace membership stub)
- Classes: `TestFromAC_FilesystemWalk`, `TestFromAC_MarkdownFormat`, `TestFromAC_OutboundLinkExtraction`, `TestFromAC_DiagramDescribesField`, `TestFromAC_Idempotency`, `TestFromAC_ConditionalRegen`, `TestFromAC_CLIEntryPoint`, `TestFromAC_Parser`
- Tests per category: happy 30, edge 8, boundary 5, error 0
- Total: 43 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_tools' — valid RED per arch review)
- ruff: clean
- Commit: a5975240

### AC Coverage

| AC line | Tests |
|---------|-------|
| Filesystem walk with exclusion list (12 dirs) | `TestFromAC_FilesystemWalk` — 18 tests (12 parametrized per dir + 6 behavioral) |
| Markdown output format — header, `## path`, backtick bullets, `### Outbound links` | `TestFromAC_MarkdownFormat` — 6 tests |
| Outbound link extraction excludes code blocks | `TestFromAC_OutboundLinkExtraction` — 4 tests (fenced, inline, indented) |
| Diagram entries include `describes` field | `TestFromAC_DiagramDescribesField` — 3 tests |
| Index is idempotent | `TestFromAC_Idempotency` — 2 tests |
| Conditional regen (skip when index newer) | `TestFromAC_ConditionalRegen` — 3 tests |
| CLI entry point `doc-index` resolvable | `TestFromAC_CLIEntryPoint` — 2 tests |
| Parser round-trip (arch review addition) | `TestFromAC_Parser` — 5 tests |

### Note for GREEN (#1020)
`serve/tools/pyproject.toml` is a stub with no `src/` yet. GREEN must:
1. Create `serve/tools/src/owlbear_tools/doc_index.py` with `collect_docs`, `generate_index`, `should_regenerate`, `parse_index`, `main`
2. Add `serve/tools/src` to root `pyproject.toml` `pythonpath`
3. Register `doc-index = "owlbear_tools.doc_index:main"` in `serve/tools/pyproject.toml` (already present in stub)
[[2026-04-20]]
## Builder Notes

### Files changed
- `serve/tools/src/owlbear_tools/__init__.py` — new, package init
- `serve/tools/src/owlbear_tools/doc_index.py` — new, full implementation
- `serve/tools/tests/test_doc_index_1018.py` — added `import sys`, `main` import, `TestBuilderDiscovered` (4 tests)
- `pyproject.toml` — added `serve/tools/src` to `pythonpath` and `[tool.ruff] src`

### Implementation
- `collect_docs()` — `os.walk` with in-place pruning of 12 excluded dirs (exact path match, not prefix)
- `generate_index()` — emits auto-generated header, `## path`, heading bullets, `### Outbound links`, and `describes:` for excalidraw; excludes the index file itself from collection (idempotency)
- `should_regenerate()` — mtime comparison, returns True when index absent or any doc is newer
- `parse_index()` — refactored into `_parse_markdown()` + `_update_entry()` helper (complexity control)
- `main()` — argparse CLI entry point wired to `doc-index` console_scripts

### Test results
- 43 TestFromAC tests: all PASS (GREEN)
- 4 TestBuilderDiscovered tests added: invalid JSON excalidraw, string describes, non-outbound section header, main() invocation
- Total: 47 passed, 0 failed

### Lint
- ruff: clean (fixed PIE810, PERF401, C901/FBT001)

### Coverage
- `owlbear_tools.doc_index`: **100%** (139/139 statements)

### Commit
40216a00
[[2026-04-20]]
## Review Evidence
### Test Results
- pytest: 47 passed, 0 failed

### Lint: clean

### Coverage: UNVERIFIABLE
`owlbear_tools` not in `[tool.coverage.run] source_pkgs` in pyproject.toml. Builder's self-reported 100% (139/139) cannot be confirmed. Fix: add `"owlbear_tools"` to `source_pkgs`.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Filesystem walk, 12-dir exclusion | `TestFromAC_FilesystemWalk` (parametrized, line 113) | Yes | COVERED |
| Markdown output format | `TestFromAC_MarkdownFormat` (5 tests, lines 153–239) | Yes | COVERED |
| Outbound links exclude code blocks | `TestFromAC_OutboundLinkExtraction` (4 tests, lines 246–297) | Yes | COVERED |
| Diagram entries include `describes` field | `TestFromAC_DiagramDescribesField` (line 309) | Partially — `"describes" in entry_text` could match heading text; compensated by `test_describes_field_contains_globs` (line 326) | LAX/compensated |
| Index is idempotent | `TestFromAC_Idempotency` (lines 360–383) | Yes — bit-for-bit equality | COVERED |
| Conditional regen | `TestFromAC_ConditionalRegen` (lines 390–419) | Yes | COVERED |
| CLI entry point `doc-index` resolvable | `TestFromAC_CLIEntryPoint` (lines 425–439) | Yes | COVERED |
| Parser round-trip | `TestFromAC_Parser` (lines 477–519) | Yes | COVERED |

No MISSING AC lines. LAX compensated. No FAIL from this section.

#### Security Review — **FAIL** (OWASP A01/A05 — Path Traversal)
`doc_index.py:220`: `index_path = (root / args.output).resolve()` — Python's `/` operator silently discards `root` when `args.output` is an absolute path (e.g. `doc-index . --output /tmp/steal.md`). Combined with `index_path.parent.mkdir(parents=True, exist_ok=True)` at line 155, this allows writing files and creating directory trees at any filesystem location. No `is_relative_to(root)` containment check exists. No test covers this attack vector.

**Fix required:** Add guard after line 220:
```python
if not index_path.is_relative_to(root.resolve()):
    raise SystemExit(f"error: output path must be inside workspace root: {index_path}")
```

#### Test Integrity
All 43 `TestFromAC_*` tests PRESERVED. No relaxed comparisons, no `pytest.skip`, no `xfail`. Builder only added `import sys`, `main` import, and 4 `TestBuilderDiscovered` tests. **No violations.**

#### Test Quality
| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | ADEQUATE | No bare `assert result`; entry-scoped checks throughout |
| Negative/error-path | ADEQUATE | Code-block exclusion tested; missing OSError on markdown read |
| Mutation sensitivity | ADEQUATE | `>` vs `>=` in `should_regenerate` unmutated (equal-mtime boundary not tested — informational) |
| Test independence | STRONG | All use `tmp_path` or pure strings |
| Descriptive names | STRONG | |

No WEAK dimensions. No FAIL from this section.

#### Data Safety
- Non-atomic `write_text` for index output (partial file on interruption) — low risk for local CLI, informational only.
- No unbounded input, no LLM output, no shared mutable state.

No FAIL from this section.

#### Implementation-Aware Gaps — **FAIL** (3 significant untested paths)

**Gap 1 — `main()` no-regen guard (doc_index.py:221):**
```python
if should_regenerate(index_path, root):
    generate_index(root, index_path)
```
`TestBuilderDiscovered::test_main_generates_index_when_absent` only tests when index is absent (regen=True path). The skip-when-current branch has zero test coverage. A removed or inverted `if` guard would not be caught.

**Gap 2 — `should_regenerate` with zero docs and existing index (doc_index.py:162–163):**
`any(doc.stat().st_mtime > index_mtime for doc in collect_docs(root))` returns `False` when `collect_docs` returns `[]`. This means a stale index is never regenerated if all docs are deleted. No test creates an empty workspace with an existing index to verify (or challenge) this behavior.

**Gap 3 — `_render_entry` with `describes=[]` (doc_index.py:124–128):**
`isinstance(describes, list) and describes` is falsy for empty list → no `describes` line emitted silently. No test exercises this path. Existing tests use non-empty lists and strings only.

Minor (informational): inconsistent OSError handling between excalidraw branch (caught) and markdown branch (propagates); `~~~` tilde fences not tested.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Redundant test: `test_output_header_contains_do_not_edit` (line 163) duplicates assertion already in `test_output_starts_with_auto_generated_header`.
- `mtime` equal-to boundary (`doc.mtime == index.mtime`) not tested in `TestFromAC_ConditionalRegen`; `should_regenerate` uses strict `>`.
- Closing fence regex `^{char}{3,}` is over-permissive (matches language-tagged closing fences like `` ```python ``).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Test file at `serve/tools/tests/test_doc_index_1018.py` | File exists | N/A | PASS |
| 12-dir exclusion | `TestFromAC_FilesystemWalk` + `doc_index.py:66–76` | `test_excludes_all_exclusion_dirs` | PASS |
| Markdown format | `TestFromAC_MarkdownFormat` + `doc_index.py:84–100` | 5 tests | PASS |
| Outbound links exclude code blocks | `TestFromAC_OutboundLinkExtraction` + `doc_index.py:101–111` | 4 tests | PASS |
| Diagram `describes` field | `TestFromAC_DiagramDescribesField` + `doc_index.py:120–129` | 3 tests (LAX compensated) | PASS |
| Idempotency | `TestFromAC_Idempotency` + self-exclusion guard `doc_index.py:68` | 2 tests | PASS |
| Conditional regen | `TestFromAC_ConditionalRegen` + `doc_index.py:160–163` | 3 tests | PASS |
| CLI entry point | `TestFromAC_CLIEntryPoint` + `serve/tools/pyproject.toml` | 2 tests | PASS |
| Parser round-trip | `TestFromAC_Parser` + `doc_index.py:165–208` | 5 tests | PASS |

### Confidence: .48
### Verdict: FAIL

**Required fixes (all mandatory before re-review):**
1. **Security (OWASP A01):** Add `is_relative_to(root.resolve())` containment check after resolving `index_path` in `main()`. Raise `SystemExit` with clear message on violation. Add test to `TestBuilderDiscovered` covering absolute-path output rejection.
2. **Test Gap 1:** Add test to `TestBuilderDiscovered` calling `main()` when index is already up-to-date; assert `generate_index` is NOT called (use `monkeypatch` or check index mtime unchanged).
3. **Test Gap 2:** Add test to `TestFromAC_ConditionalRegen` or `TestBuilderDiscovered`: empty workspace + existing index → `should_regenerate` returns False. Decide and document whether this is intentional behavior.
4. **Test Gap 3:** Add test to `TestFromAC_DiagramDescribesField` or `TestBuilderDiscovered`: excalidraw with `{"describes": []}` → output entry has no `describes` line. Decide if silent emission is correct or if a fallback should be shown.
5. **Coverage config:** Add `"owlbear_tools"` to `[tool.coverage.run] source_pkgs` in `pyproject.toml` so coverage is measurable on re-review.
[[2026-04-20]]
## Builder Notes (re-review pass)

### Reviewer fixes applied
All 5 required fixes from reviewer FAIL verdict addressed:

1. **Security (OWASP A01):** `is_relative_to(root)` guard added to `main()` after resolving `index_path` — raises `SystemExit` with clear message on absolute/external output path.
2. **Test Gap 1:** `TestBuilderDiscovered::test_main_skips_regen_when_index_is_current` — verifies `main()` leaves existing up-to-date index unchanged.
3. **Test Gap 2:** `TestBuilderDiscovered::test_should_regenerate_empty_workspace_with_existing_index` — documents and tests that empty workspace + existing index → `should_regenerate` returns False (intentional: no docs means no staleness trigger).
4. **Test Gap 3:** `TestBuilderDiscovered::test_excalidraw_empty_describes_list_no_describes_line` — verifies `describes=[]` silently emits no line (silent-emission is intentional behavior).
5. **Coverage config:** `owlbear_tools` added to `[tool.coverage.run] source_pkgs` in `pyproject.toml`.

### Files changed
- `serve/tools/src/owlbear_tools/doc_index.py` — +3 lines (path traversal guard)
- `serve/tools/tests/test_doc_index_1018.py` — +4 `TestBuilderDiscovered` tests (total: 8)
- `pyproject.toml` — added `owlbear_tools` to `source_pkgs`
- `uv.lock` — auto-updated

### Test results
- 51 passed, 0 failed (43 TestFromAC + 8 TestBuilderDiscovered)
- Coverage: `owlbear_tools.doc_index` **100%** (142/142 statements)
- ruff: clean

### Commit
cc9b21d7
[[2026-04-20]]
## Review Evidence

### Test Results
pytest: 51 passed, 0 failed (43 TestFromAC + 8 TestBuilderDiscovered)

### Lint
clean: true

### Coverage
`owlbear_tools.doc_index`: 100% (142/142 statements) — now verifiable: `owlbear_tools` confirmed in `[tool.coverage.run] source_pkgs` at pyproject.toml:164

### Re-review: 5 Required Fixes

| Fix | Location | Status |
|-----|----------|--------|
| Security: `is_relative_to(root)` guard in `main()` | `doc_index.py:245–248` | APPLIED — guard raises `SystemExit` on absolute/external output path |
| Test Gap 1: skip-regen branch covered | test file:575–590 | APPLIED — `test_main_skips_regen_when_index_is_current` uses mtime manipulation |
| Test Gap 2: empty workspace + existing index | test file:607–610 | APPLIED — returns False, documented as intentional |
| Test Gap 3: `describes=[]` silent emission | test file:613–621 | APPLIED — no `describes` line emitted for empty list |
| Coverage config | pyproject.toml:164 | APPLIED — `owlbear_tools` in source_pkgs |

### TestFromAC_* Integrity
All 43 TestFromAC_* tests preserved unmodified. Builder added 4 new TestBuilderDiscovered tests (total 8). No WEAKENED or REMOVED tests.

### Builder Process
2 Builder Notes sections — re-review applied exactly the 5 reviewer-specified fixes. CLEAN.

### AC Compliance
All 9 AC lines (including arch-review refinements) map to passing tests with specific assertions. No MISSING or LAX-uncompensated lines.

### Confidence: .95
### Verdict: PASS
[[2026-04-20]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | New `owlbear_tools` package + `doc-index` CLI. `copilot-instructions.md` covers Cockpit only — no change needed. README directory layout table was missing `serve/tools/` — added row: `serve/tools/ | Workspace utility scripts — doc-index CLI`. |
| 2 | Module docstrings | Yes | Verified | All public symbols in `doc_index.py` have accurate docstrings: module, `LinkEntry`, `DocEntry`, `_is_excluded_dir`, `collect_docs`, `_parse_markdown`, `_render_entry`, `generate_index`, `should_regenerate`, `_update_entry`, `parse_index`, `main`. All match implementation. No edits needed. |
| 3 | External attribution | No | N/A | Standard Python stdlib implementation (os.walk, argparse, pathlib, re, json). No external repos, articles, or patterns cited in task body or review evidence. |
| 4 | CLI changes | Yes | Updated | New `doc-index` console_scripts entry in `serve/tools/pyproject.toml:16`. Covered by Item 1 (directory layout row). No dedicated CLI usage section needed — tool is dev-utility, not a primary user-facing command. |
| 5 | Research doc | No | N/A | No research doc produced for this task. Brief was parent #1016. No `.owlbear/research/` file for 1016/1018/docs-tooling. |

### Files Updated
- `README.md` — added `serve/tools/` row to directory layout table (commit 893641e0)

### Scratch Files
No `.owlbear/scratch/1018-*` files found — nothing to clean.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at `test_doc_index_1018.py` | File exists (confirmed) | PASS |
| Filesystem walk, 12-dir exclusion | `TestFromAC_FilesystemWalk` — 7 functions, parametrized for 12 dirs | PASS |
| Markdown output format | `TestFromAC_MarkdownFormat` — 6 tests | PASS |
| Outbound links exclude code blocks | `TestFromAC_OutboundLinkExtraction` — 4 tests (spot-checked: fenced/inline/indented assertions) | PASS |
| Diagram `describes` field | `TestFromAC_DiagramDescribesField` — 3 tests | PASS |
| Idempotency | `TestFromAC_Idempotency` — 2 tests | PASS |
| Conditional regen | `TestFromAC_ConditionalRegen` — 3 tests | PASS |
| CLI entry point resolvable | `TestFromAC_CLIEntryPoint` — 2 tests | PASS |
| Parser round-trip (arch refinement) | `TestFromAC_Parser` — 5 tests | PASS |

### Test Results
- pytest: 787 passed, 6 failed (all in `serve/mcp-knowledge/` — pre-existing, not in task scope), 4 skipped
- ruff: clean

### Architect Quality: 4/5
Original AC adequate but needed 4 refinements (file naming convention, exclusion list expansion 6→12, parser test coverage, module path). Challenge/response cycle was thorough — all concerns addressed. Refinements improved quality meaningfully.

### Reviewer Quality
Two-pass review. First pass caught OWASP A01 path traversal (confirmed: `is_relative_to` guard at doc_index.py:221) and 3 significant test gaps. FAIL at .48 was well-calibrated. Second pass verified all 5 fixes. Strong review quality.

### Deduction Breakdown
- AC lines with no evidence: 0 → -0.00
- Lint violations: 0 → -0.00
- AC quality ≤ 3: No (4/5) → -0.00
- Missing reviewer evidence: No → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 1.00
### Action: archive