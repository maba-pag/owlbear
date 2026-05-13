# owlbear-tools — Workspace Utilities

Workspace utility scripts for the OwlBear project. Currently provides the doc-index generator, which scans all documentation files in the workspace and writes a structured index used by agents for navigation.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
# Regenerate .owlbear/doc-index.md
uv run doc-index
```

The command skips the write if `doc-index.md` is newer than all collected documentation files.

### Public API

```python
from owlbear_tools.doc_index import collect_docs, generate_index, should_regenerate, parse_index

docs    = collect_docs(root)          # list[DocEntry]
index   = generate_index(docs)        # str (Markdown)
skip    = should_regenerate(root)     # bool
entries = parse_index(index_content)  # list[DocEntry]
```

| Function | Description |
|----------|-------------|
| `collect_docs(root)` | Walk the workspace, skip excluded dirs, return parsed `DocEntry` list |
| `generate_index(docs)` | Render collected entries to the Markdown index format |
| `should_regenerate(root)` | Return `True` if any doc is newer than the existing index |
| `parse_index(content)` | Parse an existing index back into `DocEntry` objects |

### Excluded directories

The following paths are never indexed: `.owlbear/scratch`, `.owlbear/research`, `.owlbear/kanban`, `.owlbear/briefs`, `.owlbear/sources`, `store`, `tests`, `node_modules`, `.git`, `dist`, `build`.

## Configuration

No environment variables. The index is always written to `.owlbear/doc-index.md`.

## Dependencies

No third-party dependencies — standard library only.
