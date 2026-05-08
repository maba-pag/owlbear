# Security Debate Log — Pipeline Review Rethink

## Round 1 — Initial Position → Critic

### Initial Position Summary

The proposed restructuring introduces one genuine trust boundary change (reviewer reads builder evidence instead of re-generating it). Risk is lower than it appears because "independent verification" was never truly independent — same model, same tool, no adversarial incentive. The real risks are: (1) prompt injection via malicious code could affect builder evidence without cross-check, (2) OWASP cognitive scanning is unreliable as sole security layer, (3) test immutability removal needs a replacement control.

### Critic Challenges (Round 1)

1. **Critical — Execution independence ≠ model identity.** Re-execution verifies execution state (clean workspace, correct commit scope, no artifacts), not just reasoning. Same model ≠ same execution context. The position collapsed two distinct verification dimensions.

2. **Critical — Reviewer context purity is a false premise.** The reviewer reads the same changed files as the builder. Prompt injection affects both agents equally. The protection from independent execution is evidence fabrication prevention, not context isolation.

3. **Critical — Auditor as security backstop is overstated.** Auditor trusts reviewer's code-level verdict, spot-checks 1-2 AC items, runs full regression suite. Green suite doesn't validate evidence provenance or proof quality. Auditor is a regression backstop, not a security backstop.

4. **Moderate — OWASP scanning is already conditional.** td:0 and td:1 skip code-reader entirely. Only td:2 gets OWASP cognitive scan via code-reader. The "uniform overhead" premise was already inaccurate.

5. **Critical — Immutability ≠ lifecycle cleanup.** Immutability prevents in-flight tampering; structural separation handles archival. Different threat windows, different controls. AC audit can miss semantic weakening that immutability would catch.

6. **Moderate — No risk classifier defined.** "Security-tagged tasks" assumes reliable tagging with no defined process, false-negative detection, or audit mechanism.

7. **Moderate — Security findings ≠ ordinary findings.** Batching is a throughput decision. Security auto-FAIL status and operational handling are separate from batch mechanics.

### Position Revisions After Round 1

- Acknowledged execution context verification as the real control being lost (not just "same model, same output")
- Corrected prompt injection model: both agents equally exposed, protection was independent execution not context purity
- Downgraded auditor from "security backstop" to "regression backstop with incidental security value"
- Corrected OWASP baseline: already conditional by depth, but identified td:0/td:1 coverage gap
- Separated immutability (in-flight tamper control) from structural separation (lifecycle management) as distinct problems
- Proposed quality-runner evidence provenance + test-file diff as replacement controls

## Round 2 — Revised Position → Critic

### Critic Challenges (Round 2)

1. **Critical — Metadata cross-check cannot falsify upstream evidence.** Metadata audit replaces an independent observation channel with reported-state verification. The reviewer loses the ability to independently produce contradicting evidence.

2. **Critical — Metadata scope is too narrow.** Commit hash + workspace cleanliness doesn't cover runtime configuration, dependency state, or environment toggles. "Preserves state verification" is overstated.

3. **Critical — Symmetric exposure is common-mode failure.** Equal exposure to malicious code means one poisoned source can mislead every LLM-based stage. This concentrates risk rather than neutralizing it.

4. **Critical — Coverage claims don't add up.** SAST misses design-level issues, cognitive review is only for tagged tasks, tagging catches false negatives via CI — but untagged design-level security changes fall through all three layers.

5. **Critical — Auditor catches logic flaws that ARE security flaws.** Security defects often present as logic flaws. Removing the auditor from the security model removes the downstream observer best positioned to catch this defect class.

6. **Critical — Test diff overclaims what it proves.** Semantic weakening (fixture design, mock shapes, negative-path removal) isn't detectable by assertion-line diffs. Multi-iteration tasks blur the "original commit" anchor.

7. **Moderate — Mitigations may recreate reviewer overload.** Adding commit cross-checking, test diffs, severity marking, and conditional cognitive review approaches the complexity being removed.

8. **Moderate — Batch severity labeling doesn't prevent dilution.** Auto-FAIL labeling is necessary but not sufficient — security items can be buried in long mixed batches even if labeled critical.

### Final Position Revisions

- Reframed core risk as **common-mode failure** (all LLM agents share the same vulnerability surface), not symmetric exposure
- Acknowledged auditor has **incidental security value** through logic-flaw detection without needing explicit security mandate
- Dropped test-assertion diff as a strong control — it proves less than claimed; replaced with AC-level coverage verification (reviewer's core job)
- Accepted metadata mitigation as **partial, not complete** — residual risk acknowledged and accepted
- Accepted risk classification will have **false negatives** — CI/SAST catches pattern-matchable gaps, design-level gaps in untagged tasks are the accepted residual risk
- Kept mitigations minimal to avoid recreating reviewer overload — security layering via different technology tiers, not LLM redundancy

### What Survived Both Critic Rounds

- CI/SAST as baseline independent security layer (different technology = no common-mode with LLM review)
- Evidence provenance binding (quality-runner metadata for commit/scope verification)
- Security findings retain auto-FAIL severity regardless of batching
- Auditor's logic-flaw detection as incidental security coverage
- Risk classification at task creation with accepted false-negative rate

### What Was Dropped or Revised

- "Independent verification was never truly independent" — revised to "independent execution verified state, which metadata partially replaces"
- "Reviewer context purity protects against prompt injection" — dropped entirely; common-mode failure model adopted
- "Auditor is NOT a security backstop" — revised to "not an explicit security backstop, but has incidental security value through logic-flaw detection"
- Test assertion diffs as tamper detection — dropped; overclaims provability
- "Full coverage" claims for reviewer + CI — revised to acknowledge residual gaps for untagged design-level changes
