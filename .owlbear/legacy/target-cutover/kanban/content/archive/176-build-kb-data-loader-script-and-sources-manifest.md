---
id: 176
title: Build KB data loader script and sources manifest
status: archived
priority: medium
created: 2026-03-29 19:50:47.477056+02:00
updated: 2026-04-01 04:38:21.685927+02:00
started: 2026-04-01 04:38:17.410880+02:00
completed: 2026-04-01 04:38:17.410880+02:00
tags:
- phase-2
- scope:knowledge
- type:build
depends_on:
- 32
- 308
- 431
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create data/knowledge/general/sources.yaml manifest and a loader script (packages/knowledge/src/owlbear_knowledge/loader.py) that reads the manifest and ingests documents via IngestPipeline.

## Acceptance Criteria
- [ ] sources.yaml schema: sequence of {name: str, type: file_glob|url_list, config: {glob: str} or {urls: [str]}, scope: str (default global), enabled: bool (default true)}
- [ ] Manifest parsed and validated using strictyaml with typed schema; malformed YAML raises immediately with a clear error message
- [ ] Loader resolves file globs via pathlib.Path.glob() relative to workspace root
- [ ] Each resolved path passed through intake.read_file(path, workspace_root=root) for sandbox validation
- [ ] Registers each manifest entry as a KnowledgeSource via KnowledgeSourceStore.create() with ISO timestamps for created_at/updated_at
- [ ] Ingests each resolved file via IngestPipeline.ingest(IntakeResult, scope=source.scope) with delta detection handled internally by the pipeline
- [ ] Empty glob matches logged as WARNING, processing continues to next source
- [ ] Per-file ingest failures logged, processing continues; final summary reports ok/skipped/failed counts per source
- [ ] CLI entry point: uv run python -m owlbear_knowledge.loader --manifest <path> [--root <workspace_root>]; argparse, no extra deps
- [ ] Non-zero exit code when any source has all files failed
- [ ] Initial sources.yaml includes: all docs/research/*.md, all skills/*/SKILL.md, all instructions/*.md

## Context
Split from #24. See docs/research/general-kb-initial-data-load.md.
Research: docs/research/kb-data-loader-manifest.md

## Architecture Notes
- Use IngestPipeline.ingest(IntakeResult) not ingest_text() per research finding (.90 confidence). ingest() handles delta detection via check_content_changed() and content hash updates internally.
- Follow intake.read_file() for sandbox-safe file reading. sandbox_path() in _paths.py prevents path traversal.
- KnowledgeSource model has required created_at/updated_at: str fields. Loader sets these to datetime.now(tz=UTC).isoformat().
- argparse CLI, no click/typer dependency. Knowledge package stays lean.
- strictyaml schema provides fail-fast validation at parse time. Requires #308 (add strictyaml to knowledge deps).

[[2026-03-30]] Mon 21:33
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| sources.yaml manifest format | Good; maps to existing SourceType enum and KnowledgeSource model | Tightened schema spec with field defaults |
| Loader reads manifest, resolves globs | Good; pathlib.Path.glob() is correct approach | Added sandbox_path reference |
| Registers via KnowledgeSourceStore.create() | Good; verified method signature: create(source: KnowledgeSource) | Added created_at/updated_at requirement |
| Checks content delta via StatusStore | Redundant; IngestPipeline.ingest() handles delta internally | Removed from AC |
| Calls IngestPipeline.ingest_text() | Wrong API; ingest(IntakeResult) is superior (.90 confidence) | Replaced with ingest(IntakeResult) |
| CLI entry point | Good; argparse, no extra deps | Added --root flag |
| Unit tests with mock EmbeddingProvider | Belongs in test task | Moved to #431 |
| Initial sources.yaml ~50 docs | Vague quantity | Tightened to explicit glob patterns |

### Architecture Notes
Verified all interfaces in packages/knowledge/src/owlbear_knowledge/: IngestPipeline.ingest(IntakeResult) at ingest.py:127, intake.read_file() at intake.py:32, KnowledgeSourceStore.create(KnowledgeSource) at source_store.py:67, sandbox_path() at _paths.py:11. All align with proposed design. Single domain (scope:knowledge).

### Changes Made
- Rewrote AC: ingest_text() replaced with ingest(IntakeResult), removed redundant StatusStore check, tightened manifest schema, moved tests to #431
- Created #431 (Test: KB data loader) at todo with depends_on #308
- Added depends_on: #308 (strictyaml dep), #431 (test task)

### Dependencies
- #32 (vector store + embedding pipeline): archived (done)
- #308 (strictyaml dep): backlog, must complete before test-writer/builder
- #431 (test task): todo, TDD RED phase precedes implementation

[[2026-03-31]] Tue 17:29
## Test-Writer Notes
- Test file: tests/test_kb_loader_176.py
- Classes: TestFromAC_ScopeField, TestFromAC_EnabledField, TestFromAC_DisabledSourceSkip, TestFromAC_ScopePassthrough, TestFromAC_InitialSourcesYaml
- Tests per category: happy 9, edge 4, error 0, boundary 7
- Total: 20 tests, all FAIL (verified with pytest)
- ruff: clean
- AC coverage:
  AC1 scope field: TestFromAC_ScopeField (5 tests) + TestFromAC_DisabledSourceSkip indirect
  AC1 enabled field: TestFromAC_EnabledField (3 tests)
  AC1 enabled=false skip: TestFromAC_DisabledSourceSkip (3 tests)
  AC6 scope passthrough: TestFromAC_ScopePassthrough (4 tests)
  AC11 initial sources.yaml: TestFromAC_InitialSourcesYaml (5 tests)
- Failure types: YAMLValidationError (scope/enabled not in schema), AttributeError (ManifestEntry missing fields), FileNotFoundError (sources.yaml missing)
- Note: AC1-AC10 overlap with #431 already covered by test_kb_loader.py; this file covers the 176-specific gaps.

[[2026-03-31]] Tue 21:52
## Review Evidence
- pytest: 20 passed (test_kb_loader_176.py), 32 passed (test_kb_loader.py) â€” all green
- ruff: All checks passed!

### Test-Writer Coverage Table (test_kb_loader_176.py)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 scope field: str, default global | TestFromAC_ScopeField (5 tests) | Yes â€” test_scope_defaults_to_global_when_omitted asserts exactly | COVERED |
| AC1 enabled field: bool, default true | TestFromAC_EnabledField (3 tests) | Yes â€” test_enabled_defaults_to_true_when_omitted asserts .enabled is True | COVERED |
| AC1 enabled=false skip | TestFromAC_DisabledSourceSkip (3 tests) | Yes â€” assert_not_called on source_store.create and pipeline.ingest | COVERED |
| AC6 scope passthrough to ingest | TestFromAC_ScopePassthrough (4 tests) | Yes â€” checks kwargs.get(scope) equals manifest value | COVERED |
| AC11 initial sources.yaml globs | TestFromAC_InitialSourcesYaml (5 tests) | Yes â€” checks glob patterns for all 3 required directories | COVERED |

No MISSING entries. No LAX entries for lines covered by test_kb_loader_176.py.

### TestFromAC Comparison Table

| Class / Method | Change | Assessment |
|----------------|--------|------------|
| All TestFromAC_* in test_kb_loader_176.py | No modifications by builder | PRESERVED |
| All TestFromAC_* in test_kb_loader.py | No modifications by builder; builder added no TestBuilderDiscovered changes to test file | PRESERVED |

### Security Review

No issues. strictyaml provides type-safe YAML parsing (no code execution risk). Glob resolution is bounded to workspace_root via pathlib. intake.read_file() enforces sandbox_path() defense against path traversal. No hardcoded secrets, no injection risks.

### CRITICAL FAIL â€” AC9: CLI Entry Point is non-functional

**Evidence:** uv run python -m owlbear_knowledge.loader (no args) exits code 0 with no output.
AC9 requires --manifest to be required and missing --manifest to exit non-zero.

Root cause: loader.py has no if __name__ == '__main__': main() guard and no __main__.py in the package.
When Python executes python -m owlbear_knowledge.loader, it runs loader.py as a script with __name__ == '__main__', but since main() is never called, the module simply defines functions and exits silently with code 0.

**Test quality issue (LAX):** TestFromAC_CLI::test_missing_manifest_flag_raises_system_exit_nonzero imports and calls main([]) directly â€” it never tests the module invocation path. All CLI tests patch load_manifest_file entirely, bypassing the structural defect.

**Secondary issue in main():** source_store=None and pipeline=None are passed to load_manifest_file with type: ignore comments. Any non-empty manifest would raise AttributeError: NoneType has no attribute create at runtime. No test exercises main() with an actual live call (all tests mock load_manifest_file).

### Test Quality Rating

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | STRONG | All assertions check exact values; no loose asserts |
| Negative/error coverage | ADEQUATE | Error paths covered in test_kb_loader.py per scope split |
| Mutation resistance | STRONG | key paths well covered |
| Test independence | STRONG | tmp_path fixtures throughout |
| Test names | STRONG | Descriptive and scenario-based |
| CLI coverage | WEAK | Tests call main() directly; module invocation path untested; main() broken in production |

### Builder Process Quality

No ## Builder Notes section in task body. Implementation exists (loader.py) but build context is missing. FRICTION â€” informational only.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: sources.yaml schema with scope and enabled fields | loader.py lines 32-43 _SOURCE_SCHEMA; ManifestEntry dataclass with defaults | PASS |
| AC2: strictyaml schema; malformed YAML raises | test_kb_loader.py TestFromAC_ManifestParsing; _ParseError wrapping | PASS |
| AC3: glob via pathlib.Path.glob() relative to workspace root | loader.py line ~190 workspace_root.glob(pat); test_kb_loader.py TestFromAC_GlobResolution | PASS |
| AC4: intake.read_file(path, workspace_root=root) | loader.py line ~198 intake_mod.read_file(file_path, workspace_root=workspace_root) | PASS |
| AC5: KnowledgeSourceStore.create() with ISO timestamps | loader.py lines ~170-183; test_kb_loader.py TestFromAC_SourceRegistration | PASS |
| AC6: IngestPipeline.ingest(IntakeResult, scope=source.scope) | loader.py line ~200; TestFromAC_ScopePassthrough all pass | PASS |
| AC7: Empty glob logged WARNING; processing continues | loader.py lines ~192-196 logger.warning; test_kb_loader.py TestFromAC_EmptyGlob | PASS |
| AC8: Per-file failure isolation; summary counts | loader.py lines ~202-212; test_kb_loader.py TestFromAC_FailureIsolation | PASS |
| AC9: CLI uv run python -m owlbear_knowledge.loader works | No __name__ == __main__ guard; python -m produces no output, exits 0 silently | **FAIL** |
| AC10: Non-zero exit when any source has all files failed | main() never executes load_manifest_file in practice; LoadSummary.all_source_ok logic correct but unreachable via CLI | **FAIL** (blocked by AC9) |
| AC11: Initial sources.yaml with three required globs | TestFromAC_InitialSourcesYaml all pass; sources.yaml verified at data/knowledge/general/sources.yaml | PASS |

### Verdict: FAIL (confidence .92)

AC9 and AC10 fail: CLI entry point is syntactically defined but never invoked when called via python -m owlbear_knowledge.loader. Fix required: add if __name__ == '__main__': sys.exit(main()) at end of loader.py. Also fix: main() must receive real source_store and pipeline instances, not None.

[[2026-04-01]] Wed 01:01
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited LAX CLI tests (module invocation path untested)
- Added: 5 new failing tests in TestFromAC_ModuleInvocation (3) and TestFromAC_MainInstantiation (2)
- Gaps addressed: AC9 module __main__ guard, AC10 source_store/pipeline not None
- Preserved: 20 existing tests (all PASS)
- ruff: clean

[[2026-04-01]] Wed 01:35
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/loader.py
- Tests: 57 passed (25 in test_kb_loader_176.py + 32 in test_kb_loader.py), coverage 98% on loader.py
- Lint: ruff clean (noqa Q000 for __main__ guard literal required by test)
- Evidence: 5 new TestFromAC tests: GREEN after fix
- Fixes applied: (1) Added if __name__ == '__main__': sys.exit(main()) guard. (2) Replaced source_store=None and pipeline=None with real instantiation: GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, DocumentStore, EntityExtractor, TextChunker, IngestPipeline, KnowledgeSourceStore using OWLBEAR_KB_PATH env var or default data/knowledge/knowledge.db. (3) Added mkdir parents=True ensure DB dir exists before connect.

[[2026-04-01]] Wed 02:33
## Review Evidence (retry)
- pytest: 57 passed (25 in test_kb_loader_176.py + 32 in test_kb_loader.py), 0 failed â€” verified independently
- ruff: builder reports clean; noqa Q000 (__main__ guard single-quote literal required by inspect test) and noqa PLC0415 (lazy imports in main()) both reviewed and justified
- 2 RuntimeWarnings on runpy tests (expected module re-import artifact, does not affect test validity)

### Test-Writer Coverage Table (new tests added in retry)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC9 __main__ guard present | TestFromAC_ModuleInvocation::test_loader_module_has_main_guard | Yes â€” inspect.getsource checks exact string | COVERED |
| AC9 module invocation exits nonzero without args | TestFromAC_ModuleInvocation::test_module_invocation_without_manifest_exits_nonzero | Yes â€” runpy.run_module, asserts SystemExit code != 0 | COVERED |
| AC9 module invocation exits 0 with valid manifest | TestFromAC_ModuleInvocation::test_module_invocation_with_valid_manifest_exits_zero | Yes â€” runpy.run_module, asserts SystemExit(0) | COVERED |
| AC10 source_store not None | TestFromAC_MainInstantiation::test_main_does_not_pass_none_source_store | Yes â€” asserts source_store is not None in kwargs | COVERED |
| AC10 pipeline not None | TestFromAC_MainInstantiation::test_main_does_not_pass_none_pipeline | Yes â€” asserts pipeline is not None in kwargs | COVERED |

No MISSING. No LAX.

### TestFromAC Comparison Table (new tests)

| Class / Method | Change | Assessment |
|----------------|--------|------------|
| TestFromAC_ModuleInvocation â€” 3 methods | No modifications by builder | PRESERVED |
| TestFromAC_MainInstantiation â€” 2 methods | No modifications by builder | PRESERVED |
| All 20 original TestFromAC_* (from first cycle) | PRESERVED per prior review cycle | PRESERVED |

### Security Review

No new issues in this diff. Lazy imports inside main() are guarded behind if __name__ == __main__ â€” no import-time side effects. Real dependencies (GraphStore, QdrantVectorStore, etc.) instantiated only at CLI invocation scope. sandbox_path() defense unchanged.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: scope/enabled fields in schema | loader.py lines 32-43 _SOURCE_SCHEMA; ManifestEntry dataclass with defaults scope='global' enabled=True | PASS |
| AC2: strictyaml; malformed YAML raises | test_kb_loader.py TestFromAC_ManifestParsing all pass | PASS |
| AC3: pathlib.Path.glob() relative to workspace_root | loader.py ~line 190; test_kb_loader.py TestFromAC_GlobResolution | PASS |
| AC4: intake.read_file(path, workspace_root=root) | loader.py ~line 198 | PASS |
| AC5: KnowledgeSourceStore.create() with ISO timestamps | loader.py ~lines 170-183 | PASS |
| AC6: IngestPipeline.ingest(IntakeResult, scope=source.scope) | TestFromAC_ScopePassthrough 4 tests all pass | PASS |
| AC7: Empty glob logged WARNING | loader.py ~lines 192-196; test_kb_loader.py TestFromAC_EmptyGlob | PASS |
| AC8: Per-file failure isolation; summary counts | loader.py ~lines 202-212; TestFromAC_FailureIsolation | PASS |
| AC9: CLI python -m owlbear_knowledge.loader functional | if __name__ == '__main__': sys.exit(main()) at loader.py line 281; TestFromAC_ModuleInvocation 3 tests pass | PASS |
| AC10: Non-zero exit when all files failed | main() instantiates real source_store + pipeline; all_source_ok logic reachable; TestFromAC_MainInstantiation 2 tests pass | PASS |
| AC11: Initial sources.yaml with 3 required globs | data/knowledge/general/sources.yaml: docs/research/*.md, skills/*/SKILL.md, instructions/*.md â€” all 3 confirmed | PASS |

### Loop Detection (Step 6.7)

1 Builder Notes section. CLEAN process quality.

### Verdict: PASS (confidence .93)

All AC lines met. Previous FAIL items fixed: (1) __main__ guard added at loader.py line 281. (2) main() instantiates real KnowledgeSourceStore and IngestPipeline â€” no more None arguments.

[[2026-04-01]] Wed 03:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | No system-level behavior change; knowledge tech stack description unchanged |
| 2 | Docstrings complete | Yes | Pass | Module, ManifestEntry, LoadSummary, _ParseError, parse_manifest(), load_manifest_file(), main() all have accurate docstrings |
| 3 | docs/sources/overview.md | Yes | Updated | Added task #176 section: GraphRAG YAML config + strictyaml docs |
| 4 | README.md | Yes | Updated | Added Knowledge Base section with loader CLI and OWLBEAR_KB_PATH |
| 5 | Research doc linked | Yes | Pass | docs/research/kb-data-loader-manifest.md exists and linked from task body |

### Files Updated
- README.md, docs/sources/overview.md

### Scratch Files Cleaned
- None

[[2026-04-01]] Wed 04:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: sources.yaml schema (scope, enabled) | loader.py L39-43 _SOURCE_SCHEMA; ManifestEntry defaults scope=global, enabled=True | PASS |
| AC2: strictyaml; malformed YAML raises | _ParseError wraps low-level errors; TestFromAC_ManifestParsing (test_kb_loader.py) | PASS |
| AC3: pathlib.Path.glob() relative to workspace_root | loader.py L190 workspace_root.glob(pat) | PASS |
| AC4: intake.read_file(path, workspace_root=root) | loader.py L198 intake_mod.read_file(file_path, workspace_root=workspace_root) | PASS |
| AC5: KnowledgeSourceStore.create() with ISO timestamps | loader.py L170-183 datetime.now(tz=UTC).isoformat(), source_store.create(source) | PASS |
| AC6: IngestPipeline.ingest(IntakeResult, scope=source.scope) | loader.py L200 pipeline.ingest(intake_result, scope=entry.scope); TestFromAC_ScopePassthrough | PASS |
| AC7: Empty glob logged WARNING | loader.py L192-196 logger.warning; TestFromAC_EmptyGlob | PASS |
| AC8: Per-file failure isolation; summary counts | loader.py L202-212 try/except per file; TestFromAC_FailureIsolation | PASS |
| AC9: CLI entry point functional | loader.py L281 if __name__ == '__main__': sys.exit(main()); TestFromAC_ModuleInvocation (3 tests) | PASS |
| AC10: Non-zero exit when all files fail | main() returns 0 if summary.all_source_ok else 1; TestFromAC_MainInstantiation (2 tests) | PASS |
| AC11: Initial sources.yaml with 3 required globs | data/knowledge/general/sources.yaml: docs/research/*.md, skills/*/SKILL.md, instructions/*.md | PASS |

### Test Results
- pytest (task-scoped): 57 passed, 0 failed (25 in test_kb_loader_176.py + 32 in test_kb_loader.py)
- pytest (full suite): 2478 passed, 236 failed, 8 skipped. No failures in task scope.
- ruff: 3 violations, none in task scope (E902 src phantom, PT018 test_necessity_check_196.py)

### Architect Quality
- AC specificity: Good. Explicit field names, types, defaults, API method signatures.
- Edge case gap: Missed __name__=='__main__' guard (caught by reviewer in first cycle).
- Design direction: Architecture notes accurate. ingest(IntakeResult) over ingest_text() was correct.
- AC quality score: 4/5

### Commit Verification
- e4a684f test: add failing tests for scope/enabled (#176, test-writer)
- e11feaf feat: add scope/enabled fields and sources.yaml (#176, builder)
- 5195264 test: add failing module-invocation tests (#176, test-writer)
- 793a587 fix: add __main__ guard and real instantiation (#176, builder)
- 5adb4da docs: update README and sources (#176, writer)
All deliverables committed.

### Deduction breakdown: none. All 11 AC lines have specific evidence, lint clean in scope, tests green, reviewer evidence thorough, AC quality 4.
### Confidence: 1.0
### Action: archive
