---
id: 2098
title: 'P17-05: Verify the assembled Cockpit release journey'
status: collect
priority: high
created: 2026-07-27T19:45:20.808938+02:00
updated: 2026-07-28T12:00:30.566838+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T5
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on:
  - 2097
ac:
  - "AC-1: Given #2097's completed temporary consumer, the built Cockpit SPA over
    the real FastAPI backend displays admitted specification, plan/build/accept/audit
    history, supersession/corrective chain, current receipts, evidence, activity,
    and immutable legacy inventory through Specification, Delivery, Evidence, Activity,
    and Legacy routes without mocked HTTP."
  - 'AC-2: Given desktop and mobile viewports, the representative journey resolves
    its maintained request interaction, reaches final-audit/current-chain state, emits
    no page exception, renders nonblank content, and has neither horizontal overflow
    nor overlap among the inspected route header, navigation, controls, and primary
    content bounds.'
  - 'AC-3: Given successful public setup, assembled MCP workflow, native launch, and
    browser journey, durable PROOF-013 output records invoked commands, tested Git
    revision, delivery/node-plan digests, admission/plan/build/accept/audit receipts,
    corrective finding/supersession identities, allowed replacements, native health,
    and active legacy-surface absence for DN-015; it does not invoke live carrier
    finalization.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Built Cockpit observes the actual completed and corrective state from #2097 in the temporary consumer on desktop and mobile and records the durable PROOF-013 release evidence.

## Scope
In scope: MOD-008 Playwright/FastAPI proof over #2097 scenario state. Out of scope: mocked HTTP, product fixes, live carrier mutation, and DN-015 execution.

## Authority
DN-013, REQ-018, PROOF-013, IF-011/012/013/014, RISK-005/RISK-009/RISK-010/RISK-012 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a dedicated serial Playwright desktop/mobile project plus focused API/proof-output assertions; the #2097 fixture repository is allowed, but HTTP and UI are not replaced.

[[2026-07-28T11:56:42+02:00]]
## Builder Notes

DONE. Added a dedicated PROOF-013 Cockpit release stack that exports the completed #2097 fresh-consumer workflow, preserves the existing PROOF-009 default seeder, skips finalization/DN-015, and exercises the built SPA over real FastAPI on desktop and mobile.

- AC-1: `npm run test:e2e:native-release` passed 2/2 against real uvicorn/FastAPI and the production SPA build. Specification, Delivery, Evidence, Activity, and Legacy showed admitted authority, plan/build/accept/audit history, current receipts, supersession/invalidation/finding chain, final audit, and empty immutable legacy inventory.
- AC-2: The serial 1440x900 and 390x844 journeys resolved their maintained requests, captured clean page/API error arrays, asserted nonblank content, zero horizontal overflow, and pairwise non-overlap for navigation, route headers, controls, and primary content. Screenshots were inspected for desktop authority/graph, mobile correction history, and empty Legacy.
- AC-3: `.owlbear/scratch/proof-013-cockpit.json` records setup/workflow/browser commands, tested revision, delivery and all three node-plan digests, admission/plan/build/accept/audit receipt identities, corrective identities, allowed replacements, both viewport runs, clean work/change health, empty legacy state, and explicit `setup_finalize_invoked=false` / `dn_015_invoked=false`.

Focused proof: release E2E 2 passed repeatedly; Ruff clean; Cockpit production build, CSS lint, and HTML lint clean; default `tests/test_native_cutover.py` 2 passed; normal/export assembled workflow each passed. Builder challenger independently reran the release E2E and returned pass with no repair.

[[2026-07-28T12:00:30+02:00]]
## Verify Notes

PASS. Verified committed builder state at `732c75136d908cc2c708955c4f1c4bd5d161699d`.

- AC-1: Fresh `npm run test:e2e:native-release` passed 2/2 against the built SPA and real FastAPI/uvicorn stack. The journey asserts admitted authority, completed lifecycle receipt history, current corrected receipt state, terminal audit, supersession/invalidation/finding chain, Activity, and exact empty immutable Legacy API/UI state.
- AC-2: Both required viewports resolve their maintained request and collect clean API/page-error arrays. The browser asserts nonblank routes, zero horizontal overflow, and pairwise non-overlap across six route samples for navigation, route headers, controls, and primary content; four screenshots per viewport were produced.
- AC-3: An independent external parser validated the generated durable manifest: tested revision; delivery plus DN-001/DN-002/DN-014 plan digests; admission and all plan/build/accept/audit/supersession identities; exact corrective IDs; whole-change `/` audit; clean work/change health; no active legacy state; real FastAPI/built SPA markers; both viewport runs; and false finalization/DN-015 flags.

The first external parser attempt expected five geometry samples, but the journey intentionally inspects six routes; correcting that verifier-only assertion passed without changing product or proof code. Verifier challenger returned pass with no findings and explicitly confirmed this did not invalidate evidence.
