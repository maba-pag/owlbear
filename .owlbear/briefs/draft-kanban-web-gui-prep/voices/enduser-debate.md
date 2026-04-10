# End-User Voice — Critic Debate Log

## Cycle 1

### Position Presented

Seven-point position on engine API design for GUI consumers:

1. Return rich task objects everywhere, kill the lean-dict hack
2. Board metadata should be queryable (statuses, priorities with display order)
3. Status transitions should be discoverable
4. Claim semantics should be invisible to GUI consumers
5. Efficient polling needs a board-level change signal (revision counter or last_modified)
6. `start_work`/`end_work` are agent workflows, not GUI operations
7. Engine should expose a high-level `get_board()` convenience

### Critic Challenges

**Point 1 — CHALLENGED.** "The lean-dict exists for a reason you're dismissing: LLM context window cost." Full TaskRecord with body/timestamps/deps for 40+ tasks burns thousands of agent tokens per poll. The fix isn't killing lean dicts — it's returning full TaskRecord from the engine and letting each boundary layer project what it needs. Engine deals in one canonical type; MCP adapter strips down; GUI adapter passes through.

**Point 5 — CHALLENGED.** "Over-engineered. The board is backed by a file on the local filesystem. The file's mtime is already a change signal." The GUI adapter can stat() the board file and skip re-fetching. A revision counter adds mutable state to a currently stateless engine.

**Points 2, 3, 4, 6, 7 — solid.** No material objections raised.

### Response

**Point 1 — ACCEPTED.** The Critic is right that token economy matters for the existing MCP consumer. Revised to: engine always returns `TaskRecord`, projection happens at each boundary. MCP projects lean dicts. GUI passes rich objects. This solves the three-representation problem without penalizing agents.

**Point 5 — REJECTED.** The Critic assumed a monolithic board file. The board is actually a directory of individual YAML frontmatter files (one per task). Directory mtime only changes on file add/remove, not on individual file modification (NTFS, APFS behavior). Checking "has anything changed?" via filesystem requires walking the entire tasks directory and statting every file — more expensive than a single in-memory `int` that increments on writes. No persistence needed.

---

## Cycle 2

### Position Presented

Revised seven-point position with:
- Point 1 corrected: engine returns full TaskRecord, projection at boundaries
- Point 5 revised: in-memory revision counter justified by individual-file board structure

### Critic Response

**"Position is solid."** No material flaws found. One observation (non-objection): the revision counter answers "has anything changed?" but not "what changed?" — a GUI doing incremental re-rendering still diffs against full `get_board()` on counter mismatch. At this board scale (low hundreds of tasks), full-board diff is cheap enough that finer-grained change tracking would be over-engineering.

### Response

Acknowledged. The counter is the right primitive at this scale. Agreed that a change log would be over-engineering.

---

## Final Assessment

- **Cycles completed:** 2
- **What changed:** Point 1 refined from "kill lean dicts" to "projection at boundaries" — a more precise and consumer-fair formulation
- **What was challenged and held:** Point 5 (revision counter) — defended against filesystem-mtime alternative with evidence about individual-file storage
- **What was unchallenged:** Points 2, 3, 4, 6, 7 — all survived without objection
