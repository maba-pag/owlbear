---
id: 1364
title: 'P1-01: Test Cockpit PDS v4 build compatibility'
status: review
priority: critical
created: 2026-05-06T00:58:30.519362+00:00
updated: 2026-05-06T04:09:28.697833+00:00
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