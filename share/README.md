# share/ — Agent Ecosystem

OwlBear's agent ecosystem definitions and supporting documents. This directory is their single source of truth.

## Directory Layout

| Directory | Contents |
|-----------|----------|
| `agents/` | Agent definitions (`.agent.md`) |
| `skills/` | Reusable domain knowledge (`SKILL.md`) |
| `instructions/` | Auto-loaded instruction files (`.instructions.md`) |
| `prompts/` | User-invocable one-shot commands (`.prompt.md`) |
| `diagrams/` | Shared visual assets (Excalidraw, SVG) |

## Loading Model

Content reaches agents through four mechanisms, ordered by cost:

| Mechanism | When it loads | Cost | Use for |
|-----------|--------------|------|---------|
| `copilot-instructions.md` | Every turn, every agent | Project-dependent | Current-project identity, topology, stack, commands, and resources |
| Instructions (`.instructions.md`) | Every turn when `applyTo` glob matches a touched file | ~20–70 tokens/turn | Safety-net stubs and universal rules |
| Skill frontmatter | Every turn, every agent (YAML header only) | ~20 tokens/skill/turn | Discovery — VS Code uses this to decide when to suggest the skill |
| Skill body (`read_file`) | Once per session, on demand | One-time read (~300–500 tokens) | Procedures, protocol, domain knowledge |

**Key insight:** Instructions are per-turn system prompt cost. Skills are one-time read cost. Large content belongs in skills, not instructions.

### Two-Tier Skill Loading

1. **Mandatory** — listed in the agent's `<required_reading>` section. Read via `read_file` at session start. These are skills the agent needs in 90%+ of sessions.
2. **On-demand** — loaded during the workflow when a specific scenario arises. Referenced by other skills' companion tables or Step 0 directives.

### Belts and Suspenders

For important skills, use both tiers:

- **Belt:** List the skill in the agent's `<required_reading>` (guarantees it's loaded)
- **Suspenders:** Provide an `applyTo` instruction stub that fires when the agent touches relevant files (catches agents that skip required_reading)

### Transitive Dependencies

Skills can declare companion skills that consumers should load when needed:

- **Level 0 (direct):** Agent → skill, listed in `<required_reading>`
- **Level 1 (transitive):** Skill A → skill B, declared in A's companion table or Step 0
- Only Level 0 goes in `<required_reading>`. Level 1 is the skill's responsibility.

## Always-Loaded Context

These load into every agent's context on every turn:

| File | Mechanism | Authority |
|------|-----------|-----------|
| `.github/copilot-instructions.md` | Workspace instructions (always present) | Current-project facts only; never shared OwlBear behavior |
| `owlbear-system.instructions.md` | `applyTo: "**"` (fires on any file touch) | Universal OwlBear behavior |

## Agents

Agent definitions use `.agent.md` files.

| Tier | Agents |
|------|--------|
| T1 — Orchestrator | orchestrator |
| T2 — Pipeline | shaper, builder, verifier, collector |
| T3 — Support | test-curator, memory-curator |
| T4 — Tools/Panel | shaper-challenger, builder-challenger, verifier-challenger |
| T5 — Knowledge | knowledge-enricher, knowledge-ingestor |

### Nesting Depth

VS Code does not inject the agents catalog at nesting depth ≥2. Agents at depth ≥3 (ND3) must have `disable-model-invocation: false` to be resolvable, and dispatching agents rely on their `<agents>` body section — not the system-injected catalog — for subagent discovery.

**ND3 agents** (marked with `(ND3)` in their description): shaper-challenger, builder-challenger, verifier-challenger.

See `h-agent-structure` § Nesting Depth & DMI for the full rule and ND3 agent table.

## Skills

Skill definitions live under `share/skills/{name}/SKILL.md`.

| Prefix | Purpose |
|--------|---------|
| `w-` | Workflow — step-by-step procedures |
| `r-` | Rules — shared conventions |
| `h-` | Handbook — domain knowledge |

## Instructions

Instruction files use `.instructions.md`. Two categories:

**Substantive documents** — contain full behavioral specifications:

| File | Purpose |
|------|---------|
| `owlbear-system.instructions.md` | Decision heuristics, system awareness, memory governance, and operational fundamentals |

**Instruction stubs** — safety nets loaded when `applyTo` glob matches a touched file; each stub points to the authoritative skill:

| File | applyTo | Points to |
|------|---------|-----------|
| `python.instructions.md` | `**/*.py` | `h-python-conventions` |
| `frontend.instructions.md` | `**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss` | `h-frontend-conventions` |
| `agent-ecosystem.instructions.md` | `share/agents/**,share/skills/**,share/instructions/**,share/prompts/**,.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**` | `share/README.md` + `h-agent-structure` |
| `doc-standards.instructions.md` | `README.md,README-consumer.md,SECURITY.md,serve/*/README.md,share/README.md,setup/*.md` | `r-doc-standards` |
| `research-docs.instructions.md` | `.owlbear/research/*.md` | `w-research` |

Stubs catch agents editing files without the relevant skill loaded. They do not duplicate the skill content — they direct the agent to load it.

## Prompts

Prompt files use `.prompt.md`. Prompts are user-invocable one-shot commands triggered from the VS Code chat command palette. Many accept `${input:...}` variable substitution.

**Naming convention:**

| Pattern | Meaning |
|---------|----------|
| `{verb}.prompt.md` | Single-purpose action (e.g., `orchestrate`) |
| `{scope}-{verb}.prompt.md` | Scoped action (e.g., `frontend-audit`, `memory-audit`) |

**Current prompts:**

| Group | Prompts |
|-------|--------|
| Orchestration | `shape`, `orchestrate` |
| Planning and design | `ideate`, `architecture-review` |
| Audits | `arch-audit`, `frontend-audit`, `memory-audit`, `legacy-audit` |
| Knowledge | `kb-ingest`, `kb-enrich` |
| Curation | `test-curation` |

## File Interconnections

See [WIRING.md](WIRING.md) for the full two-way mapping:

- **Table 1:** Agent/Prompt → relevant files (regularly vs. seldom, with connection method)
- **Table 2:** File → consuming agents/prompts (inverse)

## Structural Standards

For the authoritative specification of agent/skill/instruction file structure, section conventions, and naming grammar, see the `h-agent-structure` skill.
