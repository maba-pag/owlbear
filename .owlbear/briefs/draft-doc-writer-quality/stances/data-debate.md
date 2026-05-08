# Data Quality Debate Log — doc-writer quality

## Round 1

### Draft Position

Layered grep + scoped LLM for verification. `ast.parse` rejected as overkill. TODO markers with `<!-- TODO(doc-writer): [category] — description — #task_id -->`. doc-index should not parse code blocks. Three-category taxonomy (stale/inaccurate/missing). Gate is a filter, not a certifier.

### Critic Challenges (5 critical, 2 moderate)

1. **Critical — Grep confuses lexical presence with validity.** String existing "anywhere in the tree" doesn't mean the reference is valid. Internal aliases survive after public API removal.
2. **Critical — LLM backstop reuses the rubber-stamp failure mode.** The current agent already has the instruction to verify and still stamps bad content. Using "LLM editorial judgment" as the safety net is the same broken mechanism.
3. **Critical — TODO schema has provenance contradiction.** Hard-requires `#task_id` but doc-audit findings have no triggering task. "File path + line number" isn't a real natural key (line numbers shift, regex doesn't encode them).
4. **Critical — Taxonomy omits verification-integrity failure.** The core pathology (false "Last verified" stamps) isn't stale, inaccurate, or missing — it's false attestation. Taxonomy doesn't cover the corruption path most targeted.
5. **Critical — "Filter not certifier" is bar-lowering in nicer language.** Tasks still pass while wrong docs survive.
6. **Moderate — Two parsers for same README creates silent divergence risk.**
7. **Moderate — AST rejection premise is technically wrong.** `ast.parse` doesn't require importing — it parses source text.

### Revisions Applied

- Grep scoped to public API surface (`__init__.py` exports), not "any file"
- LLM backstop replaced with evidence-producing comparison table (not pass/fail stamp)
- TODO schema: task ID made optional, lifecycle semantics added
- Fourth category `unverified` added for verification-integrity failures
- Gate produces per-section dispositions, never implicit pass
- AST premise corrected

## Round 2

### Critic Challenges (4 critical, 2 moderate)

1. **Critical — `describes` contract assumed but doesn't exist.** Doc-index `DocEntry` has no `describes` field. No README has `describes:` metadata. The mapping gap is moved to a prerequisite, not solved.
2. **Critical — "Public surface" = `__init__.py` exports is too narrow.** Cockpit README documents env vars and HTTP routes; `__init__.py` exports nothing. MCP server names defined in `.vscode/mcp.json`, not in package source. Knowledge README documents submodule imports not in root `__all__`.
3. **Critical — Layer 2 retreats from locked brief requirement.** Brief explicitly calls for "signature comparison." Stance says "NOT full signature comparison." Real example: `generate_index(docs)` in README vs `generate_index(root, index_path)` in source — all names exist, docs still wrong.
4. **Critical — LLM evidence table is still ungrounded narrative.** No file anchors, no reproducible extraction points. A three-column table from the same model is more reviewable but still ungrounded.
5. **Moderate — HTML comment visibility contradiction.** Brief says markers "visible to humans reading the doc" — false for rendered markdown.
6. **Moderate — "Natural key" uses similarity matching, not deterministic identity.** Dedup depends on semantic judgment, not stable state.

### Revisions Applied

- `describes` migration acknowledged as prerequisite with convention-based fallback
- Public surface broadened: env vars, HTTP routes, MCP tool names, entry points, CLI commands
- Layer 2 restored: signature comparison for task-changed functions using `ast.parse` on source files
- Layer 3 evidence anchored with file:line references
- Dedup changed to deterministic slug matching (no similarity)
- Visibility trade-off acknowledged explicitly

## Round 3

### Critic Challenges (3 critical, 3 moderate)

1. **Critical — Scope fallback contradicts broadened surface.** Convention mapping (`serve/{pkg}/src/**`) excludes `pyproject.toml` entry points and `.vscode/mcp.json` that the taxonomy claims are in scope.
2. **Critical — "Structurally impossible" overclaim.** Layer 3 anchors "could be fabricated" contradicts "false positives become structurally impossible." Both can't be true.
3. **Critical — UNVERIFIED as escape hatch.** UNVERIFIED passes gate. Task-introduced claims that can't be verified are still task risk, but the disposition allows them through.
4. **Moderate — Claim-to-section rollup undefined.** Layer 3 produces claim-level rows; gate works at section level. Mixed results within a section have no rollup rule.
5. **Moderate — Heterogeneous extractor contracts.** MCP tool registration appears in decorator form and reassignment form — no pinned extraction rule.
6. **Moderate — Marker identity still lossy.** 80-char slug with no section anchor can collide on similar descriptions.

### Revisions Applied

- Fallback mapping gaps acknowledged explicitly; `describes` migration named as prerequisite
- "Structurally impossible" → "structurally resistant" — honest about Layer 3 limitations
- UNVERIFIED split: pre-existing content passes gate; task-introduced content blocks gate
- Section rollup defined: worst-case claim disposition = section disposition
- Collision risk acknowledged as acceptable at expected volume
- Extraction rule variation acknowledged; named as implementation detail

### Remaining Blind Spots (acknowledged in final stance)

- Section boundary definition absent (what heading level counts as a "section")
- Layer precedence rules not fully specified
- Non-Python surfaces rely entirely on Layer 3 with no mechanical fallback
- Doc-audit cadence not specified (though that's outside data quality scope)

## Confidence Trajectory

| Round | Critic Confidence | Pressure |
|---|---|---|
| 1 | 0.31 | high |
| 2 | 0.38 | high |
| 3 | 0.41 | high |
| Final stance | 0.75 (self-assessed) | — |

The gap between Critic confidence (0.41 at round 3) and final self-assessment (0.75) reflects that the remaining Critic challenges are increasingly implementational (section boundaries, extractor patterns, rollup edge cases) rather than architectural. The core mechanisms — layered verification, TODO schema, 4-category taxonomy, disposition model — are stable after three rounds.
