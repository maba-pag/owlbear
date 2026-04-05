# instructions/

Instruction stubs — safety nets that catch agents editing files without the relevant skill loaded. VS Code auto-loads them when `applyTo` glob matches an open file.

| File | applyTo | Points to |
|------|---------|-----------|
| `python.instructions.md` | `**/*.py` | `h-python-conventions` |
| `frontend.instructions.md` | `**/*.tsx,**/*.jsx,**/*.vue,**/*.svelte,**/*.css,**/*.scss` | `h-frontend-conventions` |
| `research-docs.instructions.md` | `.owlbear/research/*.md` | `w-research` |
| `agents-and-skills.instructions.md` | `share/agents/**,share/skills/**` | `h-agent-structure` |

See `h-agent-structure` → Instruction Stub Format for structure rules.
