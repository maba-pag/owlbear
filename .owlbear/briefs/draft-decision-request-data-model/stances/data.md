# Data Quality Stance — Decision Request Data Model

## Position

The decision request data model requires strict schema validation with kind-discriminated cross-field constraints, explicit YAML coercion protection on both read and write paths, and a clear separation between frontmatter-validated structured data and unvalidated markdown body.

## Schema and Validation Reasoning

### Core Models

```python
class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")
    author: str = Field(min_length=1, max_length=80, pattern=r"^\S.*\S$|^\S$")
    timestamp: datetime  # UTC, tz-aware required
    content: str = Field(min_length=1, max_length=500)

class Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    label: str = Field(min_length=1, max_length=120, pattern=r"^\S.*\S$|^\S$")
    recommended: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=500)

class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str  # validated by parent cross-field validator
    selected_option_id: str | None = None
    free_text: str | None = Field(default=None, max_length=2000)
    resolved_by: str = Field(min_length=1, max_length=80, pattern=r"^\S.*\S$|^\S$")
    resolved_at: datetime  # UTC, tz-aware required

class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID4
    task_id: str = Field(pattern=r"^\d{4,5}$")  # numeric kanban ID
    kind: Literal["decision", "action"]
    title: str = Field(min_length=1, max_length=120, pattern=r"^\S.*\S$|^\S$")
    summary: str = Field(min_length=1, max_length=500)
    agent: str = Field(min_length=1, max_length=80, pattern=r"^\S.*\S$|^\S$")
    created_at: datetime  # UTC, tz-aware required
    options: list[Option] = Field(default_factory=list, max_length=10)
    notes: list[Note] = Field(default_factory=list, max_length=20)
    resolution: Resolution | None = None
```

### Key Design Choices

**Body is NOT in the model.** The Pydantic model validates YAML frontmatter only. The engine pairs it with a separate `body: str` (the markdown below the YAML fence). Body is optional extended context — max 10,000 chars enforced at engine level, not schema level.

**`extra="forbid"` everywhere.** Unknown fields cause immediate validation failure. No silent field accumulation from agent typos or schema drift.

**String normalization.** Single-line fields use `pattern=r"^\S.*\S$|^\S$"` to reject leading/trailing whitespace and empty-looking strings. Multi-line fields (summary, rationale, content, free_text) allow internal newlines but enforce min_length.

**task_id is numeric.** Pattern `^\d{4,5}$` matches the kanban system's numeric task IDs. Not arbitrary strings.

### Kind-Discriminated Validation

```python
@model_validator(mode="after")
def validate_kind_constraints(self) -> Self:
    if self.kind == "decision":
        if len(self.options) < 2:
            raise ValueError("decision requests require >= 2 options")
        ids = [o.option_id for o in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate option_id within request")
        rec_count = sum(1 for o in self.options if o.recommended)
        if rec_count > 1:
            raise ValueError("at most one option may be recommended")
    elif self.kind == "action":
        if self.options:
            raise ValueError("action requests must not have options")
    if self.resolution:
        self._validate_resolution()
    return self

def _validate_resolution(self):
    r = self.resolution
    if self.kind == "decision":
        if r.status not in ("approved", "rejected"):
            raise ValueError(f"invalid decision resolution status: {r.status}")
        if r.status == "approved":
            valid_ids = {o.option_id for o in self.options}
            if r.selected_option_id not in valid_ids:
                raise ValueError("selected_option_id must reference a valid option")
        if r.status == "rejected" and r.selected_option_id is not None:
            raise ValueError("rejected decisions must not set selected_option_id")
    elif self.kind == "action":
        if r.status not in ("done", "rejected"):
            raise ValueError(f"invalid action resolution status: {r.status}")
        if r.selected_option_id is not None:
            raise ValueError("action resolutions must not set selected_option_id")
    if r.resolved_at < self.created_at:
        raise ValueError("resolved_at must not precede created_at")
```

## Required vs Optional Fields

| Field | kind=decision | kind=action | Notes |
|-------|:---:|:---:|-------|
| request_id | required | required | UUID4, also filename stem |
| task_id | required | required | Numeric kanban ID |
| kind | required | required | Discriminator |
| title | required | required | 1-120 chars, no leading/trailing whitespace |
| summary | required | required | 1-500 chars |
| agent | required | required | Creating agent identifier |
| created_at | required | required | UTC datetime |
| options | required, ≥2 | forbidden (empty) | Max 10 options |
| notes | optional (default []) | optional (default []) | Clarification thread |
| resolution | None when pending | None when pending | Populated on terminal resolve |
| body (markdown) | optional | optional | Extended context, max 10k chars |

## Resolution Payload

### Terminal States Only

| kind | status | selected_option_id | free_text | Semantics |
|------|--------|:---:|:---:|-----------|
| decision | `approved` | REQUIRED (valid option_id) | optional | User chose this option |
| decision | `rejected` | FORBIDDEN (None) | optional | User rejected all options |
| action | `done` | FORBIDDEN (None) | optional | Action approved/completed |
| action | `rejected` | FORBIDDEN (None) | optional | Action denied |

**`needs-info` is NOT a resolution status.** It is a non-terminal interaction modeled as a `Note` appended to the `notes` list. The request stays in `pending/`, the task stays blocked, and the creating agent sees the note via list/get. This avoids the "resolved but still blocking" contradiction and prevents body pollution.

### Resolution Fields

- `resolved_by`: who resolved (user identifier or agent name). Required, non-empty.
- `resolved_at`: UTC datetime. Must be ≥ created_at.
- `free_text`: optional user explanation. Max 2000 chars. Immutable once written.

## Confidence Representation

- **Range:** 0.0–1.0 inclusive. Float.
- **Semantics:** Independent viability assessment per option. NOT probabilities — no sum-to-1 constraint.
- **Validation:** `ge=0.0, le=1.0`. Required on every option (no default — forces explicit assessment).
- **Precision:** No artificial precision constraint. Store as-is.
- **Relationship to `recommended`:** Independent signals. `confidence` = how viable the agent believes the option is. `recommended` = the agent's explicit pick. They MAY diverge (high-confidence option not recommended due to complexity, etc.). At most one option carries `recommended=True`.

## Option ID Format

- **Pattern:** `^[a-z0-9][a-z0-9-]{0,62}$`
- **Max length:** 63 chars (DNS label convention — safe in filenames, URLs, YAML keys).
- **Character set:** lowercase alphanumeric + hyphens. No leading/trailing hyphens.
- **Uniqueness:** Within a single request only.
- **Source:** Agent-provided. Human-readable slugs, not UUIDs.
- **Examples:** `mcp-tools`, `hybrid-approach`, `option-a`, `keep-current`

## Temporal Fields

- **Format:** ISO 8601 with explicit `Z` suffix: `"2026-05-24T10:30:00Z"`
- **Storage:** Quoted strings in YAML frontmatter (prevents YAML date coercion).
- **Type:** `datetime` with `tzinfo=timezone.utc`. Pydantic validator rejects naive datetimes.
- **Read-path safety:** Engine MUST use a restricted YAML loader that disables implicit date/timestamp resolution (same pattern as task storage's custom loader). Writer-side quoting alone is insufficient for manually edited files.
- **Invariant:** `resolved_at >= created_at`

## Data Integrity Invariants

1. **Identity:** `request_id` is UUID4. Filename = `{request_id}.md`. Frontmatter request_id must match filename stem. Engine verifies on read.
2. **Uniqueness:** Guaranteed by `O_EXCL` atomic file creation in `pending/`. Since `resolved/` is only populated by moves from `pending/`, no cross-directory collision is possible. Direct creation in `resolved/` is forbidden by the engine API.
3. **Kind/options coupling:** `kind=decision` → `len(options) >= 2`. `kind=action` → `len(options) == 0`.
4. **Option ID uniqueness:** No duplicate `option_id` within a request.
5. **Recommendation uniqueness:** At most one option has `recommended=True`.
6. **Resolution cross-field rules:** Status determines which fields are required/forbidden (see table above).
7. **File location (eventual):** Resolved requests eventually reside in `resolved/`. During crash windows, a resolved-but-in-pending file is valid and the engine moves it on next sweep/startup.
8. **Temporal ordering:** `resolved_at >= created_at`.
9. **Immutability:** Once a file is in `resolved/`, the entire file (frontmatter + body) is frozen. No modifications. This is the audit trail.
10. **Cardinality:** Max 10 options, max 20 notes per request. Body max 10,000 chars.

## Malformed File Handling

Invalid on-disk files MUST NOT silently disappear. The engine defines a separate contract:

```python
class MalformedRequest(BaseModel):
    file_path: str  # relative path within decisions/
    request_id_guess: str | None  # from filename stem, may not be valid UUID
    errors: list[str]  # human-readable validation errors
```

The list operation returns `(valid: list[DecisionRequest], malformed: list[MalformedRequest])`. Cockpit renders malformed items with an error badge and displays the error list. This surfaces corruption to humans immediately rather than hiding it behind a 200 OK with missing items.

Failure modes and handling:
- **YAML parse failure:** MalformedRequest with parse error message.
- **Filename/request_id mismatch:** MalformedRequest — file is untrustworthy.
- **Schema validation failure:** MalformedRequest with Pydantic error details.
- **Unreadable file (permissions):** MalformedRequest with OS error.

## Key Trade-offs

| Decision | Trade-off | Justification |
|----------|-----------|---------------|
| `extra="forbid"` | Agents must know exact schema; no graceful field additions | Prevents silent drift. Schema changes are intentional, not accidental. |
| options forbidden for actions | Actions have no structured requester signal | Actions are permission requests — the summary IS the signal. Confidence only helps multi-option choices. |
| needs-info as Note, not Resolution | More complex model (notes list) | Eliminates "resolved but blocking" semantic contradiction. Clean terminal-only resolution. |
| Filename = UUID | Poor `ls` readability | Trivial lookup, no collision logic, self-verifying identity. Engine provides human-friendly list. |
| Restricted YAML loader | Custom code, not stdlib safe_load | Prevents coercion of `yes`/`no`/dates from manually edited files. Non-negotiable for data integrity. |
| Max 10 options | Limits expressiveness | Prevents unbounded frontmatter. 10 options already exceeds typical decision complexity. |
| Resolved file immutability | Cannot fix typos in resolved requests | Audit trail integrity. If correction needed, annotate the task, don't rewrite history. |

## Warnings

1. **YAML coercion is the #1 silent corruption vector.** Without a restricted loader, a manually edited `option_id: yes` becomes boolean `True`, and `created_at: 2026-05-24` becomes a date object without timezone. Both pass through silently. The restricted loader is not optional.

2. **Body content is unvalidated beyond length.** It can contain anything — the model intentionally does not parse it. Consumers must not extract structured meaning from body text (that was the old regex-extraction anti-pattern). All machine-readable data lives in frontmatter.

3. **`recommended` without `confidence` context is misleading.** If only one option has `recommended=True` but its confidence is 0.3, the recommendation is weak. Consumers should always display both signals together.

4. **Cross-directory uniqueness depends on the engine being the sole writer.** If external tools create files directly in `resolved/`, uniqueness guarantees break. The engine is the only sanctioned write path.

## Confidence

**0.82** — The model handles the known requirements cleanly. The needs-info-as-notes design is less battle-tested but avoids proven semantic contradictions. YAML safety requires implementation diligence but the pattern exists in the codebase. The action branch is intentionally thin — this is a correct simplification, not a gap.
