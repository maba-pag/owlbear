---
id: 1976
title: Restore DetailTab lifecycle bounds under PDS 4.5
status: build
priority: high
created: 2026-07-21T18:33:01.110997+02:00
updated: 2026-07-21T23:10:31.261126+02:00
tags:
  - baseline-repair
  - frontend
  - test-infra
  - scope:cockpit
parent:
depends_on: []
ac:
  - 'AC-1: Given a clean frontend install from `package-lock.json`, `npm ls @porsche-design-system/components-js
    @porsche-design-system/components-react` exits zero and reports one deduplicated
    4.5.0 instance of each package, while the root manifest declares `^4.5.0` for
    both direct dependencies.'
  - "AC-2: Given `DetailTab` in display mode, the rendered surface includes `Edit
    details` and omits the edit form plus its priority `p-select`; after invoking
    `Edit details`, the edit form and priority control are rendered with the task's
    current values."
  - "AC-3: Given PDS 4.5.0 and Cockpit's maintained jsdom setup, `npm test -- src/__tests__/DetailTab`
    terminates and exits zero across the descriptively named DetailTab concern suites,
    with no `SelectOption.onSlotChange` teardown error; no suite basename contains
    `testbuilderdiscovered` or `testfromac-additional-groups`."
  - 'AC-4: Given the task-owned frontend changes, the maintained unsharded `npm test`
    command terminates and exits zero with zero failed test files and zero failed
    tests, and `npm run build` exits zero without a PDS asset-version mismatch diagnostic.'
  - "AC-5: At the task's final archive commit in a clean detached checkout, these
    admission commands exit zero: Cockpit build; Python non-API and non-E2E suite;
    Ruff check; Ruff format check; Stylelint; HTMLHint; ESLint; maintained unsharded
    `npm test`; maintained `npm run test:e2e` fast Playwright gate."
  - 'AC-6: Given `MarkdownPreview` renders `<script>alert(1)</script><img src="x"
    onerror="alert(2)">[unsafe](javascript:alert(3))safe` through the real markdown
    pipeline without a markdown mock, the output includes `safe` and contains no `script`
    element, no `onerror` attribute, and no anchor `href` beginning with `javascript:`.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Restore the deterministic Cockpit unit-test baseline while retaining Porsche Design System 4.5.0 by aligning direct dependency authority, avoiding hidden edit-surface custom-element work, and curating legacy DetailTab coverage into bounded behavioral concern suites.

## Grounded Defect
Dependency-first diagnosis found a coherent, peer-compatible, deduplicated PDS 4.5.0 install and synchronized 4.5.0 self-hosted assets, but the root manifest still declared 4.4-compatible ranges. The remaining termination defect is cumulative lifecycle work in the legacy 58-test `DetailTab.test.tsx`: `TaskFieldsEditor` mounts the complete PDS edit form, including the proof-bundle select options, while display mode only hides it. PDS 4.5.0 queues `SelectOption.onSlotChange` callbacks during teardown; repeated real edit-form mounts eventually stall file cleanup. Neighboring real-PDS select coverage and smaller DetailTab groups terminate, while error suppression and detached-slot cleanup probes do not restore the full-file boundary.

## Scope
- Retain PDS 4.5.0 packages and synchronized self-hosted assets; update direct dependency ranges to `^4.5.0` without introducing overrides or duplicate versions.
- In `TaskFieldsEditor`, render the display surface alone until the user invokes `Edit details`; mount the existing edit form and PDS controls only while editing.
- Update DetailTab tests that interact with edit controls to enter edit mode through the public `Edit details` action.
- Curate the legacy `DetailTab.test.tsx` assertions by the durable-test Rent Test: consolidate the display/edit regression and unique user interactions, mine unique acceptance-criteria, payload, callback, confirmation, and accessibility assertions into descriptively named concern suites, and remove duplicate or DOM-scaffolding assertions.
- Move the legacy mocked script-injection assertion to `MarkdownPreview.test.tsx`, where the real markdown and sanitization boundary is rendered.
- Remove artifact-named split suites after mining; do not preserve a historical test count as an acceptance target.
- Do not mock PDS controls, suppress runtime errors, patch installed dependency files, change Vitest sequencing, or replace the maintained unsharded test command with diagnostic shards.

## Proof Guidance
Run `npm test -- src/__tests__/DetailTab` through the maintained package script first; this prefix selects the complete descriptively named DetailTab concern suite. Then run `npm ls` for the two PDS packages, the maintained unsharded `npm test`, and `npm run build`. Treat a process that reaches passing assertions but does not return to the shell as failed termination. The final archive revision must pass the complete admission baseline in a clean detached checkout and receive an independent challenge tied to that revision.

## Change Module Map
- Dependency authority: `serve/cockpit/web/package.json` and `serve/cockpit/web/package-lock.json`.
- Runtime owner: `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`; its display/edit state controls whether the PDS form exists.
- Primary display/edit regression owner: `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` plus its non-test support module.
- Concern owners: existing descriptively named `DetailTab*.test.tsx` suites; a new `DetailTab.acceptance-criteria.test.tsx` only if no existing concern owner fits; `MarkdownPreview.test.tsx` for real markdown sanitization.
- Explicitly unchanged boundaries: `serve/cockpit/web/vitest.setup.ts`, `serve/cockpit/web/vite.config.ts`, installed PDS files, and the `npm test` script.

## Prior Rejection Evidence
The original stack-qualified window-error guard prevented reporting but did not stop the underlying slotchange lifecycle work, so it was fully reverted. Dependency diagnosis ruled out duplicate PDS versions, peer conflicts, stale installed packages, Node mismatch, and stale self-hosted assets. A mechanical three-file split then proved that fresh jsdom environments terminate, but independent challenge rejected its historical 58-test target and artifact-named duplicate suites under the Rent Test.

## User Direction
- Keep Porsche Design System 4.5.0; do not restore 4.4.0.
- Start the repair at dependency resolution and installation before considering test restructuring or dependency patching.

## Shape Notes
- Repair classification: material reshape because current source moved ownership from a test-harness error guard to production render lifecycle plus durable test curation.
- Dependency facts: one deduplicated, peer-compatible PDS 4.5.0 tree; direct manifest authority corrected to `^4.5.0`; synchronized assets remain 4.5.0.
- Discriminating evidence: the 20-test editable group terminates; a 16-test mutation suite terminates in 7.3 seconds; the unsplit 58-test file stalls in `afterEach`; three fresh jsdom files terminate in 15.1 seconds; Cockpit build exits zero.
- Challenger repair: replace unnamed three-file and fixed-count criteria with the independently identifiable `DetailTab` file-prefix gate; mine unique assertions into named concern owners and remove duplicate or low-value task artifacts.
- Resulting route requires a fresh challenger pass before `build`; maintained unsharded `npm test` remains the acceptance boundary.



## Shape Challenge Repair
- First challenge removed the fixed 58-test target and artifact-named duplicate suites in favor of durable concern owners and the `DetailTab` prefix gate.
- Second challenge identified that the real-boundary markdown sanitization relocation lacked an owning AC. AC-6 now names concrete script, event-handler, and `javascript:` URL inputs and observable sanitized output through the unmocked `MarkdownPreview` boundary.

[[2026-07-21T23:10:31+02:00]]
## Shape Notes
- Repaired the rejected error-suppression shape after dependency-first diagnosis and current-source validation.
- Retained PDS 4.5.0, corrected direct dependency authority to `^4.5.0`, and identified `TaskFieldsEditor` display/edit rendering as the production lifecycle owner.
- Replaced the historical 58-test preservation target with Rent-Test curation into descriptively named concern suites and the independently identifiable `npm test -- src/__tests__/DetailTab` gate.
- Added AC-6 so the legacy mocked script-injection assertion must be replaced at the unmocked `MarkdownPreview` sanitization boundary.
- Fresh shaper-challenger verdict: pass. It confirmed AC-1 through AC-6 are boundary-valid, independently verifiable, and build-ready; no PDS mocks, suppression, installed patches, or Vitest sharding are admitted.
- Route: `build`; full unsharded `npm test`, build, and final clean-detached admission baseline remain mandatory.
