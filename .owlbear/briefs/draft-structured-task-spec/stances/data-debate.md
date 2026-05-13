# Data Debate Log — `ac` and `proof_bundle` Schema Design

## Cycle 1

### Draft Position Summary

Seven positions covering AC validation (non-empty only), proof bundle (frozenset-validated string), defaults (ac=[], proof_bundle=None), YAML serialization (no special handling), backward compatibility (no risk), uniqueness (reject exact duplicates in Pydantic model), and ordering (insertion order meaningful).

### Critic Challenges (confidence 0.41, pressure: high)

**Critical challenges:**

1. **Duplicate AC rejection creates a corruption path.** Position 1 (minimal validation) contradicts Position 6 (reject duplicates). The storage layer classifies Pydantic validation failures as corruption, and corrupt tasks are silently skipped during list scans. A hand-edited task with duplicate AC lines would be quarantined — worse than the duplicates themselves. The validation boundary is in the wrong layer.

2. **Backward compatibility understated.** Position 5 focused on TaskSummary but ignored: `_CANONICAL_FIELDS` ordering, `migrate.py` active-default concept, engine summary projection, and existing storage/model tests that pin field sets and ordering.

**Moderate challenges:**

3. **YAML serialization claim too absolute.** "No special handling needed" ignores that `_CANONICAL_FIELDS` requires explicit placement and storage.py already has field-specific serialization behavior (timestamps). The data may not need special handling, but the serialization infrastructure does.

4. **Frozenset vs config inconsistency.** Status and priority use config-driven validation. Proof bundle uses a hardcoded frozenset. The stance dismissed config-driven without engaging the consistency argument.

**Blind spots identified:**

- Write-path reachability: engine and MCP don't accept these fields yet
- Normalization rules absent: no spec for whitespace stripping or case handling
- Migration policy for active tasks not stated
- Consumer semantics for summary/dispatch inclusion not grounded in actual consumer needs

### Modeler Response

**Accepted (revised):**

- **Challenge 1 → P6 rewritten.** Uniqueness enforcement moved to engine write path. Pydantic model accepts duplicates on read. This is the decisive revision — the Critic identified a genuine data loss path.
- **Challenge 2 → P5 expanded.** Full implementation surface table added: _CANONICAL_FIELDS, all three model tiers, DispatchEntry, engine, MCP, migrate.py, and existing tests.
- **Challenge 3 → P4 nuanced.** Acknowledged _CANONICAL_FIELDS placement requirement and existing serialization infrastructure. Maintained that AC/proof_bundle data itself needs no special quoting.
- **Normalization rules added** to P1 and P2: whitespace stripping, case normalization for proof bundle.
- **Write-path scope acknowledged** in P5 surface table.
- **Migration policy stated:** forward-only, no backfill required.
- **Consumer semantics grounded:** proof_bundle in TaskSummary and DispatchEntry (board views, dispatch scope). AC omitted from both (no list-view consumer, verbose).

**Defended:**

- **Challenge 4 (frozenset vs config):** Proof bundle is pipeline-protocol-defined, not board-owner-defined. Config-driven validation conflates board configuration with pipeline convention. The valid set changes when `r-pipeline-protocol` changes — that's a code change with protocol review, not a `kanban.yaml` edit. Consistency with status/priority is structural, not semantic — different ownership model.

**Critical late revision (post-Critic):**

- Realized `@field_validator` on `proof_bundle` in the Pydantic model fires during `_parse_task_file` read path, not just write path. Moved proof_bundle validation to engine-only, matching the AC uniqueness approach. Both fields: permissive model, strict engine.

### Position After Cycle 1

All seven positions revised or defended. Core architectural insight: **split validation between permissive read-path model and strict write-path engine.** No model-level validators for business rules on either field. Confidence raised from ~0.65 (draft) to 0.82 (post-Critic).

No further Critic cycle needed — the critical challenge was addressed and the position is architecturally consistent.
