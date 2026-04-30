---
# >> Resolved decision (filed 2026-04-29)
response: approved
decision: "Bind three architectural rulings — see below"
notes: "Rulings are binding constraints for the builder. MCP server.py bug (s['name'] on strings) is a separate concern — file as new task."
# >> Agent metadata
task_id: 1155
agent: researcher
created: 2026-04-28
urgency: blocking
decision_type: scope-decision
impact_tier: 3
resolved: 2026-04-29
---

# Config Schema Grouping — Pre-Implementation Contradictions

## Concern

T3 breaking schema change: config.yml nested sub-model grouping requires user-facing format change (flat→grouped keys), deprecation of legacy keys (board, defaults, tui, version), and seed template restructure.

**Three critical pre-implementation contradictions:**

1. **AC says version bump 10→11 but engine treats version field as legacy marker — incompatible.** The AC specifies incrementing `version: 10` to `version: 11`, but the engine currently uses version as a deprecation marker for detecting old formats. These goals conflict: is version a schema version tracker or a legacy-detection flag?

2. **defaults.priority is actively used at runtime but stripped by save_config — fragile.** The field is required at engine initialization but gets dropped during write-back. This creates a silent data loss path and couples runtime behavior to save timing.

3. **Three divergent config write paths must be unified.** Multiple code paths write config (save_config, move_task, edit_task mutations). No single authority exists for schema validation or key preservation. Unifying these requires mapping out all write sites and their serialization contracts.

## Resolution

### Ruling 1: Version Field — Versionless Grouped Configs

Grouped configs remain **versionless**, like current new-schema output. The `version` field stays a legacy-only detection marker. The AC line "version bump (10 → 11)" is **dropped**. If schema versioning is needed later, use a distinct field (e.g., `schema_version`).

### Ruling 2: defaults.priority → pipeline.default_priority

Migrate `defaults.priority` into the grouped structure as `pipeline.default_priority`. The migration path must explicitly move the value; the builder must not rely on Pydantic model defaults to paper over a missing field.

### Ruling 3: save_config as Single Write Authority

`storage.save_config` is the **single canonical write path**. Migration and merge paths must produce output that `save_config` can round-trip without loss. Update `save_config` to emit grouped output first, then align the other two paths.

## Reference

Research doc: `.owlbear/research/1155-config-schema-grouping-validation.md`
