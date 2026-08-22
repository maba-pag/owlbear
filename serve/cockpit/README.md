# owlbear-cockpit — Steering Cockpit Package

Cockpit combines a FastAPI backend (`src/owlbear_cockpit/`) with a React frontend (`web/`),
served as built static assets from `dist/`. The backend loads the canonical Delivery application
and projects admitted semantic work items, requests, evidence, Memory, and Ideas without becoming
Delivery authority.

**Use this guide when:** you need to build, launch, or package Cockpit, or trace its frontend/backend
boundary and human operator controls.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

Launch against a consumer project that references a sibling owlbear clone:

```bash
cd ../my-project
uv run --project ../owlbear cockpit
```

Launch from the owlbear development checkout:

```bash
uv run cockpit
```

`uv run cockpit` serves `serve/cockpit/dist/`, starts on `127.0.0.1:8420` by default,
and opens a browser unless disabled with `COCKPIT_NO_OPEN=1`. Cockpit reads
`.owlbear/delivery/config.json`, canonical Delivery state, and `.owlbear/memory/` relative to the
workspace root. Consumer launches must use the target project as their working directory or pass
it to `uv --directory`.

Build frontend assets for the developer/source workflow:

```bash
cd serve/cockpit/web
npm run build
cd -
```

Sync Porsche Design System runtime assets from CDN (developer maintenance command):

```bash
cd serve/cockpit/web
npm run sync:pds
cd -
```

This downloads the core chunk, 60 component chunks, and 290 icon SVGs from
`cdn.ui.porsche.com` into `public/porsche-design-system/` and commits them for offline
use. Assets are version-pinned to the installed `@porsche-design-system/components-js`.
CI and sync-to-main run this automatically; developers only need to run it locally when
preparing or debugging PDS upgrades.

## Frontend Surface

Frontend source is under `serve/cockpit/web/` and is the only Node/npm package in this
repository.

| Attribute | Value |
| --- | --- |
| Node development pin | `24.19.0` (`web/.nvmrc`) |
| Node support/build floor | `>=24.16.0` (`web/package.json`) |
| Stack | React `^19.2.7`, Vite `^8.1.5`, TypeScript `^6.0.3`, React Router `^8.2.0`, Porsche Design System React `^4.5.0`, React Compiler (`babel-plugin-react-compiler` `^1.0.0`), Tailwind CSS `^4.3.3` (`@tailwindcss/vite` + `tailwindcss`) |
| Test runner | Vitest `^4.1.10` (`npm test`) |
| E2E runner | Playwright `^1.61.1` (`npm run test:e2e`) |
| Browser output target | Chrome/Edge `123`, Firefox `120`, Safari/iOS `17.5` (native `light-dark()` floor) |
| CSS/HTML lint | Stylelint `^17.12.0` (`npm run lint:css`), HTMLHint `^1.9.2` (`npm run lint:html`) |
| Build output | `serve/cockpit/dist/` via `npm run build` |

The Node development pin is the reproducible local toolchain; the support/build floor is the
oldest Cockpit runtime exercised in CI. Vite compiles JavaScript and CSS for the listed browser
target but does not polyfill missing Web APIs. The browser floor includes native `light-dark()`
support; TypeScript's `ES2020` target is a type-checking configuration here because the project
uses `noEmit`.

## Browser-backed tests

These tests run from the OwlBear development checkout, not from a consumer project. Install the
web dependencies and Chromium once, then run the maintained Cockpit gate:

```shell
cd /path/to/owlbear
npm ci --prefix serve/cockpit/web
cd serve/cockpit/web
npx playwright install chromium
cd ../../..
uv run test-e2e
```

Expected result: the Cockpit smoke tests start without an executable-missing error. Consumer
workspaces use the prebuilt bundle and do not run this developer-only procedure.

Run the explicit cross-engine compatibility smoke gate when validating browser support:

```shell
cd /path/to/owlbear/serve/cockpit/web
npx playwright install chromium firefox webkit
npm run test:e2e:compat
```

The compatibility gate uses a separate Playwright configuration and runs only the shell and PDS
smoke scenarios against the Playwright-pinned current Chromium, Firefox, and WebKit engines. It
does not execute the exact minimum browser versions in the output-target table. The maintained
fast and assembled suites remain Chromium-only.

## Delivery Evidence

Cockpit projects current Delivery state and user-owned controls without becoming authority:

| Surface | Authority |
| --- | --- |
| Outcome portfolio | Admitted outcomes, dependencies, Planning/Build stages, task progress, and explicit per-Change admission/runtime status from `PortfolioApplication` |
| Actionable attention | Typed requests, requestless blocks, long-idle claims, revision attention, publication and target-sync attention, and acceptance attention |
| User controls | Answer requests, clear blocks, recover confirmed-dead claims or worktrees, move backward, reconcile target-sync conflicts, supersede a publication, and observe acceptance |
| Completed history | Bounded list, semantic search, and exact completed-change lookup |
| Startup authority | Tracked `.owlbear/delivery/config.json` and validated canonical Delivery roots |

The `/api/work-items` response consumes Delivery's explicit status axes. A package is shown as
unadmitted Design only when persisted admission is absent. An admitted Change with no tasks is a
valid Planning state and reports `Task plan not published`; an admitted but non-actionable Change
retains its admission state and reports the generic `runtime_unavailable` diagnostic.

The current frontend polls `/api/work-items` every three seconds. Each poll observes a reconciled
Delivery read, so an already-running Cockpit can see newly admitted Changes without a process
restart. Polling does not reload the full application, use SSE, or replace persisted Delivery
authority.

The assembled FastAPI inventory preserves 21 POST routes for user-owned controls:

| Control family | Preserved operations | Routes |
| --- | --- | ---: |
| Requests and outcomes | Answer a request; clear a requestless block; recover a claim; preview a backward move; apply a backward move | 5 |
| Publication and acceptance | Reconcile acceptance; reconcile a publication; mark ready; observe acceptance; observe publication checks; resolve attention; supersede a publication; defer; resume | 9 |
| Target and worktree | Sync with target; abort or resolve a target conflict; abandon a Change; clean up abandoned or completed worktrees; recover a worktree | 7 |

These controls remain Cockpit user authority and continue to use the Delivery domain methods and
locks. Cockpit does not schedule work, choose worker transitions, interpret reviewer evidence, or
silently turn these controls into agent actions.

Cause-specific missing-coordination classification is deferred to a separate follow-up Change.
Delivery MCP user-control parity is also deferred: this remediation adds no Delivery MCP operation,
and any later parity work must define explicit user confirmation and reuse the core Delivery
methods.

Cockpit calls the same transport-free application owners used by the MCP adapter but exposes the
answer-bearing and administrative controls reserved for users. It does not schedule work, choose
worker transitions, interpret reviewer evidence, repair source, merge pull requests, or update the
configured target branch on its own. Persisted legacy Integration attention remains visible only
through compatibility surfaces.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |

Cockpit always reads Delivery authority and memory state from the current workspace and serves the
package's bundled `dist/` directory.

## Delivery Packaging

- Developer branch (`dev`): frontend source (`serve/cockpit/web/`) is present and used for
  build/test/lint workflows.
- Consumer branch (`main`): sync-to-main builds and stages prebuilt
  `serve/cockpit/dist/` artifacts; consumers launch Cockpit from their project root with
  `uv run --project ../owlbear cockpit` and do not need Node/npm.

## Dependencies

| Package | Purpose |
| --- | --- |
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `owlbear-delivery` | Design authority, Delivery runtime, admission, publication, acceptance observation, and completed history |
| `owlbear-memory` | Memory engine (workspace package) |
