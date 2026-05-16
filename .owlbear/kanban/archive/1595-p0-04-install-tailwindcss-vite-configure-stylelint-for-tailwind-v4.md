---
id: 1595
title: 'P0-04: Install @tailwindcss/vite + configure Stylelint for Tailwind v4'
status: archived
priority: critical
created: 2026-05-16T03:35:01.729375+00:00
updated: 2026-05-16T12:52:59.956367+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1592
ac:
  - PDS Tailwind utilities (bg-canvas, text-contrast-high, gap-md) compile 
    without error and light-dark() preserved in vite build
  - package.json pins tailwindcss ^4 and @tailwindcss/vite ^4; no PostCSS config
    exists; LightningCSS remains CSS transformer
  - npm run lint:css passes with zero violations on @theme, @utility, @apply 
    at-rules
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: duplicate
archival_refs:
  - 1592
---
Brief: see parent #1590.

Install `@tailwindcss/vite` as Vite plugin (NOT PostCSS — preserves LightningCSS). Import PDS Tailwind theme from `@porsche-design-system/components-react/tailwindcss/index.css`. Pin `tailwindcss ^4` + `@tailwindcss/vite ^4`. Update Stylelint config for Tailwind v4 `@theme` / `@utility` at-rules.

Scope: Tailwind install + Stylelint config.
Out of scope: Token migration, component migration, layout.

[[2026-05-16T14:12:07+02:00]]
## Research
- Research doc: .owlbear/research/1595-tailwind-stylelint-redundancy.md
- Sources: 9 studied, 6 high-relevance (1.0)
- Finding: ALL 3 ACs already satisfied by #1592 builder (commit 6a5b07b3, audit .97)
- Recommendation: Archive as superseded by #1592 (confidence: 0.95)
- Follow-up tasks created: none — no remaining work
- Decision requests: none
- AC discrepancy: `gap-md` in AC-1 is invalid; PDS uses `gap-fluid-md` (already corrected in #1592)

## Challenge Results
- Challenger: SKIPPED — no competing recommendation; finding is factual (code exists)

[[2026-05-16T14:24:29+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: Tailwind v4 + Stylelint config |
| Interface clarity | PASS | ACs are specific and testable |
| Dependency correctness | PASS | Depends on #1592 (archived, completed) |
| Module layering | PASS | Frontend domain only |
| TDD compliance | N/A | Superseded — no work to test |
| KISS/YAGNI | N/A | No implementation needed |
| Premise challenge | FAIL — SUPERSEDED | All 3 ACs already satisfied by #1592 builder (commit 6a5b07b3, audit .97) |
| Pattern consistency | N/A | No new code |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend only |

### Premise Challenge Detail
Verified in live codebase:
- package.json: @tailwindcss/vite ^4.3.0, tailwindcss ^4.3.0 (AC-2 ✅)
- vite.config.ts: imports and registers @tailwindcss/vite plugin (AC-1 ✅)
- .stylelintrc.json: 8-entry ignoreAtRules allowlist (AC-3 ✅)
- src/tailwind.css: imports tailwindcss + PDS theme (AC-1 ✅)
- No postcss.config.* exists; LightningCSS active in vite.config.ts (AC-2 ✅)
- #1592 archived with audit confidence .97, all tests pass (8/8)

### Challenger Results
- Challenger: SKIPPED — factual supersession (code exists and is audited), no competing recommendation to challenge

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: skip (superseded — no implementation work remaining)
- Test-writer: SKIP

### Design Diverge
- Trigger: skipped — task is superseded, no design decisions to make

### Verdict: ARCHIVE AS SUPERSEDED
### Action Taken: All 3 ACs satisfied by #1592 builder commit 6a5b07b3. Task has zero remaining implementation scope. Moving to done for archival with archival_refs: [1592].

[[2026-05-16T14:52:51+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: pytest 4621 passed / 224 pre-existing failures (all unrelated task-scoped tests); vitest 1895 passed / 0 failed; ruff 0 violations
- regression verdict: PASS — task has zero code changes (superseded), no regressions possible

### Intent Verification
- scope alignment: PASS (all 3 ACs confirmed satisfied by #1592 commit 6a5b07b3)
- purpose match: PASS (Tailwind v4 vite plugin, pin versions, Stylelint config — all present in live codebase)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer (N/A — superseded path)

### Architect Quality: 4/5
ACs specific and testable. Minor inaccuracy: AC-1 references `gap-md` but PDS uses `gap-fluid-md` — caught by researcher, already corrected in #1592. Premise challenge correctly identified supersession.

### Commit Integrity
- upstream commit presence: PASS — no source commits expected (superseded task); #1592 commit 6a5b07b3 verified
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
No deductions. Task is superseded with zero code changes; all ACs verified against live codebase; AC quality adequate.

### Confidence: 1.00
### Action: archive (superseded by #1592)
