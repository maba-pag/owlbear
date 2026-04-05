# Test: owlbear-project.json Generation — Research

> **Owning task:** #75 — Test: owlbear-project.json generation in setup script
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #75 is the TDD RED phase for #69 (owlbear-project.json generation). The test-writer needs: a target function signature, testing patterns for JSON file generation with Pydantic models, a strategy for deterministic time assertions, and a clear dependency chain so the model (#68) is available at import time.

**Key questions:** What function signature should tests target? How to test cross-platform paths and deterministic timestamps? What dependency is missing from #75?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pytest tmp_path fixture docs | <https://docs.pytest.org/en/stable/how-to/tmp_path.html> | .95 |
| 2 | Pydantic v2 serialization (model_dump_json) | <https://docs.pydantic.dev/latest/concepts/serialization/> | .90 |
| 3 | v1 test_cli_project.py (project scaffolding tests) | `v1/tests/test_cli_project.py` | .85 |
| 4 | v1 test_knowledge_models.py (Pydantic model tests) | `v1/tests/test_knowledge_models.py` | .80 |
| 5 | #69 research doc | `docs/research/setup-script-project-json-generation.md` | 1.0 |
| 6 | #68 research doc | `docs/research/owlbear-project-file-model-impl.md` | .95 |

## 3. Analysis

### 3.1 Missing Dependency — Critical Gap

Task #75 has **no `depends_on`**. The tests import `OwlbearProjectFile` from #68 for round-trip validation. Without explicit dependency, the pipeline could dispatch #75 before #68 is built, causing import failures (not useful test failures).

**Fix:** Add `depends_on: [68]` to #75.

### 3.2 Target Function Signature

The #69 AC and research (Source 5, §3.2–3.4) imply this signature:

```python
def generate_project_json(
    project_dir: Path, owlbear_dir: Path,
    *, name: str | None = None, project_type: str = "bare",
) -> Path:
```

Module: `mcp_project.setup` (or equivalent in `packages/mcp-project/`). Returns the path to the written file.

### 3.3 Test Pattern Comparison

| Pattern | Use for | Source |
|---------|---------|--------|
| `tmp_path` fixture | Filesystem isolation, temp dirs for project and owlbear paths | Source 1 |
| `monkeypatch` datetime | Deterministic `created_at` assertions | Source 3 (v1 pattern) |
| `json.loads(path.read_text())` | Raw JSON field assertions (schema_version, forward slashes) | Standard |
| `OwlbearProjectFile.model_validate_json()` | Round-trip validation — proves output is valid per model | Source 2, 6 |
| Pre-create file + assert unchanged | Idempotency testing | Source 5 §3.3 |

### 3.4 Test-to-AC Mapping

| Test Scenario | #69 AC | Technique |
|---------------|--------|-----------|
| Generates valid JSON with 5 fields | AC1 | `tmp_path`, assert 5 keys in parsed JSON |
| schema_version is 1 | AC2 | `json.loads()["schema_version"] == 1` |
| owlbear_path uses forward slashes | AC3 | Assert `"/" in path` and `"\\" not in path` |
| created_at is timezone-aware UTC | AC4 | `monkeypatch` + `AwareDatetime` parse check |
| Idempotent: no overwrite | AC5 | Write sentinel, call function, assert sentinel preserved |
| Validates against model | AC6 | `model_validate_json()` — no `ValidationError` |
| Name defaults to dir name | — | Call without `name`, assert JSON name == `tmp_path.name` |
| Type defaults to bare | — | Call without `project_type`, assert JSON type == "bare" |
| Explicit overrides | — | Pass name="custom", assert JSON reflects override |

### 3.5 Time Mocking Strategy

| Approach | Mechanism | KISS |
|----------|-----------|------|
| **`monkeypatch` on `datetime` (.85)** | Patch `datetime.now` in the target module | **High** — no extra deps |
| `freezegun` (.75) | `@freeze_time("2026-03-26T12:00:00Z")` | Medium — adds test dependency |

**Recommendation (.85):** Use `monkeypatch` — already available, no new dependency. The test-writer patches `datetime.now` in the target module namespace and asserts the JSON `created_at` matches the frozen time.

## 4. Recommendation (.85 confidence)

1. **Add `depends_on: [68]`** to #75 — the model must be importable before tests are written.
2. **Target function signature** documented above — test-writer imports from `mcp_project.setup`.
3. **Use `tmp_path`** for filesystem isolation (Sources 1, 3). Create sibling dirs: `project_dir = tmp_path / "my-project"`, `owlbear_dir = tmp_path / "owlbear"`.
4. **Use `monkeypatch`** for time freezing — no new dependency needed.
5. **Assert both raw JSON and model validation** — raw for specific fields, model for structural validity.
6. **Test cross-platform paths** by asserting forward slashes in `owlbear_path` value.

**Risks:**
- Function signature may change during architect review of #69 — test-writer should follow the AC, not this exact signature. Mitigation: tests assert behavior, not implementation details.
- Monorepo skeleton (#7) doesn't exist yet — test file location (`tests/`) depends on it. Mitigation: #68 already has transitive dependency on #7 via #41; by the time #75 is dispatched, the structure should exist.
