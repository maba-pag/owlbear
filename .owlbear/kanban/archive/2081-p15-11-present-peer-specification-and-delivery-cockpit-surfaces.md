---
id: 2081
title: 'P15-11: Present peer Specification and Delivery Cockpit surfaces'
status: archived
priority: high
created: 2026-07-26T01:59:59.934764+02:00
updated: 2026-07-26T13:09:47.626936+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-002
  - scope:cockpit-frontend
  - shell
  - specification
  - responsive
  - type:build
  - rigor:thorough
  - risk:RISK-010
parent: 1988
depends_on:
  - 2080
ac:
  - 'AC-1: Given loaded and invalid change summaries, the shell exposes peer `Specification`
    and `Delivery` navigation, stores selected `change_id` in the URL, and labels
    invalid authority with text plus icon rather than color alone.'
  - 'AC-2: Given change detail, Specification displays current digest, Product Intent,
    implementation design, accepted decisions, and authority metadata with retained-data
    Retry states and no task-history dependency.'
  - 'AC-3: At 1440×900 and 390×844, keyboard navigation reaches change selection and
    authority sections, shell controls do not overlap, and the page has no horizontal
    viewport overflow.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 2 for `REQ-010`, `IF-012`, and `RISK-010`.

## Outcome
Cockpit navigation presents Specification and Delivery as peer product phases, with URL-addressable current change authority.

## Envelope
In: routes/shell/provider, change selector, Specification authority reader, invalid/missing/loading/error states, responsive keyboard shell.

Out: graph visualization, operational board, requests, evidence, legacy, feature changes to Memory/Ideas.

Proof guidance: component tests plus browser geometry/focus checks at 1440×900 and 390×844; lower HTTP may be replaced here because PROOF-012 belongs to the final packet.

[[2026-07-26T12:41:45+02:00]]
Builder implementation at digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357 and base SHA 5197c5e150e661168ff13a515677c37bb48787d4. Production App now mounts native-only peer Specification/Delivery shell with URL-backed change selection; invalid/missing/loading/error states; retained Retry; accepted-only decisions; digest, intent, design and authority/admission metadata; Memory/Ideas modules unchanged and Memory task links route to Delivery job URLs. Browser proof at 1440x900 and390x844 verifies keyboard selector reach, icon+text invalid states, bounded controls and no horizontal overflow. Curated only retired legacy Shell/Kanban/Decisions composition tests. Validation 1485 pass/2skip, build, Playwright3, final challenger PASS.

[[2026-07-26T12:54:29+02:00]]
Verifier rejected bde1a1e473c51ae47cc151aba0ef62fb8936d580: URL-requested changes are marked missing while summaries are still loading and alongside summaries errors, producing contradictory states and duplicate Retry controls. Return for state-gating repair.

[[2026-07-26T12:58:39+02:00]]
Final repair gates missing URL changes on successfully loaded summaries, keeping loading, error, and missing states mutually coherent. Added delayed/error/loaded-missing regressions. Validation: build; provider5/5; mandatory components11/11; Playwright3 at desktop/mobile; final signoff PASS. Unrelated workspace state untouched.

[[2026-07-26T13:04:26+02:00]]
## Verify Notes

REJECT at accepted candidate SHA `338ba0a52b5320d9efc77f8e291d124bb1666a1e` for delivery digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`.

Read-only HEAD report: the repair commit changes only `serve/cockpit/web/src/hooks/NativeChangeProvider.tsx` and `serve/cockpit/web/src/__tests__/NativeChangeProvider.test.tsx`; `serve/cockpit/web` remained clean before and after verification.

Focused component command: `npm test` with `NativeChangeProvider.test.tsx`, `SpecificationPage.test.tsx`, `DeliveryPage.test.tsx`, and `NativeShell.test.tsx`. Exact result: 4 test files passed, 12 tests passed, duration 1.08 seconds.

Focused browser command: Playwright `e2e/native-shell.spec.ts` with project `chromium`. Exact result: 3 tests passed in 5.4 seconds: desktop bounded keyboard-accessible geometry, mobile bounded keyboard-accessible geometry, and invalid URL-selected icon plus text in both phases. The configured server also completed its production build and preview startup.

Verifier challenger decision: fail. The E2E keyboard loop proves that `change-selector` receives focus but does not assert that the named authority sections receive focus. Source gives Authority, Authority metadata, Product Intent, and Implementation design `tabIndex={0}`, and the component test checks the Product Intent tab-index contract, but the critical browser proof does not directly exercise authority-section focus at both required viewports. No product or test edits were made because this invocation was explicitly read-only.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-3/authority-keyboard-reach | builder | Extend the focused native-shell Chromium proof to tab beyond the change selector and assert focus reaches the authority section at both 1440x900 and 390x844, then rerun the focused Vitest and Chromium commands. | `serve/cockpit/web/e2e/native-shell.spec.ts` | Verifier challenger fail; current browser loop stops when `change-selector` is reached. |

[[2026-07-26T13:05:35+02:00]]
Verifier repair strengthens AC-3 browser proof: at 1440x900 and390x844 keyboard Tab traversal must reach change selector, Authority metadata, and Product Intent section hosts; geometry/no-overflow and invalid icon/text remain asserted. Playwright 3/3 passed.

[[2026-07-26T13:09:06+02:00]]
## Verify Notes

PASS at accepted candidate SHA `71c3bfff155b96f831eef4735f0fc1849f46b413` for delivery digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`.

Read-only HEAD report: the accepted commit changes only `serve/cockpit/web/e2e/native-shell.spec.ts`; `serve/cockpit/web` was clean before and after verification. No product or test edits were made.

Focused Vitest result for NativeChangeProvider, SpecificationPage, DeliveryPage, and NativeShell: exactly 4 test files passed and 12 tests passed in 1.07 seconds.

Focused Playwright result for `e2e/native-shell.spec.ts` on Chromium: exactly 3 tests passed in 5.4 seconds. Desktop 1440x900 and mobile 390x844 proofs require keyboard traversal to reach change selection, Authority metadata, and Product Intent section hosts, while preserving bounded controls and no horizontal overflow. Invalid URL-selected change text plus icon passes in both phases.

Required follow-up `AC-3/authority-keyboard-reach` is closed by the desktop and mobile Chromium focus assertions at this SHA. Verifier challenger decision: pass.

[[2026-07-26T13:09:47+02:00]]
## Collect Notes

ARCHIVED: delivery digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357` accepted at SHA `71c3bfff155b96f831eef4735f0fc1849f46b413`.

Closure evidence: focused Vitest passed exactly 4 test files and 12 tests in 1.07 seconds; native-shell Playwright on Chromium passed exactly 3 tests in 5.4 seconds at desktop 1440x900 and mobile 390x844. The prior `AC-3/authority-keyboard-reach` follow-up is explicitly closed, verifier challenger passed, and final `serve/cockpit/web` scope was clean. Read-only collection; no edits or commits.
