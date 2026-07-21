---
id: 1976
title: Restore Vitest termination for PDS select teardown
status: shape
priority: high
created: 2026-07-21T18:33:01.110997+02:00
updated: 2026-07-21T18:36:54.574222+02:00
tags:
  - baseline-repair
  - frontend
  - test-infra
  - scope:cockpit
parent:
depends_on: []
ac:
  - 'AC-1: Given a window error whose TypeError message, stack frame, and package
    path match the PDS teardown defect, the maintained Vitest setup prevents that
    event; given the same message with a stack outside that PDS frame/path, the event
    remains unprevented.'
  - "AC-2: Given PDS 4.5.0 and Cockpit's maintained jsdom setup, `npm test -- src/__tests__/DetailTab.test.tsx`
    terminates, exits zero, and emits no unhandled matching PDS teardown error."
  - 'AC-3: Given the patched harness, the maintained unsharded `npm test` command
    terminates and exits zero with zero failed test files and zero failed tests.'
  - 'AC-4: Given the final task archive commit in a clean detached checkout, the admission
    baseline commands pass: Cockpit build with no PDS mismatch diagnostic; Python
    non-API/non-E2E suite; Ruff check and format check; Stylelint; HTMLHint; ESLint;
    maintained unsharded `npm test`; maintained `npm run test:e2e` fast Playwright
    gate.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Restore the deterministic Cockpit unit-test baseline after the lock-resolved Porsche Design System 4.5.0 jsdom polyfill leaves `DetailTab.test.tsx` teardown non-terminating.

## Grounded Defect
At exact revision `55b9365a4c432dcebc3446a780bfa12aff54e89c`, diagnostic sharding and bounded bisection isolate the hang to `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`. Its final test passes before teardown times out. PDS emits `TypeError: Cannot read properties of null (reading 'children')` from `SelectOption.onSlotChange` under `@porsche-design-system/components-js/jsdom-polyfill` after a select option is detached.

## Scope
Extend the existing known-PDS jsdom error guard only when the exact message, `SelectOption.onSlotChange` stack frame, and PDS jsdom-polyfill package path match. Add one focused harness contract proving the matching event is prevented and the same message from an unrelated stack is not. Do not change production code or dependencies. If this guard does not restore isolated termination, return the task to shape instead of widening it.

## Proof Guidance
Patch the guard first and immediately rerun the isolated DetailTab command. If it terminates, add and run the focused positive/negative harness contract, then run the maintained unsharded `npm test`. Diagnostic shards are evidence only, not the maintained acceptance boundary. The final archive revision must pass the complete admission baseline and independent verifier challenge.

## Shape Notes
- Shaper challenger decision: pass after replacing diagnostic shard criteria with the maintained unsharded gate and qualifying the suppression by message, frame, and dependency path.
- Change Module Map: owner `serve/cockpit/web/vitest.setup.ts`; focused proof under `serve/cockpit/web/src/__tests__/`; interface is the globally registered capture-phase window error guard; no production interface changes.

[[2026-07-21T18:36:54+02:00]]
## Builder Notes
- Tested the shaped mechanism with the smallest reversible edit: a capture-phase guard matching the exact `children` message, `SelectOption.onSlotChange` frame, and PDS jsdom-polyfill path.
- `npm test -- src/__tests__/DetailTab.test.tsx` still failed to terminate within the safety bound. A bounded verbose run had already shown the final test passes before teardown stalls, so `preventDefault()` affects error reporting but does not stop the underlying slotchange cleanup loop.
- Reverted the probe completely; `git diff --exit-code -- serve/cockpit/web/vitest.setup.ts` passes. No product or test-harness change remains.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper | Replace the error-suppression mechanism with a narrowly bounded PDS detached-option cleanup/event mechanism, grounded in executable proof; preserve the maintained unsharded `npm test` boundary and unrelated-error visibility. | `serve/cockpit/web/vitest.setup.ts`, installed PDS 4.5 jsdom polyfill source, focused harness proof | Exact isolated command remains non-terminating after the stack-qualified error guard; probe is reverted. |
