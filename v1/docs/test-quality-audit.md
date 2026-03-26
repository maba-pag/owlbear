# Test Quality Audit — OwlBear

> **Date:** 2026-03-03 **Status:** Complete

## 1. Executive Summary

The OwlBear test suite is **strong** — 3171 tests, 98% coverage, and the code exercises real behavior through well-structured TDD. However, 8 tests are currently failing (not 6 as reported), test quality has specific weaknesses in prompt-assertion brittleness and missing prefix-path tests, and the benchmark harness tests are fundamentally broken due to network/SSL dependencies running unguarded.

**Verdict:** High-quality suite with actionable gaps. The issues below are ordered by severity.

## 2. Failing Test Analysis

### Actual failures: 8 (not 6)

| Test file | Count | Root cause | Severity |
|---|---|---|---|
| test_benchmark_harness.py — `TestLoadNfcorpus` | 6 | SSL cert verification failure downloading BEIR dataset from `public.ukp.informatik.tu-darmstadt.de`. Corporate proxy intercepts SSL. **Not a code bug — environment issue.** | HIGH |
| test_kanban_pipeline.py — `TestOrchestratorKanbanPrompt` | 2 | Tests assert `"Kanban Pipeline"` and `"kanban_edit"` exist in the orchestrator agent's `system_prompt`. The prompt was updated, but these tests were not. **Stale prompt assertions.** | MEDIUM |

**TestLoadNfcorpus fix:** These tests attempt to download a 2.8 MB dataset from the internet with no skip guard. They should: (a) be marked `@pytest.mark.network` and skipped by default, (b) use `truststore` or pass `verify=False` through beir's requests session, or (c) mock the download path for unit tests and reserve real downloads for a CI integration marker.

**TestOrchestratorKanbanPrompt fix:** The orchestrator's `.agent.md` definition was refactored and no longer contains those exact strings. Either update the assertions to match the current prompt, or test for semantic intent (e.g., "mentions kanban tools") rather than exact substrings.

## 3. Coverage Gap Analysis

| Module | Coverage | Missed | Justified? | Recommendation |
|---|---|---|---|---|
| `copilot_multipliers.py` | 80% | 2 lines: prefix-stripping loop body (`model = model[len(prefix):]`, `break`) | **CONCERNING** — clear missing test. No test calls `get_premium_requests("openai:gpt-4o")` or `get_premium_requests("copilot:o1")`. | Add 2 tests for prefix stripping. Trivial fix. |
| `bookmark_pipeline.py` | 89% | 6 lines: `_default_web_read()` function (lines ~178–191) — httpx+trafilatura | **JUSTIFIED** — fallback web reader requires real HTTP. Pipeline tests use `mock_web_read` fixture. | Add a unit test that mocks `httpx.AsyncClient` and `trafilatura.extract` to cover the function shape. |
| `bootstrap.py` | 94% | 19 lines: `_add_project_toolset` exception path, `_patch_project_toolset_agent` miss on no match, voice channel creation, Slack channel creation | **PARTIALLY JUSTIFIED** — exception paths and channel dispatch branches for voice/Slack. Bootstrap integration tests cover the main paths. | Add unit tests for `_add_project_toolset` exception handling and Slack/voice channel branches. |
| `browser/config.py` | 94% | 4 lines: `_cdp_endpoint_localhost_only` URL parse exception, `_cdp_port_valid_range` boundary | **MINOR** — validator edge cases for malformed URLs. Main paths well-tested. | Add test for `cdp_endpoint="not://a-url-at-all"` and port 0 / 65536. |
| `bearclaw/cli.py` | 96% | 22 lines: voice brainstorm (lines 320–338, needs voice extras), chat REPL internals (lines 1088–1101), daemon `_is_process_alive` (lines 1044–1048), knowledge-source refresh (line 594) | **JUSTIFIED** — voice commands need optional extras, chat REPL inner loop is integration-level, `_is_process_alive` is OS-specific. | Low priority. Add targeted mocked tests for `_is_process_alive` and `_read_multiline`. |
| `tools/ask_user.py` | 96% | 3 lines: likely the `_receive_option` exhausted-retries path when all retries produce `None` | **MINOR** — edge case where channel returns None on every attempt. | Add test: channel returns `[None, None, None]` with `max_retries=3` for options. |
| `tools/github_api.py` | 96% | 4 lines: `get_issue` error path, possibly `_emit_hook` when hooks is None | **MINOR** — HTTP error paths for `get_issue` are likely untested. | Add `test_get_issue_error_returns_message`. |
| `tools/filesystem.py` | 97% | 3 lines: `_search_files` truncation message branch (>100 results) | **JUSTIFIED** — requires 101+ glob matches in test. | Low priority. Add test with 101 files to exercise truncation. |
| `knowledge/ingest.py` | 97% | 7 lines: likely `_read_source` URL dispatch, `_run_embed` fallback wrapping | **JUSTIFIED** — pipeline tested extensively with 1719 lines of tests. Some branches unreachable with standard mocks. | Low priority. |
| `memory/usage.py` | 97% | 2 lines: `summary()` with `window=None` (all-records path) | **MINOR** — `summary(None)` calls `self.load()` instead of `self.query(window)`. | Add `test_summary_none_window_returns_all`. |

## 4. Test Quality Findings

### CRITICAL

None.

### HIGH

**H1. Benchmark harness tests require network with no guard** — `TestLoadNfcorpus` (6 tests) unconditionally downloads a dataset from the internet. No `@pytest.mark.network` marker, no skip-on-failure, no mock fallback. These tests will fail on any machine behind a corporate proxy, on CI without outbound access, or when the server is down. This violates test isolation.

**H2. Two additional failing tests unreported** — `test_kanban_pipeline.py::TestOrchestratorKanbanPrompt` has 2 failures asserting stale prompt content. The reported failure count (6) undercounts actual failures (8).

### MEDIUM

**M1. Prompt assertion brittleness** — `TestOrchestratorKanbanPrompt` asserts exact substrings (`"Kanban Pipeline"`, `"kanban_edit"`) in agent system prompts. Any prompt rewording breaks these. Better: test for tool names in the agent's tool list, or use regex patterns for semantic intent.

**M2. `copilot_multipliers.py` at 80% with trivial fix** — The prefix-stripping code path (the whole feature of the function) is untested. Two lines that handle the primary input normalization (`openai:model`, `copilot:model`) are never exercised.

**M3. conftest.py is minimal** — Only 1 fixture (`default_settings`). Every test file reinvents `_run()`, `_make_channel()`, and similar helpers. This works but creates duplication across 120+ files. Consider extracting common patterns.

### LOW

**L1. `_run()` helper duplication** — At least 8 test files define `def _run(coro): return asyncio.run(coro)`. This could be a shared conftest fixture or utility.

**L2. Some test files import `Path` inside methods** — `test_filesystem_tools.py` has `from pathlib import Path` inside individual test methods instead of at the top. Functional but unconventional.

**L3. Deprecation warnings from PydanticAI** — 77 warnings about "Specifying a model name without a provider prefix is deprecated." Bootstrap tests pass `MagicMock` as model, which triggers the warning. Not a test failure but noisy.

### INFO

**I1. `_default_web_read` completely untested** — The fallback web reader in `bookmark_pipeline.py` is never exercised. All pipeline tests correctly mock `web_read_fn`. This is fine for unit tests but means the real HTTP+trafilatura path has zero test coverage.

**I2. Voice CLI commands completely untested** — The `voice listen`, `voice speak`, and `voice brainstorm` commands are untested because they require the `[voice]` optional extra. Justified — but if voice is ever shipped, these need test coverage.

## 5. Mock Usage Assessment

**Verdict: Mocks are used appropriately.** The codebase follows the right pattern:

- **Mocked at boundaries:** LLM calls (`AsyncMock` on `agent.run`), HTTP (`httpx.AsyncClient`), subprocess (`asyncio.create_subprocess_exec`), file I/O for remote resources.
- **Real implementations for logic:** `GraphStore` tests use real in-memory SQLite. `SessionStore` tests use real `tmp_path` files. `BrowserConfig` tests use real Pydantic validation.
- **No mock abuse detected:** Tests don't mock internal functions to force coverage. The `IngestPipeline` tests mock external providers but exercise the real orchestration logic.

One minor concern: `test_cli.py` mocks deep into the bootstrap chain (`patch("owlbear.bootstrap.bootstrap")`, `patch("owlbear.daemon.run_daemon")`), which couples tests to import paths. This is acceptable for CLI integration tests but would be fragile if module paths change.

## 6. Test Categories Assessment

| Category | Present? | Quality | Notes |
|---|---|---|---|
| Unit tests | Yes — majority | High | Well-isolated, behavior-focused, good assertion density |
| Integration tests | Yes | Good | `test_bootstrap_integration.py`, `test_integration_e2e.py`, `test_e2e_chat.py`, several `*_integration.py` files |
| Error path tests | Yes | Good | `test_error_recovery.py` (507 lines), error classification, retry logic, escalation edge cases |
| Edge case tests | Yes | Good | Null bytes, empty strings, boundary values, frozen model mutation |
| Async tests | Yes | Correct | Proper `@pytest.mark.asyncio` and `asyncio.run()` patterns |
| Performance/benchmark | Partial | Broken | `tests/benchmarks/` exists but `TestLoadNfcorpus` fails due to environment |
| Fixture quality | Good | — | Local fixtures are well-scoped; `conftest.py` minimal but intentional |
| Test isolation | Good | — | No test-order dependencies detected; `tmp_path` and `monkeypatch` used correctly |

## 7. Test Isolation Assessment

- **No shared mutable state** between tests. Each test creates fresh fixtures.
- **Environment leakage prevented** by `default_settings` fixture that clears `OWLBEAR_*` env vars.
- **`tmp_path`** used for all file-based tests — no test writes to real filesystem.
- **`ALLOW_MODEL_REQUESTS = False`** in e2e tests prevents accidental real API calls.
- Tests can run in any order. No evidence of test coupling.

## 8. Async Testing Assessment

- `pytest-asyncio` used correctly throughout.
- Two patterns coexist: `@pytest.mark.asyncio async def test_...` and `def test_...: asyncio.run(coro)`. Both are valid.
- No `loop_scope` issues observed (explicit `loop_scope="function"` used where needed).
- No fire-and-forget `create_task` leaks in tests — background tasks in `IngestPipeline` are tested with `await asyncio.sleep(0)` draining patterns.

## 9. Top 10 Testing Improvements

| # | Action | Impact | Effort |
|---|---|---|---|
| 1 | Add `@pytest.mark.network` to `TestLoadNfcorpus` + skip by default | Fixes 6 failing tests | Low |
| 2 | Fix `TestOrchestratorKanbanPrompt` stale prompt assertions | Fixes 2 failing tests | Low |
| 3 | Add prefix-stripping tests to `test_copilot_multipliers.py` | Raises coverage from 80% → 100% | Low |
| 4 | Add `_default_web_read` unit test with mocked httpx/trafilatura | Raises bookmark_pipeline from 89% → ~95% | Low |
| 5 | Add `summary(window=None)` test to `test_usage_tracker.py` | Covers the all-records path | Low |
| 6 | Extract `_run()` helper to `conftest.py` | Removes duplication across 8+ files | Low |
| 7 | Add `cdp_endpoint` malformed URL + port boundary tests | Raises browser/config from 94% → ~100% | Low |
| 8 | Add `get_issue` HTTP error test to `test_github_api.py` | Raises github_api from 96% → ~100% | Low |
| 9 | Add `_is_process_alive` + `_read_multiline` tests for CLI | Reduces cli.py missed from 22 → ~15 | Medium |
| 10 | Fix PydanticAI deprecation warnings in bootstrap tests | Cleans up 77 warnings | Low |

## 10. Follow-up Tasks

```
kanban\kanban-md.exe create "Fix 6 failing TestLoadNfcorpus — add @pytest.mark.network skip" --priority needed --status todo --tags "test,phase-12" --description "Add @pytest.mark.network marker and pytest skip condition for SSL/network failures. Tests download BEIR dataset — must not run on corporate proxy or offline CI."

kanban\kanban-md.exe create "Fix 2 failing TestOrchestratorKanbanPrompt — update stale prompt assertions" --priority needed --status todo --tags "test,phase-12" --description "Orchestrator agent prompt was refactored. Update test assertions to match current system_prompt content or switch to semantic checks."

kanban\kanban-md.exe create "Add prefix-stripping tests to test_copilot_multipliers.py" --priority important --status todo --tags "test,phase-12" --description "Test get_premium_requests('openai:gpt-4o') and get_premium_requests('copilot:o1') to cover the for-loop prefix stripping. Raises coverage from 80% to 100%."

kanban\kanban-md.exe create "Add unit test for _default_web_read in bookmark_pipeline.py" --priority important --status todo --tags "test,phase-12" --description "Mock httpx.AsyncClient and trafilatura.extract to test the fallback web reader. Raises coverage from 89% to ~95%."

kanban\kanban-md.exe create "Test suite cleanup — extract _run() helper, fix PydanticAI deprecation warnings" --priority nice-to-have --status todo --tags "test,phase-12" --description "Extract _run() to conftest.py. Fix model prefix warnings in bootstrap tests. Add summary(None) test to usage tracker."
```
