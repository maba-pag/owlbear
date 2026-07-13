---
id: 1364
title: 'P1-01: Test Cockpit PDS v4 build compatibility'
status: archived
priority: medium
created: 2026-05-06T00:58:30.519362+00:00
updated: 2026-05-06T06:34:04.704160+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- design-system
- build
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write the failing test and quality-gate proof for Cockpit PDS v4 build compatibility.

## Problem Evidence
- The Cockpit frontend build currently fails.
- PDS v4 API and type mismatches were observed around tertiary variants, select/input/textarea events and props, JSX namespace typing, and PendingDR/ResolveModal body typing.
- The sync-to-main workflow builds the Cockpit SPA before staging dist, so this blocks delivery.

## Acceptance Criteria
- A focused frontend verification path proves that npm run build in serve/cockpit/web must pass cleanly.
- Coverage or type-focused assertions catch the known PDS v4 component usage failures without broad type suppression.
- The PendingDR and ResolveModal body type mismatch is represented in the failing proof if it is still present.
- The proof fails against the audited broken state and is suitable for #1365 to satisfy.

## Scope
- In scope: Cockpit web build/type verification and PDS v4 compatibility proof.
- Out of scope: runtime custom-element loading, CSP policy changes, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1365.


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: prove PDS v4 build failure |
| Interface clarity | PASS | Build exit code + specific type errors = clear I/O |
| Dependency correctness | PASS | No deps, correct for Layer 1 |
| Module layering | PASS | Test-only task, no module changes |
| TDD compliance | PASS | This IS the RED phase test, paired with #1365 |
| KISS/YAGNI | PASS | Minimal scope: verify build state |
| Premise challenge | PASS | sync-to-main requires passing build; blocking delivery |
| Pattern consistency | PASS | Existing PdsMigration_1230.test.tsx shows pattern; build check is complementary |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | cockpit-web only |

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Self-challenge: AC is verifiable, no overlap with existing runtime PDS tests, scope is bounded. Proceed.

### Test Depth
- AC1: (td:1) — single assertion: build exit code 0
- AC2: (td:1) — tsc output contains specific PDS v4 type errors
- AC3: (td:1) — conditional presence in tsc output
- AC4: (td:1) — run now, expect failure
- Max depth: 1
- Test-writer: SKIP (type:test tag — pass-through)

### Verdict: APPROVE
### Action Taken: Approved to todo. AC is verifiable; type:test tag ensures test-writer pass-through. Builder writes the failing build proof directly.

[[2026-05-06]]
Architecture review complete. All 10 criteria PASS. AC is verifiable: build exit code assertion, specific PDS v4 type error capture, conditional PendingDR/ResolveModal body check. Tagged type:test for test-writer pass-through. Challenger: FALLBACK (no response). Self-challenged and confirmed. Approved to todo.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- Architecture review explicitly flagged test-writer SKIP: "type:test tag ensures test-writer pass-through. Builder writes the failing build proof directly."
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Implementation: added RED proof test file [tests/test_cockpit_pds_build_compat_1364.py](tests/test_cockpit_pds_build_compat_1364.py)
- Approach: execute `npm run build` once per test module and assert delivery gate + audited PDS v4/typing signatures are absent.
- Tests: 0 passed, 6 failed (intentional RED for counterpart #1365)
- Coverage: 0% (expected; integration build-output assertions only, no Python module instrumentation)
- Ruff: clean (after fixing W292 newline)
- Evidence summary: scoped quality-runner run confirms current cockpit build exits 1 and reproduces audited signatures:
  - `"tertiary"` variant type mismatch
  - unsupported `onInput` prop on PDS wrappers
  - missing required `name` prop on PDS form controls
  - `Cannot find namespace 'JSX'`
  - PendingDR vs PendingDRWithBody mismatch in ResolveModal flow
- Commit: `acd93141` (`test: add cockpit pds build red proof (#1364, builder)`)
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_cockpit_pds_build_compat_1364.py`: 0 passed, 6 failed, 0 skipped, `pytest` exit 1.
- Failing proofs match the audited broken snapshot: `test_npm_build_exits_zero`, 4 parametrized `test_known_pds_v4_type_failures_absent[...]` cases, and `test_pending_dr_body_type_mismatch_absent`.
- The build gate exercised by the test is the real delivery path: `serve/cockpit/web/package.json` defines `build` as `tsc -b && vite build`.

### Lint Results
- Ruff scoped to `tests/test_cockpit_pds_build_compat_1364.py`: clean, `ruff` exit 0.

### Coverage
- Not applicable for this scoped review. The artifact under review is a Python RED-proof harness that shells out to the frontend build; no Python source module is the subject of this task.

### Scope / Integrity
- Builder commit presence verified from `.git/logs/HEAD`: `acd93141` (`test: add cockpit pds build red proof (#1364, builder)`).
- No prior `## Review Evidence` section found in the task body: this is the first review cycle.
- `type:test` authority exception applies: Architecture Review explicitly assigned the RED-proof file to the builder, so builder-authored `TestFromAC_*` content is allowed here.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: focused frontend verification path proves `npm run build` must pass cleanly | `tests/test_cockpit_pds_build_compat_1364.py` defines `test_npm_build_exits_zero` at line 38 and asserts `returncode == 0` at line 40. quality-runner shows that test fails because `npm run build` exits 1. | PASS |
| AC2: assertions catch known PDS v4 failures without broad type suppression | `tests/test_cockpit_pds_build_compat_1364.py` defines `test_known_pds_v4_type_failures_absent` at line 71 and only asserts `fragment not in build_output` at line 73. quality-runner confirms the current broken snapshot contains the audited fragments, but the proof never inspects source/config for suppression-based escapes. A builder could make the build green with broad suppression and still satisfy these assertions. | FAIL |
| AC3: PendingDR / ResolveModal body mismatch represented if still present | `tests/test_cockpit_pds_build_compat_1364.py` defines `test_pending_dr_body_type_mismatch_absent` at line 79 and asserts the body-mismatch fragment is absent at line 82. Current sources still show `PendingDRWithBody` in `serve/cockpit/web/src/components/ResolveModal.tsx` lines 14 and 19, while `serve/cockpit/web/src/Shell.tsx` passes `selectedDR` into `ResolveModal` at lines 186-193. quality-runner reports this test failing on the live snapshot. | PASS |
| AC4: proof fails against the audited broken state and is suitable for #1365 to satisfy | quality-runner reports 0 passed / 6 failed against the current snapshot, matching the builder note and the expected RED state. | PASS |

### Critical Checks
- Security review: PASS. The test invokes a fixed repo-local build command with a fixed cwd; no user-controlled shell interpolation or path traversal.
- Test integrity: PASS. No prior test-writer artifact exists for this task, and the architecture note explicitly delegated this test file to the builder.
- Test quality: FAIL. AC2's `without broad type suppression` clause is not enforced by a discriminating assertion.
- Builder process quality: CLEAN. First review cycle; no loop pattern detected.

### Deductions
- `-0.14` AC2 is only partially proven. Current assertions validate broken-output signatures, but they do not fail if the implementation hides those signatures with broad suppression.
- `-0.02` Commit existence was verified via `.git/logs`, but diff-scoped dirty-tree reconstruction was not available from the current tool surface.

### Verdict
- FAIL -> in-progress
- Confidence: 0.84
- Routing rationale: although this is a proof-quality defect, the Architecture Review explicitly assigned the RED-proof artifact to the builder for this `type:test` task, so the builder can fix the gap directly without a test-writer handoff.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Strengthen AC2 in the RED-proof file so the task fails if #1365 uses broad type suppression instead of a real PDS-v4-compatible fix. Add discriminating source/config assertions, not only build-output string checks. | `tests/test_cockpit_pds_build_compat_1364.py` | AC2 text in task body; `tests/test_cockpit_pds_build_compat_1364.py:71-73` only checks build-output fragments |
| 2 | builder | Keep the existing RED build-gate proof intact while adding the no-suppression guard. The build must still run through `npm run build` and remain RED on the audited broken snapshot. | `tests/test_cockpit_pds_build_compat_1364.py`; `serve/cockpit/web/package.json` | quality-runner `0 passed, 6 failed`; `package.json` build script `tsc -b && vite build` |
[[2026-05-06]]
## Builder Notes
- Implementation: strengthened RED proof in tests/test_cockpit_pds_build_compat_1364.py by adding AC2 anti-suppression guards without changing the existing build-output RED assertions.
- Fixes applied:
  - Added non-test source scan fixture and assertions blocking `@ts-ignore`, `@ts-nocheck`, and `@ts-expect-error` in cockpit app source.
  - Added tsconfig assertion guard requiring `compilerOptions.strict == true` and forbidding `compilerOptions.noCheck == true`.
  - Kept the delivery gate proof (`npm run build`) and existing audited error-fragment assertions intact.
- Tests (quality-runner, scoped): 4 passed / 6 failed on tests/test_cockpit_pds_build_compat_1364.py.
  - Expected RED failures remain for the audited broken state (build exit + known PDS v4/typing mismatches).
  - New no-suppression guard tests pass, proving discriminating AC2 coverage.
- Coverage: N/A for this RED proof harness (integration build-output assertions; no target Python module instrumentation).
- Ruff: clean (ruff exit 0).
- Commit: 7240af07 (`test: harden pds build red proof against suppression (#1364, builder)`).

### Evidence Summary
- RED gate still fails against current audited snapshot, preserving counterpart suitability for #1365.
- AC2 now includes source/config-level checks that fail suppression-based shortcuts instead of relying only on build-output fragment matching.

### Post-task Reflection
- Problem faced: prior AC2 proof could be bypassed by broad suppression tactics while still producing a green build.
- Workaround applied: added explicit anti-suppression assertions in source and tsconfig scope.
- Pattern discovered: type:test tasks may still need builder-owned test hardening when architecture delegates RED-proof ownership to builder.
- Quality gap addressed: moved AC2 from output-only signal to output + configuration/source guard coverage.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_cockpit_pds_build_compat_1364.py`: 4 passed, 6 failed, 0 skipped, `pytest` exit 1.
- quality-runner confirmed all 10 collected tests executed; repo `pyproject.toml` has no `-x` or `--maxfail` early-stop flag.
- RED failures still match the audited broken snapshot: `test_npm_build_exits_zero`, 4 parametrized `test_known_pds_v4_type_failures_absent[...]` cases, and `test_pending_dr_body_type_mismatch_absent`.
- New anti-suppression guards pass on the current snapshot: 3 directive-scan cases plus `test_tsconfig_does_not_disable_typecheck`.

### Lint Results
- Ruff scoped to `tests/test_cockpit_pds_build_compat_1364.py`: clean, `ruff` exit 0.

### Coverage
- Not applicable for this review. The artifact under review is a Python RED-proof harness for the frontend build gate; no Python source module is the subject of task #1364.

### Scope / Integrity
- Builder commit presence verified from `.git/logs/HEAD`: `7240af07` (`test: harden pds build red proof against suppression (#1364, builder)`).
- One prior `## Review Evidence` section already exists in the task body, so this is the second review cycle. Reviewer loop-breaker routing applies on FAIL.
- Diff-scoped changed-file and dirty-tree verification were not fully available from the current tool surface; live file inspection and the builder note both point to `tests/test_cockpit_pds_build_compat_1364.py` as the retry surface.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: a focused frontend verification path proves that `npm run build` in `serve/cockpit/web` must pass cleanly | `tests/test_cockpit_pds_build_compat_1364.py:23` runs `npm run build`, and `tests/test_cockpit_pds_build_compat_1364.py:59` asserts zero exit status. The live build script is still the canonical sync-to-main path at `serve/cockpit/web/package.json:11` (`tsc -b && vite build`). | PASS |
| AC2: coverage or type-focused assertions catch the known PDS v4 component usage failures without broad type suppression | The retry added source/config guards at `tests/test_cockpit_pds_build_compat_1364.py:120` and `tests/test_cockpit_pds_build_compat_1364.py:129`, but the proof file contains no assertion pinning `package.json` or `tsc -b`. A grep of the proof file found no `package.json` or `tsc -b` references. That leaves a broad bypass open: `#1365` could weaken `npm run build` to skip type-checking, make the audited fragments disappear, and this harness would go green. | FAIL |
| AC3: the PendingDR and ResolveModal body type mismatch is represented in the failing proof if it is still present | `tests/test_cockpit_pds_build_compat_1364.py:99` asserts the body-mismatch fragment is absent. The live source still exposes the mismatch: `serve/cockpit/web/src/components/ResolveModal.tsx:14` and `serve/cockpit/web/src/components/ResolveModal.tsx:19` require `PendingDRWithBody`, while `serve/cockpit/web/src/hooks/usePendingDRs.ts:6` defines `PendingDR` without `body`, and `serve/cockpit/web/src/Shell.tsx:187` plus `serve/cockpit/web/src/Shell.tsx:188` pass `selectedDR` straight into `ResolveModal`. quality-runner reports this test failing on the current snapshot. | PASS |
| AC4: the proof fails against the audited broken state and is suitable for `#1365` to satisfy | The harness is still RED today (`4 passed / 6 failed`), but it is not yet suitable for the GREEN counterpart because it does not fail if the future fix weakens the `build` script instead of fixing the PDS v4 incompatibilities. | FAIL |

### Critical Checks
- Security review: PASS. The test invokes a fixed repo-local build command with a fixed cwd; no user-controlled shell interpolation or path traversal was observed.
- Test integrity: PASS. This is a `type:test` task and the Architecture Review explicitly delegated the RED-proof file to the builder.
- Test quality: FAIL. The proof executes whatever `npm run build` means at runtime but never asserts that the command remains the canonical `tsc -b && vite build` delivery gate at `serve/cockpit/web/package.json:11`. That is a false-green path for AC2/AC4.
- Builder process quality: CLEAN. One retry, materially different approach, no loop in implementation tactics.

### Deductions
- `-0.10` AC2 remains non-discriminating against a build-script bypass. Source/tsconfig suppression guards were added, but the harness still does not pin the canonical type-checking build command.
- `-0.04` AC4 remains incomplete because the proof is RED on the current snapshot but still not safe as a GREEN gate for `#1365`.
- `-0.02` Dirty-tree/diff-scoped integrity evidence was partially reconstructed from task notes and `.git/logs` rather than a direct `git diff-tree` / `git status` surface.

### Verdict
- FAIL -> backlog
- Confidence: 0.84
- Routing rationale: this is the second review failure on the same task. The retry closed part of the prior gap, but the proof still leaves a canonical-build-script bypass open. Under the reviewer loop-breaker rule, the task returns to backlog for architecture-level clarification before another builder cycle.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2/AC4 so the proof must pin the canonical Cockpit delivery build script, not only execute `npm run build`. Make the requirement explicit that the harness fails if `serve/cockpit/web/package.json` drops `tsc -b` from the `build` script. | `.owlbear/kanban/tasks/1364-p1-01-test-cockpit-pds-v4-build-compatibility.md`; `tests/test_cockpit_pds_build_compat_1364.py`; `serve/cockpit/web/package.json` | Current proof file has no `package.json` / `tsc -b` assertion; `serve/cockpit/web/package.json:11` is the only live source proving the canonical gate today. |
| 2 | architect | Re-issue the builder-facing proof requirement with an executable assertion shape for the build-gate contract, not just a prose note to “keep the delivery gate proof intact.” | `.owlbear/kanban/tasks/1364-p1-01-test-cockpit-pds-v4-build-compatibility.md`; `tests/test_cockpit_pds_build_compat_1364.py` | Prior reviewer follow-up at task body line 144 required the real build gate to stay intact, but the retry only added source/tsconfig guards and still never encoded the build-script contract in the test file. |

### Post-task Reflection
- The builder retry improved AC2 materially, but it translated the previous follow-up only partially: source/config suppression is guarded, build-script weakening is not.
- For RED-proof tasks that shell out to `npm run build`, the script definition itself is part of the contract and often needs a direct assertion.
- The first quality-runner summary underreported the failure surface; a second scoped run was necessary to confirm all 10 tests executed and no early-stop flag was involved.
[[2026-05-06]]

## Architecture Review (Cycle 2 — Reviewer Return)

### Reason for Return
Reviewer identified a false-green bypass path: the proof runs `npm run build` but never asserts what `build` means. If #1365 removes `tsc -b` from `package.json` `scripts.build`, all type-error assertions pass vacuously. Two review cycles confirmed the gap persists after the first builder retry.

### AC Refinement
| AC | Change | Rationale |
|---|---|---|
| AC2 | Added: "The proof must assert that `serve/cockpit/web/package.json` `scripts.build` contains `tsc -b`, failing if the build command drops type-checking." | Closes the build-script-weakening bypass identified by the reviewer. |
| AC4 | Added: "The proof is not suitable if the build script could be weakened to skip `tsc -b` without the proof detecting it." | Makes the suitability criterion for #1365 discriminating. |

### Refined Acceptance Criteria
- AC1: A focused frontend verification path proves that `npm run build` in `serve/cockpit/web` must pass cleanly. (td:1)
- AC2: Coverage or type-focused assertions catch the known PDS v4 component usage failures without broad type suppression. The proof must assert that `serve/cockpit/web/package.json` `scripts.build` contains `tsc -b`, failing if the build command drops type-checking. (td:1)
- AC3: The PendingDR and ResolveModal body type mismatch is represented in the failing proof if it is still present. (td:1)
- AC4: The proof fails against the audited broken state and is suitable for #1365 to satisfy. The proof is not suitable if the build script could be weakened to skip `tsc -b` without the proof detecting it. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: prove PDS v4 build failure with anti-bypass guards |
| Interface clarity | PASS | Build exit code + error fragments + script pinning = clear I/O |
| Dependency correctness | PASS | No deps, correct for Layer 1 |
| Module layering | PASS | Test-only task, no module changes |
| TDD compliance | PASS | This IS the RED phase test, paired with #1365 |
| KISS/YAGNI | PASS | Minimal scope: verify build state + pin build contract |
| Premise challenge | PASS | sync-to-main requires passing build; blocking delivery |
| Pattern consistency | PASS | Extends existing test with ~5 lines for build-script assertion |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | cockpit-web only |

### Builder Guidance
Add one assertion to `tests/test_cockpit_pds_build_compat_1364.py`: read `serve/cockpit/web/package.json`, parse `scripts.build`, and assert it contains `tsc -b`. This can be a new test method in `TestAc2NoBroadTypeSuppressionGuards` or a standalone test class. The existing `build_result` fixture already targets `_WEB`; reuse the `_WEB` path constant. Expected: this assertion passes today (the script IS `tsc -b && vite build`), joining the 4 already-passing anti-suppression guards.

### Challenge
Challenger: SKIP (all AC lines td:1, refinement-only cycle, no new architectural decisions). Self-challenge: the only change is adding a 5-line build-script assertion requirement — no risk of scope creep or architectural regression.

### Verdict: APPROVE → todo

[[2026-05-06]]
Architecture review cycle 2 (reviewer return). Refined AC2 and AC4 to require build-script-pinning assertion: proof must assert `package.json` `scripts.build` contains `tsc -b`, closing the false-green bypass path. All 10 criteria PASS. Builder needs ~5 lines added to existing test file. Tagged type:test for test-writer pass-through.
[[2026-05-06]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- Architecture Review Cycle 2 explicitly directs test-writer pass-through: "Tagged type:test for test-writer pass-through. Builder writes the failing build proof directly."
- Retry context noted: prior Test-Writer Notes, two Builder Notes, and two Review Evidence sections present. Architect refined AC2/AC4 and provided explicit builder guidance (~5-line build-script assertion).
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Implementation: updated tests/test_cockpit_pds_build_compat_1364.py with an AC2/AC4 anti-bypass guard that pins the Cockpit build contract.
- Fixes applied:
  - Added `package_json_data` fixture loading `serve/cockpit/web/package.json`.
  - Added `test_package_json_build_script_keeps_tsc_build` asserting `scripts.build` is a string and contains `tsc -b`.
  - Preserved existing RED gate behavior and existing audited-fragment assertions.
- Verification:
  - quality-runner could not provide stable execution evidence for this file in this environment (collection interruption/hang around module-scoped `npm run build` fixture), so fallback direct scoped execution was used per pipeline protocol.
  - Direct scoped pytest (`uv run pytest tests/test_cockpit_pds_build_compat_1364.py -q --tb=line -n 0`): 6 failed, 5 passed (expected RED for #1365 while guard tests pass).
  - Failing proofs remain the intended six `TestFromAC_*` assertions (build gate + known PDS/type mismatches + PendingDR body mismatch).
  - Ruff scoped lint (`uv run ruff check tests/test_cockpit_pds_build_compat_1364.py`): clean.
- Coverage: N/A for this RED proof harness (integration build-output assertions; no Python source-module target).
- Commit: ecc5e6b2 (`test: pin cockpit build gate in red proof (#1364, builder)`).
- Evidence summary: AC refinement from architecture cycle 2 is now encoded in executable form; the test suite will fail if `scripts.build` drops `tsc -b`, closing the previously identified false-green bypass.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_cockpit_pds_build_compat_1364.py`: 5 passed, 6 failed, 0 skipped; `pytest` exit 1.
- The 6 failing assertions are the intended RED gates for the broken snapshot: `test_npm_build_exits_zero`, 4 parametrized `test_known_pds_v4_type_failures_absent[...]` cases, and `test_pending_dr_body_type_mismatch_absent`.
- The 5 passing assertions are the anti-bypass guards added on the retry: 3 directive-scan cases, `test_tsconfig_does_not_disable_typecheck`, and `test_package_json_build_script_keeps_tsc_build`.

### Lint Results
- Ruff scoped to `tests/test_cockpit_pds_build_compat_1364.py`: clean; `ruff` exit 0.

### Coverage
- Not applicable for this review. The artifact under review is a Python RED-proof harness for the frontend build gate; no Python source module is the subject of task #1364.

### Scope / Integrity
- Latest task-related builder commit presence verified in `.git/logs`: `acd93141` (`test: add cockpit pds build red proof (#1364, builder)`), `7240af07` (`test: harden pds build red proof against suppression (#1364, builder)`), and `ecc5e6b2` (`test: pin cockpit build gate in red proof (#1364, builder)`).
- Two prior `## Review Evidence` sections are present in the task body; this review confirms the architecture-cycle-2 refinement is now implemented in the live proof file.
- Diff-scoped dirty-tree verification was not directly available from the current tool surface; confidence is reduced slightly and the verdict relies on quality-runner evidence plus live file inspection.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: a focused frontend verification path proves that `npm run build` in `serve/cockpit/web` must pass cleanly | `tests/test_cockpit_pds_build_compat_1364.py:65` defines `test_npm_build_exits_zero`; the discriminating assertion is at `tests/test_cockpit_pds_build_compat_1364.py:67`. The live delivery gate is still `serve/cockpit/web/package.json:11` (`tsc -b && vite build`). quality-runner reports this test failing on the current broken snapshot. | PASS |
| AC2: coverage or type-focused assertions catch the known PDS v4 component usage failures without broad type suppression, and the proof pins `scripts.build` to `tsc -b` | Output-fragment checks remain at `tests/test_cockpit_pds_build_compat_1364.py:98` and `tests/test_cockpit_pds_build_compat_1364.py:100`. Anti-suppression guards are at `tests/test_cockpit_pds_build_compat_1364.py:126`, `tests/test_cockpit_pds_build_compat_1364.py:133`, `tests/test_cockpit_pds_build_compat_1364.py:135`, `tests/test_cockpit_pds_build_compat_1364.py:139`, `tests/test_cockpit_pds_build_compat_1364.py:140`, `tests/test_cockpit_pds_build_compat_1364.py:142`, and `tests/test_cockpit_pds_build_compat_1364.py:151`. quality-runner shows the 4 audited fragment checks still fail on the broken snapshot while the 5 anti-bypass guards pass. | PASS |
| AC3: the PendingDR and ResolveModal body type mismatch is represented in the failing proof if it is still present | `tests/test_cockpit_pds_build_compat_1364.py:106` defines `test_pending_dr_body_type_mismatch_absent`, with the discriminating assertion at `tests/test_cockpit_pds_build_compat_1364.py:109`. The live mismatch remains visible in `serve/cockpit/web/src/components/ResolveModal.tsx:14`, `serve/cockpit/web/src/components/ResolveModal.tsx:19`, `serve/cockpit/web/src/hooks/usePendingDRs.ts:6`, `serve/cockpit/web/src/hooks/usePendingDRs.ts:13`, `serve/cockpit/web/src/Shell.tsx:28`, `serve/cockpit/web/src/Shell.tsx:187`, and `serve/cockpit/web/src/Shell.tsx:188`. quality-runner reports the AC3 test failing on the current snapshot. | PASS |
| AC4: the proof fails against the audited broken state and is suitable for `#1365` to satisfy; it must not allow a `tsc -b` build-script bypass | quality-runner reports the intended RED shape today: 5 passed / 6 failed. The previously missing build-script pin is now encoded at `tests/test_cockpit_pds_build_compat_1364.py:142` and `tests/test_cockpit_pds_build_compat_1364.py:151`, anchored to the live script at `serve/cockpit/web/package.json:11`. That closes the reviewer-identified `tsc -b` removal bypass from the prior cycle. | PASS |

### Critical Checks
- Security review: PASS. The test invokes a fixed repo-local build command in a fixed cwd; no user-controlled shell interpolation or path traversal was observed.
- Test integrity: PASS. This is a `type:test` task and the architecture review explicitly delegated the RED-proof file to the builder. The original RED assertions remain present at `tests/test_cockpit_pds_build_compat_1364.py:67`, `tests/test_cockpit_pds_build_compat_1364.py:100`, and `tests/test_cockpit_pds_build_compat_1364.py:109`; the retry only adds guard fixtures/tests at `tests/test_cockpit_pds_build_compat_1364.py:115-151`.
- Test quality: PASS. The proof now uses discriminating assertions for the build gate, audited error fragments, directive-based suppression, tsconfig noCheck/strict guards, and the canonical `tsc -b` build-script contract.
- Builder process quality: FRICTION. Three builder cycles are present, but each retry materially changed approach rather than repeating the same tactic. Informational only.

### Deductions
- `-0.03` Dirty-tree / diff-scoped verification was only partially reconstructible from `.git/logs` plus live file inspection because direct `git diff` / `git status` surfaces were not available in the current tool set.

### Verdict
- PASS -> docs
- Confidence: 0.94
- Routing rationale: the architect-refined AC2/AC4 build-script guard is now encoded in executable form, and the scoped quality-runner report shows the proof has the intended RED shape with clean lint.

### Post-task Reflection
- quality-runner was stable for the reviewer even though the builder reported an earlier fallback path, so the final verdict rests on canonical reviewer-owned execution evidence.
- The architecture-cycle-2 refinement translated directly into a discriminating live assertion at `tests/test_cockpit_pds_build_compat_1364.py:151`.
- RED build-proof tasks that shell out to package scripts need the script contract pinned explicitly; output-only assertions were not enough in the earlier review cycles.
[[2026-05-06]]
## Docs Gate

| Check | Applies? | Status | Evidence |
|---|---|---|---|
| 0a: Review Evidence present | Yes | PASS | Three `## Review Evidence` sections present; latest PASS → docs verdict at confidence 0.94 |
| 1: Prose docs | No | N/A | Task is test-only (`type:test`); no behavior, API, CLI, config, or package structure changed |
| 2: Module docstrings | No | N/A | Only `tests/test_cockpit_pds_build_compat_1364.py` changed — test harness, no public source module created or modified |
| 3: External attribution | No | N/A | No external repo, article, or doc patterns incorporated |
| 4: Research doc | No | N/A | No research phase doc produced for this task |
| 5: Diagram maintenance | No | N/A | Changed file (`tests/test_cockpit_pds_build_compat_1364.py`) does not match any diagram `describes` glob; `cockpit.excalidraw` covers `serve/cockpit/src/**` and `serve/cockpit/web/src/**` only |
| 6: Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7: Deletion detection | No | N/A | No files deleted |

**No docs impact.** All seven checklist items N/A.

Files updated: none.
Child tasks created: none.
Scratch files cleaned: none found (`1364-*` absent).
[[2026-05-06]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---|---|---|
| AC1: focused frontend verification path proves `npm run build` must pass cleanly | `tests/test_cockpit_pds_build_compat_1364.py:67` asserts `returncode == 0`; currently fails RED as intended | PASS |
| AC2: assertions catch PDS v4 failures without broad type suppression; proof pins `scripts.build` to `tsc -b` | Output-fragment checks at L100, anti-suppression guards at L126-140, build-script pin at L151; 5 guards pass while 4 fragment checks fail RED | PASS |
| AC3: PendingDR/ResolveModal body mismatch represented if still present | L109 asserts body-mismatch fragment absent; currently fails RED against live mismatch | PASS |
| AC4: proof fails against broken state, suitable for #1365, detects build-script bypass | 6 failed / 5 passed; `tsc -b` pin closes previously-identified false-green path | PASS |

### Test Results
- Task-scoped: 6 failed, 5 passed (intentional RED state confirmed)
- Full suite (excl. 1364): 249 failed, 4656 passed — all pre-existing failures unrelated to this task (test-only addition, no source modifications)
- Lint: ruff clean on task file

### Commit Integrity
- `acd93141` — test: add cockpit pds build red proof (#1364, builder)
- `7240af07` — test: harden pds build red proof against suppression (#1364, builder)
- `ecc5e6b2` — test: pin cockpit build gate in red proof (#1364, builder)

### Architect Quality
- Score: 4/5 — Original AC missed build-script contract pinning; reviewer return prompted architecture cycle 2 which produced a specific, actionable refinement. Final AC is verifiable and complete.

### Deductions
- `-0.02` Full-suite background noise (249 pre-existing failures) prevents pristine cross-task regression baseline, though logically unattributable to this test-only task.

### Confidence: 0.98
### Action: Archive