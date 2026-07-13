# owlbear-tools — Workspace Utilities

Workspace utility scripts for the OwlBear project. Provides generated documentation, Python, and ECMAScript indexes used by agents for navigation.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
# Regenerate all indexes concurrently
uv run indexes

# Regenerate .owlbear/doc-index.md
uv run doc-index

# Regenerate .owlbear/py-index.md
uv run py-index

# Regenerate .owlbear/ts-index.md (TypeScript, TSX, JavaScript, and JSX)
uv run ts-index
```

Each command regenerates its complete index on every invocation. Generated indexes are advisory navigation aids; source files remain authoritative.

### Public API

```python
from owlbear_tools.doc_index import generate_index as generate_doc_index
from owlbear_tools.indexes import generate_indexes
from owlbear_tools.py_index import generate_index as generate_py_index
from owlbear_tools.ts_index import generate_index as generate_ts_index

generate_indexes(root)    # writes all three indexes concurrently
generate_doc_index(root)  # writes .owlbear/doc-index.md
generate_py_index(root)   # writes .owlbear/py-index.md
generate_ts_index(root)   # writes .owlbear/ts-index.md
```

| Function | Description |
|----------|-------------|
| `generate_indexes(root)` | Regenerate all fixed index artifacts concurrently |
| `doc_index.generate_index(root)` | Regenerate the documentation index |
| `py_index.generate_index(root)` | Regenerate the Python structure index |
| `ts_index.generate_index(root)` | Regenerate the TS/TSX/JS/JSX structure index |
| `doc_index.parse_index(content)` | Parse an existing documentation index into entries |

### Excluded directories

The documentation index excludes workspace state, generated indexes, caches, external stores, and test fixtures. Source indexes additionally exclude tests and conventional test filenames, `vendor`, `public`, `generated`, coverage, and build output.

## Configuration

No environment variables or output options. Each command writes its fixed artifact under `.owlbear/`.

## Dependencies

Python indexing uses the standard-library AST. ECMAScript indexing uses `tree-sitter-language-pack`.
