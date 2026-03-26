# CompletedProcess Factory — Implementation Gate Review

> **Owning task:** #927 — Implement shared CompletedProcess factory for BearClaw CLI tests
> **Date:** 2026-03-24  **Status:** Complete

## 1. Context and Question

Task #927 was created as a follow-up from `docs/research/bearclaw-cli-subprocess-result-helper.md` (task #926). The question: how much of the AC is already satisfied by prior work (#920, #924, #926), and what remains?

## 2. Sources Studied

| ID | Source | What it established | Relevance |
|----|--------|---------------------|-----------|
| S1 | `tests/conftest.py` lines 126–139 | `make_completed_process` factory already exists, returns real `subprocess.CompletedProcess[str]` | .95 |
| S2 | `tests/test_conftest_helpers.py` lines 188–300 | `TestFromAC_MakeCompletedProcess` has 14+ contract tests covering importability, type, defaults, payloads, malformed data, and signature | .95 |
| S3 | `tests/test_cli_chat.py` lines 305–352 | Chat tests already use the shared helper (4 call sites, replacing prior `MagicMock` boilerplate) | .95 |
| S4 | `tests/test_cli_board.py` lines 400–435 | Board tests compose the shared helper inside local routers (`_subproc_fail_list`, `_subproc_fail_log`) | .95 |
| S5 | `tests/test_cli_board.py` lines 465–472 | Missing-binary test uses inline `FileNotFoundError`, not a named fixture/helper | .90 |
| S6 | `tests/test_conftest_helpers.py` lines 324–381 | `TestFromAC_ZeroDuplicates` guards MockChannel, `_make_mock_toolset`, `_make_settings` — no guard for `make_completed_process` | .90 |
| S7 | Python subprocess docs — `CompletedProcess` | [S1] factory correctly mirrors real text-mode contract: `args`, `returncode`, `stdout`, `stderr` | .85 |
| S8 | pytest fixture docs — factory-as-fixture pattern | [S1] factory function shape matches recommended pytest "factories as fixtures" pattern | .85 |

## 3. Analysis — AC Compliance Matrix

| AC Line | Current State | Gap? | KISS/YAGNI Assessment |
|---------|-------------|------|----------------------|
| AC1: Importable conftest helper for success/nonzero/malformed | DONE — `make_completed_process` at `conftest.py:126` | No | ✅ |
| AC2: Board routing local, composes shared helper | DONE — `_subproc_fail_list`/`_subproc_fail_log` at `test_cli_board.py:400` | No | ✅ |
| AC3: Named OSError fixture/helper | NOT DONE — 1 inline `FileNotFoundError` at `test_cli_board.py:469` | Yes | YAGNI: only 1 call site. Extraction premature until a second CLI test file needs it. |
| AC4: Reuse in chat + board after #924/#920 | DONE — 4 usages in `test_cli_chat.py`, board routers compose it, #920/#924 archived | No | ✅ |
| AC5: Contract coverage + duplicate guard | PARTIAL — 14+ contract tests exist, but no `make_completed_process` duplicate-guard in `TestFromAC_ZeroDuplicates` | Yes (guard) | Duplicate-guard is trivial and matches repo convention. Worth adding. |
| AC6: Scope under tests/ only | DONE — no production changes | No | ✅ |

## 4. Recommendation (.88 confidence)

**Close #927 as substantially complete; create one narrow follow-up task.**

The core value of #927 — shared factory, reuse across CLI tests, contract coverage — was delivered incrementally by #920, #924, and #926 pipeline work. Two small gaps remain:

1. **Duplicate-guard for `make_completed_process`** (.92 confidence): Add a parametrized test in `TestFromAC_ZeroDuplicates` that asserts `test_cli_chat.py` and `test_cli_board.py` do NOT define their own `make_completed_process`. This is trivial (~10 LOC) and consistent with the existing guard pattern for MockChannel, `_make_mock_toolset`, and `_make_settings`. [S6, S8]

2. **Named OSError fixture** (.45 confidence — defer): Only board tests use the missing-binary seam (1 inline `FileNotFoundError`). Extracting a shared fixture for 1 consumer violates YAGNI. Revisit when a second CLI test file needs the pattern. [S5, S7]

## 5. Follow-up Tasks

One narrow task to close the duplicate-guard gap. The OSError fixture is deferred per YAGNI.

```
kanban\kanban-md.exe create "Add make_completed_process duplicate-guard to test_conftest_helpers.py" --priority nice-to-have --status ideation --tags "cli,test,tooling,type:test,scope:cli" --body "Research follow-up from docs/research/completedprocess-factory-implementation-gate.md.\n\n## AC\n- [ ] Add a parametrized test in TestFromAC_ZeroDuplicates (tests/test_conftest_helpers.py) that asserts test_cli_chat.py and test_cli_board.py do not define their own make_completed_process function.\n- [ ] Follows existing duplicate-guard pattern (see MockChannel, _make_mock_toolset, _make_settings guards).\n- [ ] Existing tests stay green.\n- [ ] Scope: tests/test_conftest_helpers.py only."
```
