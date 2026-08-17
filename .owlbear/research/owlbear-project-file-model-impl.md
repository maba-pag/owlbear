# OwlbearProjectFile Pydantic Model — Implementation Research

> **Owning task:** #68 — Implement OwlbearProjectFile Pydantic model in mcp-project
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #68 implements the `OwlbearProjectFile` Pydantic model defined in the schema spec (docs/research/owlbear-project-json-schema.md, task #53). The schema is settled; this research validates the implementation approach, identifies AC gaps, resolves dependency ordering, and recommends specific Pydantic v2 APIs.

**Key questions:** Should `created_at` use `AwareDatetime` or bare `datetime`? How deep should `owlbear_path` validation go? What's the correct dependency chain? Does #68 need a dedicated TDD test task?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Pydantic v2 Models docs | <https://docs.pydantic.dev/latest/concepts/models/> | .95 |
| 2 | Pydantic v2 Fields docs | <https://docs.pydantic.dev/latest/concepts/fields/> | .90 |
| 3 | Pydantic v2 Standard Library Types — Datetimes | <https://docs.pydantic.dev/latest/api/standard_library_types/#datetime-types> | .95 |
| 4 | Schema spec (owning research) | docs/research/owlbear-project-json-schema.md | 1.0 |
| 5 | v1 Project model | v1/src/owlbear/projects/models.py | .85 |
| 6 | Sibling scaffold patterns (#39, #40, #41) | kanban tasks #65, #66, #67 | .80 |

## 3. Analysis

### 3.1 `created_at` — `AwareDatetime` vs bare `datetime`

| Approach | Behavior | Schema spec alignment | KISS |
|----------|----------|----------------------|------|
| **`AwareDatetime` (.90)** | Rejects naive datetimes; requires timezone info | Matches spec: "ISO 8601 datetime with timezone" | High — single import from pydantic |
| `datetime` (.65) | Accepts both aware and naive datetimes | Allows invalid values (naive datetimes without TZ) | Medium — requires custom validator to enforce TZ |

**Recommendation (.90):** Use `AwareDatetime` from `pydantic`. It is a built-in Pydantic type (Source 3) that enforces timezone presence without custom validators. The schema spec (Source 4, §3.3) explicitly requires "ISO 8601 datetime with timezone". A bare `datetime` would silently accept `2026-03-26T19:00:00` (no TZ), violating the spec. `AwareDatetime` catches this at validation time. Import: `from pydantic import AwareDatetime`.

### 3.2 `owlbear_path` validation depth

| Approach | Validation | Catches | KISS |
|----------|-----------|---------|------|
| **A: `min_length=1` only (.80)** | Non-empty string | Empty paths | **High** |
| B: + absolute path rejection (.75) | A + startswith('/') or drive letter check | Absolute paths | Medium |
| C: + `..` traversal check (.60) | B + reject `..` segments | Directory traversal | Low — platform-dependent, fragile |

**Recommendation (.80):** Option A for the model itself. The schema spec (Source 4, §3.3) mentions "no absolute paths or `..` traversal" but this is a *documentation convention*, not a validation requirement. The setup script (#12) controls what gets written; the model validates structure, not business rules. Adding path traversal checks to the Pydantic model mixes concerns. If path safety becomes a concern, add a separate `@field_validator` in a follow-up. KISS and YAGNI apply.

The AC says "owlbear_path non-empty" — `min_length=1` satisfies this. The architect should confirm if richer validation is needed during architecture review.

### 3.3 JSON-first patterns

The model reads from `owlbear-project.json`. Pydantic v2's `model_validate_json()` (Source 1) is faster than `json.loads()` + `model_validate()` because it avoids the intermediate dict. The builder should use `model_validate_json(path.read_text())` in the server resource handler (#41, AC7). This is a consumer concern, not a model concern — no model changes needed.

### 3.4 Dependency chain

| Task | Status | Required by #68? | Reason |
|------|--------|------------------|--------|
| #7 (monorepo skeleton) | ideation | Yes (transitive) | Creates `packages/` dir |
| #41 (scaffold mcp-project) | backlog | **Yes (direct)** | Creates `packages/mcp-project/src/mcp_project/` |
| #53 (schema spec) | archived | No (already done) | Schema is defined |

**Gap:** Task #68 has no `depends_on` set. It must depend on #41 (which already depends on #7). Without this, the builder has no package to put the model in.

### 3.5 TDD test task

Following the established pattern (#39→#65, #40→#66, #41→#67), task #68 needs a dedicated TDD RED test task. Test scenarios from AC:

1. Valid model construction with all fields
2. Extra fields preserved (`extra='allow'` verified via `model_extra`)
3. Invalid `schema_version` (0, 2, -1) rejected
4. Empty name rejected; name >100 chars rejected
5. Invalid type enum value rejected
6. Empty `owlbear_path` rejected
7. Naive datetime (no timezone) rejected
8. Invalid datetime string rejected
9. `model_validate_json()` round-trip works

## 4. Recommendation (.90 confidence)

Use `AwareDatetime` for `created_at` (enforces the spec's timezone requirement with zero custom code). Keep `owlbear_path` validation simple (`min_length=1`). Add `depends_on: [41]` to #68. Create a TDD RED test task for adversarial testing.

**Refined reference model:**

```python
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from typing import Literal


class OwlbearProjectFile(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: int = Field(ge=1, le=1)
    name: str = Field(min_length=1, max_length=100)
    type: Literal["bare", "python-uv", "python-pip", "node"]
    owlbear_path: str = Field(min_length=1)
    created_at: AwareDatetime
```

**Risk:** `AwareDatetime` is `pydantic>=2.0` (already satisfied: project uses `>=2.10.0`).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Test: OwlbearProjectFile Pydantic model" --priority needed --status ideation --tags "phase-1,scope:mcp,test" --body "## Objective\nTDD RED phase: write failing tests for OwlbearProjectFile model before builder implements.\n\n## Test Scenarios\n- [ ] Valid model construction with all 5 required fields\n- [ ] Extra fields preserved (extra='allow' verified via model_extra)\n- [ ] Invalid schema_version (0, 2, -1) rejected\n- [ ] Empty name rejected; name >100 chars rejected\n- [ ] Invalid type enum value rejected\n- [ ] Empty owlbear_path rejected\n- [ ] Naive datetime (no timezone) rejected\n- [ ] Invalid datetime string rejected\n- [ ] model_validate_json round-trip works\n\n## Context\nParent impl task: #68.\nSee docs/research/owlbear-project-file-model-impl.md for implementation details.\nModel spec: docs/research/owlbear-project-json-schema.md §3.7."
```
