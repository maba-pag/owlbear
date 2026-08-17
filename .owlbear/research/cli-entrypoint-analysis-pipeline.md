# CLI Entrypoint for Analysis Pipeline

> **Owning task:** #180 — Add CLI entrypoint for analysis pipeline
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #180 requires a `python -m owlbear_orchestrator.analyze` entrypoint that reads audit JSONL, runs analysis, and prints results to stdout. The analysis module (#179) is implemented and archived. Key questions: (a) argparse vs Typer for `__main__.py`? (b) How to structure the entrypoint for testability? (c) Should we also wire `owlbear analyze` into the existing Typer CLI?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python docs — `__main__` module | https://docs.python.org/3/library/__main__.html | .95 |
| 2 | Typer docs — Building a Package | https://typer.tiangolo.com/tutorial/package/ | .85 |
| 3 | OwlBear MCP `__main__.py` files | `packages/mcp-kanban/src/owlbear_mcp_kanban/__main__.py` | .90 |
| 4 | OwlBear existing CLI | `packages/orchestrator/src/owlbear/cli.py` | .90 |
| 5 | OwlBear analysis module | `packages/orchestrator/src/owlbear_orchestrator/analysis/` | .95 |
| 6 | Research: self-improvement-analysis-pipeline | `docs/research/self-improvement-analysis-pipeline.md` S3.5 | .95 |

## 3. Analysis

### 3.1 argparse vs Typer for `__main__.py`

| Criterion | argparse (.85) | Typer (.65) |
|-----------|----------------|-------------|
| Dependencies | 0 (stdlib) | Already installed, but heavier import |
| LOC | ~35 | ~40 |
| KISS | High — 3 options, no subcommands | Medium — framework for a trivial CLI |
| Testability | `main(argv)` pattern, no framework state | Needs `CliRunner` or function extraction |
| Python docs pattern | Standard recommended approach (S1) | Not the `-m` convention |
| Startup time | Fast (stdlib only) | Slower (Typer + Click import chain) |

Python docs (S1) recommend: keep `__main__.py` short, import a `main()` function from another module, wrap in `sys.exit(main())`. Typer docs (S2) show `__main__.py` as `from .main import app; app()` — but that's for when the Typer app IS the module's purpose. Here, the module's purpose is analysis; the CLI is a thin access layer.

### 3.2 `__main__.py` Structure

Python docs (S1) recommend the idiomatic pattern:

```python
# __main__.py — kept minimal
from owlbear_orchestrator.analysis._cli import main
import sys

sys.exit(main())
```

With the actual CLI logic in a separate `_cli.py`:

```python
# _cli.py
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args(argv)
    # call analyze(), format, print
    return 0
```

The `argv` parameter enables testing without subprocess or monkeypatching `sys.argv`. MCP packages (S3) use an even simpler pattern (`mcp.run()`) but their entrypoint has no arguments.

### 3.3 Integration with `owlbear` CLI

The existing CLI (`owlbear.cli:app`) uses Typer with commands: `dispatch`, `run`, `status`. Adding `owlbear analyze` would be natural via `app.add_typer()` or a direct `@app.command()`. However:

- **AC scope:** Task #180 asks only for `python -m owlbear_orchestrator.analyze`
- **YAGNI:** The research doc (S6, S3.5) already recommended: "Module entrypoint (`-m`) for now; wrap in `owlbear analyze` when CLI materializes"
- **Separation:** Analysis is in `owlbear_orchestrator` namespace; CLI is in `owlbear` namespace

Wiring `owlbear analyze` is ~5 lines of code — a trivial follow-up if wanted.

### 3.4 AC Mapping to Implementation

| AC | Implementation |
|----|---------------|
| `python -m owlbear_orchestrator.analyze` runs analysis | `__main__.py` imports `main()` from `_cli.py` |
| `--window` filters by time window | `argparse` arg, convert hours to `timedelta`, pass to `analyze()` |
| `--format json` prints JSON array | Use existing `format_json()` from `formatters.py` |
| `--format markdown` prints formatted report | Use existing `format_markdown()` from `formatters.py` |
| Exit code 0 on success, 1 on error | `try/except` in `main()`, return int |
| No proposals: empty array or "No issues detected" | JSON: `[]`, markdown: `"No issues detected."` (already handled by `format_markdown`) |

### 3.5 Window Default

AC says "default all". The `analyze()` function uses `DEFAULT_WINDOW = timedelta(days=7)` when `window=None`. For "--window default all", the CLI should pass `window=None` AND override `analyze()`'s default to mean "no cutoff". Two approaches:

| Approach | Change needed |
|----------|--------------|
| A: Pass very large timedelta when no --window | No changes to analyze(), e.g. `timedelta(days=36500)` |
| B: Add explicit "all" support in analyze() | Change `analyze()` to treat `window=timedelta(0)` or sentinel as "no filter" |

Current `analyze()` always applies a cutoff (`now - window`). For "all", the CLI can pass a very large window (100 years). This avoids changing the already-tested `analyze()` function. KISS.

## 4. Recommendation (.85 confidence)

**Option: argparse `__main__.py` with `_cli.py` helper.** ~35 LOC total across 2 files.

- `_cli.py`: `main(argv=None) -> int` with argparse, calls `analyze()` + formatters
- `__main__.py`: 3-line entrypoint per Python docs pattern
- No changes to existing `analyze()` or `cli.py`
- "All" window handled via large timedelta (no sentinel needed)

**Rationale:** KISS — stdlib argparse for 3 simple options. Testable `main(argv)` pattern. Zero changes to existing code. Follows Python docs idiom for `-m` modules (S1, S3).

**Risks:**

| Risk | Mitigation |
|------|------------|
| Two CLI paths (owlbear CLI + -m) diverge | Future follow-up to wire `owlbear analyze` via `app.add_typer()` |
| `analyze()` default window (7d) vs "all" semantics | CLI passes explicit large window; document behavior |
| audit_dir doesn't exist | `analyze()` already handles missing dir (returns empty list) |

## 5. Follow-up Tasks

Task #180 is the implementation task itself. No additional decomposition needed — the AC is concrete and the implementation is ~35 LOC. The architect can approve and advance.

Optional future enhancement (not blocking):
- Wire `owlbear analyze` into the Typer CLI as a subcommand (separate task if needed)
