---
id: 1552
title: 'P4-02: migration verification grep gate'
status: archived
priority: important
created: 2026-05-13T18:43:53.193530+00:00
updated: 2026-05-14T12:33:25.728539+00:00
tags:
  - phase-4
  - scope:cockpit
  - test
  - frontend
parent: 1534
depends_on:
  - 1543
  - 1546
  - 1547
  - 1548
  - 1549
  - 1550
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Vitest regression gate that scans production source for leftover `--pds-theme-light-*` tokens; fix last production violation in ErrorBoundary.tsx
- **Out:** Token rename implementation (done in P1-02 #1543 and downstream tasks); test-file-only debt (stale assertions in ResponsiveLayout_1391 — already failing, separate concern)

## Acceptance Criteria

- AC-1: A Vitest test under `serve/cockpit/web/src/__tests__/` recursively scans `.css`, `.tsx`, `.ts` files under `serve/cockpit/web/src/` (excluding `__tests__/` directories) for `/--pds-theme-light-[a-z0-9-]+/` matches and asserts zero violations, reporting file:line detail for each
- AC-2: `ErrorBoundary.tsx:30` inline style `var(--pds-theme-light-contrast-medium)` is replaced with the agnostic `var(--pds-contrast-medium)`, removing the last production-code legacy token
- AC-3: The test reuses the recursive file-discovery pattern from `PDSHexScan_1395.test.ts` (walk directory, read file, match regex, collect violations)

Proof bundle: behavioral

## Research

**Key findings:**
- Pattern proven in codebase: PDSHexScan_1395.test.ts does recursive broad-scan with line-level filtering — same pattern applies here
- 1 real production violation remains: `ErrorBoundary.tsx:30` (runtime usage missed by #1543)
- Stale test assertions in ResponsiveLayout_1391.test.tsx already fail (Shell.css migrated) — not in scope
- Recommended approach: production-file-only scan (no smart filtering needed)

**Trade-off matrix:** doc at `.owlbear/research/1552-migration-grep-gate.md` §3

**Tier:** T1 — regression guard, no architecture/security/capability change
2026-05-14T11:39:02+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: grep gate regression test + trivial 1-line fix to make it pass |
| Interface clarity | PASS | After refinement — AC-1 specifies regex, scope, exclusions, assertion shape; AC-2 names exact file:line and replacement; AC-3 names pattern source |
| Dependency correctness | PASS | All 6 deps (1543, 1546–1550) archived/completed |
| Module layering | PASS | Test file only, no import layering concerns |
| TDD compliance | PASS | Tagged `test` — test-writer passes through; deliverable IS a test |
| KISS/YAGNI | PASS | Simplified scope from original research recommendation: production-only scan eliminates smart-filtering complexity entirely |
| Premise challenge | PASS | Gate prevents accidental legacy token reintroduction after migration; PDSHexScan proves the pattern works in this codebase |
| Pattern consistency | PASS | Follows PDSHexScan_1395.test.ts recursive broad-scan pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only (scope:cockpit) |

### Challenge Results
- Challenger: reconsider (0.31 confidence)
- Key findings: (1) filtering-feasibility — 3-rule smart-filtering heuristic doesn't cover multi-line patterns; (2) ac-quality — undefined exclusion classes; (3) canonical-artifact drift — refined AC not yet in task body
- Architect response: ACCEPTED all findings. Resolved by simplifying scope to production files only (exclude `__tests__/`), eliminating the need for smart filtering entirely. This follows the PDSHexScan pattern which also excludes test dirs. Stale test assertions (ResponsiveLayout_1391) already fail because Shell.css was migrated — self-correcting, not a regression risk. Rewrote AC into task body with specific, mechanically verifiable criteria.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: SKIP (tag `test` — pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC (simplified scope to production-only scan, specified exact violation file:line, named pattern source), wrote refined body, advanced to todo
2026-05-14T11:49:57+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Deliverable IS the test file (AC-1: Vitest grep gate) + production fix (AC-2: ErrorBoundary.tsx). Builder implements both.
- Pattern source referenced in AC-3: `PDSHexScan_1395.test.ts` recursive broad-scan with `__tests__/` exclusion.
- Passing through to builder.
2026-05-14T12:04:11+00:00
## Builder Notes
### Files Changed
- serve/cockpit/web/src/__tests__/ThemeLightTokenScan_1552.test.ts
- serve/cockpit/web/src/components/ErrorBoundary.tsx

### Fixes Applied
- Added a new Vitest regression gate that recursively scans production source files under `src/` for legacy tokens matching `/--pds-theme-light-[a-z0-9-]+/`.
- Scan includes `.css`, `.ts`, and `.tsx` files and excludes `__tests__/`, `node_modules`, `dist`, and `build` directories.
- Violation output is reported as `file:line:token` for actionable debugging.
- Replaced the remaining production legacy token in ErrorBoundary inline style:
  - `var(--pds-theme-light-contrast-medium)` -> `var(--pds-contrast-medium)`.

### Quality Evidence
- quality-runner scoped (task proof):
  - tests: 1 passed, 0 failed (`ThemeLightTokenScan_1552.test.ts`)
  - lint: clean (0 violations) on changed files
  - coverage extraction for `ErrorBoundary.tsx`: not extracted in scoped run because scanner test does not execute component runtime paths.
- quality-runner broader verification:
  - task-scoped test still passes (1/1)
  - broad-suite failures observed are unrelated pre-existing frontend/python debt and not caused by this task.

### Lint Status
- ESLint clean for changed files.

### Commit
- 095ea183
- message: test: add theme-light token grep gate and fix ErrorBoundary token (#1552, builder)
2026-05-14T12:16:23+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1552 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality evidence in task body reports `ThemeLightTokenScan_1552.test.ts` passing (1 passed, 0 failed), lint clean on changed files, and commit `095ea183`; commit presence verified in `.git/logs/HEAD:3067` and `.git/logs/refs/heads/dev:2855`.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/__tests__/ThemeLightTokenScan_1552.test.ts:11-33` recursively walks `src/`, excludes `__tests__`, `node_modules`, `dist`, `build`, and filters `.css`, `.ts`, `.tsx`; `:39-49` reads each file, applies `/--pds-theme-light-[a-z0-9-]+/g`, and records `src/...:line: token` violations; `:55-68` asserts `violations === []`. | Builder proof reports the task-scoped Vitest file passing; direct workspace grep for `--pds-theme-light-` under `serve/cockpit/web/src/**` returned matches only in `__tests__` files and this new test file, with no production-source hits. | PASS |
| AC-2 | `serve/cockpit/web/src/components/ErrorBoundary.tsx:30` now uses `var(--pds-contrast-medium)`; grep on `ErrorBoundary.tsx` shows the new token at line 30 and no remaining `var(--pds-theme-light-contrast-medium)` match in that file. | AC-1's scanner would fail on any reintroduced legacy token in production source, including `ErrorBoundary.tsx`; direct source inspection confirms the exact replacement requested by the AC. | PASS |
| AC-3 | `serve/cockpit/web/src/__tests__/ThemeLightTokenScan_1552.test.ts:11-33,39-49,55-61` follows the same broad pattern as `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:37-45,58-79,91-99`: recursive `readdirSync` walk, `readFileSync`, regex `matchAll`, and collected `violations.push(...)`. | Pattern-source comparison shows the requested reuse of the recursive discovery/read/match/collect approach, adapted from `.tsx`-only scanning to `.css`/`.ts`/`.tsx`. | PASS |
- Safety and security review: no new input handling, auth, storage, shell, or dependency surface introduced.
- Challenger cross-check returned `reconsider`, but the cited concerns are non-blocking here: AC-3 requires reuse of the recursive file-discovery pattern, not duplication of PDSHexScan's scanner self-tests; unlike PDSHexScan's filtered scanner, this task's scanner is a direct per-line regex match and is independently corroborated by workspace grep showing no production-source legacy-token matches.

## Observations
- `ErrorBoundary.tsx` does not have task-scoped runtime coverage in the builder proof, but AC-2 is a static source-contract replacement rather than a behavior-path change; direct source evidence plus the production-tree scan is sufficient for this contract.
- Current editor diagnostics are clean for both changed files (`ThemeLightTokenScan_1552.test.ts`, `ErrorBoundary.tsx`).
2026-05-14T12:18:27+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | PASS — no update needed | Changed files: `ThemeLightTokenScan_1552.test.ts` (new test file, no README-level interface change) and `ErrorBoundary.tsx` (1-line CSS token rename, internal implementation detail). Full read of `serve/cockpit/README.md`: no reference to `--pds-theme-light-*` tokens, ErrorBoundary component, or token migration. Layer 1 grep clean; Layer 2 editorial: no contradiction or coherence impact. |
| External Attribution | N/A — no external attribution needed | Implementation reused internal `PDSHexScan_1395.test.ts` pattern only; no external sources cited in builder notes or task body. |
| Research Doc | PASS — linked in task body | `.owlbear/research/1552-migration-grep-gate.md` exists; task body explicitly references it: "Trade-off matrix: doc at `.owlbear/research/1552-migration-grep-gate.md` §3". |
| Deletion Detection | N/A — no deletion impact | No files removed. One new file added, one file with a single-line edit. |

### Files Updated
None — no documentation changes required.

### Scratch Cleanup
No `.owlbear/scratch/1552-*` files found; nothing to clean.
2026-05-14T12:33:25+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: Python 6835 total (210+ pre-existing failures in kanban engine, server, memory, dispatch, and structural tests — all unrelated to this task's 2 frontend files); Vitest exit 1 from pre-existing frontend debt. Ruff: 0 violations. ESLint: 0 violations.\n- Task-scoped test (ThemeLightTokenScan_1552.test.ts): passes.\n- Regression verdict: PASS — no failures attributable to #1552. A frontend test file and 1-line CSS token rename cannot cause Python engine/server test failures.\n\n### Intent Verification\n- Scope alignment: PASS (2 files changed: ThemeLightTokenScan_1552.test.ts, ErrorBoundary.tsx — both in serve/cockpit/web/src/, matching scope:cockpit + frontend tags)\n- Purpose match: PASS (grep gate regression test + production legacy token fix, exactly as stated)\n- Extraneous scope: none\n- Boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 5/5\nAC lines are specific, mechanically verifiable (exact regex, exact file:line, named pattern source). Challenger findings addressed by simplifying scope. Clean implementation path.\n\n### Commit Integrity\n- Upstream commit presence: PASS (095ea183, HEAD of dev, message: \"test: add theme-light token grep gate and fix ErrorBoundary token (#1552, builder)\")\n- Commit scope: 2 files only (ThemeLightTokenScan_1552.test.ts + ErrorBoundary.tsx), both task-relevant\n- Kanban commit packaging: pending (Step 6)\n\n### Deduction Breakdown\n- Intent mismatch: 0\n- Evidence integrity concern: 0\n- Lint violations: 0\n- AC quality score lte 3: 0 (scored 5/5)\n- Missing reviewer evidence section: 0 (detailed PASS with per-AC mapping)\n- Regression failures: 0 (pre-existing background debt only)\n\n### Confidence: 1.00\n### Action: archive