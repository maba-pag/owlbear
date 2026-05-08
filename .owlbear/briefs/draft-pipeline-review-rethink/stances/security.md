# Security Stance — Pipeline Review Rethink

## Security Stance

The proposed pipeline restructuring is **acceptable with specific mitigations**. The changes shift the security model from LLM-vs-LLM redundancy (which has common-mode failure) to LLM+deterministic-tools layering (which has genuine failure-mode diversity). This is a stronger security architecture than the status quo — but only if the deterministic layer is actually built.

The status quo has a security illusion: the reviewer re-runs tests and does cognitive OWASP scanning, creating the appearance of independent verification. In reality, builder and reviewer are the same model reading the same code, sharing the same vulnerability to prompt injection. A malicious code comment that misleads the builder will also mislead the reviewer's cognitive security scan. The "independence" is execution-context verification (clean workspace, correct commit), not cognitive independence. This execution-context value is real but narrower than it appears.

The restructuring removes a real control (independent execution-state verification) but creates space for a genuinely independent control (deterministic SAST that has no common-mode with LLM reasoning). The net effect is positive — if the CI/SAST layer is implemented. Without it, there is a regression.

## Risk Assessment

### Risk 1: Common-Mode Failure (HIGH priority)

All LLM-based agents in the pipeline share the same vulnerability surface. A prompt injection via malicious code comments, filenames, or crafted test output can affect every agent that reads the contaminated files — builder, quality-runner, reviewer, and code-reader all consume the same workspace artifacts. Independent test re-execution provided no protection against this because the reviewer also reads the changed files.

**Blast radius if exploited:** A single poisoned source file can produce fabricated test evidence, bypass cognitive OWASP review, and present as a clean pass through the entire LLM-based review chain. The auditor's full-suite run catches regressions but not novel vulnerabilities that don't have existing test coverage.

**Mitigation:** CI/SAST tools (Semgrep, Bandit, or equivalent) operate on AST/pattern matching with no LLM reasoning. They provide a genuinely independent observation channel. This should run on every commit, not conditionally.

### Risk 2: Evidence Provenance Gap (MEDIUM priority)

When the reviewer stops re-executing tests and reads builder evidence instead, there is no mechanism to verify that the evidence was produced against the exact commit under review, from a clean workspace, with the correct test scope. The builder could (through prompt injection or context confusion) present evidence from a different commit or partial execution.

**Blast radius if exploited:** Reviewer approves code based on evidence from a different codebase state. Auditor's full-suite run may or may not catch this depending on whether the regression is detectable via the existing test suite.

**Mitigation:** Quality-runner evidence must include execution metadata: commit hash, workspace cleanliness indicator (uncommitted changes check), and executed test scope. The reviewer cross-checks commit hash against the task's commit record. This is partial — it verifies reported state, not observed state — but the residual risk is low given no adversarial incentive between agents.

### Risk 3: Loss of In-Flight Tamper Detection (MEDIUM priority)

Test immutability (TestFromAC_* WEAKENED/REMOVED = auto FAIL) was an in-flight control preventing builders from weakening assertions to make tests pass. Structural separation (task tests deleted at archival) solves the lifecycle problem but does not address the tamper window between test-writer and archival.

Assertion-level diffs against the test-writer's original commit are unreliable as a replacement: semantic weakening through fixture design, mock shape changes, and negative-path removal is not detectable by line diffs. Multi-iteration tasks further blur the "original commit" anchor.

**Blast radius if exploited:** Builder weakens test assertions in a way that still nominally satisfies AC wording, hiding implementation gaps. The reviewer's AC completeness audit might pass it if the weakened tests appear to cover the AC.

**Mitigation:** The reviewer's AC audit should verify coverage at the behavioral level: "does each AC have at least one test that would fail if the AC requirement were violated?" This is the reviewer's core competency (forced attention on completeness) and doesn't require mechanical diff infrastructure. Not as strong as immutability, but immutability was causing test rot — this is the intentional trade-off.

### Risk 4: Untagged Security-Relevant Changes (LOW-MEDIUM priority)

The proposed model relies on planner/architect tagging tasks as security-relevant to trigger cognitive OWASP review. Changes that introduce security-relevant code (auth boundaries, input validation, data flow) without being tagged will receive only CI/SAST scanning, missing design-level security concerns that SAST cannot detect.

**Blast radius if exploited:** Design-level security flaws (broken trust boundaries, authorization bypasses, data exposure beyond intended boundaries) in untagged tasks pass without cognitive review.

**Mitigation:** CI/SAST catches pattern-matchable vulnerabilities regardless of tagging. The residual gap is design-level security in untagged tasks. This is accepted as the cost of not running cognitive security review on every task. The planner and architect both evaluate tasks — two opportunities to identify security relevance. If empirical false-negative rates are too high, expand the tagging heuristic or make cognitive security review unconditional for tasks touching specific directories (auth, API boundaries, data handlers).

## Compliance Implications

This is a laptop-resident development tool with no external users, no multi-tenant data, and no production deployment surface. Traditional compliance frameworks (SOC2, GDPR, PCI) do not apply. The compliance-relevant question is: does the pipeline produce code that meets the workspace's own security standards?

The answer is **yes, with the CI/SAST layer**: deterministic scanning catches OWASP Top 10 patterns that LLM cognitive review is unreliable at detecting anyway (hardcoded secrets, injection patterns, insecure deserialization). The cognitive review layer adds value for design-level concerns that SAST cannot detect, applied conditionally to security-tagged tasks.

## Least-Privilege Recommendations

1. **Quality-runner evidence should be a direct artifact, not builder-mediated.** The builder should not summarize or reformat quality-runner output. The reviewer reads the quality-runner's structured output directly. This removes the builder as an intermediary in the evidence chain. (Addresses evidence fabrication risk without re-execution cost.)

2. **CI/SAST must run on every commit, unconditionally.** This is the baseline security layer that replaces the reviewer's per-task cognitive OWASP scan for td:0/td:1 tasks. It is not optional or conditional. Without it, td:0/td:1 tasks have zero security scanning (same as today, but now acknowledged as a gap).

3. **Security findings retain auto-FAIL severity in batched output.** Batching all findings (Locked #3) is acceptable, but security vulnerabilities must be clearly separated in the batch output and retain pipeline-stopping severity. The builder must address security findings before non-security findings.

4. **Auditor should retain awareness that logic flaws can be security-relevant.** The auditor should not receive an explicit OWASP mandate (that recreates mandate impurity). But its existing logic-flaw detection naturally covers security defects that present as logic errors. This incidental coverage should be preserved, not designed away.

5. **Do not add new reviewer controls that recreate the overload.** The mitigations above are deliberately minimal. Commit-hash cross-checking and AC-level coverage verification are lightweight additions to the reviewer's existing mandate. Do not add assertion-level diffs, coverage enforcement thresholds, or multi-phase security protocols — these recreate the complexity being removed.

## Warnings

1. **Without CI/SAST, this restructuring is a security regression.** The current reviewer provides unreliable but nonzero cognitive security scanning on td:2 tasks. Removing independent execution without adding deterministic scanning creates a net loss. The CI/SAST layer is not an enhancement — it is the minimum viable replacement for the control being removed.

2. **Common-mode failure is the systemic risk, not agent cheating.** The pipeline's security threat model should be "prompt injection via workspace artifacts" not "adversarial agents." All mitigations should assume that any single contaminated file can affect every LLM-based agent. Defense-in-depth requires non-LLM layers, not more LLM layers.

3. **The first-principles stance's "one checker with two phases" proposal amplifies common-mode risk.** Collapsing reviewer and auditor into a single agent means one prompt-injected context contaminates both completeness and soundness checks in a single invocation. Keeping them as separate agents with separate context windows provides at least context-refresh between checks. The locked decision to keep them separate (Locked #8, decisions.md) is the correct security call.

4. **Risk classification at task creation is early-binding — security relevance can emerge during implementation.** A task tagged "non-security" at creation can become security-relevant when the builder introduces helper reuse, boundary changes, or scope drift. CI/SAST is the safety net for this — it operates on the code as-written, not as-planned.

## Confidence

0.76

Position hardened through two Critic cycles. Confident in the common-mode failure framing and the CI/SAST layering recommendation. Less confident in the evidence-provenance mitigation (partial by design) and the accepted false-negative rate for untagged security-relevant changes. The overall restructuring is sound from a security perspective — the move from LLM-redundancy to LLM+deterministic layering is architecturally superior — but it requires the deterministic layer to actually exist before the LLM redundancy is removed.
