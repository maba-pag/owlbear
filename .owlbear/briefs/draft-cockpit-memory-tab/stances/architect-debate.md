# Architect Debate Log — Cockpit Memory Tab

## Cycle 1: Initial Draft → Critic

### Draft Position (summary)
1. Extract `serve/memory/` following kanban pattern
2. State machine enforcement moves into engine class
3. Cockpit mirrors kanban DI/cache pattern "exactly"
4. SSE extension is "minimal incremental work"
5. Frontend independent of #1638
6. Simple API surface (GET all, POST approve/edit, DELETE)

### Critic Challenges (Cycle 1)

| # | Severity | Challenge | My Assessment |
|---|----------|-----------|---------------|
| 1 | Critical | API inconsistency: GET returns all states including deleted, but hard-deleted pending entries won't exist | **Accepted — clarified.** Not a contradiction: GET returns what's on disk. Hard-deleted entries are simply gone. Made explicit in revised position. |
| 2 | Critical | Understated shared behavior — extraction scope is larger than "parsing + ~100 lines" | **Accepted.** Expanded extraction scope to include metadata-only list, visibility filtering, deleted-read rejection, scoped recall. |
| 3 | Critical | Storage root confusion (`.owlbear/memory/` vs `store/memory/entries/`) | **Accepted.** Verified via server.py — default is `.owlbear/memory/`. Made configurable in position. |
| 4 | Moderate | "Exactly mirrors kanban" is unsupported — cache model differs | **Accepted.** Changed to "follows same DI topology" with accurate cache description (blake2b hashing, not "newest mtime_ns"). |
| 5 | Critical | SSE is not minimal — hardcoded event types, separate watch root, frontend provider changes | **Accepted.** Revised to "bounded but non-trivial" with enumerated integration points. |
| 6 | Moderate | #1638 independence is aspirational — shell is hardcoded kanban-only | **Accepted.** Position now explicitly acknowledges shell modification is real work. |

### Blind Spots Surfaced (Cycle 1)

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Git audit lifecycle for cockpit mutations | Added as open design question. Per-mutation commits recommended but needs fresh design. |
| 2 | No concurrency model | Added OCC via `updated_at` token as new cockpit-specific contract. |
| 3 | Visibility policy not stated | Added admin-override recommendation with caveat that it needs product decision. |

---

## Cycle 2: Revised Position → Critic

### Revised Position Changes
- Expanded extraction scope (7 components enumerated)
- OCC via `updated_at` as new contract (not reused)
- Git lifecycle acknowledged as design question
- SSE = "bounded incremental work" (4 integration points)
- Shell modification acknowledged as real work
- Engine instance = app-scoped singleton
- Visibility = admin surface recommendation

### Critic Challenges (Cycle 2)

| # | Severity | Challenge | My Assessment |
|---|----------|-----------|---------------|
| 1 | Critical | Extraction is a repo-topology refactor, not a tab refinement — contradicts brief's "read files directly" assumption | **Rebutted.** The brief says "cockpit cannot import MCP server packages." A standalone `serve/memory/` is NOT an MCP server package — it satisfies the constraint. The brief's "read files directly" phrasing describes the mechanical outcome (cockpit reads files via shared engine), not a prohibition on shared packages. Kanban proves this interpretation. |
| 2 | Critical | Git batching is a design question, not transferable behavior | **Accepted.** Weakened from "inherit" to explicit open question. Per-mutation commits recommended for cockpit but needs fresh design. |
| 3 | Critical | OCC is new for memory, not reused — MCP tools don't share it | **Accepted and strengthened.** Made explicit that OCC is cockpit-introduced, MCP bypasses it (single-writer assumption). Engine supports both modes via optional parameter. |
| 4 | Moderate | Engine instance scope not stated (app vs request) | **Accepted.** Explicitly stated app-scoped singleton via WeakKeyDictionary pattern. |
| 5 | Critical | Pre-#1638 shell modification is deeper than "add a route" — shell is kanban-shaped globally | **Partially accepted.** Acknowledged the coupling depth, but the architectural direction (build as lazy module, migrate to config when #1638 lands) remains correct regardless of coupling depth. The coupling is a sizing concern, not an architectural one. |
| 6 | Moderate | SSE contract churn understated | **Accepted.** Position says "bounded but non-trivial" and enumerates the 4 integration points. Accurate as stated. |
| 7 | Moderate | Deleted visibility is an open question, not settled | **Accepted.** Downgraded from locked position to recommendation needing user decision. |

### Blind Spots Surfaced (Cycle 2)

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Caller identity / policy boundary — curator-only restrictions vs admin override | Added to open questions. Engine should accept visibility configuration; policy enforcement belongs in caller layer. |
| 2 | Brief baseline numbers inconsistent (103 vs 14) | Acknowledged as brief error. Position uses "current scale is small, ceiling ~500" without relying on precise count. |
| 3 | Error contract ownership — teaching messages are MCP-layer, not engine-layer | Implicitly handled: engine raises domain exceptions, callers augment with transport-appropriate messages. Teaching messages stay in MCP tools. |

### Assessment After Cycle 2

The Critic's second pass found precision gaps and open questions but did not challenge the fundamental structural direction. The core choice — extract to `serve/memory/`, share between consumers — remains unchallenged on structural grounds. All critical challenges were either accepted (leading to refinements) or rebutted with evidence.

**Position is solid. Publishing.**
