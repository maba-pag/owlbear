---
id: 1118
title: Harden ideation-overhaul static test proofs with glob-based discovery
status: in-progress
priority: important
created: 2026-04-24T11:10:50.379753+00:00
updated: 2026-04-24T12:25:35.529419+00:00
tags: []
parent:
depends_on: []
blocked: true
block_reason: 'AC8 fails: `share/agents/ideation-critic.agent.md` has an uncommitted
  `model: GPT-5.4 (copilot)` field (auto-added by VS Code IDE when the agent was invoked).
  The new glob in `_ideation_agent_files()` correctly detects this violation — which
  the old curated list would have missed. Fix: `git checkout -- share/agents/ideation-critic.agent.md`.
  Once reverted, `uv run pytest tests/test_ideation_overhaul_static.py -q` passes.'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Replace curated hardcoded file lists in `tests/test_ideation_overhaul_static.py` with glob-based dynamic discovery to prevent silent proof bypass when new ideation agent files are added.

Research doc: `.owlbear/research/1115-ideation-test-proof-hardening.md`

## Acceptance Criteria

1. Negative scans for `model:` field use `_REPO_ROOT.glob("share/agents/ideation-*.agent.md")` instead of curated lists
2. Negative scans for `working-log.md`/`checkpoint` use glob-based discovery across the full ideation surface (agents + skills + briefs README)
3. Both glob helpers assert `len(files) >= N` (min-count guard against empty-glob false pass)
4. The split test pairs are merged: `test_role_files_do_not_use_model_field_as_contract` + `test_late_panelist_files_do_not_use_model_field_as_contract` into one test; `test_no_working_log_or_checkpoint_contract_reappears` + `test_late_panelist_files_have_no_working_log_or_checkpoint` into one test
5. Forbidden-term check for `checkpoint` is case-insensitive
6. `test_phase_split_files_exist` existence check covers the 4 late-domain panelists (architect, data, enduser, security)
7. All existing tests that use semantic subsets (critic narrow contract, context/decisions paired contract) remain unchanged
8. Full suite passes: `uv run pytest tests/test_ideation_overhaul_static.py -q`

## Affected Files

- `tests/test_ideation_overhaul_static.py`

[[2026-04-24]]
## Research

Validated the existing research doc `.owlbear/research/1115-ideation-test-proof-hardening.md` against current repo state. All claims confirmed:

- **11** ideation agent files match `ideation-*.agent.md` glob (min-count guard value)
- **17** total surface files for forbidden-term scans (11 agents + ideator + 4 skills + briefs README)
- Split test pairs confirmed: model-free (7+4) and forbidden-terms (13+4) — ready to merge
- Case-sensitivity gap on `checkpoint` confirmed (lowercase-only check)
- 4 late panelists missing from existence check confirmed
- Semantic subsets (critic narrow contract, context/decisions paired contract) correctly scoped — must remain unchanged
- Glob patterns align with repo precedent (`test_package_boundary.py` line 51)

**Tier:** T1 — autonomous test refactor, no architecture or capability change.
**Confidence:** .82 (matches research doc).
**Follow-ups:** None — #1118 itself is the implementation follow-up from the research pass.
[[2026-04-24]]
## Research (validation pass)

Re-validated `.owlbear/research/1115-ideation-test-proof-hardening.md` against current repo state. All 7 claims confirmed:
- 11 ideation agent files match glob (exact count)
- 17 surface files all present
- Split test pairs confirmed in test source
- Case-sensitivity gap, missing panelists, glob precedent all verified
- No new ideation files added since research doc was written

**Tier:** T1 — autonomous test refactor. No follow-up tasks needed; #1118 is the implementation task.
**Confidence:** .82 (unchanged from research doc).
[[2026-04-24]]
## Architecture Review

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: model-free scan uses `ideation-*.agent.md` glob | PASS — specific, testable | None |
| AC2: forbidden-term scan uses "glob-based discovery across full ideation surface" | REFINED — surface undefined; builder could miss `ideator.agent.md` or hit historical brief files with legitimate forbidden terms | Enumerated exact surface composition |
| AC3: min-count guard `len(files) >= N` | REFINED — N unbound in AC text; values only in research notes | Specified exact thresholds: ≥11 for agent glob, ≥17 for full surface |
| AC4: merge split test pairs | PASS — names exact functions | None |
| AC5: case-insensitive checkpoint check | PASS — specific | None |
| AC6: existence check covers 4 late panelists | PASS — intentionally curated (known required files), not a negative scan | None |
| AC7: semantic subset tests unchanged | PASS — identifies which tests | None |
| AC8: full suite passes | PASS — gives exact command | None |

### Refined AC (rewritten in task body)

AC2 → `_ideation_surface_files()` returns: files from `ideation-*.agent.md` glob + `ideator.agent.md` + 4 skill SKILL.md paths (`w-ideation`, `w-ideation-discovery`, `w-ideation-mediation`, `h-ideation-panel`) + `.owlbear/briefs/README.md`. No brief history/draft files.

AC3 → min-count guards: ≥11 for `_ideation_agent_files()`, ≥17 for `_ideation_surface_files()`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One task: harden test discovery in one test file |
| Interface clarity | PASS (after refinement) | AC now enumerates exact surface and guard values |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | PASS | Test file only, no production code |
| TDD compliance | PASS | Task IS a test refactor; tagged `test` for pass-through |
| KISS/YAGNI | PASS | Minimal scope, follows existing patterns |
| Premise challenge | PASS | Addresses real gap flagged by review |
| Pattern consistency | PASS | Glob discovery exists in `test_package_boundary.py` |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Testing domain only |

### Challenge Results
- Challenger: reconsider (0.68) — AC2 surface ambiguity, AC3 unbound N, historical brief files contain legitimate forbidden terms
- Architect response: accepted — refined AC2 to enumerate exact surface, AC3 to specify thresholds

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC2 and AC3 for precision, tagged `test` for pipeline pass-through, advanced to todo
[[2026-04-24]]
## Architecture Review

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| 1. Glob for model-field scan | PASS — precise: `ideation-*.agent.md` excludes ideator (router, not panelist; has dedicated `TestFromAC_IdeatorRouterContract`) | Tightened: added clarifying note about intentional ideator exclusion |
| 2. Glob for forbidden-term surface | PASS — agents + skills + briefs README is correct scope; blackboard/golden-scenario tests are positive content checks (AC 7 preserves them) | None |
| 3. Min-count guards | REFINED — `>= N` was underspecified | Tightened: specified `>= 11` for agent glob, `>= 17` for full surface glob |
| 4. Merge split test pairs | PASS — reduces maintenance; merged tests preserve per-file offender reporting via assertion messages | Tightened: added diagnostic preservation requirement |
| 5. Case-insensitive checkpoint | PASS — `.lower()` on content before matching is standard | None |
| 6. Late panelist existence check | PASS — adds architect, data, enduser, security to `test_phase_split_files_exist` | None |
| 7. Semantic subsets unchanged | PASS — critic narrow contract, context/decisions paired contract correctly scoped | None |
| 8. Suite passes | PASS — standard build-time verification | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: harden test discovery mechanism |
| Interface clarity | PASS | AC specifies exact glob patterns, merge targets, guard values |
| Dependency correctness | PASS | No dependencies; standalone test file change |
| Module layering | PASS | Test file only, no production code |
| TDD compliance | PASS | Tagged `test` — test-writer pass-through |
| KISS/YAGNI | PASS | Minimal refactor: shared helpers + merges + case-fix |
| Premise challenge | PASS | Reviewer flagged proof weakness; research confirmed gap is real |
| Pattern consistency | PASS | Matches `test_package_boundary.py` glob discovery pattern (L51, L111) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Testing domain only |

### Challenge Results
- Challenger: reconsider (0.72)
- Architect response: rebutted 4/5 concerns; accepted AC precision gap on min-count values and ideator boundary documentation. Refined AC 3 to specify exact guard values, added clarifying note on AC 1 ideator exclusion, added diagnostic preservation requirement on AC 4.

### Verdict: APPROVE (after refinement)
### Action Taken: Refined AC 3 with explicit guard values (>= 11 agents, >= 17 surface), added notes to AC 1 (ideator exclusion rationale) and AC 4 (preserve per-file diagnostics). Tagged `test` for test-writer pass-through. Advanced to todo.
[[2026-04-24]]
## Builder Notes
- Scope check: AC requires edits only in tests/test_ideation_overhaul_static.py and specifically TestFromAC_* contract tests.
- Builder boundary mismatch: builder mode forbids writing/modifying tests and explicitly forbids touching TestFromAC_* classes.
- RED verification evidence (quality-runner, scoped): 38 passed, 0 failed; ruff clean.
- Rejection reason: task implementation belongs to test-writer role (test refactor ownership), not builder.
- Requested next action (test-writer): implement AC 1-6 in tests/test_ideation_overhaul_static.py (glob helpers with guards >=11 and >=17, merge split pairs, case-insensitive checkpoint scan, add 4 late panelists to existence check) while preserving AC 7 semantic-subset tests.

Post-task reflection:
- Problem faced: role/task mismatch (builder dispatched on test-only refactor).
- Workaround applied: strict boundary check before code edits to avoid violating TestFromAC protection.
- Quality gap: task body lacks explicit test-writer pass-through marker despite test-only scope.
[[2026-04-24]]
## Test-Writer Notes

**Test file:** `tests/test_ideation_overhaul_static.py`

**Scope:** Test refactor — no new production code; test-writer owns this task per builder rejection.

### Changes implemented

| AC | Change |
|----|--------|
| AC1 | `test_role_files_do_not_use_model_field_as_contract` now uses `_ideation_agent_files()` glob helper (>= 11 guard) |
| AC2 | `test_no_working_log_or_checkpoint_contract_reappears` now uses `_ideation_surface_files()` helper (11 agents + ideator + 4 skills + briefs README) |
| AC3 | `_ideation_agent_files()` guards `len >= 11`; `_ideation_surface_files()` guards `len >= 17` |
| AC4 | Merged `test_late_panelist_files_do_not_use_model_field_as_contract` into model-field test; merged `test_late_panelist_files_have_no_working_log_or_checkpoint` into forbidden-term test |
| AC5 | Forbidden-term check uses `.lower()` on file content — case-insensitive checkpoint detection |
| AC6 | Added architect, data, enduser, security to `test_phase_split_files_exist` required list |
| AC7 | `test_ideation_surfaces_keep_context_and_decisions_contract` and `test_critic_keeps_narrow_context_only_contract` unchanged |
| AC8 | `uv run pytest tests/test_ideation_overhaul_static.py -q` → 36 passed |

### AC coverage
All 8 AC lines covered. Suite result: **36 passed, 0 failed**. Ruff: clean.
[[2026-04-24]]
## Test-Writer Notes

**Test file:** `tests/test_ideation_overhaul_static.py`

**Scope:** Test refactor — glob-based discovery replacing curated lists. Committed: `5d27276c`.

### AC coverage

| AC | Status | Change |
|----|--------|--------|
| AC1 | DONE | `test_role_files_do_not_use_model_field_as_contract` uses `_ideation_agent_files()` glob helper |
| AC2 | DONE | `test_no_working_log_or_checkpoint_contract_reappears` uses `_ideation_surface_files()` (11 agents + ideator + 4 skills + briefs README) |
| AC3 | DONE | `_ideation_agent_files()` guards `len >= 11`; `_ideation_surface_files()` guards `len >= 17` |
| AC4 | DONE | Split pairs merged: late-panelist model-field test folded into AC1 test; late-panelist forbidden-term test folded into AC2 test |
| AC5 | DONE | Forbidden-term check uses `.lower()` — case-insensitive checkpoint detection |
| AC6 | DONE | `test_phase_split_files_exist` covers architect, data, enduser, security |
| AC7 | DONE | Semantic subset tests (`test_ideation_surfaces_keep_context_and_decisions_contract`, `test_critic_keeps_narrow_context_only_contract`) unchanged |
| AC8 | BLOCKED | Suite: 35 passed, 1 failed. `test_role_files_do_not_use_model_field_as_contract` correctly detects `model: GPT-5.4 (copilot)` in uncommitted `share/agents/ideation-critic.agent.md`. This is an IDE-auto-added field, not an intentional commit. Fix: `git checkout -- share/agents/ideation-critic.agent.md`. |

### Blocker
`share/agents/ideation-critic.agent.md` has an uncommitted `model:` field (auto-added by VS Code). The glob-based discovery — which is the whole point of this task — correctly catches it. Ruff: clean.
