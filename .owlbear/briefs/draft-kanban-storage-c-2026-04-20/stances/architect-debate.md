# Architect — Critic Debate Log

**Panelist:** Architect
**Brief:** C — Kanban Storage Layer
**Cycles:** 5

---

## Cycle 1 — Archive-move atomicity

**Critic:** You claim filesystem + atomic-rename satisfies D41 for all engine operations. But `move_task` to archive is a two-step operation: write_task to the current location, then `_move_file(src, archive_path)`. Even with fsync on the write, a crash between write and move leaves the task updated-but-not-moved. How is that D41-compliant? SQLite would do this in one transaction.

**Architect response:** Accepted. The two-phase archive move is a real gap. The fix is to change the archive-move strategy:

1. Write the updated task (status=archived, fields updated) atomically directly to `archive/{id}-{slug}.md` via the standard atomic-write primitive.
2. Remove `tasks/{id}-{slug}.md`.

If crash between 1 and 2: the task exists in both locations. This is a detectable corruption mode — same ID in both `tasks/` and `archive/`. Recovery: next `list_tasks` detects the duplicate location, raises `CorruptionError(ERR_CORRUPT_DUPLICATE_LOCATION)`. Manual resolution: the archive copy is canonical (it has the later timestamp and correct status). Delete the stale `tasks/` copy.

This shrinks the D41 gap to: "a crash between atomic-write-to-archive and os.remove-of-original produces a detectable, recoverable inconsistency." The crash window is microseconds. The inconsistency is loud and the fix is mechanical. SQLite avoids this entirely — conceded — but the trade-off is three other capabilities forfeited.

**Position refined:** Added corruption mode #7 (ERR_CORRUPT_DUPLICATE_LOCATION). Documented two-phase archive strategy with explicit crash semantics.

---

## Cycle 2 — ruamel.yaml feasibility for Go-era timestamps

**Critic:** You propose converging to ruamel.yaml-only, but the M3 landscape shows PyYAML's custom `YAML12SafeLoader` was built specifically to handle Go-era 7-digit-nanosecond timestamps as strings. Does ruamel handle this? What breaks when you switch?

**Architect response:** The core issue is YAML timestamp resolution — both PyYAML and ruamel try to auto-resolve ISO-8601-like strings to datetime objects. The current code strips the timestamp resolver on both sides already:
- **Read side (PyYAML):** `YAML12SafeLoader` removes the timestamp resolver at `task_io.py:46-72`.
- **Write side (ruamel):** `_version_implicit_resolver` at `task_io.py:74-89` strips the timestamp resolver.

Converging to ruamel means applying the same resolver-stripping pattern on the read side too. ruamel's API supports this via `YAML(typ='safe')` with constructor overrides. The pattern is identical — strip the timestamp tag so values stay as strings.

For reads: `YAML(typ='safe')` (faster than round-trip, still YAML 1.2 by default). For writes: `YAML(typ='rt')` (preserves key order). One library, two loader configurations, each appropriate for its direction.

**Position confirmed.** ruamel convergence is feasible. The timestamp resolver stripping is a mechanical port of existing logic.

---

## Cycle 3 — Round-trip normalization vs Markdown line breaks

**Critic:** Your normalization rules say "trailing whitespace stripped per line." Markdown uses two trailing spaces to indicate a `<br>` line break. You're silently destroying formatting semantics. Is that acceptable for a system that promises predictable round-trip?

**Architect response:** Excellent catch. This is a real problem. Two trailing spaces in Markdown (`  \n`) produce a hard line break. Stripping them would silently change the rendered output.

**Revised normalization scope:**
- **Structural normalization (applied):** heading format (single space after `#`), inter-section blank-line count (exactly one), trailing newline at EOF, leading blank lines before first content.
- **Content preservation (byte-exact):** everything within a section's `content` field is preserved verbatim — including trailing whitespace on lines, internal blank lines, code block content. The storage layer does not touch section content.

This means the round-trip is "structurally normalized, content-preserved." The parser extracts sections from headings; content between headings is opaque. This is both simpler to implement and safer than content-level normalization.

**Position refined:** Section content is byte-exact. Only structural elements (headings, inter-section spacing, file-level whitespace) are normalized.

---

## Cycle 4 — Proposed DSL extension (section_min_lines)

**Critic:** You propose `section_min_lines: dict[str, int]` as a new predicate DSL key. What pipeline failure does this prevent? `required_sections` ensures the section exists. `require_list_in_section` ensures it has list items. An empty AC section without list items already fails. Who asked for `section_min_lines`?

**Architect response:** Fair. Let me check the real pipeline:

- `required_sections: ["acceptance criteria"]` → catches missing section
- `require_list_in_section: {"acceptance criteria": true}` → catches section with no list items
- `test_section_or_non_impl_tag` → catches missing test section on impl tasks

What gap does `section_min_lines` fill? "Section exists but contains only blank lines or whitespace." But `require_list_in_section` already handles the AC case (the main structural-quality driver). For other sections like "Builder Guidance" — there's no predicate requiring them to have content because the pipeline doesn't gate on it.

**No demonstrated need. YAGNI. Dropped.**

**Position refined:** No new DSL keys in Brief C. The existing D64 keys + structural section parsing fully deliver Outcome 3. Future extensions are discrete decisions per D64's extensibility clause.

---

## Cycle 5 — Performance of ruamel safe-read at scale

**Critic:** ruamel.yaml's safe mode is still ~5-10x slower than PyYAML's C-extension loader. At 150 active tasks (cold boot), that's potentially 150-300ms vs 15ms. Is this acceptable?

**Architect response:** The mtime-keyed cache (`_task_cache`) means cold boot is the only scenario where all 150 files are parsed. After that, only changed files (0-2 per operation typically) are re-parsed.

Cold boot at 300ms is noticeable but acceptable for a CLI/MCP tool that runs on localhost. The engine starts once per MCP session (not per call). `list_tasks` cold-boot latency of 300ms is within acceptable UX for the first call; subsequent calls are cache-hot.

If this becomes a real bottleneck (it hasn't been in 3 months with PyYAML): the read path could use `YAML(typ='base')` (even faster, no resolver at all — all values are strings, let Pydantic coerce types). This is a performance optimization that doesn't change the architecture.

**Position confirmed.** 300ms cold-boot is acceptable. The cache makes steady-state O(1). The fallback to `base` loader exists if needed but is YAGNI today.

---

## Exit Assessment

After 5 cycles:
- Cycle 1 hardened the archive-move atomicity story (real gap, now documented with crash recovery)
- Cycle 2 confirmed ruamel convergence feasibility
- Cycle 3 caught a normalization bug (trailing whitespace = Markdown line breaks)
- Cycle 4 correctly pruned a YAGNI DSL extension
- Cycle 5 confirmed performance acceptability

The position is solid. All challenges either refined the stance (3 changes) or confirmed it (2 confirmations). No fundamental reversals.
