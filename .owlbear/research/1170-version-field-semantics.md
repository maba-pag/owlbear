# Version Field Semantics for Grouped Config Schema

> **Owning task:** #1170 — Resolve version field semantics for grouped config schema
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

#1155 AC specifies "version bump (10 → 11)" for the grouped config migration.
The live codebase contradicts this: engine.py L471-475 treats `version` presence
as a legacy-schema marker, storage.py strips it on write, and migrate.py
classifies it as a legacy key. These are incompatible goals.

**Question:** Should grouped configs (a) be versionless like current new-schema,
(b) use a different field for format identification, or (c) repurpose `version`
as a schema tracker by rewriting all detection logic?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `engine.py` L471-475 | Internal | 1.0 — `is_legacy_schema` detection gate |
| `models.py` L185-220 | Internal | 1.0 — `_normalise_legacy` validator |
| `storage.py` L240-260 | Internal | 1.0 — `save_config` strips version |
| `migrate.py` L50-68, L325-336 | Internal | 1.0 — `_LEGACY_CONFIG_KEYS`, `_is_config_migrated` |
| `migrate.py` L367-475 | Internal | 0.9 — `_migrate_config` omits version |
| 7+ test fixtures (v9/v10) | Internal | 0.8 — encode version=legacy contract |
| Docker Compose Spec — version field | External | 0.8 — deprecated version, uses structure-based detection |
| `.owlbear/research/1155-config-schema-grouping-validation.md` | Internal | 0.9 — identified contradiction |

## 3. Analysis

### Current Version Semantics (4 modules)

| Module | Location | Behavior |
|--------|----------|----------|
| engine.py | L471-475 | `version` present → legacy schema |
| models.py | L210 | `"version" in data` → populate fallback `agent_map` |
| storage.py | L250 | Strips `version` from all writes |
| migrate.py | L68, L332 | `version` in `_LEGACY_CONFIG_KEYS` — must be absent for "migrated" |

**Consensus:** `version` is a deprecation marker across all modules. It has never
functioned as a schema version tracker — no code path reads its numeric value.

### Option Comparison

| Criterion | A: Pure versionless | B: New `schema` field | C: Repurpose `version` |
|-----------|--------------------|-----------------------|------------------------|
| KISS | ✓ No new concepts | ~ One new field | ✗ Redefines existing field |
| YAGNI | ✓ Key detection exists | ~ Adds field for future-proofing | ✗ Rebuilds tested logic |
| Code changes | ~3 (extend detection) | ~4 (add field + detection) | ~10+ (rewrite 4 modules) |
| Test changes | ~2 | ~3-5 | ~10+ fixture rewrites |
| Vendor-field safety | ✗ `extra='allow'` can spoof group keys | ✓ Explicit signal | ✓ Explicit signal |
| Future migration ordering | ✗ None — key shapes may collide | ✓ Schema values are orderable | ✓ Version numbers orderable |
| Backward compat | ✓ No new fields | ✓ New field, old code ignores | ✗ Version semantics change |
| Risk | Medium (fragile at 3+ formats) | Low | High (blast radius) |

### Detection Cascade (Option B)

```
1. Has `schema` field?  → check value: "grouped" = grouped format
2. No `schema`, has all _NEW_CONFIG_KEYS, no legacy keys? → flat Brief-C
3. Has legacy keys (version, board, etc.)? → legacy schema
```

This cascade:
- Requires zero changes to existing legacy detection (engine.py, models.py)
- Works with `extra='allow'` (explicit field, not inferred from structure)
- Scales to future formats (new `schema` value, no structural ambiguity)
- Flat Brief-C configs remain untouched (no retrofit needed)

### Docker Compose Precedent

Docker Compose deprecated its `version` field (docs.docker.com): "Compose always
uses the most recent schema to validate the Compose file, regardless of the
`version` field." They moved to structure-based detection. Our situation is
analogous but smaller-scale — the `schema` field approach is a middle ground
between pure structure-based and version-tracked.

## 4. Recommendation (confidence: .75)

**Option B: Introduce a `schema` field for grouped and future formats.**

- Grouped configs: `schema: grouped` (top-level, after `---`)
- Legacy configs: no `schema` (detected by `version` presence, as today)
- Flat Brief-C: no `schema` (detected by key set, as today)
- Future formats: `schema: <name>` (no numeric versioning)

**Rationale:** Option A is viable for the immediate flat→grouped transition but
breaks down at 3+ formats due to `extra='allow'` ambiguity and no ordering
mechanism (challenger confirmed). Option C has high blast radius for marginal
benefit. Option B adds one field, doesn't touch existing detection, and scales.

**AC correction for #1155:** Replace "version bump (10 → 11)" with "add
`schema: grouped` field; key-based detection for format identification."

Challenge: reconsider → revised from pure versionless (.82) to schema field (.75)
Challenger confidence in original: .52. Key challenges accepted: ordered-migration
blind spot (critical), vendor-field ambiguity with `extra='allow'` (moderate).

## 5. Follow-up Tasks

No new tasks — this research resolves one of #1155's three blocking dependencies.
The recommendation feeds into the pending T3 DR at
`.owlbear/decisions/pending/1155-config-schema-grouping.md`.

**Required AC update for #1155** (when architect revisits):
- Remove: "Live config migrated via version bump (10 → 11)"
- Add: "Grouped configs include `schema: grouped` at top level"
- Add: "Detection cascade: schema field → key-based → legacy"
