---
name: h-quality-runner
description: "Handbook: Quality-Runner subagent — consumer invocation pattern, I/O contract, and fallback"
user-invocable: false
---

# Quality-Runner Subagent

Consumer reference for invoking the `quality-runner` utility subagent. Quality-Runner runs pytest, ruff, and coverage (Python) or vitest, eslint, and coverage (TypeScript/JavaScript), returning a structured report. It is a mechanical utility agent — it does not edit files, interact with kanban, or make judgments.

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
  Run: mode=scoped, task_id=1230, test_paths=["frontend/src/__tests__/MyComponent.test.tsx"], lint_paths=["frontend/src/components/MyComponent.tsx"]
# adjust test_paths and lint_paths for your project layout
```

Full suite:

```
agentName: quality-runner
prompt: |
  Run: mode=full, task_id=263
```

Quality-runner selects the toolchain and execution cwd by resolving the nearest package manifest from each test path:

1. Walk up from the test file's directory toward the workspace root.
2. If you encounter `package.json` containing a `test` script or vitest dependency, that directory is the **frontend cwd** — use vitest + eslint (see `h-vitest-and-linting`).
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
| `mode` | `scoped` \| `full` | Yes | `scoped` runs only `test_paths`; `full` runs the project full-suite default (`tests/ serve/ -m "not api"` in OwlBear) |
| `test_paths` | string[] | If `mode=scoped` | Paths to test files, e.g. `["tests/test_foo.py", "tests/test_bar.py"]` |
| `task_id` | string | Yes | Kanban task ID, or a stable run label for suite-scoped workflows — isolates file-capture fallback output in `.owlbear/scratch/` |
| `coverage_modules` | string[] | No | Module names for focused coverage display; bare `--cov` always runs against all packages |
| `lint_paths` | string[] | No | Paths to lint; defaults to your source package paths plus `tests/` (Python) or `src/` (frontend) if omitted |

**Frontend detection:** When any `test_paths` entry resolves to a directory containing `package.json` with vitest (via the manifest-walk above), switch to frontend mode (vitest + eslint). See `h-vitest-and-linting`.
> Example (OwlBear-dev): `serve/cockpit/web/src/__tests__/MyComponent.test.tsx` → cwd `serve/cockpit/web/`

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
