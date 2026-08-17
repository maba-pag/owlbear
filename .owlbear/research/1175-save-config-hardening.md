# Harden storage.save_config for Grouped Config Output

> **Owning task:** #1175 — Harden storage.save_config for grouped config output
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

`storage.save_config` (L236-261) uses a hardcoded pop-loop to strip four keys
from `model_dump()` output: `board`, `version`, `defaults`, `activity_log`.
This approach breaks when #1155 adds nested sub-models (new keys won't be
handled), and silently loses `defaults.priority` and `activity_log` values
that the engine actively reads.

Question: What implementation approach replaces the hardcoded strip list with
model-driven field emission, fixes the `defaults.priority` loss, and handles
frozenset conversion at nested depth?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| storage.py L236-261 (save_config) | Internal | 1.0 |
| engine.py L936 (`config.defaults.priority`) | Internal | 1.0 |
| engine.py L458-462 (`config.activity_log`) | Internal | 1.0 |
| models.py L129-175 (BoardDefaults, BoardConfig) | Internal | 1.0 |
| migrate.py L65-72 (_LEGACY_CONFIG_KEYS) | Internal | 0.9 |
| test_migrate.py L505-520 (AC-C33 strip test) | Internal | 0.9 |
| test_storage_1050.py L796-804 (round-trip) | Internal | 0.8 |
| .owlbear/research/1171-config-write-path-audit.md | Internal | 1.0 |
| Pydantic v2 model_dump(exclude=) API | External | 0.9 |

## 3. Analysis

### Current Defects

| Defect | Impact | Severity |
|--------|--------|----------|
| `defaults` stripped → `defaults.priority` lost | Non-default priority silently reverts to "important" after first task creation | High |
| `activity_log` stripped → value lost | Non-default `activity_log: false` silently reverts to `true` | Moderate |
| Frozenset check top-level only | Nested frozensets in future sub-models would crash YAML serialization | Low (latent) |
| Hardcoded strip list | New fields from #1155 require manual list update or break silently | Moderate (latent) |

### Bug Reproduction (verified)

Created BoardConfig with `defaults.priority="critical"`. Called
`save_config` → reloaded → `defaults.priority` reverted to `"important"`.
Root cause: save_config strips `defaults` key; load_config rebuilds it
from `BoardDefaults()` model default.

### Approach Comparison

| Criterion | A: model_dump(exclude=DEAD) | B: model_dump(include=ALLOWED) | C: Field(exclude=True) |
|-----------|---------------------------|-------------------------------|----------------------|
| Adapts to new fields | Yes — only dead keys excluded | No — every new field needs allowlisting | Yes — per-field |
| Preserves vendor fields | Yes — extra='allow' passthrough | No — loses all extras | Yes |
| Code change size | ~15 LOC (replace pop-loop + add walker) | ~15 LOC | ~5 LOC (model only) |
| Migration contract alignment | Diverges: save_config preserves defaults/activity_log; migrate drops them | Depends on allowlist | Model-wide — affects logging/debug dumps |
| Maintenance burden | Low — dead set rarely changes | High — every schema change | Moderate — per-field decision |
| AC1 fit ("model-driven") | Partial — denylist is policy, not schema-derived | Full — explicit allowlist | Full — lives in model |
| KISS score | .85 | .50 | .65 |

### Key Design Decisions

**1. Which fields are truly dead?**

Only `board` and `version` have zero runtime readers. Both are legacy
identity/migration markers that no engine method consumes.

`defaults` is read at engine.py L936 (`config.defaults.priority`).
`activity_log` is read at engine.py L459 (`config.activity_log`).
Both are legacy-origin but actively consumed — stripping them is a bug.

**2. Migration contract divergence**

migrate.py classifies `defaults` and `activity_log` as `_LEGACY_CONFIG_KEYS`
(L65-72). AC-C33 asserts they're absent after migration. But the migration
contract governs format *conversion* (old → new), not live-config
*persistence*. save_config's job is to round-trip the live BoardConfig state.

Divergence is acceptable: migrate produces a "clean" new-schema file;
save_config preserves runtime state including legacy-origin fields. When
#1170 resolves field ownership, both paths can be synchronized.

**3. Denylist vs allowlist (AC1)**

AC1 says "model-driven field emission (e.g. model_fields allowlist)". An
allowlist (`model_dump(include=...)`) would lose `extra='allow'` vendor
fields, which the current code preserves. A minimal denylist
(`model_dump(exclude={"board", "version"})`) is functionally model-driven:
new fields are included automatically; only known-dead keys are excluded.
The exclude set is a frozenset constant collocated with the model.

**4. Recursive frozenset walker**

Current code handles only top-level `archival_reasons`. A recursive
`_deep_frozenset_to_list()` (~8 LOC) converts frozenset→sorted(list) at
any depth. This prepares for #1155's nested sub-models without solving a
hypothetical problem — frozenset fields exist today (archival_reasons) and
the current handler would miss nested ones.

## 4. Recommendation (confidence: .75)

**Approach A: `model_dump(exclude=_LEGACY_WRITE_EXCLUDE)` + recursive walker**

Implementation outline:

```python
_LEGACY_WRITE_EXCLUDE: frozenset[str] = frozenset({"board", "version"})


def _deep_frozenset_to_list(obj):
    """Convert frozenset→sorted list recursively for YAML serialization."""
    if isinstance(obj, frozenset):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _deep_frozenset_to_list(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_frozenset_to_list(v) for v in obj]
    return obj


def save_config(config: BoardConfig, kanban_dir: Path) -> None:
    data = config.model_dump(exclude=_LEGACY_WRITE_EXCLUDE)
    data = _deep_frozenset_to_list(data)
    # ... CommentedMap + YAML dump + atomic_write (unchanged)
```

**AC coverage:**
- AC1: model_dump(exclude=) replaces hardcoded strip list — auto-adapts to new fields
- AC2: Test nested dict round-trip (defaults sub-model)
- AC3: Test frozenset conversion at nested depth (via walker)
- AC4: defaults.priority preserved — removed from exclude set

**Risks:**
- Migration contract divergence: save_config now preserves `defaults` and
  `activity_log` that migrate drops. Acceptable — different operations with
  different contracts. #1170 can synchronize.
- `defaults.status` redundancy: both `entry_status` and `defaults.status`
  appear in output. Harmless — normalizer handles both.
- Vendor field passthrough: unchanged from current behavior.

Challenge: reconsider — confidence in original: .58
Key challenges accepted:
- activity_log runtime dependency confirmed (engine.py L459) — both
  defaults and activity_log are actively consumed, not just defaults
- Migration contract divergence acknowledged — documented as acceptable
  with #1170 synchronization path
- Confidence lowered from .85 to .75 — no executable tests in repo yet
Rebutted:
- "Block for migration parity": save_config and migrate have different
  jobs (round-trip vs conversion). Synchronization is a #1170 concern.
- "Allowlist required for AC1": allowlist loses vendor fields — worse
  outcome. Denylist is model-driven in practice.

## 5. Follow-up Tasks

Implementation is a single T1 task — the AC is already well-specified.
No additional decomposition needed beyond what the task AC states.
Testing strategy: 3 new tests covering AC2-AC4. Existing save_config
round-trip tests (test_storage_1050, test_engine_archived_edit_1120)
serve as regression guards.
