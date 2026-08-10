# Brief — Doc-Writer Quality Redesign

## Scope

Rewrite `w-doc-update` skill and revise `doc-audit.prompt.md` to make the `docs` pipeline stage produce honest, useful documentation updates instead of verification theater.

## Problem

The doc-writer asks "did this task's diff break any docs?" — almost always "no" because most tasks touch few lines, the README was already wrong before the task ran, and the checklist doesn't ask "is the doc correct overall?" Result: 90% no-op rate by design, stale READMEs never caught, diagrams get timestamp stamps without content verification.

**Root cause:** Task-scoped diff checking will never fix pre-existing rot. The doc-writer lacks (1) a systematic mapping from code files to READMEs, (2) full-file reading of documentation content, and (3) structured forcing to prevent rubber-stamping.

## Outcomes

1. **Per-task honest verification.** Doc-writer reads the entire relevant README when a task touches a package. Grep-based structural checks for removed symbols + LLM editorial for prose accuracy. Fixes task-caused issues inline. Marks pre-existing issues with visible TODO markers.
2. **No diagram responsibility.** Doc-writer no longer touches `.excalidraw` files. All diagram work moves to doc-audit.
3. **Doc-audit as deep sweep.** Revised prompt handles TODO marker resolution in batch, full diagram responsibility, and cross-reference checking.

### Out of scope

- Module docstrings (ruff D100 — separate backlog item)
- AST-based signature comparison
- Automated audit cadence

## Design

### Convention-Based README Mapping

| Code Path Pattern | Mapped Documentation |
|-------------------|---------------------|
| `serve/{pkg}/src/**` | `serve/{pkg}/README.md` |
| `serve/{pkg}/pyproject.toml`, `serve/{pkg}/tests/**` | `serve/{pkg}/README.md` |
| `setup/**` | `setup/setup-guide.md`, `setup/sharing-guide.md` |
| `share/**` | `share/README.md`, `share/WIRING.md` |
| Any package's public interface changes | `README.md`, `README-consumer.md` (LLM judgment) |

No metadata needed — directory structure provides the mapping.

### 4-Item Checklist

| # | Item | Behavior |
|---|------|----------|
| 1 | README Verification | Convention-mapped full-file read. Grep for removed symbols (Layer 1). LLM reads full README + source, compares claims (Layer 2). Task-caused: fix inline. Pre-existing: TODO marker. |
| 2 | External Attribution | Unchanged. |
| 3 | Research Doc | Unchanged. |
| 4 | Deletion Detection | Unchanged. Child-task + DR protocol. |

No-impact fast path: if all changed files are OUT-scope or map to no READMEs, write "no docs impact" with evidence and advance.

### Verification Layers

**Layer 1 — Structural (grep, mechanical):**
- Extract removed/renamed symbols from git diff
- Grep target README for those symbols
- Found → stale reference. Fix inline if task-caused, TODO marker if pre-existing.

**Layer 2 — Editorial (LLM, full-file reading):**
- Read full README + current source
- Compare: code blocks accurate? Behaviors correct? New APIs missing?
- Task-caused inaccuracies: fix inline. Pre-existing: TODO marker.

Honest limitation: Layer 2 depends on model quality. Full-file reading + explicit checklist makes rubber-stamping harder but not impossible.

### TODO Marker Format

```markdown
> **TODO:** stale — load_board returns dict not Board [#1234]
```

- Always visible in rendered markdown
- One format, no variants
- Greppable: `grep -rn '> \*\*TODO:\*\*'`
- 4 categories: `stale` (grep-verified) | `inaccurate` (LLM editorial) | `missing` (LLM editorial) | `unverified` (honest uncertainty)
- Task reference: `[#{id}]`

**Gate behavior:**
- `unverified` on pre-existing content → passes gate
- `unverified` on task-introduced content → blocks gate

**Dedup:** Doc-audit resolves by fixing issue + removing markers. Harmless duplication acceptable.

### doc-writer / doc-audit Boundary

| Dimension | doc-writer | doc-audit |
|-----------|-----------|-----------|
| Trigger | Every task in `docs` stage | Manual invocation |
| Scope | Convention-mapped READMEs (1–3 per task) | Full documentation surface |
| Fix scope | Task-caused only | All issues |
| Pre-existing | TODO markers inserted | TODO markers resolved |
| Diagrams | None | Full responsibility |

**Sync-to-main:** Pre-sync check lists unresolved markers as warning (not hard gate).

**Audit cadence:** Manual-only. Recommend running before significant sync-to-main events.

### Known Limitations

- Attribution heuristic is imperfect: ambiguous cases default to TODO marker
- Asymmetric visibility: touched packages get markers, untouched look clean until audit
- Non-Python surfaces rely entirely on LLM editorial
- Category misclassification between `inaccurate`/`missing`/`unverified` is acceptable — doc-audit fixes regardless

## Deliverables

| # | Artifact | Action |
|---|----------|--------|
| 1 | `share/skills/w-doc-update/SKILL.md` | Rewrite: 4-item checklist, convention mapping, verification layers, TODO markers |
| 2 | `share/agents/doc-writer.agent.md` | Update: remove diagram references, align with new behavior |
| 3 | `.owlbear/prompts/doc-audit.prompt.md` | Revise: batch TODO-marker resolution, full diagram responsibility |
| 4 | `.owlbear/doc-index.md` | No change required |

## Acceptance Criteria

1. `w-doc-update` contains: convention mapping table, 4-item checklist with no diagram items, verification procedure (grep + LLM editorial), TODO marker insertion rules with visible format, gate-blocking rule for unverified task content
2. `doc-writer.agent.md` no longer references diagrams or Excalidraw
3. `doc-audit.prompt.md` includes: TODO marker batch resolution dimension, diagram ownership section, `describes`-based diagram verification
4. No references to old items 5-6 (diagram maintenance/creation) remain in the doc-writer skill
5. TODO marker format matches: `> **TODO:** {category} — {description} [#{id}]`
