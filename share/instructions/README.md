# instructions/

6 instruction files in the default VS Code discovery location. Two categories:

**Substantive documents** — loaded automatically for all agents; contain full behavioral specifications:

| File | Purpose |
|------|---------|
| `agent-common.instructions.md` | Channel B communication protocol, section-header mapping, and per-agent kanban conventions |
| `owlbear-system.instructions.md` | Decision heuristics, system awareness, memory governance, and operational fundamentals |

**Instruction stubs** — safety nets loaded when `applyTo` glob matches an open file; each stub points to the authoritative skill:

| File | applyTo | Points to |
|------|---------|-----------|
| `python.instructions.md` | `**/*.py` | `h-python-conventions` |
| `frontend.instructions.md` | `**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss` | `h-frontend-conventions` |
| `research-docs.instructions.md` | `.owlbear/research/*.md` | `w-research` |
| `agents-and-skills.instructions.md` | `.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**` | `h-agent-structure` |

Stubs catch agents editing files without the relevant skill loaded. They do not duplicate the skill content — they direct the agent to load it.

See `h-agent-structure` → Instruction Stub Format for structure rules.
