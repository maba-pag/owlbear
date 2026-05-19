---
id: 887
title: Add package-root lazy-export policy note to docs/architecture.md
status: archived
priority: nice-to-have
created: 2026-03-21T05:06:16.0354924+01:00
updated: 2026-03-21T13:33:24.6107605+01:00
started: 2026-03-21T13:33:19.2260314+01:00
completed: 2026-03-21T13:33:19.2260314+01:00
tags:
    - docs
    - architecture
    - scope:tools
    - type:docs
parent: 882
class: standard
---

Add a short subsection to docs/architecture.md under the architecture design-rules area describing OwlBear's package-root lazy-export policy. Capture when cached module-level __getattr__ import maps are allowed (only for deliberate public package roots with measured eager-import side effects or optional-dependency pressure), why __all__ stays explicit and limited to the supported surface, why lazy-loader stays out of scope for small fixed surfaces like owlbear.tools and owlbear.memory.knowledge, and that __dir__ is optional rather than default. State explicitly that lazy exports are not a substitute for fixing illegal dependency edges. Cite src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py as the current repo examples. See docs/research/package-root-lazy-export-pattern.md. AC: (1) docs/architecture.md gains a short policy note with those rules, (2) the note names both current repo examples, (3) the note states that __all__ is the public contract and __getattr__ is an implementation detail, (4) no new standalone architecture note file is created.

[[2026-03-21]] Sat 05:43

## Research

Validated that #887 is already the concrete implementation follow-up created from docs/research/package-root-lazy-export-pattern.md and does not need a new split or decision request.

- Existing doc remains the research deliverable: docs/research/package-root-lazy-export-pattern.md.
- Source basis checked:
  - Local: docs/research/package-root-lazy-export-pattern.md, docs/research/tools-init-side-effects.md, docs/architecture.md, src/owlbear/tools/__init__.py, src/owlbear/memory/knowledge/__init__.py.
  - External already logged in docs/sources/overview.md: Python data model docs, PEP 562, PEP 8 public/internal interfaces, Scientific Python SPEC 1, and lazy-loader docs.
- Findings:
  - Python data model docs plus PEP 562 support module-level __getattr__ as the standard lazy package-root hook; __dir__ is optional ergonomics, not mandatory policy.
  - PEP 8 plus the current repo implementations support keeping __all__ explicit as the public contract while treating the lazy import map and __getattr__ as implementation detail.
  - SPEC 1 plus lazy-loader docs support lazy exports as a valid mechanism but explicitly do not recommend them for every project; OwlBear's small fixed surfaces (owlbear.tools and owlbear.memory.knowledge) do not justify helper dependency or stub-management overhead.
  - docs/research/tools-init-side-effects.md plus the current package roots support the boundary that lazy exports must not be used to hide illegal dependency edges.
- Architecture fit:
  - The canonical destination remains docs/architecture.md; no standalone architecture note file is warranted.
  - #887 is ready for architect review as written.
- Follow-up tasks:
  - No new kanban-md create commands executed. #887 itself is the already-created implementation follow-up from #882, and #883 already isolates the optional __dir__ ergonomics question.
- Attribution:
  - No new docs/sources/overview.md rows added because this task reuses the existing research document and its already-logged external sources.

[[2026-03-21]] Sat 06:09

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) docs/architecture.md gains a short policy note with those rules. | Single docs concern and correct canonical destination, but the task body references a generic "design-rules area" rather than an existing heading in docs/architecture.md. | Approve with a binding insertion target: add the note as a short subsection under ## 8. Key Design Decisions. |
| (2) The note names both current repo examples. | Verifiable against the two live package-root lazy-export implementations. | Keep. |
| (3) The note states that __all__ is the public contract and __getattr__ is an implementation detail. | Precise, aligns with the existing package-root implementations, and keeps the supported surface explicit. | Keep. |
| (4) No new standalone architecture note file is created. | Preserves docs/architecture.md as the single long-lived architecture source of truth. | Keep. |

### Architecture Notes

- docs/architecture.md currently exposes ## 8. Key Design Decisions as the stable insertion point for this policy note; there is no existing "design-rules" heading to target directly.
- Current repo examples are src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py. Both use explicit __all__ plus cached module-level __getattr__ maps and omit __dir__, so the note should document that bounded pattern rather than generic lazy loading.
- Single-domain check passes: this is a docs/architecture change only. Related runtime ergonomics remain isolated in #883.
- TDD: not applicable. This task changes architecture documentation only and introduces no runtime behavior.
- Failure mode map: not required for a docs-only task.

### Binding Contract

1. docs/architecture.md gains a short subsection under ## 8. Key Design Decisions, titled Package-root lazy exports or an equivalently explicit heading.
2. The note states OwlBear defaults to direct imports or eager re-exports for ordinary package roots.
3. The note states cached module-level __getattr__ import maps are allowed only for deliberate public package roots with measured eager-import side effects, optional-dependency pressure, or import-cycle pressure.
4. The note states __all__ is the supported public contract and the lazy import map plus __getattr__ are implementation details.
5. The note states lazy-loader is out of scope for OwlBear's current small fixed public surfaces, specifically owlbear.tools and owlbear.memory.knowledge.
6. The note states __dir__ is optional ergonomics and not part of the default policy.
7. The note states lazy exports must not be used to hide illegal dependency edges; layering problems must be fixed first.
8. The note cites src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py as the current repo examples.
9. No new standalone architecture note file is created.

### Changes Made

- Claimed #887 as architect.
- Appended this architecture review with the concrete docs/architecture.md insertion target.
- No new tasks created; #883 remains the separate optional __dir__ ergonomics follow-up.

### Dependencies

- Verified: no predecessor task is required for this docs-only change.
- Related: #882 is the parent research track; #887 is the concrete execution leaf for the architecture-document update.
- Related: #883 remains out of scope for this task.

[[2026-03-21]] Sat 06:27

## Test-Writer Notes

- Non-implementation task (tagged docs, type:docs) — no tests applicable.
- Passing through to builder.

[[2026-03-21]] Sat 06:51

## Builder Notes

- Files changed: docs/architecture.md (already committed in ce1b9b9 under parent #882)
- Tests: N/A (docs-only task; test-writer confirmed pass-through)
- Lint: N/A (no .py files changed)
- Evidence:
  - AC(1): ### Package-root lazy exports subsection present under ## 8. Key Design Decisions
  - AC(2): Both repo examples cited: src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py
  - AC(3): '__all__ is the supported public contract' + '__getattr__ are implementation details' stated explicitly
  - AC(4): git show ce1b9b9 --name-only shows only docs/architecture.md, no new standalone file
  - Architect Binding Contract: all 9 items verified against section text
- Fixes applied: None — section already committed; builder verified AC coverage

[[2026-03-21]] Sat 12:32

## Review Evidence

## Review: #887 - Add package-root lazy-export policy note to docs/architecture.md

### Test Results

- Command: uv run pytest tests/test_knowledge_init_trim.py -q --tb=short
- Result: 26 passed, 2 warnings, exit code 0.

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: exit code 1 with 460 pre-existing findings outside #887 scope.

### Coverage

- Not applicable for docs-only task.

### Pass 1 - CRITICAL

- Security review: No in-scope issues; docs-only change.
- Test integrity: Not applicable; no test files changed.
- Test quality: Not applicable; AC is documentation assertions only.
- Data safety: No in-scope issues; no runtime/data-path changes.

### AC Compliance

1. AC1 PASS: policy subsection exists under ## 8. Key Design Decisions at docs/architecture.md:444 and docs/architecture.md:462-499.
2. AC2 PASS: both repo examples named at docs/architecture.md:495 and docs/architecture.md:498.
3. AC3 PASS: __all__ contract and __getattr__ implementation-detail statement at docs/architecture.md:476-477.
4. AC4 PASS: commit ce1b9b9 changed only docs/architecture.md; no standalone architecture note file added.

### Verdict: PASS

- Confidence: .93

### Action Taken

- PASS transition to docs is justified.

[[2026-03-21]] Sat 13:33

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| (1) docs/architecture.md gains policy note | Subsection at L462 under sec 8. Key Design Decisions | PASS |
| (2) Names both repo examples | src/owlbear/tools/__init__.py (L495) and src/owlbear/memory/knowledge/__init__.py (L498) cited | PASS |
| (3) __all__ is public contract, __getattr__ is impl detail | Explicit at L476-477 | PASS |
| (4) No new standalone architecture note file | Commit ce1b9b9 only changed docs/architecture.md | PASS |

### Binding Contract (9 items)

All 9 architect binding contract items verified: (1) subsection at L462, (2) direct-imports default at L464, (3) three conditions at L466-473, (4) __all__ contract at L476-477, (5) lazy-loader out of scope at L479-482, (6) __dir__ optional at L484-486, (7) no hiding illegal edges at L488-490, (8) both examples at L493-499, (9) no standalone file.

### Test Results

- pytest: 3702 passed, 105 failed (all pre-existing: numpy compat, bootstrap unpacking, CLI daemon — none related to #887 docs-only change)
- ruff: N/A (no .py files changed)
- Commit: ce1b9b9 correctly scoped to docs/architecture.md only

### Confidence: .97

### Action: archive
