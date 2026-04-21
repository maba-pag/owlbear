# Synthesis — Brief B: Kanban Engine API

**Pragmatist synthesis of Architect, Data, End-User, and Security stances.**
**Confidence: 0.78** — Strong convergence on 6 of 9 questions; genuine 3-way conflict on Q1 token semantics and type; genuine 2-way conflict on Q2 and Q6.

---

## Q1: Optimistic Concurrency Token — OPEN (coupled to D11)

**Three positions in play:**

| Position | Panelists | Core Argument |
|----------|-----------|---------------|
| Optional at engine; required via `CockpitEngineView` type contract. Token = `updated` timestamp. | Architect, End-User | Single-user laptop; MCP agents work sequentially on claimed tasks; forcing pre-fetch round trips penalises the common case. |
| Required on `edit_task`, `move_task`, `end_work`. Token = `updated` timestamp. | Security | Without identity (D11) AND without a mandatory token, `end_work` is an unguarded write path. Zombie-agent scenario produces silent data corruption. |
| Required on `edit_task`; optional on `move_task`. Token = `revision: int` (NOT `updated`). | Data | Timestamp equality is brittle (truncation, microsecond collisions). A monotonic integer is deterministic and storage-agnostic. |

**Interaction — Q1 ↔ D11 ↔ `end_work` safety:** Security's argument is load-bearing. D11 drops `claimed_by`, removing the only identity-based guard. If the concurrency token is also optional on `end_work`, a zombie agent's stale write succeeds silently. The Architect acknowledged this gap and added optional OCC to `end_work` — but "optional" doesn't close the hole when the zombie doesn't have a fresh token. This is the single highest-stakes coupling in Brief B.

**Sub-question — token type (`updated` vs `revision: int`):** Data's `revision` counter eliminates clock edge cases (same-microsecond writes, TZ normalisation bugs). Architect/End-User/Security all assumed `updated`. Migration cost is low (default `revision: 1` on first read). The counter is a cleaner primitive if Brief C picks a DBMS.

**User must decide:**

1. **Scope of requirement:** (a) Required everywhere except `start_work`/`create_task` (Security), (b) Optional at engine, required only by CockpitEngineView type (Architect/End-User), or (c) Required on `edit_task` only (Data).
2. **Token type:** `updated` timestamp (Architect/End-User/Security) or `revision: int` counter (Data).
3. **`end_work` specifically:** Required or optional? This is the D11-safety question.

---

## Q2: Clarity Gate Predicate — OPEN

**Two positions:**

| Position | Panelists | Core Argument |
|----------|-----------|---------------|
| Keep loose (body-wide regex + 9-tag escape). | Architect | No demonstrated false-positive problem. Tightening forces migration. |
| Tighten to require `## AC` section with ≥1 list item. | End-User | D7 structured body makes this a structural query, not a regex change. Zero raw-text migration — tasks without `## AC` simply stay undispatched. |

Security: no security impact. Data: no explicit position.

**End-User's Critic loop-back:** Originally held the loose position; changed after recognising that D7's structured body makes the check trivial (`any(s.heading == "AC" for s in sections)`). This is a genuine insight — the structured model changes the cost/benefit calculus.

**Reconciliation attempted:** The positions are closer than they appear. "Tasks without `## AC` stay undispatched" is functionally equivalent to "migration happens organically." The real question is whether Brief B locks the tighter predicate now (forcing immediate task curation) or documents it as a recommended follow-up.

**User must decide:** Tighten now (End-User) or keep loose with tightening as a documented follow-up (Architect)?

---

## Q3: Section Model Shape — RECOMMENDED

**Proposal:** `Section = {heading: str | None, level: int, content: str}`. Amend D7.

**Convergence:** Architect, Data, and End-User all agree on adding `level: int`. Architect and Data independently specified identical parsing rules (fence-aware, preamble at level 0, document-order preservation). Security: no security impact.

**D7 amendment required.** The locked D7 shape `{heading, content}` is lossy without `level`. All three stances that addressed the model agree this is necessary.

**RECOMMENDED: Adopt `level: int`. Specify fence-aware parsing. Normalization rules per Data's round-trip contract.**

---

## Q4: Exception Taxonomy — RECOMMENDED

**Proposal:** Shallow hierarchy (6 classes, max depth 2) with `code: str` for programmatic discrimination and two-tier messaging (`user_message` for wire, `detail` for diagnostics only).

**Convergence:** Architect (hierarchy + code field), End-User (structured codes, no remediation hints), Security (two-tier message policy). All three positions are complementary, not conflicting.

**RECOMMENDED: Architect's class hierarchy + Security's two-tier message policy. End-User's "no hints" position is consistent. Merge verbatim.**

---

## Q5: Wave Algorithm — RECOMMENDED

**Proposal:** Greedy priority-first, deterministic, task_id tiebreak. Bidirectional dep-edge exclusion within waves. Full Brief B gate set (including dep_status).

**Convergence:** Architect and End-User specified the same algorithm independently. Security: no impact. Data: no explicit position on algorithm.

**Sub-question — `wave_reason: str`:** End-User proposes a per-DispatchEntry reason field for self-explaining dispatch. Nobody else addressed it. Token cost is ~10-20 per entry. Value is real for orchestrator debugging. Risk of noise is mitigatable with a `verbose` flag.

**RECOMMENDED: Greedy deterministic algorithm per Architect/End-User. `wave_reason` is a net-new proposal — include as optional field (present when non-trivial), not blocking.**

---

## Q6: `agent_map` Config Shape — OPEN

**Two positions:**

| Position | Panelists | Core Argument |
|----------|-----------|---------------|
| Must cover all statuses in config. Missing mapping → `ValidationError` at engine construction (fail-fast). No `_default`. | Architect | Null-agent tasks leaking into waves is worse than a startup error. |
| `_default` key. Unmapped status → use default. Missing default → `null` + guidance warning. Engine does NOT error. | Data | Engine should be permissive; orchestrator decides on null-agent tasks. |

End-User: `dict[str, str]`, no multi-agent — agrees on shape, didn't address completeness. Security: no impact.

**Reconciliation attempted:** Both positions use `dict[str, str]` (single agent per status). The conflict is strictness: fail-fast vs graceful degradation. Architect's position prevents null-agent DispatchEntries from ever reaching consumers. Data's position allows partial configs during incremental adoption.

**User must decide:** Fail-fast at construction (Architect) or `_default` fallback (Data)?

---

## Q7: `claim_timeout` Format — RECOMMENDED

**Proposal:** Support `s`/`m`/`h`/`d` suffixes. Pydantic validation at config-load time.

**Convergence:** Architect, End-User, and Security all agree. No dissent.

**RECOMMENDED: Adopt as specified. Fail-fast at config load.**

---

## Q8: Body Wire Format — RECOMMENDED (D7 implication change)

**Proposal:** `body: str` on the wire for ALL consumers. Engine-internal `list[Section]` does not leak. No Brief A revision needed for `TaskFull.body` typing.

**Convergence:** Architect, Data, and End-User all agree. This CHANGES the implication of D7 as currently written — D7 says "body: list[Section]" but that is now explicitly engine-internal only. Wire consumers see rendered markdown.

**RECOMMENDED: `body: str` on wire. D7's `list[Section]` is the engine's internal model. Brief B must clarify that D7 does not imply a wire-format change.**

---

## Q9: Cockpit Sessions — historical synthesis (superseded)

Outcome note (post final decisions): this discussion was superseded by D31/D32/D33/D43 and the final SessionRecord unification. Closed-session filters remain supported (`"all"`, `"blocked-or-rejected"`, `"released"`), the activity stream is first-class product data rather than a diagnostic side-channel, `last_end_outcome` was not adopted, and `agent_name` removal stands on the no-identity path rather than on a diagnostic-log rationale. The text below is retained as historical deliberation only.

**Proposal:** Narrow `/api/sessions` to running + stuck only. Drop closed-session listing per D10.

**Convergence:** Architect and End-User agree on the narrowing. Security: no impact given D10.

**Sub-question — `last_end_outcome` field:** End-User proposes adding `last_end_outcome: str | None` to the Task model, set by `end_work`, cleared on `move_task`. Purpose: one-glance Cockpit debugging ("last outcome: reject") without drilling into body. Nobody else weighed in. Architect and Data should have a view — this is a model addition that crosses the "no implementation" boundary if not scoped carefully.

Historical recommendation at synthesis time: narrow sessions to running+stuck and flag `last_end_outcome` as needs-decision. Superseded by the final D31/D43 path.

---

## Additional Cross-Cutting Risks

### R1: Activity Log Naming — historical recommendation

**Proposal:** Rename from "audit log" to "diagnostic log" in Brief B language.

**Source:** Security. Rationale: no tamper-evidence, no write-once guarantees, no integrity checksums. Calling it "audit" implies trust properties it cannot provide. Security also specifies: curation ownership (rotation, truncation) belongs to the launching script, not the engine.

**No dissent.** Other panelists use "audit-only artifact" language but don't contest renaming.

Historical recommendation at synthesis time: rename to "diagnostic log". Superseded by the final D32/D43 activity-stream contract.

### R2: `last_end_outcome` Field — historical open question

**Proposal:** New Task model field `last_end_outcome: str | None`. Set by `end_work` to outcome value. Cleared on `move_task`.

**Source:** End-User only. Architect, Data, and Security did not address.

This is a model addition with write-path implications (`end_work` writes it, `move_task` clears it). It compensates for D10's loss of session history. The UX argument is sound — but it needs Architect/Data buy-in since it touches the model and write semantics.

Historical unresolved question at synthesis time: include `last_end_outcome` in Brief B model spec, or defer to a follow-up? Final brief did not adopt it.

### R3: `agent_name` in Constructor — historical recommendation

**Proposal:** D11 makes `agent_name` vestigial (only used by activity log writes, which are diagnostic-only per D10). Drop the parameter.

**Source:** Architect flagged as vestigial but deferred removal. D11 + D10 together eliminate all semantic uses. Keeping it adds confusion about whether identity matters.

**RECOMMENDED: Drop `agent_name` from `KanbanEngine.__init__` in Brief B spec. Activity log can use a fixed string or omit the field. No follow-up needed — the semantic justification is gone.**

### R4: `refresh_config` Cache Invalidation — RECOMMENDED

**Proposal:** Brief B contract should document that `refresh_config()` is a heavy operation (reloads config + invalidates task cache) and specify when consumers should call it.

**Source:** Landscape Red Flag #8. No panelist explicitly addressed it.

**RECOMMENDED: Brief B includes a note: "`refresh_config()` invalidates all caches. Consumers should call it only on explicit user action (e.g., Cockpit reload button), not on every request." This is a contract warning, not a new feature.**

### R5: AST Test for Cockpit Role View Enforcement — RECOMMENDED

**Proposal:** Brief B specifies an acceptance criterion: an AST/import test scans all Cockpit route files and verifies they access only `CockpitEngineView` methods, never the full `KanbanEngine` or `AgentEngineView`.

**Source:** Security. Extends existing `test_cockpit_boundary.py` precedent. Landscape confirms Cockpit mutation routes currently bypass the adapter (Red Flag #12, fixed by D21).

**RECOMMENDED: Add as explicit Brief B AC. The test is the enforcement mechanism for D9's type-level capability contract.**

### R6: Max Body Size Cap — RECOMMENDED

**Proposal:** Engine enforces a maximum body size (e.g., 1MB) at `edit_task`/`create_task` write time. `ValidationError` on exceed.

**Source:** Security. Prevents accidental agent append loops and protects section-parsing performance.

**No dissent.** Architect's body-parser warning implicitly supports bounding input size.

**RECOMMENDED: Specify 1MB cap in Brief B. Operational sanity, not security control.**

### R7: `dep_status` + `archival_reason` Coupling — RECOMMENDED

**Proposal:** When `edit_task` changes `archival_reason` on an archived task, the engine scans for dependents and includes guidance warning.

**Source:** Data (Risk 1). The coupling is real: changing a dep's reason from `completed` to `wontfix` silently flips dependents from `ok` to `blocked`.

**RECOMMENDED: Document the coupling explicitly in Brief B. Include guidance on archival_reason mutation. No stored notification — compute at response time.**

### R8: Sweep Compare-and-Clear Safety — RECOMMENDED

**Proposal:** `sweep()` must not clear a claim whose `claimed_at` differs from the expired value it observed. Compare-and-clear semantic.

**Source:** Architect (AC-9). Prevents sweep from destroying a fresh claim placed between sweep's read and clear.

**RECOMMENDED: Specify compare-and-clear contract in Brief B. Implementation strategy is Brief C's freedom.**

### R9: Concurrency Token Type (`updated` vs `revision`) — OPEN

This is the token-type axis of Q1, broken out because it's orthogonal to the required/optional axis.

| Position | Panelists | Core Argument |
|----------|-----------|---------------|
| ETag-style on `updated` timestamp | Architect, End-User, Security | Existing field, zero migration, familiar HTTP semantics |
| `revision: int` counter | Data | Deterministic, immune to clock edge cases, natural DBMS fit |

Data's argument is technically stronger. Architect/End-User/Security assumed `updated` without analysing the edge cases Data raised (microsecond collisions, string comparison brittleness). Migration cost is near-zero per Data's analysis.

**User must decide:** `updated` (familiar, zero new fields) or `revision: int` (technically superior, one new field)?

---

## Critic Loop-Back Findings

| Panelist | Critic Issue Found | Resolution |
|----------|-------------------|------------|
| Architect | Wave algorithm needed bidirectional dep check (task X skipped if it depends on OR is depended on by a wave member). | Corrected in hardened stance. |
| Architect | `end_work` concurrency gap — zombie agent path was unguarded. | Added optional OCC to `end_work`. Security argues optional is insufficient. |
| Architect | `sweep()` race against concurrent claim — stale sweep could clear fresh claim. | Added compare-and-clear contract (AC-9). |
| Architect | Null-agent DispatchEntries could leak if agent_map incomplete. | Added fail-fast validation at construction. |
| Data | Section parsing must be fence-aware (code blocks with `## Heading`). | Specified as parsing rule. |
| Data | Missing dependency treated as `blocked` (defensive). | Specified in dep_status computation. |
| End-User | Changed Q2 position from loose to tight after recognising D7 makes structural checking trivial. | Adopted tightened predicate. |
| Security | Q1 is a blocking dependency for D11. Optional tokens + dropped identity = unguarded `end_work`. | Flagged as coupled decision — not resolved by any panelist. |

---

## Recommended User-Decisions for M4

The Mediator should present these items for confirmation before M5 drafting. Items marked **RECOMMENDED** have a synthesised position; items marked **OPEN** require a user choice.

1. **Q1a — Token requirement scope** `OPEN`: (a) Required on `edit_task`/`move_task`/`end_work` [Security], (b) Optional at engine, required only via CockpitEngineView [Architect/End-User], (c) Required on `edit_task` only [Data]. **Recommendation: (a) — Security's coupling argument with D11 is the strongest.**

2. **Q1b — Token type** `OPEN`: (a) `updated` timestamp [Architect/End-User/Security], (b) `revision: int` counter [Data]. **Recommendation: (b) — technically superior, near-zero migration.**

3. **Q2 — Clarity gate predicate** `OPEN`: (a) Keep loose [Architect], (b) Tighten to `## AC` section requirement [End-User]. **Recommendation: (b) — D7 structured body makes the cost negligible and the quality gain real.**

4. **Q3 — Section model `level: int`** `RECOMMENDED`: Amend D7 to add `level: int`. All panelists agree.

5. **Q6 — `agent_map` completeness** `OPEN`: (a) Fail-fast, all statuses must be mapped [Architect], (b) `_default` fallback, permissive [Data]. **Recommendation: (a) — null-agent DispatchEntries are a worse failure mode than a startup error.**

6. **Q9 sub — `last_end_outcome` field** `HISTORICAL OPEN`: (a) Include in Brief B model [End-User], (b) Defer to follow-up. Final brief did not adopt it.

7. **R1 — Activity log naming** `HISTORICAL RECOMMENDATION`: Rename to "diagnostic log" throughout Brief B. Superseded by the final D32/D43 activity-stream contract. [Security]

8. **R3 — Drop `agent_name` from constructor** `HISTORICAL RECOMMENDATION`: the final D33 outcome still drops it, but on the no-identity rationale rather than the older diagnostic-log rationale.

9. **R5 — AST test for Cockpit role view** `RECOMMENDED`: Add as explicit Brief B AC. [Security]

10. **R6 — Max body size cap (1MB)** `RECOMMENDED`: Operational sanity cap at write time. [Security]

11. **D7 wire clarification** `RECOMMENDED`: D7's `list[Section]` is engine-internal only; wire format stays `body: str`. All panelists agree.

12. **R8 — Sweep compare-and-clear** `RECOMMENDED`: Specify contract; implementation is Brief C's freedom. [Architect]
