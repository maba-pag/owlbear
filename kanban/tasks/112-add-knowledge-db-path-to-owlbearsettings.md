---
id: 112
title: Add knowledge_db_path to OwlBearSettings
status: todo
priority: high
created: 2026-02-27T03:31:42.1253923+01:00
updated: 2026-02-27T03:44:41.3317935+01:00
started: 2026-02-27T03:32:50.278732+01:00
tags:
    - memory
    - knowledge-graph
    - config
    - phase-2
class: standard
---

Add knowledge configuration fields to `OwlBearSettings` in `src/owlbear/config.py`.

## Acceptance Criteria

- [ ] Add `knowledge_db_path: Path` field to `OwlBearSettings`
  - Default: `Path.home() / '.owlbear' / 'knowledge.db'`
  - Overridable via `OWLBEAR_KNOWLEDGE_DB_PATH` env var
- [ ] Add `embedding_model: str` field to `OwlBearSettings`
  - Default: `'BAAI/bge-small-en-v1.5'`
  - Overridable via `OWLBEAR_EMBEDDING_MODEL` env var
- [ ] Fields placed in a `# --- Knowledge ---` section (follows existing section pattern)
- [ ] Add test assertions in `tests/test_config.py`:
  - `test_knowledge_db_path_default` — verifies default is `~/.owlbear/knowledge.db`
  - `test_embedding_model_default` — verifies default is `BAAI/bge-small-en-v1.5`
  - `test_knowledge_db_path_env_override` — verifies OWLBEAR_KNOWLEDGE_DB_PATH works
  - `test_embedding_model_env_override` — verifies OWLBEAR_EMBEDDING_MODEL works
- [ ] Existing config tests still pass
- [ ] Follow existing field patterns (see `copilot_token_path` for Path, `chat_model` for str)

See docs/knowledge-graph-research.md section 4, key decision 1-2
