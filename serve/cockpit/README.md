# owlbear-cockpit — Steering Cockpit Package

Cockpit combines a FastAPI backend (`src/owlbear_cockpit/`) with a React frontend (`web/`),
served as built static assets from `dist/`. The backend binds a `NativeWorkspace` and exposes
native changes, jobs, requests, evidence, health, Memory, Ideas, and immutable legacy inventory.
The frontend provides purpose-specific delivery controls rather than arbitrary status mutation.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

Build frontend assets (developer/source workflow):

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

Launch from the owlbear development checkout:

```bash
uv run cockpit
```

Launch against a consumer project that references a sibling owlbear clone:

```bash
cd ../my-project
uv run --project ../owlbear cockpit
```

`uv run cockpit` serves `serve/cockpit/dist/`, starts on `127.0.0.1:8420` by default,
and opens a browser unless disabled with `COCKPIT_NO_OPEN=1`. Cockpit reads
`.owlbear/kanban/` and `.owlbear/memory/` relative to the process working directory, so
consumer launches must set the working directory to the target project or override
`OWLBEAR_WORK_ROOT` and `MEMORY_DIR`.

## Frontend Surface

Frontend source is under `serve/cockpit/web/` and is the only Node/npm package in this
repository.

| Attribute | Value |
|-----------|-------|
| Node requirement | `>=24.16.0` (`web/package.json`) |
| Stack | React `^19.2.7`, Vite `^8.1.5`, TypeScript `^6.0.3`, React Router `^8.2.0`, Porsche Design System React `^4.5.0`, React Compiler (`babel-plugin-react-compiler` `^1.0.0`), Tailwind CSS `^4.3.3` (`@tailwindcss/vite` + `tailwindcss`) |
| Test runner | Vitest `^4.1.10` (`npm test`) |
| E2E runner | Playwright `^1.61.1` (`npm run test:e2e`) |
| CSS/HTML lint | Stylelint `^17.12.0` (`npm run lint:css`), HTMLHint `^1.9.2` (`npm run lint:html`) |
| Build output | `serve/cockpit/dist/` via `npm run build` |

## Delivery Evidence

Cockpit projects the native evidence model without becoming authority:

| Surface | Authority |
|---------|-----------|
| Change intent, design, decisions, and delivery graph | `.owlbear/changes/<change-id>/` |
| Jobs, attempts, requests, findings, and activity | `.owlbear/kanban/` native stores |
| Successful delivery evidence | Immutable receipts in the owning change |
| Retired workflow records | Hash-verified read-only inventory under `.owlbear/legacy/` |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |
| `OWLBEAR_WORK_ROOT` | `$PWD/.owlbear/kanban/` | Override the native delivery work root |
| `MEMORY_DIR` | `$PWD/.owlbear/memory/` | Override memory directory path used by `MemoryEngine` |

## Delivery Packaging

- Developer branch (`dev`): frontend source (`serve/cockpit/web/`) is present and used for
  build/test/lint workflows.
- Consumer branch (`main`): sync-to-main builds and stages prebuilt
  `serve/cockpit/dist/` artifacts; consumers launch Cockpit from their project root with
  `uv run --project ../owlbear cockpit` and do not need Node/npm.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `sse-starlette` | SSE streaming for the `GET /api/events` invalidation endpoint |
| `watchfiles` | File-system watcher used by the events endpoint |
| `owlbear-kanban` | Native change and delivery control plane |
| `owlbear-memory` | Memory engine (workspace package) |
| `ruamel.yaml` | Canonical native authority and evidence YAML parsing |
