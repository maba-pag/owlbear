# Test: OwlbearProjectFile Pydantic Model — Research Validation

> **Owning task:** #74 — Test: OwlbearProjectFile Pydantic model
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #74 is a TDD RED test task for the `OwlbearProjectFile` Pydantic model (#68). The model spec is settled (docs/research/owlbear-project-json-schema.md §3.7) and implementation research complete (docs/research/owlbear-project-file-model-impl.md §3.5). This research validates the test scenarios, resolves the test file location, confirms dependencies, and identifies gaps.

**Key questions:** Where should the test file live? Does #74 need a dependency on #41? Are the 9 test scenarios complete?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Pydantic v2 AwareDatetime docs | <https://docs.pydantic.dev/latest/api/standard_library_types/#datetime-types> | .95 |
| 2 | Pydantic v2 Literal validation | <https://docs.pydantic.dev/latest/api/standard_library_types/#literals> | .85 |
| 3 | v1 test_project_model.py | v1/tests/test_project_model.py | .90 |
| 4 | v1 test_project_definition_models.py | v1/tests/test_project_definition_models.py | .90 |
| 5 | v1 test_knowledge_models.py | v1/tests/test_knowledge_models.py | .85 |
| 6 | Schema spec | docs/research/owlbear-project-json-schema.md §3.7 | 1.0 |
| 7 | Implementation research | docs/research/owlbear-project-file-model-impl.md §3.5 | .95 |
| 8 | Sibling test tasks (#65, #66, #67) | kanban tasks | .80 |

## 3. Analysis

### 3.1 Test file location

| Option | Location | Convention match | KISS |
|--------|----------|-----------------|------|
| **A: Package-local (.85)** | `packages/mcp-project/tests/test_models.py` | v2 pattern (siblings #65–#67) | **High** |
| B: Root tests/ (.70) | `tests/test_owlbear_project_file.py` | v1 pattern | Medium |

**Recommendation (.85):** Option A. All sibling test tasks place tests inside the package's `tests/` dir. Import path: `from mcp_project.models import OwlbearProjectFile` (produces `ImportError` in RED, as expected).

### 3.2 Dependency chain

| Task | Current depends_on | #74 needs it? | Reason |
|------|--------------------|---------------|--------|
| #7 (monorepo) | — | Yes (transitive) | Creates `packages/` dir |
| #41 (scaffold) | [7, 67] | **Yes (direct)** | Creates `packages/mcp-project/tests/` dir |

**Gap:** #74 has no `depends_on`. Should add `depends_on: [41]`. This produces a clean TDD chain: `#41 (scaffold) → #74 (RED tests) → #68 (GREEN impl)`. Without this, the test-writer could be dispatched before the package structure exists.

### 3.3 Scenario gap analysis

Reference model from docs/research/owlbear-project-file-model-impl.md §4:

```
schema_version: int = Field(ge=1, le=1)
name: str = Field(min_length=1, max_length=100)
type: Literal["bare", "python-uv", "python-pip", "node"]
owlbear_path: str = Field(min_length=1)
created_at: AwareDatetime
```

| # | Scenario | Coverage | Status |
|---|----------|----------|--------|
| 1 | Valid construction with all 5 fields | Happy path | ✓ |
| 2 | Extra fields preserved (model_extra) | extra='allow' | ✓ |
| 3 | Invalid schema_version (0, 2, -1) | ge/le constraints | ✓ |
| 4 | Empty name / >100 chars | min/max length | ✓ |
| 5 | Invalid type enum value | Literal rejection | ✓ |
| 6 | Empty owlbear_path | min_length=1 | ✓ |
| 7 | Naive datetime rejected | AwareDatetime (Source 1) | ✓ |
| 8 | Invalid datetime string | Type validation | ✓ |
| 9 | model_validate_json round-trip | Serialization | ✓ |
| 10 | **Missing required field raises** | Required field check | **GAP** |
| 11 | **Each valid type value accepted** | Positive Literal check | **GAP (minor)** |

**Gap 10 (required):** v1/tests/test_project_definition_models.py (Source 4) tests each required field individually (`test_missing_name_raises`, etc.). This catches regressions if someone accidentally adds a default to a required field. Add one parametrized scenario covering all 5 fields.

**Gap 11 (minor):** No explicit check that each valid `type` value (`"bare"`, `"python-uv"`, `"python-pip"`, `"node"`) is accepted. A parametrized test strengthens coverage and serves as living documentation of the enum values.

### 3.4 AwareDatetime test pattern

Pydantic docs (Source 1) confirm `AwareDatetime` "requires the input to have a timezone." Naive datetime `datetime(2026, 3, 26, 19, 0, 0)` (no tzinfo) will raise `ValidationError`. String `"2026-03-26T19:00:00"` (no TZ offset) will also fail. Both cases should be tested.

## 4. Recommendation (.90 confidence)

All 9 existing scenarios are valid. Add 2 scenarios (missing-required-field parametrized test + valid-type-values parametrized test) to strengthen coverage. Place tests in `packages/mcp-project/tests/test_models.py`. Add `depends_on: [41]` to #74.

No new follow-up tasks needed — #74 is itself the follow-up from #68 research.

## 5. Task Updates

- Add `depends_on: [41]` to #74 (dependency chain: #41 → #74 → #68)
- Add two test scenarios to #74 body: missing required field + valid type values
