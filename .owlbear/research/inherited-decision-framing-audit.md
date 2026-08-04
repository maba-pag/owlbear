# Inherited Decision Framing Audit

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which recorded decisions can constrain the redesign, and how should OwlBear obtain informed choices without forced alternatives or unnecessary user ceremony?
> **Status:** Working audit. It does not invalidate or rewrite admitted authority.

## 1. Context and Question

The current change contains 40 decision records: 36 `accepted` and 4 `superseded`, all attributed to
the user. The user reports that many were selected from agent-framed menus with little source context,
an implausible alternative, and no apparent open-list path. Therefore, status alone cannot establish
informed confirmation.

The redesign still needs agent guidance and recommendations. The correction is not to make the user
design the system unaided. It is to separate evidence gathering, open alternative discovery,
recommendation, user authority, and engineering delegation.

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| `decisions.yaml` | Contains 40 records, each with a selected option, recommendation flags, confidence, and alternatives. |
| `w-design-session` Step 5 | Requires two to four options, tradeoffs, risks, a recommendation, and one-question user resolution. |
| `intent.md` | User-facing value centers on low-ceremony agent-guided design and dependable delivery. |
| `design.md` | Many recorded choices concern internal transaction, receipt, currentness, transport, and bootstrap mechanics. |
| User correction on 2026-08-02 | Prior selections may have been false-forced and must not be presumed deliberate. |

## 3. Measured Framing Pattern

Structured inspection of all 40 decision records found:

| Measure | Result |
|---|---:|
| Selected option pre-marked `recommended` | 40 / 40 |
| Selected option had highest stated confidence | 39 / 40 |
| Median selected confidence | 0.950 |
| Median best-alternative confidence | 0.455 |
| Median confidence advantage before user choice | 0.475 |
| Menus with at least 0.40 confidence advantage | 24 / 40 |

This does not prove each selected architecture is wrong. It does prove the records cannot, by
themselves, distinguish informed user intent from recommendation anchoring.

### Recurrent framing defects

- The preferred answer was visually and numerically privileged before the user assessed the option
  space.
- Several alternatives were failure extremes rather than the strongest competing architecture.
- Option sets were presented as complete even when hybrids or another framing were credible.
- Confidence often described the agent's preference, not uncertainty in source evidence.
- Internal mechanics were elevated into user decisions instead of being derived from accepted product
  guarantees and reviewed engineering judgment.
- Accepted rationale was agent-authored, so it cannot be assumed to capture the user's actual reason.

## 4. Decision Authority Tiers

| Tier | What belongs here | Who decides | Required treatment |
|---|---|---|---|
| 1. Product value | Desired workflows, visible behavior, exclusions, compatibility, acceptable risk/cost | User with agent assistance | Informed explicit choice or confirmation |
| 2. Consequential architecture | Irreversible topology, authority boundaries, assurance model, concurrency or migration strategy with material consequences | Joint: agent recommendation, user authority | Source-grounded alternatives and explicit consequences |
| 3. Engineering design | Transaction shape, event identity, adapter placement, recovery algorithm, schema details | Agent/engineering owner within user-guided constraints | Evidence-backed rationale and independent review; user reviews the semantic implementation strategy, while code-level mechanics need no separate choice unless Tier 1/2 consequences differ |
| 4. Mechanical derivation | IDs, canonical expansion, graph legality, digests, currentness, generated jobs/receipts | Code | Deterministic validation; never ask the user |

The current registry mixes all four tiers under `authority: user`. Revalidation should correct the
authority classification before asking for any selection.

## 5. Decision Families and Treatment

| Family | Existing records | Proposed treatment |
|---|---|---|
| Product boundary and cutover promise | DEC-001, 002, 017, 035, 036, 038, 039 | Reframe around user-visible downtime, retained history, compatibility, reversibility, and recovery; derive internal sequence afterward. |
| Specification and authority model | DEC-003, 004, 010, 011, 012, 028, 030, 031 | Revalidate as a small set of Tier 1/2 principles; do not ask the user to choose file layout independently of the experience it enables. |
| Delivery decomposition and economics | DEC-005, 006, 007, 015, 027, 029, 032, 033, 037 | Re-evaluate together using observed agent starts, review rounds, context load, re-plans, and recovery behavior. |
| Review, acceptance, and proof guarantees | DEC-008, 013, 018, 019, 021, 040 | Ask the user for assurance and independence expectations; let agents derive checkout and receipt mechanics. |
| Runtime correction and administration | DEC-009, 022, 023, 024, 034 | Treat mostly as Tier 3 design; preserve visible recovery guarantees and independently review implementation. |
| Worktree, package, bootstrap, and transport topology | DEC-014, 016, 020, 025, 026 | Treat as Tier 2 only where user-work safety, cost, or reversibility differs; otherwise delegate to engineering. |

The four superseded records remain history and require no separate user re-decision unless their
underlying question reappears.

## 6. Priority Revalidation

Do not replay forty prompts. Revalidate the minimum high-leverage questions:

1. **User contract:** What should the user provide, review, approve, and be able to inspect?
2. **Authority depth:** What semantic completeness must exist before Delivery, and what may Planning
   refine autonomously?
3. **Agent economics:** What independence and fresh-context guarantees justify another invocation or
   review cycle?
4. **Assurance:** Which outcomes require independent acceptance, exact-commit proof, or whole-change
   audit?
5. **Correction:** When should downstream work reconcile automatically, and when should a material
   change return to the user?
6. **Cutover:** What downtime, migration loss, rollback, and self-hosting risk are acceptable?

Internal schemas, IDs, selectors, event fields, store layout, and transport adapters follow from these
answers unless they expose a new consequence.

## 7. Informed Decision Protocol

For each material question:

1. Rehydrate current evidence and state what is observed, assumed, and user-confirmed.
2. Classify the decision tier and explain why user authority is or is not needed.
3. Develop the strongest credible paths and hybrids when a genuine material tradeoff exists; do not
   manufacture alternatives for clarification or technical facts.
4. Explain each path through the same consequences: what it enables, takes over, preserves, prevents,
   weakens, improves, costs, risks, and whether it can be reversed.
5. State the agent's technical assessment only after the consequence comparison, without presenting
   its target as the option space or using an implausible foil.
6. Ask which consequence better matches the user's intent and what the framing missed, rather than
   asking the user to select a recommended label.
7. Synthesize the answer into the layer's review object and let the user correct, defer, or delegate
   the remaining engineering choice.
8. Record user-originated priorities and rationale separately from agent analysis.
9. Re-open only when new evidence changes a material consequence, not whenever implementation detail
   changes.

Apply `graduated-semantic-collaboration.md` so the amount and abstraction of discussion match intent,
outcomes, constraints, acceptance, strategy, or implementation detail.

### Record states for inherited choices

- `unreviewed`: historical selection with no current informed confirmation;
- `reaffirmed`: user confirmed after open alternatives and consequences;
- `delegated`: user accepted the product constraints and delegated the engineering choice;
- `superseded`: no longer controls current design; and
- `confirmed-by-current-request`: directly restated by the user in current conversation.

The current request confirms graduated collaboration: user depth is greatest for intent and decreases
as agent depth increases through outcomes, constraints, acceptance, strategy, and details. User review
operates on enabled high-level abstractions; agents and independent reviewers own the nitty gritty. It
does not confirm the present artifact count, planning schema, review loop, or lifecycle mechanics.

## 8. Implementation Checklist

- [ ] Add decision tier, framing state, and rationale provenance to the redesign model.
- [ ] Mark all inherited accepted records `unreviewed` in the redesign assessment without mutating
  admitted authority.
- [ ] Mark only the user-guided, agent-assisted semantic-authority boundary `confirmed-by-current-request`.
- [ ] Consolidate the 40 records into the six priority questions before any revalidation interview.
- [ ] Test the protocol on acceptance ownership and one internal runtime choice.
- [ ] Amend `w-design-session` so neutral framing precedes recommendation and open alternatives are
  explicit.
- [ ] Add review checks for implausible foils, omitted hybrids, authority-tier mismatch, and agent-
  authored rationale presented as user rationale.
- [ ] Update Cockpit to distinguish user-confirmed, delegated, and engineering-owned decisions.

## 9. Recommendation, Confidence, And Limits

**Recommendation:** Preserve the useful technical reasoning in all 40 records, but suspend their use
as proof of informed user intent. Revalidate six high-leverage consequence questions, delegate Tier 3
mechanics, and regenerate architecture decisions from the resulting constraints.

**Confidence:** High in the measured framing defect and authority-tier mismatch. Medium in the six-
question consolidation until it is checked against ordinary feature work as well as this exceptional
self-hosting change.

**Limits:** This audit does not determine that any selected option is technically wrong, alter current
authority, or exhaust the possible decision families.