"""Regenerate all OwlBear navigation indexes concurrently."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from owlbear_tools.doc_index import generate_index as generate_doc_index
from owlbear_tools.py_index import generate_index as generate_py_index
from owlbear_tools.ts_index import generate_index as generate_ts_index

_GENERATORS = (generate_doc_index, generate_py_index, generate_ts_index)


def generate_indexes(root: Path) -> None:
    """Regenerate every workspace index concurrently."""
    with ThreadPoolExecutor(max_workers=len(_GENERATORS)) as executor:
        futures = [executor.submit(generator, root) for generator in _GENERATORS]
        for future in futures:
            future.result()


def main() -> None:
    """CLI entry point for regenerating all workspace indexes."""
    parser = argparse.ArgumentParser(description="Regenerate all OwlBear navigation indexes.")
    parser.add_argument("root", nargs="?", default=".", help="Workspace root directory")
    arguments = parser.parse_args()
    generate_indexes(Path(arguments.root).resolve())
