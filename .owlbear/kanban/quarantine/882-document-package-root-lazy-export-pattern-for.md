---
id: 882
title: Document package-root lazy export pattern for OwlBear public APIs
status: archived
priority: nice-to-have
created: 2026-03-20T16:43:22.1935111+01:00
updated: 2026-03-21T12:54:05.0878868+01:00
started: 2026-03-21T12:53:33.6183584+01:00
completed: 2026-03-21T12:53:33.6183584+01:00
tags:
    - docs
    - architecture
    - scope:tools
    - type:docs
parent: 879
class: standard
---

AC: add a short architecture note describing when package __init__.py may use cached module-level __getattr__ import maps; document why OwlBear keeps __all__ explicit and avoids adding lazy-loader for small public surfaces; cite src/owlbear/memory/knowledge/__init__.py and src/owlbear/tools/__init__.py as the current repo examples.

## Research

- Doc: docs/research/package-root-lazy-export-pattern.md
- Attribution updated: docs/sources/overview.md now logs the Python data model docs, PEP 562, PEP 8 public/internal interfaces, Scientific Python SPEC 1, and lazy-loader docs used for this task.
- Key findings:
    Cached module-level __getattr__ package roots should be an exception, not the default. Use them only for deliberate public package roots with measured eager-import side effects or optional-dependency pressure.
    Keep __all__ explicit and small. It is the supported public contract; the lazy import map is private machinery.
    For OwlBear's small fixed surfaces (owlbear.tools = 10 names, owlbear.memory.knowledge = 14 names), an inline importlib map is lower cost than adding lazy-loader and its stub or packaging overhead.
    docs/architecture.md is the correct long-lived home for this rule; a standalone architecture note would duplicate the canonical architecture doc.
    Lazy exports must not be used to hide illegal dependency edges. Fix layering first, then apply lazy exports only if import pressure remains.
- Follow-up task created:
    #887 Add package-root lazy-export policy note to docs/architecture.md
    Create command: kanban\kanban-md.exe create "Add package-root lazy-export policy note to docs/architecture.md" --priority nice-to-have --status ideation --tags docs,architecture,scope:tools,type:docs --parent 882 --body "Add a short subsection to docs/architecture.md under the architecture design-rules area describing OwlBear's package-root lazy-export policy. Capture when cached module-level __getattr__ import maps are allowed (only for deliberate public package roots with measured eager-import side effects or optional-dependency pressure), why __all__ stays explicit and limited to the supported surface, why lazy-loader stays out of scope for small fixed surfaces like owlbear.tools and owlbear.memory.knowledge, and that __dir__ is optional rather than default. State explicitly that lazy exports are not a substitute for fixing illegal dependency edges. Cite src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py as the current repo examples. See docs/research/package-root-lazy-export-pattern.md. AC: (1) docs/architecture.md gains a short policy note with those rules, (2) the note names both current repo examples, (3) the note states that __all__ is the public contract and __getattr__ is an implementation detail, (4) no new standalone architecture note file is created." --dir kanban
- Existing related task:
    #883 remains the optional __dir__ ergonomics follow-up and is not part of the default policy.
- Verdict: #882 is correct in theme but under-specified as an execution leaf; #887 makes the destination and acceptance criteria concrete for architect review.

[[2026-03-21]] Sat 05:33

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| add a short architecture note describing when package __init__.py may use cached module-level __getattr__ import maps; document why OwlBear keeps __all__ explicit and avoids adding lazy-loader for small public surfaces; cite src/owlbear/memory/knowledge/__init__.py and src/owlbear/tools/__init__.py as the current repo examples. | Single docs concern and architecturally sound, but under-specified as an execution leaf because it does not name the canonical destination inside docs/architecture.md and leaves optional __dir__ ergonomics adjacent to this task's scope. | Approved with the binding contract below: land the policy in docs/architecture.md under ## 8. Key Design Decisions, keep __dir__ out of scope, and cite the two live package-root examples. |

### Architecture Notes

- Existing repo examples are src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py. Both use explicit __all__ plus cached module-level __getattr__ import maps, so the docs task should describe that exact pattern rather than a generic lazy-loading design.
- docs/architecture.md is the canonical destination. The file currently has no package-root lazy export policy subsection, so this task should add one there instead of creating a standalone note.
- Refined delivery target: add a short subsection under ## 8. Key Design Decisions titled Package-root lazy exports, or an equivalently explicit heading in that section.
- TDD: not applicable. This is a docs-only task with no runtime behavior change.
- Single domain: docs/architecture only. Related runtime ergonomics remain isolated in #883.
- Failure mode map: not required for a docs-only task.

### Binding Contract

1. docs/architecture.md gains a short subsection under ## 8. Key Design Decisions that states OwlBear defaults to direct imports or eager re-exports for ordinary package roots.
2. The note states cached module-level __getattr__ import maps are allowed only for deliberate public package roots with measured eager-import side effects, optional-dependency pressure, or import-cycle pressure.
3. The note states __all__ is the supported public contract and the lazy import map plus __getattr__ are implementation details.
4. The note states lazy-loader is out of scope for OwlBear's current small fixed public surfaces, specifically owlbear.tools and owlbear.memory.knowledge.
5. The note states __dir__ is optional ergonomics and not part of this task.
6. The note states lazy exports must not be used to hide illegal dependency edges; layering problems must be fixed first.
7. The note cites src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py as the current repo examples.
8. No new standalone architecture note file is created.

### Changes Made

- Claimed #882 as leaf-pond.
- Refined the execution contract in this review section so the builder has a concrete docs target.
- No new tasks created; #883 remains the separate optional runtime ergonomics follow-up.

### Dependencies

- Verified: no predecessor task is required for this docs-only change.
- Related: #883 remains out of scope for this task.
- Related: #887 contains the same concrete docs destination and is redundant once #882 is executed from this refined contract, but it was not modified because it is outside this dispatched assignment.

[[2026-03-21]] Sat 06:04

## Test-Writer Notes

Non-implementation task (tagged: docs, type:docs) — no testable code will be produced. Architecture Review explicitly states 'TDD: not applicable. This is a docs-only task with no runtime behavior change.'
Passing through to builder.

[[2026-03-21]] Sat 06:23

## Builder Notes

- Files changed: docs/architecture.md (+40 lines)
- Tests: N/A — docs-only task; test-writer passed through
- Lint: N/A — no .py files changed
- Evidence: subsection 'Package-root lazy exports' added under ## 8. Key Design Decisions (line 462)
- Binding contract checklist: (1) subsection under section 8 checked (2) three allowed conditions stated checked (3) __all__ is public contract checked (4) lazy-loader out of scope for owlbear.tools + memory.knowledge checked (5) __dir__ optional ergonomics checked (6) lazy exports must not hide illegal dependency edges checked (7) both example files cited with rationale checked (8) no standalone file created checked
- Commit: ce1b9b9

[[2026-03-21]] Sat 06:48

## Review Evidence

## Review: #882 — Document package-root lazy export pattern for OwlBear public APIs

### Test Results

- pytest: 15 passed, 0 failed, 2 warnings
- Command: `uv run pytest tests/test_tools_lazy_exports.py -q --tb=short`
- Evidence: warnings are optional-dependency skips from `tests/conftest.py`; no test failures.

### Lint Results

- ruff: failed (exit code 1) with pre-existing repository lint findings in unrelated test files (examples observed: `tests/test_cli_knowledge_source.py:220` D403, `tests/test_daemon_coverage_gaps.py:134` D205/D209).
- Command: `uv run ruff check src/ tests/`

### Coverage

- Not applicable for this task. Task delta is docs-only (`git show --name-status ce1b9b9` shows only `docs/architecture.md`).

### Pass 1 — CRITICAL

#### Security Review

- No security issues found.
- Scope evidence: commit `ce1b9b9` modifies documentation text only; no runtime code paths, secrets, command execution, or deserialization logic changed.

#### Test Integrity (TestFromAC comparison)

- Not applicable. No test files were changed in task delta, so no `TestFromAC_*` method modifications to compare.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are specific (`pytest.raises(AttributeError)` at `tests/test_tools_lazy_exports.py:305`, message match at `tests/test_tools_lazy_exports.py:330`), with one looser assertion (`result is not None` at `tests/test_tools_lazy_exports.py:90`). |
| Negative/error paths | STRONG | Unknown-name error behavior covered (`test_getattr_raises_attribute_error_for_unknown_names`, `test_attribute_error_message_names_the_module`). |
| Mutation reasoning | ADEQUATE | Cache and eager-load regressions are mutation-sensitive via subprocess checks (e.g., `test_core_retry_absent_after_bare_import` at `tests/test_tools_lazy_exports.py:267`). |
| Test independence | STRONG | Subprocess-based checks isolate module import state and avoid cross-test pollution. |
| Descriptive names | STRONG | Test names encode behavior and expected outcome (e.g., `test_tools_module_has_no_custom_dir` at `tests/test_tools_lazy_exports.py:342`). |

#### Data Safety

- No data safety issues found.
- Rationale: docs-only change; no persistence, concurrency, or input-processing logic modified.

### Pass 2 — INFORMATIONAL

- Repository lint debt exists and is unrelated to #882 deliverable. Ruff output was large/truncated by terminal capture, but explicit violations were observed in files outside this task's diff.

### AC Compliance

| AC / Binding Contract Line | Evidence | Mapped Test | Status |
|----------------------------|----------|-------------|--------|
| 1. Add short subsection under `## 8. Key Design Decisions` | `docs/architecture.md:444` section 8 header and `docs/architecture.md:462` new `### Package-root lazy exports` | N/A (docs-only AC) | PASS |
| 2. State default is direct imports/eager re-exports for ordinary roots | `docs/architecture.md:464` | N/A (docs-only AC) | PASS |
| 3. Allow cached `__getattr__` maps only for measured side effects / optional deps / import cycles | `docs/architecture.md:469`, `docs/architecture.md:471`, `docs/architecture.md:473` | `tests/test_tools_lazy_exports.py:57` | PASS |
| 4. State `__all__` is public contract; lazy map/`__getattr__` are implementation details | `docs/architecture.md:476` | `tests/test_tools_lazy_exports.py:57`, `tests/test_tools_lazy_exports.py:305` | PASS |
| 5. State lazy-loader is out of scope for current small fixed surfaces and cite both package examples with counts | `docs/architecture.md:480`, `docs/architecture.md:495`, `docs/architecture.md:498`; counts validated from source declarations: `src/owlbear/tools/__init__.py:11` (10 names), `src/owlbear/memory/knowledge/__init__.py:11` (14 names) | `tests/test_tools_lazy_exports.py:358` | PASS |
| 6. State `__dir__` is optional and not required in this task | `docs/architecture.md:485` | `tests/test_tools_lazy_exports.py:342` | PASS |
| 7. State lazy exports must not hide illegal dependency edges | `docs/architecture.md:489`, `docs/architecture.md:491` | `tests/test_tools_lazy_exports.py:267` | PASS |
| 8. Cite current repo examples (`src/owlbear/tools/__init__.py`, `src/owlbear/memory/knowledge/__init__.py`) | `docs/architecture.md:495` and `docs/architecture.md:498`; source files confirm `_LAZY_IMPORTS` and caching: `src/owlbear/tools/__init__.py:26`, `src/owlbear/tools/__init__.py:40`, `src/owlbear/tools/__init__.py:45`, `src/owlbear/memory/knowledge/__init__.py:30`, `src/owlbear/memory/knowledge/__init__.py:48`, `src/owlbear/memory/knowledge/__init__.py:53` | `tests/test_tools_lazy_exports.py:57` | PASS |
| 9. No new standalone architecture note file created | `git show --name-status --oneline ce1b9b9` reports only `M docs/architecture.md` | N/A (artifact constraint) | PASS |

### Verdict: PASS

### Confidence

- .96

### Action Taken

- Review evidence appended by reviewer.

[[2026-03-21]] Sat 12:54

## Audit

### AC Verification

| BC# | Requirement | Evidence | Status |
|-----|-------------|----------|--------|
| 1 | Subsection under section 8 | docs/architecture.md:462 heading | PASS |
| 2 | Default is direct/eager re-exports | docs/architecture.md:463 | PASS |
| 3 | Three allowed conditions stated | docs/architecture.md:468-473 | PASS |
| 4 | __all__ is public contract | docs/architecture.md:475-476 | PASS |
| 5 | lazy-loader out of scope, cites both packages | docs/architecture.md:478-480 | PASS |
| 6 | __dir__ optional | docs/architecture.md:482-484 | PASS |
| 7 | No hiding illegal deps | docs/architecture.md:486-488 | PASS |
| 8 | Both repo examples cited | docs/architecture.md:490-498 | PASS |
| 9 | No standalone file created | commit ce1b9b9 shows only M docs/architecture.md | PASS |

### Test Results

- pytest: 3689 passed, 105 failed (all pre-existing), 20 skipped
- ruff: N/A (docs-only change)

### Confidence: .97

### Action: archive

[[2026-03-21]] Sat 12:54

## Audit

### AC Verification

All 9 binding contract items PASS (docs/architecture.md:462-498). Commit ce1b9b9 modifies only docs/architecture.md.

### Test Results

- pytest: 3689 passed, 105 failed (all pre-existing), 20 skipped. No regressions from #882.
- ruff: N/A (docs-only)

### Confidence: .97

### Action: archive
