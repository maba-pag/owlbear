# Extract Shared Test Helpers to conftest.py

> **Owning task:** #555 — Extract shared test helpers to conftest.py
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The test suite has 1 fixture in `conftest.py` (`default_settings`). Multiple test
files independently define identical helper functions (`_run`, `_make_channel`,
`MockChannel`, `_make_mock_toolset`, `_make_settings`). Should these be extracted
to `conftest.py`, a `tests/helpers.py` module, or left as-is?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pytest docs — conftest.py | <https://docs.pytest.org/en/stable/reference/fixtures.html> | .95 |
| pytest docs — fixtures how-to | <https://docs.pytest.org/en/stable/how-to/fixtures.html> | .90 |
| OwlBear test-quality-audit.md | local: docs/test-quality-audit.md | .95 |
| pytest-asyncio docs | <https://pytest-asyncio.readthedocs.io/> | .80 |

## 3. Inventory of Duplicated Helpers

### 3a. `_run()` — asyncio.run wrapper (16 files)

| File | Return type | Variant |
|------|-------------|---------|
| test_approval_gate.py | `object` | returns result |
| test_ask_user.py | `object` | returns result |
| test_browser_safety.py | `None` | discards result |
| test_command_guard.py | `None` | discards result |
| test_context_hook.py | `None` | discards result |
| test_daemon.py | `object` | returns result |
| test_delegation.py | `object` | returns result |
| test_error_recovery.py | `Any` | returns result |
| test_error_sanitization_callsites.py | `object` | returns result |
| test_hooked_toolset.py | `object` | returns result |
| test_lint_hook.py | `None` | discards result |
| test_notification_hook.py | `object` | returns result |
| test_slack_interactive.py | `object` | returns result |
| test_subagent_hook.py | `None` | discards result |
| test_terminal_tools.py | `object` | returns result |
| test_test_hook.py | `None` | discards result |

Two variants: 10 return the result, 6 return `None`. A single `_run` returning
`Any` covers both.

### 3b. `MockChannel` class (3 files)

Identical implementation in: `test_daemon.py`, `test_error_sanitization_callsites.py`,
`test_integration_e2e.py`. All have same `__init__`, `name`, `send`, `receive`.

### 3c. `_make_channel()` factory (2 files)

`test_approval_gate.py`, `test_ask_user.py` — similar but different signatures
(MagicMock vs AsyncMock, different param names). **Not identical** — keep local.

### 3d. `_make_mock_toolset()` factory (3 files)

`test_approval_gate.py`, `test_hooked_toolset.py`, `test_slack_interactive.py` —
nearly identical (only default return value differs: `"tool_result"` vs `"mock_result"`).

### 3e. `_make_settings()` factory (3 files)

`test_bootstrap_integration.py`, `test_integration_e2e.py` — identical.
`test_pipeline_e2e.py` — different (uses `AGENTS_DIR` constant). **2 extractable.**

## 4. Analysis: conftest.py vs tests/helpers.py

| Criterion | conftest.py | tests/helpers.py |
|-----------|-------------|-----------------|
| Auto-discovery | Yes — pytest finds fixtures automatically | No — requires explicit import |
| Fixtures (teardown, scope) | Yes — full fixture protocol | No — plain functions only |
| Plain helpers (non-fixtures) | Works but unconventional | Natural fit |
| IDE discoverability | Excellent (pytest plugin support) | Good (standard import) |
| pytest best practice | Fixtures in conftest, helpers importable | Helpers that aren't fixtures go here |
| KISS | One file to check | Two files to check |

**Recommendation (.85 confidence):** Use **conftest.py only**. Rationale:

- `_run` is best as a plain function (not a fixture) but conftest can hold module-level
  functions that tests import. However, pytest convention discourages importing from
  conftest directly.
- **Better:** Make `_run` a plain function in conftest (tests won't import it — they'll
  call it directly as a module-level helper). Actually, `_run` cannot be a fixture
  because it takes a `coro` argument. Fixtures only inject via name.
- **Best approach:** Put `_run` in conftest.py as a module-level function. Tests import
  it: `from conftest import _run`. This is acceptable for test code per pytest FAQ.
  Alternatively, use a `tests/helpers.py` module for non-fixture helpers.

**Revised recommendation (.90 confidence):** Split approach:

- **conftest.py:** Fixtures — `mock_channel` (yields `MockChannel` instance),
  `make_settings` (factory fixture), `make_mock_toolset` (factory fixture)
- **conftest.py** (module-level): `_run()` function — callers do
  `from conftest import _run` or simply define tests as `async def` with
  `@pytest.mark.asyncio`.

The cleanest option for `_run` is actually eliminating it entirely by converting
those 16 test files to use `@pytest.mark.asyncio` + `async def test_*()`. This
removes the helper instead of extracting it.

## 5. Recommendation (.90 confidence)

**Phase 1 — Extract to conftest.py:**

1. Add `MockChannel` class to conftest.py (used by 3 files)
2. Add `make_mock_toolset()` factory function to conftest.py (used by 3 files)
3. Add `make_settings()` factory fixture to conftest.py (used by 2 files)
4. Remove duplicates from individual test files, import from conftest

**Phase 2 — Eliminate `_run()` via pytest-asyncio (separate task):**

Converting 16 files from `def test_x(): _run(coro())` to
`@pytest.mark.asyncio async def test_x(): await coro()` is mechanical but
touches every test in those files. Best done as a dedicated task to keep diffs
reviewable. This is the **correct** fix — `_run()` exists because tests were
written before the project adopted pytest-asyncio. Note: `asyncio_mode = "strict"`
is already configured, so `@pytest.mark.asyncio` is required per test.

**Risk:** Phase 2 is a large diff (16 files × multiple tests each). Mitigate by
doing one file per commit.

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Extract MockChannel, make_mock_toolset, make_settings to conftest.py" --priority nice-to-have --status todo --tags "test,audit" --description "Move shared test helpers to tests/conftest.py: (1) MockChannel class from test_daemon/test_error_sanitization_callsites/test_integration_e2e, (2) make_mock_toolset factory from test_approval_gate/test_hooked_toolset/test_slack_interactive, (3) make_settings factory from test_bootstrap_integration/test_integration_e2e. Remove duplicates from source files. AC: no duplicate MockChannel or make_mock_toolset definitions across test files."

kanban\kanban-md.exe create "Convert 16 test files from _run(coro) to async def + pytest.mark.asyncio" --priority nice-to-have --status todo --tags "test,audit" --description "Eliminate _run() helper by converting sync test functions to native async tests: test_approval_gate, test_ask_user, test_browser_safety, test_command_guard, test_context_hook, test_daemon, test_delegation, test_error_recovery, test_error_sanitization_callsites, test_hooked_toolset, test_lint_hook, test_notification_hook, test_slack_interactive, test_subagent_hook, test_terminal_tools, test_test_hook. One file per commit. AC: zero _run() definitions in tests/. All tests pass."
```
