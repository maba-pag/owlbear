# config.yml Schema Grouping

> **Owning task:** #1114 — Research: config.yml schema grouping after Brief A/B/C
> **Date:** 2026-04-28 **Status:** Complete

## 1. Context and Question

config.yml uses a hybrid schema: legacy nested groups (`board:`, `defaults:`,
`tui:`) coexist with 14 flat Brief-C keys. The live board and seed template
diverge (live has `board:`/`tui:`; seed uses dict-form statuses). As field
count grows, should config.yml adopt a consistent grouped structure?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `.owlbear/kanban/config.yml` (live) | Internal | 1.0 — actual hybrid schema |
| `seed/.owlbear/kanban/config.yml` | Internal | 1.0 — seed divergence |
| `serve/kanban/src/owlbear_kanban/models.py` (BoardConfig) | Internal | 1.0 — 17 fields, validators |
| `serve/kanban/src/owlbear_kanban/config_loader.py` | Internal | 0.9 — round-trip write semantics |
| `serve/kanban/src/owlbear_kanban/engine.py` | Internal | 0.9 — 40+ config field access sites |
| `serve/kanban/README.md` | Internal | 0.7 — manual stub completion path |
| 69+ test fixture matches (tests/), 41+ (serve/) | Internal | 0.8 — migration cost |

## 3. Analysis

### Current State: Hybrid Schema (Not Flat)

The problem is NOT "17 flat fields" — it's schema inconsistency:
- **Live config:** 3 legacy nested groups + 14 flat keys + `version`
- **Seed config:** 1 legacy group + dict-form statuses + 15 flat keys
- **BoardConfig model:** Flat 17 fields with `extra='allow'` for unknowns
- `_normalise_legacy` bridges both at parse time

### Impact Assessment

| Dimension | Status | Evidence |
|-----------|--------|----------|
| Access sites to change | ~40+ in engine.py alone | `self._config.field` × 20, `config.field` × 20+ |
| Test fixtures to update | ~110 matches across tests/ + serve/ | grep for config fixture patterns |
| User-facing impact | Moderate | Setup requires manual agent_map stub completion |
| Nested access precedent | Already exists | `config.defaults.priority` in engine.py L935 |
| Round-trip serializer | Already handles nesting | `_merge_into` recurses into CommentedMap |

### Option Comparison

| Criterion | A: Nested sub-models | B: YAML comments only | C: Defer (YAGNI) |
|-----------|---------------------|----------------------|-------------------|
| Schema consistency | .90 — resolves hybrid state | .30 — cosmetic only | .10 — hybrid persists |
| Code simplicity | .50 — nested access everywhere | .95 — zero code changes | .95 — no changes |
| Migration cost | .30 — 110+ fixtures, 40+ access sites, version bump | .95 — zero | 1.0 — zero |
| Onboarding UX | .85 — discoverable groups | .60 — comments help scanning | .40 — hybrid confusing |
| Timing risk | .20 — Briefs may change fields | .90 — safe anytime | 1.0 — no risk |
| Round-trip compat | .80 — `_merge_into` supports nesting | .70 — comments preserved | .95 — no change |
| `extra='allow'` compat | .40 — unknown keys: which group? | .90 — no impact | .95 — no impact |
| **Weighted score** | **.52** | **.72** | **.68** |

### Key Risk: Timing

Briefs A/B/C remain in draft. The task's original block reason ("Wait for
Briefs A, B, C to land — field set may still change") is still active. Any
grouping decision made now may need restructuring when Briefs add, remove, or
rename fields.

## 4. Recommendation (confidence: .72)

**Sequence, don't dismiss.**

1. **Now:** Re-block task until Briefs A/B/C stabilize the field set.
2. **After Briefs land:** Implement Option A (nested sub-models) as schema
   consolidation — resolves the hybrid state, not just readability.
3. **Preliminary grouping** (to validate after Briefs):
   - `paths:` — tasks_dir, archive_dir
   - `pipeline:` — statuses, priorities, entry_status, terminal_status, wave_size
   - `agents:` — agent_map, agent_types, agent_compatibility
   - `policy:` — archival_reasons, status_predicates, non_impl_tags, claim_timeout
   - Top-level: next_id, activity_log, version
   - Legacy cleanup: drop board, defaults, tui from new schema
4. **Migration:** Version bump (10 → 11), `_normalise_legacy` handles both
   flat and grouped inputs.

**Challenge:** reconsider — confidence in original: .47
Key challenges accepted: comment fallback was unsupported, cost inventory was
understated (110+ not 14), hybrid schema is the real problem, users DO hand-edit
config during setup. Revised from "defer indefinitely" to "sequence correctly."

## 5. Follow-up Tasks

- One implementation task (at `research`): config.yml schema grouping implementation
  — gated on Brief A/B/C completion
