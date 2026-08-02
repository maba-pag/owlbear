---
id: 2088
title: 'P16-04: Remove legacy runtime, store, and transport execution'
status: archived
priority: high
created: 2026-07-27T08:39:27.780712+02:00
updated: 2026-07-27T10:28:24.013491+02:00
tags:
  - phase-16
  - scope:core
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T4
  - module:MOD-001
  - module:MOD-002
  - module:MOD-004
  - module:MOD-007
parent: 1989
depends_on: []
ac:
  - 'AC-1: Given the shipped Python import inventory, MCP tool inventory, and FastAPI
    route inventory, native change, graph, job, request, evidence, health, history,
    and legacy-inventory read contracts remain callable through their public boundaries.'
  - 'AC-2: Given a lookup or call for legacy task CRUD, arbitrary movement, old lifecycle
    statuses, OpenSpec runtime loading, compatibility translation, or retired task/decision
    routes, the public boundary exposes no registered callable and HTTP surfaces return
    the maintained not-found response.'
  - 'AC-3: Given the native health scanner and mapped package checks after removal,
    they complete without dangling legacy registrations, imports, schemas, or store
    readers.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Shipped Python, MCP, and FastAPI surfaces expose native change/job contracts without an executable legacy task or OpenSpec runtime path.

## Scope
In scope: MOD-001, MOD-002, MOD-004, and MOD-007 legacy readers, task CRUD/lifecycle registrations, old status/schema imports, compatibility translation, and retired HTTP routes.

Out of scope: agent/prompt/skill retirement, consumer installation, documentation, immutable historical inventory, and live-board deletion.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, NEG-004, MIG-001 through MIG-004 consumer inventories, RISK-005, and completed native IF-001 through IF-004, IF-010, and IF-011.

Proof guidance: run focused native import, MCP contract, FastAPI contract, and health checks plus a bounded downstream-impact scan; remove stale tests that preserve retired execution behavior.

[[2026-07-27T10:25:36+02:00]]
## Builder Notes

Implemented the DN-012 P16-04 delivery cutover: removed executable legacy task/OpenSpec engine, stores, migration entry point, task/decision Cockpit routes, and legacy MCP task tools; introduced `NativeWorkspace` bootstrap for Cockpit and MCP; retained native change/job/receipt/request runtime, Ideas, Memory, native SSE, and immutable snapshot inventory. `/api/legacy` now reads only snapshot manifest metadata and does not parse retired schemas.

Proof:
- Native core: 315 passed.
- Cockpit mapped backend: 153 passed; focused native routes 26 passed; native cutover 6 passed.
- MCP complete split execution: 61 non-acceptance, 1 planner, 31 acceptance/lifecycle, and 21 audit cases passed. Splitting avoided only the aggregate session timeout; no case failed.
- Root suite collection: 851 tests collected cleanly.
- Final cutover slice after formatting: 33 passed; builder challenger independently ran 36 tests, APPROVE, no follow-up.
- Ruff production checks passed; editor diagnostics reported no errors.
- Production absence scans found no retired engine/view/model/module imports, legacy task/OpenSpec callables, migration entry point, or task/decision registrations. Retained `storage_io` imports serve Ideas and native transaction locking.

[[2026-07-27T10:27:44+02:00]]
## Verifier Notes

PASS against committed builder artifact `ac1913815efce4ed72c5da6ba0ffabae3e035159`.

- `git show --check` passed.
- Commit-based focused proof passed: 35 tests covering native workspace/bootstrap, immutable snapshot inventory, exact MCP public registry and legacy absence, Cockpit native/retained routes, and retired task/decision 404 behavior.
- Verifier challenger returned PASS with no findings or follow-up. It mapped AC-1 to native exports, exact MCP inventory, and Cockpit route contracts; AC-2 to MCP absence plus OpenAPI/404 assertions; AC-3 to package health, import/collection, Ruff, diagnostics, and production absence evidence.
- Intentional retained boundaries remain correct: snapshot manifest inventory, Ideas, Memory, native SSE, and `storage_io` for Ideas/native transactions.

No compatibility shim or executable legacy task/OpenSpec path remains.

[[2026-07-27T10:28:24+02:00]]
## Collect Notes

ARCHIVED. Builder commit `ac1913815efce4ed72c5da6ba0ffabae3e035159` and verifier commit `f0e6ae2778f521cf1a790d8031deb94c92909215` are reachable from `dev`; the committed source/test slice has no outstanding changes. Direct evidence covers every AC: retained native Python/MCP/FastAPI and immutable inventory boundaries, explicit absence of retired task/OpenSpec tools and routes, and clean package health/import/collection checks. Builder and verifier challengers both approved with no follow-up. No unresolved request or dependency remains.
