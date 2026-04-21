# Architect Debate Log — Brief B

## Critic Cycle 1

### Challenges Received

1. **Q1 OCC rationale contradicts D11.** Stance claimed "claims serialize agent access" but D11 explicitly defines claims as non-ownership tokens. Claims don't serialize anything. ACCEPTED — rewrote rationale to ground in consistent engine behavior (validate when present) rather than claim serialization.

2. **Q5 wave gates use current 7-gate set, missing dep_status.** The current dependency gate only skips tasks with active deps — it doesn't handle dep_status="blocked" (AC27/AC28). ACCEPTED — rewrote gate set to include dep_status-based exclusion and redirect guidance.

3. **Q6 agent_map missing rank.** Context B1 requires "status → agent name + rank." Bare `dict[str, str]` drops rank. ACCEPTED — added rank derivation from config list ordinals. STATUS_RANK = index in `statuses`, PRIORITY_RANK = index in `priorities`. Explicit and user-editable.

4. **Q8 body wire split uses views as representation dialects.** Using views to return different data shapes (structured vs string) exceeds their intended role as capability filters. Context says "Brief A is mutable" — should surface revisions, not work around. ACCEPTED — unified to `body: str` for all consumers. Views are pure capability filters. Structured body for Cockpit is YAGNI.

5. **Q9 ActiveSession.agent sources from claimed_by which D11 drops.** Once claimed_by is gone, agent field has no source. ACCEPTED — dropped `agent` from ActiveSession. Claims are anonymous under D11.

6. **Q2 TDD gate mitigation overstated.** TDD gate only applies to in-progress, not all active statuses. ACCEPTED — removed TDD-gate mitigation claim, replaced with honest risk assessment (false positive rate is low because dispatched tasks have been curated).

7. **Q3 missing repeated-heading behavior.** show_task(section="X") with multiple matches was unspecified. ACCEPTED — added explicit: multiple matches concatenated in document order, guidance reports count (per AC12). Missing section returns null + missing_sections (per AC11).

### Blind Spots Addressed

- **AC30 timestamp prefix.** Added AC-11 position: full ISO 8601 with offset for new appends, no retroactive rewrite.
- **Absent agent_map default.** Added explicit fallback behavior in Q6.

## Critic Cycle 2

### Challenges Received

1. **end_work is a body-writing mutation with no OCC.** Zombie-writer path: crashed agent calls end_work after task was re-claimed. D11 has no identity check. ACCEPTED — extended OCC model: end_work optionally accepts `updated` at engine level, same as all other mutations. Consistent concurrency model across all operations.

2. **Wave algorithm correctness bug.** If A depends on B and A sorts before B, both get admitted to the same wave — violating AC22. The dependency check was unidirectional. ACCEPTED — fixed to bidirectional: skip task X if any already-selected task in the wave has a dep edge with X in either direction.

3. **Metadata return shapes not explicitly confirmed.** Guidance, missing_sections, dep_status need defined return paths. ACCEPTED — clarified that Brief A already defines these (ListTasksResponse.guidance, ShowTaskResponse.missing_sections, TaskSummary.dep_status, etc.). Added explicit reference to Brief A projection schemas.

4. **Null-agent in waves undercuts engine-owned dispatch.** If agent_map is incomplete and null-agent tasks enter waves, orchestrator gets undispatchable work. ACCEPTED — changed to fail-fast: incomplete agent_map raises ValidationError at construction. Every DispatchEntry always has non-null agent.

5. **Sweep race — stale sweep clears fresh claim.** Consumer A observes expired claim, consumer B re-claims, consumer A's sweep clears the fresh claim. ACCEPTED — specified compare-and-clear semantic: sweep must not clear a claim whose claimed_at differs from the expired value it observed. Implementation strategy is Brief C's freedom.
