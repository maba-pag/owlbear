# Extract Error-Exit Pattern into CLI Helper

> **Owning task:** #532 — Extract error-exit pattern into CLI helper
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

F-19 from code-quality audit: `except SomeException: typer.echo(f'Error: {exc}'); raise typer.Exit(1)` is repeated 21 times in `src/bearclaw/cli.py`. What's the best DRY extraction?

Research checklist: N/A — trivial DRY extraction, rationale: single-file mechanical refactor of a 2-line pattern.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Typer docs — Exit | <https://typer.tiangolo.com/tutorial/terminating/> | 1.0 — confirms `typer.Exit(code=1)` is the canonical error-exit |
| FastAPI/Typer repos | <https://github.com/fastapi/typer> | 0.7 — no built-in error helper; user code handles this |

## 3. Analysis

### Current pattern inventory (21 sites + 1 clean exit)

| Shape | Count | Example |
|-------|-------|---------|
| `except X as exc: echo(f"Error: {exc}"); raise Exit(1) from None` | 7 | project create, new, voice listen/speak/brainstorm |
| `except X as exc: echo(f"Error: ...{error_to_user_message(exc)}"); raise Exit(1) from exc` | 4 | slack auth/test, browser start, auth login |
| `if bad: echo(f"Error: ..."); raise Exit(1)` | 10 | validation checks in knowledge-source commands, slack, browser stop |
| `raise typer.Exit` (version callback, no error) | 1 | _version_callback — not in scope |

### Options

| Criterion | A: `_cli_error(msg)` helper | B: Context manager | C: Decorator |
|-----------|-----------------------------|--------------------|--------------|
| Covers try/except pattern | Yes | Yes | Yes |
| Covers validation pattern | Yes | No | No |
| LOC added | ~4 | ~8 | ~12 |
| Magic/complexity | None | Low | Medium |
| KISS | High | Medium | Low |
| YAGNI | High | Medium — context mgr unused for validation | Low — too coarse |

## 4. Recommendation (.90 confidence)

**Option A: `_cli_error(msg)` helper function** — a single `NoReturn` function that does `typer.echo(f"Error: {msg}"); raise typer.Exit(code=1)`.

```python
def _cli_error(msg: str) -> NoReturn:
    """Print error message and exit with code 1."""
    typer.echo(f"Error: {msg}")
    raise typer.Exit(code=1)
```

Usage at all 21 sites:

- **try/except**: `except ValueError as exc: _cli_error(str(exc))`
- **try/except with sanitizer**: `except httpx.HTTPError as exc: _cli_error(f"Slack API request failed: {error_to_user_message(exc)}")`
- **validation**: `if source is None: _cli_error(f"No source named '{name}'")`

Trade-off: loses `from None`/`from exc` chaining on the `Exit`. This is cosmetic — `typer.Exit` is a `SystemExit` subclass; the chain is never displayed to CLI users. Acceptable.

The one non-error exit (`_version_callback`) stays as-is.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement _cli_error() helper in bearclaw/cli.py" --priority nice-to-have --status todo --tags "audit,dry,scope:cli" --body "Extract _cli_error(msg: str) -> NoReturn helper. Replace all 21 echo+Exit(1) sites. See docs/research/cli-error-exit.md. AC: (1) _cli_error() defined with NoReturn annotation. (2) Zero raw typer.Exit(code=1) in cli.py except _version_callback. (3) All existing CLI tests pass. (4) ruff clean."
```

## 6. Existing test coverage

8 test files cover CLI commands — changes are mechanical replacements so existing tests verify behavior is preserved.
