# Target Delivery Information Flow — Step 9: Review, Authorize, And Admit

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should one validated Delivery Contract receive independent forward and reverse
> semantic checks, user-owned authorization, and atomic admission without asking the user to review
> machine representation?

## 1. Phase Audit And Boundary

| Dimension | Decision |
|---|---|
| Actor | Designer resolves findings; fresh forward and reverse reviewers advise independently under distinct-model policy; runtime validates and admits; user owns material consequences and authorization. |
| Authority | Approved `intent.md` is the root claim; reviewed `design.md` owns realization; the generated Delivery Contract is the executable projection. Review output has no authority. |
| Inputs | Exact source-bound contract, approved intent, reviewed architecture, decisive evidence, proof boundaries, assumptions, exclusions, and known limits. |
| Tools | Two read-only agent invocations, `validate_change`, `askQuestions`, and `admit_change`. |
| Outputs | Resolved Specification, reproducible valid contract, operational authorization, admission receipt, and exact initial Planning frontier. |
| Handoff | Step 10 receives admitted digest-bound jobs and authority references, never chat summaries or reviewer prose. |

Step 8 deterministically proves derivation fidelity, semantic coverage, graph validity, and frontier
derivability. Step 3 already reviewed and confirmed intent; Step 6 reviewed architecture forward from
that intent. A final review must test the complete trace in both directions without replacing those
earlier, cheaper review points.

Step 9 may repair or reopen Specification before admission. It does not create task plans, inspect
implementation, or ask the user to certify contract fields. Its "final plan" is the generated
Delivery Contract; implementation task planning starts only after admission.

## 2. Decision D1 — Independent Forward And Reverse Reviews

Keep Step 6's timely architecture critique. After deterministic validation and before authorization,
run two fresh owned final-Specification reviewers independently and in parallel. They do not read each
other's output. This is an additional end-to-end perspective, not a replacement architecture review
or a per-entity admission challenge.

The **Forward Specification Reviewer** works through three deliberately staged reads:

1. Read approved `intent.md` and state the obligations it creates.
2. Read `design.md` and decisive source evidence. Check whether the architecture supports every
   obligation without silent narrowing, unsupported assumptions, or missing proof.
3. Read the validated Delivery Contract. Check whether executable outcomes, acceptance,
   dependencies, scopes, and proof boundaries preserve that architecture and intent completely.

The **Reverse Specification Reviewer** works backward through the same layers:

1. Read only the validated Delivery Contract. Independently reconstruct the likely resulting product
   change, beneficiary and purpose, visible behavior, boundaries, exclusions, risks, dependencies,
   and credible completion evidence. Fix this interpretation before opening authored Specification.
2. Read `design.md` and decisive source evidence. Check whether the architecture actually explains
   and supports the inferred result, and identify unsupported, contradictory, or silently introduced
   consequences.
3. Read approved `intent.md`. Check whether the reconstructed result and supporting architecture
   preserve the Product Promise, workflow, scope, protected behavior, accepted exclusions, and
   observable success without silent weakening or expansion.

During reverse stages 2 and 3, explicitly compare each extracted normative block with its surrounding
authored meaning. Any silent narrowing, expansion, or contradiction is a derivation defect even when
the block is structurally valid.

Do not provide either reviewer with prior review output or all layers at once. Each records concise
stage conclusions before opening the next layer. Forward order tests promise preservation; reverse
order limits anchoring on stated meaning and tests what Delivery itself communicates. Different model
judgment and opposite anchoring direction provide the diversity; findings are unioned, never voted.
Each reviewer returns formative observations with targets, evidence, consequences, uncertainty, and
bounded correction and issues no verdict, score, replacement Specification, vote, or approval.

## 3. Decision D2 — Designer Owns Finding Resolution

Designer evaluates every material observation. It may autonomously repair a clear technical,
structural, evidentiary, or mapping defect only when one grounded correction exists wholly inside
approved user intent. It may also reject unsupported feedback with concise rationale or ground a
disputed fact before deciding.

Expose one decision to the user when a finding could change or call into question the Product
Promise, workflow or control, scope or preserved behavior, accepted exclusion, public contract,
migration consequence, security or privacy posture, irreversible commitment, or completion-evidence
cost and confidence. A suspected defect in approved intent therefore reopens intent explicitly; it
is never silently repaired downstream.

Review output remains transient. Corrected current Specification is the durable result. Any material
intent, architecture, or contract change reruns affected formative review, deterministic derivation
and validation, and both final directional reviews before authorization. Unresolved material
observations keep the session in Design.

## 4. Decision D3 — One Operational Authorization

After all reverse-review observations are resolved, ask one plain-language question: whether to begin
autonomous Delivery for the approved change. This is operational consent to release Planning and
subsequent reviewed repository work, not another approval of intent, architecture, generated fields,
or review evidence.

Show only the approved Product Promise, accepted exclusions or known limits, configured integration
target, the fact that completed Specification, change-owned research, and request answers enter target Git history,
and the immediate breadth of Planning. Do not show a digest, dependency graph, entity
inventory, validation report, or machine contract. The live Designer workflow is the trusted consent
boundary and calls admission only after the answer. The expected digest binds that call to the exact
validated revision as a stale-write guard; it is not proof that runtime independently verified consent.
Admission also binds the shown integration-target ref and configuration identity. Semantic revision or
target-identity change requires fresh authorization; an identical replay does not. Never bind the
target head: normal target advancement is handled by Integration CAS and candidate-tree proof.

Do not persist who authorized or when, including actor class, account identity, or timestamp. The
admitted revision records successful workflow completion without claiming machine-verifiable consent.
Add no authorization record, personal information, or one-use capability unless the trust boundary
itself later changes.

Authorization is a one-time command to start Delivery, not a durable permission lease. Add no pause,
revocation, or authorization-history state. Stopping orchestration naturally stops future launches;
an interrupted active owner follows existing typed recovery. A requested semantic change returns to
Design and revision rules rather than mutating an authorization record.

User refusal or absence leaves the complete reviewed session resumable and creates no Delivery work.
Validation or review failure occurs before this question and routes to its owning earlier step rather
than asking the user to authorize a known-defective revision. Either unavailable or coverage-
incomplete directional review leaves the session unauthorized and unadmitted.

## 5. Decision D4 — Tool Disposition

- **Keep** `validate_change` as deterministic preview and `admit_change` as the atomic validating
   publication boundary.
- **Use** Step 13's invariant-checked administrative surface for unchanged-contract target rebinding.
- **Keep** `askQuestions` only for one material finding at a time and final operational authorization.
- **Keep** the Step 6 Concept Reviewer in its focused architecture role.
- **Add** two narrow final-Specification reviewer agents sharing one formative observation protocol:
   Forward and Reverse Specification Reviewer. Current replaceable policy assigns Claude Opus 5
   forward and Sol reverse and requires different model families.
- **Remove** the old per-entity Designer Challenger, admission baseline, warning evidence, repeated
   caller-visible validation, and any review ledger or machine-evidence report.
- **Do not add** an MCP review wrapper or combined review artifact. Agent judgment stays advisory;
   runtime tools own deterministic validation and mutation.

## 6. Why This Is Not Step 8 Again

The deleted Step 8 challenger iterated declared entities and could not detect absent meaning. This
pair traces the whole chain from both approved intent and assembled result. Deterministic checks still
own exact compilation and graph safety; Step 11 later owns per-outcome task-plan review at exact
authority. No admission baseline, review ledger, per-entity evidence, or durable passing report is
added.

## 7. Decision D5 — Revalidate And Publish Atomically

Use one deterministic validation before final review to establish the exact contract digest and
frontier preview. After review resolution and authorization, call admission once. Admission itself
must reread and verify the bound source revisions and gate states, re-derive the contract, rerun
deterministic validation, and require equality with the expected validated digest before writing anything. Do not make a
second caller-visible validation call after approval.

Publish the immutable Delivery Contract, runtime frontier, minimal admission receipt, and admitted
snapshot through one staged idempotent operation keyed by change and expected digest. Prepare runtime
bytes and the package-history snapshot first, then publish the receipt last as the sole admission
visibility point. A visible receipt with missing or invalid runtime bytes fails closed; snapshot
recovery never participates in scheduling authority. The receipt binds change identity, contract digest and therefore source bindings, and
integration-target ref/configuration identity, and frontier identities. Do not duplicate known limits from
Specification or persist reviewer observations, passing checks, warnings, baselines, or validation
reports.

The snapshot contains exact authored Specification, generated contract, and source bindings. The
transaction does not modify the product branch. A pre-visibility interruption may leave prepared Git
objects or the expected ref snapshot, but creates no admitted work; replay or explicit repair is its
only consumer.

A source, contract, or authorization mismatch fails before publication and returns to the earliest
affected Specification step. User refusal or absence remains an unadmitted reviewed session. An
interruption after durable publication is recovered by replaying the identical request, which returns
the same artifacts without another review or authorization. A different semantic revision requires
quiescent Delivery, archives the prior admitted revision, and repeats affected review, validation,
and authorization; active work blocks replacement. Revised admission applies Step 2's deterministic
equivalence and closure policy, rebinds contract-equivalent task chains and results to the new digest,
rebinds only equivalent block/request context, and creates Planning work for invalidated outcomes plus
ordinary removal/replacement outcomes required by the revised contract.
Prior result commits locate reversal evidence but never authorize deletion by themselves.

If only the integration-target ref/configuration identity changes after admission, ask D3's same
plain-language authorization against the unchanged contract digest. The invariant-checked
administrative update rebinds only target identity and creates no semantic revision, frontier, job,
or product-branch change.

On success, return only admission identity and the ready Planning count needed to explain the state.
The runtime, not Designer, owns the exact initial jobs and exposes their dependency-ready subset to
Step 10. Admission starts no agent and creates no product-code work beyond its semantic snapshot.

## 8. Step Completion

Step 9 is decided. It consists of independent forward and reverse whole-Specification
reviews, Designer-owned finding resolution, one user authorization to begin autonomous Delivery,
and one atomic admission call with internal revalidation and replay. Step 10 begins from admitted
runtime state and selects ready Planning claims without reloading Design conversation or review
evidence.