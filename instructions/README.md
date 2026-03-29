# instructions/

Shared instruction files for OwlBear agents. Each file uses YAML frontmatter
(`applyTo`, `description`) to define its scope. Migrated from `.github/instructions/`
during the v2 migration (task #10).

| File | applyTo | Purpose |
|------|---------|--------|
| `python.instructions.md` | `**/*.py` | Python coding conventions |
| `agent-common.instructions.md` | `**` | Cross-agent rules |
| `research-docs.instructions.md` | `docs/research/*.md` | Research doc guardrails |
| `frontend.instructions.md` | `src/**/ui/**,**/*.tsx,...` | Frontend conventions |
