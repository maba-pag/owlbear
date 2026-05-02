# Synthesis — Memory Module Restructure (compare)

## Divergence Matrix

| Decision Point | Architect | Data | Enduser | Security | Tension Level |
|---|---|---|---|---|---|
| **Directory structure** | Flat `entries/` subdir | Flat `entries/` subdir | Category subdirectories (`behavior/`, `knowledge/`, etc.) | Flat directory (no subdirs — eliminates traversal via dir creation) | **high** |
| **Filename convention** | `{uuid8}-{slug}.md` — human-scannable in git log | `{uuid}.md` — stable across edits, no rename cascade | `{slug}-{id6}.md` — instant recognition without opening | `{uuid}.md` — eliminates path traversal entirely | **high** |
| **Soft delete vs hard delete** | Soft delete (`approval_state: deleted`, file stays) | Soft delete (file stays, `deleted_at` timestamp) | Hard delete (file removed, git history is the archive; no zombie states) | Soft delete only via MCP; hard purge is manual-only, never automated | **high** |
| **Deduplication at write time** | Not addressed | Yes — content+agent SHA-256 fingerprint; upserts confidence if higher | No — "that's the curator's job; agents should never be blocked from recording" | Not addressed | **medium** |
| **Corruption quarantine** | Explicitly no corruption detection (simpler than kanban) | Full quarantine protocol — 8 error codes, move to `quarantine/` dir, `.reason` files, never abort load | Not addressed | Reject invalid input at boundaries; no quarantine directory | **medium** |
| **State transition: approved→deleted** | Not detailed | Explicitly disallowed (must go through pending; delete only unvetted entries) | Not applicable (hard delete = file removal) | Explicitly allowed (part of the valid FSM) | **medium** |
| **Curator-only tool restriction** | Not restricted at tool level | Not restricted at tool level | Not restricted at tool level | `set_approval_state` and `mark_for_deletion` exposed only to curator via MCP tool registration | **medium** |
| **Entry/content limits & rate limiting** | None specified | Body must be non-empty (invariant I6) | None specified | 500 entry hard cap, 20 writes/session rate limit, 4096 char content max | **medium** |
| **Secret scanning on write** | Not addressed | Not addressed | Not addressed | Full regex scan (ghp_, sk-, AKIA, xox, absolute paths); reject with clear error, never log rejected content | **medium** |
| **Immutable fields after creation** | Not specified | Not explicitly specified (strict invariants imply it) | Not specified | Explicit: `id`, `created_at`, `source`, `scope_agent` locked post-creation; edits limited to `content`, `confidence`, `category` | **low** |
| **Batch approval** | Not addressed | Not addressed | Yes — `set_approval_state(ids=[...], state=...)` for efficient curator sessions | Not addressed | **low** |
| **`storage_io` import strategy** | Inline copy (40 lines; avoid cross-package dep) | Not specified | Not specified | Direct reuse from kanban module | **low** |
| **Frontmatter field naming** | `created`/`updated`/`approval_state` (kanban-aligned) | `created_at`/`updated_at`/`approval_state` | `created`/`updated`/`approval` (shortest) | `created_at`/`approval_state` | **low** |
| **Response cap on `get_knowledge`** | Not specified | Not specified | Hard limit 50 entries max regardless of `limit` param | Not specified | **low** |
| **Short-ID resolution** | 8-char prefix in filename (implicit support) | No — full UUID filename, strict invariant I1 | Yes — 6-char short ID accepted by `set_approval_state` | No — full UUID only | **low** |

## Common Ground

- **Storage format:** Replace SQLite with per-entry `.md` files using YAML frontmatter + markdown body. All four agree.
- **Storage root:** `.owlbear/memory/` (inside ops-data namespace, same pattern as kanban).
- **Tool surface:** Preserve all 5 existing MCP tools (`get_knowledge`, `record_learning`, `list_entries`, `set_approval_state`, `mark_for_deletion`) with compatible semantics.
- **Entry IDs:** UUIDv4 (random). Full UUID stored in frontmatter `id` field.
- **Data model core:** `id`, `category`, `confidence`, `approval_state`, `source`, `scope_agent`, `scope_project`, plus timestamps. Body is free-form markdown.
- **Categories:** Exactly five — `preference`, `knowledge`, `context`, `behavior`, `goal`. Enum-enforced.
- **Confidence range:** `[0.7, 1.0]`, validated at write boundary via Pydantic.
- **New entries always start as `pending`** — never caller-controlled approval state on creation.
- **Core state transitions:** `pending→approved` and `pending→deleted` are valid. All agree on these two.
- **`source` field:** Records the agent that created the entry (replaces the overloaded `agent_id` name).
- **Pydantic validation** on every read and write path. No "maybe valid" entries.
- **Atomic writes:** `mkstemp` → write → `fsync` → `os.replace` → `fsync` parent. Proven kanban pattern.
- **YAML safe loading only** — never `FullLoader` or `UnsafeLoader`. Pydantic as second validation gate.
- **Full in-memory load** on startup. No lazy loading, no caching, no indexing at <200 entry scale.
- **No OCC / file locking** at current scale. Single-session MCP, add later if needed.
- **One-shot migration** from SQLite with verification. SQLite file preserved for rollback.
- **Scope-based retrieval:** Filter by `scope_agent` and `scope_project`. Global entries (null scope) visible to all.
- **Sort order for agents:** Approved before pending, higher confidence first, scope-specific before global.
- **`config.yml` deferred** — no config file in v1; environment variables sufficient.
- **Temp file cleanup** on startup (orphaned `.tmp-*` files from interrupted writes).

## Open Questions

1. **Flat directory vs category subdirectories?** Architect, Data, and Security all propose flat storage; Enduser proposes 5 category subdirectories for human scanability and scoped `git log`. Security explicitly argues against subdirectories (eliminates traversal via dir creation). At stake: human browsing UX vs filesystem security surface area vs implementation simplicity.

2. **Should filenames include content-derived slugs?** Architect and Enduser want human-readable filenames (slug-bearing); Data and Security want UUID-only filenames (stable, no traversal risk, no rename cascade on content edit). At stake: git log readability vs filename stability vs security.

3. **Soft delete or hard delete?** Architect, Data, and Security favour soft delete (file stays with `deleted` state); Enduser favours hard delete (file removed, git history is the archive). At stake: recoverability and audit trail vs clean directory and no zombie states. Linked question: if soft delete, should `deleted_at` be a field?

4. **Should `record_learning` deduplicate at write time?** Data proposes content+agent fingerprint checking with confidence upsert. Enduser explicitly opposes — agents should never be blocked, dedup is the curator's job. At stake: write-path simplicity vs data cleanliness at the source.

5. **How should corrupt/invalid files on disk be handled?** Data proposes a full quarantine protocol (8 error codes, move to `quarantine/` dir, continue loading). Architect explicitly chose no corruption detection. Security rejects at boundaries but has no quarantine. At stake: data recovery capability vs implementation complexity.

6. **Can approved entries be directly deleted?** Data says no (approved→deleted is disallowed; only unvetted entries can be deleted). Security says yes (approved→deleted is a valid transition). At stake: whether the curator can remove a previously-approved entry without an intermediate step.

7. **Should approval/deletion tools be curator-only?** Security proposes tool-level access control — `set_approval_state` and `mark_for_deletion` exposed only to the curator agent's MCP config. Other proposals don't restrict access. At stake: self-promotion prevention vs operational flexibility.

8. **Are entry caps and rate limits needed in v1?** Security proposes 500 entry hard cap, 20 writes/session, 4096 char max. Others propose none. At stake: DoS resistance from misbehaving agents vs YAGNI at current scale.

9. **Should content be scanned for secrets before write?** Only Security proposes this (regex patterns for tokens, API keys, absolute paths). At stake: preventing accidental secret commits vs write-path complexity and regex maintenance burden.

10. **Which timestamp field names?** Three variants proposed: `created`/`updated` (Architect, Enduser — kanban-aligned), `created_at`/`updated_at` (Data, Security), and shorter `approval` vs `approval_state`. Minor but needs one answer for the Pydantic model.
