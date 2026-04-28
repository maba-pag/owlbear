# Config Schema Grouping — Validation Research

> **Owning task:** #1155 — Implement config.yml schema grouping (nested sub-models)
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

#1114 research recommended nested sub-models after Briefs A/B/C stabilize the
field set. Briefs are now archived (A=#1045, B=#1044, C=#1043). This validation
pass audits the 5 architect handoff concerns and assesses implementation
readiness against live codebase state.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/kanban/src/owlbear_kanban/engine.py` L471-475, L936 | Internal | 1.0 — version gate + defaults.priority |
| `serve/kanban/src/owlbear_kanban/storage.py` L236-257 | Internal | 1.0 — save_config strips version/defaults |
| `serve/kanban/src/owlbear_kanban/migrate.py` L396-447 | Internal | 1.0 — v10 migration infra |
| `serve/kanban/src/owlbear_kanban/config_loader.py` L95-150 | Internal | 0.9 — _merge_into nested support |
| `serve/kanban/src/owlbear_kanban/corruption.py` | Internal | 0.8 — 7 config access sites |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L481 | Internal | 0.9 — pre-existing bug |
| `serve/kanban/tests/test_migrate.py` | Internal | 0.8 — 10+ migration tests |
| `.owlbear/research/1114-config-yml-schema-grouping.md` | Internal | 0.9 — prior research |

## 3. Analysis

### Architect Handoff Findings

| # | Concern | Finding | Severity |
|---|---------|---------|----------|
| 1 | `defaults.priority` used in engine.py | CONFIRMED: L936 `config.defaults.priority`. But `storage.save_config` strips `defaults` from disk (L250). After any save cycle, `defaults` is lost — works only because `BoardDefaults.priority` model default (`"important"`) matches typical config value. Fragile. | Critical |
| 2 | migrate.py not in prior research | CONFIRMED gap. `_migrate_config()` (L396-520) handles legacy→v10. Emits flat Brief-C keys, not grouped. No v10→v11 path exists. 10+ tests cover v10 transitions. | Critical |
| 3 | storage.py + corruption.py access sites | CONFIRMED: storage.py 7 sites, corruption.py 7 sites, engine.py 40+, MCP server 1+, cockpit 2+. Total: ~70+ code sites + 35+ test fixture files. | Moderate |
| 4 | Brief B/C dependency IDs | MOOT: All Briefs archived. Field set is stable. | Resolved |
| 5 | T3 DR for breaking schema change | CONFIRMED T3: user-facing config format change + legacy deprecation. See §4. | Critical |

### Version Field Contradiction

The AC specifies "version bump (10 → 11)" but live code contradicts this:

| Component | Behavior | Evidence |
|-----------|----------|----------|
| `engine.py` L471-475 | Presence of `version` field = legacy schema | `is_legacy_schema = bool(getattr(self._config, "version",...))` |
| `storage.save_config` L250 | Strips `version` from new-schema output | `("board", "version", "defaults", "activity_log")` |
| `_normalise_legacy` | Uses `version` as legacy detection marker | `"version" in data or "board" in data` |

**Implication:** Introducing v11 as a version field would make the engine treat grouped configs as legacy. The version bump AC is incompatible with current runtime semantics.

### Config Authority Split

Three independent config-writing paths with divergent assumptions:

| Path | Location | Behavior | Nested-safe? |
|------|----------|----------|-------------|
| Round-trip merge | `config_loader._merge_into` | Preserves YAML comments, recurses nested dicts | Yes |
| Canonical rewrite | `storage.save_config` | Full atomic rewrite, strips legacy keys | Needs update |
| Migration builder | `migrate._migrate_config` | Emits flat Brief-C keys only | Needs rewrite |

### Access Site Inventory (Refined)

| Module | Sites | Fields accessed |
|--------|-------|----------------|
| engine.py | ~40 | statuses, priorities, entry_status, terminal_status, claim_timeout, tasks_dir, archive_dir, activity_log, agent_map, agent_compatibility, defaults.priority, model_extra |
| storage.py | 7 | tasks_dir, archive_dir, next_id, model_dump() |
| corruption.py | 7 | priorities, statuses, tasks_dir, archive_dir |
| config_loader.py | 3 | load/save/merge paths |
| migrate.py | 10+ | All Brief-C fields |
| MCP server.py | 1+ | statuses (BUGGY — see below) |
| Cockpit routes | 2+ | statuses, priorities |
| **Total code** | **~70+** | |
| **Test fixtures** | **35+ files** | Full config dicts |

### Pre-existing Bug: MCP server.py L481

```python
status_names = [s["name"] for s in app_ctx.engine.board_config().statuses]
```

`board_config().statuses` is `list[str]` (post-Brief-C). `s["name"]` on a
string raises `TypeError`, silently caught by `contextlib.suppress(Exception)`.
Guidance collection is broken on new-schema boards. Not caused by this task
but should be fixed before or alongside grouping work.

## 4. Recommendation (confidence: .45)

**Block for pre-implementation resolution.** Three critical contradictions must
be resolved before the grouping AC can be implemented:

1. **Version semantics**: AC says v10→v11 but engine treats version=legacy.
   Either: (a) grouped configs are versionless (like current new-schema), or
   (b) engine migration gate is rewritten to use a different detection method.
2. **defaults.priority ownership**: Must be explicitly migrated to a grouped
   location (e.g., `pipeline.default_priority`) or preserved as a top-level
   field. Current fragile dependency on model defaults is a latent bug.
3. **Config writer unification**: Three divergent write paths must agree on
   grouped output format before implementation can safely proceed.

**T3 classification**: Two T3 triggers — changes user-facing config format,
proposes deprecation of legacy keys. Blocking DR required.

**Challenge:** block — confidence in original: .34
Challenger identified version contract contradiction (critical), defaults.priority
taxonomy gap (critical), migration infrastructure gaps (moderate), blast-radius
understatement (moderate). Revised from "proceed" to "block for pre-resolution."

## 5. Follow-up Tasks

1. Resolve version field semantics for grouped config schema
2. Audit and unify config write paths (config_loader vs storage vs migrate)
3. Fix MCP server.py L481 pre-existing bug (status_names dict assumption)
4. T3 Decision Request for breaking config.yml schema change
