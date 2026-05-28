# owlbear-cockpit — Steering Cockpit Package

Cockpit combines a FastAPI backend (`src/owlbear_cockpit/`) with a React frontend (`web/`),
served as built static assets from `dist/`. The backend wraps `KanbanEngine` with read and
mutation APIs, and the frontend provides the steering viewport used to view, edit, move,
archive, inspect activity, and resolve decisions.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

Build frontend assets (developer/source workflow):

```bash
cd serve/cockpit/web
npm run build
cd -
```

Sync Porsche Design System runtime assets from CDN (run once after PDS version bumps):

```bash
cd serve/cockpit/web
npm run sync:pds
cd -
```

This downloads the core chunk, 58 component chunks, and 290 icon SVGs from
`cdn.ui.porsche.com` into `public/porsche-design-system/` and commits them for offline
use. Assets are version-pinned to the installed `@porsche-design-system/components-js`
version; re-run after any PDS upgrade.

Launch Cockpit backend + static frontend:

```bash
uv run cockpit
```

`uv run cockpit` serves `serve/cockpit/dist/`, starts on `127.0.0.1:8420` by default,
and opens a browser unless disabled with `COCKPIT_NO_OPEN=1`.

## Frontend Surface

Frontend source is under `serve/cockpit/web/` and is the only Node/npm package in this
repository.

| Attribute | Value |
|-----------|-------|
| Node requirement | `>=24.15.0` (`web/package.json`) |
| Stack | React `^19.2.5`, Vite `^8.0.10`, TypeScript `^6.0.3`, React Router `^7.14.2`, Porsche Design System React `^4.0.0`, React Compiler (`babel-plugin-react-compiler` `^1.0.0`), Tailwind CSS `^4.3.0` (`@tailwindcss/vite` + `tailwindcss`) |
| Test runner | Vitest `^4.1.5` (`npm test`) |
| E2E runner | Playwright `^1.59.1` (`npm run test:e2e`) |
| CSS/HTML lint | Stylelint `^17.10.0` (`npm run lint:css`), HTMLHint `^1.9.2` (`npm run lint:html`) |
| Build output | `serve/cockpit/dist/` via `npm run build` |

## Audit Trail

Activity events use a `source` field for attribution:

| Source | Meaning |
|--------|---------|
| `source="cockpit"` | UI-initiated mutation (user action in the Cockpit frontend) |
| `source="agent"` | agent-initiated mutation (pipeline agent via MCP) |
| `source="engine"` | internal engine operation (lifecycle, migration) |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |
| `KANBAN_DIR` | `.owlbear/kanban/` | Override kanban directory path |
| `MEMORY_DIR` | `.owlbear/memory/` | Override memory directory path used by `MemoryEngine` |

## Delivery Packaging

- Developer branch (`dev`): frontend source (`serve/cockpit/web/`) is present and used for
  build/test/lint workflows.
- Consumer branch (`main`): sync-to-main builds and stages prebuilt
  `serve/cockpit/dist/` artifacts; consumers launch Cockpit without Node/npm.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `sse-starlette` | SSE streaming for the `GET /api/events` invalidation endpoint |
| `watchfiles` | File-system watcher used by the events endpoint |
| `owlbear-kanban` | Kanban engine (workspace package) |
| `owlbear-memory` | Memory engine (workspace package) |
| `ruamel.yaml` | Round-trip YAML parsing for the Decisions API |
