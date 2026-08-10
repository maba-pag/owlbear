---
name: h-vitest-and-linting
description: "Handbook: Vitest, Playwright, frontend linting, build proof, and coverage commands"
user-invocable: false
---

# Frontend Test, Lint, and Coverage Reference

Use the target project's package manager, scripts, and test configuration. Do not assume a package
root, framework, browser, or script name.

## Discover the Owning Package

1. Start from the changed source or test file. When available, OwlBear's supplied helper can suggest
   the working directory and toolchain:

   ```shell
   uv run --project {owlbear-root} test-root {test-or-source-path}
   ```

2. Verify the result against the nearest `package.json`, workspace manifest, lockfile, and Vitest,
   Vite, Playwright, ESLint, Stylelint, or framework configuration.
3. Read package scripts before constructing commands. Prefer maintained scripts over direct binary
   invocation because scripts may provide environment variables, setup files, reporters, or gates.
4. Use a repository-root proxy script when it intentionally delegates to the owning package.
   Otherwise run from the package root when configuration resolution depends on the current working
   directory.

Use these placeholders:

| Placeholder | Meaning |
|-------------|---------|
| `{package-root}` | Directory owning the relevant frontend manifest and configuration |
| `{package-runner}` | Package manager command: `npm`, `pnpm`, `yarn`, or `bun` |
| `{test-script}` | Discovered unit/component test script |
| `{e2e-script}` | Discovered browser/E2E script |
| `{lint-script}` | Discovered lint script for the affected file type |
| `{build-script}` | Discovered typecheck/build script |

## Select Proof by Claim

| Claim | Primary proof |
|-------|---------------|
| Pure logic, state transition, serialization, hook, or supported component interaction | Vitest or the configured unit/component runner |
| Type safety, bundling, imports, generated assets, or static validity | Typecheck, build, or relevant linter |
| Browser API, assembled workflow, focus behavior, geometry, viewport behavior, or screenshot | Playwright or configured real-browser runner |
| CSS/HTML syntax or project style policy | Stylelint, HTML linter, or configured framework lint |

Do not use jsdom to prove layout geometry, clipping, overlap, element reachability, real focus
trapping, or viewport behavior. Do not run browser E2E when a smaller test exercises the same public
contract with equivalent confidence.

## Command Templates

Run from `{package-root}` unless a verified root proxy script is used.

### Unit or component tests

Scoped:

```shell
{package-runner} run {test-script} -- {test-file-or-filter}
```

Full configured suite:

```shell
{package-runner} run {test-script}
```

When invoking Vitest directly for one-shot proof, use `vitest run`; bare `vitest` enters watch mode.
Prefer the package script when it already includes `run` and required environment setup.

### Lint and build

```shell
{package-runner} run {lint-script}
{package-runner} run {build-script}
```

Pass affected files only when the script supports positional filters. Run CSS or HTML lint when those
file types changed or the claimed behavior depends on their validity; JavaScript lint does not
validate CSS or HTML.

### Browser/E2E

```shell
{package-runner} run {e2e-script} -- {spec-or-filter}
```

Run the configured fast gate by default. Run every browser spec only when the task, risk, or explicit
request justifies it. If Playwright fails before assertions execute, inspect web-server, typecheck,
and build output before attributing the failure to the spec.

Browser binaries may require one-time installation. Use the browser set declared by Playwright
configuration rather than assuming Chromium.

### Coverage

```shell
{package-runner} run {test-script} -- --coverage
```

Use the configured provider and thresholds. Coverage identifies unexamined paths; it does not justify
tests for generated branches, DOM shape, component internals, or compiler output.

## Durable Frontend Test Admission

A committed test must pass the pipeline Rent Test and protect observable behavior, a public API or
component contract, a non-obvious state transition, a realistic failure boundary, or a previously
observed regression.

Do not commit tests that merely assert:

- removed text, files, imports, selectors, or old components are absent;
- a source file, config key, dependency, export, CSS string, or literal exists;
- a component has a particular internal DOM shape when users and callers do not depend on it;
- compiler output, generated cache branches, snapshots, or implementation details remain unchanged.

Use search, diff, lint, typecheck, build, or focused manual/browser inspection as task proof for those
claims. A structural assertion belongs in the durable suite only when it is itself a maintained
public contract and no owning validator provides cheaper proof.

Every durable test should answer: which plausible user-visible, state, or API regression makes this
fail? Exercise meaningful input and observable output. Add alternate or negative cases only when
they distinguish the contract from a common incorrect implementation.

## Cockpit/PDS Profile

Apply this profile only when the target package uses Cockpit's scripts and Porsche Design System:

- The package root is discovered from `serve/cockpit/web/package.json`; repository-root proxy scripts
  are also valid.
- In the OwlBear development checkout, `uv run test [PATH ...]` is the preferred path-aware unit-test
  entry point and `uv run test --all` includes this frontend suite.
- `npm test` supplies `NODE_OPTIONS=--max-old-space-size=2048`, `vitest run`, and `--silent=true`.
  Preserve those flags for normal runs; direct `npx vitest run` is useful when debugging console
  output.
- Vitest configuration lives in `vite.config.ts` and uses jsdom plus `vitest.setup.ts`. Running a
  direct Vitest command from the wrong directory can skip this setup and produce environment errors.
- Setup includes the PDS jsdom polyfill, Testing Library matchers, CDN-request suppression, and local
  shims for browser APIs such as `HTMLDialogElement`, `HTMLElement.attachInternals`, and `EventSource`.
- PDS custom elements may not expose native roles in jsdom. Drive their actual host contracts:
  `PSelect` commonly emits `change` with `detail.value`; `PMultiSelect` emits `update` with
  `detail.value`.
- `npm run test:e2e` is Cockpit's maintained fast gate; `npm run test:e2e:all` is the deliberate full
  sweep. `uv run test-e2e` and `uv run test-e2e --all` are the repository-level wrappers. Playwright
  currently uses Chromium and starts through the configured build/preview server.
- PDS can emit extremely large jsdom console output. Use the silent package script normally. If
  output is still truncated, capture it under `.owlbear/scratch/vitest-{task_id}.log` and inspect a
  bounded summary with `tail` or targeted `grep`; do not load the entire log into model context.

## Known Gotchas

- **Configuration resolution.** A wrong working directory can silently select the wrong environment,
  setup file, aliases, or include patterns. Verify the owning config before diagnosing test failures.
- **Build failures can mask E2E assertions.** Separate web-server and build startup failures from
  failures in the browser test body.
- **One-shot execution.** Use a maintained non-watch script or `vitest run`; do not leave a watcher
  running as proof.
- **Output volume.** Prefer normal direct command output. Use OwlBear scratch capture only when output
  is actually truncated, and inspect bounded summaries rather than entire logs.
