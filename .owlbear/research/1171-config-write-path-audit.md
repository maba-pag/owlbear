# Config Write Path Audit

> **Owning task:** #1171 — Audit and unify config write paths before schema grouping
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

#1155 research identified three independent config-writing paths with divergent
assumptions. Before schema grouping can proceed, these must agree on grouped
output format. This audit inventories each path's behavior, identifies the
actual divergences, and recommends a unification strategy.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `config_loader.py` L56-130 (save_config + _merge_into) | Internal | 1.0 |
| `storage.py` L236-260 (save_config) | Internal | 1.0 |
| `migrate.py` L367-510 (_migrate_config) | Internal | 1.0 |
| `storage.py` L545-557 (allocate_next_id — sole production caller) | Internal | 1.0 |
| `models.py` L137-240 (BoardConfig + model_dump behavior) | Internal | 0.9 |
| `.owlbear/research/1155-config-schema-grouping-validation.md` | Internal | 0.9 |
| `.owlbear/research/1114-config-yml-schema-grouping.md` | Internal | 0.8 |
| grep: `config_loader import` across serve/ and tests/ | Internal | 1.0 |

## 3. Analysis

### Path Inventory

| Aspect | config_loader.save_config | storage.save_config | migrate._migrate_config |
|--------|--------------------------|--------------------|-----------------------|
| Location | config_loader.py L56-75 | storage.py L236-260 | migrate.py L367-510 |
| **Status** | **DEAD CODE — zero callers** | Active (1 prod, 3 test) | Active (migration CLI) |
| Signature | `(kanban_dir, config)` | `(config, kanban_dir)` | `(kanban_dir, *, dry_run)` |
| Strategy | Read-modify-write | Atomic full rewrite | Build from scratch |
| YAML comments | Preserved (_merge_into) | Lost (new CommentedMap) | Lost (new CommentedMap) |
| Legacy key strip | None — preserves all | Strips: board, version, defaults, activity_log | Strips all legacy, emits flat Brief-C only |
| Crash safety | No (direct file.write) | Yes (atomic_write) | Yes (atomic_write) |
| frozenset handling | None (would crash on archival_reasons) | Converts to sorted list | N/A (hardcodes list) |
| Nested dict support | Yes (_merge_into recurses) | Implicit (model_dump produces nested dicts) | No (flat keys only) |
| Tests for write func | Zero | 3 tests | Covered by migration lane tests |

### Critical Finding: config_loader.save_config Is Dead Code

Zero imports of `save_config` from `config_loader` exist in the entire codebase.
All production and test code uses `storage.save_config`. The config_loader
version was never wired in — it has three latent bugs:

1. **No atomic_write** — direct `fh.write` risks partial writes on crash
2. **No frozenset→list conversion** — `archival_reasons` would cause YAML
   serialization error
3. **No legacy key stripping** — would re-emit `board`, `version`, `defaults`

The `_merge_into` helper (the only valuable part) also has zero test coverage.

### What Breaks Under Schema Grouping

When #1155 adds nested Pydantic sub-models to BoardConfig:

| Write Path | Impact | Required Changes |
|------------|--------|-----------------|
| storage.save_config | `model_dump()` produces nested dicts → CommentedMap serializes correctly | Update legacy-key strip list (new groups ≠ legacy groups); review frozenset handling for nested fields |
| migrate._migrate_config | Hardcoded flat key set → won't produce grouped output | Full rewrite of output builder to emit grouped keys |
| config_loader.save_config | Would handle nesting via _merge_into | **Delete — dead code** |

### Argument Order Hazard

The two `save_config` functions have reversed argument order:
- `config_loader.save_config(kanban_dir, config)`
- `storage.save_config(config, kanban_dir)`

Both parameters are non-overlapping types (Path vs BoardConfig), so misuse
would raise a runtime TypeError, not a silent bug. But the naming collision
creates confusion about which `save_config` is canonical.

### model_dump() Nested Behavior (Verified)

`BoardConfig.model_dump()` serializes sub-models as plain dicts:
`defaults → {'status': 'research', 'priority': 'important'}`.
`CommentedMap(data)` wraps top-level only — nested dicts serialize correctly
but lose any YAML comments on nested keys. This is acceptable because:
1. storage.save_config already discards all comments (full rewrite)
2. Comment preservation on nested keys is only valuable for config_loader's
   read-modify-write pattern, which is dead code

### defaults.priority Loss on Create-Task Hot Path

`storage.save_config` strips `defaults` from output (L250). `engine.py` reads
`config.defaults.priority` at L936 during task creation. `allocate_next_id`
calls `save_config` → full rewrite → `defaults` key vanishes from disk. Next
engine reload: `defaults` falls back to `BoardDefaults()` model default
(`priority="important"`). Works only because the live config value matches the
model default. A non-default value would be silently lost after first task
creation.

This is a pre-existing bug shared with #1170 (version/defaults semantics).
Not caused by write-path divergence, but exposed by it — storage.save_config
strips a key the engine still reads.

## 4. Recommendation (confidence: .72)

**T1 — Three-step unification, no user decision needed.**

### Step 1: Delete dead code
- Delete `config_loader.save_config` and `_merge_into` — zero callers, zero
  tests, 3 latent bugs (no atomic_write, no frozenset handling, re-emits
  legacy keys). The module docstring advertises a public save API, but no
  internal or downstream consumer uses it.
- Keep `config_loader.load_config` (actively used by engine.py and storage.py)
- Eliminates naming collision and "which save_config?" confusion

### Step 2: Harden storage.save_config for grouped output
- Replace hardcoded legacy-key strip list (`board`, `version`, `defaults`,
  `activity_log`) with a model-driven approach: emit only fields defined in
  the BoardConfig schema (using `model_fields` or an explicit allowlist)
- This resolves the defaults.priority loss: the new approach must either
  preserve `defaults` until #1170 resolves its ownership, or the strip list
  must be synchronized with engine.py's read set
- Add test proving nested dict round-trip works (currently untested)
- Verify frozenset→list conversion at nested depth

### Step 3: Update migrate._migrate_config output shape
- Migration output must match whatever storage.save_config produces
- Currently emits flat Brief-C keys; must emit grouped keys after #1155
- This step is inherently coupled to the grouping schema design (#1155) but
  the contract is clear: migrate output = storage output for equivalent data
- Scope as part of #1155 implementation, with explicit AC requiring
  migrate/storage output parity

### Why not adopt config_loader's comment-preserving approach?
- Comment preservation requires read-modify-write, which conflicts with
  atomic_write crash safety
- Every task creation triggers allocate_next_id → save_config → full rewrite,
  meaning comments are already lost on every board with active task creation
- Re-implementing comment-preserving atomic write is possible (write to temp,
  rename) but adds complexity for a scenario where comments are already gone
- If comment preservation becomes needed, _merge_into is 15 LOC and can be
  re-implemented with atomic_write and frozenset handling

Challenge: block — confidence in original: .42
Key challenges accepted:
- Contract mismatch: reframed Step 3 to explicitly require migrate/storage
  output parity as an #1155 AC, rather than deferring without contract
- defaults.priority loss: elevated to standalone finding (§3), acknowledged
  as cross-cutting with #1170
- Grouped correctness proof gap: added explicit "nested round-trip test" to
  Step 2 follow-up
Rebutted:
- "Block" recommendation: this task is research — its job is to produce
  findings and actionable follow-ups, not to implement unification. The
  three steps above ARE the unification plan; follow-up tasks carry the work.
- "config_loader contract divergence ≠ bug": the module's stated contract
  (lossless round-trip) is aspirational — it was never tested, never called,
  and would produce broken output (frozenset crash) if invoked today. Dead
  code with untested contracts is dead code, not an alternative architecture.

## 5. Follow-up Tasks

1. Delete config_loader.save_config + _merge_into dead code (T1, backlog)
2. Harden storage.save_config: model-driven field emission, nested round-trip
   test, defaults.priority strip-list alignment with engine read set (T1, backlog)
3. #1155 AC amendment: require migrate._migrate_config output parity with
   storage.save_config (scope note, not a separate task)
