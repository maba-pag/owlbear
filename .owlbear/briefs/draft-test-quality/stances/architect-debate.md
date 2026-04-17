# Architect — Critic Debate Log

## Cycle 1 — Initial Position

### Architect Position (v1)
Two-tier test model (task-scoped transient, module-level permanent) with a test-curator agent as a new pipeline stage after review. Curator consolidates task-scoped assertions into module-level tests, deletes transient files. Coverage gate ensures no behavioral regression. Non-blocking degradation: if consolidation fails, leave file + create follow-up.

### Critic Challenges (8 total, 4 critical)
1. **Critical:** Coverage gate is insufficient — coverage can stay flat while losing assertions, boundary cases, and contract checks.
2. **Critical:** Curator's semantic judgments (equivalent/new/implementation-coupled) are fragile — task-scoped tests are the least reliable population for inferring durable intent.
3. **Critical:** Non-blocking fail-open ("leave file, create follow-up, advance anyway") recreates the original failure mode for the hardest cases.
4. **Critical:** Pipeline insertion doesn't fix late detection — builders/reviewers still don't see cross-task breakage; curator only runs module tests, not full suite.
5. **Moderate:** "Permanent" module-level tests have no lifecycle either — recreates accumulation one level up.
6. **Moderate:** Not every test has a single module home — cross-module and integration tests lack clear promotion targets.
7. **Moderate:** Reviewer immutability is formally intact but AC-to-proof lineage is diluted when task files are merged and removed.
8. **Moderate:** Migration plan understates risk — batch semantic judgments over stale, agent-authored tests.

### Architect Response
- **Accepted C1:** Upgraded from coverage gate to assertion-level audit as primary verification.
- **Partially accepted C2:** Adopted conservative merge strategy — "when in doubt, promote." Curator targets obvious duplicates (60-70%), promotes the rest.
- **Accepted C3:** Replaced fail-open with quarantine mechanism — unconsolidated files move to `tests/quarantine/`, excluded from default suite.
- **Partially accepted C4:** Late detection reclassified as adjacent concern. Curator runs full module suite post-consolidation.
- **Accepted C5:** Module-level tests get lighter lifecycle via auditor-driven pruning.
- **Accepted C6:** Added promotion target hierarchy (module → integration → quarantine).
- **Accepted C7:** Traceability via comment annotations + kanban task body as primary audit trail.
- **Partially accepted C8:** Migration phased (triage → analyze → promote → quarantine).

**Critic confidence:** 0.29

---

## Cycle 2 — Refined Position (v2)

### Architect Position (v2)
Conservative merge strategy. Assertion audit replaces coverage gate. Quarantine for hard cases. Traceability comments. Promotion target hierarchy. Module-level pruning as second-order. Phased migration.

### Critic Challenges (8 total, 4 critical)
1. **Critical:** Quarantine = silent coverage loss. Hardest behaviors disappear from trusted suite while task advances.
2. **Critical:** "Delete broken" migration step treats current implementation as truth without proving tests are obsolete.
3. **Critical:** Curator mutates artifacts after review gate with no adversarial gate after that mutation.
4. **Critical:** Assertion-level mapping is too reductive — scenarios encode meaning in setup/mock interaction, not isolated assertions.
5. **Moderate:** "Mock-heavy = disposable" heuristic is too simple — many mock-heavy tests test boundary orchestration.
6. **Moderate:** "When in doubt, promote" conflicts with fast/right-sized suite goals.
7. **Moderate:** Traceability via comment provenance degrades in many-to-many merge histories.
8. **Moderate:** Cross-cutting behaviors have no stable home beyond "ambiguous."

### Architect Response
- **Accepted C1:** Replaced quarantine with pending-curation markers in the ACTIVE suite. Tests stay active (preserving coverage) but are tracked for escalation.
- **Accepted C2:** Migration phase 2 changed from "delete broken" to "analyze broken" — broken tests may signal code drift.
- **Accepted C3:** Auditor verifies curator work — diffs module-level tests, checks consolidation logs, verifies coverage.
- **Accepted C4:** Upgraded from assertion-level to test-method-level comparison. Complete scenario (setup + action + assertions) is the unit of promotion.
- **Accepted C5:** Dropped "mock-heavy = disposable" heuristic entirely. Only criterion is provable duplication.
- **Stood firm on C6:** Brief outcomes rank trust (#1) above speed (#2) above right-sizing (#4). When in doubt, promote is the correct priority order.

**Critic confidence:** 0.56

---

## Cycle 3 — Refined Position (v3)

### Architect Position (v3)
Test-method-level comparison. No quarantine — pending-curation markers in active suite. Auditor verifies curator. Conservative-only drop criterion. Analyze broken (not delete). Late detection = adjacent concern. Success metrics defined.

### Critic Challenges (8 total, 5 critical)
1. **Critical:** Module-activity-dependent cycle clock fails for dormant modules — pending files never advance.
2. **Critical:** Auto-archive on timeout doesn't prove behavior survives — can create false-green.
3. **Critical:** Promotion preserves implementation-coupled logic in bigger files — file count shrinks but signal quality unchanged.
4. **Moderate:** Audit checks paperwork (names) not semantic correctness.
5. **Moderate:** Module-scoped runs don't close the full late-detection loop.
6. **Moderate:** Mixed files spanning multiple modules have undefined ownership and cycle counting.
7. **Moderate:** Immediate follow-up vs. cycle-10 escalation is inconsistent.

### Architect Response
- **Accepted C1:** Added wall-clock fallback — 90 calendar days as alternative to 10 module cycles. Eliminates dormant-module blind spot.
- **Partially accepted C2:** Auto-archive is an imperfect backstop. Alternative (indefinite accumulation) is worse. 90% coverage floor provides lower bound.
- **Accepted C3:** Explicitly separated file lifecycle (curator) from test quality (auditor pruning). These are sequential, not simultaneous concerns. Curator solves accumulation; quality improvement is second-order.
- **Accepted C6:** Multi-module files have methods promoted individually to their respective targets.
- **Accepted C7:** Unified escalation model — single follow-up task with escalating priority (LOW → HIGH → auto-archive).

**Critic confidence:** 0.38

---

## Cycle 4 — Refined Position (v4)

### Architect Position (v4)
Wall-clock fallback. Explicit lifecycle/quality separation. Multi-module handling. Consolidated escalation model. Acknowledged irreducible risks.

### Critic Challenges (5 total, 3 critical)
1. **Critical:** Same as previous C1 reframed — unconditional ceiling claim is false if module stops receiving work (addressed by wall-clock but Critic noted the dormant module edge).
2. **Critical:** Auto-archive on timeout still doesn't prove behavior survives.
3. **Critical:** Promotion relocates implementation-coupled logic without transforming it — file wall shrinks but "green suite = trust" not established by curator alone.
4. **Moderate:** Audit verifies names not semantic identity — renames/splits break the chain.
5. **Moderate:** Pending files are still noisy for up to 90 days.

Blind spots: No independent verification of curator judgments. No success criterion for overlap reduction vs. relocation.

### Architect Assessment
Challenges are now cycling on the same three fundamental tensions:
1. Semantic judgment is irreducible (no design eliminates it)
2. Promotion ≠ quality transformation (acknowledged; quality is sequential concern)
3. Pending files are noisy but protective (coverage > noise, per brief priority)

These are design trade-offs explicitly acknowledged in the stance, not unaddressed flaws.

**Critic confidence:** 0.28

---

## Cycle 5 — Final Position (v5)

### Architect Position (v5)
Added: cross-module scenarios promoted whole to integration files (never fragmented). Final acknowledgment of irreducible risks.

### Critic Challenges (5 total, 3 critical)
1. **Critical (recurring):** Curator doesn't solve signal quality — promoted tests may still be implementation-coupled. "Green suite = trust" requires quality improvement too.
2. **Critical:** Multi-module fragmentation risk — cross-module interaction shouldn't be split across module files.
3. **Critical (recurring):** Auto-archive permits false-green states.
4. **Moderate (recurring):** Audit checks paperwork not semantics.
5. **Moderate (recurring):** Pending files remain noisy.

### Architect Final Assessment
Challenge 2 was valid and incorporated (cross-module scenarios stay whole in integration files). All other challenges are variations of tensions already acknowledged and bounded in the stance. The Critic could not find new structural flaws after cycle 3, cycling instead on the same irreducible trade-offs.

**Final Critic confidence:** 0.28

---

## Convergence Summary

**Resolved through debate:**
- Coverage gate → assertion audit → test-method-level comparison (cycle 1 → 2 → 2)
- Fail-open → quarantine → pending-curation in active suite (cycle 1 → 2 → 2)
- No adversarial gate → auditor verification (cycle 2)
- Mock-heavy heuristic → provable-duplication-only (cycle 2)
- Fixed cycle clock → wall-clock fallback (cycle 3)
- Multi-module fragmentation → whole-scenario integration promotion (cycle 5)

**Acknowledged as irreducible trade-offs:**
- Semantic judgment in equivalence detection (all cycles)
- Promotion ≠ quality transformation (cycles 3–5)
- Pending-curation noise vs. coverage protection (cycles 2–5)
- Auto-archive imperfection (cycles 3–5)
