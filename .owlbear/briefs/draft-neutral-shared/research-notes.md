# Research Notes — Neutral Shared Layer (v3 — complete audit)

## Verified Findings

### Correct boundary definition

- **OwlBear-specific** = only relevant to THIS repo's own code layout (`serve/`, `serve/cockpit/web/`, monorepo structure)
- **Consumer product** = MCP servers, pipeline agents, kanban, memory, knowledge, orchestration, ideation — ALL consumers use these
- The MCP skills (h-mcp-kanban, h-mcp-memory, h-knowledge-ops), orchestration, pipeline protocol, ALL agents — these are CORE consumer product, NOT OwlBear-specific

### Actual scope of the problem

**Complete audit results (ALL 80 files + 6 hooks):**
- **Total files in share/: 80** (35 skills + 26 agents + 7 instructions + 12 prompts)
- **Files with genuine path issues: 10** (serve/ hardcoding)
- **Files with cosmetic naming: 4** (s/OwlBear/project/g)
- **Files to MOVE: 2** (prompts only for OwlBear-dev)
- **Files to GENERICIZE: 4** (prompts with OwlBear refs)
- **Files CLEAN: 60** (no changes needed)
- **Hooks: 6** (all clean, consumer-facing)
- **Missing file: 1** (w-decision-routing referenced but doesn't exist)

### Files with genuine issues (HIGH priority)

| File | Issue |
|------|-------|
| `owlbear-system.instructions.md` | Directory structure table lists `serve/`, `share/`, `setup/` — OwlBear-dev layout |
| `r-architecture-standards` | v2 Architecture Overview + package namespace table describe OwlBear's `serve/` packages |
| `r-project-standards` | File placement table hardcodes `serve/*/src/`; description says "OwlBear project" |
| `r-doc-standards` | Hardcodes `serve/{package}/README.md` paths; §1.3 titled with `serve/` |
| `doc-standards.instructions.md` | applyTo includes `serve/*/README.md`; description says "OwlBear doc files" |
| `h-python-conventions` | Lists `serve/*/src/` as source layout; description says "OwlBear workspace" |
| `h-pytest-and-linting` | Hard-codes `serve/` in examples and testpaths; says "OwlBear workspace" |
| `h-vitest-and-linting` | Hard-codes `serve/cockpit/web/` throughout (~6 references) |
| `h-quality-runner` | Hard-codes `serve/mcp-kanban/`, `serve/cockpit/web/` in examples |
| `w-doc-update` | Hardcoded `serve/*/README.md (9 files)`, references `README-consumer.md` |
| `w-code-review` | Template: `lint_paths: ["serve/{package}/src/", ...]` |

### Files to MOVE to .owlbear/prompts/ (2 — OwlBear-dev-only)

| File | Reason |
|------|--------|
| `agent-audit.prompt.md` | Audits the agent ecosystem OwlBear ships; not for consumers |
| `arch-audit.prompt.md` | Audits `serve/` packages — OwlBear's monorepo backend |

### Prompts to GENERICIZE (4 — consumer-facing but has OwlBear refs)

| Prompt | Consumer use case | Fix needed |
|--------|-------------------|------------|
| `doc-audit` | Consumer audits their own docs | "OwlBear documentation" → generic |
| `memory-audit` | Consumer audits their `/memories/repo/` | "OwlBear project" → "this project" |
| `orchestrate` | Consumer orchestrates their kanban board | Check for assumptions |
| `test-curation` | Consumer curates their task-scoped tests | Check for assumptions |

### Files with cosmetic "OwlBear" naming only (4 total)

| File | Issue | Fix |
|------|-------|-----|
| `h-frontend-design` | "OwlBear-authored UI" | → "authored UI" |
| `h-memory-structure` | "OwlBear memory entries", "OwlBear workspace" | → remove "OwlBear" |
| `h-agent-structure` | "for OwlBear" in description | → remove |
| `doc-standards.instructions.md` | "OwlBear doc files" | → "project documentation" |

### Files confirmed CLEAN (no changes needed)

**Agents (26/26 clean):** All pipeline + ideation agents are consumer-facing product. No serve/ paths.

**Hooks (6/6 clean):** allow-stances-only, deny-non-doc-writes, deny-src-writes, deny-writes, lint-changed, session-context — all generic guard scripts.

**Instructions (5/7 clean):** agent-ecosystem, frontend, pipeline-agents, python, research-docs.

**Skills (24/35 clean):** h-decision-requests, h-excalidraw-diagram, h-frontend-conventions, h-ideation, h-ideation-panel, h-knowledge-ops, h-mcp-kanban, h-mcp-memory, h-visual-output, r-pipeline-protocol, w-arch-review, w-fix-attempt, w-ideation-discovery, w-ideation-mediation, w-mem-curation, w-orchestration, w-research, w-task-decomposition, w-task-verification, w-tdd-green, w-tdd-red, w-test-curation, w-decision-routing (missing), h-frontend-design (cosmetic only).

**Prompts (6/12 clean):** ideation-discover, ideation-mediate, design-context, frontend-audit, frontend-normalize, frontend-polish.

### The r-architecture-standards question

- Its RULES (error handling, config patterns, MCP server structure) ARE generic consumer content
- Its OVERVIEW and NAMESPACE TABLE are entirely OwlBear-dev specific (lists every `serve/` package)
- Solution: keep the generic rules in share/, extract OwlBear-specific overview/table to copilot-instructions.md

### The h-vitest-and-linting question

- Currently says "All commands below run from `serve/cockpit/web/`"
- Consumers MAY have frontends using Vitest — skill should be generic
- Replace `serve/cockpit/web/` with "your frontend package root" throughout
- Keep in `share/` — Vitest knowledge is consumer-useful

## Candidate Implications

### Primary strategy: parameterize paths (~8 files)

Most fixes are straightforward text substitutions:
- `serve/*/src/` → "your source packages" or just describe the convention generically
- `serve/cockpit/web/` → "your frontend package root"
- `serve/` in test commands → remove or describe generically
- Specific testpaths references → "your project's testpaths in pyproject.toml"

### Secondary strategy: split 2 mixed files

Two files need section-level surgery:
- `owlbear-system.instructions.md`: keep §1 Decision Heuristics + most of §4 Operational Fundamentals; move directory structure table to copilot-instructions.md
- `r-architecture-standards`: keep generic architecture rules; move v2 overview + namespace table to copilot-instructions.md

### Tertiary: move 2 prompts, genericize 4 prompts

- Move agent-audit.prompt.md and arch-audit.prompt.md to `.owlbear/prompts/`
- Genericize doc-audit, memory-audit, orchestrate, test-curation (remove "OwlBear" refs)

### Quaternary: cosmetic naming (4 files)

s/OwlBear/project/g in: h-frontend-design, h-memory-structure, h-agent-structure, doc-standards.instructions.md

### Where do extracted OwlBear-dev specifics go?

`.github/copilot-instructions.md` already contains project-specific sections (Cockpit, Backend, Tools, Branches). Natural additions:
- Directory structure table (from owlbear-system.instructions.md)
- Architecture v2 overview + namespace table (from r-architecture-standards)
- Specific testpaths note (`["tests", "serve"]`)

## Open Research Questions

1. **h-vitest-and-linting:** Generic with placeholder paths (recommended), or move to `.owlbear/skills/`?
2. **Placeholder notation:** Use `{package}/src/` template style, or prose ("your source packages")? Prose is clearer for LLM consumption.
3. **copilot-instructions.md size:** Adding content makes it larger — size concern? (Likely not.)
4. **Dead code (secondary, separate brief):** Is `serve/orchestrator/` dead? Is `owlbear-project.json` still used?

---

## File-by-File Approved Assessment (user-reviewed)

### File 1: `share/instructions/owlbear-system.instructions.md`

**OwlBear-dev-specific (extract to copilot-instructions.md):**
- Directory Structure table (lines 35-48): lists `serve/`, `seed/`, `setup/`, `scripts/` — these are OwlBear-dev's own directories that consumers do NOT have.

**Cosmetic:**
- Frontmatter description says "OwlBear system instructions"

**Consumer-facing (keep in shared):**
- §1 Decision Heuristics — universal methodology
- Tech Stack table — describes the services consumers receive (Python+uv, VS Code agents, MCP servers, kanban)
- Pipeline diagram — consumers follow this same pipeline
- §3 Memory Governance — universal tier structure
- §4 Operational Fundamentals — MCP bootstrap table + operational rules (consumers have the same MCP servers)

### File 2: `share/skills/r-architecture-standards/SKILL.md`

**OwlBear-dev-specific (extract to copilot-instructions.md):**
- v2 Architecture Overview (lines 10-26): ASCII diagram using `serve/` source paths. The architecture concept (agents → MCP → libs) IS consumer-relevant, but the specific source paths are OwlBear-dev-internal.
- Domain Taxonomy table (lines 131-156): maps task domains to `serve/` directories — purely OwlBear-dev contributor routing.
- Package Dependency Rules (lines 119-125): references `tests/test_package_boundary.py` and ALLOWED_IMPORTS — OwlBear-dev's internal package enforcement.

**Consumer-facing (keep in shared):**
- Module Quality Vocabulary, Deletion Test, Dependency Classification
- ALL MCP Server Conventions (error handling, tool annotations, return types, lifespan, exclusion)
- Configuration section

### File 3: `share/skills/r-project-standards/SKILL.md`

**OwlBear-dev-specific (extract or rewrite for consumer context):**
- ENTIRE §2 File Placement (lines 33-53): This table prescribes OwlBear-dev's project layout for contributors. Key issue: consumers add agents to `.owlbear/agents/` (not `share/agents/`), skills to `.owlbear/skills/` (not `share/skills/`), source to THEIR own layout (not `serve/*/src/`). The whole table is from OwlBear-dev's contributor perspective.

**Cosmetic:**
- Line 9: "conventions for the OwlBear project"
- Line 62: "Where it appears in OwlBear"

**Consumer-facing (keep in shared):**
- §1 Commit Discipline (format, rules, VS Code staging trap) — universal convention
- §3 Attribution — universal concept
- §4 Priority Scheme — universal
- §5 Tag Taxonomy — universal

### File 4: `share/skills/r-doc-standards/SKILL.md`

**Entire file is OwlBear-dev-specific — move out of share/.**

All five doc types map to OwlBear-dev's layout:
- §1.3 "Package README" → `serve/*/README.md` (consumers don't have serve/)
- §1.4 "Share-Category README" → `share/*/README.md` (consumers don't write share/)
- §1.5 "Setup Guide" → `setup/*.md` (consumers don't have setup/)
- §2 Placement table maps to OwlBear-dev paths
- §4 Audience table defines OwlBear's audiences

Consumers don't use OwlBear's doc-type rules. If they want doc standards, they'd write rules matching their own project structure. This is "how OwlBear-dev's docs must be structured", not generic guidance.

**Dependency:** `doc-audit.prompt.md` references these rules — must be addressed together.

### File 5: `share/instructions/doc-standards.instructions.md`

**Entire file is OwlBear-dev-specific — moves out with r-doc-standards as a pair.**

- `applyTo` pattern includes `serve/*/README.md`, `README-consumer.md` — OwlBear-dev paths
- Body points agents to `r-doc-standards` — which is moving out of shared
- Description says "for OwlBear doc files"

### File 6: `share/skills/h-python-conventions/SKILL.md`

**OwlBear-dev-specific (extract):**
- Project Layout section (lines 22-25): `serve/*/src/` and `serve/*/tests/` paths
- Testing section: `--import-mode=importlib ... required for monorepo layout`

**Cosmetic:** description "for the OwlBear workspace"

**Consumer-facing (keep):** Package Management (uv), Code Style (ruff, docstrings, type hints), Testing (pytest, TDD, Two-Tier Test Model), Known Gotchas, Patterns (tenacity, Typer)

### File 7: `share/skills/h-pytest-and-linting/SKILL.md`

**OwlBear-dev-specific (path references in ~7 command examples):**
- Full suite commands use `tests/ serve/`
- testpaths reference: `["tests", "serve"]`
- Ruff command: `uv run ruff check serve/ tests/`
- File-capture fallback uses `'tests/', 'serve/'`
- "Flags that don't work" example uses `--cov=serve/mcp-kanban/src/`

**Cosmetic:** "in the OwlBear workspace"

**Consumer-facing (keep):** Scoped run pattern, async mode, test markers, pytest config table, coverage commands, PowerShell warning, file-capture technique, Windows gotcha. Fix = genericize serve/ path references in examples.

### File 8: `share/skills/h-vitest-and-linting/SKILL.md`

**OwlBear-dev-specific (~6 path references):**
- `serve/cockpit/web/` hardcoded throughout (working dir, cd commands, eslint, coverage, gotchas)

**Cosmetic:** description "for the Cockpit frontend"

**Consumer-facing (keep):** Vitest commands, PDS console noise gotcha, ESLint config/exit codes, coverage commands, Vitest configuration, setup file shims, all Known Gotchas content. Any PDS+Vitest project needs this knowledge. Fix = genericize to "your frontend package root".

### File 9: `share/skills/h-quality-runner/SKILL.md`

**OwlBear-dev-specific (paths + detection logic):**
- Examples use `serve/my-package/`, `serve/cockpit/web/src/__tests__/...`
- Frontend detection hardcodes: "paths under `serve/cockpit/web/` use vitest"
- Full suite: "runs `tests/ serve/ -m 'not api'`"
- Defaults: "lint_paths defaults to `serve/ tests/`"
- Output example: `serve/foo/src/foo/bar.py`

**Implementation note:** The frontend detection mechanism itself (prefix check on `serve/cockpit/web/`) needs to become project-configurable, not just the documentation.

**Consumer-facing (keep):** Quality-runner concept, invocation pattern, input fields, output format, exit codes, agents: prerequisite. Fix = genericize paths + note detection needs config.

### Files 10-21: Review in progress

### File 10: `share/skills/w-doc-update/SKILL.md`

**OwlBear-dev-specific (3 path entries in scope classification list):**
- "Package READMEs: `serve/*/README.md` (9 files)"
- "Setup guides: `setup/setup-guide.md`, `setup/sharing-guide.md`"
- "`README-consumer.md`"

**Consumer-facing (keep):** The entire workflow (setup, scope classification concept, relevance-gated checklist, clean scratch, commit & advance, output template). Fix = genericize the 3 IN-scope entries.

### File 11: `share/skills/w-code-review/SKILL.md`

**OwlBear-dev-specific (2-3 template path references):**
- Step 2.5 and Step 3 lint_paths: `"serve/{package}/src/"`

**Consumer-facing (keep):** The entire code review methodology (Steps 0-8), critical checks (security, test integrity, quality, data safety, necessity, loop detection), informational checks, AC compliance, verdict logic, code-reader delegation. Fix = genericize lint_paths template.

### Files 12-17: Prompts

**MOVE to `.owlbear/prompts/` (3 files — OwlBear-dev only):**
- `agent-audit.prompt.md` — audits OwlBear's shipped agent ecosystem, not consumer's
- `arch-audit.prompt.md` — explicitly audits `serve/` packages
- `doc-audit.prompt.md` — depends on `r-doc-standards` (which is moving out). Since its standard is OwlBear-dev-specific, this prompt is too.

**COSMETIC (1 file):**
- `memory-audit.prompt.md` — "for the OwlBear project" → s/OwlBear/this/. Audit targets `/memories/repo/` which consumers have.

**ALREADY CLEAN (2 files — no changes needed):**
- `orchestrate.prompt.md` — just `Orchestrate: ${input:...}`. No OwlBear refs.
- `test-curation.prompt.md` — just `Curate tests`. No OwlBear refs.

### File 18: `share/skills/h-frontend-design/SKILL.md`

**Cosmetic (1 occurrence):** Line 8 "for OwlBear-authored UI" → s/OwlBear-authored/project/

**Consumer-facing (entire file):** Design context methodology, reference pack, universal blockers, design domains (typography, color, spatial, motion, interaction, responsive, UX writing), anti-pattern classification. No serve/ paths.

### File 19: `share/skills/h-memory-structure/SKILL.md`

**Cosmetic (1 occurrence):** Line 9 "OwlBear memory entries" → s/OwlBear //

**NOT cosmetic (product names — keep):** `owlbearMemory` (MCP tool name), `.owlbear/` paths (universal convention), `owlbear-system.instructions.md` (valid cross-ref).

**Consumer-facing (entire file):** Entry shape, tier-content fit, file vs MCP relationship, deduplication rules, content-quality bar, confidence calibration, anti-patterns. No serve/ paths.
- `orchestrate.prompt.md` — just `Orchestrate: ${input:...}`. No OwlBear refs.
- `test-curation.prompt.md` — just `Curate tests`. No OwlBear refs.

### File 20: `share/skills/h-agent-structure/SKILL.md`

**Assessment: Keep in share/ + fix delivery mechanism.**

Currently only loaded by OwlBear-dev contributors (via agent-audit and agent-ecosystem.instructions.md with `applyTo: "share/agents/**,..."`). Consumers writing to `.owlbear/agents/**` don't trigger it.

Content IS consumer-useful (file type selection, boundary fitness, naming grammar, required sections, nesting depth rules). The delivery mechanism needs fixing: extend `agent-ecosystem.instructions.md` applyTo to also cover `.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**`.

**Cosmetic:** "for OwlBear" in description and intro.
**Stale after refactor:** "Current stubs" table row for doc-standards.instructions.md (that file moves out).

### File 21: Already covered as File 5

(`doc-standards.instructions.md` — moves out with r-doc-standards)

**Cosmetic (1 occurrence):** Line 8 "for OwlBear-authored UI"

**Consumer-facing (entire file):** Design context methodology, reference pack, universal blockers, design domains (typography, color, spatial, motion, interaction, responsive, UX writing), anti-pattern classification. Pure design guidance. No serve/ paths.

### File 19: `share/skills/h-memory-structure/SKILL.md`

**Cosmetic (1 occurrence):** Line 9 "OwlBear memory entries"

**NOT cosmetic (product names — keep):** `owlbearMemory` (MCP tool name), `.owlbear/` paths (universal convention), `owlbear-system.instructions.md` (valid cross-ref).

**Consumer-facing (entire file):** Entry shape, tier-content fit, file vs MCP relationship, deduplication rules, content-quality bar, confidence calibration, anti-patterns. No serve/ paths.

---

## Follow-up Topics (out of scope — need separate ideation)

1. **Reduce agents/instructions/skills/prompts based on SNR and common knowledge** — which files add value vs. stating the obvious?
2. **Remove serve/orchestrator (the CLI part of OwlBear)** — potentially dead code, maybe more to remove.
3. **Split singleton tests/ folder into per-module tests** — since modules don't interact, per-module testing may be simpler/faster.
