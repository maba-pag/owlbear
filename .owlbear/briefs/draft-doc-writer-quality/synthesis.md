# Synthesis — doc-writer Quality Redesign

## Summary

Three stances converge strongly on diagnosis, boundary design, and the core behavioral shift. The doc-writer must read full READMEs (not just diff-adjacent sections), fix task-caused issues inline, and flag pre-existing rot via TODO markers. Diagrams and docstrings are removed from doc-writer scope. A doc-audit sweep handles the remainder. Disagreements concentrate on three surfaces: TODO marker visibility, mechanical signature comparison (Layer 2), and marker schema complexity.

## Convergences

### Root cause and behavioral shift

All three stances agree the current failure is structural: the doc-writer asks "did this diff break docs?" when it should ask "are the docs for this package correct?" The fix is full-file reading of convention-mapped READMEs when a task touches a package. (architect L5–7, data L3–5, enduser L3–4)

### Checklist reduction to 4 items

All agree on removing diagram items and module docstrings from the doc-writer checklist. Diagrams move to doc-audit; docstrings are deferred to ruff D100. The remaining items are: README verification, external attribution, research doc check, deletion detection. (architect §1, data §Classification Taxonomy implicitly, enduser §Diagram deprioritization)

### Convention-based README mapping

All agree `serve/{pkg}/src/**` maps to `serve/{pkg}/README.md` by directory convention. No `describes` metadata needed for READMEs (though data flags gaps for non-`src/` contract surfaces). (architect §2, data §doc-index, enduser implicit)

### Option C: task-scoped fix + pre-existing flagging

All agree on the locked decision: fix task-caused issues inline, mark pre-existing issues with TODO markers. This preserves commit attribution while surfacing rot. (architect §6, data §Per-Task Gate, enduser §What the reader actually experiences)

### Dual-layer verification minimum

All agree on at least two verification layers: (1) grep-based removal detection (mechanical, high confidence) and (2) LLM editorial review (required for prose, lower confidence). Layer 1 catches stale symbol references; Layer 2/3 catches signature drift, missing coverage, and inaccurate descriptions. (architect §3, data §Verification Mechanism, enduser §What I recommend instead)

### doc-writer / doc-audit boundary

All agree on the boundary: doc-writer is a per-task gate (1–3 READMEs, fast, task-scoped fixes); doc-audit is a periodic sweep (full corpus, resolves TODO markers, owns diagrams, cross-references). TODO markers are the handoff mechanism. (architect §4, data §Classification Taxonomy gate scope, enduser §Trade-offs)

### doc-audit cadence is underspecified

All three flag that doc-audit frequency is not locked and that marker accumulation is a real risk if audit discipline is weak. (architect Warning 2, data Warning regarding `describes` migration cadence, enduser Warning 3)

## Disagreements

### 1. TODO marker visibility

- **architect** (L136–139) and **data** (L73–75): HTML comments only. Rationale: markers are for machine consumption and source-reading developers; rendered-doc noise at scale creates its own trust failure.
- **enduser** (L9–14, §What I recommend instead): Disagrees. HTML-only markers leave rendered-doc readers with no warning. Recommends **visible inline warnings for mechanically-confirmed removals only** (grep-verified symbol absence), keeping everything else as HTML comments. This avoids LLM severity classification while alerting readers to the highest-confidence class of stale information.

The enduser also flags that the locked outcome's claim "visible to humans reading the doc" is inaccurate for rendered markdown — it is only true for raw source readers. (enduser Warning 1)

### 2. Layer 2: AST-based signature comparison

- **architect** (L95–98): Skip it. LLM editorial (Layer 3) handles signature drift naturally during full-file reading. AST tooling adds engineering cost for marginal improvement.
- **data** (L19–28): Include it, scoped to task-changed functions only. Uses `ast.parse` on full module files. Catches concrete gaps like `generate_index(docs)` vs. `generate_index(root, index_path)`. Considers this the structural satisfaction of the locked "signature comparison" requirement.
- **enduser**: Does not take a position on this specific mechanism.

### 3. TODO marker schema complexity

- **architect** (L113–127): Pipe-delimited format with three fields: description, found-date, task-ID. Namespace `TODO(doc-writer)` prevents collision.
- **data** (L48–68): Adds a required **category** field (`stale | inaccurate | missing | unverified`) with defined extraction regex. Identity/dedup based on `(file_path, category, description_slug)`. Separate `TODO(doc-audit)` namespace for audit-originated markers.
- **enduser**: Does not take a position on schema details.

### 4. Gate blocking rules for UNVERIFIED content

- **data** (§Per-Task Gate): Defines explicit disposition model — UNVERIFIED on pre-existing content passes the gate; UNVERIFIED on task-introduced content blocks the gate. Task-authored claims must be verifiable.
- **architect** and **enduser**: Do not define this distinction. The architect's model implicitly allows all pre-existing issues to pass (via TODO markers) but does not address the case where the task itself introduces unverifiable claims.

### 5. `describes` field migration as prerequisite

- **data** (§doc-index): Treats the `describes` field migration as load-bearing. Convention-based mapping silently excludes non-`src/` contract surfaces (`pyproject.toml` entry points, `.vscode/mcp.json`). Recommends shipping the migration early.
- **architect** (L63–67): Explicitly rejects `describes` metadata for READMEs. Directory convention is 100% inferrable; metadata would pollute human-readable files for a mapping that's derivable.
- **enduser**: Does not address this.

## Recommendation

The three stances converge on all major structural decisions: full-file reading, convention-based mapping, Option C attribution, dual-layer verification, diagram removal, and the doc-writer/doc-audit boundary. These convergences are strong enough to proceed to brief drafting.

Three items need mediator resolution before the brief can lock:

1. **TODO marker visibility**: The enduser's narrow proposal (visible warnings for grep-confirmed removals only, HTML for everything else) is a targeted compromise that both architect and data positions could accommodate — it adds no LLM judgment dependency and affects only the highest-confidence failure class.

2. **Layer 2 inclusion**: The data stance's task-scoped `ast.parse` proposal is concrete and bounded. The architect's objection is cost-based, not correctness-based. This is a scope/investment decision.

3. **Marker schema**: The data stance's category field adds classification structure that supports the disposition model and doc-audit batch processing. The architect's simpler format is sufficient for basic grep workflows. This is a complexity/utility trade-off.

**Confidence: 0.82** — High structural convergence on the core design. Residual disagreements are scoped to mechanism details, not architecture.

## Open Questions

1. **Doc-audit cadence**: All stances flag this as underspecified. What triggers a doc-audit run — task count threshold, time interval, sync-to-main pre-check, or manual-only?
2. **Sync-to-main enforcement**: Architect proposes a pre-sync validation for unresolved TODO markers. Is this a hard gate (block sync) or a warning?
3. **Non-Python surface verification**: Data warns that env vars, HTTP routes, and MCP tool names rely entirely on LLM editorial (Layer 3) with no mechanical extractor. Is this acceptable for v1, or should grep-based extractors (FastAPI decorators, `os.environ`) be included?
4. **Ruff D100 follow-up task**: Architect flags this as a deliverable of the brief. Is it in-scope or a separate backlog item?
5. **Section boundary definition**: Data flags that "every section of a touched README" requires defining what constitutes a section. How is this pinned — heading level, or something else?
