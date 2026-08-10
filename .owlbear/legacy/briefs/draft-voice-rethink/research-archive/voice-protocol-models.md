# Voice Protocol Pydantic Models — Implementation Research

> **Owning task:** #61 — Implement voice protocol Pydantic models
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #61 implements the Pydantic models for the voice addon NDJSON protocol (7 message types in 2 union types). The protocol design was completed in #49 (see `docs/research/voice-stdio-protocol.md` S3.3, S3.7). This research validates the implementation approach, identifies dependency gaps, and refines AC.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Pydantic v2 Unions docs | <https://docs.pydantic.dev/latest/concepts/unions/> | .95 — `Literal` discriminator + `Field(discriminator=...)` pattern |
| 2 | Pydantic v2 TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | .90 — `validate_json()` / `dump_json()` API, perf note (create once) |
| 3 | MCP Python SDK `_types.py` | <https://github.com/modelcontextprotocol/python-sdk> | .95 — `type: Literal["text"]` on content models, `TypeAdapter[Union]` at module level |
| 4 | v1 `JsonlStore` + `SessionStore` | Local: `v1/src/owlbear/core/jsonl_store.py`, `v1/src/owlbear/memory/session.py` | .90 — project-internal TypeAdapter NDJSON pattern |
| 5 | v1 `test_pydantic_messages.py` | Local: `v1/tests/test_pydantic_messages.py` | .85 — round-trip testing pattern for discriminated unions |
| 6 | Voice stdio protocol design | `docs/research/voice-stdio-protocol.md` S3.3, S3.7 | .95 — authoritative message type catalog |

## 3. Analysis

### 3.1 Pattern Validation

All sources converge on the same pattern for tagged message unions:

| Aspect | MCP SDK (Source 3) | v1 Codebase (Source 4) | Pydantic Docs (Source 1) |
|--------|--------------------|------------------------|--------------------------|
| Discriminator field | `type: Literal["text"] = "text"` | `kind` (PydanticAI internal) | `pet_type: Literal['cat']` |
| Union construction | `TypeAlias = A \| B \| C` | `TypeAdapter(ModelMessage)` | `Annotated[Union[...], Field(discriminator=...)]` |
| Serialization | `model_dump_json()` | `adapter.dump_json(record)` | `adapter.dump_json()` |
| Deserialization | `adapter.validate_json(data)` | `adapter.validate_json(line)` | `adapter.validate_json()` |
| Adapter scope | Module-level constant | Module-level / instance | "Create once, reuse" (Source 2) |

The voice protocol should use `Annotated[Union, Field(discriminator="type")]` with module-level `TypeAdapter` instances. This matches both MCP SDK and v1 codebase patterns exactly.

### 3.2 API Surface: model_dump_json vs TypeAdapter.dump_json

Two serialization paths exist in Pydantic v2:

| Method | Returns | Available on |
|--------|---------|-------------|
| `model.model_dump_json()` | `str` | BaseModel instances |
| `adapter.dump_json(model)` | `bytes` | TypeAdapter instances |

The AC says "Serialize via `model_dump_json()`" — this is correct and simpler. `model_dump_json()` returns `str`, which is ready for `stdin.write(msg + "\n")`. No `.decode()` step needed. Both v1 (`SessionStore.append`) and MCP SDK use the `TypeAdapter.dump_json()` path, but for voice the per-model `.model_dump_json()` is cleaner since we always know the concrete type when sending.

For deserialization, `TypeAdapter.validate_json()` is mandatory because we receive raw JSON and need the union discriminator to select the concrete type. Accepts both `str` and `bytes`.

### 3.3 Dependency Gap: Monorepo Skeleton

The AC specifies `src/owlbear/voice/protocol.py`. In the v2 monorepo layout this resolves to `packages/orchestrator/src/owlbear/voice/protocol.py`. But task #7 (monorepo skeleton) is at `ideation` — no package structure exists. **#61 must depend on #7.**

### 3.4 Model Design Recommendations

Based on MCP SDK (Source 3) and Pydantic docs (Sources 1–2):

- **`frozen=True`** on all models — protocol messages are immutable value objects. MCP SDK uses `ConfigDict` on its base `MCPModel`. For voice, set `model_config = ConfigDict(frozen=True)` on a `VoiceMsg` base or on each model.
- **`VoiceState` type alias** — `Literal["ready", "listening", "speaking", "idle", "shutdown"]` used by StatusMsg. Define as type alias for reuse.
- **Module-level adapters** — `_out_adapter = TypeAdapter(VoiceOutMessage)` and `_in_adapter = TypeAdapter(VoiceInMessage)` created once (Source 2 perf note).
- **No base class needed** — 7 flat models with a shared `type` field is simpler than a base class hierarchy. KISS.

### 3.5 Testing Approach

Following v1 `test_pydantic_messages.py` (Source 5):

| Test category | Count | Pattern |
|---------------|-------|---------|
| Round-trip per message type | 7 | `model_dump_json()` then `adapter.validate_json()` preserves all fields |
| Discriminator field present | 7 | Serialized JSON contains correct `"type"` value |
| Union selects correct model | 7 | `validate_json()` returns correct concrete type via `isinstance()` |
| Unknown type rejection | 2 | `{"type":"unknown"}` raises `ValidationError` for both unions |
| Missing required fields | 2 | Omit required field, expect `ValidationError` |

Total: ~25 tests. No mocks needed — pure data models.

## 4. Recommendation (.90 confidence)

**Proceed with the approach from voice-stdio-protocol.md S3.7**, validated by Pydantic docs and MCP SDK patterns. No alternative designs considered — the pattern is well-established and KISS.

**AC refinements for architect:**
- Add `depends_on: [7]` — monorepo skeleton must exist
- Clarify location: `packages/orchestrator/src/owlbear/voice/protocol.py`
- Add: `frozen=True` on all protocol models (immutable value objects)
- Add: Module-level `TypeAdapter` instances, one per union
- Add: `VoiceState` type alias for status message states

**Risk:** Location AC may shift if architect decides protocol models should live in the owlbear-voice addon package instead of the orchestrator. Both sides need the models; MCP SDK precedent favors a shared types module in the core package.

## 5. Follow-up Tasks

No new tasks needed — #61 was already decomposed from #49. The only change is adding the dependency.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Pydantic v2 Unions docs | <https://docs.pydantic.dev/latest/concepts/unions/> | Literal discriminator + Field(discriminator) pattern | Voice protocol model design | 2026-03-27 |
| Pydantic v2 TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | validate_json/dump_json API, create-once perf note | Voice protocol serialization approach | 2026-03-27 |
| MCP Python SDK types | <https://github.com/modelcontextprotocol/python-sdk> | type: Literal[...] on content models, module-level TypeAdapter unions | Pattern validation for protocol models | 2026-03-27 |
