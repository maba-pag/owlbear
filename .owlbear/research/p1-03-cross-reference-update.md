# P1-03: Cross-Reference Update Plan

> **Owning task:** #1283 — P1-03: Update cross-references in README, WIRING, h-agent-structure, h-memory-structure
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1282 (P1-02) splits `owlbear-system.instructions.md` by extracting the §2 Directory Structure table to `.github/copilot-instructions.md` and updating the YAML description to project-neutral wording. Task #1283 must update all downstream cross-references so nothing dangles after the split.

Additional scope: extend `agent-ecosystem.instructions.md` applyTo to cover `.owlbear/` agent ecosystem paths (from brief research-notes File 20).

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Brief | `.owlbear/briefs/draft-neutral-shared/brief.md` | 1.0 — defines the split scope |
| Task #1282 AC | kanban | 1.0 — defines what changes in owlbear-system.instructions.md |
| share/README.md | `share/README.md` | 1.0 — target file |
| share/WIRING.md | `share/WIRING.md` | 1.0 — target file |
| h-agent-structure | `share/skills/h-agent-structure/SKILL.md` | 1.0 — target file |
| h-memory-structure | `share/skills/h-memory-structure/SKILL.md` | 1.0 — target file |
| agent-ecosystem.instructions.md | `share/instructions/agent-ecosystem.instructions.md` | 1.0 — applyTo extension target |
| research-notes File 20 | `.owlbear/briefs/draft-neutral-shared/research-notes.md:294-296` | 0.9 — applyTo rationale |
| Test file #1281 | `tests/test_neutral_shared_1281.py` | 0.9 — defines pass criteria |

## 3. Analysis

### Cross-reference inventory

Searched all `share/` files for references to `owlbear-system.instructions` and `agent-ecosystem.instructions`.

#### Changes required after #1282 updates the description

| File | Line | Current text | Action |
|------|------|-------------|--------|
| share/README.md | 97 | `"Decision heuristics, system awareness, memory governance, and operational fundamentals"` | Update to match new description from #1282 |
| h-agent-structure/SKILL.md | 344 | `"Decision heuristics, system awareness, memory governance (universal)"` | Update to match new description from #1282 |

#### Changes required for agent-ecosystem.instructions.md applyTo extension

| File | Line | Current | New |
|------|------|---------|-----|
| agent-ecosystem.instructions.md | 3 | `share/agents/**,...,share/prompts/**` | Add `.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**` |
| share/README.md | 105 | Stubs table applyTo column | Mirror new applyTo |
| h-agent-structure/SKILL.md | ~320 | "Current stubs" table applyTo column | Mirror new applyTo |
| share/WIRING.md | 226 | `"any agent editing share/ files"` | Update to `"any agent editing share/ or .owlbear/ ecosystem files"` |
| share/WIRING.md | 257 | `"Fires when any agent edits share/ files"` | Update scope description |

#### No changes needed

| File | Line | Reference | Why safe |
|------|------|-----------|---------|
| share/WIRING.md | 42 | Filename in Universal Files table | Filename unchanged |
| share/WIRING.md | 221 | Filename in inverse table | Filename unchanged |
| h-memory-structure/SKILL.md | 43 | `§ Memory Governance` section ref | §3 Memory Governance stays in the file |
| memory-layers.excalidraw | 65-66 | `owlbear-system.instructions.md §3` | §3 stays |

### Dependency analysis

#1283 must execute AFTER #1282 because the exact new description text is unknown until #1282 sets it. Currently `depends_on` is empty — **add #1282 as a dependency**.

### Test coverage

`tests/test_neutral_shared_1281.py::TestFromAC_NoDanglingCrossRefs::test_section_refs_exist_in_owlbear_system` validates § section references. Currently only h-memory-structure has a § ref (`§ Memory Governance`) which remains valid. No additional tests needed for the cross-reference updates themselves — AC6 ("Tests from #1281 pass") is satisfied by the existing test.

## 4. Recommendation

T1 — Autonomous. Trivial doc cross-reference update. No new capability, no architecture change, no user decision needed.

Implementation plan (confidence: 0.92):

1. Wait for #1282 to complete (dependency)
2. Read #1282's output to get the new description text
3. Update 2 description references (README.md, h-agent-structure)
4. Extend agent-ecosystem.instructions.md applyTo
5. Update 4 mirror references (README.md stubs table, h-agent-structure stubs table, WIRING.md ×2)
6. Run `test_neutral_shared_1281.py` to verify AC6

Total: 5 files edited, ~7 line changes. Estimated diff: <20 lines.

Challenge: skipped (trivial cross-reference inventory, no recommendation trade-offs).

## 5. Follow-up Tasks

No additional follow-up tasks needed — this task IS the implementation task. It advances to backlog for execution.
