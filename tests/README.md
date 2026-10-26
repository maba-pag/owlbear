# Tests

The top-level `tests/` tree verifies workspace-wide contracts: package
boundaries, MCP registrations, memory and knowledge persistence, CI workflows, and the agent
ecosystem. It is development evidence, not a runtime package.

## What lives here

- `test_*.py` contains cross-package and repository-contract regressions.
- `benchmarks/` is reserved for benchmark support; it currently contains only package scaffolding.

Package-specific tests stay beside the implementation under `serve/*/tests/`, including the
Delivery engine's under `serve/delivery-next/tests/`. Those package-local tests follow their
package's toolchain; this directory
does not replace them.

## Run the suite

From the repository root:

```shell
# Full maintained Python and frontend test routing
uv run test --all

# Tests affected by your changes, with their direct consumers
uv run test --changed

# One narrow Python regression
uv run pytest tests/test_ci_workflows.py -q
```

A focused run should report the selected tests and a zero exit status. If collection or imports
fail, run the locked workspace setup from the [development README](../README.md) before treating a
behavioral failure as a product defect.

## What is not here

Runtime source belongs under `serve/` and portable agent assets belong under `share/`.
