# Knowledge: SourceStore Implementation Research

> **Owning task:** #1870 — Knowledge: SourceStore implementation
> **Date:** 2025-05-25 **Status:** Complete

## 1. Context and Question

Implement `SourceStore` protocol against SQLite as the first greenfield store proving the pattern for the knowledge module. Key questions:

1. What table schema supports both ConfiguredSourceRecord and WishedSourceRecord in one table?
2. How to serialize/deserialize the SourceConfig discriminated union?
3. What implementation patterns apply (ensure_tables, ID generation, state transitions)?
4. Are there AC/protocol discrepancies requiring correction?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| SourceStore Protocol | `protocols/sources.py` | 1.0 — authoritative contract |
| ARCHITECTURE.md | `protocols/ARCHITECTURE.md` | .95 — "spec is authoritative, code conforms" |
| DESIGN_DECISIONS CP24/CP25 | `protocols/DESIGN_DECISIONS.md` | .90 — wish optionality + metadata merge |
| Existing source_store.py | `owlbear_knowledge/source_store.py` | .70 — old CRUD pattern (reference only) |
| Registry (TABLE_OWNERSHIP) | `protocols/registry.py` | .85 — prefix `source_*` |
| Pydantic TypeAdapter docs | pydantic.dev/docs/concepts/unions | .80 — discriminated union serialization |
| schema.py | `owlbear_knowledge/schema.py` | .75 — current centralized DDL pattern |

## 3. Analysis

### 3.1 AC vs Protocol Discrepancies (CRITICAL)

| AC Claim | Protocol Definition | Resolution |
|----------|-------------------|------------|
| `report_health` method name | `record_health` | Protocol wins — use `record_health` |
| `delete_source` idempotent on missing ID | Raises `LookupError` on missing ID | Protocol wins — raise `LookupError` |
| `SourceDeletionInfo.had_documents` | Field does not exist on model | Protocol wins — not needed |
| AC says `error_count` exposed | Not on boundary types | Internal column only (implementation detail) |

**Recommendation:** Update AC to match protocol before implementation.

### 3.2 Table Schema Design

Single table `source_registry` with nullable columns for state-specific fields:

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | uuid4().hex (32 chars) |
| name | TEXT NOT NULL | |
| state | TEXT NOT NULL | active/inactive/wished |
| scope | TEXT DEFAULT 'global' | |
| kind | TEXT | NULL for WISHED |
| fetch_method | TEXT | NULL for WISHED |
| config_json | TEXT | NULL for WISHED; JSON discriminated union |
| enrich | INTEGER | NULL for WISHED |
| refreshable | INTEGER | NULL for WISHED |
| priority | INTEGER DEFAULT 0 | |
| expected_kind | TEXT | NULL for CONFIGURED |
| expected_fetch_method | TEXT | NULL for CONFIGURED |
| reason | TEXT DEFAULT '' | |
| health | TEXT DEFAULT 'unknown' | |
| last_refreshed_at | TEXT | ISO datetime or NULL |
| last_checked_at | TEXT | ISO datetime or NULL |
| last_error | TEXT | NULL |
| error_count | INTEGER DEFAULT 0 | Internal; not on boundary |
| metadata_json | TEXT DEFAULT '{}' | JSON dict |
| created_at | TEXT NOT NULL | ISO datetime |
| updated_at | TEXT NOT NULL | ISO datetime |

**Unique constraint:** `(name, scope)` — enforces wish-promotion and registration conflict rules.

### 3.3 SourceConfig Serialization

```python
from pydantic import TypeAdapter

_CONFIG_ADAPTER = TypeAdapter(SourceConfig)
# Store: _CONFIG_ADAPTER.dump_json(config).decode()
# Load: _CONFIG_ADAPTER.validate_json(raw_json)
```

Discriminator `kind` in JSON ensures correct variant selection. Round-trip safe.

### 3.4 State Transition Validation

Valid transitions (from `SourceUpdate` docstring):

```
WISHED → ACTIVE, WISHED → INACTIVE
ACTIVE → INACTIVE
INACTIVE → ACTIVE
```

Invalid: ACTIVE → WISHED, INACTIVE → WISHED. Implementation uses a `_VALID_TRANSITIONS` set.

### 3.5 Implementation Pattern

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Location | `stores/sources.py` (new `stores/` package) | Task specifies this path |
| Constructor | `__init__(self, conn: sqlite3.Connection)` | Matches existing pattern |
| DDL | `ensure_tables()` method (CREATE IF NOT EXISTS) | Self-contained per AC |
| IDs | `uuid4().hex` | Existing codebase pattern |
| Timestamps | `datetime.now(UTC).isoformat()` | ISO strings in SQLite TEXT |
| Metadata merge | `{**existing, **update}` | CP25 shallow merge |
| Wish promotion | `register_source` checks name+scope for existing WISHED; supersedes | Protocol guarantee |
| Wish conflict | `register_wish` raises ValueError if name+scope exists ACTIVE | Protocol guarantee |

### 3.6 Testing Strategy

- In-memory `sqlite3.connect(":memory:")` fixtures
- Test matrix: all 4 SourceConfig types round-trip correctly
- State transition: valid passes, invalid raises ValueError
- CP25 metadata merge: key-level replace, absent keys preserved
- Wish promotion: register_source supersedes existing wish
- list_sources: filter by scope and/or state
- record_health: updates health + last_checked_at + last_error
- delete_source: raises LookupError on missing
- stats: counts match after operations
- ensure_tables idempotent: calling twice doesn't error

## 4. Recommendation

**Confidence: .90** — Straightforward implementation. Protocol is well-specified. Single risk: AC text contains 4 discrepancies vs. authoritative protocol.

**Action:** Fix AC discrepancies (protocol wins), then proceed with greenfield implementation at `stores/sources.py`. Pattern is proven by existing `source_store.py` (simpler CRUD) and Pydantic TypeAdapter handles discriminated union serialization cleanly.

Challenge: PROCEED — no architectural risk. Implementation is mechanical against a fully-specified protocol.

## 5. Follow-up Tasks

1. Fix AC discrepancies on #1870 (report_health → record_health, delete idempotency, had_documents)
2. Implement SourceStore at `stores/sources.py` with ensure_tables() and full protocol coverage
3. Write test suite `test_source_store_{task_id}.py`
