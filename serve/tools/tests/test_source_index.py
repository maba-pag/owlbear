"""Tests for the Python and ECMAScript source indexes."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

from owlbear_tools.py_index import generate_index as generate_py_index
from owlbear_tools.ts_index import generate_index as generate_ts_index


def _write(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_py_index_describes_modules_without_importing_them(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/example.py",
        '''"""Example service."""

import json
from pathlib import Path

class Service(BaseService):
    def run(self, value: str = "x") -> bool:
        return True

async def build(path: Path) -> Service:
    return Service()
''',
    )
    generate_py_index(tmp_path)

    content = (tmp_path / ".owlbear/py-index.md").read_text()
    assert "## src/example.py" in content
    assert "Example service." in content
    assert "`json`" in content
    assert "`pathlib`" in content
    assert "### Imports\n\n- `json`" in content
    assert "### Interfaces\n\n- `class Service(BaseService)`" in content
    assert "`class Service(BaseService)`" in content
    assert "`def run(self, value: str = 'x') -> bool`" in content
    assert "`async def build(path: Path) -> Service`" in content


@pytest.mark.parametrize(
    ("relative_path", "declaration"),
    [
        ("src/example.ts", "export function parse(value: string): number"),
        ("src/example.tsx", "export const Panel: React.FC<Props>"),
        ("src/example.js", "export class Store"),
        ("src/example.jsx", "export default function View()"),
    ],
)
def test_ts_index_covers_ecmascript_family(
    tmp_path: Path,
    relative_path: str,
    declaration: str,
) -> None:
    sources = {
        ".ts": "import { value } from './values';\nexport function parse(value: string): number { return 1; }\n",
        ".tsx": "import React from 'react';\nexport const Panel: React.FC<Props> = (props) => <div />;\n",
        ".js": "import item from './item.js';\nexport class Store { read(key) { return key; } }\n",
        ".jsx": "import React from 'react';\nexport default function View() { return <main />; }\n",
    }
    _write(tmp_path, relative_path, sources[Path(relative_path).suffix])
    generate_ts_index(tmp_path)

    content = (tmp_path / ".owlbear/ts-index.md").read_text()
    assert f"## {relative_path}" in content
    assert f"`{declaration}`" in content
    assert "### Imports\n\n- `import" in content
    assert f"### Interfaces\n\n- `{declaration}`" in content


def test_ts_index_includes_type_interfaces_and_class_methods(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/contracts.ts",
        "export interface Item { id: string }\n"
        "export type ItemId = string;\n"
        "export class Repository { find(id: ItemId): Item | undefined { return undefined; } }\n",
    )
    generate_ts_index(tmp_path)

    content = (tmp_path / ".owlbear/ts-index.md").read_text()
    assert "`export interface Item`" in content
    assert "`export type ItemId = string`" in content
    assert "`export class Repository`" in content
    assert "`find(id: ItemId): Item | undefined`" in content


def test_ts_index_includes_export_only_statements(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/exports.ts",
        "const Shell = () => null;\nexport default Shell;\nexport { Shell };\nexport type { TaskDetail };\n",
    )

    generate_ts_index(tmp_path)

    content = (tmp_path / ".owlbear/ts-index.md").read_text()
    assert "`export default Shell`" in content
    assert "`export { Shell }`" in content
    assert "`export type { TaskDetail }`" in content


@pytest.mark.parametrize("generator", [generate_py_index, generate_ts_index])
def test_indexes_are_deterministic_and_skip_non_product_paths(tmp_path: Path, generator) -> None:
    _write(tmp_path, "src/keep.py", "def keep():\n    pass\n")
    _write(tmp_path, "src/keep.ts", "export const keep = () => true;\n")
    _write(tmp_path, "tests/skip.py", "def skip():\n    pass\n")
    _write(tmp_path, "src/test_skip.py", "def skip():\n    pass\n")
    _write(tmp_path, "src/skip_test.py", "def skip():\n    pass\n")
    _write(tmp_path, "node_modules/pkg/skip.ts", "export const skip = true;\n")
    _write(tmp_path, "vendor/pkg/skip.ts", "export const skip = true;\n")
    _write(tmp_path, "generated/pkg/skip.py", "def skip():\n    pass\n")
    generator(tmp_path)
    output = tmp_path / ".owlbear" / ("py-index.md" if generator is generate_py_index else "ts-index.md")
    first = output.read_text()
    generator(tmp_path)

    assert output.read_text() == first
    assert "tests/skip.py" not in first
    assert "src/test_skip.py" not in first
    assert "src/skip_test.py" not in first
    assert "node_modules/pkg/skip.ts" not in first
    assert "vendor/pkg/skip.ts" not in first
    assert "generated/pkg/skip.py" not in first


@pytest.mark.parametrize("generator", [generate_py_index, generate_ts_index])
@pytest.mark.parametrize("state_root", ["delivery", "legacy", "target", "worktrees"])
def test_indexes_skip_owlbear_runtime_and_secondary_trees(tmp_path: Path, generator, state_root: str) -> None:
    _write(tmp_path, "src/keep.py", "def keep():\n    pass\n")
    _write(tmp_path, "src/keep.ts", "export const keep = true;\n")
    hidden = _write(tmp_path, f".owlbear/{state_root}/nested/hidden.py", "def hidden():\n    pass\n")
    generate_path = tmp_path / ".owlbear" / ("py-index.md" if generator is generate_py_index else "ts-index.md")

    generator(tmp_path)

    content = generate_path.read_text()
    assert hidden.as_posix() not in content
    assert ".owlbear/" + state_root not in content


def test_ts_index_skips_tests_and_generated_public_bundles(tmp_path: Path) -> None:
    _write(tmp_path, "src/keep.ts", "export const keep = true;\n")
    _write(tmp_path, "src/__tests__/skip.ts", "export const skip = true;\n")
    _write(tmp_path, "src/skip.test.tsx", "export const skip = true;\n")
    _write(tmp_path, "public/vendor/generated.js", "export const skip = true;\n")
    generate_ts_index(tmp_path)

    content = (tmp_path / ".owlbear/ts-index.md").read_text()
    assert "src/keep.ts" in content
    assert "__tests__" not in content
    assert ".test.tsx" not in content
    assert "public/vendor/generated.js" not in content


def test_ts_index_marks_parse_errors(tmp_path: Path) -> None:
    _write(tmp_path, "src/broken.ts", "export function broken( {\n")
    generate_ts_index(tmp_path)

    assert "Parse status: error; inspect source directly." in (tmp_path / ".owlbear/ts-index.md").read_text()


def test_source_index_entry_points_are_registered() -> None:
    names = {entry.name for entry in importlib.metadata.entry_points(group="console_scripts")}
    assert {"py-index", "ts-index"} <= names
