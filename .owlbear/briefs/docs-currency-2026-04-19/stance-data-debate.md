# Data Panelist — Critic Debate Log

Brief: `draft-docs-currency-2026-04-19`
Panelist: **The Modeler** (ideation-data)
Cycles completed: 5

---

## Cycle 1

### Initial Position

1. **Doc-index integrity:** Allowlist-based path patterns (not exclusion globs). The doc surface is structurally stable (~76 files across `share/agents/`, `share/skills/`, `share/instructions/`, `share/prompts/`, `serve/*/README.md`, `setup/`, root `*.md`, `.github/`). Exclusion lists fail open — new working directories get auto-included as product docs. Allowlist fails closed — safer. Index is a pure function of filesystem state, regenerated on demand, never cached, never hand-edited.
2. **Diagram drift:** Per-diagram `describes` field in the index, listing the paths/concepts the diagram covers. Without it, `doc-audit` can only confirm file existence, not semantic accuracy.
3. **Deletion integrity:** Multi-step transaction — propose (with blast-radius: inbound link scan) → user approval → delete + fix inbound links → single atomic commit.
4. **Cross-references:** Index captures outbound links per file (regex extraction). Inbound is computed by reversal.
5. **Drift detection:** Semantic drift lives in `doc-audit` D4, not the index. LLM-based spot-checking of claims against code. Index provides the coverage map.
6. **Verification log:** Permanent one-time artifact in `.owlbear/`, markdown format.

### Critic Challenge 1

**On allowlist extensibility:** "Your allowlist fails on extensibility. New doc-bearing directories (say `share/templates/*.md`) are silently excluded — index doesn't see them, doc-writer ignores them, doc-audit doesn't audit them. This is worse than exclusion-list failure: excluding real docs is invisible. At least exclusion lists fail open (including non-docs is noisy but visible)."

**On diagram `describes` field:** "This violates the 'auto-generated, no hand-maintained data fields' constraint. You call it 'source data not index data' but the constraint doesn't distinguish."

**On cross-reference regex:** "Your `\[.*?\]\((.*?)\)` matches image embeds, external URLs, anchor links — not just doc cross-references. Signal-to-noise may be terrible."

### Response 1

**Allowlist extensibility:** Fair point on silent exclusion. Refined: allowlist with a validation step — `doc-audit` separately runs an "unrecognized .md files" check. Any `.md` file outside the allowlist that isn't in a known-excluded working directory gets flagged. This converts "fail closed silently" to "fail closed loudly." The regen script still uses the allowlist; the safety net is in doc-audit.

**Diagram `describes`:** Accepted tension. This metadata genuinely cannot be auto-derived. Two options: (a) accept as a controlled exception, documented; (b) drop diagram drift detection from index, make it pure human/LLM judgment. I choose (a) — the `describes` field is authored once at diagram creation by the agent creating the diagram. It's analogous to a filename: chosen once, not maintained. The constraint targets the index (auto-generated); this is source metadata.

**Cross-reference regex:** Accepted. Refined: filter extracted links to workspace-relative paths only (exclude `http://`, `#anchor-only`, image extensions like `.png/.svg`). Extraction is candidates; a filter pass retains only internal doc cross-references.

---

## Cycle 2

### Refined Position

1. Allowlist-based with noisy unknown-file detection via `doc-audit` (not in the regen script).
2. Diagram `describes` as a controlled exception — authored at creation, immutable.
3. Deletion unchanged.
4. Outbound link extraction with workspace-relative-path filter.
5. Drift detection unchanged.
6. Verification log unchanged.

### Critic Challenge 2

**On noisy detection complexity:** "You're building a validator for the validator. If the allowlist is a config-driven glob pattern set in one place, a simple `find . -name '*.md' | diff against allowlist matches` at audit time is sufficient. Don't couple the regen script and the validation."

**On deletion atomicity:** "You say 'atomic commit' but a deletion fixing inbound links across 5 files is potentially large. What's the approval granularity? Per-file? Per-batch?"

### Response 2

**Detection complexity:** Partially accepted. The "find + diff" approach at audit time is sufficient — it doesn't need to be in the regen script. Simplified: regen script uses allowlist → produces index. `doc-audit` separately checks for unrecognized files. Two concerns, two tools, no coupling.

**Deletion granularity:** Per-proposal, not per-file. Each proposal is one doc + its blast radius (list of files with inbound links). User sees the full impact and approves or rejects the unit. If blast radius is large, user can reject and scope down. One logical commit per approved deletion.

---

## Cycle 3

### Refined Position

1. Allowlist (config-driven globs), `doc-audit` separately checks unrecognized `.md`.
2. Diagram `describes` as controlled exception.
3. Per-proposal deletion approval (one doc + blast radius), single logical commit.
4. Outbound internal links per file in index, inbound computed by reversal.
5. Semantic drift in doc-audit D4, LLM-based, index as coverage map.
6. Verification log: permanent artifact in `.owlbear/`.

### Critic Challenge 3

**On content sensitivity:** "You say the index is a 'pure function of filesystem state' but it includes outbound links extracted from file contents. That makes it content-sensitive. If content changes (adding a link) but path/headings don't, the index is stale. Your regen cadence must account for content changes, not just file existence."

**On format:** "The context says 'md / yaml / json — planner's call' but from data integrity: YAML and JSON are machine-parseable; markdown tables are not reliably. If doc-writer and doc-audit query the index programmatically, markdown is unsuitable."

### Response 3

**Content sensitivity:** Critical point. Accepted. The index IS content-sensitive (headings + outbound links), not just path-sensitive. Regeneration must scan file contents. Cost: reading ~76 markdown files, extracting headings and links — sub-second in Python. Cheap enough to regenerate on every doc-writer / doc-audit invocation. No caching needed; always fresh.

**Format:** Strong data integrity position: the index must be machine-parseable. YAML or JSON, not markdown. `doc-writer` and `doc-audit` need programmatic queries (find files linking to X, list files in a pattern, get TOC for file Y). Markdown tables require fragile regex parsing — that's exactly the kind of implicit schema assumption I exist to reject. Recommending YAML (human-readable + machine-parseable). This is a data integrity constraint, not an implementation detail I'm overstepping on.

---

## Cycle 4

### Refined Position

1. Allowlist (config in `.owlbear/doc-index.config.yaml`), content-sensitive (headings + outbound links), regenerated on every invocation, YAML format.
2. Diagram `describes` as controlled exception, authored at creation.
3. Per-proposal deletion with blast-radius from cross-reference data.
4. Outbound internal links per file, inbound computed.
5. Semantic drift in doc-audit D4, LLM-based.
6. Verification log: permanent YAML artifact with reproducible evidence.
7. Unrecognized-file detection: doc-audit concern, not index concern.

### Critic Challenge 4

**On format recommendation scope:** "You're making a format recommendation that M2 explicitly delegated to the planner. Is this overstepping?"

**On allowlist config placement:** "Where does the config live? In the script (code), in a config file (another artifact), or hardcoded (inflexible)?"

**On verification log trustworthiness:** "If doc-writer v2 runs 6 test cases and writes 'pass' for all, how does anyone verify later? Is the log self-certifying (worthless) or does it contain reproducible evidence?"

### Response 4

**Format scope:** Not overstepping. "Must be machine-parseable" is a data integrity constraint. Whether it's YAML or JSON is implementation — I defer that. But "not markdown for programmatic consumption" is squarely my lane.

**Config placement:** `.owlbear/doc-index.config.yaml` — single source of truth for "what counts as a product doc." Inspectable, diffable, version-controlled. Changes only when project doc structure changes (rare). Alternative (hardcoded in script) couples doc-surface definition to code — bad separation.

**Verification log:** Strong point. Self-certifying is worthless. The log must contain: task ID used as input, behavioral mode tested, observable output (commit SHA, Channel A message, or explicit no-op with reasoning), enough context to reproduce ("run doc-writer on task X, expect behavior Y"). This makes the log verifiable — anyone can re-run and check. Not proof, but reproducible evidence.

---

## Cycle 5

### Position (near-final)

All seven items from Cycle 4, plus verification log refinement (reproducible evidence, not self-certification).

### Critic Challenge 5

**On link extraction in code blocks:** "What about links inside fenced code blocks? Those are examples, not live cross-references. Your extraction will produce false positives unless it skips fenced regions."

### Response 5

Accepted. Link extraction must operate on non-code-block markdown only. Skip fenced code blocks (``` delimited regions). Straightforward parser concern — adds to the extraction specification.

### Exit

Position is solid after 5 cycles. The Critic loop refined:

- Allowlist → allowlist with noisy detection via doc-audit (not coupled to regen)
- Diagram metadata → controlled exception with explicit acknowledgment
- Index format → machine-parseable constraint (not markdown)
- Link extraction → workspace-relative filter + skip fenced code blocks
- Verification log → reproducible evidence requirement
- Content sensitivity → acknowledged, regen is cheap, always-fresh model
- Config placement → dedicated config file, separation of concerns
