# Config Schema Grouping — Research Refresh

> **Owning task:** #1155 — Implement config.yml schema grouping (nested sub-models)
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

#1114 research and #1155 validation research recommended nested sub-models,
gated on Brief stability. Briefs are now archived (A=#1045, B=#1044, C=#1043).
Three architectural rulings are resolved. This refresh validates the 5
architect handoff concerns against live code and corrects errors in prior docs.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `storage.py` L206 `_CONFIG_WRITE_EXCLUDE` | Internal | 1.0 — actual strip set |
| `engine.py` L936 `config.defaults.priority` | Internal | 1.0 — default priority |
| `migrate.py` + 1700-line test suite | Internal | 1.0 — migration infra |
| `models.py` L185-224 `_normalise_legacy` | Internal | 1.0 — format bridge |
| `server.py` L481 | Internal | 1.0 — s['name'] bug status |
| `storage.py` L236-260 `save_config` | Internal | 1.0 — canonical write path |
| `corruption.py` L315-675 | Internal | 0.8 — config access |
| Brief C paper L508 | Internal | 0.9 — tasks_dir/archive_dir drop intent |
| `.owlbear/research/1170-version-field-semantics.md` | Internal | 0.9 |
| `.owlbear/research/1171-config-write-path-audit.md` | Internal | 0.9 |
| `.owlbear/kanban/config.yml` (live) | Internal | 1.0 |

## 3. Analysis

### Architect Handoff Findings (5 Concerns)

| # | Concern | Finding | Severity |
|---|---------|---------|----------|
| 1 | `defaults.priority` used in engine.py | **Confirmed** at L936. BUT: prior research overstated fragility — `save_config` only strips `{board, version}`, NOT `defaults`. The value persists on disk. Ruling 2 (→`pipeline.default_priority`) is a design improvement, not a bug fix. | Moderate |
| 2 | migrate.py not in prior research | **Now studied.** 1700+ line test suite, 10 classes. `_migrate_config` emits flat Brief-C keys. Needs grouped output path for new schema. `_NEW_CONFIG_KEYS` and `_LEGACY_CONFIG_KEYS` frozensets control detection. | Moderate |
| 3 | storage.py + corruption.py access | **Inventoried.** storage: 9 sites, corruption: 8 sites, engine: 59 sites, models: 3, config_loader: 3. Total: 82 source sites. | Moderate |
| 4 | Brief B/C dependency IDs | **Moot.** All Briefs archived. Field set stable. | Resolved |
| 5 | T3 DR for breaking change | **Resolved.** Three architectural rulings bound. | Resolved |

### Corrections to Prior Research Docs

| Prior claim | Actual state | Impact |
|-------------|-------------|--------|
| save_config strips `defaults`, `activity_log` (#1155 validation, #1171 audit) | `_CONFIG_WRITE_EXCLUDE = {"board", "version"}` — only 2 keys stripped | defaults.priority persistence is NOT fragile |
| MCP server.py L481 `s["name"]` bug (#1155 validation) | Already fixed: `list(board_config().statuses)` | No separate bug task needed |
| config_loader has `_merge_into` (#1171 audit) | No such function in current code | Dead code already removed |
| "110+ test fixtures" (original #1114) | 18 BoardConfig constructors + 88 statuses refs = 106 matches across ~50 files | Estimate was correct |

### Detection Mechanism: schema Field

Research #1170 resolved the version-vs-versionless tension:
- **Grouped configs:** `schema: grouped` top-level field
- **Flat Brief-C:** no `schema` field (detected by key set, as today)
- **Legacy:** no `schema` field (detected by `version` presence, as today)
- Aligns with resolved DR's "use distinct field if needed later" clause

Detection cascade: `schema` field → `_NEW_CONFIG_KEYS` check → legacy keys.

### Impact Summary

| Dimension | Count | Notes |
|-----------|-------|-------|
| Source files to modify | 5 | engine, storage, corruption, models, migrate |
| Source access sites | 82 | 59 engine + 9 storage + 8 corruption + 6 other |
| Test fixture files | ~50 | 18 BoardConfig + 88 statuses patterns |
| Write paths to update | 2 | storage.save_config + migrate._migrate_config |
| Dead code to delete | 1 | config_loader.save_config (zero callers, per #1171) |

### Open Questions for Architect Review

| Question | Context | Options |
|----------|---------|---------|
| paths group vs Brief C intent | Brief C paper L508 says tasks_dir/archive_dir are "dropped fields." Live code uses both (storage, engine, corruption). | A: Keep in `paths:` group (.70) B: Drop from schema, hardcode values (.50) |
| Mixed-shape precedence | When flat `entry_status` AND `pipeline.entry_status` coexist, which wins? | A: Grouped wins (.80) B: Flat wins (.40) C: Reject ambiguous configs (.60) |
| extra='allow' placement | Live config has `defaults.class`, `tui.*` as vendor fields. | A: Root-only allow, strict sub-models (.75) B: Allow on all levels (.50) |
| Proposed sub-model grouping | Validate or adjust from #1114 research | See §4 |

## 4. Recommendation (confidence: .65)

**Advance to backlog.** The field set is stable, approach is validated, and
architectural rulings constrain the solution. Open questions (paths group,
mixed-shape, extra) are architect-review scope — they refine AC, not research.

### Proposed Grouping (pending architect validation)

```yaml
schema: grouped
paths:
  tasks_dir: tasks           # or drop per Brief C intent
  archive_dir: archive
pipeline:
  statuses: [research, backlog, todo, in-progress, review, docs, done]
  priorities: [someday, nice-to-have, important, needed, critical]
  entry_status: research
  terminal_status: done
  wave_size: 4
  default_priority: important  # from defaults.priority (Ruling 2)
agents:
  agent_map: {}
  agent_types: {}
  agent_compatibility: {}
policy:
  archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
  status_predicates: {}
  non_impl_tags: []
  claim_timeout: 1h
# Top-level (not grouped)
next_id: 1171
activity_log: false
# Vendor extensions preserved at root via extra='allow'
tui:
  title_lines: 2
  hide_empty_columns: true
```

### AC Revision Recommendations

| Current AC line | Recommendation |
|-----------------|----------------|
| `_normalise_legacy handles flat (v10) and grouped (v11)` | Replace with: `_normalise_legacy handles flat, grouped, and legacy; schema field for detection` |
| `Live config migrated via version bump (10 → 11)` | **Drop** per Ruling 1. Replace with: `Grouped configs include schema: grouped` |
| (missing) | Add: `defaults.priority → pipeline.default_priority` per Ruling 2 |
| (missing) | Add: `save_config emits grouped output; migrate._migrate_config updated` per Ruling 3 |
| (missing) | Add: `config_loader.save_config dead code deleted` per #1171 |

Challenge: reconsider — confidence in original: .37 (challenger), revised to .65.
Key challenges accepted: paths/Brief-C conflict (deferred to architect), mixed-shape
precedence (deferred to architect), detection mechanism (resolved by #1170).
Key challenges rebutted: defaults.priority fragility was based on incorrect claim
that save_config strips defaults (it doesn't — only strips board, version).

## 5. Follow-up Tasks

No new research tasks needed. Prior follow-ups (#1170, #1171) are completed.
The MCP server.py s['name'] bug is already fixed in current code.
Task #1155 itself is the implementation task — advances to backlog for arch review.
