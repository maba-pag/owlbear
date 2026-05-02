# End-User Proposal — Memory Module Restructure

## Design Summary

Restructure `serve/mcp-memory/` from SQLite to markdown+frontmatter files in `.owlbear/memory/`, optimised for three consumer experiences: agents getting fast high-signal knowledge, curators browsing/approving efficiently, and humans reviewing in git diffs. The design prioritises **scanability** (both filename and content), **minimal friction for the common path**, and **clear error feedback** when things go wrong.

## Key Structural Choices

### 1. File Naming — Human-Scannable by Design

**Format:** `{category}/{short-slug}-{id6}.md`

Example directory listing:
```
.owlbear/memory/
├── behavior/
│   ├── git-staging-check-before-commit-a3f2c1.md
│   ├── never-retry-identical-commands-8b4e12.md
│   └── validate-file-exists-before-edit-c91d7a.md
├── knowledge/
│   ├── starlette-sse-deadlock-sync-client-f4a821.md
│   ├── mcp-tool-name-mangling-rules-2e8c43.md
│   └── apply-patch-cannot-delete-readd-d12f9b.md
├── preference/
│   ├── pro-con-confidence-in-recommendations-7c3a19.md
│   └── no-token-cost-mentions-unless-asked-1e4b56.md
├── context/
│   └── owlbear-dev-is-working-repo-b94e21.md
└── goal/
    └── reduce-agent-repeated-mistakes-e8f123.md
```

**Rationale:**
- Category subdirectories let humans and curators filter visually by type — `ls behavior/` shows all behavioral rules at a glance.
- Slugs are derived from content (first ~6 meaningful words, kebab-case). A human scanning filenames knows what's inside *without opening the file*.
- 6-char ID suffix prevents collisions without dominating the filename. It's the first 6 of the UUID — enough for uniqueness at <200 entries, and the full UUID lives in frontmatter.
- `git log .owlbear/memory/knowledge/` shows knowledge-specific changes. `git log .owlbear/memory/` shows all memory activity.

### 2. File Content — Frontmatter for Machines, Body for Humans

```yaml
---
id: a3f2c1d4-9876-4abc-def0-123456789abc
category: behavior
confidence: 0.85
approval: approved
scope_agent: builder
scope_project: null
source: reviewer
created: 2026-04-15T10:23:45+00:00
updated: 2026-04-20T14:11:02+00:00
---

Always run `git diff --cached --name-only` before committing task-scoped files.
`git add <paths>` does not unstage prior index entries — pre-staged unrelated
paths will silently be included in the commit.
```

**Design choices:**
- `approval` not `approval_state` — shorter, scans faster in YAML.
- `source` = the agent that recorded it (not `agent_id` — that's confusing when `scope_agent` also exists).
- Body is the learning itself — no headers, no wrapping, no ceremony. It's the one thing humans need to read.
- No `deleted_at` field. Deleted entries are *physically removed* (moved to git history). An entry exists or it doesn't. No zombie states cluttering the directory.

### 3. Agent Experience — `get_knowledge` Response Shape

When an agent calls `get_knowledge(agent_id="builder", limit=20, min_confidence=0.7)`:

```json
[
  {
    "id": "a3f2c1d4-...",
    "content": "Always run `git diff --cached --name-only` before committing...",
    "category": "behavior",
    "confidence": 0.85,
    "scope_agent": "builder",
    "approval": "approved"
  }
]
```

**UX decisions:**
- Response strips timestamps, source, and scope_project from the default view. Agents don't need creation metadata at pre-flight — they need *the knowledge*. Metadata is available via `list_entries` for curators.
- Sort order: approved before pending, then confidence DESC, then scope specificity (agent+project > agent-only > global). The most trustworthy, most relevant entries come first.
- Pending entries are included (not hidden) but sort below approved. Agents benefit from recent learnings even before curator review. The confidence threshold is the quality gate, not the approval state.
- **Response cap:** Hard limit of 50 entries max regardless of `limit` param. Agents should never load 200 entries into context — that defeats the purpose.

### 4. Curator Experience — Efficient Browse/Approve Workflow

`list_entries(status="pending")` returns entries sorted newest-first with full metadata:

```json
[
  {
    "id": "...",
    "content": "First 120 chars of the learning...",
    "category": "knowledge",
    "confidence": 0.72,
    "source": "reviewer",
    "scope_agent": null,
    "created": "2026-04-28T...",
    "approval": "pending",
    "file": "knowledge/starlette-sse-deadlock-sync-client-f4a821.md"
  }
]
```

**UX decisions:**
- `content` is truncated to 120 chars in list view — enough to assess without overwhelming. Full content requires reading the file or calling `get_knowledge`.
- `file` field included — curator can reference the exact file for manual inspection or to pass to `set_approval_state`.
- `list_entries` accepts filters: `status`, `category`, `scope_agent`, `since` (ISO date). Curator can narrow efficiently: "show me pending knowledge entries from this week."
- `set_approval_state` accepts entry ID (UUID or 6-char short ID). Short IDs are resolved against the directory — no need to copy full UUIDs.
- **Batch support:** `set_approval_state(ids=["a3f2c1", "8b4e12"], state="approved")` — curator shouldn't need 15 separate calls for a routine review session.

### 5. `record_learning` — Zero-Friction Write Path

Agent calls:
```
record_learning(
  agent_id="builder",
  content="Starlette sync TestClient deadlocks on SSE endpoints...",
  category="knowledge",
  confidence=0.8
)
```

Returns: `"recorded: knowledge/starlette-sse-deadlock-sync-client-f4a821.md"`

**UX decisions:**
- Slug is auto-generated from content. Agent never provides a filename.
- Return value includes the relative path — agent can reference it in commit messages or notes.
- Validation errors return structured, actionable messages:
  - `"error: confidence must be >= 0.7, got 0.5"` (not just "invalid")
  - `"error: invalid category 'insight'. Valid: preference, knowledge, context, behavior, goal"`
- `scope_agent` defaults to `agent_id` if omitted. Most learnings are agent-specific. Global scope requires explicit `scope_agent=null`.
- No duplicate detection at write time — that's the curator's job. Agents should never be blocked from recording.

### 6. Human Git Experience

A PR review shows:
```diff
+ .owlbear/memory/behavior/git-staging-check-before-commit-a3f2c1.md
```

Opening the diff:
```diff
+---
+id: a3f2c1d4-9876-4abc-def0-123456789abc
+category: behavior
+confidence: 0.85
+approval: pending
+scope_agent: builder
+source: reviewer
+created: 2026-04-15T10:23:45+00:00
+---
+
+Always run `git diff --cached --name-only` before committing task-scoped files.
```

**Why this works for humans:**
- Filename alone tells you *what changed* in the git log.
- Frontmatter is compact (8 lines) — doesn't dominate the diff.
- Content body is the actual learning — readable without YAML knowledge.
- Approval state changes show as a single-line diff: `- approval: pending` → `+ approval: approved`.
- Deletion is a file removal — clear in any diff tool.
- Category renames are file moves — `git mv` tracks them.

### 7. Discovery — Finding Relevant Entries

**Agent discovery (via tools):**
- `get_knowledge(agent_id, categories=["behavior"])` — filtered retrieval by domain.
- No full-text search tool needed at <200 entries. Confidence + category + scope provides sufficient filtering.
- If future scale demands it, add `search_knowledge(query, limit)` — but YAGNI at current scale.

**Human discovery (via filesystem):**
- `ls .owlbear/memory/knowledge/` — browse by category.
- `grep -r "SSE" .owlbear/memory/` — full-text search via standard tools.
- `git log --oneline .owlbear/memory/` — temporal discovery.
- Category subdirectories are the primary navigation aid. No index file needed.

**Curator discovery:**
- `list_entries(status="pending", since="2026-04-28")` — "what's new since last review?"
- `list_entries(category="knowledge", scope_agent="builder")` — "what has builder learned?"

### 8. Error Messages — Actionable, Not Cryptic

| Scenario | Message |
|----------|---------|
| Invalid category | `"error: invalid category 'insight'. Valid: preference, knowledge, context, behavior, goal"` |
| Low confidence | `"error: confidence must be >= 0.7, got 0.5"` |
| Entry not found | `"error: no entry matching id 'xyz123'. Use list_entries to find valid IDs."` |
| Invalid state transition | `"error: cannot transition from 'approved' to 'pending'. Valid transitions: pending→approved, pending→deleted, deleted→pending"` |
| Filesystem write failure | `"error: could not write entry. Check .owlbear/memory/ permissions."` |
| Slug collision (unlikely) | Append incrementing suffix: `-a3f2c1` → `-a3f2c1b`. No user action needed. |

Every error names the constraint, shows the invalid value, and tells the caller what to do next.

### 9. Content Organization — Grouping and Lifecycle

**Category subdirectories** (not flat):
- `behavior/` — operational patterns (do X, avoid Y)
- `knowledge/` — factual findings (X works like Y, tool Z has bug W)
- `preference/` — user/project preferences (always include confidence scores)
- `context/` — environmental context (owlbear-dev is the working repo)
- `goal/` — strategic objectives (reduce repeated agent mistakes)

**Lifecycle:**
- New entries land as `approval: pending` — visible to agents but sorted lower.
- Curator approves → `approval: approved` — sorts to top.
- Curator deletes → file removed from disk (git history preserves it).
- Curator merges → delete source entries, create one consolidated entry at higher confidence.

**No archive folder.** Deleted means gone (from the filesystem). Git is the archive. An `.owlbear/memory/.deleted/` folder would just accumulate noise that agents accidentally scan.

## Trade-offs

| Choice | Gain | Cost |
|--------|------|------|
| Category subdirectories | Human scanability, scoped `git log` | 5 directories to maintain; category rename = file move |
| Slug-based filenames | Instant recognition without opening | Slug generation logic; rare edge cases with very short content |
| Physical deletion (no soft-delete) | Clean directory, no zombies | Can't "undelete" without git; curator must be careful |
| Pending entries visible to agents | Fast value from fresh learnings | Lower-quality entries in pre-flight until curated |
| Batch approval | Efficient curator sessions | Slightly more complex tool implementation |
| 120-char truncation in list | Scanable curator view | May not be enough for some entries; full read needed |
| No full-text search tool | Simplicity at current scale | Would need adding if scale exceeds ~500 entries |

## Domain Rationale

The three users have fundamentally different interaction modes:

1. **Agents** interact via tool calls. They need *fast, relevant, high-signal responses* with no ceremony. The design optimises `get_knowledge` to return the minimum useful payload sorted by relevance. Agents don't browse — they consume.

2. **Curators** interact via tool calls in batch. They need efficient *scan → decide → act* loops. Truncated list views, batch operations, and temporal filtering serve this workflow. The curator should be able to review 20 pending entries in one session without tool-call overhead per entry.

3. **Humans** interact via filesystem and git. They need *readable filenames, compact diffs, and standard tool compatibility*. The design makes `ls`, `grep`, `git log`, and diff tools all work naturally. No special tooling required to understand what's in memory.

The design deliberately avoids optimising for one user at the expense of another. The slug filename serves humans (scanable) AND curators (the `file` field in list output). Category subdirectories serve humans (browsing) AND agents (category-filtered retrieval maps to directory structure internally).

## Confidence

**0.84** — High confidence in the file layout, naming, and UX decisions. The kanban pattern is proven at this scale. Minor uncertainty around: optimal slug length (6 words may be too long for some entries), whether batch approval belongs in v1 or v2, and whether `scope_project` earns its keep at current single-project scale.
