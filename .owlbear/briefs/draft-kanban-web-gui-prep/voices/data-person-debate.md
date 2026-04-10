# Data Person — Critic Debate Log

## Cycle 1

### Position
One canonical Task model (extra='allow') in the engine, TaskSummary for list projections, MCP boundary adapter, string timestamps, atomic writes.

### Challenges

**C1 — Timestamp sort is broken with mixed TZ offsets.**
ISO 8601 strings only sort correctly lexicographically when timezone offsets are identical. Go timestamps have +02:00; Python timestamps have +00:00. The engine's `tasks.sort(key=lambda t: t.created)` produces wrong ordering.

**Response: Accepted.** Verified in engine.py — sort by created/updated is pure string comparison (lines 147–158). This is a real data quality bug. Updated position: engine sort methods must parse timestamps to datetime for comparison. String storage remains correct; string comparison for ordering is not.

---

**C2 — Config staleness is out of scope per D2 (concurrency accepted risk).**
D2 says single-laptop, single-user, concurrency is accepted risk. Config caching is a concurrency concern.

**Response: Partially rejected.** D2 covers concurrent write safety — "user overwrites an agent's quick edit." Config staleness is different: two long-lived processes (MCP server + GUI) each cache config at startup. If MCP's create_task bumps next_id to 800, but the GUI's engine instance still thinks next_id is 799, the GUI allocates a duplicate ID. This isn't a race condition — it's a stale cache across serial operations. create_task already reloads config specifically to handle this. The pattern needs extending, not inventing.

---

**C3 — extra='allow' silently accepts typos in frontmatter keys.**
A misspelled `proirity: needed` silently becomes an extra field while the real `priority` gets the default value. No validation, no warning.

**Response: Accepted as trade-off, not as change.** The alternative (extra='forbid') would reject legitimate vendor fields like `class`, `started`, `completed`. The correct mitigation is engine-level validation of constrained fields (status, priority) against config-defined enums — which move_task already does for status. Extend the pattern, don't change the model config.

## Cycle 2

### Updated Position
Added: parsed-datetime sort keys, config freshness per create, engine-level enum validation for status/priority.

### Challenges

**C4 — TaskSummary placement: engine or MCP server?**
If TaskSummary is in the engine, a UI concern (what fields to show in a list) leaks into the domain. If in the MCP server, it's just a renamed hand-built dict.

**Response: Rejected.** TaskSummary is a domain concept — "task identity and state summary" — not a UI concern. All consumers (MCP, GUI, CLI) need the same compact representation for listing tasks. The engine defines the canonical projection; consumers can further adapt. This is analogous to a database view: the schema defines useful projections, not just raw tables.

---

**C5 — KanbanTask.file field is dead (always None).**
The `file` field exists on the MCP boundary model but `_record_to_task` never populates it. Misleading schema.

**Response: Accepted.** A field that's always None is worse than absent — it misleads consumers. Two options: (a) populate it in the MCP adapter by passing the task path alongside the record, or (b) drop it from the boundary model. Added as a warning. The canonical engine model should NOT include file paths — that's an implementation detail.

---

**C6 — Activity log needs actor identity for multi-consumer.**
claim/release actions include agent_name in detail; edit/move/create do not. Can't distinguish sources in multi-consumer setup.

**Response: Accepted.** Not a model design question but an important data integrity warning for the restructuring. Added to warnings.

## Cycle 3

### Updated Position
Core model design is stable. Added file field warning, activity log actor warning.

### Challenges

**C7 — Body separator ambiguity with `---` in body content.**
Could the YAML frontmatter parser be confused by `---` lines in the markdown body?

**Response: Rejected (non-issue).** The parser finds only the FIRST `---` after line 0, which is the YAML closing delimiter. The body starts after that. write_task produces `---\n{yaml}---\n{body}`, so the closing delimiter immediately follows the YAML content. Body `---` lines appear after the parser has already split. Verified in task_io.py lines 150–168.

---

**C8 — Atomic write file permissions.**
tempfile.mkstemp creates files with restrictive permissions. The replaced file may have different permissions than the original.

**Response: Rejected (out of scope).** Minor concern for a Windows-primary single-laptop system. Not a data model issue. If it matters later, the fix is a two-line `shutil.copymode()` addition.

## Final Assessment

- **Cycles completed:** 3
- **Challenges raised:** 8
- **Accepted:** 4 (timestamp sort bug, config staleness scope, frontmatter typo trade-off acknowledgment, file field warning, activity log actor)
- **Rejected:** 3 (config staleness as pure D2 concern, TaskSummary as UI leak, body separator ambiguity, file permissions)
- **Position refined by:** timestamp sort must parse to datetime; config freshness is in-scope distinct from D2 concurrency; file field on KanbanTask flagged as dead; activity log needs actor field
- **Position held on:** string timestamp storage, extra='allow', TaskSummary in engine, canonical model without file path, YAML frontmatter format, atomic write pattern
