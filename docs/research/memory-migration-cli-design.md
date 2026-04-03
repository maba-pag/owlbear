# Memory Migration CLI Tool Design

> **Owning task:** #527 — Build memory migration CLI tool
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #527 designs a CLI tool to bulk-import existing `/memories/repo/` files into the memory.db SQLite database (defined by #524). The design doc (`docs/research/memory-mcp-server-design.md` sec 3L) outlines a 5-phase migration path; this task is Phase 3 (bulk import). It depends on #524 (scaffold mcp-memory), which is blocked by DR 387.

**Research questions:** (a) What files should be migrated? (b) How to parse them? (c) How to map all 12 schema fields? (d) Where should the CLI live? (e) What CLI framework? (f) Idempotency and error handling?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Memory-mcp design doc sec 3L | `docs/research/memory-mcp-server-design.md` | .95 |
| S2 | Mem0 CLI import command | `docs.mem0.ai/platform/cli` | .80 |
| S3 | Knowledge loader (project prior art) | `packages/knowledge/src/owlbear_knowledge/loader.py` | .85 |
| S4 | Analysis CLI (project prior art) | `packages/orchestrator/src/owlbear_orchestrator/analysis/_cli.py` | .80 |
| S5 | Actual inbox files (13 files) | `/memories/repo/inbox/*.md` | .95 |
| S6 | Actual established repo files (7 files) | `/memories/repo/*.md` | .90 |
| S7 | Design doc sec 3B (12-field schema) | `docs/research/memory-mcp-server-design.md` | .95 |

## 3. Analysis

### 3A. Scope: Which files to migrate?

| Source type | Count | Format consistency | Value as memory entries |
|-------------|-------|--------------------|------------------------|
| Inbox files (`inbox/*.md`) | 13 | High — consistent header + category-prefixed bullets | High — atomic lessons, maps directly to schema |
| Established files (`*.md`) | 7 | Low — heterogeneous sections, tables, code blocks, multi-paragraph | Low — curated reference docs, not atomic facts |

Inbox files have a consistent format: `# Lessons: #{id} ({agent}, {date})` followed by `- {category}: {text}` bullets. Each bullet is an atomic lesson that maps cleanly to a memory entry.

Established files (kanban-md-limits.md, process-patterns.md, etc.) are curated reference documents with complex structure: `##` sections containing tables, code blocks, evidence citations, and multi-paragraph prose. Converting these to flat `content` strings loses their relational structure and produces entries of wildly varying size (2–30+ lines per section). These files are already auto-loaded into agent context via the `/memories/repo/` convention in copilot-instructions.md.

**Recommendation (.85):** Migrate **inbox files only**. Established files should remain as `/memories/repo/` reference docs — they serve a different purpose (curated knowledge vs atomic lessons). This simplifies scope and eliminates the fragile established-file parser. The existing AC line "reads established repo memory files" should be narrowed by the architect.

### 3B. Parsing inbox files

Inbox format (confirmed across all 13 files):
```
# Lessons: #{task-id} ({agent}, {date})

- {category}: {text}
- {category}: {text}
...
```

**Parsing approach:** Regex extraction. Two patterns:
1. Header: `r"^# Lessons:\s*#(\d+)\s*\((\w[\w-]*),\s*(\d{4}-\d{2}-\d{2})\)"` → task_id, agent, date
2. Bullets: `r"^- (\w+):\s*(.+)$"` → category, content (multiline not observed in current corpus)

No markdown parser library needed (KISS, S3 uses regex similarly for YAML manifests).

### 3C. Full 12-field mapping for inbox entries

| Field | Source | Value |
|-------|--------|-------|
| `id` | Generated | `uuid.uuid4()` |
| `content` | Bullet text | Content after category prefix |
| `category` | Bullet prefix | Mapped per sec 3D |
| `confidence` | Default | `0.7` (per AC) |
| `created_at` | Header date | Parsed from `{date}` in header |
| `updated_at` | Header date | Same as `created_at` (no edit history) |
| `source` | Filename | `migration:{filename}` (e.g., `migration:141-builder.md`) |
| `scope_agent` | Header agent | Extracted agent name (e.g., `builder`, `researcher`) |
| `scope_project` | Runtime | Current project name from `owlbear-project.json` or `None` |
| `approval_state` | Default | `pending` (per AC) |
| `deleted_at` | Default | `NULL` |
| `content_hash` | Computed | `hashlib.sha256(content.strip().encode()).hexdigest()` if field exists; `NULL` if DR 387 excludes pattern 3 |

### 3D. Category mapping

| Inbox prefix | Memory category | Rationale |
|-------------|----------------|-----------|
| `problems_faced` | `knowledge` | Factual observation about what went wrong (S1 sec 3L) |
| `workarounds_applied` | `knowledge` | Factual resolution technique (S1 sec 3L) |
| `patterns_discovered` | `behavior` | Prescriptive rule for agent behavior (S1 sec 3L) |
| `time_sinks` | `context` | Environmental context about effort (S1 sec 3L) |
| `quality_gaps` | `context` | Environmental context about upstream quality (S1 sec 3L) |
| (unknown prefix) | `knowledge` | Safe default; flagged in dry-run output |

### 3E. CLI location and framework

| Option | Location | Framework | Pros | Cons |
|--------|----------|-----------|------|------|
| **A (rec)** | `packages/mcp-memory/.../migrate.py` | argparse | Co-located with schema/models; matches loader.py pattern (S3) | Depends on #524 existing |
| B | `scripts/migrate_memory.py` | argparse | Independent of #524; raw SQLite writes | Schema drift risk; cross-package if importing models |

**Recommendation (.80):** Option A — place in mcp-memory package. The dependency on #524 is already encoded (`depends_on: [524]`). Co-location ensures schema changes propagate to the migration tool. Matches the knowledge loader pattern (S3) which lives in `packages/knowledge/`.

### 3F. Idempotency strategy

Running the migration twice must not create duplicates. Two approaches:

| Approach | Mechanism | Complexity |
|----------|-----------|------------|
| **Source-field matching (rec)** | Before INSERT, check `WHERE source = 'migration:{filename}'`; skip if exists | Low — single SQL query per file |
| Content hash dedup | Check `WHERE content_hash = ?`; skip if exists | Depends on pattern 3 approval |

**Recommendation (.85):** Source-field matching. Each file has a unique filename, so `source` field provides natural idempotency key without depending on pattern 3 (S1 sec 3K, not in DR).

### 3G. Dry-run mode

Match mem0 CLI pattern (S2: `mem0 delete --dry-run`): collect all entries to create, print summary table (filename, entry count, categories), then exit without writing. Implementation: `--dry-run` flag on argparse (S4 pattern).

## 4. Recommendation (.80 confidence)

Inbox-only migration via argparse CLI in `packages/mcp-memory/`, with regex parsing, full 12-field mapping including `scope_agent` extraction from headers, source-field idempotency, and dry-run mode. Narrow the AC to exclude established files (they're already served by `/memories/repo/` and would produce low-quality entries).

Challenge: block — confidence in original: .45. Challenger surfaced valid gaps: established files are unsuitable for migration (accepted — revised to inbox-only), 7 of 12 schema fields were unaddressed (addressed in sec 3C), idempotency gap (addressed in sec 3F), and DR 387 dependency (acknowledged — already in `depends_on`). Revised confidence .80 after integrating feedback.

## 5. Follow-up Tasks

T1 classification — utility script, no new capability, no arch/agent/security change. No DR needed for the migration tool itself (DR 387 covers the parent capability).

The existing task #527 AC should be refined by the architect to reflect inbox-only scope and full field mapping. No new tasks needed — #527 covers the work.
