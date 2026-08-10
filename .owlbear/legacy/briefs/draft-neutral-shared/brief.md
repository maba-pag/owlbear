# Brief — Neutral Shared Layer

## Problem

OwlBear's `share/` directory (agents, skills, instructions, prompts) syncs from `dev` to `main` and is consumed by non-OwlBear projects. 10 of 80 files contain hardcoded OwlBear-dev paths (`serve/*/src/`, `serve/cockpit/web/`) that confuse consumer agents. 2 files need section-level splits. 3 prompts belong only in OwlBear-dev.

Consumers get incorrect path references, stale examples, and OwlBear-specific directory tables that don't apply to their projects.

## Outcomes

**Success:** Every `share/` file provides a good generic default for typical Python+TS projects. No unlabeled OwlBear-specific paths. OwlBear-dev's project-specifics live in its own `.github/copilot-instructions.md` and local `.owlbear/` files. A new consumer runs `setup/init.py` and gets working, neutral agent tooling immediately.

**Minimum viable:** Always-loaded system instruction and frequently-triggered skills are project-neutral (P1 + P2).

## Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D3 | Shared files = project-neutral defaults; project specifics in local config | VS Code has no priority/shadowing mechanism |
| D5 | Prose-first notation with framed examples | 3 of 4 panelists reject template syntax; labeled examples preserve concreteness |
| D6 | Phased delivery P1→P2→P3 | Ships value fast; each phase internally atomic |
| D7 | 80% rule for copilit-instructions.md; conditional content in .owlbear/instructions/ | Balances always-loaded context size vs. coverage |
| D8 | Framed examples stay in shared (labeled as project-specific) | Better than unlabeled hardcoding AND better than pure abstraction |

## Notation Convention

### In shared skills (generic context)

- Use conceptual nouns inline: "your source packages", "your frontend package root"
- Where concreteness aids comprehension, add a framed example:

  > Example (OwlBear-dev): `serve/cockpit/web/`

- Never use template syntax `{var, e.g. X}` in shared files

### In shell commands / tool invocations

- Always use concrete illustrative paths with an adjacent prose note:

  ```bash
  uv run ruff check src/ tests/  # adjust paths for your project layout
  ```

- Never put placeholder syntax in executable commands

### In copilot-instructions.md (project-local authority)

- Use concrete paths directly — this IS the resolution layer:

  ```markdown
  ## Project Layout
  - Source packages: `serve/*/src/`
  - Frontend: `serve/cockpit/web/`
  - Test paths: `tests/ serve/`
  ```

## Graceful Degradation Contract

Shared skills must produce correct behavior at two levels:

1. **Without project overlay:** Skills use generic nouns. Agents explore the filesystem, ask the user, or infer from project structure. Behavior is correct but vague — the agent finds the right paths through exploration rather than being told.

2. **With project overlay (copilot-instructions.md):** Skills reference conceptual nouns that the project config resolves to concrete paths. Both files are in the same context window. Behavior is precise.

The framed examples in shared skills serve as a fallback for level 1: they show agents what KIND of path to look for, even if the specific example doesn't apply.

## Delivery Plan

### Phase 1 — System Instruction Split + Scaffolding

**Goal:** Remove OwlBear-dev directory table from the always-loaded instruction. Scaffold consumer binding layer.

**Files to edit:**

| File | Action |
|------|--------|
| `share/instructions/owlbear-system.instructions.md` | Extract §2 Directory Structure table to OwlBear-dev local. Keep §1 Decision Heuristics, Tech Stack, Pipeline, §3 Memory Governance, §4 Operational Fundamentals. Rename from "OwlBear system instructions" to neutral. |
| `.github/copilot-instructions.md` | Add extracted directory structure table |
| `share/README.md` | Update cross-references |
| `share/WIRING.md` | Update cross-references |
| `share/skills/h-agent-structure/SKILL.md` | Update "Current stubs" table if it references moved content |
| `share/skills/h-memory-structure/SKILL.md` | Update if it references owlbear-system.instructions.md by OwlBear-specific content |
| `setup/init.py` | Scaffold a copilot-instructions.md template for new consumers with a commented path-mapping section |

**Acceptance criteria:**
- [ ] `owlbear-system.instructions.md` contains no `serve/` paths or OwlBear-dev directory listing
- [ ] Directory structure table lives in `.github/copilot-instructions.md`
- [ ] `setup/init.py` generates a consumer copilot-instructions.md with path-mapping scaffold
- [ ] `grep -r 'serve/' share/instructions/` returns zero hits (excluding MCP server names)
- [ ] No dangling cross-references from README.md, WIRING.md, or skills
- [ ] OwlBear-dev's agent behavior unchanged (specifics now in local config)

### Phase 2 — Path-Heavy Skills + Doc-Standards Chain

**Goal:** Genericize 5 path-heavy skills. Migrate r-doc-standards chain atomically.

**Files to edit:**

| File | Action |
|------|--------|
| `share/skills/r-project-standards/SKILL.md` | Extract §2 File Placement table. Keep commit format, attribution, priority, tags. |
| `share/skills/h-python-conventions/SKILL.md` | Extract Project Layout section (serve/*/src/ paths). Keep everything else. |
| `share/skills/h-pytest-and-linting/SKILL.md` | Genericize ~7 serve/ path references in examples. Use concrete illustrative + prose note pattern. |
| `share/skills/h-vitest-and-linting/SKILL.md` | Replace ~6 `serve/cockpit/web/` references with generic "your frontend package root" + framed example. |
| `share/skills/h-quality-runner/SKILL.md` | Genericize path examples. Add routing prose: "Read your project's copilot-instructions.md for frontend root and test paths. Frontend detection uses the declared frontend root." |
| `share/skills/w-doc-update/SKILL.md` | Genericize 3 IN-scope path entries |
| `share/skills/w-code-review/SKILL.md` | Genericize lint_paths template |
| `share/skills/r-doc-standards/SKILL.md` | Split: extract OwlBear-specific scope enumeration (doc-type table, serve/ paths, audience table). Keep generic quality rules IF sufficient substance remains; otherwise move entire file to `.owlbear/skills/`. |
| `share/instructions/doc-standards.instructions.md` | Update applyTo + description if r-doc-standards remains in shared; otherwise move to `.owlbear/instructions/` |
| `share/prompts/doc-audit.prompt.md` | Move to `.owlbear/prompts/` (depends on OwlBear-specific r-doc-standards) |
| `share/prompts/agent-audit.prompt.md` | Move to `.owlbear/prompts/` |
| `share/prompts/arch-audit.prompt.md` | Move to `.owlbear/prompts/` |
| `.github/copilot-instructions.md` | Add extracted file placement table, project layout paths |
| `.owlbear/instructions/architecture.instructions.md` | NEW — extract r-architecture-standards v2 overview + namespace table + domain taxonomy. `applyTo: "serve/**"` |
| `share/skills/r-architecture-standards/SKILL.md` | Remove extracted sections (v2 overview, namespace table, domain taxonomy, package dependency rules) |

**Acceptance criteria:**
- [ ] `grep -r 'serve/' share/skills/ | grep -v 'mcp-\|Example ('` returns zero hits
- [ ] h-quality-runner skill tells agents to read project config for routing
- [ ] r-doc-standards chain (skill + instruction + prompt) migrated atomically — no dangling refs
- [ ] 3 OwlBear-dev-only prompts moved to `.owlbear/prompts/`
- [ ] r-architecture-standards retains only generic MCP/module-quality rules
- [ ] OwlBear-dev's agent behavior unchanged (extracted content in local files)

### Phase 3 — Cosmetic (Deferred)

**Goal:** Remove "OwlBear" branding from 4 files with cosmetic-only issues.

**Files:** h-frontend-design, h-memory-structure, h-agent-structure, doc-standards.instructions.md (if still in shared)

**Trigger:** Defer until consumer friction reports. Not urgent — cosmetic naming doesn't cause behavioral confusion.

## Migration for Existing Consumers

The 2 existing non-OwlBear consumers already ran `setup/init.py`. They need manual steps after P1 ships:

1. Create/update `.github/copilot-instructions.md` with their project's path-mapping section (template provided by updated init.py as reference)
2. No file removals needed — shared files become more generic, which is backwards-compatible
3. Optional: re-run `setup/init.py` if an "update" mode is added (not required for P1)

## Out of Scope

| Topic | Reason | Follow-up |
|-------|--------|-----------|
| Value audit of "clean" 60 files | Separate ideation (first-principles question: do they add signal?) | research-notes.md follow-up #1 |
| h-quality-runner code/logic changes | Structural config mechanism beyond text refactoring | Separate task if prose-routing proves insufficient |
| Dead code removal (serve/orchestrator, owlbear-project.json) | D4 — noted, separate investigation | Separate brief |
| Agent file genericization | 26 agents are consumer product, already clean | N/A |
| New mechanisms (variable resolution, priority) | Out of scope per context.md | N/A |
| Reduce share/ file count based on SNR | Separate ideation | research-notes.md follow-up #1 |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLMs adopt framed examples literally | Medium | Agent uses OwlBear paths on consumer project | Label format makes non-normative clear; copilot-instructions.md overrides in same context |
| Genericized skills become too vague | Low | Agent explores instead of acting precisely | Scaffolded copilot-instructions.md provides precision; framed examples provide fallback patterns |
| P1→P2 intermediate state confuses | Low | Path-heavy skills still hardcode between phases | P1 hits highest-frequency file (always-loaded); consumers tolerate conditional-load files |
| Existing consumers miss migration | Low | They continue with status quo (current paths work for them via copilot-instructions.md) | Migration section in this Brief; both consumers user-controlled |

## Validation

Post-implementation verification:
```bash
# After P1:
grep -r 'serve/' share/instructions/ | grep -v 'mcp-'
# Expected: 0 hits

# After P2:
grep -r 'serve/' share/skills/ share/prompts/ | grep -v 'mcp-\|Example ('
# Expected: 0 hits

# Cross-reference integrity:
grep -rn 'r-doc-standards\|doc-standards.instructions' share/ | grep -v '.owlbear/'
# Expected: 0 hits (all moved or updated)
```
