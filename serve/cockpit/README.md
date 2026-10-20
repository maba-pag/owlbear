# owlbear-cockpit — Steering Cockpit Package

Cockpit combines a FastAPI backend (`src/owlbear_cockpit/`) with a React frontend (`web/`),
served as built static assets from `dist/`. It shows and edits the workspace's Memory and Ideas.
Changes run on the new Delivery engine's Changes page; Cockpit's old Delivery view is retired.

**Use this guide when:** you need to build, launch, or package Cockpit, or trace its frontend/backend
boundary.

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
and opens a browser unless disabled with `COCKPIT_NO_OPEN=1`. Cockpit reads `.owlbear/memory/` and
`.owlbear/ideas.md` relative to the workspace root. Consumer launches must use the target project
as their working directory or pass it to `uv --directory`.

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
CI runs this automatically; run it locally only when preparing or debugging PDS upgrades.

## Frontend Surface

Frontend source is under `serve/cockpit/web/` and is the only Node/npm package in this
repository.

| Attribute | Value |
| --- | --- |
| Node development pin | `24.21.0` (`web/.nvmrc`) |
| Node engine floor | `>=24.21.0` (`web/package.json`) |
| Stack | React `^19.2.7`, Vite `^8.1.5`, TypeScript `^6.0.3`, React Router `^8.2.0`, Porsche Design System React `^4.5.0`, React Compiler (`babel-plugin-react-compiler` `^1.0.0`), Tailwind CSS `^4.3.3` (`@tailwindcss/vite` + `tailwindcss`) |
| Test runner | Vitest `^4.1.10` (`npm test`) |
| E2E runner | Playwright `^1.61.1` (`npm run test:e2e`) |
| Browser output target | Chrome/Edge `123` (native `light-dark()` floor) |
| CSS/HTML lint | Biome `2.5.11`, HTMLHint `^1.9.2` (`npm run lint:html`) |
| Build output | `serve/cockpit/dist/` via `npm run build` |

The Node development pin is the reproducible local toolchain; the support/build floor is the
Node is pinned to `24.21.0` for local development and CI, and the package engine floor matches it.
Vite targets Chrome and Edge `123` and does not polyfill missing Web APIs. The target includes
native `light-dark()` support; TypeScript's `ES2020` target is a type-checking configuration here
because the project uses `noEmit`.

## Frontend Quality

From the development checkout root, `uv run lint-cockpit` applies safe Biome fixes and runs
HTMLHint. Use `--no-fix` for check-only runs or `--unsafe-fix` to opt into unsafe Biome fixes.
`uv run format-biome` formats without lint fixes; `uv run format` includes it. Both commands
support `--staged`. `uv run help quality` lists the complete command tree and options.
`uv run typecheck-cockpit` checks both the application and all E2E TypeScript inputs.

The root [Biome configuration](../../biome.json) owns frontend code, configuration, scripts,
CSS, and repository JSON/JSONC. Git ignores and explicit exclusions protect generated, vendored,
and machine-managed files. Biome natively skips npm lockfiles. The PDS plugin retains the ban on
raw interactive PDS elements. Other lint rules use Biome's recommended preset.

Formatting imports [EditorConfig](../../.editorconfig). `lineWidth: 120` is also explicit because
Biome 2.5.11 did not reliably inherit that value in this checkout; 120 is a wrapping target, not
a hard limit for unsplittable strings. VS Code selects Biome for supported owned languages while
format-on-save remains off. CI runs the complete `npm run lint:biome:ci` scope, including on
configuration-only changes and manual dispatch. Package scripts anchor Biome at the repository
root regardless of the caller's working directory.

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
workspaces only build the bundle ([Delivery Packaging](#delivery-packaging)) and do not run this
developer-only procedure.

Run the Chromium compatibility smoke gate used by pull requests:

```shell
cd /path/to/owlbear/serve/cockpit/web
npx playwright install chromium
npm run test:e2e:compat
```

The compatibility gate uses a separate Playwright configuration and runs only the shell and PDS
smoke scenarios against the Playwright-pinned Chromium engine. Pull-request CI and manual dispatch
both install and test Chromium only. Chrome and Edge are the supported browser families; consumers
do not run these developer-only tests.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |

Cockpit always reads memory and ideas from the current workspace and serves the package's bundled
`dist/` directory.

## Delivery Packaging

- `main` carries the frontend source (`serve/cockpit/web/`) and no built bundle. After cloning or
  updating OwlBear, build it once with Node 24.21.0 or later:
  `npm ci --prefix serve/cockpit/web && npm run build --prefix serve/cockpit/web`.
- Consumers then launch Cockpit from their project root with `uv run --project ../owlbear cockpit`.

## Dependencies

| Package | Purpose |
| --- | --- |
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `owlbear-memory` | Memory engine (workspace package) |
