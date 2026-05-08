# Data Quality Debate Log — Pipeline Review Rethink

## Cycle 1

### Initial Position (pre-Critic)

Core claim: AC is the pipeline's schema contract, and the current system has no validation at the schema boundary. Every downstream failure traces to unvalidated input data.

Five positions:
1. AC must follow a single predicate schema template
2. Evidence handoff needs explicit data contracts (builder→reviewer→auditor)
3. Test lifecycle is a data retention problem — lost data when task tests deleted
4. Spiral detection is mechanical AC text analysis (pattern matching, not AI judgment)
5. Checker output should be structured findings with severity, not prose; confidence scores explicitly rejected

Initial confidence: 0.82

### Critic Challenges (11 findings, pressure: high)

**Critical challenges:**

1. **Over-claimed causality.** Draft said "5/5 worst tasks trace to vague AC. This is not correlation." Critic: the brief's own archive synthesis says spirals are multi-causal (bad AC + bad fixtures + proof scope creep + reviewer one-at-a-time discovery). Single-cause framing is inaccurate.

2. **AC schema too rigid for process requirements.** The locked outcomes include workflow predicates ("Planner cannot create unchecked AC", "Every agent gets role sharpening") that cannot be forced into `function(inputs) → output` form. The schema risks forcing implementation-shaped AC onto process-shaped requirements.

3. **AC schema doesn't address the actual spiral drivers.** An AC can satisfy the proposed template and still produce spirals from default-only fixtures, mock≠real shapes, and single-scenario proof. The schema constrains wording, not proof quality.

4. **Builder→reviewer evidence as single source of truth is brittle.** "Missing or malformed → FAIL, do NOT re-run" replaces duplicated verification with a single-artifact dependency. Missing section could mean failed serialization, not missing evidence.

**Major challenges:**

5. **Builder evidence fields too shallow for reviewer's actual job.** Pass/fail counts and coverage are telemetry. Reviewer's value is catching missed AC semantics and proof-quality gaps — the proposed contract doesn't surface that.

6. **Planner doesn't know durable test coverage.** Requiring planner to state "which AC are already covered by durable tests" assumes planner can inventory test coverage, which it cannot.

7. **Docstring metadata circularity.** Task tests are intentionally temporary; consolidation task is a "single point of failure." Embedding metadata in temporary artifacts that depend on the fragile preservation stage is circular.

8. **"Mechanical spiral detection" is carrying semantic weight.** "Are boundary conditions specified?" and "Does any AC reference internal state?" are not lexical checks — they require domain judgment.

9. **Case against confidence scores is asserted, not evidenced.** Certainty and impact are different dimensions; collapsing them into severity alone loses information.

**Moderate challenges:**

10. **Ownership inconsistency.** Position 1 says "reject back to planner" but the brief says architect rewrites. Different ownership, cost placement, and gate semantics.

11. **Data retention overstated.** Brief says 60% of task tests rot naturally — most are scaffolding, not durable knowledge.

**Blind spots surfaced:**
- Multiple data contracts exist (not just AC): proof artifacts, stage transitions, evidence, test lifecycle
- No evidence provenance (commit, timestamp, run ID, freshness)
- No treatment of partial/indeterminate states (interrupted runs, flaky tests, timeouts)
- Cross-AC and temporal invariants missing from single-line predicate model
- Schema versioning absent for handoff formats themselves
- Compliance theater risk: agents satisfying template rules while producing weak content

### Revisions Made

| Challenge | Response | Position changed? |
|-----------|----------|-------------------|
| Over-claimed causality | Acknowledged multi-causal pattern. AC is highest-leverage single fix, not sole cause. | Yes — weakened exclusivity claim |
| Schema too rigid | Split into Tier 1 (behavior) and Tier 2 (process) with shared verifiability rule | Yes — major restructure |
| Schema ≠ proof quality | Added explicit section: "AC schema does NOT solve proof-quality failures." Separated three remediation layers. | Yes — scope narrowed |
| Evidence brittleness | Changed from "FAIL, do NOT re-run" to "flag gap, attempt to verify from available evidence, do not silently compensate." | Yes — softened |
| Evidence too shallow | Added `proof_notes` field. Acknowledged deeper proof-quality data is reviewer's cognitive work, not a form field. | Partially |
| Planner doesn't know coverage | Reassigned durable-test inventory to consolidation-test writer. Planner provides AC + task IDs only. | Yes |
| Docstring circularity | Dropped mandatory docstrings. Consolidation-test writer uses AC + task tests + durable tests as inputs. | Yes — dropped mechanism |
| Semantic vs. mechanical | Honestly decomposed into lint (lexical) and semantic (AI judgment). Acknowledged both needed. | Yes — reframed |
| Confidence scores | Added `evidence_strength: direct|inferred|absent` as factual provenance indicator, not subjective confidence. | Yes — compromise |
| Ownership inconsistency | Fixed to "architect rewrites, not reject to planner." | Yes — aligned with brief |
| Data retention overstated | Tempered. Most task tests are disposable scaffolding. Some contain genuine edge-case knowledge. | Yes — weakened claim |
| Provenance blind spot | Added commit, timestamp, run_id to builder evidence contract. | Yes — new field |

### Revised Confidence

0.75 — Core positions held (AC as schema, structured evidence, multi-point fix needed). Main uncertainty: whether agents reliably produce structured evidence or whether compliance is theatrical.

## Exit

Position is solid after addressing Critic challenges. Major gaps (multi-causality, schema rigidity, proof quality separation, evidence provenance) are now covered. Remaining uncertainty (agent compliance with structured formats) cannot be resolved by design — requires empirical validation.
