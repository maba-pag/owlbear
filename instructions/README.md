# instructions/

Primary location for VS Code instruction files. Each file uses YAML frontmatter
(`applyTo`, `description`) to define its scope and is auto-loaded by Copilot when
relevant files are open.

| File | applyTo | Purpose |
|------|---------|---------|
| `agent-common.instructions.md` | `**` | Cross-agent rules |
| `python.instructions.md` | `**/*.py` | Python conventions |
| `frontend.instructions.md` | `src/**/ui/**,...` | Frontend conventions |
| `research-docs.instructions.md` | `docs/research/*.md` | Research guardrails |
