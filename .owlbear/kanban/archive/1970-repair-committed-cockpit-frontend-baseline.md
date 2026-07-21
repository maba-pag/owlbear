---
id: 1970
title: Repair committed Cockpit frontend baseline
status: archived
priority: high
created: 2026-07-21T14:10:09.400725+02:00
updated: 2026-07-21T15:32:25.950705+02:00
tags:
  - baseline
  - scope:cockpit-web
  - test
  - maintenance
parent:
depends_on: []
ac:
  - MemoryTab routing tests use the committed score field, score selector, 
    complete lifecycle-state ordering, and current default state set, and the 
    focused file passes without product changes.
  - The obsolete Tailwind generated-output test is removed; production build, 
    Stylelint, and HTMLHint remain the authoritative passing checks for the 
    behavior it duplicated.
  - 'At the resulting exact commit, the complete Cockpit Vitest suite and frontend
    static/build checks pass, while unrelated dirty workspace paths remain uncommitted
    and task #1968 remains untouched.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Restore a commit-addressable green Cockpit frontend baseline by aligning stale MemoryTab routing assertions with the already-committed score/lifecycle UI contract and removing an obsolete generated-output Tailwind test.

## Scope
In scope: `MemoryTab.routing.test.tsx`, deletion of `TailwindStylelint.test.ts`, focused/full frontend proof, and exact-commit verification. Out of scope: MemoryTab product behavior, memory backend/domain changes, workspace-health behavior, admission artifacts, and task #1968.

## Ownership Context
These two paths are the remainder of the baseline-curation work first identified before the workspace-health tasks. Other repair/Cleanup test paths were legitimately absorbed by #1944. The current two-path diff is distinct from unrelated dirty memory, configuration, research, and domain work and must be committed alone.

## Proof Guidance
Run focused MemoryTab tests first, then the complete Cockpit Vitest suite, production build, Stylelint, and HTMLHint. Verify the resulting commit in a disposable exact-SHA checkout. Deletion of the generated-output test is justified by the durable-test rent test: build and Stylelint own those contracts directly, while the test writes a temporary source file, rebuilds the app, and asserts compiler output internals.

[[2026-07-21T14:41:22+02:00]]
## Builder Notes

**Verdict:** DONE to verify.

**Change envelope:** Curated the remaining two Cockpit baseline-test paths without changing product code. `MemoryTab.routing.test.tsx` now asserts the committed score field and selector, complete lifecycle-state ordering, and all non-deleted default states. The obsolete `TailwindStylelint.test.ts` generated-output suite was removed.

**Files changed:** `serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx`; deleted `serve/cockpit/web/src/__tests__/TailwindStylelint.test.ts`; this task record. No product, memory backend/domain, admission, or #1968 artifact is owned by this task.

**Proof selected:** The focused MemoryTab suite binds observable route sorting, row signals, and filter reset behavior. Full Vitest proves package compatibility. Production build and CSS/HTML lint are the direct authorities for the Tailwind/Vite/Stylelint contract formerly inspected through generated output.

**Durable-test justification:** The updated MemoryTab file remains valuable behavioral coverage. The deleted Tailwind test failed the Rent Test: it wrote a temporary source fixture, rebuilt the package, and asserted compiler-output internals including a stale color-variable emission assumption. The maintained build and Stylelint gates exercise that contract more directly and cheaply.

**Commands and results:** Focused MemoryTab passed 56 of 56. Complete Cockpit Vitest passed 123 of 123 files with 1,879 tests passed and 2 skipped. Production build passed with only the existing Vite chunk-size advisory. Stylelint passed. HTMLHint scanned one file with no errors. Owned-path `git diff --check` passed, and no temporary `_tailwind-test-fixture.tsx` remained.

**Memory assessment:** All ten recalled entries were assessed. The artifact-to-scope check was applied directly; active-workspace guidance was followed; the remaining entries were not used.

**Builder challenger:** `decision: pass`; no blocker or auto-fixed file. It confirmed the two-path scope, MemoryTab observable contract, Tailwind test removal, and current-tree proof. Exact-commit repetition is explicitly verifier follow-up after this scoped commit.

[[2026-07-21T15:31:28+02:00]]
## Verify Notes

**Verdict:** PASS to collect.

**Exact revision:** `ce3f10e61bd11b8a7a218b764079ebc99edda5fe` in a disposable detached checkout.

**Scope review:** The commit contains only the #1970 task record, the MemoryTab routing assertion update, and deletion of the obsolete Tailwind generated-output test. No product code, #1968 artifact, or unrelated workspace path is present.

**Exact-commit proof:** Production build passed and emitted multiple JavaScript chunks, with only the existing Vite chunk-size advisory. The complete built-first Vitest run passed 122 of 122 files: 1,878 tests passed and 2 skipped in 232.22 seconds. Stylelint passed. HTMLHint scanned one file with no errors. No temporary `_tailwind-test-fixture.tsx` remained. The detached checkout had no tracked delta; its only untracked path was the deliberate `node_modules` dependency symlink.

**Failure classification:** A pre-build Vitest attempt had one failure in the route chunk assertion because `dist/assets` did not yet exist. That test explicitly requires a prior production build. Running the shaped build gate first made the assertion pass, and the unchanged complete suite then exited green.

**AC judgment:** The retained MemoryTab tests exercise the committed score, selector, lifecycle ordering, and current non-deleted default-state behavior. Build and static lint are the maintained direct authorities replacing the deleted compiler-output inspection test. All three ACs pass at the exact revision.

**Memory assessment:** All ten recalled verifier entries were assessed. Artifact-to-scope and background-debt separation guidance were applied; the remaining entries were not used.

**Verifier challenger:** `decision: pass`; it confirmed exact-revision proof sufficiency, owned-path scope, durable-test rent justification, and no unresolved AC.

[[2026-07-21T15:32:25+02:00]]
## Collect Notes

**Verdict:** ARCHIVED as completed.

This is an ordinary verified leaf with no parent, dependencies, pending requests, or resolved-request obligations. The verifier PASS is committed at `117648b4`, and its exact-revision evidence covers all three ACs at builder revision `ce3f10e61bd11b8a7a218b764079ebc99edda5fe`: production build passed, complete Vitest passed 122 of 122 files with 1,878 tests passed and 2 skipped, Stylelint passed, and HTMLHint reported no errors.

The task-owned commit contains only the task record, MemoryTab routing test alignment, and obsolete Tailwind generated-output test deletion. No product code or #1968 artifact was included. No additional aggregate proof is required.

All seven recalled collector memories were assessed; background-debt separation, active-workspace, and build-proof guidance were applied.
