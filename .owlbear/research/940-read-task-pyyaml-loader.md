# read_task() PyYAML SafeLoader Switch

> **Owning task:** #940 — Tier 1: Switch read_task() to NoTimestampSafeLoader (PyYAML)
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Research #921 found ruamel.yaml round-trip parsing is 90% of `list_tasks()` cost (0.501ms/file). The task AC proposes a `NoTimestampSafeLoader(yaml.SafeLoader)` subclass for the read path. Does this approach hold up under scrutiny, and what implementation details need revision?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/task_io.py` — current `read_task()` / `write_task()` | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/models.py` — `Task` model (bool fields, str timestamps) | 1.0 |
| S3 | `.owlbear/research/list-tasks-perf-921.md` — benchmark data, option analysis | 1.0 |
| S4 | PyYAML `yaml_implicit_resolvers` — REPL verification of subclass pattern | 0.9 |
| S5 | YAML 1.1 vs 1.2 boolean spec — REPL verification of coercion difference | 0.9 |
| S6 | `serve/kanban/pyproject.toml` — dependency audit (pyyaml absent) | 0.8 |

## 3. Analysis

### 3.1 Critical Gap in Original AC: YAML 1.1 Boolean Coercion

Challenger identified (confidence 0.35 in original): PyYAML uses YAML 1.1 where `yes`/`no`/`on`/`off` are implicit booleans. ruamel.yaml write path uses YAML 1.2 (only `true`/`false`). A `block_reason: no` written by ruamel would be read as `False` by vanilla PyYAML SafeLoader — silent data corruption.

Verified empirically: `yaml.safe_load("block_reason: no")` → `{'block_reason': False}`.

### 3.2 Revised Approach: YAML12SafeLoader

Strip both timestamp AND YAML 1.1 boolean resolvers, then re-add a YAML 1.2 boolean resolver (`true`/`false` only). Verified: all Task model types resolve correctly.

| Field example | YAML 1.1 SafeLoader | YAML12SafeLoader |
|---------------|---------------------|------------------|
| `blocked: true` | `True` (bool) ✓ | `True` (bool) ✓ |
| `block_reason: no` | `False` (bool) ✗ | `"no"` (str) ✓ |
| `tags: [on, off]` | `[True, False]` ✗ | `["on", "off"]` ✓ |
| `created: 2026-04-09T03:24:26.6974428+02:00` | `datetime` ✗ | `str` ✓ |
| `id: 42` | `42` (int) ✓ | `42` (int) ✓ |

### 3.3 Performance Comparison (1000-iteration benchmark, ms/file)

| Option | ms/file | vs rt | YAML 1.2 bools | Timestamps safe | New dep |
|--------|---------|-------|:-:|:-:|---------|
| A. ruamel rt fresh (status quo) | 0.523 | 1.0× | ✓ | ✓ | — |
| B. ruamel rt cached | 0.467 | 1.1× | ✓ | ✓ | — |
| C. ruamel base cached | 0.338 | 1.5× | ✗ (all str) | ✓ | — |
| D. PyYAML NoTimestampSafeLoader (orig AC) | 0.238 | 2.2× | ✗ (1.1) | ✓ | pyyaml |
| E. PyYAML YAML12SafeLoader (revised) | 0.167 | 3.1× | ✓ | ✓ | pyyaml |
| F. ruamel safe cached | 0.351 | 1.5× | ✓ | ✗ | — |

Option E gives 3.1× speedup (not 2.2× as originally projected) because stripping unused resolvers reduces per-scalar overhead.

### 3.4 Dependency Impact

- `pyyaml>=6.0.3` must be added to `serve/kanban/pyproject.toml` (currently only `ruamel.yaml>=0.18`, `pydantic>=2.0`)
- Two YAML libraries as direct deps is unusual but justified: pyyaml for fast reads, ruamel for round-trip writes
- pyyaml is already in workspace dev deps — no new transitive weight

### 3.5 AC Revisions Required

| Original AC | Revised |
|-------------|---------|
| `NoTimestampSafeLoader` | `YAML12SafeLoader` — reflects both timestamp and bool handling |
| timestamp resolver only stripped | Strip timestamp + YAML 1.1 bool, re-add YAML 1.2 bool resolver |
| — | Add `pyyaml>=6.0.3` to `serve/kanban/pyproject.toml` |
| Timestamp regression test only | Add write→read round-trip test for `yes`/`no`/`on`/`off` string fields |

## 4. Recommendation

**(rec:) Option E — YAML12SafeLoader with YAML 1.2 boolean semantics.** Confidence: 0.88.

Straightforward ~40 LOC change in `task_io.py`. The class is self-contained, the pattern is standard, and the 3.1× speedup exceeds the original 2.2× projection.

Challenge: reconsider → revised — confidence in original: 0.35. Accepted C1 (boolean coercion, critical) and C3 (missing dependency). The revised approach fully addresses both.

## 5. Follow-up Tasks

1. **Build task** — implement YAML12SafeLoader, update `read_task()`, add `pyyaml` dep, add regression tests
