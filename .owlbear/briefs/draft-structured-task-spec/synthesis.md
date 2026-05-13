# Synthesis — Structured Task Specification in Frontmatter

## Summary

Four domain panelists evaluated adding `ac` (list[str]) and `proof_bundle` (str | None) to task frontmatter. Broad structural agreement exists on field types, defaults, model hierarchy, and API shape. The primary unresolved tension is **where proof_bundle validation lives** (model vs engine), with downstream implications for normalization, corruption handling, and migration urgency. User M3 corrections (enum not regex; no AC in pick_tasks; ac_count rejected; AC in list_tasks 55/45) are incorporated and largely pre-resolve several panel disagreements.

## Convergences

### C1 — Field types and defaults (all four)

`ac: list[str] = Field(default_factory=list)` and `proof_bundle: str | None = None`. No panelist proposes alternatives. Matches existing `tags`/`depends_on` precedent for lists, `archival_reason` for optional strings. `None` means "not set" — no silent default.

### C2 — Enum validation for proof_bundle, not regex (all four + user correction)

Closed-set membership check against a hardcoded frozenset of valid combinations. User explicitly rejected regex. The combination space is small (~15 values). Architect, data, and security all converge on frozenset over Literal for practical extensibility.

### C3 — Model hierarchy placement (all four)

| Model | `ac` | `proof_bundle` | Consensus |
|-------|------|----------------|-----------|
| Task | Yes | Yes | Unanimous |
| TaskSummary | No | Yes | Unanimous — no list-view consumer for AC |
| TaskFull | Yes | Yes (inherited) | Unanimous |
| DispatchEntry | No | Yes | Architect strong yes; enduser recommended; data yes; security implicit |

User corrections lock this: no AC in pick_tasks, ac_count rejected.

### C4 — Dual mutation API for AC (architect; others non-objecting)

`edit_task` gets full replacement (`ac`) and atomic ops (`add_ac`/`remove_ac`) with mutual exclusion, following the `body`/`append_body` precedent. No panelist objects. Data's P6/P7 positions reinforce the add/remove semantics (append to end, remove by exact match, write-path uniqueness check).

### C5 — Search must extend to frontmatter AC (architect, enduser)

Moving AC from body to frontmatter makes AC text invisible to `list_tasks(search=...)`. Both architect and enduser flag this as a regression, not polish. Enduser calls it "the worst kind of UX failure because it looks like the system is working." No panelist disagrees.

### C6 — Forward-only migration is acceptable for AC (all four)

Pydantic defaults handle missing fields on read. No backfill script is required for AC correctness. Disagreement exists only on proof_bundle migration urgency (see D2).

### C7 — Cockpit UI deferred (D5, all four)

Out of scope for this feature. Unanimous.

### C8 — Actionable error messages (enduser, security; others compatible)

Failed mutations must return the attempted value, reason, and correction context. Enduser specifies exact patterns (duplicate AC, invalid proof_bundle, remove-not-found listing existing entries). Security reinforces write-time validation for actionable errors over silent exclusion.

### C9 — AC ordering is semantically meaningful (data, architect)

List, not set. Insertion order preserved. Agents reference items by position. Data explicitly warns against set/frozenset storage.

## Disagreements

### D1 — proof_bundle validation layer (2v2 split)

The central design tension. Where does proof_bundle validation and normalization run?

| Position | Advocates | Argument |
|----------|-----------|----------|
| **Model-level** `@field_validator` — normalize + validate at construction time | architect (L45–52), enduser (§4) | Single canonical authority. All surfaces return normalized form. Pydantic validators are the standard layer for type-level constraints. |
| **Engine-only** — model accepts any `str | None`, validate in `create_task`/`edit_task` | data (P2 correction, §Schema split), security (Risk 3, §Least-Privilege) | Model validation fires on read (deserialization). An unrecognized proof_bundle value written to disk (typo, taxonomy change, merge conflict) would trigger CorruptionError → task silently disappears from all views. Write-path validation catches bad values before storage; read-path accepts whatever exists. |

**Evidence favoring engine-only:** Data's P2 correction is self-revised and evidence-based — the Critic exposed that `_parse_task_file` runs model construction, so a `@field_validator` fires on read. Security independently verified that engine corruption handling silently excludes malformed tasks (engine.py:670–715). A model validator + corruption handler = invalid proof_bundle → invisible task.

**Evidence favoring model-level:** Architect argues proof_bundle is a product constant (not board config), making model validation appropriate. Enduser wants guaranteed canonical form across all surfaces without surface-specific normalization.

**Possible hybrid:** Normalize in the model (sort modifiers, lowercase) but validate membership only in the engine. This gives canonical form everywhere without read-path exclusion risk. Neither panelist explicitly proposes this, but it resolves both concerns.

### D2 — proof_bundle migration urgency

| Position | Advocates | Argument |
|----------|-----------|----------|
| Optional / forward-only | architect (§7), data (P5) | Pydantic defaults handle missing fields. No migration script required at engine level. |
| Non-optional / first-run recommended | security (Risk 1, Warning 2), enduser (§5) | proof_bundle controls test scope, challenger dispatch, review depth. Unmigrated tasks get `None` → no proof strategy → reduced verification rigor. "Optional migration is a split-brain factory." |

Security and enduser are stronger here. proof_bundle is integrity-relevant routing metadata — leaving it unset on existing tasks is not neutral, it's a verification gap.

### D3 — Skill update timing relative to schema change

| Position | Advocates | Argument |
|----------|-----------|----------|
| Same release | security (Warning 1, §Least-Privilege), architect (§7 implicit) | If frontmatter fields land but agents still read body text, split-brain is certain for every task. |
| Not explicitly addressed | data, enduser (flags body-gate breakage but doesn't specify timing) | — |

Security's warning is unambiguous: "Do not ship schema without skill updates." Architect implicitly agrees. No panelist argues for shipping schema first. This is effectively convergence, but enduser's body-gate evidence (dispatch clarity gate inspects body for AC) adds concrete scope to what "skill updates" means.

### D4 — _CANONICAL_FIELDS ordering

| Placement | Advocate | Logic |
|-----------|----------|-------|
| `...depends_on, ac, proof_bundle, blocked...` (spec fields cluster together after relationships) | architect (§4) | Clean frontmatter layout: identity → timestamps → taxonomy → relationships → specification → operational |
| `ac` after `depends_on` (list cluster), `proof_bundle` after `priority` (scalar metadata cluster) | data (P4) | Group by type shape rather than semantic category |

Minor implementation detail. Both are defensible. Architect's grouping is more semantically coherent.

### D5 — AC in list_tasks (user-flagged 55/45)

All four panelists lean toward omitting AC from TaskSummary. User flagged this as 55/45, worth discussing. No panelist provides a consumer use case. The question is whether future utility justifies the payload cost of embedding lists in every summary.

### D6 — Defense-in-depth limits on AC

Security recommends max-length (500 chars) and max-items (20) as "reasonable defense-in-depth but not security-critical." No other panelist addresses this. For a single-user laptop-resident system, these are low-risk guardrails that prevent accidental bloat but aren't load-bearing.

## Recommendation

Ship with the **engine-only validation** approach for proof_bundle (data + security position). The silent-exclusion risk from model-level validation is concrete and evidence-based — it's the failure mode that turns a fixable typo into an invisible task. Add a **normalizing pass** (lowercase, sort modifiers) at the engine write path so canonical form is guaranteed for all newly written values, while existing tasks with non-canonical strings survive read without corruption.

Promote proof_bundle migration from optional to **recommended first-run**. The verification-routing impact of unset proof_bundle on existing tasks is real, and the migration script is trivial (iterate task files, extract `Proof bundle: X` from body, write to frontmatter).

Ship skill updates (body → frontmatter reading) in the same delivery as the schema change. Scope the skill update list to the five agents security identified plus the dispatch clarity gate enduser flagged.

Keep AC out of TaskSummary for now (no consumer), but note the user's 55/45 signal — revisit if a consumer emerges.

**Confidence: 0.80** — High convergence on field types, model hierarchy, API shape, and search extension. The validation-layer split is the only structural disagreement, and the evidence favors engine-only. Remaining uncertainty: exact frozenset composition, whether the normalizing-without-validating hybrid satisfies architect/enduser's canonical-form requirement, and migration script scope.

## Open Questions

1. **Validation hybrid:** Should the model normalize proof_bundle (lowercase + sort modifiers) without checking membership, leaving membership to the engine? This would give canonical form on all surfaces (architect/enduser want) without read-path exclusion risk (data/security warn). No panelist explicitly proposes this — needs user decision.

2. **AC in list_tasks:** User flagged 55/45 pro. All panelists lean omit. Is there an anticipated consumer, or is this closed?

3. **Frozenset composition:** The exact set of valid proof_bundle values needs to be enumerated from `r-pipeline-protocol`. Bases: `skip`, `existing`, `smoke`, `behavioral`, `critical`. Modifiers: `+challenge`, `+reader`. All valid combinations = bases × modifier powerset? Or only specific pairings?

4. **AC naming convention:** Enduser recommends semantic prefixes (`AC-lint:`, `AC-tests:`) over ordinal (`AC1:`, `AC2:`). This is convention, not schema — but enduser warns it will calcify fast. Establish before launch or leave organic?

5. **Body-gate scope:** Enduser flags dispatch clarity gate and status predicates as body-coupled. Security flags five agent skills. What is the complete list of body-reading consumers that must migrate? This determines skill-update scope for same-release delivery.

6. **Defense-in-depth limits:** Max-length (500) and max-items (20) on AC — include as engine-level guardrails or skip for single-user system?

7. **Invalid proof_bundle on read:** If engine-only validation is chosen and a task file has an invalid proof_bundle, should the engine log a warning, annotate the task, or silently pass the raw string through? Data and security agree the model should accept it — but what does the consumer see?
