# Synthesis — Proof Bundle Taxonomy (Compare Mode)

**Working directory:** `.owlbear/briefs/draft-proof-bundle-taxonomy/`
**Mode:** compare
**Stances compared:** architect-proposal, data-proposal, enduser-proposal, security-proposal
**Date:** 2026-05-11

---

## Divergence Matrix

Only points where proposals differ are listed. Points of agreement are in the Common Ground section below.

| Decision Point | architect | data | enduser | security | Tension Level |
|---|---|---|---|---|---|
| **Axis count** | Single axis — 5-value enum (`skip`/`existing`/`smoke`/`behavioral`/`critical`) is the routing key directly | Two primary axes (`test` + `proof`) with two derived signals (`review` + `challenge`) | Single axis — 5 named labels under `proof:` prefix, identical values to architect | Two primary axes (`test` + `proof`) with one derived signal (`challenge`); code-reader derived mechanically from `proof` | **High** — fundamental structural split: architect+enduser vs. data+security |
| **Bundle indirection** | Bundle values ARE the routing key — no decomposition into sub-fields | Bundles are optional syntactic sugar; expanded to canonical `test:`/`proof:` fields at assignment time; consumers never read `bundle:` | No bundle concept — labels are the routing key directly | No bundles — rejected as indirection that creates audit risk from mapping-table drift | **Medium** — data proposes bundles-as-sugar; others treat labels as primary or reject bundles entirely |
| **Challenger default threshold** | ON for `behavioral` + `critical` only; `smoke` skips challenger by default | ON for any `test != skip` (i.e., `smoke` and above trigger challenger) | ON for `behavioral` + `critical` only; matches architect | ON for any `test != skip`; matches data | **High** — architect+enduser lower the threshold (speed); data+security keep it higher (scrutiny) |
| **Override surface** | Two append modifiers (`+challenge`, `+reader`); escalation only — cannot suppress defaults | Two override fields (`challenge`, `review`); can both escalate and suppress; derivation table is the default | One boolean override (`challenge:yes`); escalation only — minimal surface | One three-value field (`challenge: derived\|required\|skip`); skip triggers mandatory reviewer acknowledgment | **High** — architect+enduser allow escalation only; data allows full bidirectional override; security allows suppression but with friction |
| **Code-reader override** | `+reader` modifier forces code-reader dispatch on any bundle | No explicit code-reader override — must escalate `proof` to `full` | No code-reader override | No code-reader override — must escalate `proof` to `full` | **Medium** — only architect proposes a dedicated code-reader override |
| **File-path security guardrail** | Not addressed | Not addressed | Not addressed | Mandatory auto-escalation for security-sensitive file paths; non-overridable by architect; self-referential (pipeline skills are in the trigger set) | **High** — only security proposes this; others have no equivalent mechanism |
| **Proof-scope structure** | Free-text note in verdict: `Existing proof scope: tests/test_engine_*.py` | Structured `proof_scope` field with validation matrix (required when `proof:existing`, forbidden when `proof:full`, etc.) | Free-text in AC text alongside the label | Not specifically addressed | **Medium** — data proposes formal validation; architect+enduser use free text |
| **Legacy td:0 + existing-proof mapping** | Maps to `existing` — no challenger (intentional speed gain) | Maps to `test:none proof:existing` — challenger derived as `skip` per derivation table | Maps to `proof:existing` — no challenger | Maps to `test:skip proof:existing challenge:required` — deliberate escalation, more scrutiny than current behavior | **High** — security escalates legacy tasks; all others preserve or reduce current behavior |
| **Suppression audit trail** | Not applicable — suppression is structurally impossible (modifiers only escalate) | `challenge: skip` is a valid value with no mandatory audit trail | Not applicable — suppression is structurally impossible | `challenge: skip` is valid but triggers mandatory reviewer acknowledgment in verdict | **Medium** — data+security allow suppression; security requires paper trail; architect+enduser prevent it structurally |
| **Field naming** | `Proof bundle:` — single field in verdict | `test:` / `proof:` / `challenge:` / `review:` — multiple fields, some derived | `proof:` — single prefixed label | `test:` / `proof:` / `challenge:` — explicit fields | **Low** — cosmetic, but affects consumer parse logic and migration complexity |

---

## Common Ground

All four proposals agree on the following:

1. **`(td:0)` overload must be eliminated.** "No proof" and "existing proof required" are unambiguously distinguished in every proposal — this is the single highest-value change.

2. **Task-level annotation replaces per-AC-line `(td:N)`.** Per-line annotation is architect busywork; consumers already aggregate. Test-writer reads AC text for assertion granularity (D4 settled).

3. **Five routing categories.** All proposals produce the same five dispatch profiles (skip / existing / smoke / behavioral / critical), differing only in whether these are first-class values or derived from axis combinations.

4. **Named values over ordinals.** All proposals replace numeric `td:0/1/2` with self-documenting names. No proposal retains ordinal notation.

5. **Legacy mapping without task rewriting.** In-progress tasks use a compatibility mapping table; archived tasks are untouched. Legacy mapping is removed after pipeline clears.

6. **Challenger default reduction for low-risk work.** All proposals agree challenger should not fire on `skip` or `existing` tasks (absent explicit override). The threshold for `smoke` is disputed (see matrix).

7. **Code-reader dispatches only at the highest proof level.** All proposals agree code-reader fires for `critical`/`proof:full` by default. Only architect adds a separate override for lower levels.

8. **Rollout sequence.** All proposals target the same ~6 files: `r-pipeline-protocol`, `w-arch-review`, `w-tdd-red`, `w-tdd-green`, `w-code-review`, and agent dispatch tables.

9. **Auditor unchanged.** `w-task-verification` is not affected by routing reform — it verifies evidence artifacts exist, not routing signals.

---

## Open Questions

1. **Single axis vs. two axes?** The central structural question. Architect and enduser argue 0/10 spot-check divergence makes two axes redundant; data argues unambiguity-at-read-time justifies two fields even without divergence; security argues axis independence is necessary for decoupling adversarial review from test depth. User must decide whether the 0/10 divergence is conclusive evidence or an insufficient sample.

2. **Challenger threshold for `smoke`-level tasks?** Architect+enduser skip challenger at smoke (speed gain); data+security require it (scrutiny gain). The tension is directly between the stated primary driver (speed) and a meaningful security posture difference. This decision has measurable pipeline throughput impact.

3. **Should suppression of challenger be possible?** Architect+enduser make suppression structurally impossible (modifiers only escalate). Data allows suppression freely. Security allows it with mandatory reviewer acknowledgment. The tradeoff: structural impossibility is simpler but prevents legitimate "I know this doesn't need a challenger" cases; asymmetric friction is more flexible but adds a reviewer obligation.

4. **File-path security guardrail: adopt or defer?** Only security proposes auto-escalation for security-sensitive paths. The mechanism is self-referential (pipeline skills trigger their own challenger review). The other three proposals are silent on this — they neither endorse nor reject it. It could be added to any model as an independent feature. User must decide if this belongs in the initial reform or is a follow-up.

5. **Proof-scope: structured field or free text?** Data proposes a validated `proof_scope` field with a constraint matrix; architect and enduser use free-text annotation. Structured validation prevents "existing without naming what to run"; free text is simpler and doesn't require schema enforcement in YAML frontmatter.

6. **Code-reader override: dedicated modifier or proof escalation?** Only architect proposes `+reader` as a standalone modifier. All others require escalating `proof` to `full` to get code-reader. The question: does a dedicated override justify its complexity, or is "promote to critical" sufficient for the rare case where code-reader is wanted below full proof?
