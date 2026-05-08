# Synthesis — Pipeline Review Rethink

Sources: `context.md`, `decisions.md`, `research-notes.md`, `stances/architect.md`, `stances/data.md`, `stances/enduser.md`, `stances/security.md`, `stances/simplifier.md`, `stances/firstprinciples.md`.

---

## Summary

Six panelists evaluated the pipeline review rethink across architecture, data quality, end-user experience, security, simplification, and first-principles challenge. The panel converges strongly on seven of the eight locked outcomes and on the overall direction: sharpen role mandates, eliminate redundant mechanical checks, add upstream AC quality control, and replace LLM-redundancy security with LLM+deterministic layering. The main unresolved tensions are around evidence handoff formality, the exact shape of AC quality rules, reviewer finding categorization, and the consolidation-test trigger mechanism — all implementation-level decisions that don't threaten the direction.

---

## Convergences

### C1: Mandatory architect gate — universal agreement

All six panelists support routing every task through the architect before implementation. Architect (Joint 2): architect is the single AC quality owner, planner is a drafter. Data: AC is "the pipeline's primary schema contract" — validating it at entry prevents downstream amplification. Security: two evaluation points (planner + architect) for security-relevance tagging. FirstPrinciples: "insufficiently tested claim" on whether architect is necessary, but includes it as mandatory in the minimum design. Simplifier: includes architect as "AC rewrite + feasibility gate" in the cut role table.

**Implementation meaning:** The planner's routing logic changes — no direct `backlog → todo` path. Every task transits through architect. The `w-arch-review` skill and planner dispatch logic both need modification. The architect gets a fast-approve exit path (challenger validates AC → approve in one pass) to minimize per-task cost on well-specified tasks.

### C2: Reviewer stops re-executing tests — universal agreement

Simplifier: "already dead, bury it." Architect (Joint 3): "non-negotiable." Security: acceptable because the independent-execution value was execution-context verification (clean workspace, correct commit), not cognitive independence — and that value is replaceable with evidence provenance metadata. Data: builder's quality-runner output provides pass/fail status; reviewer reads it rather than re-running. EndUser: implicit (no objection). FirstPrinciples: "NO test re-run" in minimum design.

**Implementation meaning:** Remove test-execution dispatch from `w-code-review/SKILL.md`. Reviewer reads quality-runner output for pass/fail status and reads source files directly for AC completeness verification. The quality-runner invocation in the review stage is eliminated entirely.

### C3: Reviewer batches all findings — strong agreement with nuance

Architect: batch all findings, loop-breaker at 2 cycles. Data: structured findings with severity/evidence fields. EndUser: batch by default, but adds an escape valve — if the reviewer encounters a finding that invalidates the task's premise, it should escalate immediately rather than completing the full pass. Security: acceptable, but security findings must retain auto-FAIL severity and be clearly separated in the output.

**Implementation meaning:** `w-code-review/SKILL.md` changes from gate-on-first-failure to collect-all-findings. The finding output format needs structure (severity, AC reference, evidence). The escape-valve and security-severity rules are additive constraints on top of the batching default. Loop-breaker threshold drops from 3 to 2 batch cycles (architect's recommendation, pending empirical validation).

### C4: Structural test separation — universal agreement

All panelists support: task-scoped tests in `tests/` with `_{task_id}` naming (deleted at archival), durable tests in `serve/*/tests/` (survive indefinitely). FirstPrinciples originally proposed tagging as alternative but structural separation won on maintenance burden (zero-infrastructure vs. metadata drift). Architect (Joint 5): TestFromAC immutability rule must be revised — task-scoped tests are *expected* to be deleted at archival; only durable tests retain the immutability guard.

**Implementation meaning:** TestFromAC immutability revision is a prerequisite change (architect Joint 5). Reviewer skill must distinguish task-scoped vs. durable test paths. Archival hook (or planner-created consolidation task) handles the lifecycle transition. The 219 existing stale tests need a one-time migration task.

### C5: Two checking agents (reviewer + auditor), not one — 4/4 late-domain agreement

Architect: two agents with pure mandates. Data: separate attention on completeness vs. soundness+integration. EndUser: implicit (no proposal to merge). Security: explicitly warns that collapsing to one agent "amplifies common-mode risk" — one prompt-injected context contaminates both completeness and soundness checks. FirstPrinciples is the sole dissenter, proposing "one checker with two attention phases" but acknowledges uncertainty about whether sequential attention direction changes within one context window actually avoid contamination.

The locked decision (`decisions.md`) already resolves this: keep as separate agents. The panel evidence reinforces the decision — security's common-mode argument and the empirical data on distinct failure classes (reviewer = completeness, auditor = correctness+integration) provide the strongest support.

**Implementation meaning:** Both agents get rewritten skill files with purer mandates and explicit scope boundaries. The reviewer's checklist is fixed and exhaustive (architect: 3 items). Auditor drops AC spot-checking and focuses on full-suite regression, intent-vs-AC alignment, and logic flaws.

### C6: AC quality is highest-leverage fix — universal agreement

All panelists agree vague AC is the root cause of the worst iteration spirals (5/5 archive tasks). Data adds the important caveat: AC quality is necessary but not sufficient — proof-quality defects (default-only fixtures, mock≠real shape) and reviewer scope creep are independently necessary fixes. "Shipping only the AC fix and expecting spiral elimination will produce disappointment" (data warning #4).

**Implementation meaning:** A shared AC quality skill (`h-ac-quality` or equivalent) must exist before agent role rewrites ship. This is a delivery-order dependency (architect structural warning #4, data position).

### C7: CI/SAST as deterministic security baseline — strong agreement

Security: "without CI/SAST, this restructuring is a security regression." The current reviewer provides unreliable but nonzero cognitive security scanning — removing it without adding deterministic scanning creates a net loss. Architect: move mechanical security scanning (SAST) to CI, keep lightweight cognitive check only for security-tagged tasks. FirstPrinciples: CI as #6 in minimum design (full regression suite, not an agent).

**Implementation meaning:** CI/SAST (Semgrep, Bandit, or equivalent) must be configured and running before the reviewer's cognitive security scanning is removed. This is a sequencing dependency, not an optional enhancement. The reviewer retains a lightweight security attention-check only for tasks explicitly tagged `security`.

---

## Disagreements

### D1: AC schema formality — architect vs. data

**Architect** proposes 3 concrete rules: (1) function-scoped (name the function under test), (2) input→output pairs, (3) banned quantifiers without exhaustive enumeration. Quality test: "can a test-writer derive the exact set of test scenarios without ambiguity?"

**Data** proposes a two-tier schema: Tier 1 (Behavior AC) for code changes — similar to architect's rules but more formal. Tier 2 (Process AC) for workflow/role changes — names the agent/stage/artifact, specifies observable pipeline behavior change, verifiable by artifact inspection. Both tiers share one meta-rule: "every AC line must be independently verifiable by a downstream agent without access to the author's intent."

**Simplifier** wants minimal intervention — roles define cognitive work, not metadata emissions.

**Tension:** Architect's rules are simpler and cover the main failure mode (vague behavior AC). Data's two-tier model covers a real gap — the locked outcomes in this very brief are process AC that don't fit the function-call template — but adds schema complexity. The user must decide whether Tier 2 (Process AC) is worth the additional rule surface, or whether behavior AC rules plus informal process-AC handling is sufficient.

### D2: Evidence handoff formality — data + security vs. simplicity

**Data** proposes full structured evidence blocks: builder→reviewer (run_id, commit hash, timestamp, per-test results, coverage, lint, changed files, proof notes) and reviewer→auditor (AC mapping, per-AC evidence, structured findings, scope note). Warns that "silent compensation is the pipeline equivalent of NaN propagation."

**Security** agrees on provenance (commit hash, workspace cleanliness) and adds: quality-runner evidence should be a direct artifact, not builder-mediated — removing the builder as an intermediary in the evidence chain.

**Architect** proposes a lighter version: reviewer writes Review Evidence section with AC completion matrix, proof quality notes, and flagged concerns. Less formal than data's proposal but covers the key handoff.

**Simplifier** doesn't address evidence format.

**Tension:** The data+security position produces a more robust evidence chain with tamper resistance and freshness verification. The architect's position is lighter and may be more practical for initial rollout. The user must decide how much evidence structure to mandate upfront vs. iterate toward. Note: security explicitly warns that without the evidence provenance layer, the restructuring has a medium-priority evidence-gap risk.

### D3: Reviewer finding categorization — enduser position, others silent

**EndUser** argues the batching design *requires* a blocker/follow-up distinction: "a long undifferentiated list is more overwhelming than serial discovery." Findings should be categorized as **blocking** (AC not met, test unsound) vs. **follow-up** (improvement opportunity, proof depth enhancement). Warning: "this is not optional polish; it's a prerequisite for batching to deliver its UX promise."

**Architect** doesn't propose explicit categorization but achieves a similar effect by scoping the reviewer's checklist to exactly 3 items — anything outside those 3 goes to "flagged concerns" for auditor. This implicitly creates a two-tier output (in-scope findings = blocking, flagged concerns = follow-up).

**Tension:** Are these two approaches functionally equivalent? Architect's 3-item checklist creates a structural scope boundary; EndUser's blocker/follow-up creates a severity classification within findings. They could coexist: the reviewer's 3-item checklist defines what it checks, and within those checks, findings are categorized by severity. The user should decide whether explicit severity labels add value or whether the structural scope boundary is sufficient.

### D4: Consolidation-test trigger mechanism

**Architect:** Planner creates task D with dependencies on A, B, C during upfront decomposition. "Small maintenance cost beats unreliable state detection." Planner updates deps if scope changes. Auditor flags missing consolidation-test as backstop.

**Data:** Planner creates when the feature chain's final implementation task is created. "The chain endpoint is a planner judgment."

**EndUser:** Auto-create but fully visible on board, user can move/defer/retrigger.

**Tension:** Architect's "upfront during decomposition" vs. Data's "when final task is created" differ in timing but not in principle. The real question is whether the planner can reliably identify the chain endpoint upfront (architect assumes yes; scope changes may invalidate). EndUser's override capability is additive and compatible with either trigger. The user should decide whether the consolidation task is created at decomposition time (earlier, may need dep updates) or at final-task time (later, more accurate but risks being forgotten).

### D5: Temporary implementation lifecycle — acknowledged gap, no solution

**Architect** (structural warning #3): "Code can't be structurally separated like tests. The AC should explicitly note which implementations are scaffolding. The consolidation task should include replacing scaffolding implementations with durable ones. This needs more design work."

**FirstPrinciples:** Builder should NOT tag temporary code — builder has no lifecycle visibility. Planner or architect should mark temporary implementations.

**Tension:** All agree this is a real gap. Tests have structural separation; code does not. No panelist offers a concrete solution beyond "architect/planner marks scaffolding in AC." This is an acknowledged design gap that needs separate treatment — it should not block the rest of the pipeline rethink.

---

## Open Questions

### OQ1: Can proof-sufficiency be cleanly bounded between reviewer and auditor?

Architect: reviewer checks *structural* proof quality (test exists, asserts exactly, covers AC-named branches). Reviewer does NOT evaluate *correctness* of test logic — that's auditor territory. Data's checker output format (evidence_strength: direct/inferred/absent) provides a mechanism but doesn't resolve where the boundary sits. This is the highest-risk bleed point between the two agents and needs explicit examples in the skill files (what's in-scope vs. out-of-scope for reviewer proof-sufficiency checks).

### OQ2: How should the 219 existing stale tests be migrated?

Research notes mention this. Architect: migration task must happen AFTER TestFromAC immutability rule is revised (Joint 5). No panelist specifies whether this is a single cleanup task or gradual archival-triggered cleanup. Practical question for implementation sequencing.

### OQ3: What is the exact evidence format for quality-runner output?

Security recommends quality-runner evidence be a "direct artifact, not builder-mediated." Data specifies structured fields (run_id, commit, timestamp, per-test results). Neither specifies whether this is a file artifact, a task-body section, or a structured data record. The implementation mechanism affects tamper resistance.

### OQ4: How does the architect fast-approve path work mechanically?

All agree the architect should have a lightweight exit when AC are already good. Architect: "challenger approves in one pass → move on." But the challenger is currently defined in `w-arch-review/SKILL.md` Step 2.5 — its scope needs expansion to include AC quality validation, not just design decision validation. The exact skill changes need specification.

### OQ5: What happens when a task's security relevance emerges during implementation?

Security (risk #4): a task tagged "non-security" can become security-relevant when the builder introduces boundary changes. CI/SAST is the safety net. But should there be a mechanism for the builder or reviewer to retag a task as security-relevant mid-flight? No panelist specifies this.

---

## Recommendation

The panel evidence supports a phased implementation aligned with the simplifier's two-phase structure but incorporating the late-domain panelists' specificity:

**Phase 1 — Role boundaries and AC quality (atomic, ships first):**
1. Create shared AC quality skill (`h-ac-quality`) with architect's 3 concrete rules as baseline. Defer data's Tier 2 (Process AC) to empirical validation — adopt it if behavior-AC rules prove insufficient for workflow tasks.
2. Rewrite skill files for all 6 agents with purer mandates, starting upstream (planner → architect → test-writer → builder → reviewer → auditor).
3. Reviewer: 3-item checklist (AC→code mapping, test→AC alignment, structural proof sufficiency). Batch all findings. No test re-execution. Findings categorized as blocking vs. follow-up (enduser's prerequisite for batching UX).
4. Auditor: full suite regression, intent-vs-AC alignment, logic flaws. Reads reviewer's Review Evidence as a claim, does not re-verify AC completeness.
5. Mandatory architect routing in planner dispatch. Architect gets challenger-based AC validation with fast-approve exit.
6. Revise TestFromAC immutability: task-scoped tests (`tests/test_*_{task_id}.py`) expected to die at archival; durable tests (`serve/*/tests/`) retain immutability guard.
7. Loop-breaker at 2 batch cycles (architect's recommendation), with escalation to architect for AC refinement on cycle 3.

**Phase 2 — Infrastructure layers (ships after Phase 1 is validated):**
1. CI/SAST pipeline (prerequisite before removing reviewer cognitive security scanning on non-security-tagged tasks).
2. Evidence handoff formalization: start with architect's lighter Review Evidence section; add data's provenance fields (commit hash, run_id) and security's direct-artifact requirement once the basic flow is proven.
3. Consolidation-test lifecycle: planner creates at decomposition time (architect's recommendation), auditor flags missing as backstop, user can override (enduser).
4. One-time migration of 219 stale tests (after immutability rule revision).

**What this defers:** Temporary-implementation lifecycle (acknowledged gap, needs separate design work). Data's full two-tier AC schema (start with behavior AC rules, add process AC tier if needed). Full evidence-chain tamper resistance (start with basic provenance, harden iteratively).

**Confidence: 0.80**

High confidence on: role boundaries (C5), AC quality as highest leverage (C6), no test re-execution (C2), batching with categorization (C3+D3), mandatory architect (C1), structural test separation (C4). These have near-universal panel support and strong empirical grounding.

Lower confidence on: evidence handoff formality level (D2, 0.65 — right direction but optimal formality is uncertain), consolidation-test trigger timing (D4, 0.65 — both approaches are workable), proof-sufficiency boundary (OQ1, 0.60 — needs examples in skill files to validate the split works in practice).
