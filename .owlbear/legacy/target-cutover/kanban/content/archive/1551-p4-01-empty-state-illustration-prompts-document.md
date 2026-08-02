---
id: 1551
title: 'P4-01: empty state illustration prompts document'
status: archived
priority: medium
created: 2026-05-13T18:43:53.131232+00:00
updated: 2026-05-13T22:19:40.734681+00:00
tags:
  - phase-4
  - scope:cockpit
  - docs
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Markdown document with image-generation prompts for each of the 7 board column statuses (research, backlog, todo, in-progress, review, docs, done), including dimensions, file type, creative direction, and visual tone
- **Out:** Actual image generation (user action), image rendering code (done in column CSS task)

## Acceptance Criteria

- AC-1: Markdown file exists at `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md` containing one image-gen prompt per board column status (7 prompts)
- AC-2: Each prompt specifies target column status name, image dimensions, file format, and creative direction describing the intended visual tone

Proof bundle: skip
2026-05-13T19:16:58+00:00
## Research
- Research doc: .owlbear/research/1551-empty-state-illustration-prompts.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: PNG 320×240, transparent bg, flat muted-pastel line-art with owl-bear mascot (confidence: .85)
- Follow-up tasks created: none (task itself advances)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial docs task, no architecture decision
- Confidence in original: .85
- Key specs: 4:3 landscape, 2× retina, muted pastels to respect enduser "receding" guidance
- Researcher response: N/A (no challenge needed)
2026-05-13T19:51:56+00:00
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | One deliverable: prompts markdown document |\n| Interface clarity | PASS | AC specifies exact file path, 7-prompt structure, per-prompt fields |\n| Dependency correctness | PASS | No deps needed; document is independent of implementation |\n| Module layering | N/A | No code modules |\n| TDD compliance | N/A | Proof bundle `skip`; docs pass-through |\n| KISS/YAGNI | PASS | Minimal scope — one structured document |\n| Premise challenge | PASS | Brief D11 mandates prompts document; research validates approach |\n| Pattern consistency | PASS | Artifact path follows `.owlbear/briefs/{slug}/` convention |\n| Security surface | PASS | No system boundaries; static document |\n| Single domain | PASS | Documentation/design only |\n\n### User-Action Detection Override\nPlanner tagged `type:user-action` but M/S/C rule evaluation fails:\n- M2 not met: AC is structurally verifiable (file exists, 7 sections, each has required fields)\n- 0/3 signals: no physical-action verbs, no external systems, no manual steps\n- Builder can produce this document using research-provided creative parameters\n- Tag removed; `docs` pass-through tag retained\n\n### Proof-Bundle Validation\n- Planner assignment: `skip`\n- Final bundle: `skip`\n- Existing proof scope: N/A\n- Test-writer: SKIP\n\n### Challenge Results\n- Challenger: SKIPPED — proof bundle `skip`\n\n### Design Diverge\n- Trigger: skipped — single valid approach (structured prompts doc per research specs)\n\n### Verdict: APPROVE\n### Action Taken: Removed incorrect `type:user-action` tag (failed M/S/C rule). Retained `docs` pass-through tag. Advanced backlog → todo.
2026-05-13T20:15:12+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Also tagged `docs` (non-implementation pass-through).
- Passing through to builder.
2026-05-13T20:42:05+00:00
Implemented AC-complete prompts document for board empty-state illustrations.

## Builder Notes
- Files changed:
  - .owlbear/briefs/draft-board-visual-design/empty-state-prompts.md (new)
- Acceptance criteria evidence:
  - AC-1: Created markdown file at required path with one prompt for each of 7 statuses: research, backlog, todo, in-progress, review, docs, done.
  - AC-2: Each status section includes explicit target status name, dimensions (320x240, 4:3), file format (PNG transparent), and creative direction/visual tone.
- Test results:
  - Proof bundle: skip (docs pass-through task; no test execution required).
- Lint status:
  - N/A for this docs-only artifact.
- Evidence summary:
  - Document follows research recommendation (muted pastel flat line-art, owl-bear mascot, transparent background, 2x-retina source sizing).
- Fixes applied:
  - Added structured, reusable prompt template style across all seven statuses to ensure generation consistency.
2026-05-13T21:14:44+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1551 -> docs | AC mapped to document and evidence sufficient.
- Builder evidence review: Builder file list and AC summary matched direct inspection of `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md`. Builder marked lint as `N/A`, so reviewer ran an independent scoped markdown lint check.
- AC evidence map:

| AC Line | Code Evidence | Test/Lint Evidence | Status |
|---|---|---|---|
| AC-1 | `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md:13`, `:26`, `:39`, `:52`, `:65`, `:78`, `:91` define the seven status sections; `Prompt:` blocks at `:20`, `:33`, `:46`, `:59`, `:72`, `:85`, `:98` provide one image-gen prompt per status. | Proof bundle `skip`; structural AC verified directly from the artifact. | PASS |
| AC-2 | `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md:15-18`, `:28-31`, `:41-44`, `:54-57`, `:67-70`, `:80-83`, `:93-96` each specify target status name, dimensions, file format, and creative direction. | Independent scoped markdown lint via `quality-runner`: `markdownlint` exit code `0`, 0 violations for `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md`. | PASS |

- Proof sufficiency: The AC is purely structural and the document provides direct, falsifiable proof for every required field; no executable behavior or existing-proof requirement is in scope.
- Safety & security: Static markdown artifact only; no input handling, secrets, or executable surface introduced.

## Observations
- Non-blocking: docs-only `skip` tasks should still record explicit markdown lint status in Builder Notes instead of `N/A`; this review passed because the reviewer independently supplied the missing lint evidence.
- Non-blocking: direct `git status` was not available in this tool session, so contamination checking relied on available workspace signals rather than a shell-level scoped status command.
2026-05-13T21:51:03+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | Changed file `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md` has no convention mapping — `.owlbear/briefs/**` is outside all `serve/{pkg}/src/**`, `setup/**`, `share/**` patterns. No public interface changed. |
| 2. External Attribution | PASS | `.owlbear/sources/overview.md` already contains `## Empty State Illustration Prompts Research (Task #1551)` with both external sources (UX Planet, Mockplus) present and correctly attributed. |
| 3. Research Doc | PASS | `.owlbear/research/1551-empty-state-illustration-prompts.md` exists and is linked in the task body (`Research doc:` field). |
| 4. Deletion Detection | N/A | Builder created one new file only; no deletions, no orphaned references. |

### Files Updated
None — no docs impact.

### Scratch Cleanup
No `.owlbear/scratch/1551-*` files existed.
2026-05-13T22:19:40+00:00
## Audit
### Regression Detection
- quality-runner mode full: 221 Python failures, 16 frontend failures — all in unrelated modules (test_support_module_migration, test_engine_dep_lookup, test_dispatch_gate_port, test_frontend_polling). Lint clean (ruff 0, eslint 0).
- builder commit 18ca2372 touched only `.owlbear/briefs/draft-board-visual-design/empty-state-prompts.md` — zero causal link to any failure.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single markdown file in `.owlbear/briefs/` — docs/design domain matches task scope)
- purpose match: PASS (7 status prompts with dimensions, format, creative direction per AC)
- extraneous scope: none (1 file, 101 lines)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
- AC-1/AC-2 are specific and structurally verifiable (exact path, 7 prompts, named fields).
- Proof bundle `skip` correct for docs-only task.
- Architecture review caught and corrected incorrect `type:user-action` tag — good upstream QA.
- No edge-case gaps for a static document deliverable.

### Commit Integrity
- upstream commit presence: PASS (18ca2372 `docs: add empty state illustration prompts (#1551, builder)`)
- commit scope: single deliverable file only — clean
- kanban commit packaging: pending (this step)

### Review Evidence Assessment
- Reviewer evidence: PASS — detailed AC map with line-number citations, independent markdown lint run (markdownlint exit 0), safety assessment, two non-blocking observations noted.

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive