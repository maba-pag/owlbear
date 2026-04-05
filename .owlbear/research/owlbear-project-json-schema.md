# Owlbear Project JSON Schema

> **Owning task:** #53 - Define owlbear-project.json schema specification
> **Date:** 2026-03-27
> **Status:** Complete

## 1. Context and Question

Task #53 defines the canonical `owlbear-project.json` schema shared by:

- setup script task #12 (writes the file)
- mcp-project scaffold task #41 (reads the file)
- mcp-project server task #17 (consumes the file via resources/tools)

The goal is one stable contract that is strict for required fields but flexible for additive metadata.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Scaffold research | docs/research/scaffold-mcp-project-server.md | .95 |
| 2 | Task #12 AC | kanban/tasks/012-bootstrap-owlbear-setup-script.md | .90 |
| 3 | Task #17 AC | kanban/tasks/017-build-mcp-project-server.md | .90 |
| 4 | JSON Schema Draft 2020-12 | <https://json-schema.org/draft/2020-12/json-schema-core.html> | .80 |

## 3. Schema Specification

### 3.1 Canonical fields

The file has five required fields:

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `schema_version` | integer | Must be `1` for current schema | Integer-only versioning strategy |
| `name` | string | Non-empty, max 100 chars | Human-readable project name |
| `type` | enum (string) | One of `bare`, `python-uv`, `python-pip`, `node` | Project template/type |
| `owlbear_path` | string | Non-empty relative path | Relative path from workspace root to owlbear install |
| `created_at` | string (ISO 8601) | RFC 3339 / ISO 8601 timestamp with timezone | Project creation timestamp |

### 3.2 Versioning strategy

- Use integer `schema_version`.
- Initial version is `1`.
- Version increases only for breaking schema changes.
- Additive non-breaking fields do not require a version bump.

Rationale: integer versioning is simple (KISS), easy to validate, and sufficient for current scope.

### 3.3 Validation rules

- All five canonical fields are required.
- Per-field constraints:

| Field | Rule |
|-------|------|
| `schema_version` | Integer and exactly `1` |
| `name` | String with `minLength: 1`, `maxLength: 100` |
| `type` | String enum: `bare`, `python-uv`, `python-pip`, `node` |
| `owlbear_path` | Non-empty string; consumers treat it as relative path |
| `created_at` | String with `format: date-time` (ISO 8601) |

### 3.4 Forward compatibility

Schema is open:

- `additionalProperties: true`
- Unknown fields are preserved/ignored by consumers

Rationale: allows additive metadata without breaking older writers/readers.

### 3.5 Location convention

`owlbear-project.json` lives at the project workspace root.

- Writer: setup script (#12)
- Readers: mcp-project scaffold/server (#41, #17)

Path is intentionally fixed to avoid discovery ambiguity for MCP resource handlers.

### 3.6 Example file

```json
{
  "schema_version": 1,
  "name": "my-project",
  "type": "python-uv",
  "owlbear_path": "../owlbear",
  "created_at": "2026-03-27T02:30:00Z"
}
```

### 3.7 Reference JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OwlbearProjectFile",
  "type": "object",
  "required": [
    "schema_version",
    "name",
    "type",
    "owlbear_path",
    "created_at"
  ],
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "type": {
      "type": "string",
      "enum": ["bare", "python-uv", "python-pip", "node"]
    },
    "owlbear_path": {
      "type": "string",
      "minLength": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": true
}
```

## 4. Implementation Mapping

Recommended Pydantic v2 mapping for task #68:

- `schema_version: int = Field(ge=1, le=1)`
- `name: str = Field(min_length=1, max_length=100)`
- `type: Literal["bare", "python-uv", "python-pip", "node"]`
- `owlbear_path: str = Field(min_length=1)`
- `created_at: AwareDatetime`
- model config `extra="allow"`

## 5. Follow-up Tasks

1. #68 Implement OwlbearProjectFile Pydantic model in mcp-project
- Priority rationale: needed by setup script and server consumers
- Dependency: #41 scaffold package
- One-line AC: create Pydantic model enforcing this schema

2. #69 Add owlbear-project.json generation to setup script
- Priority rationale: required producer of canonical file
- Dependency: #68 model
- One-line AC: setup writes valid root-level file matching this schema

Create commands used:

```powershell
kanban\kanban-md.exe create --title "Implement OwlbearProjectFile Pydantic model in mcp-project" --status ideation --priority needed --tags "phase-1,scope:mcp"
kanban\kanban-md.exe create --title "Add owlbear-project.json generation to setup script" --status ideation --priority needed --tags "phase-1,scope:cli"
```

Created task IDs:

- #68
- #69
