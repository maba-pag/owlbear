---
id: 1486
title: 'P1-05: Update w-tdd-green handling for skip/existing bundles'
status: archived
priority: medium
created: 2026-05-11T08:59:01.954913+00:00
updated: 2026-05-11T16:13:45.510044+00:00
tags:
- pipeline
- convention
- scope:skills
- agent
parent: 1481
depends_on:
- 1482
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. Builder handles skip/existing bundles: implement from AC directly (no tests to pass)
2. For `existing` bundle, builder ensures named existing tests still pass
3. Legacy td:0 pass-through check replaced with bundle-based routing

## Scope

- In: `share/skills/w-tdd-green/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481


## Architecture Review

**Verdict:** APPROVED

**AC Assessment:**

| AC Line | td | Assessment |
|---------|------|-----------|
| 1. Builder handles skip/existing bundles: implement from AC directly (no tests to pass) | td:0 | Clear — describes what the skill text should say about bundle routing |
| 2. For `existing` bundle, builder ensures named existing tests still pass | td:0 | Clear — existing `Existing proof required:` format is visible in the target file |
| 3. Legacy td:0 pass-through check replaced with bundle-based routing | td:0 | Clear — targets the `"All AC lines are (td:0)"` condition in Step 0a |

**Architecture Notes:**
- Single file scope (`w-tdd-green/SKILL.md`), no runtime code
- Non-impl pass-through (test-writer notes "Non-implementation task") remains separate from bundle routing
- Bundle routing replaces ONLY the td:0 condition; non-impl early-exit preserved
- `Existing proof required:` field format already in-file — builder preserves it under `existing` bundle path
- Dependency #1482 (taxonomy definition) is done/archived

**Test-writer:** SKIP — all AC td:0
**Challenger:** skipped (all td:0)
[[2026-05-11]]
## Architecture Review

Verdict: APPROVED → todo

- All 3 AC lines are td:0 (skill-document edits, no testable Python interface)
- Single file scope: `share/skills/w-tdd-green/SKILL.md`
- Dependency #1482 satisfied (archived)
- Non-impl pass-through preserved; only td:0 condition replaced with bundle routing
- Challenger skipped (all td:0)
[[2026-05-11]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines are td:0 (skill-document edits to `w-tdd-green/SKILL.md`, no testable Python interfaces).
- Architecture Review explicitly annotated: "Test-writer: SKIP — all AC td:0".
- Proof bundle: skip.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Implementation: updated share/skills/w-tdd-green/SKILL.md Step 0a to bundle-based routing.
- Routing change: replaced legacy td:0 trigger with `Proof bundle` handling (`skip` and `existing`) and retained td mapping only as compatibility fallback via `r-pipeline-protocol`.
- `existing` path: requires named `Existing proof required: ...` execution via quality-runner and blocks advance when missing/failing.
- `skip` path: explicit AC-direct pass-through with no `TestFromAC_*` pass requirement.
- Tests: Proof bundle is `skip` for this task; no runtime test execution required.
- Lint: not applicable for this doc-only skill update.
- Evidence summary: single-file surgical edit, commit af62c0a8.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner executed a scoped lint-only review for this td:0 markdown skill task on `share/skills/w-tdd-green/SKILL.md`.
- Tests: 0 passed, 0 failed, 0 skipped. Runner note: `No test_paths provided (td:0 markdown skill documentation review)`.
- Review cycle: first review. No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md`.

### Lint
- quality-runner markdownlint result: `clean: false`.
- Blocking violations are in the edited Step 0a block of `share/skills/w-tdd-green/SKILL.md`:
  - `MD032` at lines 43, 47, 48, 49, 56, 57 (`Lists should be surrounded by blank lines`)
  - `MD007` at lines 44, 45, 46, 47, 49, 50, 51, 52, 53, 54, 55, 56 (`Unordered list indentation`)
- This is review-relevant because the parent proof-bundle brief defines reviewer scope for `skip` tasks as lint-only, and this child task is a single markdown skill-file change.

### Coverage
- N/A for markdown-only skill task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Builder handles skip/existing bundles: implement from AC directly (no tests to pass) | `share/skills/w-tdd-green/SKILL.md:41-56` now contains explicit `Proof bundle: skip` and `Proof bundle: existing` branches. Parent brief requires `w-tdd-green` to handle skip/existing at `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:115-117,165-169`. | PASS |
| 2. For `existing` bundle, builder ensures named existing tests still pass | `share/skills/w-tdd-green/SKILL.md:48-55` instructs the builder to find the named existing proof, run it through Quality-Runner, record the summary, and block advance when proof is missing or failing. | PASS |
| 3. Legacy td:0 pass-through check replaced with bundle-based routing | `share/skills/w-tdd-green/SKILL.md:41,57-58` routes from `Proof bundle:` first and keeps legacy `(td:N)` only as compatibility fallback when `Proof bundle:` is absent. Parent brief compatibility mapping is at `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:137-146`. | PASS |

### Findings
- The substantive AC text landed in the only in-scope file, but the edited Step 0a block does not pass markdownlint.
- Non-blocking observation: terminology remains mixed across the reform (`Existing proof scope:` in `share/skills/w-arch-review/SKILL.md:100-105` versus `Existing proof required:` here, `share/skills/w-tdd-red/SKILL.md:107-110`, and `share/skills/w-code-review/SKILL.md:92-94`). Task 1486's Architecture Review explicitly bound this child task to preserving the existing in-file label, so this inconsistency is noted but not used as a gating failure for 1486.

### Deductions
- `-0.12` lint failure in the changed lines of the only deliverable.
- `-0.02` direct `git diff/status` evidence was unavailable from the current reviewer tool surface; commit existence and task-parent brief context were verified independently, and the gating defect is artifact-local.
- Confidence: `.86`

### Verdict
- FAIL -> in-progress
- Reason: AC content is present, but reviewer-scope lint fails on the changed Step 0a block in the only in-scope file.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Fix the markdownlint failures in the new Step 0a bundle-routing list by adding the required blank lines and correcting nested-list indentation | `share/skills/w-tdd-green/SKILL.md` | quality-runner lint report: `MD032` at lines 43, 47, 48, 49, 56, 57 and `MD007` at lines 44-56 |

### Action
- Rejected to `in-progress` for builder cleanup.
[[2026-05-11]]
## Builder Notes
- Implementation: adjusted Step 0a formatting in `share/skills/w-tdd-green/SKILL.md` to resolve markdownlint failures while preserving bundle-routing behavior.
- Scope: single-file surgical doc edit (no runtime code changes).
- Quality-Runner: scoped lint-only verification on `share/skills/w-tdd-green/SKILL.md` is clean (0 violations, markdownlint exit 0).
- Tests: none required for this `Proof bundle: skip` doc task.
- Coverage: N/A (documentation-only change).
- Commit: `ef406b77` (`docs: fix w-tdd-green bundle routing markdownlint formatting (#1486, builder)`).
- Evidence summary: reviewer-blocking `MD007`/`MD032` findings in Step 0a were removed by list-structure normalization and blank-line corrections.
[[2026-05-11]]
## Review Evidence
### Test Results
- Proof bundle: `skip` -> reviewer scope is lint-only for this markdown skill task.
- quality-runner markdownlint on `share/skills/w-tdd-green/SKILL.md`: `clean: true`, `violations: none`, exit code 0.
- Tests: N/A for this documentation-only skill update.
- Coverage: N/A for this documentation-only skill update.
- Review cycle: second review. One prior `## Review Evidence` section already exists in `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md:86`, so any new failure routes to `backlog` under the loop-breaker rule.

### Lint
- Clean. No markdownlint violations remain in the edited file.

### Coverage
- N/A for markdown-only skill task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Builder handles skip/existing bundles: implement from AC directly (no tests to pass) | `share/skills/w-tdd-green/SKILL.md:41-50` says `Route non-implementation flow from Proof bundle`, then under `Proof bundle: skip` tells the builder to advance with `No code changes needed` and `Stop here`. The parent brief requires skip/existing bundles to be implemented directly from AC, not treated as an automatic no-op pass-through (`.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:115-118,169`). | FAIL |
| 2. For `existing` bundle, builder ensures named existing tests still pass | `share/skills/w-tdd-green/SKILL.md:52-67` requires `Existing proof required: ...`, runs the named proof through Quality-Runner, records the summary, and blocks advance while the proof is missing or failing. | PASS |
| 3. Legacy td:0 pass-through check replaced with bundle-based routing | `share/skills/w-tdd-green/SKILL.md:41-50,69-71` still frames Step 0a as `non-implementation flow` and keeps the `skip` branch as a no-op exit. The brief change surface requires replacing the depth-zero pass-through check with a skip/existing routing change, while preserving true non-impl pass-through separately (`.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:157,169`). | FAIL |

### Findings
- The prior markdownlint defect is fixed.
- The current Step 0a contract is still substantively wrong for `Proof bundle: skip`: it tells future builders to advance without making the AC-driven change. That contradicts both the task AC and the parent brief.
- The explicit non-impl pass-through trigger at `share/skills/w-tdd-green/SKILL.md:71` is the correct place for true no-op tasks. The `skip` bundle branch should not duplicate that behavior.

### Deductions
- `-0.10` AC 1 violation: the `skip` branch still hardcodes `No code changes needed` and immediate exit.
- `-0.04` AC 3 violation: Step 0a still defines bundle handling as non-implementation flow instead of bundle-based implementation routing.
- `-0.02` direct `git diff/status` evidence was unavailable from the current reviewer tool surface; commit existence was independently verified via `.git/logs/refs/heads/dev:2502` and `.git/logs/HEAD:2701`.
- Confidence: `.84`

### Verdict
- FAIL -> backlog
- Reason: second-cycle review. Lint is clean, but the delivered Step 0a still violates the core `skip`-bundle contract by instructing a no-op pass-through instead of direct AC implementation.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite the `Proof bundle: skip` builder routing so it requires direct implementation from AC and does not auto-advance with `No code changes needed`; keep true no-op behavior only under the separate non-impl trigger | `share/skills/w-tdd-green/SKILL.md` | `share/skills/w-tdd-green/SKILL.md:41-50,69-71`; `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:115-118,157,169` |
| 2 | architect | Reconcile the Step 0a heading/intro so `Proof bundle:` no longer defines `non-implementation flow` and instead expresses bundle-based routing compatible with the preserved explicit non-impl pass-through | `share/skills/w-tdd-green/SKILL.md` | `share/skills/w-tdd-green/SKILL.md:41,71`; task Architecture Notes in task body |

### Action
- Rejected to `backlog` under the loop-breaker rule after a second review failure.
[[2026-05-11]]

## Architecture Re-Review (loop-breaker return)

**Context:** Reviewer returned this task to backlog after second review cycle (loop-breaker rule). Two AC violations found in delivered Step 0a:

1. **AC 1 violation:** `skip` branch says "Implement from AC directly" then immediately contradicts with "No code changes needed" and auto-advance. The brief (`.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:115-118`) is clear: `skip` means "builder implements from AC directly (no tests to pass)" — the builder does the work, just without `TestFromAC_*` gates.
2. **AC 3 violation:** Step 0a heading says "Route non-implementation flow from `Proof bundle:`" — but bundle routing is implementation routing by test-verification level. True non-implementation flow is the separate item 4 trigger.

### Refined AC

Replacing the original 3 AC lines with tightened versions:

1. `Proof bundle: skip` branch instructs builder to implement the AC changes normally (commit source files, write Builder Notes), without `TestFromAC_*` pass gates. The branch MUST NOT contain "no code changes needed" or direct the builder to auto-advance without implementing. `(td:0)`
2. `Proof bundle: existing` branch instructs builder to implement from AC AND run named existing proof through Quality-Runner before advancing. `(td:0)`
3. Step 0a heading and intro describe bundle-based routing, NOT "non-implementation flow." True non-impl pass-through (item 4) remains a separate trigger independent of proof bundles. `(td:0)`

### Builder Guidance

The semantic distinction to encode in the skill text:

- **`skip` bundle** = "no test verification needed" ≠ "no work needed." The builder reads the AC, implements the changes, commits, then advances. The only difference from a normal task is there are no `TestFromAC_*` classes to pass.
- **Non-impl pass-through** (item 4) = truly no code changes. This triggers from Test-Writer Notes containing "Non-implementation task", not from proof bundle value.
- The heading should read something like "Bundle-Based Routing" (not "Bundle-Based Pass-Through" or "non-implementation flow").

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file, single concept |
| Interface clarity | PASS | Refined AC has explicit negative constraints |
| Dependency correctness | PASS | #1482 done/archived |
| Module layering | PASS | Skill doc only |
| TDD compliance | PASS | All td:0, test-writer SKIP |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | Brief mandates this change |
| Pattern consistency | PASS | Follows existing skill structure |
| Security surface | PASS | No runtime code |
| Single domain | PASS | Pipeline/skills domain |

Test-writer: SKIP — all AC td:0
Challenger: skipped (all td:0)

[[2026-05-11]]
## Architecture Re-Review

Verdict: REFINE + APPROVE → todo

- Loop-breaker return from reviewer: two AC violations in delivered Step 0a (skip branch self-contradictory, heading mislabeled as non-implementation flow)
- Refined all 3 AC lines with explicit negative constraints and builder guidance section
- All AC td:0, test-writer SKIP, challenger skipped
- Dependency #1482 satisfied (archived)
[[2026-05-11]]
## Test-Writer Notes
- Retry cycle: task has prior `## Test-Writer Notes` + `## Review Evidence`.
- Reviewer's Required Follow-up (both items) targeted the **architect**, not the test-writer — architect has completed the re-review and refined the AC.
- Proof bundle: `skip` — no new RED tests required (Step 1d pass-through).
- Tags include `agent` — non-implementation task (Step 1a also applies).
- All 3 AC lines are td:0 (skill-document edits to `w-tdd-green/SKILL.md`, no testable Python interfaces).
- No test gaps introduced by the architecture re-review.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Implementation: updated `share/skills/w-tdd-green/SKILL.md` Step 0a semantics and heading.
- Fixes applied:
  - Renamed Step 0a from `Bundle-Based Pass-Through` to `Bundle-Based Routing`.
  - Replaced `skip` no-op/pass-through wording with explicit AC-implementation routing (no `TestFromAC_*` gate, but normal plan/implement/verify/commit obligations remain).
  - Updated `existing` branch wording to require normal builder flow continuation after named proof passes.
  - Preserved explicit non-implementation pass-through trigger as a separate condition.
- Tests: 0 passed, 0 failed (doc-only task).
- Coverage: N/A (no tests collected).
- Lint: clean (`markdownlint` exit 0 via quality-runner).
- Evidence summary: reviewer-blocking semantic mismatch in `skip` branch resolved; scoped lint gate passes.
- Commit: `467f1516` (`docs: fix skip bundle routing semantics (#1486, builder)`).
[[2026-05-11]]
## Review Evidence
### Test Results
- Proof bundle: `skip`; task remains a td:0 markdown skill update, so reviewer scope is lint-only.
- quality-runner linted `share/skills/w-tdd-green/SKILL.md`: clean, 0 violations, exit code 0.
- Tests: N/A for this documentation-only skill update.
- Coverage: N/A for this documentation-only skill update.
- Review cycle: third review overall, after loop-breaker architecture re-review at `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md:185-198`.

### Lint
- Clean. No markdownlint violations remain in `share/skills/w-tdd-green/SKILL.md`.

### Coverage
- N/A for markdown-only skill task.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. `Proof bundle: skip` branch requires normal AC implementation, not a no-op pass-through | `share/skills/w-tdd-green/SKILL.md:44` says `Implement from AC directly`; `share/skills/w-tdd-green/SKILL.md:46` says `Continue the normal builder flow (plan, implement, verify, commit, and advance)`; `share/skills/w-tdd-green/SKILL.md:48` says `Proof bundle: skip` removes only `TestFromAC_*` verification, not AC implementation obligations. This matches the refined AC at `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md:196` and the parent brief at `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:117,169`. | PASS |
| 2. `Proof bundle: existing` branch requires named existing proof before advance | `share/skills/w-tdd-green/SKILL.md:55` says `Implement from AC directly`; `share/skills/w-tdd-green/SKILL.md:57` requires `Existing proof required: ...`; `share/skills/w-tdd-green/SKILL.md:63` blocks advance while the proof is missing or failing; `share/skills/w-tdd-green/SKILL.md:65` resumes the normal builder flow only after proof passes. This matches the refined AC at `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md:197` and the parent brief at `.owlbear/briefs/draft-proof-bundle-taxonomy/brief.md:117`. | PASS |
| 3. Step 0a now describes bundle-based routing, with true non-impl pass-through kept separate | `share/skills/w-tdd-green/SKILL.md:39` is `Bundle-Based Routing`; `share/skills/w-tdd-green/SKILL.md:41` says `Route builder verification flow from Proof bundle`; legacy fallback remains separate at `share/skills/w-tdd-green/SKILL.md:71`; explicit non-impl pass-through remains separate at `share/skills/w-tdd-green/SKILL.md:73`. This matches the refined AC at `.owlbear/kanban/tasks/1486-p1-05-update-w-tdd-green-handling-for-skip-existing-bundles.md:198`. | PASS |

### Findings
- The prior blocker is resolved. The `skip` branch no longer equates to `No code changes needed`; it now explicitly preserves the normal builder implementation/commit flow.
- The `Return ... Stop here` lines are acceptable in context because the preceding branch text already requires plan/implement/verify/commit before advance; they do not reintroduce the earlier no-op contract.
- No security, data-safety, or `TestFromAC_*` integrity concerns apply to this single-file documentation task.

### Deductions
- `-0.03` direct `git diff/status` evidence was unavailable from the current reviewer tool surface; changed-file scope was reconstructed from task scope and builder notes, and commit presence was independently confirmed in `.git/logs/refs/heads/dev:2513` and `.git/logs/HEAD:2712`.
- Confidence: `.95`

### Verdict
- PASS -> docs

### Action
- Advanced to `docs`.
[[2026-05-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Only changed file is `share/skills/w-tdd-green/SKILL.md` (OUT of scope). No IN-scope prose doc references `w-tdd-green` by name in README or setup guides. |
| 2 | Module docstrings | No | N/A | No Python modules modified. |
| 3 | External attribution | No | N/A | No external patterns used — purely internal skill-text rewrite. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: serve/*/pyproject.toml, share/**, setup/**, .owlbear/**` which matches `share/skills/w-tdd-green/SKILL.md`. Footer updated to `Last verified: 2026-05-11 (0e3baa80)` and committed (`64e63de9`). |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/skills/w-tdd-green/SKILL.md` | OUT (agent-executable SKILL.md) | N/A — no edits |
| `share/diagrams/project-overview.excalidraw` | IN | Footer updated |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer only (commit `64e63de9`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1486-*` scratch files found)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: pytest 4413 passed / 209 failed / 5 errors; vitest 1393 passed / 0 failed. All pytest failures are pre-existing background noise — task #1486 only modified `share/skills/w-tdd-green/SKILL.md` (markdown), which cannot cause Python test regressions. Ruff 271 violations and ESLint 1 error are also pre-existing.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file `share/skills/w-tdd-green/SKILL.md` matches declared scope)
- purpose match: PASS (Step 0a now implements bundle-based routing for skip/existing bundles per parent brief #1481)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Initial AC was adequate but the `skip` bundle semantics were ambiguous enough that the builder misinterpreted them as a no-op pass-through, causing two review rejections. The architect performed a thorough loop-breaker re-review with refined AC containing explicit negative constraints and builder guidance. The refined AC was specific and unambiguous, leading to a clean third-cycle pass. Score reflects the need for refinement but credits the quality of the re-review.

### Commit Integrity
- upstream commit presence: PASS (builder: `af62c0a8`, `ef406b77`, `467f1516`; doc-writer: `64e63de9`)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- No deductions applied. Regression detection clean for task scope, intent aligned, architect quality adequate, commits present.

### Confidence: 1.00
### Action: archive