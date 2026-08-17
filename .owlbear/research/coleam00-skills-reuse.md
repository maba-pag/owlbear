# Reuse Assessment: coleam00/skills

> **Owning task:** User-requested comparative research; no Delivery Change
> **Date:** 2026-08-16
> **Question:** Which complete skills, partial skills, concepts, or individual sentences from `coleam00/skills` can improve OwlBear without weakening its native authority model?

## 1. Context And Question

The external repository was evaluated at the exact commit
[`ecef6ffd4caa0b23a8c79601c1215b1e2908ac72`](https://github.com/coleam00/skills/tree/ecef6ffd4caa0b23a8c79601c1215b1e2908ac72).
The corpus contains exactly 33 `SKILL.md` files. All 33 skill bodies were read, together with the
referenced Markdown files for `ablate-ai-layer`, `ast-grep`, `build-dark-factory`, `skills-create`,
and `worktree-create`.

The comparison asks a stricter question than whether a skill is useful in isolation. A candidate must
also fit GitHub Copilot in VS Code, OwlBear's `w-`/`r-`/`h-` skill model, and the native Delivery
lifecycle: `design -> plan -> sequential build -> completed`. In particular, a useful idea must not
replace claim custody, exact-commit evidence, independent review, typed transitions, recovery, or
provider-owned publication.

### Evaluation method

1. Pin the external source to one immutable commit and inspect the complete skill corpus.
2. Record the external runtime assumptions: Claude Code frontmatter, Claude hooks, `gh`, conventional
   branches, direct commits, pull-request writes, and human-owned PR review.
3. Compare each skill with the nearest OwlBear authority or runtime implementation.
4. Classify the result as `adapt now`, `adapt selectively`, `already stronger`, `reference only`,
   `concept only`, or `reject`.
5. Preserve recommendations at the smallest useful unit: a native workflow, a handbook principle, a
   validation rule, or one sentence. Do not copy a whole skill when only its reasoning is reusable.

## 2. Sources Studied

| Source | URL or path | Material studied | Evidence limit |
|---|---|---|---|
| `coleam00/skills` | [Exact pinned tree](https://github.com/coleam00/skills/tree/ecef6ffd4caa0b23a8c79601c1215b1e2908ac72) | 33 external `SKILL.md` bodies | Static source inspection; external code was not executed |
| `build-dark-factory` references | `references/automation.md`, `deployment.md`, `guidance-layer.md`, `interview.md`, `setup.md`, `validation-harness.md` | Harness design, interview defaults, deployment loop, validation and autonomy boundaries | Read as design material; no factory was installed or run |
| `skills-create` references | `references/creating-skills.md`, `refactoring-skills.md`, `skill-standards.md`, `validation.md` | Skill structure, progressive loading, compression, and validation | Compared with OwlBear's native schema; not copied |
| OwlBear skill model | [share/README.md](../../share/README.md), [h-agent-structure](../../share/skills/h-agent-structure/SKILL.md) | Artifact types, loading tiers, source-of-truth rules, validators, and forbidden content | Local source authority |
| OwlBear shaping and Delivery | [w-design-session](../../share/skills/w-design-session/SKILL.md), [w-frontier-planning](../../share/skills/w-frontier-planning/SKILL.md), [w-packet-building](../../share/skills/w-packet-building/SKILL.md), [w-change-finalization](../../share/skills/w-change-finalization/SKILL.md), [w-orchestration](../../share/skills/w-orchestration/SKILL.md) | Native design, planning, build, review, recovery, and publication workflow | Local source authority |
| OwlBear quality and governance | [h-ac-quality](../../share/skills/h-ac-quality/SKILL.md), [r-challenger-protocol](../../share/skills/r-challenger-protocol/SKILL.md), [r-workspace-governance](../../share/skills/r-workspace-governance/SKILL.md), [w-test-curation](../../share/skills/w-test-curation/SKILL.md) | Acceptance proof, advisory review, scoped commits, artifact placement, and durable test curation | Local source authority |
| Delivery implementation and tests | [delivery_runtime.py](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py), [change_workspace.py](../../serve/delivery/src/owlbear_delivery/change_workspace.py), [portfolio_application.py](../../serve/delivery/src/owlbear_delivery/portfolio_application.py), [worktree authority tests](../../tests/test_delivery_worktree_authority.py) | Exact-head receipts, managed worktrees, claims, transitions, finalization, and publication | Static source and test inspection; no live Delivery run was benchmarked |

## 3. Analysis

### 3.1 System-level conclusion

Cole's repository is strongest as a collection of process heuristics around empirical validation and
AI-layer maintenance. It is not a suitable source for OwlBear's control plane. The external PIV loop
assumes a conventional branch per ticket, direct Git commits, `gh`-mediated pull requests, and a human
orchestrating a mostly prose-defined sequence. OwlBear already represents those decisions as native
claims, managed Change worktrees, exact-head receipts, advisory review receipts, typed transitions,
recovery operations, and provider-observed publication.

The most valuable external distinction is between:

- **soft guidance**, which an agent may optimize around; and
- **hard proof or control**, which should be enforced by a hook, schema, validator, test, or runtime
  operation.

That distinction is already documented locally in [share/README.md](../../share/README.md), but Cole's
validation-harness material supplies useful concrete tests for it: positive proof markers, an
independence line between builder-visible and evaluator-only checks, protected governance files,
holdout scenarios, mutation checks, and the rule that empty output is not a pass.

### 3.2 Highest-value concepts to adapt

| Priority | Candidate | Recommendation | Benefit | Cost or limitation | Main risk | Suggested owner | Confidence |
|---|---|---|---|---|---|---|---|
| 1 | `ablate-ai-layer` | Adapt as a report-only experiment for bounded completed work | Measures whether a rule, skill, or instruction changes a real task outcome instead of assuming that more guidance helps | Requires comparable runs, controlled scope, and a way to separate instruction effects from task variance | Optimizing a narrow benchmark or treating a noisy result as a governance decision | Ecosystem audit maintainer, with [w-agent-audit](../../.owlbear/skills/w-agent-audit/SKILL.md) as the nearest authority | High |
| 2 | `rules-check-drift` | Adapt as an advisory drift check over instructions, skills, source, and tests | Finds rules that are stale, now false, or missing an observed invariant; directly supports the Rule of Two and lean loading | Needs careful authority mapping and should remain report-only until repeated evidence justifies mutation | False positives create instruction churn or duplicate rules | Agent-ecosystem audit maintainer | High |
| 3 | `opportunity-scan` | Adapt as a report-only scan of real task artifacts and session evidence | Turns recurring failures and repeated corrections into a prioritized improvement queue | Requires privacy boundaries, durable input selection, and human or Delivery review of candidates | A self-improvement loop may promote anecdotes into authority without corroboration | Agent-ecosystem audit maintainer | High |
| 4 | `system-evolution-review` plus `system-execution-report` | Adapt the pair as a post-result process review, not a second proof system | Captures plan/result divergence, friction, and missing AI-layer guidance after exact-commit work is complete | Qualitative reports can duplicate compact Delivery receipts and must not become lifecycle authority | Prose retrospectives may overrule exact evidence or trigger speculative edits | Build/finalization workflow owner with the audit maintainer | High |
| 5 | `build-dark-factory` validation principles | Adapt only positive markers, empty-is-not-pass, evaluator independence, protected paths, holdouts, and selected mutation tests | Makes the existing evidence boundary more adversarial and helps distinguish skipped validation from passing validation | Holdouts and mutation suites cost maintenance and are only justified for high-risk surfaces | Importing the dark-factory autonomy model could bypass claims, review, publication, and user decisions | [h-ac-quality](../../share/skills/h-ac-quality/SKILL.md) with Delivery quality ownership | High |

The first practical experiment should be small and read-only: inspect a few completed task results and
their reviews, identify repeated process failures, and test whether the five concepts above produce
specific findings rather than generic advice. No experiment should edit native authority or publish a
Change merely because an external pattern recommends it.

### 3.3 Full 33-skill comparison

The matrix below is the complete corpus assessment. `Already stronger` means the external skill's
central behavior exists locally with a stronger identity, custody, or evidence boundary; it does not
mean the external wording has no useful sentence-level idea.

| External skill | Disposition and recommendation | Benefit or reason | Cost or risk | Suggested owner | Confidence |
|---|---|---|---|---|---|
| `ablate-ai-layer` | **Adapt now.** Use controlled instruction-removal or instruction-variant comparisons as report-only research. | Provides empirical evidence for whether AI-layer guidance earns its context cost. | Repeated runs are expensive; task variance and model variance can confound results; avoid turning one result into a rule. | Ecosystem audit maintainer | High |
| `agent-browser` | **Reference only.** Use only for browser-domain recipes when a native browser task needs them. | Browser interaction patterns may help a browser handbook. | It assumes a Claude/browser CLI and external credentials; OwlBear already has browser tools and `browser-mcp`. | Browser MCP and browser handbook owner | High |
| `ast-grep` | **Adapt selectively.** Preserve structural-search knowledge as an optional code-intelligence technique, not as a required dependency. | AST queries can find code structures that text search misses. | Adds a language/tool dependency and its output still needs boundary-valid proof. | Codebase-orientation or tooling owner | Medium |
| `build-dark-factory` | **Concept only.** Separate its validation-harness ideas from its unattended factory architecture. | Positive markers, holdouts, protected files, and staged autonomy expose proof gaps. | The full skill is large, provider-specific, and operationally coupled to GitHub automation. | Delivery architecture and `h-ac-quality` owner | High |
| `hooks-create` | **Adapt selectively.** Document native hook authoring only if repeated hook work justifies a workflow. | Treats deterministic hooks as the right home for guarantees such as write restrictions. | Claude hook events and settings do not map directly to Copilot; prose can overstate enforcement. | Hook and workspace-governance owner | High |
| `opportunity-scan` | **Adapt now.** Add a report-only scan for recurring failure patterns in real work artifacts. | Supplies a proactive complement to reactive bug fixing and audit. | Needs input curation, privacy boundaries, and a non-authoritative output path. | Agent-ecosystem audit maintainer | High |
| `piv-commit` | **Already stronger.** Do not port its direct commit procedure. | Its atomic-commit intent is covered by scoped `commit-owned` discipline. | Direct Git assumptions could mix unrelated paths or ignore task custody. | `r-workspace-governance` owner | High |
| `piv-create-pr` | **Already stronger.** Use native publication and readiness operations. | The external PR summary shape is harmless, but native publication binds exact heads and provider state. | Pushes and PR writes from a skill would bypass the user's publication boundary. | Delivery-GitHub and portfolio owner | High |
| `piv-fix-review-findings` | **Adapt selectively.** Keep one-finding-at-a-time repair and explicit deferral as a review style inside typed Delivery returns. | Focused repair reduces scope creep and makes chosen versus deferred findings visible. | A separate findings file can drift from the claim and exact commit. | `w-packet-building` and `r-challenger-protocol` owners | High |
| `piv-implement-issue` | **Adapt selectively.** Use RCA drift checks as planning evidence, without GitHub issue or branch mutation. | Prevents implementing a stale diagnosis and encourages regression tests. | GitHub issue state is not native task authority; direct branch creation conflicts with managed worktrees. | `w-research` and `w-frontier-planning` owners | High |
| `piv-implement` | **Already stronger.** Retain only its per-task validation emphasis. | Native Build binds maintained surfaces, scoped commit, observations, and independent review. | A generic checklist duplicates the result contract and can give false confidence without receipts. | `w-packet-building` owner | High |
| `piv-investigate-issue` | **Adapt selectively.** Make evidence chains and root-cause analysis optional research structure. | The 5-Whys evidence chain is a useful way to avoid stopping at symptoms. | `gh` posting, parallel agent assumptions, and a fixed RCA path are not OwlBear authority. | `w-research` owner | High |
| `piv-plan-implementation` | **Already stronger.** Keep the context-completeness and clarifying-question ideas, but use native planning claims. | OwlBear planning already binds task chains, dependencies, maintained surfaces, and proof boundaries. | A second plan format would create competing authority and may re-decide admitted Design. | `w-frontier-planning` and `h-ac-quality` owners | High |
| `piv-review-changes` | **Already stronger.** Use its findings-first review style only as communication guidance. | Native challenger review is advisory, exact-commit-bound, and routed by the caller. | A free-standing report is not sufficient proof unless it is bound to the reviewed commit. | `r-challenger-protocol` and build-reviewer owners | High |
| `piv-review-pr` | **Already stronger.** Do not import the open-PR review loop. | Finalization, publication checks, and provider acceptance cover the lifecycle more completely. | `gh`-driven review and direct approve/request-changes actions would duplicate provider authority. | `w-change-finalization` and Delivery-GitHub owners | High |
| `piv-run-full-loop` | **Reject.** Do not import hands-off chaining of planning, implementation, commit, and publication. | Convenience is not enough to justify removing native stage, claim, recovery, and user-decision gates. | High risk of uncontrolled writes, skipped review, lost recovery context, and unauthorized publication. | `w-orchestration` owner | High |
| `piv-slice-epic` | **Adapt selectively.** Use vertical slices, dependency graphs, and just-in-time planning within native task chains. | Produces smaller, testable units and makes parallelism explicit. | External tracker creation and conventional worktree parallelism do not define OwlBear execution. | `w-frontier-planning` owner | High |
| `piv-validate` | **Adapt selectively.** Keep explicit validation levels and command inventories; replace placeholders with local executable proof. | Helps prevent a nominal test command from being mistaken for complete validation. | Commands drift, and a generic template can report green without a meaningful boundary check. | Python/frontend validation owners and `w-packet-building` | High |
| `plan-architecture` | **Already stronger.** Map trade-offs, spikes, and user decisions to native Design sessions. | Its architecture-versus-intent separation is useful and already represented by Design authority. | A separate external architecture document could re-open or contradict admitted Design. | `w-design-session` owner | High |
| `plan-create-prd` | **Adapt selectively.** Use problem, evidence, hypothesis, non-goal, and open-question framing in idea refinement. | Improves intent quality before engineering decisions are made. | A new PRD authority would compete with native Design and is not required for every Change. | `w-idea-refinement` owner | High |
| `plan-create-stories` | **Already stronger.** Use acceptance-driven decomposition in the native published task chain. | Traceability from outcomes to bounded tasks is already mechanically represented. | Creating GitHub/Jira issues would add an external backlog authority and mutation surface. | `w-frontier-planning` and `h-ac-quality` owners | High |
| `prime-backend` | **Reference only.** Retain the idea of domain-bounded orientation for backend work. | Narrow context can reduce noise for a domain-specific investigation. | It assumes a different project layout and can omit OwlBear Delivery context. | `h-codebase-orientation` owner | High |
| `prime-codebase` | **Already stronger.** Use local codebase orientation, project instructions, and targeted reads. | The useful goal is covered without Claude-specific shell priming. | Broad inventory commands and generic assumptions can increase context cost and stale guidance. | `h-codebase-orientation` owner | High |
| `prime-frontend` | **Reference only.** Use as inspiration for a future frontend-specific handbook if demand recurs. | Separating frontend orientation from backend context is sensible. | Existing frontend instructions already own the applicable React/CSS conventions. | Frontend instruction and handbook owner | High |
| `rules-check-drift` | **Adapt now.** Add an advisory comparison of rules against current code, tests, and wiring. | Directly addresses stale instructions and missing current invariants. | Drift detection needs a precise authority map and should not auto-edit files. | Agent-ecosystem audit maintainer | High |
| `rules-create-global` | **Already stronger.** Use setup, `.github/copilot-instructions.md`, and OwlBear skill structure for rule derivation. | Its lean-rule goal aligns with the local Rule of Two. | A Claude `CLAUDE.md` replacement would misroute provider-specific authority and loading. | Setup and `h-agent-structure` owners | High |
| `second-brain-audit` | **Adapt selectively.** Apply stale-fact and deduplication ideas only through Memory lifecycle and curation. | Helps identify obsolete institutional knowledge without treating raw notes as truth. | Memory deletion, scope, and provenance have lifecycle consequences. | `w-mem-curation` and `h-memory-structure` owners | High |
| `setup-ai-tutor` | **Reject.** It is sample-project bootstrap material, not an OwlBear capability. | No reusable system behavior beyond ordinary setup narration. | It would introduce unrelated files, dependencies, and project assumptions. | None | High |
| `skills-create` | **Already stronger.** Use OwlBear's native structure, categories, references, loading tiers, and validators. | The external skill reinforces progressive loading and concise source-of-truth design. | Claude frontmatter, tool names, and forbidden-content boundaries do not match OwlBear. | `h-agent-structure` owner | High |
| `system-evolution-review` | **Adapt now.** Review completed task results for process divergence and candidate AI-layer changes. | Closes the loop between execution evidence and improvement of instructions or skills. | Requires disciplined separation between a review finding and an authority change. | Agent-ecosystem audit and test-curation owners | High |
| `system-execution-report` | **Adapt selectively.** Preserve concise qualitative deviations beside, not instead of, exact Delivery receipts. | Explains friction and plan/result differences that compact receipts may not capture. | Duplicated prose increases maintenance cost and must never override exact evidence. | `w-packet-building` and `w-change-finalization` owners | High |
| `worktree-create` | **Already stronger.** Use managed Change worktree creation, registration, recovery, and custody. | OwlBear can bind the worktree to Change identity and reviewed head. | Direct worktree setup can create unauthorized branches, copy unsafe config, or evade recovery. | `change_workspace.py` and `w-orchestration` owners | High |
| `worktree-merge` | **Reject.** Use native target synchronization and typed integration repair instead of an arbitrary merge branch. | Post-merge validation is a valid goal, but target identity and repair routing are native concerns. | Free-form merges can lose exact authority, conceal conflicts, or publish an unreviewed head. | Delivery integration owner | High |

### 3.4 Sentence-level and principle-level reuse

The following ideas are worth preserving as short native guidance, even when the surrounding skill is
not adopted:

| External idea | OwlBear-safe interpretation |
|---|---|
| Propose defaults from the user's PRD and repository instead of asking them to invent every detail | During Design or planning, present evidence-grounded options and ask only for decisions the native workflow cannot resolve. Keep the user-owned decision visible in the Design or request record. |
| Reflect each material answer back into a concrete artifact | Bind the answer to a Design package, plan task, request resolution, or Delivery transition rather than leaving it as conversational context. |
| A named finish line reduces interview fatigue | State the next gate and the artifact it will produce; do not keep asking questions after the shaping decision is sufficient. |
| Empty output is not a pass | A validation observation must identify a real command or procedure and an observable result; absence of output cannot satisfy acceptance. This aligns with [h-ac-quality](../../share/skills/h-ac-quality/SKILL.md). |
| Positive markers prove that the intended thing actually ran | Prefer explicit boundary observations, output markers, and persisted receipts over a zero exit code alone when startup or workflow execution is at issue. |
| The independence line matters | Keep builder-visible proof distinct from evaluator-only checks when a high-risk behavior could be optimized around. Do not claim independent review if the same mutable context controls both sides. |
| Protected governance and validation files matter | Keep hard restrictions in hooks, schemas, validators, or managed runtime operations; prose alone cannot protect a file. Existing write guards and worktree authority tests are the local precedent. |
| Holdouts and mutation checks test the evaluator | Use them only for selected high-risk acceptance surfaces, with clear ownership and maintenance; do not turn a generalized dark-factory harness into a default gate. |
| Scoped diffs and staged autonomy reduce blast radius | Preserve maintained surfaces, exact-commit review, sequential claims, and explicit user decisions. Autonomy should expand only after evidence supports it. |

## 4. Work List

> **Worklist updated:** 2026-08-17

This is the durable queue for working through the findings one at a time. The full matrix above is the
coverage record for all 33 external skills; this section selects the actionable candidates and records
the decisions that should not be rediscovered later.

### Status vocabulary

| Status | Meaning |
|---|---|
| `candidate` | Worth a future bounded implementation or design decision; not scheduled or started |
| `pilot` | Start with a small report-only or evidence-gathering experiment before implementation |
| `guardrail` | Preserve a boundary or validation rule while explicitly declining the external mechanism |
| `deferred` | Useful only when a named trigger or repeated need appears |
| `skipped` | Explicitly declined for the current queue because the proposed evidence or mechanism is too weak; reopen only with a concrete new justification |
| `already-covered` | Native OwlBear behavior is stronger; do not create duplicate work |
| `rejected` | Do not port under the current architecture; revisit only after an explicit architecture decision |

Confidence scores are calibrated confidence in the recommendation and fit, not predicted return on
investment. Scores above 90 mean the next action is clear; scores from 70 to 89 mean the direction is
sound but a pilot or boundary decision is needed; lower scores require more evidence before work begins.

### 4.1 Actionable candidates

| ID | Status | Candidate and potential use cases | Benefit | Risk / cost | Owner | Depends on | Confidence | Completion evidence |
|---|---|---|---|---|---|---|---:|---|
| `CWS-001` | `skipped` | Establish a small evidence set of completed Changes, exact-commit results, reviews, validation observations, and representative instruction versions. Use it to compare process outcomes without relying on memory. | Would give later ablation and opportunity work a reproducible baseline. | Selection bias, sensitive session content, and analysis time; the proposed baseline was judged too weak to justify the work now. | Agent-ecosystem audit maintainer | None | 94 | User explicitly requested that this baseline be skipped; dependent comparison work remains blocked unless a concrete stronger justification is recorded. |
| `CWS-002` | `deferred` | Reopen the `ablate-ai-layer` idea for report-only comparisons only when a stronger baseline justification or a specific suspected guidance-cost question exists. A future comparison would test one rule, skill, or instruction on matched bounded work. | Could measure whether guidance earns its loading and maintenance cost. | Without the intentionally skipped baseline, repeated runs would be noisy and easy to overinterpret; the experiment also costs operator and model variance control. | Agent-ecosystem audit maintainer | `CWS-001` | 91 | `CWS-001` was explicitly skipped, and this report does not define a specific rule-cost question or measurement plan. Reopen only with one of those triggers, then record the changed guidance, matched tasks, outcomes, confounders, and recommendation without mutating authority. |
| `CWS-003` | `already-covered` | Make bounded drift checking a default part of the agent audit, comparing instructions, skills, source, tests, and wiring without creating a separate workflow. Use cases include stale commands, contradicted architecture claims, duplicate rules, and new invariants with no owner. | Keeps the AI layer truthful and reduces context cost under the Rule of Two. | False positives can create instruction churn; authority mapping is laborious; auto-editing would be unsafe. | Agent-ecosystem audit maintainer | None | 95 | The default drift pass is defined in [w-agent-audit](../skills/w-agent-audit/SKILL.md); it requires evidence, canonical ownership, loading impact, and a bounded keep/strengthen/compress/move/delete disposition. |
| `CWS-004` | `deferred` | Reopen the privacy and retention boundary for `opportunity-scan` only when a concrete scan request or repeated process evidence justifies policy work. A future boundary would cover task artifacts, review findings, repeated corrections, and any selected session evidence. | Could make proactive improvement possible without treating private transcripts as an unbounded data source. | Privacy review, storage growth, redaction, and provenance requirements are premature without an intended scan. | Agent-ecosystem audit maintainer with workspace-governance owner | `CWS-001` | 92 | `CWS-001` was explicitly skipped, and no approved scan input, privacy boundary, or retention plan is defined here. Reopen after repeated corrections, failures, or a user-requested scan, then define allowed inputs, exclusions, retention, redaction, output, and action ownership before implementation. |
| `CWS-005` | `deferred` | Reopen the report-only `opportunity-scan` after the privacy boundary is defined and repeated evidence shows a real recurrence question. Candidate inputs include user corrections, blocked claims, validation failures, and repeated missing instructions. | Could convert recurring local evidence into a prioritized improvement queue. | A model may overfit to anecdotes or recommend a rule for a one-off failure; findings need independent challenge and an approved input boundary. | Agent-ecosystem audit maintainer | `CWS-004` | 92 | `CWS-004` is deferred, and recurrence is not measured because no scan corpus or protocol is active. Reopen only after the boundary exists plus repeated evidence or a user-requested scan, then produce a bounded report with evidence locators, recurrence count, impact, owner, and confidence; mutate no authority. |
| `CWS-006` | `already-covered` | Preserve triggered process learning in an optional sidecar beside, not inside, Delivery receipts. Use cases include plan/result divergence, unexpected friction, blocked assumptions, and useful deviations after a reviewed exact commit. | Preserves qualitative learning that compact receipts do not capture without burdening ordinary successful tasks. | Sidecars can drift from receipts; prose must never override exact commit, review, or lifecycle evidence. | `w-packet-building` and `w-change-finalization` owners | None | 93 | [h-process-observations](../../share/skills/h-process-observations/SKILL.md) defines triggers, placement, exact identity, fact/interpretation separation, and no-lifecycle-authority boundaries; both owning workflows load it conditionally. |
| `CWS-007` | `already-covered` | Provide an explicit `/deviation-audit` entry point for reviewing selected process observations and deciding whether a deviation belongs in code, tests, Design, Planning, a skill, an instruction, a prompt, a hook/runtime owner, or no change. | Closes the feedback loop from completed work to system improvement without putting placement logic into `agent-audit`. | Review can become speculative retrospection or duplicate code review; proposed changes need a separate owner and evidence threshold. | `w-deviation-audit` with agent-ecosystem, Delivery, and test owners | `CWS-006` | 92 | [w-deviation-audit](../skills/w-deviation-audit/SKILL.md) defines bounded inputs, exact evidence binding, placement classification, report-only routing, and no-mutation boundaries; [deviation-audit.prompt.md](../prompts/deviation-audit.prompt.md) is the thin user-facing dispatcher. |
| `CWS-008` | `deferred` | Reopen only if an accepted proof passes without exercising its claimed boundary, or repeated reviews identify weak observation evidence; do not add a universal marker or empty-output rule preemptively. | Avoids ceremony while preserving a concrete trigger for investigating semantic proof weakness. | A weak-proof case could remain undiscovered because the repository does not collect a proof corpus that tests this trigger. | `h-ac-quality` and Delivery quality owners | Evidence of an accepted weak-proof case | 95 | Static inspection found acceptance guidance, discriminating finalization observations, and exact-commit receipts, but the repository does not retain a corpus that tests whether accepted proof exercised its claimed boundary. Treat the trigger as unmeasured and reopen when such evidence is collected. |
| `CWS-009` | `skipped` | Do not add a separate evaluator-independence workflow, pilot, or receipt mechanism. Retain only the existing sentence-level distinction between builder-visible proof and independent review. | The general distinction is already present in PAT-001 without creating another process or authority. | A separate mechanism would add ceremony and maintenance without a current product or governance benefit. | `h-ac-quality`, `r-challenger-protocol`, and build-reviewer owners | None | 93 | Explicit user disposition: the separate evaluator-independence finding has no current value. Do not create comparison collection, holdout wiring, or Delivery fields for it. Reopen only with an explicit new justification tied to a named high-risk boundary. |
| `CWS-010` | `skipped` | Do not add a holdout-scenario pilot in the current queue. Retain the external pattern only as a future option for an explicitly approved high-risk boundary. | Avoids introducing protected-scenario maintenance and governance before a bounded product need is selected. | Skipping the pilot leaves no additional holdout mechanism for future work until a new decision reopens it. | Delivery quality owner | None | 91 | Explicit user disposition: skip this finding for the current queue. No holdout pilot, protected scenario, or general gate was added. Reopen only with an explicit high-risk boundary, owner, and justification. |
| `CWS-011` | `skipped` | Do not add mutation checks in the current queue. Retain the external pattern only as a future option for an explicitly approved high-risk test boundary. | Avoids mutation generation and survivor triage without a selected test boundary that would benefit from them. | Skipping leaves no mutation-based evaluator mechanism until a new decision reopens it. | Test-curation and domain test owners | None | 90 | Explicit user disposition: skip this finding for the current queue. No mutation set, survivor gate, or test-curation workflow was added. Reopen only with a named high-risk boundary, owner, and justification. |
| `CWS-012` | `skipped` | Do not add a generalized protected-surface inventory, guard-bypass audit, holdout surface, or secret-handling mechanism in the current queue. Retain the existing named-boundary approach and reopen only for an explicitly selected surface. | Avoids broad protection work without a selected boundary, owner, or concrete enforcement question. | Skipping leaves no additional protection mechanism for surfaces that have not been selected for review. | Workspace-governance and Delivery worktree owners | None | 94 | Explicit user disposition: skip this finding for the current queue. No protection inventory, generalized policy, new guard, holdout surface, or secret-handling mechanism was added. This is a queue/value decision, not a claim that all surfaces are protected or bypass-free. Reopen with a named surface, bypass, holdout, or secret-handling requirement. |
| `CWS-013` | `already-covered` | Add a developer-only native hook-authoring handbook for write guards, lint hooks, session-context hooks, and post-tool checks. | Makes deterministic guarantees easier to author consistently without changing runtime ownership. | The handbook must not duplicate hook contracts or encourage prose to claim enforcement. | Hook and workspace-governance owner | `CWS-012` evidence | 91 | Implemented as [.github/skills/h-hook-authoring/SKILL.md](../../.github/skills/h-hook-authoring/SKILL.md), covering event selection, explicit I/O and failure contracts, bounded placement, wiring, and negative-path validation. Runtime hooks, validators, and tests remain authoritative; no consumer seed wiring was added. |
| `CWS-014` | `deferred` | Reopen optional `ast-grep` guidance only after a concrete structural-search task shows that text search is insufficient. Potential uses include syntax-level patterns, API migrations, or unsafe constructs. | Could improve codebase analysis without making a new tool mandatory. | Installation and parser cost are premature; any result would still need boundary-valid proof and tool-availability checks. | Codebase-orientation or tooling owner | A concrete structural-search task | 88 | No qualifying structural-search task is retained in this research; that absence is not evidence that text search is sufficient. Reopen when a real task is recorded, compare text and AST search on that task, record setup cost and result quality, and choose handbook, dependency, or no action. |
| `CWS-015` | `skipped` | Do not add an RCA evidence-chain workflow, template, sidecar fields, or dedicated audit in the current queue. Retain existing bounded diagnosis and repair guidance. | Avoids new diagnosis ceremony and a competing repair authority without a selected failure that needs it. | Skipping leaves no additional RCA mechanism until an explicit value decision reopens the finding. | Research, challenger, and packet-building owners | None | 92 | Explicit user disposition: skip this finding for the current queue. No RCA template, evidence-chain workflow, sidecar fields, or dedicated audit was added. This is a queue/value decision, not a claim about uncollected diagnosis or repair outcomes. Reopen with a named RCA or repair-scope failure. |
| `CWS-016` | `already-covered` | Preserve the explicit no-port boundary for `piv-run-full-loop`, `worktree-merge`, direct PR/commit skills, and dark-factory autonomy. Use cases include future requests for unattended planning-to-publication loops or free-form branch integration. | Prevents convenience automation from bypassing claims, reviews, recovery, publication authority, or user decisions. | Requires maintaining a clear boundary as Delivery evolves; may feel slower than direct scripting. | Orchestration, integration, and Delivery-GitHub owners | None | 96 | Existing native orchestration, workspace-governance, wiring, managed-worktree, validator, hook, and Delivery authority controls preserve the boundary; no duplicate guardrail artifact is added. Any future exception requires an explicit Design decision with scoped proof. |

### 4.2 Deferred, reference, and already-covered ledger

These entries remain in the worklist so later work does not accidentally reopen settled questions:

| Aspect | Current decision | Potential use case or trigger | Owner | Confidence |
|---|---|---|---|---:|
| `agent-browser` | `deferred/reference` | Reopen only when a native browser task exposes a recipe gap not covered by the existing browser tools or `browser-mcp`; do not import its CLI, credential, or provider assumptions. | Browser MCP and browser-handbook owner | 94 |
| `prime-backend` and `prime-frontend` | `deferred/reference` | Reopen only after a concrete backend or frontend orientation failure, or repeated domain-specific work, shows that `h-codebase-orientation` and the existing frontend instructions leave a real gap; do not create competing orientation skills by default. | Codebase-orientation and frontend owners | 94 |
| `prime-codebase` | `already-covered` | Retain the useful staged orientation sequence, evidence-first navigation, task-shaped context, and stop conditions in `h-codebase-orientation`; revisit only after a concrete orientation miss or material context waste, and do not create a standalone `prime-codebase` skill. | `h-codebase-orientation` owner | 97 |
| `plan-architecture`, `plan-create-prd`, and `plan-create-stories` | `already-covered/adapt selectively` | Retain problem/evidence/non-goal framing, explicit architecture trade-offs, and acceptance-driven decomposition through the existing idea-refinement, Design, and frontier-planning owners; adapt only after a concrete shaping failure, and do not create a competing PRD, architecture, or tracker authority. | Design and frontier-planning owners | 95 |
| `piv-commit`, `piv-create-pr`, `piv-implement`, `piv-plan-implementation`, `piv-review-changes`, and `piv-review-pr` | `already-covered` | Retain scoped commits, per-task validation, context-complete planning, findings-first review communication, and exact-head publication checks through native Delivery owners; revisit only when a native receipt, review, or publication boundary demonstrably misses an external use case, and do not add unmanaged commit, PR, review, or provider mutations. | Delivery workflow owners | 98 |
| `worktree-create` | `already-covered` | Retain isolated execution, explicit branch/source-head identity, task-owned path boundaries, and cleanup/recovery through managed Change worktrees; revisit only after a managed-worktree recovery or custody failure, and do not add standalone manual worktree creation. | Change workspace and orchestration owners | 98 |
| `second-brain-audit` | `deferred/reference` | Reopen only after repeated stale-fact, deduplication, or scope failures demonstrate a gap in MCP memory curation; retain any useful report-only checks inside `w-mem-curation` and do not create a parallel audit or mutation authority. | Memory curation owner | 91 |
| `setup-ai-tutor` | `rejected` | Keep rejected: no current OwlBear beneficiary or maintained product boundary exists; reconsider only if the sample project becomes an explicit maintained product surface, through a separate Design decision rather than skill reuse. | None | 99 |
| Direct Claude frontmatter, Claude hooks, `gh`, conventional branches, and provider-specific setup | `rejected` | Keep rejected: do not silently translate provider-specific metadata, hooks, CLI mutation, branch conventions, or setup into OwlBear authority; reconsider only after an explicit provider-support architecture decision with a defined adapter boundary. | Ecosystem architecture owner | 99 |

### 4.3 Suggested execution order

Work one item at a time in this order unless new evidence changes the queue:

1. `CWS-002` remains deferred behind the skipped baseline and a concrete guidance-cost question; `CWS-008` remains deferred until its reopen trigger occurs; `CWS-006` is complete as an optional sidecar protocol.
2. `CWS-004` remains deferred until a concrete opportunity-scan need; `CWS-005` remains deferred behind that privacy-boundary decision and recurrence evidence; `CWS-007` is complete as the explicit deviation-review entry point.
3. `CWS-009`, `CWS-010`, `CWS-011`, and `CWS-012` are skipped for the current queue; `CWS-015` remains deferred until a concrete RCA or repair-scope failure.
4. `CWS-015` is skipped for the current queue; `CWS-013` is complete as a developer-only hook-authoring handbook; `CWS-014` remains deferred until a concrete structural-search failure.
5. `CWS-016` is already covered by native Delivery and workspace-governance controls; do not add a duplicate guardrail unless a concrete bypass or exception request appears.

Each completed item should record its result, evidence, changed recommendation, and follow-up ID in a
durable research or native Delivery artifact. A report-only item must not be marked complete merely
because a command ran; its output must answer the item's stated question.

### 4.4 Pattern-first recheck

On 2026-08-17, the comparison was restarted from OwlBear's local owners rather than from the
external disposition matrix. The question for this pass was narrower: which provider-neutral
patterns are missing, fragmented, or awkward locally, and can be added without creating a second
authority? A pattern qualifies only when it has a named local owner, a smaller adaptation than the
external mechanism, and a discriminating check that could show the adaptation is unnecessary or
harmful.

| ID | Reusable pattern | External evidence | Local comparison | Smallest useful adaptation | Confidence |
|---|---|---|---|---|---:|
| `PAT-001` | Choose proof by the claimed boundary, stage proof in time, and require a positive signal for startup or side-effect claims. Keep builder-visible proof distinct from independent evaluation. | `piv-validate` separates project commands, working directories, continued reporting after failures, and a single verdict. `build-dark-factory` separates factory plumbing from the validation harness, requires a positive startup marker, rejects empty output, and places an independence line after integration proof. | [h-ac-quality](../../share/skills/h-ac-quality/SKILL.md) already enforces observable boundaries and assembled-boundary proof. [w-packet-building](../../share/skills/w-packet-building/SKILL.md) already separates pre-commit shaping proof from exact-commit publication proof. The missing part is a compact cross-stage rule for selecting proof and recognizing a zero-exit-only or empty observation as weak evidence. | Add a proof-selection and signal-quality section to `h-ac-quality`; keep exact-head mechanics in `w-packet-building` and `w-change-finalization`. Do not add a generic holdout, mutation gate, or receipt field. | 91 |
| `PAT-002` | Triage review findings before editing: fix now, defer, manual look, or noise; repair one selected finding at a time with proof. | `piv-fix-review-findings` explicitly treats review as input rather than a work order and requires a decision before sequential repair. | [r-challenger-protocol](../../share/skills/r-challenger-protocol/SKILL.md) already defines advisory findings and caller routing. [w-packet-building](../../share/skills/w-packet-building/SKILL.md) already distinguishes local repair from Planning or Design return. The pattern is covered, but the choice table is distributed between caller and reviewer guidance. | Add one concise triage table only if a concrete mixed-finding repair shows repeated scope confusion; otherwise retain the existing typed routing. | 86 |
| `PAT-003` | Build an evidence chain and root-cause hypothesis before implementing a bug fix, then preserve uncertainty instead of treating a symptom as authority. | `piv-investigate-issue` uses parallel code/history investigation, a 5-Whys evidence chain, explicit confidence, and a separate implementation step. | [w-research](../../share/skills/w-research/SKILL.md) and [w-idea-refinement](../../share/skills/w-idea-refinement/SKILL.md) already separate observed claims from assumptions and return evidence to the shaping owner, but they do not prescribe a bug-specific RCA artifact. | Add an optional evidence-chain subsection to `w-research` only after a concrete stale-diagnosis or repair-scope failure. Do not create a GitHub-issue RCA authority. | 79 |
| `PAT-004` | Make each implementation unit context-complete: local patterns, exclusions, dependencies, exact validation, and a clear finish line. | `piv-plan-implementation` requires inherited decisions, file-level context, patterns to mirror, gotchas, validation commands, and task-level acceptance traceability. | `DeliveryTaskDefinition` already requires commitments, dependencies, outputs, maintained surfaces, constraints, exclusions, acceptance observations, and proof boundaries; [w-frontier-planning](../../share/skills/w-frontier-planning/SKILL.md) and the planner challenger enforce the graph. | Preserve the external checklist as a review heuristic, not a new plan format. Reopen only if a real task repeatedly fails because its context is technically valid but not implementation-complete. | 94 |

#### First finding: `PAT-001` proof selection and signal quality

**Finding.** OwlBear has stronger proof identity than the external workflow: acceptance scenarios name
boundaries, Build reruns observations against the exact candidate commit, and finalization retains
heterogeneous exact-head receipts plus independent review. What is less explicit is the portable
reasoning between those owners:

1. choose the cheapest proof that crosses the boundary actually claimed;
2. escalate from local or unit proof when the claim is assembled, user-facing, or side-effect based;
3. treat pre-commit proof as implementation feedback, not commit evidence;
4. require a positive observable marker or artifact for startup and side-effect claims, not only a
   zero exit status or non-empty command invocation; and
5. keep evidence visible to the builder separate from independent evaluation when the claimed
   behavior could be optimized around.

This is a guidance-locality gap, not a Delivery schema gap. The external source supplies the pattern,
but its dark-factory harness and provider assumptions should not be imported.

**Recommended owner and shape.** Add one short section to
[h-ac-quality](../../share/skills/h-ac-quality/SKILL.md) covering proof selection, positive signal,
and the builder/evaluator distinction. Cross-reference the existing exact-commit procedure in
[w-packet-building](../../share/skills/w-packet-building/SKILL.md) and
[w-change-finalization](../../share/skills/w-change-finalization/SKILL.md). Keep holdouts, mutation
checks, protected files, and runtime receipt changes out of this first adaptation; each needs a
separate concrete failure trigger.

**Discriminating check.** Rewrite one boundary-level acceptance example and one process acceptance
example using the proposed rule. The check fails the recommendation if the examples need new runtime
fields, duplicate existing B1-B4/P1-P3 rules, or cannot name a positive observable result without
turning the handbook into a generic test checklist.

**Decision options.** Ratings use 1-5, where 5 is strongest for the factor.

| Option | Benefit | Locality | Enforcement | Cost | Authority risk | Confidence |
|---|---:|---:|---:|---:|---:|---:|
| **A. Extend `h-ac-quality` only (recommended)** | 5 | 5 | 2 | 4 | 5 | 5 |
| **B. Extend `h-ac-quality` and `w-packet-building` together** | 5 | 3 | 3 | 3 | 4 | 4 |
| **C. Put the rule only in `r-challenger-protocol`** | 3 | 4 | 2 | 5 | 5 | 3 |
| **D. Enforce positive markers in Delivery receipts** | 4 | 2 | 5 | 1 | 2 | 3 |

**Option A - extend `h-ac-quality`.**

- **Pro:** One owner teaches authors and challengers how to select boundary-valid proof; it leaves
  Delivery identity and exact-head mechanics unchanged.
- **Con:** Guidance cannot force a worker to emit a meaningful marker, so the result still depends on
  the existing observation and review owners.
- **Risk:** A poorly written section could duplicate B4 or turn an acceptance handbook into a
  framework-specific checklist.
- **Outcome:** Clearer proof selection and stronger acceptance wording with no lifecycle mutation.
- **Confidence:** 0.90.

**Option B - extend `h-ac-quality` and `w-packet-building`.**

- **Pro:** The rule appears both where proof is specified and where pre-commit versus exact-commit
  proof is performed.
- **Con:** Two files must stay synchronized, and the Builder workflow becomes longer.
- **Risk:** Duplicated wording may drift or make Builders treat positive markers as mandatory for
  claims that do not need them.
- **Outcome:** Better operational recall than Option A, at the cost of a second maintenance owner.
- **Confidence:** 0.82.

**Option C - extend `r-challenger-protocol` only.**

- **Pro:** Independent reviewers get a single compact test for weak or merely nominal evidence.
- **Con:** The rule arrives after planning and implementation choices have already been made.
- **Risk:** Reviewers become the only place that notices proof-selection problems, producing returns
  instead of preventing them.
- **Outcome:** Stronger review findings, but little improvement to task authoring or Builder behavior.
- **Confidence:** 0.72.

**Option D - enforce positive markers in Delivery receipts.**

- **Pro:** A hard validator could reject empty or purely nominal observations consistently.
- **Con:** Delivery cannot define a provider-neutral marker vocabulary for every command, artifact,
  or manual procedure.
- **Risk:** False failures, schema coupling to tool output, and a new authority boundary created from
  an external heuristic rather than an observed defect.
- **Outcome:** Stronger enforcement only for a named high-risk surface; premature as a general rule.
- **Confidence:** 0.62.

**Implementation result (2026-08-17).** The selected Option A was implemented in
[h-ac-quality](../../share/skills/h-ac-quality/SKILL.md): proof selection now distinguishes claimed
boundaries, proof timing, positive signals, and independent evaluation without adding Delivery
fields or enforcement claims. Focused `validate_skills.py` and `git diff --check` validation passed.

**Implementation result (PAT-002) (2026-08-17).** The selected Option B was implemented in
[w-packet-building](../../share/skills/w-packet-building/SKILL.md): Builder now classifies a concrete
review finding as fix-now, return-to-authority, block-for-user, or no-repair before editing. The
external defer/noise categories are mapped to native return, block, or invalid-evidence boundaries;
no reviewer output or Delivery transition was changed. Focused `validate_skills.py`, content checks,
and `git diff --check` validation passed.

**Decision result (PAT-003) (2026-08-17).** The recommended Option D was adopted: defer an evidence-
chain or RCA adaptation until a concrete stale-diagnosis or repair-scope failure demonstrates that
the existing observed-claim and assumption boundary is insufficient. No new RCA skill, research
artifact, lifecycle field, or GitHub-issue authority was added. Reopen this finding only when a real
investigation stops at a symptom or a repair is mis-scoped because its causal hypothesis was not
made explicit.

**Decision result (PAT-004) (2026-08-17).** The recommended Option A was adopted: retain the
existing `DeliveryTaskDefinition`, frontier-planning, and planner-challenger contract without adding
a checklist, handbook, or context fields. The external context-completeness pattern is already
represented by commitments, dependencies, maintained surfaces, constraints, exclusions, acceptance
observations, and proof boundaries. Reopen this finding only after a real task fails because its
technically valid context was not implementation-complete.

**Implementation result (CWS-013) (2026-08-17).** The selected Option C was implemented as the
developer-only [h-hook-authoring](../../.github/skills/h-hook-authoring/SKILL.md) handbook. It covers
event selection, explicit input/output and failure contracts, bounded placement and wiring, and
negative-path validation. It does not add a hook, change an agent declaration, alter a validator,
or create consumer seed wiring; existing runtime hooks, validators, and tests remain authoritative.
Focused skill validation and `git diff --check` validation passed.

**Decision result (CWS-014) (2026-08-17).** The recommended Option A was adopted: defer structural-
search guidance until a concrete task demonstrates that text search is insufficient. No `ast-grep`
dependency, wrapper, handbook, or codebase-orientation change was added. The report does not retain
a structural-search task corpus, so this deferral is an unmeasured-scope decision rather than
evidence that text search is sufficient. Reopen when a real syntax-level search task can compare
text and AST approaches, setup cost, and result quality.

**Decision result (CWS-008) (2026-08-17).** The recommended Option A was adopted: defer a new weak-
proof mechanism while preserving the general PAT-001 guidance. The repository does not collect a
proof corpus that can establish whether accepted observations exercised their claimed boundaries;
this is an evidence gap, not evidence that weak proof is absent. Reopen when a retained observation
or review record supplies that comparison.

**Decision result (CWS-009) (2026-08-17).** The prior defer recommendation is superseded by the
explicit user disposition: the separate evaluator-independence mechanism has no current value for
OwlBear. No comparison collection, holdout wiring, evaluator-only receipt field, or new authority
was added. The useful sentence-level distinction remains covered by PAT-001; this finding is closed
for the current queue and should reopen only with an explicit new high-risk boundary justification.

**Decision result (CWS-010) (2026-08-17).** The user chose to skip the holdout-scenario pilot for
the current queue. No holdout pilot, protected scenario, or general gate was added. Reopen only
with an explicit high-risk boundary, owner, and justification; this skip is a queue decision, not
a claim about uncollected runtime outcomes.

**Decision result (CWS-011) (2026-08-17).** The user chose to skip mutation checks for the current
queue. No mutation set, survivor gate, or test-curation workflow was added. Reopen only with a named
high-risk test boundary, owner, and justification; this skip is a queue decision, not a claim about
uncollected mutation outcomes.

**Decision result (CWS-012) (2026-08-17).** The user chose to skip generalized protected-surface,
guard-bypass, holdout, and secret-handling mechanisms for the current queue. No protection inventory,
generalized policy, new guard, holdout surface, or secret-handling mechanism was added. This is a
queue/value decision, not a claim that all surfaces are protected or bypass-free. Reopen with a named
surface, bypass, holdout, or secret-handling requirement.

scope failure warrants a local evidence-chain pattern beyond the current workflows. No `CWS-015`
**Decision result (CWS-015) (2026-08-17).** The user chose to skip an RCA evidence-chain workflow,
template, sidecar fields, and dedicated audit for the current queue. Existing bounded diagnosis and
repair guidance remains in place. This is a queue/value decision, not a claim about uncollected
diagnosis or repair outcomes. Reopen with a named RCA or repair-scope failure.

**Queue status:** No unworked finding remains in the `CWS-001` through `CWS-016` worklist. `CWS-016`
is already covered by native Delivery and workspace-governance controls; the remaining deferred
entries have explicit reopen triggers and prior decisions. No further implementation is authorized
by this report update.

## 5. Recommendation, Confidence, And Limits

### Recommendation

Do not copy any of the 33 external skills directly into `share/skills/`. The external Claude-specific
workflow, GitHub mutation, branch, and unattended-factory assumptions are incompatible with OwlBear's
native Delivery authority.

Adapt five bounded ideas in priority order:

1. A report-only ablation protocol for measuring whether AI-layer guidance helps real work.
2. An advisory rules-drift check that compares current instructions with source, tests, and wiring.
3. A report-only opportunity scan over completed task artifacts and recurring failures.
4. A post-result system-evolution review that classifies process divergence without mutating authority.
5. Preserve existing boundary-valid proof and exact-commit evidence; investigate stronger markers
  only after a concrete weak-proof failure, while separately evaluating evaluator independence,
  protected governance, and selective holdout or mutation checks for high-risk surfaces.

The first four belong to audit and research ownership. The fifth belongs to acceptance and Delivery
quality. None should silently create a new lifecycle, bypass claims, weaken exact-head receipts, or
publish code. The external PIV planning and worktree ideas should be treated as already superseded by
native OwlBear mechanisms, not as missing features.

### Confidence

Overall confidence is **high** for the compatibility and rejection findings because they are grounded
in explicit external provider assumptions and local runtime contracts. Confidence is **medium** for the
priority ordering of the five adaptations: the concepts are strong, but this research did not run
controlled OwlBear experiments to measure their value or maintenance cost.

### Limits and unresolved questions

- This is source-grounded comparative research, not a benchmark of live OwlBear runs.
- No external repository code, setup script, hook, package, or deployment loop was executed.
- The external Markdown references were read; non-Markdown assets were not treated as implementation
  inputs.
- The report does not decide whether OwlBear should add a new audit skill. That requires observing
  repeated local failures and, if material, a separate Design or planning decision.
- Holdout and mutation strategies need a bounded pilot before becoming persistent repository gates.
- Session-log analysis requires an explicit privacy and retention boundary before `opportunity-scan`
  can be operationalized.

### Source cleanup

The external corpus was stored temporarily under `.owlbear/scratch/research/coleam00-skills/` during
the investigation. It is scratch evidence only and should be removed after this durable report and
the source attribution entry are validated.