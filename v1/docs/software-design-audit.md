# Software Design Audit — DRY / YAGNI / Modularity

> **Date:** 2025-07-14  **Scope:** `src/owlbear/` + `src/bearclaw/` (14 624 LOC, 112 files)

## Executive Summary

12 DRY violations, 5 YAGNI violations, 4 modularity issues. The largest systemic problem is the knowledge-infrastructure construction code duplicated across `bootstrap.py`, followed by three independent JSONL-store implementations sharing identical structure. Most violations are low-to-medium effort fixes (extract helper, add base class, or use constant).

---

## DRY Violations

### DRY-01 — Knowledge infrastructure double-build in bootstrap.py

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Files** | `src/owlbear/bootstrap.py` L276–365, L383–433 |
| **Duplicated LOC** | ~30 lines |

`_build_knowledge_toolset` and `_build_bookmark_toolset` both construct the same object graph: `owlbear_dir.mkdir()` → `sqlite3.connect()` → `init_db()` → `GraphStore` → `BgeM3EmbeddingProvider` → `QdrantVectorStore` → `EntityExtractor` → `TextChunker` → `IngestPipeline`. The imports, directory creation, DB connection, and pipeline assembly are near-identical.

**Recommendation:** Extract a `_build_knowledge_infra(workspace, chat_model) → KnowledgeInfra` helper that returns a dataclass/NamedTuple with all shared objects. Both builders call it and add their specific wiring.

---

### DRY-02 — `_emit_hook` copied across 3 toolsets

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/tools/git_local.py` L80, `tools/kanban.py` L85, `tools/github_api.py` L114 |
| **Duplicated LOC** | 4 lines × 3 = 12 lines |

Identical 4-line method:

```python
async def _emit_hook(self, tool_name: str, args: dict[str, object]) -> None:
    if self._hooks is not None:
        await self._hooks.emit(HookEvent.PRE_TOOL_USE, {"tool_name": tool_name, "args": args})
```

**Recommendation:** Add a `HookMixin` (or put the method on a `HookedFunctionToolset` base class) that all hook-aware toolsets inherit from.

---

### DRY-03 — `_safe_path` duplicated in 2 toolsets

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/tools/filesystem.py` L52, `tools/knowledge.py` L81 |
| **Duplicated LOC** | ~12 lines × 2 |

Same null-byte check, same `resolve()` logic, same `PermissionError` message. `knowledge.py` even has a comment: `# reuses FileToolset pattern`.

**Recommendation:** Extract to `owlbear.tools._path_utils.safe_path()` or a shared mixin.

---

### DRY-04 — Table formatting boilerplate 3× in cli.py

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/bearclaw/cli.py` L161–168, L492–499, L680–686 |
| **Duplicated LOC** | 8 lines × 3 = 24 lines |

Identical pattern each time:

```python
col_widths = [len(h) for h in headers]
for row in rows:
    for i, cell in enumerate(row):
        col_widths[i] = max(col_widths[i], len(cell))
fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
typer.echo(fmt.format(*headers))
typer.echo("  ".join("-" * w for w in col_widths))
```

**Recommendation:** Extract a `_print_table(headers, rows)` helper at module level.

---

### DRY-05 — `OwlBearSettings()` instantiated 12 times in cli.py

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/bearclaw/cli.py` L108, L185, L223, L362, L594, L735, L853, L869, L926, L1038, L1115, L1157 |
| **Instances** | 12 |

Every CLI command creates its own `OwlBearSettings()` from scratch. `pydantic-settings` re-reads environment variables and config each time.

**Recommendation:** Use Typer's `@app.callback()` to create a shared settings instance, or a module-level lazy singleton (e.g., `functools.lru_cache`).

---

### DRY-06 — JSONL store pattern implemented 3 separate times

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Files** | `src/owlbear/memory/usage.py` (UsageTracker), `core/observability.py` (EventStore), `memory/error_journal.py` (ErrorJournal) |
| **Duplicated LOC** | ~40 lines × 3 |

All three implement: `__init__(path)`, `append()` with `mkdir(parents=True)` + serialize + `open("a")`, `load()` / `_load_all()` with `exists()` check + `read_text` + `splitlines` + deserialize, `query(window)` with datetime cutoff. `ErrorJournal` additionally re-implements serialization with raw `json.dumps` instead of Pydantic's `TypeAdapter`.

**Recommendation:** Extract a generic `JsonlStore[T]` base class parameterized by record type. Subclasses provide schema and any custom query logic (rotation for `ErrorJournal`, aggregation for the others).

---

### DRY-07 — Toolset unwrapping loop duplicated 4× in production code

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/bootstrap.py` L691, L755, L848; `projects/toolset.py` L149 |
| **Instances** | 4 in production (+ 3 in tests) |

```python
inner = ts
while hasattr(inner, "wrapped"):
    inner = inner.wrapped
```

Used to peel `HookedToolset`/`ApprovalGateToolset` wrappers to find the inner toolset.

**Recommendation:** Add `unwrap(toolset) → AbstractToolset` utility function (e.g., in `tools/hooked.py` or a `tools/_utils.py` module).

---

### DRY-08 — String-based type dispatch 4× in bootstrap.py

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `src/owlbear/bootstrap.py` L692, L693, L757, L848 |
| **Instances** | 4 |

```python
if type(inner).__name__ == "ProjectToolset":
```

Fragile — breaks if class is renamed. All 4 sites use the pattern after the unwrap loop.

**Recommendation:** Use `isinstance()` checks (already importing the class) or register toolsets in a name→instance dict during construction.

---

### DRY-09 — `trafilatura.extract` used in 3 separate wrappers

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `tools/web_search.py` L204, `tools/browser/content_extractor.py`, `memory/knowledge/bookmark_pipeline.py` L190 |
| **Instances** | 3 |

Each call site wraps `trafilatura.extract()` with slightly different fallback logic and metadata handling.

**Recommendation:** Centralize in a shared `extract_text_content(html) → str` utility. Different callers only diverge in how they obtain the HTML, not in extraction.

---

### DRY-10 — `ingest()` and `_ingest_from_intake()` largely duplicate pipeline steps

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Files** | `src/owlbear/memory/knowledge/ingest.py` L259–370 vs L457–520 |
| **Duplicated LOC** | ~45 lines of pipeline steps (chunk → insert → embed/extract → process → status → hash → graph) |

`ingest()` performs intake + delta-check + the full pipeline inline. `_ingest_from_intake()` implements the same pipeline minus intake/delta-check. `ingest()` should delegate its post-intake steps to `_ingest_from_intake()` rather than reimplementing them.

**Recommendation:** Refactor `ingest()` to call `_ingest_from_intake()` after the intake and delta-check phases. The `ingest_text()` method already does this correctly — follow its pattern.

---

### DRY-11 — SELECT column list inlined 6× in source_store.py

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `src/owlbear/memory/knowledge/source_store.py` L93, L107, L120, L127, L140, L149 |
| **Instances** | 6 |

The string `"SELECT id, name, source_type, config, scope, enabled, priority, last_refreshed_at, last_error, created_at, updated_at"` is repeated in every query. `BookmarkStore` (same package) already uses a `_SELECT_COLS` constant — this file doesn't.

**Recommendation:** Define `_SELECT_COLS` constant and reference it in all queries, following the `BookmarkStore` pattern.

---

### DRY-12 — Hook `register()` method repeated across 9 hook classes

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `core/observability.py`, `core/command_guard.py`, `core/context_hook.py`, `core/lint_hook.py`, `core/notification_hook.py`, `core/subagent_hook.py`, `core/test_hook.py`, `core/escalation.py`, `tools/screenshot_hook.py` |
| **Instances** | 9 |

Each hook class has a `register(hooks: HookRegistry)` method that manually calls `hooks.register(HookEvent.X, self.handle)` for its events. No shared protocol or base class.

**Recommendation:** Define a `Hook` protocol or ABC with a `register(HookRegistry)` method and `events: ClassVar[list[HookEvent]]` so registration can be automated. Low priority — current approach is explicit and works.

---

## YAGNI Violations

### YAGNI-01 — `_register_tools` boilerplate in all 14 toolset classes

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | All 14 FunctionToolset subclasses (see DRY section for full list) |

Every toolset follows the same ceremony: `__init__` → `super().__init__()` → `self._register_tools()` → N × `self.add_function(self.method, name=..., description=...)`. The `_register_tools` method adds no value beyond grouping calls.

**Recommendation:** Consider a `@tool` decorator or `tools: ClassVar[list]` pattern that auto-registers methods, eliminating the boilerplate. Alternatively, accept the explicitness — this is borderline since PydanticAI's FunctionToolset doesn't provide a declarative API.

---

### YAGNI-02 — `EscalationHook` exists but is never wired

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/core/escalation.py` (entire file) |

`EscalationHook` is fully implemented (prompts user retry/skip/abort on errors) but is never imported or registered in `bootstrap.py`. It's an orphan — tested but unreachable in production.

**Recommendation:** Either wire it in bootstrap or delete it. Don't keep dead code.

---

### YAGNI-03 — Role system over-engineered for 2 roles

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `src/owlbear/core/roles.py` (100 lines) |

Full infrastructure (`AgentRole` enum, `RolePolicy` dataclass, `apply_role_policy()` function, `BUILDER_POLICY`, `VALIDATOR_POLICY`) exists to express: "validators cannot use `write_file` and `create_file`." That's a 2-element frozenset requiring 100 lines of framework.

**Recommendation:** Keep if you plan more roles soon. Otherwise, simplify to a `deny_tools(toolset, names)` utility function. Current approach is not wrong, just disproportionate.

---

### YAGNI-04 — `MemoryConsolidator` not integrated

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/memory/consolidation.py` |

`MemoryConsolidator` uses `model: str | Model = "test"` as its default — a test-scaffolding artifact. It is never imported or wired in `bootstrap.py` or the daemon. Tests exist in `test_consolidation.py`, but the feature is unreachable in production.

**Recommendation:** Wire it into the session lifecycle or remove it. Dead code with tests is still dead code.

---

### YAGNI-05 — `_make_refresh_orchestrator` stub in cli.py

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `src/bearclaw/cli.py` L374–384 |

```python
def _make_refresh_orchestrator(...):
    raise NotImplementedError
```

Exists "as a seam for test mocking" but always raises. If it's only a test seam, it should be in the test fixtures, not production code.

**Recommendation:** Remove from production code. Tests can mock the real function or use dependency injection.

---

## Modularity Issues

### MOD-01 — `cli.py` is a 1 274-line monolith

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Files** | `src/bearclaw/cli.py` |
| **LOC** | 1 274 |

Contains auth, browser, slack, project, usage, voice, knowledge-source, chat, and daemon subcommands in a single file. Adding features means growing the monolith.

**Recommendation:** Split into subcommand modules (`bearclaw/commands/auth.py`, `commands/knowledge.py`, etc.) and assemble via `app.add_typer()`.

---

### MOD-02 — `ingest.py` at 849 lines with internal duplication

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/memory/knowledge/ingest.py` |
| **LOC** | 849 |

The single `IngestPipeline` class handles: HTTP/file reading (intake), content hashing, chunking orchestration, document CRUD, embedding dispatch, entity extraction, graph enrichment, inter-doc graph building, and status tracking. It's a pipeline, but all stages live in one class.

**Recommendation:** After fixing DRY-10, consider extracting intake (already partially in `intake.py`) and reducing `IngestPipeline` to orchestration only.

---

### MOD-03 — `bootstrap.py` at 894 lines and growing

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Files** | `src/owlbear/bootstrap.py` |
| **LOC** | 894 |

Assembles all subsystems: channels, hooks, toolsets, MCP, agent registry, knowledge, bookmarks, projects. Each builder function is independent — they could be in separate modules.

**Recommendation:** Group builder functions into sub-modules (`bootstrap/hooks.py`, `bootstrap/toolsets.py`, `bootstrap/knowledge.py`) with a thin `bootstrap/__init__.py` orchestrator.

---

### MOD-04 — `knowledge/` package has 22 files without sub-packages

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Files** | `src/owlbear/memory/knowledge/` (22 .py files) |

The flat namespace mixes: schema/models, storage (graph, qdrant, source_store, bookmark), pipeline (ingest, chunker, extractor, embeddings), retrieval, toolsets, and builders. Navigation is difficult.

**Recommendation:** Create sub-packages: `knowledge/storage/`, `knowledge/pipeline/`, `knowledge/retrieval/`. Low priority — current flat layout works, just doesn't scale well.

---

## Quantitative Summary

| Metric | Count |
|--------|-------|
| Total findings | 21 |
| DRY violations | 12 |
| YAGNI violations | 5 |
| Modularity issues | 4 |
| High severity | 4 (DRY-01, DRY-06, DRY-10, MOD-01) |
| Medium severity | 10 |
| Low severity | 7 |
| Estimated duplicated LOC | ~250–300 lines |
| Dead/unwired production code | 3 modules (EscalationHook, MemoryConsolidator, _make_refresh_orchestrator) |

### Top-3 highest-impact fixes

1. **DRY-01 + DRY-06** — Knowledge infra helper + generic JSONL store → eliminates ~100 duplicated lines
2. **DRY-10** — Refactor `ingest()` to delegate to `_ingest_from_intake()` → eliminates ~45 duplicated lines, simplifies maintenance
3. **MOD-01** — Split `cli.py` into subcommand modules → unblocks parallel development, reduces cognitive load

---

## Follow-up Tasks

```
kanban\kanban-md.exe create "Extract _build_knowledge_infra helper in bootstrap.py" --priority needed --tags "dry,refactor,phase-10" --description "DRY-01: Extract shared knowledge infrastructure construction (owlbear_dir, conn, init_db, GraphStore, BgeM3, QdrantVectorStore, EntityExtractor, TextChunker, IngestPipeline) from _build_knowledge_toolset and _build_bookmark_toolset into a single _build_knowledge_infra() helper returning a NamedTuple. AC: both builders use the helper; no duplicated DB/embedding/pipeline construction; tests pass."

kanban\kanban-md.exe create "Extract generic JsonlStore base class" --priority needed --tags "dry,refactor,phase-10" --description "DRY-06: UsageTracker, EventStore, and ErrorJournal all implement identical append-only JSONL persistence. Extract a generic JsonlStore[T] base class with append/load/query. Subclasses provide schema. AC: all 3 stores inherit from JsonlStore; no duplicated file I/O code; existing tests pass."

kanban\kanban-md.exe create "Refactor ingest() to delegate to _ingest_from_intake()" --priority needed --tags "dry,refactor,knowledge" --description "DRY-10: ingest() reimplements the same pipeline steps as _ingest_from_intake(). After intake+delta-check, ingest() should call _ingest_from_intake() like ingest_text() already does. AC: ingest() delegates post-intake steps; no duplicated pipeline code; all ingest tests pass."

kanban\kanban-md.exe create "Split bearclaw/cli.py into subcommand modules" --priority important --tags "modularity,refactor,cli" --description "MOD-01: cli.py is 1274 lines with 8+ concern areas. Split into bearclaw/commands/{auth,browser,slack,project,knowledge_source,usage,voice,chat}.py. Wire via app.add_typer(). AC: cli.py < 200 lines; all CLI commands work; no functional regression."

kanban\kanban-md.exe create "Add unwrap() utility for toolset wrapper peeling" --priority important --tags "dry,refactor" --description "DRY-07+08: while hasattr(inner, 'wrapped') loop appears 4x in production + type(inner).__name__ string dispatch 4x. Add unwrap(toolset) and find_toolset(toolsets, cls) utilities. AC: all unwrap loops replaced; isinstance() used instead of string comparison; tests pass."

kanban\kanban-md.exe create "Extract _emit_hook and _safe_path into shared mixins" --priority nice-to-have --tags "dry,refactor,tools" --description "DRY-02+03: _emit_hook is identical in git_local/kanban/github_api (3×). _safe_path is identical in filesystem/knowledge (2×). Extract HookMixin._emit_hook and safe_path() utility. AC: no duplicated method bodies; all toolset tests pass."

kanban\kanban-md.exe create "Extract _print_table helper in bearclaw/cli.py" --priority nice-to-have --tags "dry,refactor,cli" --description "DRY-04: Table formatting col_widths boilerplate repeated 3x in cli.py. Extract _print_table(headers, rows). AC: single implementation; all 3 call sites use it."

kanban\kanban-md.exe create "Wire or remove EscalationHook and MemoryConsolidator" --priority important --tags "yagni,cleanup" --description "YAGNI-02+04: EscalationHook (core/escalation.py) and MemoryConsolidator (memory/consolidation.py) are fully implemented+tested but never wired in bootstrap.py. Either integrate them into the bootstrap pipeline or delete them with their tests. AC: no unreachable production code."

kanban\kanban-md.exe create "Lazy-singleton OwlBearSettings in cli.py" --priority nice-to-have --tags "dry,refactor,cli" --description "DRY-05: OwlBearSettings() instantiated 12 times in cli.py. Use Typer callback or functools.lru_cache to create once. AC: single construction point; all commands get same instance."

kanban\kanban-md.exe create "Add _SELECT_COLS constant to source_store.py" --priority nice-to-have --tags "dry,refactor,knowledge" --description "DRY-11: SELECT column list inlined 6 times. Follow BookmarkStore pattern with _SELECT_COLS constant. AC: single column-list definition; all queries reference it."
```
