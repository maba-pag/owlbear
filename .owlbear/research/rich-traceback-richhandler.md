# Rich Traceback and RichHandler for Daemon Logging

> **Owning task:** #632 — Add rich.traceback and RichHandler to daemon logging
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #632 asks: should we install `rich.traceback.install()` in the CLI entry point and replace the daemon's stderr `StreamHandler` with `RichHandler`? The file handler must remain plain text (no ANSI escape codes in log files).

Key questions:

1. Is `rich.traceback` + `RichHandler` the right approach?
2. Does `RichHandler` leak ANSI codes into file handlers?
3. Where exactly should each piece be wired in?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|:---------:|
| Rich logging docs | <https://rich.readthedocs.io/en/stable/logging.html> | .95 |
| Rich traceback docs | <https://rich.readthedocs.io/en/stable/traceback.html> | .90 |
| `RichHandler` source | <https://github.com/Textualize/rich/blob/master/rich/logging.py> | .95 |
| `RichHandler` API reference | <https://rich.readthedocs.io/en/stable/reference/logging.html> | .85 |
| Litestar logging config | <https://github.com/litestar-org/litestar/blob/main/litestar/logging/config.py> | .70 |
| Uvicorn logging (colored formatter) | <https://github.com/encode/uvicorn/blob/master/uvicorn/logging.py> | .65 |

## 3. Analysis

### 3.1 Theoretical Validity

`rich.traceback.install()` replaces `sys.excepthook` so uncaught exceptions get syntax-highlighted tracebacks in the terminal. `RichHandler` is a `logging.Handler` subclass that renders log output with colored levels, timestamps, and optional rich tracebacks. Both are standard, well-maintained APIs from the `rich` library (v14.3.3, already a transitive dependency via typer).

**Verdict:** Sound approach. No new dependencies. ~15 LOC of changes.

### 3.2 RichHandler vs File Handler Isolation

| Concern | Risk | Mitigation |
|---------|------|------------|
| ANSI in log file | **None** — `RichHandler` writes only to its own `Console` instance; it does not affect other handlers | Each handler is independent in Python logging |
| `rich.traceback.install()` affects stderr globally | Low — only changes `sys.excepthook` for _uncaught_ exceptions | Logged exceptions still go through their handler's formatter |
| File handler formatter | No risk — `RotatingFileHandler` keeps its own `Formatter` | Verified: `RichHandler` uses `Console.print()`, not `Formatter.format()` |

Key insight from rich source: `RichHandler.__init__` accepts a `console` parameter. When provided, it writes to **that console only**. The `RotatingFileHandler` uses a standard `logging.Formatter` — these are completely independent code paths. ANSI codes cannot leak from `RichHandler` to the file handler.

### 3.3 Where to Wire Each Piece

| Change | Location | Rationale |
|--------|----------|-----------|
| `rich.traceback.install()` | `cli.py` → `@app.callback()` (`main()`) | Affects CLI processes only; runs before any subcommand |
| Replace `StreamHandler` with `RichHandler` | `daemon.py` → `setup_logging()` | stderr handler becomes rich-formatted; file handler unchanged |

### 3.4 Implementation Approach

**`setup_logging()` in daemon.py** — replace:

```python
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
```

with:

```python
from rich.console import Console
from rich.logging import RichHandler

console = Console(stderr=True)
stream_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    markup=False,
    show_path=False,
)
```

- `markup=False` — safe for third-party log messages containing `[brackets]`
- `show_path=False` — daemon logs include `%(name)s` in the file handler; path column is redundant noise for stderr
- `rich_tracebacks=True` — logged exceptions get syntax-highlighted tracebacks on stderr
- File handler formatter stays as `logging.Formatter(_LOG_FORMAT)` — zero ANSI risk

**`main()` in cli.py** — add:

```python
from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=False, suppress=[typer, click])
```

- `show_locals=False` — avoids leaking secrets in crash dumps
- `suppress=[typer, click]` — hides framework frames from unhandled exceptions

### 3.5 Comparison: RichHandler vs Custom Colored Formatter

| Criterion | RichHandler (.90) | Custom formatter (.50) |
|-----------|-------------------|----------------------|
| LOC to implement | ~5 (constructor call) | ~40 (like uvicorn) |
| Rich tracebacks | Built-in | Manual integration |
| Maintenance | Upstream maintained | We own it |
| KISS alignment | High | Low |
| Dependency | Already installed | Same |

### 3.6 Testing Strategy

1. **No ANSI in file output:** Write a log message through `setup_logging()`, read the file, assert no bytes matching `\x1b\[` (ANSI CSI sequences).
2. **RichHandler on stderr:** Verify the stderr handler is an instance of `RichHandler`.
3. **File handler unchanged:** Verify file handler is still `RotatingFileHandler` with plain formatter.
4. **`rich.traceback.install()` in callback:** Verify `sys.excepthook` is set after CLI app callback runs. (Or simply trust side-effect and test via CLI runner — simpler.)

ANSI regex for tests: `re.compile(r'\x1b\[[\d;]*m')` catches all SGR sequences.

## 4. Recommendation (.90 confidence)

Proceed with the implementation as described in §3.4. This is a ~15 LOC change with zero new dependencies, clear isolation between rich stderr and plain-text file handler, and measurable test coverage. Risk is minimal — `RichHandler` is a drop-in replacement for `StreamHandler` that only affects its own `Console` output.

**Risks:**

- If daemon stderr is redirected to a file (e.g. `2>err.log`), `Console` auto-detects non-TTY and disables color. No action needed.
- Future handlers added to root logger must use their own formatters (standard Python logging practice).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Test: rich.traceback and RichHandler in daemon logging" --priority important --status todo --tags "phase-cli,scope:core,cli,test" --body "Test-first companion for #632. Write failing tests before implementation.`n`nSee docs/research/rich-traceback-richhandler.md S3.6.`n`n## AC`n`n- [ ] Test: setup_logging() stderr handler is RichHandler instance`n- [ ] Test: setup_logging() file handler is RotatingFileHandler with plain Formatter`n- [ ] Test: log output written to file contains no ANSI escape sequences (regex: \\x1b\\[)`n- [ ] Test: RichHandler has markup=False and rich_tracebacks=True`n- [ ] All tests fail initially (no implementation yet)`n- [ ] ruff clean"
```

Implementation task is #632 itself — move to backlog after research gate passes.
