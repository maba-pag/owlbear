# Architect Stance — Brief C (Kanban Storage Layer)

**Panelist:** Architect
**Brief:** C — Kanban Storage Layer
**Critic cycles:** 5 (3 refinements, 2 confirmations)
**Confidence:** 0.88

---

## 1. Axis A — Task Body Shape

**Position: Hybrid structured skeleton — parsed sections with free-form prose content.**

The body is `list[Section]` per D7/D26 — this is not Brief C's invention but its implementation obligation. Each section:

| Field | Type | Rule |
|-------|------|------|
| `heading` | `str \| None` | `None` only for preamble (first element) |
| `level` | `int` | 0 for preamble, 2+ for headings |
| `content` | `str` | Free-form Markdown prose — storage does not validate internals |

**On-disk representation:** Standard Markdown with headings. The structure IS the Markdown — no JSON body, no parallel schema. A CommonMark-compliant parser (markdown-it-py) extracts sections at read time; the writer serialises `list[Section]` back to Markdown at write time.

**Validation boundary:** Storage validates **well-formedness** at read time (valid heading levels, preamble-only-first, YAML frontmatter integrity). Storage does NOT enforce predicates (required sections, list items) — that is the engine's job per D15 at status-transition time. This separation keeps storage a dumb persistence layer and the engine the policy enforcer.

**Interaction with `edit_task(append_body=...)`:** Append is section-aware. The appended text is parsed into sections, then merged with the existing body:
- If append starts without a heading → content appended to the last existing section.
- If append starts with a heading → appended as new section(s).
- The entire body is then serialised back through the normalised write path.

**Interaction with `show_task(section=...)`:** Filtering operates on `list[Section]` by `Section.heading` (case-insensitive, whitespace-stripped) per D26+D56. All matches concatenated in document order. Multiple matches → guidance with occurrence count. `body=None` + `missing_sections=[name]` if no match. This is structural object matching, not regex — satisfying Outcome 3.

---

## 2. Axis B — Persistence Backend

**Position: Filesystem (YAML frontmatter + Markdown body files).**

Weighted analysis of the four differentiators for THIS system (single laptop, ~150 active tasks, git-tracked board, PRs reviewed):

| Differentiator | Filesystem | SQLite | Weight | Winner |
|---|---|---|---|---|
| **Atomicity & corruption** | Atomic-rename + fsync: durable single-file writes; two-phase archive-move with detectable crash recovery | Free transactional atomicity; structurally superior | High | SQLite |
| **Git diff-reviewability** | Per-task Markdown diffs in PRs — actively used today | Opaque binary blob; history exists but not human-readable in PR view | High | Filesystem |
| **Cross-branch mergeability** | Per-file merge; rename/ID-rewrite feasible | Binary blob; unmergeable; forecloses the option permanently | Medium | Filesystem |
| **Structure-enforcement ergonomics** | Markdown with parsed sections implements Axis A cleanly | Equal (relational rows implement it too); no advantage | Low | Tie |

**Verdict:** SQLite's atomicity advantage is real but narrow — closing the gap costs ~5 lines of fsync code. The three filesystem advantages are structural and two of them (diff, merge) are permanently forfeited by choosing SQLite. At this scale and concurrency, filesystem + fsync delivers sufficient atomicity without sacrificing the capabilities that the team actively uses.

### Atomic write primitive

```
mkstemp(dir=target_dir) → write → os.fsync(fd) → close → os.replace(tmp, target) → open(dir) → os.fsync(dir_fd) → close(dir)
```

This is the standard POSIX durable-atomic-write. Current code does `mkstemp → write → os.replace` but **skips both fsyncs**. Brief C closes this.

### Archive-move strategy (Critic-hardened)

Archive operations (`move_task(status="archived")`) use a two-phase approach:

1. Write updated task (status=archived, fields updated) atomically **directly to** `archive/{id}-{slug}.md`.
2. Remove `tasks/{id}-{slug}.md`.

**Crash between 1 and 2:** Task exists in both locations. Detected at next `list_tasks` as `ERR_CORRUPT_DUPLICATE_LOCATION`. Resolution: archive copy is canonical (later timestamp, correct status); delete stale `tasks/` copy. The crash window is microseconds; this scenario has zero observed occurrences in three months.

### On-disk layout

No change to directory structure:

| Path | Purpose |
|------|---------|
| `.owlbear/kanban/tasks/{id}-{slug}.md` | Active task files |
| `.owlbear/kanban/archive/{id}-{slug}.md` | Archived task files |
| `.owlbear/kanban/config.yml` | Board configuration |
| `.owlbear/kanban/.next_id.lock` | flock file for atomic ID allocation |

---

## 3. Structural Concerns

### 3.1 Atomic ID allocation

**Keep `.next_id.lock` flock.** It is correct, race-safe via flock, and the only concurrency primitive that has been tested under dual-orchestrator conditions. The lock scope already covers the full `load_config → write_task → bump_id → save_config` sequence. No reason to change a working primitive.

### 3.2 Locking strategy

**No additional locking beyond the ID flock.** Reasoning:

- Single laptop, single user. Concurrency is accidental (dual-orchestrator testing only).
- Reads are naturally safe (mtime-cached; worst case reads a mid-write temp file which doesn't exist at the target path because of atomic-rename).
- Writes are atomic-rename (last writer wins, which is correct for single-writer steady state).
- OCC tokens (D22/D23/D46) handle Cockpit edit conflicts at the application level.
- The system has operated for three months with no locking beyond ID allocation and zero data corruption.

### 3.3 PyYAML / ruamel convergence

**Converge to ruamel.yaml only. Drop PyYAML.**

| Direction | Loader | Rationale |
|-----------|--------|-----------|
| **Read** | `YAML(typ='safe')` | Fast (no round-trip overhead), YAML 1.2 default, sufficient for Pydantic ingestion |
| **Write** | `YAML(typ='rt')` | Preserves key order; produces canonical output |

Both directions strip the timestamp implicit resolver (same pattern as existing code, now in one library's API instead of two). Go-era 7-digit-nanosecond timestamps survive as strings.

Cold-boot cost: ~2ms/file × 150 files ≈ 300ms for first `list_tasks`. Acceptable for a CLI/MCP tool that starts once per session. Steady-state: mtime cache means only changed files are re-parsed (0-2 per call).

### 3.4 Persistent index

**Not needed.** At ~150 active tasks, `os.scandir` + mtime cache is sub-millisecond steady-state. A persistent index adds complexity (invalidation, corruption modes, migration) for zero measurable benefit. YAGNI.

### 3.5 CorruptionError modes

Seven corruption modes detected at read time. Storage raises `CorruptionError` to engine; engine propagates to consumer (MCP → ToolError, Cockpit → HTTP 500). **No auto-repair** per D19 principle.

| # | Mode | Code | Trigger |
|---|------|------|---------|
| 1 | Missing YAML delimiters | `ERR_CORRUPT_DELIMITERS` | `---` not found or malformed |
| 2 | Duplicate task ID | `ERR_CORRUPT_DUPLICATE_ID` | Two files claim the same `id` field (D19) |
| 3 | Required field missing | `ERR_CORRUPT_MISSING_FIELD` | `id`, `title`, `status`, `priority`, `created`, `updated` absent |
| 4 | Field type violation | `ERR_CORRUPT_FIELD_TYPE` | e.g. `id` not int, `tags` not list |
| 5 | YAML parse error | `ERR_CORRUPT_YAML` | Malformed YAML in frontmatter |
| 6 | ID-filename mismatch | `ERR_CORRUPT_ID_MISMATCH` | Frontmatter `id` ≠ filename `{id}-` prefix |
| 7 | Duplicate location | `ERR_CORRUPT_DUPLICATE_LOCATION` | Same task ID in both `tasks/` and `archive/` (crash recovery artifact) |

**Not corruption (handled elsewhere):**
- Missing body sections → predicate failure at transition time (D15)
- Archive files with extra fields → tolerated via Pydantic `extra="allow"`
- Empty body → valid

### 3.6 Predicate DSL extensions

**No new keys beyond D64.** The existing keys (`required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`, `non_impl_tags`) + structural section parsing fully deliver Outcome 3. The big win is making these keys operate on `list[Section]` objects instead of regex over rendered Markdown — that is Brief C's structural contribution.

Future extensions are discrete decisions per D64's extensibility clause, added when a pipeline failure demonstrates the need. YAGNI now.

---

## 4. D40 — Body Round-Trip Semantics

**Position: Structurally normalised, content-preserved.**

The round-trip is NOT byte-exact at the file level, but section content IS byte-exact within each section.

### Normalisation rules (applied by storage writer)

| Element | Rule |
|---------|------|
| Heading format | Single space after `#` markers: `## Heading` |
| Inter-section spacing | Exactly one blank line between sections |
| Trailing newline | Always present at EOF |
| Leading blank lines | Stripped before first content |

### Preservation rules (byte-exact)

| Element | Rule |
|---------|------|
| Section `content` | Preserved verbatim — including trailing whitespace on lines (Markdown `<br>`), internal blank lines, indentation |
| Code block content | Preserved verbatim (parser is code-block-aware per D26) |
| Frontmatter field order | Preserved (ruamel `rt` writer) |
| Frontmatter extra fields | Preserved (Pydantic `extra="allow"`) |

### Consequences

**`show_task(section=...)`:** Returns the normalised rendering of matching section(s). Heading format is canonical; content is verbatim. Predictable — what was written is what comes back, modulo heading whitespace.

**`edit_task(append_body=...)`:** Section-aware merge. The append text is parsed into sections and merged structurally (see §1). The result is normalised through the write path. No string-concatenation surprises.

**Agent-visible contract:** "Write a body; read it back; headings may be whitespace-normalised; everything else is verbatim." Satisfies Outcome 6.

---

## 5. Key Trade-offs

| Trade-off | Accepted cost | Gained benefit |
|-----------|--------------|----------------|
| Filesystem over SQLite | Two-phase archive-move with microsecond crash window; 7 corruption modes to detect | Git diff-reviewability, cross-branch mergeability, no binary blob |
| Normalised round-trip over byte-exact | Heading whitespace may change on write | Canonical output; eliminates whitespace-variant drift across tools |
| No persistent index | Cold-boot ~300ms for 150 files | Zero index maintenance, zero index corruption modes |
| ruamel-only over hybrid | ~10x slower YAML parse than PyYAML C-ext | Single library; no impedance mismatch; YAML 1.2 by default |
| No new DSL keys | Future extensions require new decisions | No speculative complexity; D64 keys cover demonstrated needs |

---

## 6. Warnings

1. **The archive-move two-phase gap is real.** It produces a detectable, recoverable inconsistency — not silent corruption — but it IS a D41 deviation for the archive path specifically. If the Mediator or user considers this unacceptable, the fallback is a write-ahead intent file (`{id}.intent` written atomically before the move, cleaned up after) that turns crash recovery into an automated replay. I consider this over-engineering for a microsecond window with zero historical occurrences.

2. **ruamel cold-boot performance is untested at 150 files.** The estimate (300ms) is based on published benchmarks, not measured in this codebase. Brief C implementation should include a one-time benchmark; if >500ms, fall back to `YAML(typ='base')` and let Pydantic handle all type coercion.

3. **Section-aware `append_body` changes semantics.** Current `append_body` is pure string concatenation. The new behaviour (parse → merge → serialise) means an append that contains `## Heading` will create a new section instead of being literal text. This is correct behaviour (it's what agents intend) but is a visible semantic change. Agents that append literal `#` characters in prose should use code fences.
