"""Inventory task-looking tests and verify immutable legacy provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_TASK_ID_RE = re.compile(r"(?<!\d)(\d{3,})(?!\d)")
_PYTHON_FILENAME_RE = re.compile(r"^test_.*_[0-9]+\.py$")
_FRONTEND_FILENAME_RE = re.compile(r"[._-][0-9]+\.test\.(?:ts|tsx)$")
_E2E_FILENAME_RE = re.compile(r"[-_][0-9]+\.spec\.ts$")
_IMPORT_RE = re.compile(r"^\s*(?:from\s+\S+\s+import\b|import\s+\S)")
_OWNERSHIP_RE = re.compile(
    r"(?i)\b(?:red(?:[- ]phase)?|task(?:[- ]local)?|tests?\s+for|test[- ]writer|"
    r"acceptance\s+(?:tests?|criteria)|consolidat(?:e|ion)|regression)\b.*?"
    r"(?:#\s*)?(\d{3,})\b"
)


@dataclass(frozen=True)
class LegacyMatch:
    """One manifest record that may establish immutable provenance."""

    manifest: str
    relative_path: str
    lifecycle: str
    hash_verified: bool


@dataclass(frozen=True)
class Candidate:
    """One task-looking test module and its provenance evidence."""

    path: str
    kind: str
    signals: tuple[str, ...]
    task_ids: tuple[str, ...]
    provenance: str
    legacy_matches: tuple[LegacyMatch, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _header(path: Path) -> str:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if _IMPORT_RE.match(line):
            break
        lines.append(line)
    return "\n".join(lines)


def _header_ids(path: Path) -> tuple[str, ...]:
    ids: set[str] = set()
    for line in _header(path).splitlines():
        if re.search(r"(?i)\bmined\s+from\b", line):
            continue
        match = _OWNERSHIP_RE.search(line)
        if match:
            ids.add(match.group(1))
    return tuple(sorted(ids, key=int))


def _filename_ids(path: Path) -> tuple[str, ...]:
    return tuple(sorted(set(_TASK_ID_RE.findall(path.name)), key=int))


def _test_roots(root: Path) -> tuple[Path, ...]:
    roots: set[Path] = set()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as stream:
            config = tomllib.load(stream)
        configured = config.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
        for value in configured if isinstance(configured, list) else []:
            if isinstance(value, str):
                roots.add(root / value)

    roots.update(path for path in root.glob("serve/*/tests") if path.is_dir())
    for path in (
        root / "serve/cockpit/web/src/__tests__",
        root / "serve/cockpit/web/e2e",
    ):
        if path.is_dir():
            roots.add(path)
    return tuple(sorted(roots))


def _kind(path: Path) -> str | None:
    if path.suffix == ".py" and path.name.startswith("test_"):
        return "python"
    if path.name.endswith((".test.ts", ".test.tsx")):
        return "frontend"
    if path.name.endswith(".spec.ts"):
        return "e2e"
    return None


def _filename_signal(path: Path, kind: str) -> bool:
    if kind == "python":
        return _PYTHON_FILENAME_RE.match(path.name) is not None
    if kind == "frontend":
        return _FRONTEND_FILENAME_RE.search(path.name) is not None
    return _E2E_FILENAME_RE.search(path.name) is not None


def _candidate_files(root: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    seen_paths: set[Path] = set()
    for test_root in _test_roots(root):
        for path in sorted(test_root.rglob("*")):
            if not path.is_file() or "node_modules" in path.parts:
                continue
            if path in seen_paths:
                continue
            kind = _kind(path)
            if kind is not None:
                seen_paths.add(path)
                files.append((path, kind))
    return files


def _lifecycle(manifest: Path, relative_path: str) -> str | None:
    parts = (*manifest.relative_to(manifest.parents[2]).parts, *Path(relative_path).parts)
    if "completed" in parts:
        return "completed"
    if "archive" in parts:
        return "archived"
    return None


def _legacy_index(root: Path) -> dict[str, tuple[LegacyMatch, ...]]:
    index: dict[str, list[LegacyMatch]] = {}
    legacy_root = root / ".owlbear/legacy"
    if not legacy_root.is_dir():
        return {}

    for manifest in sorted(legacy_root.rglob("manifest.json")):
        try:
            payload: Any = json.loads(manifest.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            continue
        records = payload.get("files", []) if isinstance(payload, dict) else []
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            relative_path = record.get("relative_path")
            expected_hash = record.get("sha256")
            if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
                continue
            lifecycle = _lifecycle(manifest, relative_path)
            if lifecycle is None:
                continue
            preserved = manifest.parent / relative_path
            hash_verified = preserved.is_file() and _sha256(preserved) == expected_hash
            match = _TASK_ID_RE.search(Path(relative_path).name)
            if match:
                index.setdefault(match.group(1), []).append(
                    LegacyMatch(
                        manifest=_relative(root, manifest),
                        relative_path=relative_path,
                        lifecycle=lifecycle,
                        hash_verified=hash_verified,
                    )
                )
    return {task_id: tuple(matches) for task_id, matches in index.items()}


def _provenance(
    task_ids: tuple[str, ...], legacy: dict[str, tuple[LegacyMatch, ...]]
) -> tuple[str, tuple[LegacyMatch, ...]]:
    matches_list: list[LegacyMatch] = []
    for task_id in task_ids:
        matches_list.extend(legacy.get(task_id, ()))
    matches = tuple(matches_list)
    if any(match.hash_verified for match in matches):
        return "verified", matches
    if matches:
        return "unverified", matches
    return "missing", matches


def inventory(root: Path = _REPOSITORY_ROOT) -> dict[str, Any]:
    """Return candidate test modules and their immutable provenance evidence."""
    root = root.resolve()
    legacy = _legacy_index(root)
    candidates: list[Candidate] = []
    for path, kind in _candidate_files(root):
        filename_ids = _filename_ids(path) if _filename_signal(path, kind) else ()
        header_ids = _header_ids(path)
        task_ids = tuple(sorted(set(filename_ids + header_ids), key=int))
        if not task_ids:
            continue
        provenance, matches = _provenance(task_ids, legacy)
        signals = tuple(
            signal for signal, present in (("filename", bool(filename_ids)), ("header", bool(header_ids))) if present
        )
        candidates.append(
            Candidate(
                path=_relative(root, path),
                kind=kind,
                signals=signals,
                task_ids=task_ids,
                provenance=provenance,
                legacy_matches=matches,
            )
        )

    candidate_data: list[dict[str, Any]] = []
    candidate_data.extend(asdict(candidate) for candidate in sorted(candidates, key=lambda item: item.path))
    counts = {
        "total": len(candidate_data),
        "verified": sum(item["provenance"] == "verified" for item in candidate_data),
        "unverified": sum(item["provenance"] == "unverified" for item in candidate_data),
        "missing": sum(item["provenance"] == "missing" for item in candidate_data),
        "python": sum(item["kind"] == "python" for item in candidate_data),
        "frontend": sum(item["kind"] == "frontend" for item in candidate_data),
        "e2e": sum(item["kind"] == "e2e" for item in candidate_data),
    }
    return {"root": str(root), "counts": counts, "candidates": candidate_data}


def _render_text(document: dict[str, Any]) -> str:
    counts = document["counts"]
    lines = [
        (
            "Candidates: "
            f"{counts['total']} (Python: {counts['python']}, "
            f"Frontend: {counts['frontend']}, E2E: {counts['e2e']})"
        ),
        (f"Provenance: {counts['verified']} verified, {counts['unverified']} unverified, {counts['missing']} missing"),
    ]
    lines.extend(
        (
            f"- {candidate['path']} | {','.join(candidate['task_ids'])} | "
            f"{','.join(candidate['signals'])} | {candidate['provenance']}"
        )
        for candidate in document["candidates"]
    )
    return "\n".join(lines)


def main() -> None:
    """Run the test-curation inventory command."""
    parser = argparse.ArgumentParser(prog="test-curation-inventory")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace root to inspect")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    args = parser.parse_args()
    document = inventory(args.root)
    if args.json:
        sys.stdout.write(f"{json.dumps(document, indent=2, sort_keys=True)}\n")
    else:
        sys.stdout.write(f"{_render_text(document)}\n")


if __name__ == "__main__":
    main()
