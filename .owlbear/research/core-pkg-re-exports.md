# Re-export Validation for auth, planning, projects, providers, safety

> **Owning task:** #813 — Add re-exports to auth, planning, projects, providers, safety `__init__.py`
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

Task #813 implements the first slice of #549 (init-re-exports research). This validation
confirms the proposed exports still match the codebase and checks for circular import risk.

## 2. Sources

| Source | URL | Relevance |
|--------|-----|-----------|
| Parent research doc | `docs/research/init-re-exports.md` (#549) | 1.0 — full analysis, pattern comparison, export inventory |
| Python import system docs | <https://docs.python.org/3/reference/import.html#regular-packages> | .90 — `__init__.py` re-export semantics |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> | .95 — direct prior art with `__all__` tuple |
| OwlBear `core/__init__.py` | Local: `src/owlbear/core/__init__.py` | 1.0 — canonical internal template (15 re-exports) |

## 3. Validation Results

### 3.1 Export inventory confirmed

All 22 proposed exports verified present in source:

| Package | Module(s) | Exports | Count |
|---------|-----------|---------|-------|
| auth | copilot.py | `request_device_code`, `poll_for_access_token`, `exchange_for_copilot_token`, `load_or_refresh_token`, `save_token`, `load_token`, `derive_base_url` | 7 |
| planning | models.py, extractor.py, markdown.py | `ProjectDefinition`, `Requirement`, `ProjectDefinitionExtractor`, `project_definition_to_markdown` | 4 |
| projects | models.py, store.py, toolset.py, workspace.py | `Project`, `ProjectStore`, `ProjectToolset`, `ProjectWorkspace` | 4 |
| providers | copilot.py, copilot_multipliers.py | `create_copilot_client`, `create_copilot_model`, `get_premium_requests` | 3 |
| safety | policy.py, gate.py | `ApprovalGateToolset`, `ApprovalPolicy`, `ApprovalRule`, `ApprovalSession` | 4 |

### 3.2 Circular import risk: none

- No module in these 5 packages imports from its own package level (`from owlbear.{pkg} import ...`)
- Internal cross-module deps are one-directional: `planning.extractor` → `planning.models`, `safety.gate` → `safety.policy`
- Baseline test: `python -c "import owlbear.auth; ..."` passes for all 5 packages

### 3.3 Consumer count (deep imports to replace)

| Package | Deep import sites (src + bearclaw) |
|---------|-----------------------------------|
| auth | 2 |
| planning | 2 |
| projects | 17 |
| providers | 2 |
| safety | 3 |

### 3.4 Import order within `__init__.py`

For packages with intra-package deps, import order matters:

- **safety:** `policy.py` first (no deps), then `gate.py` (imports `policy`)
- **planning:** `models.py` first, then `extractor.py` (imports `models`), then `markdown.py`
- Others: single module or independent — order doesn't matter

## 4. Recommendation (.95 confidence)

Proceed with implementation as specified in AC. Zero risk — additive change, no circular
imports, matches proven `core/__init__.py` pattern. The 22-export scope is conservative.

## 5. Follow-up Tasks

Task #813 already has complete AC. No additional tasks needed — this is a validation
of existing research, not new research.
