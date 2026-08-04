# Target Delivery Information-Flow Walkthrough

> **Owning task:** none — user-directed architecture walkthrough
> **Date:** 2026-08-02
> **Question:** What tool and information flow should carry one change from initial design-session
> selection through target delivery with minimum manual agent work, bounded context, exact authority,
> and no premature consolidation?

## 1. Purpose And Method

This document records the status quo, source evidence, decisions, unresolved questions, proposed
tool contracts, and required implementation changes for a step-by-step target-delivery walkthrough.
It is a comparison baseline, not admitted semantic authority and not implementation approval.

Implementation is not complete until the approved ladder, per-step tool sequence, authority
boundaries, and role-specific payload rationale are transferred into canonical project documentation.
These research records remain the source for before/after comparison, not the final operator guide.

Review one process step at a time. For each step:

1. identify the actor, authority, inputs, tools, outputs, and next-step handoff;
2. distinguish locator data from complete authority and mutation payloads;
3. assess underdelivery, overdelivery, context cost, hidden agent work, replay, and failure semantics;
4. compare keeping, splitting, combining, or adding tools without requiring prior production failure;
5. record exactly one material decision before advancing; and
6. preserve implementation deltas without implementing them during the walkthrough.

## 2. Sources Studied

| Source | Relevant fact | Limit |
|---|---|---|
| `share/prompts/ideate.prompt.md` | `/ideate` enters discovery through `w-design-session`. | Prompt routing only. |
| `share/prompts/design.prompt.md` | `/design` enters direct design and currently uses `list_changes` and `show_change`. | Prompt routing only. |
| `share/agents/designer.agent.md` | Designer has explicit search/read/terminal tools and only target admission MCP mutations. | Declared capability, not behavioral proof. |
| `share/skills/w-design-session/SKILL.md` | One session spans draft and admitted authority; Step 1 selects or creates identity. | Workflow intent, not runtime enforcement. |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/target_server.py` | `list_changes` currently returns every complete admitted `TargetAuthority`. | Current adapter implementation. |
| `serve/kanban/src/owlbear_kanban/target_admission.py` | Registry lists and shows current admitted authority and owns validation/admission. | Does not own draft sessions. |
| `serve/kanban/src/owlbear_kanban/change_workspace.py` | Public managers hide writer OCC, capacity, warm worktrees, restart, and integration. | Current domain implementation. |
| `serve/kanban/src/owlbear_kanban/proof_checkout.py` | Public proof manager owns contained exact-commit review environments. | Current domain implementation. |
| `.owlbear/research/delivery-pipeline-target-architecture.md` | Orchestration owns dispatch; board observes; workspaces and proof are retained target boundaries. | Design source, not executable state. |
| `semble search --help` through `owlbear_tools.semble` | Semantic search accepts a path, content filters, result caps, and snippet-line caps. | Backend capability, not a chosen contract. |

## 3. Whole-Process Map

The detailed steps are checkpoints inside three loops, not one agent's linear context ladder:

| Loop | Steps | Exit |
|---|---|---|
| Specification | 1-9 | One approved admitted semantic revision |
| Delivery | 10-12 and 14 | Reviewed plan, build, and assembly results plus deterministic integration |
| Correction | 13, then the earliest affected loop | Local repair, replanning, or typed Design transition |

Design is manually user-started. After admission, a pure dispatcher atomically acquires ready
packages, launches the named agents in parallel, detects invocation failure, and reports typed stop
conditions. Runtime owns scheduling and lifecycle derivation; claim owners, reviewers, and arbiters
record their own scoped transitions. The dispatcher does not interpret evidence, mediate Design, or
start user-facing collaboration.

User participation is intentionally front-loaded. Early Specification maximizes understandable
meaning and one-consequence choices; later Specification compiles that authority as technical
information density rises. Agent and deterministic responsibility grows at each step. Late phases
return to the user only when evidence changes a consequence the user owns, not to explain machine
representations or request ceremonial confirmation.

| Step | Current owner | Primary transition | Walkthrough state |
|---|---|---|---|
| 1. Select or create session | Designer | Rough idea or ID → one draft/admitted identity | Decided |
| 2. Rehydrate authority | Designer | Identity → complete current design context | Decided |
| 3. Discover intent | Designer + user | Rough intent → durable Product Promise | Decided |
| 4. Ground claims | Designer + read-only evidence | Unknowns → classified evidence | Decided |
| 5. Resolve decisions | User through Designer | Material fork → durable decision | Decided |
| 6. Design architecture | Designer + reviewer | Stable intent → critiqued architecture | Decided |
| 7. Derive Delivery Contract | Designer + deterministic parser | Reviewed Specification → candidate contract | Decided |
| 8. Pre-admission validation | Deterministic runtime | Candidate contract → valid contract/frontier | Decided; absorbed into Step 9 |
| 9. Review, authorize, and admit | Two reviewers + Designer + user + runtime | Valid contract → admitted change/jobs | Decided |
| 10. Select frontier work | Runtime + Orchestrator | Portfolio state → launch packages | Decided |
| 11. Plan target scope | Planner + challenger | Plan job → reviewed task graph | Decided |
| 12. Build or assemble | Builder + reviewer | Task claim → accepted exact commit | Decided |
| 13. Correct or re-enter | Worker + runtime + relevant owner | Worker instruction → mechanical board transition | Decided |
| 14. Integrate and complete | Runtime + workspace manager | Ready change → integrated completed-history package | Decided |

## 4. Cross-Step Information Classes

| Class | Purpose | Preferred shape |
|---|---|---|
| Inventory | Choose an identity or next item. | Paginated summaries; no complete bodies. |
| Locator | Find likely relevant authority or source. | Ranked IDs, paths, match kind, bounded snippets. |
| Authority | Establish exact current meaning. | Full owning file/model, digest when immutable. |
| Claim | Bind actor, work, revision, and attempt. | Typed minimal mutation request. |
| Evidence | Prove or challenge one claim. | Immutable references plus focused findings. |
| Projection | Help a human or agent decide what to do next. | Role-specific, bounded, derived summary. |

Tools should return the lowest information class sufficient for the current decision. A list operation
must not silently return authority bodies; a search result must not become authority; a projection
must not duplicate mutable semantics.

Writes follow the same ownership test. Agents directly edit long-form authored prose and assigned
product code. Purpose-built tools own typed records or transitions requiring stable identities,
cross-record references, OCC, replay, or atomic publication. One generic semantic mutation tool is
not a substitute for distinct authority contracts.

Specification artifacts are living explanations of current truth, not append-only audit logs.
Retain prior direction, rejected alternatives, review feedback, and change rationale only when they
can affect a later decision or prevent a credible mistake. Update or remove stale material when it no
longer serves that purpose. Git preserves confirmed intent, reviewed design, and admitted-contract
snapshots; it does not promise every transient edit or conversation.

The same consumer test applies to machine records. Persist a receipt, binding, or transition only
when a later runtime decision needs it for identity, correctness, replay, or recovery. Do not retain
review passes, authorization history, command logs, warnings, or other material merely to make the
process auditable; that information adds context cost without helping Delivery decide or recover.

## 5. Corrected Finding: Public Coordination And Proof Interfaces

The earlier recommendation to de-export `ChangeWorkspaceManager`, `PortfolioCoordinator`,
`CapacityLedger`, and `ProofCheckoutManager` is withdrawn.

- The package is a transport-free control plane with supported direct Python composition.
- Target cutover deliberately retained `ChangeWorkspaceManager` and `PortfolioDispatcher` in the
  required public contract while deleting retired execution APIs.
- Cutover adapted `ProofCheckoutManager` from legacy jobs to `TargetJob` and current target authority.
- These modules concentrate durable coordination, Git recovery/integration, and exact-commit proof
  complexity that would otherwise leak into orchestrators.
- Absence of direct MCP callers is a possible orchestration-composition gap, not evidence that the
  interfaces are accidental or obsolete.

Required follow-up: inspect where these public contracts enter Steps 10–14 before deciding whether
any exposure or composition changes are appropriate.

## 6. Step Records

Detailed evidence and contracts live in one companion per process step so this index stays bounded.

| Step | Record | Decisions |
|---|---|---|
| 1. Select or create session | [Step 1](target-delivery-information-flow-step-01.md) | D1 separate browse/search; D2 observable hybrid search; D3 Designer-specific list; D4 seeded atomic creation |
| 2. Rehydrate authority | [Step 2](target-delivery-information-flow-step-02.md) | D1-D8 context; D9-D10 Design transitions; D11 selective carry-forward |
| 3. Discover intent | [Step 3](target-delivery-information-flow-step-03.md) | D1-D2 discovery; D3-D10 formative review and retention |
| 4. Ground claims | [Step 4](target-delivery-information-flow-step-04.md) | D1-D4 policy; D5 tools; D6 authority; D7 owned researcher |
| 5. Resolve decisions | [Step 5](target-delivery-information-flow-step-05.md) | D1-D5 authority and conversation; D6 edits; D7 focused review |
| 6. Design architecture | [Step 6](target-delivery-information-flow-step-06.md) | D1 completeness; D2 proof depth; D3-D5 construction, critique, handoff |
| 7. Derive Delivery Contract | [Step 7](target-delivery-information-flow-step-07.md) | D1 derivation; D2 compilation boundary; D3 semantic-only contract |
| 8. Pre-admission validation | [Step 8](target-delivery-information-flow-step-08.md) | D1 minimum deterministic assurance; D2 inherited gate deletion |
| 9. Review, authorize, and admit | [Step 9](target-delivery-information-flow-step-09.md) | D1 directional reviews; D2 resolution; D3 authorization; D4 tools; D5 atomic admission |
| 10. Select frontier work | [Step 10](target-delivery-information-flow-step-10.md) | D1 staged recovery; D2 concurrency; D3 acquisition tool; D4 thin adapter |
| 11. Plan target scope | [Step 11](target-delivery-information-flow-step-11.md) | D1 task authority; D2 context; D3 transition; D4 tasks; D5 review; D6 publication |
| 12. Build or assemble | [Step 12](target-delivery-information-flow-step-12.md) | D1-D3 context/result; D4 transition; D5 review; D6 commit/transition; D7 Assembly |
| 13. Correct or re-enter | [Step 13](target-delivery-information-flow-step-13.md) | D1 routing; D2 requests; D3 status; D4 transitions; D5 review; D6 Assembly; D7 output separation |
| 14. Integrate and complete | [Step 14](target-delivery-information-flow-step-14.md) | D1 package; D2 integration/archive; D3 attention; D4 repair lane; D5 completion retention |

## 7. Recommendation, Confidence, And Limits

**Current recommendation:** Use one change-owned package from Design through completed history; two
authored Specification documents; one deterministically derived Delivery Contract; focused early
reviews plus dual directional final review; minimal admission evidence; runtime-owned scheduling;
invisible in-cycle worker review; and four mechanical worker instructions: `advance`, `retry`,
`return`, and `block`. Purpose-built tools own shared-state transitions; agents directly author only
their assigned meaning or code.

**Confidence:** High in the authority, information-flow, review, board-transition, and tool-ownership
boundaries. Moderately high in physical whole-package archival and integration transaction design;
representative package layout, Git transaction, cleanup replay, and search-corpus proof remain required
before implementation freezes those mechanics.

**Limits:** All fourteen information-flow phases are decided. This walkthrough authorizes no
implementation by itself. Implementation must translate these records into one coherent target
architecture and update canonical workflows, agents, tools, models, projections, and documentation;
where current runtime behavior conflicts with later decisions, the walkthrough decisions win.