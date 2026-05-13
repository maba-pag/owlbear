# Data Quality Stance — `ac` and `proof_bundle` as Frontmatter Fields

## Data Quality Stance

Seven schema questions were raised. Here are the hardened positions after Critic review.

### P1: AC format validation — non-empty only, no content constraints

Individual AC strings must be **non-empty after whitespace stripping**. No max-length, no prefix-pattern enforcement (e.g., `AC1:` naming is convention, not schema). The schema catches corruption (empty strings, whitespace-only entries); conventions are the agents' problem.

**Normalization rule:** strip leading/trailing whitespace on write. If the stripped result is empty, reject at the write path.

### P2: Proof bundle — single string validated against a hardcoded frozenset

Model as `proof_bundle: str | None` with a `@field_validator` checking membership in a module-level `VALID_PROOF_BUNDLES: frozenset[str]`.

**Why frozenset, not Literal:** Adding a combination requires a one-line set addition, not a type-level change. Literal is cleaner for 3-5 values but brittle at 15+.

**Why not config-driven:** The Critic correctly noted that `status` and `priority` use config-driven validation. However, proof bundle is defined by `r-pipeline-protocol` (pipeline convention), not by the board owner. Putting it in `kanban.yaml` conflates board configuration with pipeline protocol. The valid set changes when the protocol changes — that's a code change, not a config change.

**Why not regex:** User explicitly rejected regex validation. The combination space is small and enumerable.

**Why not decomposed (base + modifiers):** Over-engineering for ~15 values. A single string field with set membership is simpler, and the `+` separator is just a string convention within the validated set.

**Normalization rule:** strip whitespace, lowercase before membership check. Reject invalid values at the write path; accept `None` on read (field absent from YAML).

### P3: Defaults — `ac=[]`, `proof_bundle=None`

- `ac: list[str] = Field(default_factory=list)` — matches `tags` and `depends_on` precedent exactly.
- `proof_bundle: str | None = None` — `None` means "no proof strategy specified." Empty string `""` is meaningless data. `"behavioral"` as default would silently assign a testing strategy to unscoped tasks — that is data corruption by default value. `None` is honest.

### P4: YAML serialization — list-of-strings is safe; canonical ordering is required

ruamel.yaml handles `list[str]` serialization and quoting automatically. No custom quoting or escaping logic is needed for AC content.

**However:** `_CANONICAL_FIELDS` in `storage.py` must be updated with explicit placement for both fields. Recommended placement: `ac` after `depends_on` (list fields cluster), `proof_bundle` after `priority` (scalar metadata cluster). Existing tests pin canonical ordering and will need updates.

AC items should be single-line by convention. Multi-line YAML list items (block scalars in sequences) are valid but ugly. This is a convention boundary, not a schema boundary.

### P5: Backward compatibility — safe, but implementation surface is broader than it appears

**Read path (safe):** Pydantic defaults handle missing fields. Tasks without `ac` or `proof_bundle` load cleanly as `[]` and `None`. `extra='allow'` on `Task` preserves any unknown keys.

**Full implementation surface (must be addressed):**

| Surface | Impact |
|---------|--------|
| `_CANONICAL_FIELDS` (storage.py) | Explicit placement required |
| `Task` model (models.py) | New field declarations |
| `TaskSummary` model (models.py) | Add `proof_bundle` (cheap, useful for board views). Omit `ac` (verbose, no list-view consumer). |
| `TaskFull` model (models.py) | Add both fields (extends TaskSummary, so `proof_bundle` inherited; add `ac` explicitly) |
| `DispatchEntry` model (models.py) | Add `proof_bundle` (determines agent scope in dispatch). Omit `ac` (dispatch doesn't need full criteria). |
| `engine.create_task` | Add `ac` and `proof_bundle` parameters |
| `engine.edit_task` | Add `proof_bundle=` scalar, `add_ac`/`remove_ac` atomic ops (matching tags pattern) |
| MCP `create_task`, `edit_task` | Mirror engine parameter additions |
| `migrate.py` | No active-default migration needed — `None`/`[]` Pydantic defaults handle missing fields on read |
| Existing tests | Storage ordering tests, model field tests need updates |

### P6: Uniqueness — enforce at write path, not in model

**Revised from draft:** The Critic correctly identified that Pydantic model-level duplicate rejection would classify hand-edited tasks with duplicate AC lines as corrupt. The storage layer treats validation failures as corruption, and corrupt tasks are silently skipped during list scans. Rejecting duplicates at the model level is worse than the duplicates themselves.

**Position:** Accept duplicates in the Pydantic model (permissive read). Reject exact duplicates at the engine write path (`create_task`, `edit_task`) where rejection produces a clean error, not silent data loss. Duplicate check uses the stripped, normalized forms from P1.

### P7: Ordering — insertion order is semantically meaningful

AC is an ordered list. Agents reference items by position (AC1, AC2, ...). The list type preserves insertion order. Do not use a set or frozenset for storage. Atomic operations (`add_ac`, `remove_ac`) append to end and remove by exact match, respectively — matching the `tags` pattern.

## Schema and Validation Reasoning

The validation boundary is split between two layers:

| Layer | What it validates | Failure mode |
|-------|-------------------|-------------|
| Pydantic model (read path) | Type correctness, defaults | Corruption → task skipped |
| Engine write path | Business rules (non-empty, uniqueness, enum membership) | Clean error → caller retries |

This split is critical. The model must be permissive on read to avoid escalating minor data issues (duplicates, stale proof bundle values) into corruption. The engine is the enforcement boundary because rejection there produces actionable errors, not silent data loss.

**Proof bundle validation is read-path safe** because `str | None` accepts any string on read. The frozenset check runs only in the `@field_validator`, which fires during model construction — but existing tasks that predate new proof bundle values would need the frozenset updated, not the tasks quarantined. If strict read-time validation is desired later, it should be opt-in and produce warnings, not corruption.

**Correction:** On reflection, the `@field_validator` fires on read too (model construction from YAML). For proof_bundle, the validator should be **write-path only** (in engine.create_task/edit_task), not in the Pydantic model. The model field should be `proof_bundle: str | None = None` with no validator — accepting any string that was historically written. This matches the AC uniqueness approach: permissive model, strict engine.

## Key Trade-offs

| Trade-off | Position | Rationale |
|-----------|----------|-----------|
| Schema strictness vs read safety | Permissive model, strict engine | Avoid corruption classification |
| Frozenset vs config-driven proof bundle | Frozenset in code | Pipeline protocol, not board config |
| AC in TaskSummary | Omit | No list-view consumer; verbose payload |
| proof_bundle in TaskSummary | Include | Cheap; useful for board views and dispatch |
| Duplicate AC rejection | Write-path only | Read-path rejection = silent data loss |

## Warnings

1. **Do not put proof_bundle validation in the Pydantic model.** Any `@field_validator` on `Task.proof_bundle` will fire during `_parse_task_file`, and an unrecognized value will quarantine the task. Validate in the engine only.
2. **Do not put AC uniqueness in the Pydantic model.** Same reason as above.
3. **`_CANONICAL_FIELDS` ordering will break existing snapshot tests.** This is expected and the tests should be updated, not worked around.
4. **DispatchEntry needs `proof_bundle`.** Without it, agents receiving dispatch waves cannot determine their testing scope without a separate `show_task` call.
5. **Migration is forward-only.** Existing tasks load with defaults. No backfill script is required for correctness, though one is acceptable for cleanliness.

## Confidence

**0.82** — High confidence on the permissive-model/strict-engine split (Critic challenge was decisive). Moderate uncertainty on whether `proof_bundle` will eventually need config-driven validation as the pipeline protocol evolves; frozenset is correct today but may need revisiting.
