# Architectural Stance — doc-writer Quality Redesign

## Architectural Stance

The doc-writer's failure is structural, not behavioral: it asks "did this diff break docs?" when it should ask "are the docs for this package correct?" The fix is a three-part redesign: (1) convention-based README mapping so the agent reliably finds what to read, (2) dual-layer verification so checking has both mechanical and editorial teeth, and (3) TODO markers as a handoff mechanism to doc-audit so pre-existing rot is tracked without polluting commit attribution or flooding the kanban board.

## Structural Reasoning

### 1. Checklist Restructure: 4 Items

Remove diagram items (old 5–6) and module docstrings (old 2). Renumber to 4 items:

| # | Item | What Changed |
|---|------|-------------|
| 1 | **README Verification** | Replaces old item 1. Convention-mapped full-file read + dual-layer verification + inline fix for task-caused issues + TODO markers for pre-existing issues. This is the core behavioral change. |
| 2 | **External Attribution** | Unchanged. Check `.owlbear/sources/overview.md` for new external patterns. |
| 3 | **Research Doc** | Unchanged. Verify `.owlbear/research/{slug}.md` exists and is linked. |
| 4 | **Deletion Detection** | Renumbered from old item 7. Same child-task + DR protocol. |

**Why cut docstrings:** The decisions document explicitly cut module docstrings — ruff D100 handles this mechanically. Ruff D100 is currently in the ignore list (`pyproject.toml` line 57: `"D1"`) so a follow-up task must enable it. That's a config change, not a doc-writer design concern. Until D100 is enabled, there is a known gap — but re-inserting it into the doc-writer checklist would reopen a locked decision and mix two different quality mechanisms.

**Gating logic:** The no-impact fast path remains — if all changed files are OUT-scope or map to no READMEs, write "no docs impact" with evidence and advance. But the threshold for triggering a full read is now lower: any change under `serve/{pkg}/src/` triggers `serve/{pkg}/README.md` reading. This is the intended behavioral shift from the 90% no-op rate toward honest verification.

### 2. Convention-Based README Mapping

Directory structure provides the code→README mapping. No `describes` metadata needed for READMEs.

| Code Path Pattern | Mapped Documentation |
|-------------------|---------------------|
| `serve/{pkg}/src/**` | `serve/{pkg}/README.md` |
| `serve/{pkg}/pyproject.toml`, `serve/{pkg}/tests/**` | `serve/{pkg}/README.md` (config/dependency sections) |
| `setup/**` | `setup/setup-guide.md`, `setup/sharing-guide.md` |
| `share/**` | `share/README.md`, `share/WIRING.md` |
| Any package's public interface changes (entry points, CLI, config) | `README.md`, `README-consumer.md` |
| Security-relevant changes | `SECURITY.md` (LLM judgment) |
| Cross-package tasks | All mapped READMEs for all touched packages |

**Why no metadata:** READMEs sit next to their code — the relationship is derivable from directory structure. Diagrams needed `describes` fields because `.excalidraw` files don't have an obvious spatial relationship to their subjects. Adding `describes` to READMEs would pollute human-readable files with agent metadata and create a maintenance burden for a mapping that's 100% inferrable.

**Root-doc trigger rule:** Root docs (`README.md`, `README-consumer.md`) contain package-level summaries (Cockpit launch commands, MCP inventory, etc.). These are triggered when a task changes a package's **public interface** — entry points, CLI commands, configuration, or external API. Interior implementation changes don't affect root docs. This is LLM judgment, bounded by the trigger definition.

**Authority rule for overlapping content:** When both a package README and a root doc describe the same behavior, the package README is authoritative for implementation details. Root docs link to package READMEs for depth. This aligns with DRY.

### 3. Dual-Layer Verification

Structural verification is embedded as procedural steps in the skill text. No separate tool.

**Layer 1 — Mechanical (grep-based):**
1. Extract removed/renamed symbols from the git diff (`git diff --name-status`, function/class names, CLI commands)
2. Grep the target README for those symbols
3. If found: fix inline (task-caused removal/rename)

This catches stale references to things that no longer exist. It does NOT catch signature drift (when a function survives but its parameters change).

**Layer 2 — Editorial (LLM judgment):**
1. Read the full README
2. Read the current source files for the package
3. Compare: are code blocks accurate? Are described behaviors still correct? Are new public APIs missing from the docs?
4. For task-caused inaccuracies: fix inline
5. For pre-existing inaccuracies: insert TODO marker

Layer 2 catches what Layer 1 cannot: signature drift, missing coverage of new features, inaccurate prose descriptions, stale examples. Layer 1 catches what Layer 2 might miss: mechanical symbol removal that an LLM might gloss over.

**Why not AST-based signature comparison:** Research Q2 flags the practical concerns — runtime dependency, failure modes, and complexity. The LLM editorial layer handles signature drift naturally during full-file reading (it sees both the README code blocks and the current source). A mechanical signature tool would add engineering cost for marginal improvement over what Layer 2 already provides.

### 4. doc-writer / doc-audit Boundary

| Dimension | doc-writer (per-task gate) | doc-audit (periodic sweep) |
|-----------|--------------------------|---------------------------|
| Trigger | Every task in `docs` stage | Manual user invocation |
| Scope | Convention-mapped READMEs only (1–3 files per task) | Full documentation surface |
| Fix scope | Task-caused issues only (inline) | All issues including pre-existing |
| Pre-existing issues | TODO markers inserted | TODO markers resolved + independent findings |
| Diagrams | None (removed from scope) | Full diagram responsibility — creation, content verification, footer maintenance |
| Cross-references | Not checked | Full cross-reference audit |
| Speed | Fast — bounded by mapped README count | Thorough — can be slow |
| Pipeline role | Gate (blocks `docs` → `done`) | Sweep (no pipeline position) |

**Handoff mechanism:** TODO markers. doc-writer inserts them; doc-audit resolves them. This prevents kanban board flooding while ensuring nothing is lost.

**doc-audit constraint:** The current doc-audit prompt uses one-finding-at-a-time interactive remediation. With TODO markers as a new input source, doc-audit needs a batch-resolution dimension — process all TODO markers for a file in a single pass, then present findings. The doc-audit prompt revision is part of this brief's deliverables.

**Sync-to-main constraint:** TODO markers must be resolved before `sync-to-main` runs. Either doc-audit clears them, or a pre-sync validation step checks for unresolved markers. This prevents hidden warnings from leaking to the consumer-facing main branch.

### 5. TODO Marker Convention

**Format:**
```
<!-- TODO(doc-writer): {description} | found={date} | task=#{id} -->
```

**Fields:**
- `TODO(doc-writer)` — namespace prevents collision with other TODO conventions (code TODOs, IDE markers)
- `{description}` — human-readable issue description, actionable by doc-audit
- `found={date}` — ISO date of insertion, enables staleness tracking
- `task=#{id}` — which pipeline task was being processed when the issue was found (audit trail)

**Properties:**
- Pipe-delimited for simple regex parsing
- HTML comment: invisible in rendered Markdown, visible in editor source view
- Machine-parseable: `grep -rn 'TODO(doc-writer)' serve/*/README.md` finds all markers
- doc-audit extracts structured fields with regex: `<!-- TODO\(doc-writer\): (.+?) \| found=(\S+) \| task=#(\d+) -->`

**Why HTML comments, not visible markers:** Pre-existing issues are maintenance state, not reader-facing content. Consumers on the main branch should see clean docs. If a marker leaks through sync-to-main (which the sync constraint above prevents), invisible is safer than a visible `⚠️ STALE:` prefix cluttering the rendered doc.

### 6. Attribution Heuristic

When the doc-writer reads a full README and finds issues, it classifies each as task-caused or pre-existing:

1. Build the **task change set**: symbols, paths, and behaviors added, removed, or renamed in the git diff
2. Read the README in full
3. README content that references items in the task change set → **task-caused** → fix inline
4. README content that is wrong but does NOT reference the task change set → **pre-existing** → TODO marker

This heuristic is imperfect — some pre-existing issues may coincidentally reference symbols that the task also touched. In ambiguous cases, the doc-writer errs toward TODO markers (pre-existing), preserving clean commit attribution per Option C.

## Key Trade-offs

| Trade-off | Chosen Side | Cost |
|-----------|-------------|------|
| Speed vs. thoroughness | Thoroughness (full-file read) | Higher per-task latency; no-op rate drops from ~90% to estimated ~40–50% |
| Mechanical vs. editorial verification | Both (dual-layer) | Complexity in the skill text; two verification steps per README |
| Task-fix vs. pre-existing-fix | Strict separation (Option C) | Some pre-existing issues that overlap with task symbols get TODO-marked instead of fixed |
| Visible vs. invisible TODO markers | Invisible (HTML comments) | Requires sync-to-main enforcement; developers must view source to see markers |
| Docstrings in doc-writer vs. ruff | Ruff (respecting locked cut) | Known gap until D100 is enabled; requires follow-up task |
| AST signature comparison vs. LLM editorial | LLM editorial | No mechanical guarantee on signature drift; depends on LLM quality |

## Warnings

1. **Ruff D100 gap is real.** Until the follow-up task enables D100 rules, no automated system checks docstrings. The brief deliverables must include this task.

2. **TODO marker accumulation risk.** If doc-audit runs infrequently, markers accumulate faster than they're resolved. The doc-audit redesign must include batch resolution and the brief should recommend an audit cadence.

3. **Root-doc trigger is still LLM judgment.** The "public interface" trigger for root docs is a judgment call, not a convention. Some root-doc drift will be missed when the doc-writer doesn't recognize an interior change as interface-affecting. This is acceptable — doc-audit catches the remainder.

4. **Layer 2 quality depends on the model.** LLM editorial verification is only as good as the model's ability to compare prose against code. This is the same dependency the current system has, but now it's load-bearing rather than decorative.

## Confidence

**0.80**

The position is structurally coherent after two Critic cycles. The main residual risks are operational (TODO accumulation, ruff D100 gap, root-doc trigger fidelity) rather than architectural. The dual-layer verification approach, convention-based mapping, and clean doc-writer/doc-audit boundary are sound structural choices that directly address the diagnosed root cause.
