# Python And Cockpit Dependency Audit

> **Owning task:** User request - dependency bloat audit
> **Date:** 2026-08-19
> **Question:** Which declared Python/uv and TypeScript/Cockpit dependencies have active consumers, and which can be removed or replaced without changing supported behavior?

## 1. Context and Question

This audit treats a declared dependency as a candidate for removal only when source, configuration,
tests, and launch paths provide no active consumer. A dependency that is imported directly, required
by a supported test or build command, or supplies an optional runtime feature is retained even when a
smaller implementation is imaginable.

The audit covers all checked-in Python manifests under `serve/`, the root Python development group,
the Cockpit web manifest and lockfile, the root npm wrapper, and the diagram-exporter npm package.
The lockfiles are evidence for resolved and transitive weight, not a substitute for direct source
usage.

## 2. Sources Studied

| Source | Evidence used |
| --- | --- |
| [`pyproject.toml`](../../pyproject.toml) | Python workspace, development dependencies, test and lint commands |
| [`serve/*/pyproject.toml`](../../serve) | Runtime and optional dependency declarations for all 11 Python workspace packages |
| [`serve/cockpit/web/package.json`](../../serve/cockpit/web/package.json) | Cockpit runtime, build, lint, test, and E2E declarations |
| [`package.json`](../../package.json) and [export-diagrams/package.json](../../.owlbear/scripts/export-diagrams/package.json) | Root wrapper and separate diagram-exporter declarations |
| Python source under [`serve/`](../../serve) | Direct imports and runtime construction paths |
| Cockpit source under [`serve/cockpit/web/`](../../serve/cockpit/web) | TypeScript imports, Vite configuration, tests, E2E specs, and scripts |
| [`uv.lock`](../../uv.lock), [`serve/cockpit/web/package-lock.json`](../../serve/cockpit/web/package-lock.json) | Resolved package counts and transitive effects of removals |

## 3. Python Dependency Matrix

### Root development group

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `pre-commit` | Hook installation and quality commands in `serve/tools/src/owlbear_tools/project.py` and `quality.py` | Keep. Development-only and actively invoked. |
| `pytest` | Root and package test suites, `conftest.py`, and `serve/tools/src/owlbear_tools/testing.py` | Keep. |
| `pytest-asyncio` | Strict asyncio mode in `pyproject.toml` and async tests across the repository | Keep. |
| `pytest-cov` | `--coverage` support in `serve/tools/src/owlbear_tools/testing.py` | Keep. |
| `pytest-timeout` | `timeout` and `session_timeout` settings in `pyproject.toml` | Keep. |
| `pytest-xdist` | `-n auto` and `--dist loadfile` in the maintained test command | Keep. |
| `pyyaml` | Root validation scripts and repository tests parse YAML configuration and fixtures | Keep for the current test/tooling surface. See YAML consolidation below. |
| `ruff` | Root lint and format configuration in `pyproject.toml` and quality commands | Keep. |
| `ruamel.yaml` | `.owlbear/scripts/skills_ref/parser.py` uses round-trip YAML parsing | Keep. Development-only and separately justified from runtime safe-load paths. |

### Runtime packages

| Package | Direct dependencies | Evidence and decision |
| --- | --- | --- |
| [`owlbear-browser`](../../serve/browser/pyproject.toml) | `lxml`, `playwright`, `trafilatura` | Keep all. `lxml` owns DOM parsing and mutation in `cleaner.py`; `trafilatura` owns main-content extraction; Python Playwright owns authenticated browser acquisition. A standard-library HTML parser would be a behavior-changing rewrite. |
| [`owlbear-browser-mcp`](../../serve/browser-mcp/pyproject.toml) | `mcp`, `owlbear-browser` | Keep. `server.py` imports the MCP server API and the browser package; the server is launched with `python -m`, so the MCP CLI extra was removed. |
| [`owlbear-cockpit`](../../serve/cockpit/pyproject.toml) | `owlbear-delivery`, `owlbear-delivery-github`, `owlbear-memory`, `fastapi`, `uvicorn`, `pydantic` | Keep all. Routes, dependency wiring, Pydantic response models, and the Uvicorn entry point directly consume them. |
| [`owlbear-delivery`](../../serve/delivery/pyproject.toml) | `pydantic`, `ruamel.yaml`, `pyyaml`, `markdown-it-py` | Keep all for now. Pydantic validates the contract; `ruamel.yaml` handles canonical/round-trip YAML; PyYAML handles transaction manifests; `markdown-it-py` tokenizes fenced `yaml target-contract` blocks. Replacing the Markdown parser with a scanner would weaken malformed-input behavior. |
| [`owlbear-delivery-github`](../../serve/delivery-github/pyproject.toml) | `owlbear-delivery`, `pydantic` | Keep. GitHub publication and provider models import both directly. |
| [`owlbear-delivery-mcp`](../../serve/delivery-mcp/pyproject.toml) | `mcp`, `owlbear-delivery`, `owlbear-delivery-github`, `pydantic` | Keep. MCP adapters and target models use each dependency directly; the CLI extra was removed. |
| [`owlbear-knowledge`](../../serve/knowledge/pyproject.toml) | `pydantic` | Keep. Protocols, stores, and embedding models use Pydantic. The previously declared base `ruamel.yaml` dependency had no source consumer and was removed. |
| `owlbear-knowledge` optional `qdrant` | `qdrant-client` | Keep optional. `QdrantVectorStore` uses the client for persistent, remote, and in-memory vector collections. |
| `owlbear-knowledge` optional `embedding` | `FlagEmbedding` | Keep optional. `BgeM3EmbeddingProvider` lazy-loads `BGEM3FlagModel`; the Knowledge MCP server constructs it for vector search. |
| `owlbear-knowledge` optional `intake` | `httpx` | Keep optional. `HttpxContentFetcher` owns async URL intake. |
| `owlbear-knowledge` optional `full` | `qdrant-client`, `FlagEmbedding`, `httpx` | Keep as the combination of supported active extras. The unused `openai` entry and dead `llm` extra were removed. |
| [`owlbear-knowledge-mcp`](../../serve/knowledge-mcp/pyproject.toml) | `mcp`, `owlbear-knowledge[full]` | Keep. The server constructs Qdrant and BGE-M3 services and uses HTTP intake. It also imports Pydantic `ValidationError`; that direct import is currently supplied transitively and should be declared explicitly if package isolation is required. |
| [`owlbear-memory`](../../serve/memory/pyproject.toml) | `pydantic`, `ruamel.yaml` | Keep. Pydantic models and ruamel safe frontmatter parsing are runtime paths. |
| [`owlbear-memory-mcp`](../../serve/memory-mcp/pyproject.toml) | `mcp`, `owlbear-memory`, `pydantic`, `pyyaml` | Keep for now. MCP tools, memory models, and the Git/engine frontmatter paths import these directly. The PyYAML/ruamel overlap is a consolidation candidate, not a no-use dependency. |
| [`owlbear-tools`](../../serve/tools/pyproject.toml) | `owlbear-delivery`, `pyyaml`, `tree-sitter-language-pack` | Keep. Delivery migration/configuration commands, YAML quality tooling, and the TypeScript/JavaScript structural index use them. |

### MCP extra decision

All four MCP packages are launched through `python -m owlbear_*_mcp` and import `mcp.server`
directly. No source or documentation invokes the optional MCP CLI. Their declarations and package
README tables now use `mcp>=2,<2.1` instead of `mcp[cli]>=2,<2.1`. The lock resolution dropped
`python-dotenv`; focused MCP regressions still pass.

### YAML consolidation decision

PyYAML and `ruamel.yaml` are both active. PyYAML is used for simple safe-load/dump paths in delivery
transactions, memory-MCP frontmatter, quality tooling, and tests. `ruamel.yaml` is used for
round-trip output, resolver control, and memory/delivery canonical YAML. A full consolidation could
remove one distribution, but it would require changing multiple runtime packages and their malformed
YAML tests. It is deferred until a dedicated parser-compatibility change can compare output and
diagnostic behavior.

## 4. Cockpit And Node Dependency Matrix

### Cockpit runtime dependencies

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `@porsche-design-system/components-js` | `src/main.tsx`, `vite.config.ts`, and `scripts/sync-pds-assets.mjs` | Keep. It loads the PDS runtime and asset contract. |
| `@porsche-design-system/components-react` | Application components, CSS setup, tests, and `vitest.setup.ts` | Keep. It is the UI component system. |
| `react` | Hooks, JSX, and components throughout `src/` | Keep. |
| `react-dom` | `createRoot` in `src/main.tsx` and portal components | Keep. |
| `react-markdown` | `src/components/MarkdownPreview.tsx` | Keep. |
| `react-router` | App routing, navigation, blockers, and route tests | Keep. |
| `rehype-sanitize` | Markdown preview defaults and Memory tab rendering | Keep. Security boundary; do not replace with an ad hoc sanitizer. |
| `remark-gfm` | Markdown preview GFM plugin | Keep. It supplies tables, task lists, and other GFM syntax. |
| `@tanstack/react-virtual` | No active source, test, or config import | Removed. |
| `motion` | No active source, test, or config import | Removed. |

### Cockpit development, build, and test dependencies

| Dependency | Evidence | Decision |
| --- | --- | --- |
| `@axe-core/playwright` | Accessibility assertions in E2E specs | Keep. |
| `@eslint/js` | `eslint.config.js` | Keep. |
| `@eslint/json` | Root `eslint-json.config.cjs` loads it through the Cockpit package boundary | Keep. |
| `@playwright/test` | E2E specs, config, and browser check script | Keep. |
| `@rolldown/plugin-babel` | `vite.config.ts` React Compiler Babel plugin | Keep. |
| `@tailwindcss/vite` | Tailwind Vite plugin in `vite.config.ts` | Keep. |
| `@testing-library/jest-dom` | `vitest.setup.ts` | Keep. |
| `@testing-library/react` | React component and hook tests | Keep. |
| `@types/node` | Node APIs in Vite, Playwright, and package scripts | Keep. |
| `@types/react` | JSX and React type declarations | Keep. |
| `@types/react-dom` | React DOM type declarations | Keep. |
| `@vitejs/plugin-react` | React Vite plugin and compiler preset | Keep. |
| `@vitest/coverage-v8` | Supported `test --coverage` path in `serve/tools/src/owlbear_tools/testing.py` | Keep in Cockpit. The unused root copy was removed. |
| `babel-plugin-react-compiler` | React compiler preset in `vite.config.ts` | Keep. |
| `cross-env` | Cross-platform `NODE_OPTIONS` and E2E environment scripts | Keep unless platform support is intentionally narrowed. |
| `eslint` | Cockpit code lint command | Keep. |
| `htmlhint` | `lint:html` script | Keep. |
| `lightningcss` | Direct `Features.LightDark` import and CSS transformer in `vite.config.ts` | Keep as an explicit build dependency; it was previously resolved only transitively. |
| `jsdom` | Vitest environment in `vite.config.ts` | Keep. |
| `stylelint` | `lint:css` script | Keep. |
| `tailwindcss` | `src/tailwind.css` and the Vite plugin | Keep. |
| `typescript` | Build and type-check commands | Keep. |
| `typescript-eslint` | `eslint.config.js` | Keep. |
| `vite` | Build, preview, and Vitest configuration | Keep. |
| `vitest` | Unit test runner and configuration | Keep. |

`lightningcss` is now an explicit build dependency because `vite.config.ts` imports its feature
enum directly. Removing the custom transformer would need a CSS-output comparison, especially for
the `light-dark()` token in `src/custom-tokens.css`; it is not a safe dependency-only cut.

### Other npm package roots

| Package root | Dependency | Evidence and decision |
| --- | --- | --- |
| Root [`package.json`](../../package.json) | None after cleanup | The root only forwards commands to Cockpit; its orphaned `@vitest/coverage-v8` declaration was removed. |
| [`export-diagrams`](../../.owlbear/scripts/export-diagrams/package.json) | `playwright` | Keep. `export.mjs` imports `chromium` to render diagram exports. This is a separate npm root, not a duplicate Cockpit runtime dependency. |

## 5. Lockfile And Weight Observations

- The Python lock resolved 170 packages at the start of the audit, 166 after removing the unused
  Knowledge declarations, and 165 after removing the MCP CLI extra. The MCP change removed
  `python-dotenv` from the resolution.
- The Cockpit lockfile contained direct entries for `@tanstack/react-virtual` and `motion`; it was
  regenerated after their removal and now contains 536 packages. The installed dependency tree was
  pruned so those packages are no longer present.
- Python Playwright and npm Playwright serve different package roots and runtimes. Their similar
  names do not represent one safely mergeable dependency.
- `FlagEmbedding` is the largest intentional optional weight because BGE-M3 is the configured local
  embedding implementation. Removing it would require a different embedding provider or a server
  mode without vector search.
- `mcp[cli]` pulled CLI-only transitive support into servers that never call the CLI. This was the
  clearest Python transitive reduction.

## 6. Completed Changes And Proof

The following reductions are complete:

1. Removed unused Cockpit runtime declarations `@tanstack/react-virtual` and `motion`.
2. Removed the unused root npm `@vitest/coverage-v8` declaration while retaining Cockpit coverage.
3. Removed unused Knowledge base `ruamel.yaml`, the dead `llm` extra, and `openai` from `full`.
4. Replaced `mcp[cli]` with `mcp` in all four module-launched MCP packages.
5. Declared Cockpit's directly imported `lightningcss` build dependency explicitly.
6. Regenerated `uv.lock`, the Cockpit `package-lock.json`, and the root `package-lock.json`.

Focused proof completed during the audit:

- Cockpit: 23 test files, 269 tests passed; production build passed.
- Combined Knowledge, browser, delivery, memory, and MCP regressions: 260 tests passed.
- `uv lock --check` passed after the Python changes.
- `git diff --check` passed.

## 7. Recommendation, Confidence, And Limits

The current direct dependency set is mostly justified by active behavior. The high-confidence dead
declarations have been removed. The next worthwhile reduction is a separately scoped YAML parser
consolidation, but it should compare serialized bytes, malformed-input diagnostics, and frontmatter
compatibility before changing runtime packages. The Lightning CSS direct-import mismatch should be
resolved as manifest hygiene, not treated as a speculative removal.

Confidence is high for the removals above because each was supported by exact source/configuration
absence and focused executable proof. Confidence is medium for future consolidation because external
consumers may rely on package extras or YAML edge behavior not represented by this repository's
tests. This audit does not claim that every transitive package in the lockfiles is independently
removable; transitive packages are owned by the direct dependency that requires them.