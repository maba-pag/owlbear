# Extract Generic JsonlStore Base Class

> **Owning task:** #465 — Extract generic JsonlStore base class
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

DRY-06 identified that UsageTracker, EventStore, and ErrorJournal each implement ~40 lines of identical append-only JSONL persistence: `mkdir + serialize + open("a")`, `exists + read_text + splitlines + deserialize`, and time/field-based query filtering. Should we extract a generic `JsonlStore[T]` base class, and if so, what design?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | LangChain `BaseStore[K, V]` | [stores.py](https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/stores.py) | .85 — `Generic[K, V]` ABC for key-value stores; shows TypeVar + abstract methods pattern for storage generics |
| 2 | `jsonlines` library | [jsonlines.readthedocs.io](https://jsonlines.readthedocs.io/en/latest/) | .70 — Standard JSONL reader/writer; shows line-oriented append pattern with custom `dumps`/`loads` callables |
| 3 | Pydantic `TypeAdapter` docs | [docs.pydantic.dev](https://docs.pydantic.dev/latest/concepts/type_adapter/) | .90 — `dump_json`/`validate_json` for arbitrary types; create once, reuse in loops |
| 4 | OwlBear codebase (3 stores) | Local: `memory/usage.py`, `core/observability.py`, `memory/error_journal.py` | 1.0 — The actual duplication under analysis |

## 3. Analysis

### 3.1 Duplication Matrix

| Method | UsageTracker | EventStore | ErrorJournal | Identical? |
|--------|-------------|-----------|-------------|------------|
| `__init__(path)` | Path arg | Path arg | Workspace → derived path | ~same |
| `path` property | 3 lines | 3 lines | 3 lines | **yes** |
| `append()` | mkdir + TypeAdapter.dump_json + open("a") | identical | mkdir + json.dumps + open("a") | **~yes** (serializer differs) |
| `load()` | exists + read_text + splitlines + validate_json | identical | exists + read_text + splitlines + json.loads | **~yes** (deserializer differs) |
| `query()` | datetime cutoff | ISO-string cutoff | field filters + last_n | **no** |
| `summary()` | domain-specific UsageSummary | domain-specific dict | N/A | **no** |
| Rotation | N/A | N/A | `_maybe_rotate()` | unique to ErrorJournal |

**Extractable:** `__init__`, `path`, `append`, `load` = ~25 lines per class (75 total → 25 shared).
**Not extractable:** `query`, `summary`, `tool_stats`, rotation — domain-specific logic.

### 3.2 Design Options

| Criterion | A: `Generic[T]` + TypeAdapter | B: Abstract with `serialize`/`deserialize` hooks | C: Standalone functions |
|-----------|-------------------------------|--------------------------------------------------|------------------------|
| Type safety | Full — `list[T]` return types | Full — subclass declares T | Loose — caller manages types |
| Pydantic coupling | Yes — requires BaseModel T | No — any serialization | No |
| ErrorJournal compat | Needs migration to BaseModel | Works as-is with json.dumps/loads hooks | Works as-is |
| LOC saved | ~50 (migrate EJ + extract) | ~50 (extract + hooks) | ~30 (less boilerplate removed) |
| KISS score | High — one adapter, no hooks | Medium — hook methods add indirection | Highest — no class hierarchy |
| YAGNI risk | Low — 3 known consumers | Low | Low |

### 3.3 ErrorJournal Migration Question

ErrorJournal uses raw `dict` + `json.dumps` instead of Pydantic BaseModel + TypeAdapter. Two paths:

1. **Migrate ErrorJournal to BaseModel** — Create `ErrorEntry(BaseModel)`, use TypeAdapter. Unifies serialization. Slightly more work but enables option A cleanly.
2. **Keep dict, use hooks** — Option B with `serialize()`/`deserialize()` abstract methods. ErrorJournal overrides with `json.dumps`/`json.loads`.

Given that ErrorJournal is the odd one out and Pydantic models are the project standard, migration (path 1) is cleaner long-term.

## 4. Recommendation (.85 confidence)

**Option A: `JsonlStore[T]` with TypeAdapter**, with ErrorJournal migrated to BaseModel.

Rationale:

- Strongest type safety — `append(T)` and `load() → list[T]` are fully typed
- Aligns with project convention (UsageTracker/EventStore already use TypeAdapter)
- ErrorJournal migration to BaseModel is small (~15 lines: create `ErrorEntry` model, replace `json.dumps`/`json.loads`)
- One `TypeAdapter[T]` per subclass, created at class level — matches Pydantic docs recommendation

### Proposed API

```python
class JsonlStore(Generic[T]):
    """Append-only JSONL persistence for Pydantic models."""

    def __init__(self, path: Path, record_type: type[T]) -> None: ...
    @property
    def path(self) -> Path: ...
    def append(self, record: T) -> None: ...  # mkdir + dump_json + open("a")
    def load(self) -> list[T]: ...  # exists + read_text + splitlines + validate_json
```

Subclasses add domain-specific methods (`query`, `summary`, `rotate`). File location: `src/owlbear/core/jsonl_store.py` — it's a core infrastructure utility used by both `core/` and `memory/`.

### Risks

| Risk | Mitigation |
|------|------------|
| ErrorJournal dict → BaseModel migration breaks callers | Existing tests cover all call sites; run full suite |
| TypeAdapter created per-instance instead of per-class | Pass `record_type` to `__init__`, create adapter once |
| Over-abstraction — YAGNI if no 4th store appears | 3 consumers already exist; base saves ~50 LOC; justified by DRY principle |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement JsonlStore[T] base class" --priority needed --tags "dry,refactor,scope:core" --description "Create src/owlbear/core/jsonl_store.py with Generic[T] base: __init__(path, record_type), path property, append(T), load()->list[T]. Uses TypeAdapter internally. TDD: test append/load/path/mkdir/empty-file edge cases. AC: base class exists; unit tests pass; no consumers yet."
kanban\kanban-md.exe create "Migrate ErrorJournal to BaseModel + JsonlStore" --priority needed --tags "dry,refactor,scope:core" --depends-on 465 --description "Create ErrorEntry(BaseModel) replacing raw dicts. Make ErrorJournal inherit JsonlStore[ErrorEntry]. Keep rotation and field-based query as overrides. AC: ErrorJournal uses JsonlStore; ErrorEntry is a BaseModel; existing tests pass unchanged; no raw json.dumps/loads in ErrorJournal."
kanban\kanban-md.exe create "Migrate UsageTracker to JsonlStore base" --priority needed --tags "dry,refactor,scope:core" --depends-on 465 --description "Make UsageTracker inherit JsonlStore[UsageRecord]. Remove duplicated append/load/path. Keep summary() and query() as domain methods. AC: UsageTracker inherits JsonlStore; no duplicated file I/O; existing tests pass."
kanban\kanban-md.exe create "Migrate EventStore to JsonlStore base" --priority needed --tags "dry,refactor,scope:core" --depends-on 465 --description "Make EventStore inherit JsonlStore[ObservabilityEvent]. Remove duplicated append/load/path. Keep summary(), tool_stats(), query() as domain methods. AC: EventStore inherits JsonlStore; no duplicated file I/O; existing tests pass."
```

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| LangChain BaseStore | <https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/stores.py> | Generic[K,V] ABC pattern for typed stores | JsonlStore design pattern | 2026-03-06 |
| jsonlines library | <https://jsonlines.readthedocs.io/en/latest/> | JSONL append/read patterns, custom serializer hooks | JsonlStore design validation | 2026-03-06 |
| Pydantic TypeAdapter | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | TypeAdapter dump_json/validate_json for Generic types | JsonlStore serialization approach | 2026-03-06 |
