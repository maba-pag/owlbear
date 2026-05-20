---
id: 1663
title: 'P2-02: IdeasPage — markdown preview toggle'
status: archived
priority: important
created: 2026-05-18T17:42:08.354112+02:00
updated: 2026-05-20T17:40:42.164973+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1662
ac:
  - Toggle button switches IdeasPage between edit (textarea visible) and preview
    (rendered markdown visible); only one mode active at a time; default mode is
    edit
  - Preview mode renders GFM content (tables render as <table> elements, 
    ~~text~~ as strikethrough, - [x] as checked items); raw HTML in source (e.g.
    <script>, <img onerror=...>) is stripped by rehype-sanitize default schema
  - Switching from preview back to edit preserves textarea content without data 
    loss
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Uses `ReactMarkdown` + `remark-gfm` + `rehype-sanitize` for rendering. These packages are already in `package.json` — just import them.

Follow the existing pattern from `TaskFieldsEditor.tsx` (default sanitize schema, not custom like MemoryTab).

## In Scope

- Toggle button in IdeasPage (edit ↔ preview)
- Markdown preview rendering with GFM
- HTML sanitization of rendered output (default rehype-sanitize schema)

## Out of Scope

- Edit mode textarea behavior (owned by P2-01)
- Custom markdown extensions beyond GFM
- Syntax highlighting for code blocks
- Custom sanitize schema (use default)

[[2026-05-20T16:00:39+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Toggle + preview only |
| Interface clarity | PASS | AC specifies concrete DOM outputs and sanitization behavior |
| Dependency correctness | PASS | #1638 (archived), #1662 (archived) — both complete |
| Module layering | PASS | Page-level component, no upward imports |
| TDD compliance | PASS | Test-writer writes tests first |
| KISS/YAGNI | PASS | Minimal toggle following existing pattern |
| Premise challenge | PASS | Brief specifies preview toggle; no existing IDE/lib alternative |
| Pattern consistency | PASS | Follows TaskFieldsEditor.tsx ReactMarkdown+remarkGfm+rehypeSanitize pattern |
| Security surface | PASS | rehype-sanitize default schema handles XSS; AC explicitly requires raw HTML stripping |
| Single domain | PASS | Pure cockpit-web frontend |

### Design Diverge
- Trigger: skipped — single obvious approach (follow TaskFieldsEditor pattern)

### Challenge Results
- Challenger: reconsider (0.71)
- Findings: AC2 vague on testable sanitization, stale scope re npm deps, precedent ambiguity (default vs custom schema)
- Architect response: accepted AC2 refinement (now specifies concrete rendered elements and sanitization proof); clarified body to note deps already installed and to follow TaskFieldsEditor default schema (not MemoryTab custom). Rejected proof-bundle escalation to critical — rehype-sanitize default schema is a library config, not custom security code.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC2 for concrete testability, cleaned stale scope, advanced to todo

[[2026-05-20T16:07:28+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx
- Classes: TestFromAC_IdeasPageToggle, TestFromAC_IdeasPageGFMRendering, TestFromAC_IdeasPageContentPreservation
- Tests per category: happy 8, edge 2, error 2, boundary 3
- Total: 15 tests, all FAIL
- Expected testids: `ideas-preview-toggle` (toggle button), `ideas-preview` (preview container)
- Lint: clean (ESLint 0 violations)
- AC coverage:
  - AC1 (toggle, mode exclusivity, default edit): 5 tests (TestFromAC_IdeasPageToggle)
  - AC2 (GFM table, strikethrough, task-list, script stripped, img onerror stripped, empty): 6 tests (TestFromAC_IdeasPageGFMRendering)
  - AC3 (content preserved: baseline, user-edited, empty, multiline markdown): 4 tests (TestFromAC_IdeasPageContentPreservation)
- All fail with AssertionError: expected null not to be null — toggle absent from current IdeasPage

[[2026-05-20T16:21:39+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/pages/IdeasPage.tsx
- Implementation plan:
  - Add page-local preview mode state to IdeasPage.
  - Add toggle control with required test id (`ideas-preview-toggle`) to switch edit/preview.
  - Render markdown preview via `ReactMarkdown` + `remark-gfm` + `rehype-sanitize` (default schema), while keeping edit textarea behavior unchanged.
- RED verification (quality-runner):
  - Scoped tests: `serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx`
  - Result: 0 passed, 15 failed
  - Failure pattern: all `TestFromAC_*` cases failed with missing toggle assertion (`expected null not to be null`)
  - Lint: clean
- GREEN verification (quality-runner):
  - Scoped tests: `serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx`
  - Result: 15 passed, 0 failed
  - Lint paths: `serve/cockpit/web/src/pages/IdeasPage.tsx`, `serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx`
  - Lint: clean
  - Coverage: not reported by scoped frontend run
- Module-level durable test visibility:
  - No module-level durable `IdeasPage` test file detected (task-scoped files only) — skip
- Fixes applied:
  - Imported `react-markdown`, `remark-gfm`, and `rehype-sanitize` into IdeasPage.
  - Added `previewMode` state with default edit mode (`false`).
  - Added toggle button with `data-testid="ideas-preview-toggle"` and dynamic label (`Preview`/`Edit`).
  - Added preview container `data-testid="ideas-preview"` rendering sanitized GFM markdown.
  - Kept edit mode textarea and content state unchanged, preserving content across mode switches.
  - Updated focus effect to avoid focusing textarea while in preview mode.
- Commit:
  - `feat: add IdeasPage markdown preview toggle (#1663, builder)`

[[2026-05-20T17:04:54+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1663 -> docs | AC mapped to code and evidence sufficient.
- AC1 mapping: default edit mode is driven by local preview state in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L22), the toggle control is rendered in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L267), and the edit/preview branch switch is in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L274). Task proof covers entering preview, returning to edit, and one-mode-only rendering in [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L75), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L82), and [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L90).
- AC2 mapping: preview rendering is wired through ReactMarkdown with remark-gfm and default rehype-sanitize in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L3), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L4), and [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L276). Task proof covers table, strikethrough, checked-task rendering, and unsafe DOM absence in [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L114), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L122), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L129), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L140), and [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L147).
- AC3 mapping: textarea content remains page-local state in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L21), is bound back into the textarea in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L283), and is updated from user edits in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L285). Task proof covers baseline, edited, empty, and multiline round-trips in [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L168), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L177), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L189), and [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx#L197).
- Independent verification: quality-runner recheck for [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx) reported 15 passed, 0 failed, lint clean, coverage overall 42.78 with IdeasPage.tsx at 57.03% and ideas.ts at 33.33%. Adjacent regression recheck for [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx), [serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx), and [serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx) reported 58 passed, 0 failed, lint clean, and no regression of the existing load/save and unsaved-guard contract already covered at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L216), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L258), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L362), [serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx#L89), and [serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx#L182).

## Observations
- Non-blocking: AC2 sanitization proof is acceptable for this repo because source wiring in [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L276) matches the established preview pattern in [serve/cockpit/web/src/components/TaskFieldsEditor.tsx](serve/cockpit/web/src/components/TaskFieldsEditor.tsx#L310), and the task tests verify the rendered-output contract. If the team wants stronger mutation-resistant proof later, a small plugin-props test like [serve/cockpit/web/src/__tests__/ResolveModal.plugins.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.plugins.test.tsx#L67) or [serve/cockpit/web/src/__tests__/DetailTab.gfm-plugins.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.gfm-plugins.test.tsx#L46) would be the existing local pattern.

[[2026-05-20T17:14:35+02:00]]
## Docs Gate

**Verdict:** PASS

### Checklist

1. **README Verification** — `serve/cockpit/web/src/pages/IdeasPage.tsx` maps to `serve/cockpit/README.md`. No #1663 entry existed. Added bullet after #1662 describing: toggle button (`data-testid="ideas-preview-toggle"`), edit/preview mode exclusivity, default edit mode, GFM rendering via `ReactMarkdown` + `remark-gfm` + `rehype-sanitize` (default schema), preview container (`data-testid="ideas-preview"`), label switching, content preservation across mode switches, focus behaviour, sanitization contract, and test coverage (15 tests in `IdeasPage_1663.test.tsx`). Layer 1 grep confirms #1663 present at line 487. Layer 2 editorial: entry is coherent, accurate to implementation, audience-fit, no contradictions with #1662.

2. **External Attribution** — N/A. `react-markdown`, `remark-gfm`, and `rehype-sanitize` were pre-existing dependencies. No new external sources required attribution.

3. **Research Doc** — N/A. No research artifact exists for this task.

4. **Deletion Detection** — N/A. No files deleted; only `IdeasPage.tsx` modified.

### Files Updated
- `serve/cockpit/README.md` — added #1663 bullet after #1662 entry

### Scratch Cleanup
- No `1663-*` scratch files found.

[[2026-05-20T17:40:42+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: vitest exit 0 (all frontend tests pass), pytest 256 failures ALL in unrelated kanban engine domain (test_engine_*, test_forward_skip_*, test_cockpit_mutation_api_1132_*), ruff clean, ESLint 1 pre-existing violation in SidecarUX.test.tsx (unrelated)
- regression verdict: PASS (no regressions caused by this task)

### Intent Verification
- scope alignment: PASS (changed files: IdeasPage.tsx, IdeasPage_1663.test.tsx, cockpit README -- all within scope:cockpit-web)
- purpose match: PASS (markdown preview toggle with GFM and sanitization matches stated AC)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines specific and testable after challenger refinement. AC2 initially vague on sanitization proof, resolved by architect to specify concrete rendered elements and stripping behavior. No builder improvisation required.

### Commit Integrity
- upstream commit presence: PARTIAL
  - builder: 18d48b3d PASS
  - test-writer: 3fa4e27b PASS
  - doc-writer: MISSING COMMIT (README content present in working tree at line 487 but never committed -- process concern flagged)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No rubric deductions apply:
- No intent mismatch
- No evidence integrity concern (evidence is real and correct; uncommitted README is process gap, not evidence fabrication)
- No lint violations from this task
- AC quality 4/5 (above threshold)
- Reviewer evidence section present and detailed
- No regression failures from this task

### Confidence: 1.00
### Action: archive

### Process Concern (non-scoring)
Doc-writer README update for #1663 exists in working tree (serve/cockpit/README.md line 487) but was never committed. Per w-task-verification: flagged as process gap. Auditor does NOT silently commit other agents' source code.
