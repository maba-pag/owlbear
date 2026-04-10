# Security Voice — Critic Debate Log

## Cycle 1

### Position Presented
Initial security assessment identifying 8 concerns: consumer-boundary enforcement, TOCTOU, next_id race, activity log identity, GUI attack surface, path containment, agent_name self-assertion, schema monkey-patching.

Framed concurrency controls (next_id lock, modified_since guard) and activity log consumer identity as "recommendations."

### Critic Challenges
1. **next_id race condition framed as deferral but is a real data-loss risk.** "Recommend: file-level advisory lock... or at minimum document as known data loss scenario" is problematic — accepting known data loss is not acceptable if enabling concurrent consumers.
2. **TOCTOU framing too lenient.** If concurrent consumers are real, lost-write on human edit during agent claim is a blocker, not a follow-up.
3. **Activity log consumer identity is phrased as recommendation but should be a hard requirement.**
4. **Missing: what is the actual deployment model?** Same process or different processes? This shapes all risk assessments.

### Response
- **Accepted (deployment model):** Clarified MCP = stdio process per VS Code session, GUI = separate web server process. Different processes, same filesystem.
- **Accepted (activity log identity):** Elevated from recommendation to requirement of the restructuring.
- **Rejected (next_id and TOCTOU as blockers for THIS project):** The restructuring does not introduce the second consumer. Today: one consumer (MCP). After restructuring: still one consumer (MCP). The GUI is a separate future project. Concurrency risks become real when the GUI ships, not when the engine interface is restructured. However, the restructuring must not make mitigations harder to add later.

## Cycle 2

### Position Presented
Refined position with consumer identity as a requirement, concurrency controls as deferred-but-tracked, and deployment model clarified.

### Critic Challenges
1. **The restructuring creates an implicit multi-consumer contract** — even without the GUI, you should validate atomicity guarantees now (synthetic concurrency test).
2. **Consumer identity scope must be locked down** — constructor or per-call is a design decision that affects audit granularity. Decide now, don't defer.
3. **API boundary enforcement is "hope-based"** — documentation + code review is soft. Recommends runtime mode checks (`NotImplementedError` for agent-only methods in GUI context) or `_agent_only` decorator.
4. **Deferred risks lack a tracking mechanism** — verbal handoff to GUI brief will be forgotten. Needs to be in code/docs.

### Response
- **Accepted (consumer identity scope):** Locked to constructor-level. Each adapter gets its own engine instance with identity. Immutable per session. Decision made.
- **Accepted (atomicity documentation):** write_task atomicity should be explicitly documented/validated as part of restructuring, not assumed.
- **Accepted (tracking mechanism):** Deferred items must be captured in engine package documentation (SECURITY.md, docstrings, or inline comments), not just in this brief.
- **Rejected (runtime mode checks / _agent_only decorator):** Over-engineering for threat model. Single-developer laptop system. The person who would violate the boundary IS the person who designed it. Adapter pattern + documentation is proportionate. Runtime guards add complexity without addressing the actual trust boundary.

## Cycle 3

### Position Presented
Final hardened position with 7 items: adapter-pattern enforcement, constructor-scope consumer identity, data integrity foundation, deferred concurrency controls, GUI security constraints, audit trail with consumer source, documented trust assumptions. Confidence 0.88.

### Critic Response
**"Position is solid."** Threat model correctly scoped. Decisions proportionate to single-laptop, single-developer deployment. Adapter pattern vs. runtime guards distinction is sound. Consumer identity at constructor scope is clean. Distinction between restructuring risks and multi-consumer risks is correct. Agreed at 0.88 confidence.

One execution dependency flagged: the documentation work (SECURITY.md, docstrings, inline notes) capturing deferred constraints must actually happen — if skipped, the position collapses.

## Final Assessment

- **Cycles completed:** 3 (Critic exited at cycle 3 with "position is solid")
- **What changed:** Consumer identity elevated from recommendation to requirement; scope locked to constructor; deferred risks given a tracking mechanism (engine documentation); deployment model clarified
- **What held:** Adapter-pattern enforcement over runtime guards; concurrency controls deferred to GUI project; proportionate security for single-laptop threat model; rejection of over-engineering (decorators, mode checks)
