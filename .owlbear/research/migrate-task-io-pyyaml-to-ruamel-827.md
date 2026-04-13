# Migrate task_io.py from PyYAML to ruamel.yaml

> **Owning task:** #827 — Migrate task_io.py from PyYAML to ruamel.yaml
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

After #818 extracts the kanban engine to `serve/kanban/`, the `owlbear_kanban` package depends on two YAML libraries: `ruamel.yaml` (used by `config_loader.py`) and `pyyaml` (used by `task_io.py`). Consolidating to `ruamel.yaml` removes one dependency.

**Key question:** What's the correct migration pattern for `task_io.py`, and what are the risks to YAML output format stability and round-trip fidelity?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/task_io.py` | Codebase | 1.0 — subject file; 3 PyYAML touchpoints |
| S2 | `serve/kanban/src/owlbear_kanban/config_loader.py` | Codebase | 1.0 — proven ruamel.yaml pattern in same package |
| S3 | `serve/kanban/pyproject.toml` | Codebase | 0.9 — current deps: pydantic, pyyaml, ruamel.yaml |
| S4 | `.owlbear/research/extract-engine-serve-kanban-818.md` §3.2 | Codebase | 1.0 — prior research identifying this migration |
| S5 | `tests/test_kanban_task_io.py` (60+ tests) | Codebase | 0.9 — round-trip, timestamp, encoding coverage |
| S6 | yaml.dev/doc/ruamel.yaml/basicuse/ | Web | 0.9 — safe/rt modes, StringIO dump pattern |
| S7 | yaml.dev/doc/ruamel.yaml/pyyaml/ | Web | 0.8 — YAML 1.1→1.2 differences (bool, octal, sexagesimal) |

## 3. Analysis

### 3.1 PyYAML Touchpoints in task_io.py

| Line | Usage | ruamel.yaml Equivalent |
|------|-------|----------------------|
| `import yaml` | Module import | `from ruamel.yaml import YAML` |
| `class _NoTimestampLoader(yaml.SafeLoader)` | Custom loader stripping timestamp resolver | `_make_yaml()` with resolver patching (config_loader pattern) |
| `yaml.load(str, Loader=_NoTimestampLoader)` | Parse frontmatter → dict | `y.load(str)` where y = `_make_yaml()` |
| `yaml.dump(data, ...)` | Dict → YAML string | `y.dump(data, StringIO())` then `.getvalue()` |

### 3.2 Migration Approach Comparison

| Criterion | A: `typ="safe"` | B: `typ="rt"` (round-trip) | C: Mixed (safe load, rt dump) |
|-----------|-----------------|---------------------------|-------------------------------|
| Key order | Sorts by default (PyYAML behavior) — needs workaround | Preserves insertion order ✓ | Load: plain dict; Dump: preserves order |
| Load return type | Plain `dict` ✓ | `CommentedMap` → needs `_to_plain()` | Plain `dict` for load |
| Consistency with config_loader | Differs (config uses rt) | Matches existing pattern ✓ | Inconsistent |
| Dump to string | StringIO wrapper needed | StringIO wrapper needed | StringIO wrapper needed |
| Timestamp resolver | Same patching pattern | Same patching pattern | Same patching pattern |
| Complexity | Low, but sort_keys workaround fragile | Low, `_to_plain()` is 5 lines | Medium — two YAML instances |
| **Score** | **.65** | **.85** | **.55** |

### 3.3 YAML 1.2 Behavioral Differences (Risk Assessment)

ruamel.yaml defaults to YAML 1.2; PyYAML uses YAML 1.1.

| Difference | Impact on Task Files | Risk |
|------------|---------------------|------|
| `Yes/No/On/Off` no longer boolean | Task files use `true/false` — no impact | None |
| Octal `052` → string (not int) | No numeric octals in task fields | None |
| Sexagesimal `12:34:56` removed | Timestamps are ISO 8601, already string-preserved | None |
| String quoting heuristics | Minor differences possible (e.g., titles with colons) | Low — semantic round-trip unaffected |

### 3.4 Test Coverage Assessment

| Test Area | Count | Migration Risk |
|-----------|-------|---------------|
| Round-trip (semantic model_dump equality) | 8 | Safety net — catches any data loss |
| Timestamp preservation (7-digit nanosecond) | 3 | Covered by resolver patching |
| Body content preservation | 5 | Unaffected — body is plain string extraction |
| Path containment / slug / filename | 20+ | Unaffected — no YAML involvement |
| Live board integration (700+ files) | 6 | Ultimate validation — catches edge cases |

60+ existing tests provide strong safety net. No new tests needed for the migration itself.

## 4. Recommendation

**Use `YAML(typ="rt")` with timestamp resolver stripping** — same pattern as `config_loader.py`.

Implementation:
1. Replace `import yaml` with `from ruamel.yaml import YAML` + `from io import StringIO`
2. Replace `_NoTimestampLoader` class (12 lines) with `_make_yaml()` function (8 lines) from config_loader pattern
3. In `read_task`: `_to_plain(y.load(frontmatter_str))` — adds 5-line `_to_plain()` helper
4. In `write_task`: `y.dump(data, stream)` via StringIO — replaces `yaml.dump()` call
5. Remove `pyyaml` from `serve/kanban/pyproject.toml` deps

Net code delta: ~0 lines (remove ~15, add ~15). Single-file change + pyproject.toml.

**Confidence: 0.85** — Proven pattern in same package, strong test coverage, low-risk YAML 1.2 differences. Minor risk: string quoting heuristic differences requiring test adjustment.

Challenge: FALLBACK — challenger subagent not available in researcher mode.

**Tier: T1 (autonomous)** — Refactor/cleanup. No new capability, no architecture change, no user-facing behavior change.

## 5. Follow-up Tasks

| # | Task | Status | Rationale |
|---|------|--------|-----------|
| 1 | Implement task_io.py PyYAML → ruamel.yaml migration | backlog | Single-file code change + pyproject.toml dep removal |

**Dependency note:** #827 depends on #818 (engine extraction), currently `in-progress`. Implementation should wait until #818 reaches `done`.
