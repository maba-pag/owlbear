# Tests

The top-level `tests/` tree verifies workspace-wide contracts: setup and seed behavior, package
boundaries, MCP registrations, Delivery transitions, memory and knowledge persistence, hooks, and
sync behavior. It is development evidence, not a runtime package.

## What lives here

- `test_*.py` contains cross-package and repository-contract regressions.
- `fixtures/delivery-authority/` contains inert compliant and non-compliant code samples that
  workspace governance checks must accept or reject.
- `benchmarks/` is reserved for benchmark support; it currently contains only package scaffolding.

Package-specific tests stay beside the implementation under `serve/*/tests/`. Cockpit frontend
tests live under `serve/cockpit/web/`. Those package-local tests follow their package's toolchain;
this directory does not replace them.

## Run the suite

From the repository root:

```shell
# Full maintained Python and frontend test routing
uv run test --all

# One narrow Python regression
uv run pytest tests/test_sync_manifest.py -q
```

A focused run should report the selected tests and a zero exit status. If collection or imports
fail, run the locked workspace setup from the [development README](../README.md) before treating a
behavioral failure as a product defect.

## What is not here

The top-level suite is not listed in the sync manifest and is therefore absent from consumer
`main`. Runtime source belongs under `serve/`, portable agent assets belong under `share/`, and
consumer-project templates belong under `seed/`.
