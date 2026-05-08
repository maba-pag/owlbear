# Data Quality Stance — doc-writer quality

## Data Quality Position

The doc-writer's verification failure is a **silent false-positive propagation problem**, not a tooling gap. The agent stamps "verified" on content it never structurally checked (F6: pipeline diagram with "Last verified: 2026-05-05" over stale content). Fixing this requires three things: (1) mechanical detection layers that don't depend on LLM judgment, (2) a TODO marker schema with deterministic identity, and (3) an explicit disposition model where uncertainty is surfaced, never suppressed.

## Schema and Validation Reasoning

### Verification Mechanism: Three layers with decreasing confidence

**Layer 1 — Symbol removal grep (high confidence, mechanical).**
Grep for identifiers referenced in README code blocks and API tables against the package source tree. A missing symbol is definitively stale. A present symbol is inconclusive — it might exist only as an internal implementation detail, not a public contract. This layer is a negative filter: absence proves staleness; presence proves nothing.

Catches the "orchestrator still referenced" class of failures. Cannot catch "symbol exists but was demoted to internal."

**Layer 2 — Signature comparison for task-changed functions (medium confidence, mechanical).**
For functions/classes modified by the current task: extract the function signature from the source file using `ast.parse` (full module file, always parses cleanly). Extract function call patterns from README code blocks using regex or `ast.parse(mode='eval')` where the snippet parses. Compare: function name, parameter count, parameter names.

Scoped to task-changed functions only. Full-surface signature validation is doc-audit scope.

This satisfies the locked brief requirement for structural "signature comparison." Concrete gap it catches: `generate_index(docs)` in README vs. `generate_index(root, index_path)` in source — detected IF the task modified `generate_index`.

**Layer 3 — Evidence-anchored LLM review (lower confidence, required for prose and non-Python surfaces).**
The LLM reads actual code AND README text. Output is a comparison artifact with file:line anchors:

```
| README claim | Code evidence | File:Line | Status |
|---|---|---|---|
| "load_board() returns Board" | def load_board(...) -> dict[str, Any] | engine.py:45 | INACCURATE |
| "COCKPIT_PORT overrides port" | port = int(os.environ.get(...)) | main.py:12 | CONFIRMED |
```

If the LLM cannot provide a file:line anchor for a claim, the claim is `UNVERIFIED`, never `CONFIRMED`. This handles non-Python surfaces (env vars, HTTP routes, shell commands, MCP tool names) that Layers 1–2 cannot cover.

**Honest limitation:** Layer 3 anchors are LLM-generated and could be fabricated. Layers 1–2 provide the hard mechanical floor. Layer 3 is structurally *resistant* to rubber-stamping (the anchor requirement forces engagement), but not structurally *immune*. The overall system is: mechanical confidence where possible, LLM assurance with forcing function where not, explicit uncertainty everywhere else.

### TODO Marker Schema

Format:
```
<!-- TODO(doc-writer): stale — load_board returns dict not Board [#1234] -->
<!-- TODO(doc-audit): missing — browser package API undocumented -->
```

Fields:
- **Source** (required): `doc-writer` | `doc-audit`
- **Category** (required): `stale` | `inaccurate` | `missing` | `unverified`
- **Description** (required): specific, actionable, names the concrete symbol or claim
- **Task reference** (optional): `[#id]` — present for doc-writer, absent for doc-audit

Extraction regex:
```
<!-- TODO\(([\w-]+)\): (stale|inaccurate|missing|unverified) — (.+?)(?:\s*\[#(\d+)\])? -->
```

**Identity and dedup:** Exact-match dedup on `(file_path, category, description_slug)` where slug = lowercase, strip whitespace, first 80 chars. Deterministic — no semantic similarity. If two tasks flag the same issue with different wording, that produces two markers. Doc-audit resolves both by fixing the underlying issue and removing all related markers. Harmless duplication beats lossy dedup.

Known collision risk: two distinct issues in the same file whose descriptions share a prefix could collide. Acceptable at the expected volume (1–3 markers per README per task). If collision becomes a real problem, extend the slug or add a section-heading anchor.

**Lifecycle:** Marker present = open. Marker deleted = resolved. No status field, no state machine. Insertion and deletion only. Orphan detection: doc-audit verifies described issue still exists; removes markers for coincidentally fixed issues.

**Visibility trade-off:** HTML comments are invisible in rendered markdown. This is deliberate: markers are designed for machine consumption (doc-audit parsing) and source-reading developers. If rendered-doc visibility is needed, the format can be changed to admonition blocks — but that is noisier in source and adds a parsing surface. This stance recommends HTML comments; the mediator can override for the enduser concern.

### doc-index: Separate Concern, Prerequisite Migration

Verification is separate from doc-index. doc-index is structural metadata discovery; verification is content comparison. Different data flows, different failure modes.

**Prerequisite:** A README↔code mapping mechanism is needed. The `describes` field does NOT currently exist in READMEs or the `DocEntry` schema. Until it ships, fallback to convention: `serve/{pkg}/README.md` describes `serve/{pkg}/src/**`. This heuristic covers the common case but has known gaps — `pyproject.toml` entry points and `.vscode/mcp.json` config live outside `src/`. The `describes` field migration closes these gaps by allowing explicit cross-path declarations.

Both doc-index and verification consume the same mapping. No second mapping, no divergent scope.

### Classification Taxonomy

| Category | Definition | Detection | Gate scope |
|---|---|---|---|
| **stale** | References removed/renamed symbol, deleted env var, removed route | Grep negative (Layer 1) | Per-task + doc-audit |
| **inaccurate** | Describes existing thing incorrectly — wrong signature, wrong behavior, wrong example | Signature comparison (Layer 2) + anchored LLM (Layer 3) | Per-task for changed code; doc-audit for unchanged |
| **missing** | Public API, env var, route, or tool not documented | Export/config diff vs. doc coverage | Primarily doc-audit |
| **unverified** | Section read but gate could not produce structural evidence | Layer 3 unable to anchor claims to code | Per-task gate marks these honestly |

"Public surface" includes: Python exports (`__init__.py`, `__all__`), entry points (`pyproject.toml`), env vars (grepped from source), HTTP routes (FastAPI decorators), MCP tool names (registration calls), CLI commands. Extraction rules vary by surface type — the tool must handle multiple registration patterns (decorator form, reassignment form, etc.).

### Per-Task Gate: Dispositions and Consequences

Every claim in a touched README gets one disposition. Section-level disposition = worst-case claim within that section.

| Disposition | Meaning | Evidence |
|---|---|---|
| **VERIFIED** | Mechanical check + LLM evidence with file anchors | Grep pass + comparison row |
| **FIXED** | Issue found and corrected inline | Diff + evidence |
| **FLAGGED** | Pre-existing issue marked with TODO | Marker text + category |
| **UNVERIFIED** | Could not structurally confirm | Statement of what couldn't be checked |

**Gate blocking rules:**
- UNVERIFIED on pre-existing content: passes gate (pre-existing, not this task's fault)
- UNVERIFIED on content the current task introduced or modified: blocks gate — task-authored claims must be verifiable or the doc-writer must fix them before passing
- Heavily UNVERIFIED README: passes gate but doc-audit priority increases

This distinction prevents UNVERIFIED from becoming an escape hatch for task-introduced inaccuracies while avoiding blocking tasks for pre-existing rot.

## Key Trade-offs

1. **Grep catches removal only, not demotion.** A symbol that was public and became internal still passes grep. Accepted: demotion detection requires API surface tracking, which is doc-audit scope.
2. **Layer 2 is task-scoped.** Pre-existing signature drift in untouched functions is invisible. Accepted: per-task gate checks what the task touched; doc-audit handles the full surface.
3. **Layer 3 is LLM-dependent.** Anchored evidence is more reviewable than pass/fail but not independently verifiable. Accepted: this is the honest limitation of prose verification.
4. **TODO markers are invisible in rendered docs.** Source-reading developers see them; GitHub/rendered-doc readers don't. Accepted for machine-parseability; mediator can override.
5. **Convention-based mapping has gaps.** `serve/{pkg}/src/**` misses `pyproject.toml`, `.vscode/mcp.json`. Accepted as temporary until `describes` field ships.

## Warnings

- **Do not claim "structurally impossible" false positives.** Layer 3 can still produce fabricated anchors. The system is structurally resistant, not immune. Layers 1–2 are the hard floor.
- **The `describes` field migration is load-bearing.** Without it, the convention-based mapping silently excludes non-`src/` contract surfaces. This prerequisite should ship early.
- **Layer precedence must be defined.** When Layer 1 says "symbol exists" and Layer 3 says "description is wrong," Layer 3 wins (Layer 1 only proves existence, not accuracy). When Layer 2 says "signature matches" and Layer 3 says "behavior description is wrong," both findings are valid (different surfaces). The implementation must define rollup rules.
- **Non-Python surfaces rely entirely on Layer 3.** Env vars, HTTP routes, MCP tools have no mechanical extractor in this design. If Layer 3 quality is poor, these surfaces are effectively unverified. Consider adding mechanical extractors (grep for `os.environ`, regex for FastAPI decorators) as future hardening.
- **Section boundary definition is absent.** "Every section of a touched README" requires defining what a section is (heading level, table, code block). The implementation must pin this down.

## Confidence

**0.75**

High confidence in: Layer 1 removal grep, TODO marker schema, 4-category taxonomy, disposition model with gate-blocking distinction.

Medium confidence in: Layer 2 signature comparison scope (task-changed only may be too narrow for badly drifted docs), Layer 3 anchor-forcing effectiveness, convention-based mapping coverage.

Low confidence in: non-Python surface verification without mechanical extractors, section boundary definition completeness.
