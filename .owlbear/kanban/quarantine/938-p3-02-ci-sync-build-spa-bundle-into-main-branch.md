---
id: 938
title: 'P3-02: CI sync — build SPA bundle into main branch'
status: archived
priority: important
created: 2026-04-17T19:59:26.740493+00:00
updated: 2026-04-19T16:00:32.976466+00:00
tags:
- cockpit
- phase-3
- type:config
parent: 920
depends_on:
- 937
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Extend the sync-to-main GitHub Actions workflow to build the SPA bundle so consumer-side users need no Node toolchain (D15).

## Acceptance Criteria

- [ ] Workflow adds SHA-pinned `actions/setup-node` (matching existing `actions/checkout` pattern) reading `serve/cockpit/web/.nvmrc`
- [ ] Workflow adds `npm ci && npm run build` step with `working-directory: serve/cockpit/web`
- [ ] Post-build assertion step verifies `serve/cockpit/dist/index.html` exists before staging
- [ ] `git add -f serve/cockpit/dist/` stages the built bundle into the consumer commit
- [ ] New steps inserted between "Build consumer tree" and "Detect changes"
- [ ] Build failure blocks the sync (non-zero exit fails the job — default GHA behavior, no override needed)
- [ ] `serve/cockpit/web/node_modules/` never staged (only `dist/` is force-added)

## Files

- `.github/workflows/sync-to-main.yml` (updated)
[[2026-04-19]]

## Research

- Research doc: .owlbear/research/938-ci-sync-spa-bundle.md
- Sources: 7 studied, 4 high-relevance (all codebase-internal)
- Recommendation: Add 3 workflow steps (setup-node, npm ci+build, git add -f serve/cockpit/dist/) between "Build consumer tree" and "Detect changes" (confidence: 0.92)
- Follow-up tasks created: none needed — task #938 itself is the implementation task with concrete AC
- Decision requests: none (T1 — autonomous CI config change)

## Challenge Results

- Challenger: SKIPPED — single viable approach, no trade-off between options
- Key insight: build output is at serve/cockpit/dist/ (not web/dist/) due to vite outDir: '../dist'
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file change: `.github/workflows/sync-to-main.yml` |
| Interface clarity | PASS | AC now specifies exact actions, SHA-pinning, insertion point, and post-build assertion |
| Dependency correctness | PASS | Depends on #937 (archived/done). No runtime deps beyond Node/.nvmrc |
| Module layering | N/A | Workflow config, not Python code |
| TDD compliance | PASS | Tagged `type:config` — test-writer pass-through. No testable Python code |
| KISS/YAGNI | PASS | 3-4 workflow steps, no over-engineering |
| Premise challenge | PASS | Consumer users must not need Node toolchain — this is the minimal solution |
| Pattern consistency | PASS | SHA-pinned actions match existing `actions/checkout` pattern |
| Security surface | PASS | `npm ci` uses lockfile (deterministic). SHA-pinned action prevents supply-chain attack |
| Single domain | PASS | CI/build domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `npm ci` | npm registry unreachable | Non-zero exit | Yes (job fails) | Sync blocked — retry manually |
| `npm run build` | TypeScript/Vite build error | Non-zero exit | Yes (job fails) | Sync blocked — fix source on dev |
| `git add -f dist/` | dist/ empty/missing | Silent (no files staged) | Now handled — post-build assertion catches this |
| package-lock.json | Lockfile drift from package.json | npm ci fails | Yes (job fails) | Confusing error — dev must regenerate lockfile |

### AC Refinements Applied

- AC1: Split into setup-node (SHA-pinned) + npm build + staging steps for precision
- AC3 removed: "consumer clone works without Node" was untestable in-pipeline — captured by Objective section
- Added: post-build assertion (`dist/index.html` exists) to catch misconfiguration
- Added: explicit insertion point ("between Build consumer tree and Detect changes")
- Tags: replaced `docs` + `type:build` with `type:config` (correct pass-through tag for CI YAML change)

### Challenge Results

- Challenger: **reconsider** (confidence: 0.70)
- Key concerns: (1) SHA-pinning not in original AC, (2) no post-build validation, (3) AC3 untestable
- Architect response: **accepted** — all three concerns addressed via AC refinement

### Verdict: APPROVE (after REFINE)

### Action Taken: Tightened AC with SHA-pinning, post-build assertion, explicit insertion point. Fixed tags for correct pipeline pass-through. Advanced to todo

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `type:config`) — no tests applicable.
- AC describes only `.github/workflows/sync-to-main.yml` modifications (setup-node, npm ci+build, git add -f dist/).
- No testable Python interfaces exist. Step 2a heuristic: AC references only `.yml` and CI steps — no `implement`, `function`, `class`, or `.py` keywords.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `.github/workflows/sync-to-main.yml` — inserted 4 new steps between "Build consumer tree" and "Detect changes"

### Steps Added

1. **Setup Node.js** — `actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4`, reads `serve/cockpit/web/.nvmrc` (SHA-pinned, matching existing `actions/checkout` pattern)
2. **Build cockpit SPA** — `npm ci && npm run build` with `working-directory: serve/cockpit/web`
3. **Assert SPA bundle exists** — shell guard: exits 1 if `serve/cockpit/dist/index.html` missing
4. **Stage built SPA bundle** — `git add -f serve/cockpit/dist/` (only dist/, node_modules never touched)

### AC Verification

- [x] SHA-pinned `actions/setup-node` with `node-version-file: serve/cockpit/web/.nvmrc`
- [x] `npm ci && npm run build` with correct `working-directory`
- [x] Post-build assertion on `serve/cockpit/dist/index.html` before staging
- [x] `git add -f serve/cockpit/dist/` stages bundle
- [x] Inserted between "Build consumer tree" and "Detect changes"
- [x] Build failure blocks sync (default GHA behavior)
- [x] `node_modules/` never staged

### Test Results

- `type:config` task — no Python tests applicable (test-writer pass-through)
- YAML syntax validated: `yaml.safe_load` → OK

### Lint

- `uv run ruff check` — no Python files changed, N/A
[[2026-04-19]]

## Review Evidence

### Test / Lint / Coverage

- **Quality-Runner**: N/A — `type:config` task. No Python files changed, no `TestFromAC_*` classes exist.
- **Test-Writer pass-through**: Correct per Step 2a heuristic (AC references only `.yml` and CI steps).
- **YAML validation**: Builder reports `yaml.safe_load` OK. Manually confirmed structure is well-formed.
- **Sections 5.0, 5.2, 5.3, 5.4, 5.5**: All skipped (conditional — no `TestFromAC_*`, no Python implementation paths).

### AC Compliance Table

| AC Line | Evidence (file:line) | Status |
|---------|----------------------|--------|
| SHA-pinned `actions/setup-node` reading `.nvmrc` | `uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4` + `node-version-file: serve/cockpit/web/.nvmrc` — sync-to-main.yml ~L84 | PASS |
| `npm ci && npm run build` with `working-directory: serve/cockpit/web` | "Build cockpit SPA" step — sync-to-main.yml ~L88 | PASS |
| Post-build assertion on `serve/cockpit/dist/index.html` | "Assert SPA bundle exists" shell guard exits 1 if file absent — sync-to-main.yml ~L91 | PASS |
| `git add -f serve/cockpit/dist/` stages bundle | "Stage built SPA bundle" step — sync-to-main.yml ~L98 | PASS |
| Steps inserted between "Build consumer tree" and "Detect changes" | Order verified: Build consumer tree → Setup Node.js → Build cockpit SPA → Assert → Stage → Detect changes | PASS |
| Build failure blocks sync | No `continue-on-error` on any new step; GHA default fail-fast applies | PASS |
| `node_modules/` never staged | Only `git add -f serve/cockpit/dist/` issued; `node_modules/` untracked and never touched by any `git add` | PASS |

### Security Review (OWASP Top 10 scan)

1. **Hardcoded secrets**: None.
2. **Injection**: All paths are static literals (`serve/cockpit/dist/`, `serve/cockpit/web`). No user-controlled input in shell.
3. **Path traversal**: N/A — static paths only.
4. **Insecure deserialization**: N/A — no serialization in CI YAML.
5. **Supply-chain (dependency risk)**: `actions/setup-node` is SHA-pinned — this is the correct mitigation. Pattern matches existing `actions/checkout` SHA pin.
6. **Secret leakage**: Failure messages reference only paths, no credentials/PII.

All clean.

### Deductions

None.

### Verdict

All 7 AC lines PASS. Security clean. Test pass-through is properly justified by `type:config` tag and zero Python interfaces. Implementation is minimal and correct.

**Confidence: 0.97 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `sync-to-main` now builds + ships `serve/cockpit/dist/` — `copilot-instructions.md` Section 2 paragraph and Section 3 "Build output"/"Node requirement" rows updated to reflect pre-built dist in main and dev-only Node requirement |
| 2 | Module docstrings | No | N/A | No Python files changed — only `.github/workflows/sync-to-main.yml` |
| 3 | External attribution | No | N/A | All 4 high-relevance sources were codebase-internal (confirmed in research doc) |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/938-ci-sync-spa-bundle.md` exists and linked from task body; follow-up tasks noted as "none needed" |

### Files Updated

- `.github/copilot-instructions.md` — commit `5b745082dab61f4d797614b1a7aa9db98eca56b7`

### Scratch Files Cleaned

- None found (`.owlbear/scratch/938-*` — no matches)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| SHA-pinned `actions/setup-node` reading `.nvmrc` | sync-to-main.yml:L84-86 — `actions/setup-node@49933ea...# v4` + `node-version-file: serve/cockpit/web/.nvmrc` | PASS |
| `npm ci && npm run build` with `working-directory: serve/cockpit/web` | sync-to-main.yml:L88-89 — "Build cockpit SPA" step | PASS |
| Post-build assertion on `serve/cockpit/dist/index.html` | sync-to-main.yml:L91-96 — shell guard exits 1 if file absent | PASS |
| `git add -f serve/cockpit/dist/` stages bundle | sync-to-main.yml:L99 — "Stage built SPA bundle" step | PASS |
| Steps between "Build consumer tree" and "Detect changes" | Verified order: Build consumer tree → Setup Node.js → Build cockpit SPA → Assert → Stage → Detect changes | PASS |
| Build failure blocks sync | No `continue-on-error` on any new step; GHA default fail-fast | PASS |
| `node_modules/` never staged | Only `git add -f serve/cockpit/dist/` issued; no broader git add | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all pre-existing in mcp-knowledge domain — `test_get_stats_*`, `test_limit_forwarded_*`, `test_skill_md_*` — none in task scope)
- ruff: clean, no violations

### Architect Quality: 5/5

AC was precise after challenge-driven refinement: SHA-pinning, exact commands, exact paths, insertion point, post-build assertion. No builder improvisation required. Challenger concerns were addressed via AC refinement before development.

### Deduction Breakdown

- Start: 1.00
- AC lines with no evidence: 0 (all 7 verified) → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: no (score 5/5) → no deduction
- Missing reviewer evidence: no (detailed, 0.97 PASS) → no deduction
- Full-suite failures in task scope: 0 → no deduction
- Pre-existing failures (6, mcp-knowledge): noted, not in scope, no deduction

### Confidence: 1.00

### Action: archive
