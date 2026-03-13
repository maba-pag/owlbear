# pytest-cov + pydantic v2.12 RootModel MRO Crash

> **Owning task:** #646 — Fix pytest-cov + pydantic v2.12 RootModel MRO crash
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Running `uv run pytest tests/test_diagram_toolset.py --cov=owlbear.tools.diagram.toolset` crashes with:

```
ValueError: tuple.index(x): x not in tuple
  at pydantic/_internal/_model_construction.py:159
```

Plain `pytest` (no `--cov`) works fine. The question: what causes this, and how do we fix it?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pydantic `_model_construction.py` | local venv, `_RootModelMetaclass.__new__` | 1.0 — crash site |
| 2 | coverage.py `misc.py` | local venv, `SysModuleSaver` class | 1.0 — root cause |
| 3 | coverage.py `inorout.py` | local venv, `InOrOut.__init__` L313-316 | 1.0 — trigger site |
| 4 | pydantic #6584 | <https://github.com/pydantic/pydantic/issues/6584> | 0.9 — same root cause, different symptom (PyO3 double-init) |
| 5 | coverage.py CHANGES.rst 6.0.2 | referenced in pydantic#6584 by @davidhewitt | 0.7 — documents `sys_modules_saved` as intentional behavior |
| 6 | coverage.py #1942 | <https://github.com/coveragepy/coveragepy/issues/1942> | 0.6 — feature request for `source_dirs` to bypass module probing |

## 3. Root Cause Analysis

### Trigger chain (7 steps)

1. `pytest-cov` starts coverage before conftest loading (`tryfirst=True` hook)
2. `--cov=owlbear.tools.diagram.toolset` is not a directory → classified as `source_pkgs`
3. `InOrOut.__init__` calls `file_and_path_for_module()` inside `with sys_modules_saved():`
4. `file_and_path_for_module` calls `importlib.util.find_spec('owlbear.tools.diagram.toolset')` — this **imports 963 modules including 121 pydantic modules** (verified experimentally)
5. Pydantic's `@functools.cache`-decorated `import_cached_base_model()` caches the first `BaseModel` class object during these imports
6. `SysModuleSaver.restore()` deletes all 963 newly-imported modules from `sys.modules` — **but `@cache` still holds the old `BaseModel` reference**
7. Conftest loading re-imports pydantic → new `BaseModel` class (different `id()`) → `mro.index(old_BaseModel_)` fails → `ValueError`

### Experimental proof

```python
# After find_spec:  Cached BaseModel id: 2207384612192
# After sys.modules cleanup + re-import:  New BaseModel id: 2207412581776
# Same object? False
# import_cached_base_model() still returns old? True
```

### Who's at fault

| Component | Fault | Severity |
|-----------|-------|----------|
| **coverage.py** `SysModuleSaver` | Removes modules from `sys.modules` after probing — breaks any library using `@cache` or globals for identity lookups | Design trade-off (documented since 6.0.2) |
| **pydantic** `import_cached_base_model` | `@functools.cache` assumes module identity persists; `mro.index()` has no fallback | Fragile assumption |
| **Our config** | Uses dotted module names in `--cov=` instead of directory paths | Avoidable trigger |

### Why directory paths work

Coverage classifies `--cov` sources via `os.path.isdir()`. Directory paths go to `source_dirs` (no `find_spec` call needed). Module names go to `source_pkgs` (triggers `find_spec` → the full import chain).

## 4. Recommendation (.95 confidence)

**Use directory paths in all `--cov=` arguments.** Change `--cov=owlbear.{module}` → `--cov=src/owlbear/{path}` everywhere.

| Option | Confidence | Pros | Cons |
|--------|-----------|------|------|
| **A. Directory paths in --cov** | **.95** | Zero-risk, already proven, no version deps | Slightly more verbose |
| B. Bare `--cov` (use pyproject.toml) | .85 | Simplest, `pyproject.toml` already has directory source | Measures all source, not module-scoped |
| C. Pin pydantic < 2.12 | .30 | Avoids trigger | Blocks upgrades, doesn't fix root cause |
| D. Wait for pydantic/coverage fix | .20 | Upstream fix | No timeline, both projects consider this edge-case |

**Option A** aligns with KISS and matches `pyproject.toml` (which already uses `src/owlbear`). The `python.instructions.md` already uses the correct pattern (`--cov=src/owlbear`). Only the skills need updating.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Fix --cov dotted module names in code-review + tdd-workflow skills" --priority needed --status todo --tags "bugfix,config,scope:copilot" --body "Change --cov=owlbear.{module} to --cov=src/owlbear/{path} in:\n- .github/skills/code-review/SKILL.md (line 51)\n- .github/skills/tdd-workflow/SKILL.md (line 80)\n\nAlso update AC line in kanban task #646.\n\nSee docs/research/pytest-cov-pydantic-mro-crash.md for root cause."

kanban\kanban-md.exe create "Add --cov gotcha note to python.instructions.md" --priority nice-to-have --status backlog --tags "docs,config" --body "Add a warning to the coverage section:\n> Never use dotted module names with --cov (e.g. --cov=owlbear.module). Always use directory paths (--cov=src/owlbear/path). Dotted names trigger coverage.py module probing that crashes pydantic.\n\nSee docs/research/pytest-cov-pydantic-mro-crash.md"
```
