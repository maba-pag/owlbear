---
name: h-quality-runner
description: "Handbook: Quality-Runner subagent — consumer invocation pattern, I/O contract, and fallback"
user-invocable: false
---

# Quality-Runner Subagent

Consumer reference for invoking the `quality-runner` utility subagent. Quality-Runner runs pytest, ruff, and coverage (Python) or frontend quality commands from the nearest package root, returning a structured report. The default frontend path is vitest + eslint; build, CSS/HTML lint, and Playwright run only when AC, Architecture Review notes, or caller instructions explicitly require them. It is a mechanical utility agent — it does not edit files, interact with kanban, or make judgments.

## Consumer Invocation Pattern

Invoke via `runSubagent` with a structured prompt:

Scoped (Python):

```
agentName: quality-runner
prompt: |
  Run: mode=scoped, task_id=263, test_paths=["tests/test_my_module.py"], coverage_modules=["my_module"], lint_paths=["src/", "tests/test_my_module.py"]
# adjust lint_paths for your project layout
```

Scoped (TypeScript/JavaScript):

```
agentName: quality-runner
prompt: |
  Run: mode=scoped, task_id=1230, test_paths=["serve/cockpit/web/src/__tests__/MyComponent.test.tsx"], lint_paths=["serve/cockpit/web/src/components/MyComponent.tsx"]
# for other projects, substitute the equivalent frontend package paths
```

Scoped with explicit frontend proof:

```
agentName: quality-runner
prompt: |
  Run: mode=scoped, task_id=1392, test_paths=["serve/cockpit/web/e2e/responsive-layout-1391.spec.ts"], lint_paths=["serve/cockpit/web/src/Shell.css"]
  Also run the Cockpit frontend build, Playwright E2E, and CSS lint because the AC names viewport/layout proof and CSS validity.
```

Full suite:

```
agentName: quality-runner
prompt: |
  Run: mode=full, task_id=263
```

Full suite with domain scoping:

```
agentName: quality-runner
prompt: |
  Run: mode=full, task_id=263, changed_paths=["serve/cockpit/web/src/components/Foo.tsx", "serve/kanban/src/owlbear_kanban/engine.py"]
```

Quality-runner selects the toolchain and execution cwd by resolving the nearest package manifest from each test path:

1. Walk up from the test file's directory toward the workspace root.
2. If you encounter `package.json` containing a `test` script or vitest dependency, that directory is the **frontend cwd**. Use vitest + eslint by default; use build, CSS/HTML lint, or Playwright only when explicitly required (see `h-vitest-and-linting`).
3. Otherwise, use pytest + ruff from the workspace root (see `h-pytest-and-linting`).

> Example (OwlBear-dev): `serve/cockpit/web/src/__tests__/Foo.test.tsx` → walk up → `serve/cockpit/web/package.json` found → cwd is `serve/cockpit/web/`, toolchain is vitest.

If your project has `.owlbear/scripts/test-root.py` (seeded by `setup/init.py`), you can resolve this programmatically:

```bash
uv run .owlbear/scripts/test-root.py serve/cockpit/web/src/__tests__/Foo.test.tsx
# → {"test_path": "...", "cwd": "serve/cockpit/web", "toolchain": "vitest", "cmd": "npm test"}
```

The project's `.github/copilot-instructions.md` is the authoritative source for package roots and toolchain conventions. If the manifest-walk result conflicts with what's documented there, follow `copilot-instructions.md`.

**Prerequisite:** The calling agent must list `quality-runner` in its frontmatter `agents:` array. Without this, `disable-model-invocation: true` blocks the call.

```yaml
# In the calling agent's frontmatter:
agents: [quality-runner]
```

## Input Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | `scoped` \| `full` | Yes | `scoped` runs only `test_paths`; `full` runs the project full-suite default. When `changed_paths` is provided with `mode=full`, resolve affected test domains from the project's `.github/copilot-instructions.md` domain mapping and run ALL tests for those domains. When `changed_paths` is omitted, fall back to the project default (e.g. `tests/ serve/ -m "not api"` in OwlBear) |
| `test_paths` | string[] | If `mode=scoped` | Paths to test files, e.g. `["tests/test_foo.py", "tests/test_bar.py"]` |
| `task_id` | string | Yes | Kanban task ID, or a stable run label for suite-scoped workflows — isolates file-capture fallback output in `.owlbear/scratch/` |
| `changed_paths` | string[] | No | Source files changed by the task. For `mode=full`: resolve each path against the domain mapping in `.github/copilot-instructions.md`, then run ALL tests for every matched domain. Multiple domains are supported (e.g. both vitest and pytest). Ignored for `mode=scoped` |
| `coverage_modules` | string[] | No | Module names for focused coverage display; bare `--cov` always runs against all packages |
| `lint_paths` | string[] | No | Paths to lint; defaults to your source package paths plus `tests/` (Python) or `src/` (frontend) if omitted |

**Frontend detection:** When any `test_paths` entry resolves to a directory containing `package.json` with vitest (via the manifest-walk above), switch to frontend mode. Default to vitest + eslint; add build, CSS/HTML lint, or Playwright only when the caller explicitly asks or the task evidence requires it. See `h-vitest-and-linting`.
> Example (OwlBear-dev): `serve/cockpit/web/src/__tests__/MyComponent.test.tsx` → cwd `serve/cockpit/web/`

### Frontend Optional Proof Types

Use these only when named by AC, Architecture Review, Test-Writer Notes, Builder/Reviewer request, or caller instructions:

| Proof type | Cockpit command | When required |
|------------|-----------------|---------------|
| Build | `npm run build` | TypeScript/Vite/build-output proof, Playwright startup failures, or explicit build AC |
| CSS lint | `npm run lint:css` | CSS files changed, stylelint proof requested, or CSS validity AC |
| HTML lint | `npm run lint:html` | `index.html` changed or HTML validity AC |
| Playwright | `npm run test:e2e` | E2E/browser geometry, viewport, focus-trap, or layout proof |

Do not run optional frontend proof types merely because the project is frontend. Extra commands increase runtime and noise; the caller owns proof scope.

## Output Format

Quality-Runner returns exactly 5 sections. Parse all 5 before taking action.

```
## Tests
passed: 42
failed: [{name: "test_foo::TestBar::test_baz", error: "AssertionError: expected 1 got 0"}]
skipped: 2

## Lint
clean: false
violations: [{file: "src/foo/bar.py", line: 12, code: "F401", msg: "'os' imported but unused"}]

## Coverage
overall_pct: 94
modules: [{name: "foo.bar", pct: 87}, {name: "foo.baz", pct: 100}]

## Exit Codes
pytest: 1
ruff: 1

## Errors
none
```

**Exit code interpretation (Python):**

| pytest exit | Meaning |
|-------------|---------|
| 0 | All tests passed |
| 1 | Tests failed |
| 2 | Interrupted |
| 3 | Internal error |
| 4 | Command-line usage error |
| 5 | No tests collected |

**Exit code interpretation (Frontend):**

| Tool | Code | Meaning |
|------|------|---------|
| vitest | 0 | All tests passed |
| vitest | 1 | Tests failed |
| eslint | 0 | No violations |
| eslint | 1 | Violations found |
| eslint | 2 | Fatal/config error |
| build | 0 | Build passed |
| build | nonzero | Build failed |
| stylelint | 0 | CSS lint clean |
| stylelint | nonzero | CSS lint failed |
| htmlhint | 0 | HTML lint clean |
| htmlhint | nonzero | HTML lint failed |
| playwright | 0 | E2E passed |
| playwright | nonzero | E2E failed or webServer/build failed |

When optional frontend commands run, include their exit codes in the `Exit Codes` section using the keys above. Report command failures under `Tests`, `Lint`, or `Errors` depending on which section best matches the command output; do not add a sixth output section.
