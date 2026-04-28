---
task_id: 1155
response: pending
decision:
---

# Config Schema Grouping — Pre-Implementation Contradictions

## Concern

T3 breaking schema change: config.yml nested sub-model grouping requires user-facing format change (flat→grouped keys), deprecation of legacy keys (board, defaults, tui, version), and seed template restructure.

**Three critical pre-implementation contradictions:**

1. **AC says version bump 10→11 but engine treats version field as legacy marker — incompatible.** The AC specifies incrementing `version: 10` to `version: 11`, but the engine currently uses version as a deprecation marker for detecting old formats. These goals conflict: is version a schema version tracker or a legacy-detection flag?

2. **defaults.priority is actively used at runtime but stripped by save_config — fragile.** The field is required at engine initialization but gets dropped during write-back. This creates a silent data loss path and couples runtime behavior to save timing.

3. **Three divergent config write paths must be unified.** Multiple code paths write config (save_config, move_task, edit_task mutations). No single authority exists for schema validation or key preservation. Unifying these requires mapping out all write sites and their serialization contracts.

## Reference

Research doc: `.owlbear/research/1155-config-schema-grouping-validation.md`

