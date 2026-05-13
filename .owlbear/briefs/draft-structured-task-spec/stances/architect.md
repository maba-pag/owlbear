# Architectural Stance — Structured Task Specification in Frontmatter

## Architectural Stance

Adding `ac` (list[str]) and `proof_bundle` (str | None) to Task frontmatter is structurally sound. The kanban model already has a well-exercised pattern for list fields (`tags`, `depends_on`) and optional string fields (`archival_reason`). This feature follows those patterns with two targeted deviations: a dual mutation API for AC, and a normalizing validator for proof_bundle.

The design is a refactor, not greenfield. Every layer touched (model, storage, engine, AgentView, MCP) has precedent for the exact operations needed. The blast radius is bounded: 3 model classes, 2 engine methods, 1 MCP server, and a handful of skill files.

## Structural Reasoning

### 1. AC Field — `list[str]`, dual mutation API

**Type:** `ac: list[str] = Field(default_factory=list)` on `Task`. Follows the `tags` pattern exactly: same type, same default, same serialization path through `model_dump()` + ruamel.yaml.

**API:** Dual mode with **mutual exclusion**.
- `create_task` gets `ac: list[str] | None` for setting the full list at creation time.
- `edit_task` (engine) gets `ac: list[str] | None` for full replacement, plus `add_ac: list[str] | None` / `remove_ac: list[str] | None` for atomic operations.
- If both `ac` and `add_ac`/`remove_ac` are provided in the same call, **AgentView rejects with a validation error**. This follows the existing `body`/`append_body` mutual exclusion precedent in AgentView.
- MCP follows singular naming convention: `ac`, `add_ac`, `remove_ac`.

**Rationale for dual API:** Unlike tags (where adding/removing one at a time is the common case), AC is typically set as a complete list during task decomposition and rarely modified item-by-item. Forcing atomic-only operations means N `add_ac` calls from decomposition skills. Full replacement covers the 90% case; atomic ops cover the 10% (reviewer adding a late criterion).

**Semantics:** Set-like, matching tags. `add_ac` adds only if the exact string is absent. `remove_ac` removes exact matches. AC items are distinct specification statements — identity is the string itself.

### 2. proof_bundle Field — `str | None`, normalizing model validator

**Type:** `proof_bundle: str | None = None` on `Task`. Default `None` means "not set" — either a legacy task or creator didn't specify. No implicit default like "behavioral".

**Validation:** `@field_validator` on `Task` that:
1. Splits on `+` into base and modifiers.
2. Sorts modifiers alphabetically and deduplicates.
3. Reassembles into canonical form (e.g. `"challenge+behavioral"` → `"behavioral+challenge"`).
4. Validates against a hardcoded `frozenset` of canonical composite strings.

The model becomes the single canonicalizing authority. Every path (engine, MCP, direct construction) gets normalization and validation.

**Why model, not engine:** Status and priority validate in the engine because they're config-driven (board-specific). Proof bundle is a product constant — the taxonomy is product-wide, not per-board. Hardcoding is appropriate for ~15 valid combinations that change perhaps once per year. A taxonomy update is a one-line constant change.

**Why not expose the enum to agents:** User decision. Agents write the string; the model normalizes and validates. Agents see a validation error if they send garbage, but they don't need to import an enum.

### 3. Model Hierarchy

| Model | `ac` | `proof_bundle` | Rationale |
|-------|------|----------------|-----------|
| `Task` | Yes | Yes | Schema of truth |
| `TaskSummary` | No | Yes | Single string, near-zero cost, enables future utility |
| `TaskFull` | Yes (explicit) | Yes (inherited) | Full spec visible on show/update |
| `DispatchEntry` | No | Yes | Agents see proof context in dispatch without extra show_task call |

AC excluded from `TaskSummary` because: list payload in list views has no demonstrated consumer, user rejected `ac_count` as useless, and `show_task` is the right place for spec detail.

`TaskFull` inherits `TaskSummary`, so `proof_bundle` comes free. `ac` must be added explicitly to `TaskFull` since it's deliberately absent from `TaskSummary`.

### 4. `_CANONICAL_FIELDS` Placement

```
...depends_on, ac, proof_bundle, blocked, block_reason, claimed_at, archival_reason, archival_refs
```

AC and proof_bundle are specification fields — they define what the task should accomplish and how thoroughly to verify it. They cluster after relationship fields (parent, depends_on) and before operational state (blocked, claimed_at, archival). This creates a clean frontmatter layout: identity → timestamps → taxonomy → relationships → **specification** → operational state.

Both `_CANONICAL_FIELDS` in storage.py and any duplicate in migrate.py must be updated.

### 5. Validation Layer Split

| Concern | Layer | Precedent |
|---------|-------|-----------|
| Field types, proof_bundle normalization/validation | Model (`@field_validator`) | N/A — new pattern, but Pydantic validators are the standard layer |
| API-level mutual exclusion (`ac` vs `add_ac`/`remove_ac`) | AgentView | `body` vs `append_body` exclusion |
| Status/priority enum membership | Engine | Existing pattern |

### 6. Search Extension

When AC moves from body to frontmatter, the engine's search predicate (currently title + body substring match) must extend to also match against AC items. Without this, AC content becomes unsearchable — a regression. The search contract update is deliberate and should be documented and tested.

### 7. Source Precedence During Transition

**Frontmatter is authoritative when present.** If `task.ac` is non-empty, that's the AC. If `task.ac` is empty and the body contains `## Acceptance Criteria`, agents fall back to body parsing. Same for `proof_bundle`: if set, that's the value; if `None`, agents check the body.

This is a per-task rule, not global. Mixed boards (legacy + new tasks) work correctly. Legacy tasks gain `ac: []` and `proof_bundle: null` on their next edit — this is correct forward-only migration behavior, not data loss.

Skill updates switching from body parsing to frontmatter reading are part of the feature's implementation scope. Three skills reference proof_bundle by name; AC references are more diffuse but all agents consuming `show_task` output see the new field automatically.

### 8. MCP and Cockpit Surface

**MCP:** `create_task` gains `ac` and `proof_bundle` parameters. `edit_task` gains `ac`, `add_ac`, `remove_ac`, and `proof_bundle`. `show_task` response includes both fields via `TaskFull`. `list_tasks` response includes `proof_bundle` via `TaskSummary`.

**Cockpit:** Deferred to follow-up (D5). The cockpit mutation route (`routes/mutation.py`) and view layer (`view.py`) will need updates when cockpit editing surfaces these fields, but that's out of scope for this feature.

## Key Trade-offs

1. **Dual AC API adds edit_task complexity** — but matches actual usage patterns (decomposition = full list, review = surgical). The mutual exclusion rule keeps semantics clean. The alternative (atomic-only) forces decomposition skills into awkward multi-call flows.

2. **Hardcoded proof_bundle frozenset creates a code-level coupling to taxonomy** — but the taxonomy is a product constant that changes rarely. Config-driven validation (like status/priority) would be consistent but over-engineered for ~15 combos. A taxonomy update is a one-constant change.

3. **AC excluded from TaskSummary limits list-view utility** — but no consumer needs AC in list views, and the payload cost of embedding lists in every summary is unjustified. `show_task` provides full spec when needed.

4. **Search extension is a deliberate contract change** — moving AC content from body to frontmatter would otherwise make it unsearchable. The extension preserves existing discoverability. Tests must be updated.

5. **Forward-only migration means mixed boards during transition** — but the precedence rule (frontmatter wins) is simple, per-task, and organic. No migration script required at the engine level.

## Warnings

- **`_CANONICAL_FIELDS` is duplicated** in storage.py and potentially migrate.py. Both must be updated. Consider a shared constant.
- **Cockpit mutation routes** will need AC/proof_bundle parameters when UI editing is added (follow-up task). The cockpit view layer also has its own task model that will need the fields.
- **AC line identity is string-based.** If agents use naming conventions (AC1:, AC2:), those are content conventions, not schema-enforced. Reordering or rewording an AC item is a remove+add, which changes identity. This is acceptable for the current use case.

## Confidence

**0.82**

Two Critic cycles tested the position. Accepted corrections on: validation layer split (model + AgentView, not model-only), search extension, normalizing validator, absent-vs-empty semantics. Rebutted challenges on: "existing" companion data (skill concern, not schema), body-native workflow coupling (rollout scope, not design), and dual taxonomy ownership (acceptable for product constant). Remaining uncertainty is in the search extension's behavioral impact and the exact proof_bundle canonical frozenset composition.
