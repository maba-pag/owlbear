# Architect — Critic Debate Log

## Cycle 1

### Draft Position Summary

AC as `list[str]` following tags pattern with dual API (full replacement + atomic add/remove), proof_bundle as `str | None` with model-level frozenset validation, placement in _CANONICAL_FIELDS after depends_on, proof_bundle in TaskSummary but AC excluded.

### Challenges Received

1. **Body-frontmatter coupling with dispatch gates and skills (critical).** Dispatch clarity gate and skills read AC/proof_bundle from body. New frontmatter-only tasks could break routing.
2. **"existing" bundle needs companion scope data (critical).** Validating the label without modeling the companion datum (e.g. which existing tests to reference) validates the least important part.
3. **Frozenset validator doesn't handle modifier canonicalization (moderate).** Hardcoded membership check only works on already-canonical inputs.
4. **AC excluded from search (moderate).** If AC leaves the body, engine search (title+body) no longer finds AC content.
5. **Dual AC API has unresolved mutation precedence (moderate).** No established invariant for when both `ac` and `add_ac`/`remove_ac` appear in the same call.
6. **Set semantics don't fit AC well (moderate).** Tags have identity-based semantics; AC items are content strings where near-duplicates could collide.
7. **proof_bundle in TaskSummary/DispatchEntry is unsupported by current surfaces (moderate).** No filter or routing currently uses proof_bundle.

### Responses

1. **Acknowledged, scoped.** Dispatch clarity gate checks body quality (bullets/numbered content), not AC specifically. Skill updates switching from body to frontmatter are the feature's rollout scope, not schema design. Added precedence rule: frontmatter authoritative when present, body fallback when empty.
2. **Rebutted.** Companion scope data is task-specific operational context belonging in body/AC items. The field validates the category; scope details are a skill concern. Over-coupling model to skill-layer semantics that change faster.
3. **Accepted.** Validator should normalize modifier order and deduplicate before validation. Model becomes the single canonicalizing authority.
4. **Accepted.** Search should extend to match AC items alongside title and body. Deliberate contract improvement.
5. **Accepted.** Mutual exclusion: if `ac` and `add_ac`/`remove_ac` appear in same call, validation error. No precedence — mutual exclusion.
6. **Acknowledged, held.** AC items are distinct specification statements. Exact string matching for add/remove is simpler and more predictable than index-based approaches. Near-duplicate collision is a content quality issue.
7. **Softened.** Removed "useful for filtering" claim. Kept in TaskSummary because single string is near-zero cost and enables future utility without model change.

---

## Cycle 2

### Refined Position Summary

Incorporated precedence rule, normalizing validator, search extension, mutual exclusion for dual API. Softened TaskSummary/DispatchEntry justification.

### Challenges Received

1. **Absent vs empty persistence during rewrites (critical).** `write_task` serializes full model — on any unrelated edit, legacy tasks gain `ac: []` and `proof_bundle: null`, erasing the absent/empty distinction.
2. **Dual AC mutual-exclusion enforcement location (critical).** Position says "Model only" for validation but mutual exclusion is an API concern, not a model concern. Multiple mutation surfaces exist (engine, AgentView, MCP, cockpit).
3. **Body-native workflow contract is deeper than rollout (critical).** Skills and routing logic explicitly read from body. Source precedence is architectural, not just rollout.
4. **Search extension is a contract change (moderate).** Documented API and tests anchor title+body only. AC matches would be a behavioral surprise.
5. **Model-level normalizer creates dual taxonomy ownership (moderate).** Skills define the taxonomy; hardcoding in model means taxonomy changes require code changes in two places.
6. **DispatchEntry proof_bundle lacks current routing value (moderate).** Dispatch selects agents by status, not proof_bundle. Orchestrator dispatches by task ID.

### Responses

1. **Accepted as non-issue.** This is actually correct behavior — any task that gets edited gains new fields with defaults. Forward-only migration happens organically. `ac: []` and `proof_bundle: null` are semantically correct defaults for legacy tasks. The "absent" state has no semantic meaning distinct from "empty."
2. **Accepted, corrected.** Model validates field types and proof_bundle values. API-level mutual exclusion (`ac` vs `add_ac`/`remove_ac`) belongs in AgentView.edit_task, following the existing `body`/`append_body` precedent at AgentView:697. Updated stance to: model for type/value validation, AgentView for API-level mutual exclusion.
3. **Acknowledged, scoped.** Skills switching read source from body to frontmatter is part of the feature's implementation scope. The precedence rule (frontmatter wins when present) is an architectural statement. The skill updates are bounded (3 skills reference proof_bundle, AC references are diffuse but all consume show_task output).
4. **Accepted as deliberate improvement.** The contract should be updated. Removing AC from searchable content would be a regression. Document the change, update tests.
5. **Acknowledged, position held.** Taxonomy changes ~once per year. A one-line constant update is acceptable. The alternative (config-driven) over-engineers for a product constant. Status/priority are config-driven because they're board-specific; proof_bundle taxonomy is product-wide.
6. **Acknowledged, position held.** Including proof_bundle in DispatchEntry is forward-looking and near-zero cost. Even without routing changes, agents see the field in dispatch output.

### Blind Spots Addressed

- Non-MCP mutation callers (cockpit routes): noted — implementation must update cockpit mutation route if it exposes AC/proof_bundle editing.
- AC line identity/numbering: out of scope for schema. Naming convention (AC1:, AC2:) is content convention, not schema concern.
- Orchestration consumption: acknowledged that adding fields doesn't change behavior; it enables future behavior.

---

## Position Evolution

| Aspect | Draft | After Cycle 1 | After Cycle 2 |
|--------|-------|---------------|---------------|
| AC API | Dual (replacement + atomic) | + mutual exclusion rule | + AgentView enforcement |
| Validation layer | Model only | Model only | Model for types/values, AgentView for API rules |
| proof_bundle validator | Membership check | Normalizing + membership | Unchanged |
| Search | Not addressed | Extend to AC items | Deliberate contract update |
| TaskSummary | "useful for filtering" | Softened to "cheap, future-useful" | Unchanged |
| Source precedence | Not stated | Frontmatter wins when present | Unchanged |
| Absent vs empty | Not addressed | Not addressed | Non-issue — organic migration |

Final confidence: 0.82
