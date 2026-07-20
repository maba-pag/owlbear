---
id: 1966
title: 'P1-16: Establish assembled Memory purge browser proof'
status: verify
priority: medium
created: 2026-07-20T02:44:11.341963+02:00
updated: 2026-07-20T08:59:30.777294+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - test
  - integration
parent: 1951
depends_on:
  - 1950
ac:
  - 'AC-1: Given fixture-owned Kanban and Memory stores, the maintained browser proof
    command starts the built Cockpit frontend through the production FastAPI application
    with a real MemoryEngine, reaches the rendered Memory page, suppresses browser
    auto-open, and leaves workspace stores unchanged after the run.'
  - 'AC-2: Given eligible, exact-cutoff, too-recent, and non-deleted fixture memories,
    the rendered workflow proves positive-day and zero-day preview and execution through
    real HTTP and engine boundaries, with only eligible tombstones absent afterward
    and preserved entries still present.'
  - 'AC-3: Given restrictive Memory filters and one controlled eligible-file unlink
    failure, the rendered workflow shows project-wide counts and warning, cancellation
    without mutation, and an execution receipt with purged, skipped, and failed counts
    followed by refreshed entries and Purge deleted (N); verifier records the tested
    commit SHA and command result.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide a maintained isolated browser harness and executable evidence through the rendered MemoryTab, production FastAPI application, and real MemoryEngine.

## Scope
In scope: Playwright/server fixture configuration, fixture-owned Kanban and Memory stores, deterministic tombstone timestamps, one controlled lower-level unlink failure, assembled purge browser cases, and tested-commit evidence. Out of scope: product behavior changes, endpoint changes, alternate engine or API implementations, and broad E2E refactoring.

## Planning Authority
OpenSpec change `purge-deleted-memories`, Design migration step 4, and advisory task 4.1. Existing product behavior is supplied by completed siblings #1946 through #1950.

## Complexity Waiver
The three high-proof criteria share one browser proof mode and one harness lifecycle. Splitting startup and fixture ownership from workflow proof would duplicate infrastructure while neither task could independently prove the assembled boundary.

## Proof Guidance
Use a maintained package-local Playwright command. The rendered MemoryTab, production FastAPI application, Memory HTTP routes, and real MemoryEngine may not be mocked or replaced; only a lower filesystem unlink may be controlled for deterministic partial failure. Run focused Memory, Cockpit backend, and frontend checks plus the production frontend build and applicable lint checks. Record the tested commit SHA and command results in Builder and Verify Notes.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| Cockpit Playwright configuration/support/spec | Vite-only browser proof with mocked backend | Add isolated production-stack purge proof | Maintained test command/harness |
| Cockpit production entry point | Environment-configured FastAPI/static launch | Reuse as-is; add only a minimal test startup seam if source proves necessary | None expected |
| MemoryEngine and Memory HTTP routes | Purge behavior and public HTTP contract | Read-only assembled dependencies | None |
| MemoryTab purge workflow | Rendered maintenance interaction | Read-only assembled boundary | None |

## Product Invariant Map
| Product Invariant | Owner | Normal-Path Boundary |
|---|---|---|
| The assembled rendered workflow reaches real HTTP and engine behavior | This task | Browser through production Cockpit application |
| Test fixture mutation cannot alter workspace stores | This task | Isolated launch and post-run store audit |
| Engine cache/index coherence and deletion semantics remain intact | #1947 | Prior verified core boundary plus aggregate audit |

## Product Promise Coverage
- Eligible-only purge and newer/non-deleted preservation: #1946 behavior plus AC-2.
- Project-wide filter-independent scope and strict HTTP contract: #1948 behavior plus AC-2 and AC-3.
- Ordered ephemeral threshold flow: #1949 behavior plus AC-2 and AC-3.
- Visible action, warning, receipt, and refresh: #1950 behavior plus AC-3.
- Preserved deletion semantics and exclusions: prior child Verify Notes plus AC-1 and AC-2.

[[2026-07-20T02:56:32+02:00]]
## Builder Notes
Change envelope: package-local Cockpit Playwright configuration/support/spec only; no product/API changes.

Files changed: `serve/cockpit/web/playwright.config.ts`, `serve/cockpit/web/package.json`, `serve/cockpit/web/e2e/support/start-memory-purge-stack.mjs`, `serve/cockpit/web/e2e/memory-purge-assembled.spec.ts`.

Change Module Map deviations: none; production Cockpit entry point, MemoryEngine, HTTP routes, and MemoryTab remain read-only.

Proof selected: assembled Playwright project with fixture-owned Kanban and Memory stores, deterministic tombstones, production FastAPI launch settings, cancellation, positive-day preview, and zero-day execution. No durable product tests added.

Commands run: direct Playwright discovery/build previously succeeded; `get_errors` reported no errors in all touched proof files. Final assembled browser proof was not completed. Direct launcher diagnosis showed the child command resolving to an unrelated Vitest invocation and exiting before Cockpit startup; package command also encountered terminal/session exit-130 behavior.

Builder challenger: fail. First concrete issues found and fixed were fixture root resolution and assembled project baseURL. Final blocker is environment/command resolution before server startup.

Follow-up risk: do not route to verify until `node e2e/support/start-memory-purge-stack.mjs` demonstrably keeps `uv run cockpit` listening on `127.0.0.1:8421` and the focused Playwright command reports a passing browser result.

[[2026-07-20T08:59:30+02:00]]
## Builder Recovery Notes
- Root causes fixed: the launcher now resolves the repository Cockpit package explicitly; Playwright selects the production-stack server at its supported top-level boundary; fixture timestamps remain strings through YAML; threshold edits keep the purge dialog open in a configuring state.
- Assembled proof: `npm run test:e2e:memory-purge -- e2e/memory-purge-assembled.spec.ts --reporter=line` passed 1 test through built Cockpit, production FastAPI, real Memory HTTP routes, and real MemoryEngine. It proves cancellation, positive-day and zero-day previews, restrictive deleted-state filtering with project-wide counts, preserved active/recent entries, and one controlled macOS immutable-file unlink failure with receipt `Purged 2; skipped 0; failed 1` and refreshed `Purge deleted (1)`.
- Additional checks: focused purge hook tests passed; production frontend build passed; task-scoped lint passed idempotently; repository `uv run lint-all` passed before final proof-only edits.
- Delivery commit: `b3a1ce2ec957128e5e8d7747e09ebfb9ea7c00e6`.
- Builder challenger: pass; no blocking defects.
