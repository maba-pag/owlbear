# Testing BearClaw Decision Commands

> **Owning task:** #778 — Tests for bearclaw decisions commands
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

Task #777 will implement `bearclaw decisions {list,show,resolve}` in
`src/bearclaw/commands/decisions.py`. This task (#778) needs TDD tests written
**before** the implementation (RED phase). What test patterns, fixtures, and
mocking strategies should the test-writer use — especially for the interactive
`resolve` flow?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Existing CLI tests: `test_cli_project.py` | local: `tests/test_cli_project.py` | .95 — gold-standard pattern (CliRunner + tmp_path + mock settings) |
| 2 | Typer testing docs | <https://typer.tiangolo.com/tutorial/testing/> | .90 — official `input=` for prompt testing |
| 3 | Existing chat tests: `test_cli_chat.py` | local: `tests/test_cli_chat.py` | .85 — shows `input=` with CliRunner for multi-turn interaction |
| 4 | Rich Prompt docs | <https://rich.readthedocs.io/en/stable/prompt.html> | .70 — `Prompt.ask(choices=...)` API and Console integration |
| 5 | Research doc for #767 | local: `docs/research/bearclaw-decision-commands.md` | .95 — implementation spec (parsing, UX, file layout) |

## 3. Analysis

### A: Fixture strategy — how to provide test decision files

| Criterion | tmp_path direct (.85) | Shared conftest fixture (.70) |
|-----------|-----------------------|-------------------------------|
| Isolation | Each test creates its own files | Shared state risk |
| KISS | Simple: `Path.write_text()` | Extra indirection |
| Precedent | `test_cli_project.py` uses tmp_path directly | No existing conftest for CLI |
| Reuse | Small helper function in test module | Fixture coupling |

**Verdict (.85):** Use `tmp_path` directly. A module-level `_make_decision_file(dir, ...)` helper
(~10 LOC) creates a well-formed decision request file. Monkeypatch the module constant
for the decisions directory to point at `tmp_path`.

### B: Interactive resolve testing — CliRunner input= vs mocking

| Criterion | CliRunner input= (.65) | Mock prompt calls (.85) |
|-----------|------------------------|-------------------------|
| Fidelity | Tests real stdin flow | Tests logic, not prompt wiring |
| Reliability | Fragile with Rich Prompt.ask (uses `Console.input()` → builtin `input()`, not Click stdin) | Deterministic |
| Precedent | `test_cli_chat.py` uses input= with typer prompts | Standard mock pattern |
| KISS | One line per test | patch() calls needed |

**Verdict (.85):** Two-layer approach:

1. **If implementation uses `typer.prompt()` / `typer.confirm()`:** CliRunner `input=` works natively (Click patches stdin). Use `input="A\nnotes text\ny\n"` for the 3-step resolve flow.
2. **If implementation uses `Rich.Prompt.ask()`:** Mock it — `Prompt.ask` uses `Console.input()` which calls Python's `input()`, and CliRunner may not redirect `sys.stdin` reliably for non-Click prompts.

**Recommendation for #777 builder:** Prefer `typer.prompt()` with a choices list over
`Rich.Prompt.ask()` for the option selection step. This makes tests simpler and
CliRunner-compatible. The research doc for #767 already lists both as viable; this
finding narrows the recommendation.

### C: Test categories mapping to AC

| AC Item | Test class | Key assertions |
|---------|-----------|----------------|
| list with 0 decisions | `TestDecisionsList` | exit 0, "No pending" message |
| list with 1, 2+ decisions | `TestDecisionsList` | Rich Table in output, correct columns |
| show found | `TestDecisionsShow` | exit 0, file content in output |
| show not found | `TestDecisionsShow` | exit 1, error message |
| resolve interactive | `TestDecisionsResolve` | exit 0, prompts answered |
| resolve moves file | `TestDecisionsResolve` | file gone from pending/, exists in resolved/ |
| malformed frontmatter | `TestDecisionsErrors` | exit 1, graceful error (no traceback) |

## 4. Recommendation (.85 confidence)

The test file should follow `test_cli_project.py` conventions exactly:

- **Runner:** `CliRunner()` at module level
- **Path mocking:** Monkeypatch the `DECISIONS_DIR` constant in `decisions.py`
  (or patch `Path.cwd()`) to point at `tmp_path`
- **Fixture helper:** `_make_decision_file(pending_dir, task_id, title, ...)` that writes
  valid YAML-frontmatter markdown
- **Interactive input:** `runner.invoke(app, ["decisions", "resolve", "123"], input="A\nnotes\ny\n")`
- **File assertions:** `assert (resolved_dir / filename).exists()` and
  `assert not (pending_dir / filename).exists()`

**Risk:** The `decisions.py` file doesn't exist yet (#777). The test-writer must
define expected CLI interface from the AC and research doc, then write tests that
will fail until #777 is implemented. Standard TDD RED workflow.

## 5. Follow-up Tasks

No new tasks needed — #778 is already the test task for #777. The AC is specific
and complete. The test-writer can proceed directly with the patterns above.
