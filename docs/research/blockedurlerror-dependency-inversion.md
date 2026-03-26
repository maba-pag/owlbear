# BlockedURLError Dependency Inversion

> **Owning task:** #850 — Invert BlockedURLError dependency to remove core-tools circular import
> **Date:** 2026-03-19  **Status:** Complete

## 1. Context and Question

Task #850 asks whether `BlockedURLError` should move out of `tools/browser/safety.py`
to remove the `core -> tools` import in `src/owlbear/core/errors.py`.

The parent research in `docs/research/core-tools-circular-import.md` already
recommended that direction. This pass resolved one new contradiction in the
current checkout: `import owlbear.daemon` still fails in a clean process, but
`import owlbear.config; import owlbear.daemon` succeeds.

Questions:

1. Does the circular import still exist?
2. What is the narrowest fix that keeps compatibility?
3. Is the broader `tools/__init__.py` behavior part of #850 or a separate task?

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/core/errors.py`, `src/owlbear/tools/browser/safety.py` | Local | 1.0 | `core.errors` still imports `BlockedURLError` from the tools package |
| `src/owlbear/tools/__init__.py`, `src/owlbear/tools/github_api.py`, `src/owlbear/core/retry.py` | Local | 1.0 | Importing `owlbear.tools.browser.safety` still triggers the parent-package cycle through `GitHubToolset` |
| `src/owlbear/config.py` and `src/owlbear/tools/browser/config.py` | Local | .95 | `owlbear.config` preloads the parent `owlbear.tools` package through `BrowserConfig`, masking the later daemon import failure |
| Task #539 final notes | Local | .95 | `core.exceptions.py` is the intended leaf module for OwlBear root exceptions |
| Task #814 archived notes | Local | .90 | The prior “no circular import risk” conclusion only checked direct `from owlbear.tools import ...` consumers and missed parent-package import side effects |
| PEP 8 — Public and Internal Interfaces | External | .85 | Package `__init__` exports are a deliberate API decision, not free indirection |
| Google Python Style Guide §2.2 Imports and §2.4 Exceptions | External | .85 | Favors explicit imports and dedicated exception classes over import-time magic |
| `requests.exceptions` | External | .80 | Mature library precedent for central exception definitions in a dedicated module |
| `httpx/_exceptions.py` | External | .80 | Same dedicated-exception-module pattern in a second Python HTTP library |

## 3. Analysis

### 3.1 Current import behavior

| Command | Result | Meaning |
|---------|--------|---------|
| `python -c "import owlbear.daemon"` | FAIL | Direct import still hits `core.errors -> tools.browser.safety -> tools.__init__ -> github_api -> core.retry -> core.errors` |
| `python -c "import owlbear.core.errors"` | FAIL | Same circular import reproduces on the narrowest direct path |
| `python -c "import owlbear.config; import owlbear.daemon"` | PASS | `owlbear.config` imports `owlbear.tools.browser.config`; importing a submodule loads the parent `owlbear.tools` package first, so the later daemon import is masked |

Conclusion: the bug is real, but it is now order-dependent. #850 is still valid.

### 3.2 Option comparison

| Option | Change | Pros | Cons | Verdict |
|--------|--------|------|------|---------|
| A. Move `BlockedURLError` to `core.exceptions.py`, re-export from `browser.safety` | Narrow dependency inversion | Removes the forbidden `core -> tools` edge; preserves `from owlbear.tools.browser.safety import BlockedURLError`; matches #539 and the Requests/HTTPX exception-module pattern | Leaves broader `tools/__init__` side effects for separate cleanup | Best fit (.93) |
| B. Keep `BlockedURLError` in `browser.safety`, change `tools/__init__.py` behavior | Broader package import fix | Addresses the masking path and #814 side effects | Does not remove the current `core.errors -> tools` dependency by itself; wider blast radius | Follow-up, not #850 (.63) |
| C. Do A and B together | Comprehensive | Fixes both layers at once | Mixes two independently useful changes; harder to review and test | Reject for #850 (.35) |

### 3.3 Architecture fit

- `core.exceptions.py` is the correct new home. Final #539 notes treat it as a
  leaf module with zero `owlbear` imports.
- `classify_error()` should continue treating `BlockedURLError` as
  `ErrorCategory.PERMANENT`.
- `tests/test_daemon_journal_async.py` should drop the `import owlbear.tools`
  pre-seeding workaround. The regression test must exercise a clean subprocess
  direct import of `owlbear.daemon`.
- The eager `tools/__init__.py` re-exports introduced by #814 are a separate
  package-API concern. PEP 8 makes that public-surface decision explicit, so it
  should not be changed incidentally inside #850.

## 4. Recommendation (.93 confidence)

Proceed with #850 as a narrow dependency-inversion task:

1. Define `BlockedURLError` in `src/owlbear/core/exceptions.py`.
2. Import and re-export it from `src/owlbear/tools/browser/safety.py`.
3. Update `src/owlbear/core/errors.py` to import from `owlbear.core.exceptions`.
4. Replace workaround-based import coverage with a clean subprocess smoke test
   for direct `import owlbear.daemon`.
5. Keep `tools/__init__.py` side-effect cleanup separate.

## 5. Follow-up Tasks

Executed during this research pass:

- `kanban\kanban-md.exe create "Reduce owlbear.tools __init__ eager import side effects" --status ideation --priority important --tags architecture,bug,scope:tools --parent 850`
  - Result: created task #857.
