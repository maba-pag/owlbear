"""Import a Spec Kit OwlBear task manifest into the native Kanban engine."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_kanban.engine import KanbanEngine

_FRONTMATTER_DELIMITER = "---"
_IMPORT_TAG_PREFIX = "spec-kit:"
_ERR_DEPENDENCY_CYCLE = "dependency cycle"
_ERR_DUPLICATE_DEPENDENCIES = "duplicate task dependencies"
_ERR_DUPLICATE_TASK_KEYS = "duplicate task keys"
_ERR_FRONTMATTER_MAPPING = "frontmatter is not a mapping"
_ERR_FRONTMATTER_MISSING = "missing YAML frontmatter"
_ERR_FRONTMATTER_UNTERMINATED = "unterminated YAML frontmatter"
_ERR_NO_REQUIREMENTS = "spec contains no REQ identifiers"
_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")
_REQUIREMENT_RE = re.compile(r"\bREQ-[0-9]{3,}\b")
_SUPPORTED_PROOF_BUNDLES = frozenset(
    {
        "skip",
        "existing",
        "smoke",
        "behavioral",
        "critical",
        "skip+challenge",
        "existing+challenge",
        "smoke+challenge",
        "behavioral+challenge",
        "critical+challenge",
        "skip+reader",
        "existing+reader",
        "smoke+reader",
        "behavioral+reader",
        "critical+reader",
        "skip+challenge+reader",
        "existing+challenge+reader",
        "smoke+challenge+reader",
        "behavioral+challenge+reader",
        "critical+challenge+reader",
    }
)


class SpecImportError(ValueError):
    """Raised when a Spec Kit handoff cannot be imported safely."""


class AggregateManifest(BaseModel):
    """Aggregate task projected from one Spec Kit feature."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    priority: Literal["low", "medium", "high"] = "medium"
    tags: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _reject_placeholders(self) -> AggregateManifest:
        _ensure_resolved_strings([self.title, *self.tags, *self.acceptance])
        return self


class TaskManifest(BaseModel):
    """One build-ready task in the Spec Kit handoff manifest."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^T[0-9]{3,}$")
    title: str = Field(min_length=1, max_length=200)
    requirement_ids: list[str] = Field(min_length=1)
    invariant_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"
    tags: list[str] = Field(default_factory=list)
    proof_bundle: str
    boundary: str = Field(min_length=1)
    allowed_replacement: str = Field(min_length=1)
    acceptance: list[str] = Field(min_length=1)

    @field_validator("depends_on")
    @classmethod
    def _reject_duplicate_dependencies(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise SpecImportError(_ERR_DUPLICATE_DEPENDENCIES)
        return value

    @field_validator("proof_bundle")
    @classmethod
    def _validate_proof_bundle(cls, value: str) -> str:
        if value not in _SUPPORTED_PROOF_BUNDLES:
            message = f"unsupported proof bundle: {value}"
            raise SpecImportError(message)
        return value

    @model_validator(mode="after")
    def _reject_placeholders(self) -> TaskManifest:
        _ensure_resolved_strings(
            [
                self.key,
                self.title,
                *self.requirement_ids,
                *self.invariant_ids,
                *self.tags,
                self.boundary,
                self.allowed_replacement,
                *self.acceptance,
            ]
        )
        return self


class OwlBearManifest(BaseModel):
    """Typed OwlBear section from Spec Kit tasks frontmatter."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    feature: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    spec: str = Field(min_length=1)
    plan: str = Field(min_length=1)
    aggregate: AggregateManifest
    tasks: list[TaskManifest] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_graph(self) -> OwlBearManifest:
        _ensure_resolved_strings([self.feature, self.spec, self.plan])
        keys = [task.key for task in self.tasks]
        if len(keys) != len(set(keys)):
            raise SpecImportError(_ERR_DUPLICATE_TASK_KEYS)
        known = set(keys)
        for task in self.tasks:
            missing = set(task.depends_on) - known
            if missing:
                message = f"{task.key} has unknown dependencies: {sorted(missing)}"
                raise SpecImportError(message)
            if task.key in task.depends_on:
                message = f"{task.key} depends on itself"
                raise SpecImportError(message)
        invariant_owners: dict[str, str] = {}
        for task in self.tasks:
            for invariant_id in task.invariant_ids:
                previous_owner = invariant_owners.get(invariant_id)
                if previous_owner is not None:
                    message = f"{invariant_id} has multiple owners: {previous_owner}, {task.key}"
                    raise SpecImportError(message)
                invariant_owners[invariant_id] = task.key
        _topological_order(self.tasks)
        return self


class ImportDocument(BaseModel):
    """Validated Spec Kit document metadata and task manifest."""

    model_config = ConfigDict(extra="forbid")

    tasks_file: Path
    feature_dir: Path
    spec_file: Path
    plan_file: Path
    manifest: OwlBearManifest


def _ensure_resolved_strings(values: list[str]) -> None:
    unresolved = next((value for value in values if _PLACEHOLDER_RE.search(value)), None)
    if unresolved is not None:
        message = f"unresolved template placeholder: {unresolved}"
        raise SpecImportError(message)


def _topological_order(tasks: list[TaskManifest]) -> list[str]:
    dependencies = {task.key: set(task.depends_on) for task in tasks}
    dependents: dict[str, set[str]] = defaultdict(set)
    for key, task_dependencies in dependencies.items():
        for dependency in task_dependencies:
            dependents[dependency].add(key)

    ready = deque(sorted(key for key, task_dependencies in dependencies.items() if not task_dependencies))
    ordered: list[str] = []
    while ready:
        key = ready.popleft()
        ordered.append(key)
        for dependent in sorted(dependents[key]):
            dependencies[dependent].remove(key)
            if not dependencies[dependent]:
                ready.append(dependent)

    if len(ordered) != len(tasks):
        raise SpecImportError(_ERR_DEPENDENCY_CYCLE)
    return ordered


def _read_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        raise SpecImportError(_ERR_FRONTMATTER_MISSING)
    try:
        end_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == _FRONTMATTER_DELIMITER
        )
    except StopIteration as exc:
        raise SpecImportError(_ERR_FRONTMATTER_UNTERMINATED) from exc
    payload = yaml.safe_load("\n".join(lines[1:end_index]))
    if not isinstance(payload, dict):
        raise SpecImportError(_ERR_FRONTMATTER_MAPPING)
    return payload


def load_import_document(tasks_file: Path) -> ImportDocument:
    """Load and validate one Spec Kit tasks file and linked artifacts."""
    resolved_tasks = tasks_file.resolve()
    if not resolved_tasks.is_file():
        message = f"tasks file does not exist: {resolved_tasks}"
        raise SpecImportError(message)
    frontmatter = _read_frontmatter(resolved_tasks)
    raw_manifest = frontmatter.get("owlbear")
    manifest = OwlBearManifest.model_validate(raw_manifest)
    feature_dir = resolved_tasks.parent
    spec_file = (feature_dir / manifest.spec).resolve()
    plan_file = (feature_dir / manifest.plan).resolve()
    for label, path in (("spec", spec_file), ("plan", plan_file)):
        if feature_dir not in path.parents or not path.is_file():
            message = f"{label} file must exist inside the feature directory: {path}"
            raise SpecImportError(message)
            _validate_requirement_coverage(spec_file, manifest)
    return ImportDocument(
        tasks_file=resolved_tasks,
        feature_dir=feature_dir,
        spec_file=spec_file,
        plan_file=plan_file,
        manifest=manifest,
    )


def _validate_requirement_coverage(spec_file: Path, manifest: OwlBearManifest) -> None:
    spec_requirements = set(_REQUIREMENT_RE.findall(spec_file.read_text(encoding="utf-8")))
    if not spec_requirements:
        raise SpecImportError(_ERR_NO_REQUIREMENTS)
    task_requirements = {requirement_id for task in manifest.tasks for requirement_id in task.requirement_ids}
    missing = spec_requirements - task_requirements
    unknown = task_requirements - spec_requirements
    if missing:
        message = f"requirements missing from tasks: {sorted(missing)}"
        raise SpecImportError(message)
    if unknown:
        message = f"tasks reference unknown requirements: {sorted(unknown)}"
        raise SpecImportError(message)


def _import_tag(feature: str) -> str:
    return f"{_IMPORT_TAG_PREFIX}{feature}"


def build_import_preview(document: ImportDocument) -> dict[str, object]:
    """Return deterministic dry-run output for a validated manifest."""
    manifest = document.manifest
    task_by_key = {task.key: task for task in manifest.tasks}
    ordered_keys = _topological_order(manifest.tasks)
    import_tag = _import_tag(manifest.feature)
    return {
        "schema_version": 1,
        "feature": manifest.feature,
        "source": {
            "tasks": str(document.tasks_file),
            "spec": str(document.spec_file),
            "plan": str(document.plan_file),
        },
        "import_tag": import_tag,
        "tasks": [
            {
                "key": key,
                "title": task_by_key[key].title,
                "depends_on": task_by_key[key].depends_on,
                "requirements": task_by_key[key].requirement_ids,
                "invariants": task_by_key[key].invariant_ids,
                "boundary": task_by_key[key].boundary,
                "acceptance": task_by_key[key].acceptance,
            }
            for key in ordered_keys
        ],
        "aggregate": {
            "title": manifest.aggregate.title,
            "depends_on": ordered_keys,
            "acceptance": manifest.aggregate.acceptance,
        },
    }


def _task_body(document: ImportDocument, task: TaskManifest) -> str:
    relative_spec = document.spec_file.relative_to(document.feature_dir.parent.parent)
    relative_plan = document.plan_file.relative_to(document.feature_dir.parent.parent)
    requirements = ", ".join(task.requirement_ids)
    invariants = ", ".join(task.invariant_ids) or "none"
    return (
        f"Spec: `{relative_spec.as_posix()}`\n"
        f"Plan: `{relative_plan.as_posix()}`\n\n"
        "## Scope\n"
        f"Requirements: {requirements}\n"
        f"Invariants: {invariants}\n\n"
        "## Proof\n"
        f"Boundary: {task.boundary}\n"
        f"Allowed replacement: {task.allowed_replacement}\n"
    )


def _aggregate_body(document: ImportDocument) -> str:
    relative_spec = document.spec_file.relative_to(document.feature_dir.parent.parent)
    relative_plan = document.plan_file.relative_to(document.feature_dir.parent.parent)
    return (
        f"Spec: `{relative_spec.as_posix()}`\n"
        f"Plan: `{relative_plan.as_posix()}`\n\n"
        "## Aggregate Intent\n"
        f"Feature: {document.manifest.feature}\n"
    )


def apply_import(document: ImportDocument, kanban_dir: Path) -> dict[str, object]:
    """Create native Kanban tasks from a fully validated manifest."""
    engine = KanbanEngine(kanban_dir.resolve())
    manifest = document.manifest
    import_tag = _import_tag(manifest.feature)
    existing = engine.list_tasks(tag=import_tag, limit=1)
    if existing:
        message = f"feature already imported: {manifest.feature}"
        raise SpecImportError(message)

    task_by_key = {task.key: task for task in manifest.tasks}
    ordered_keys = _topological_order(manifest.tasks)
    created_ids: dict[str, int] = {}
    created_task_ids: list[int] = []
    try:
        for key in ordered_keys:
            task = task_by_key[key]
            created = engine.create_task(
                task.title,
                body=_task_body(document, task),
                tags=list(dict.fromkeys([*task.tags, import_tag, f"spec-task:{key}"])),
                priority=task.priority,
                status="build",
                depends_on=[created_ids[dependency] for dependency in task.depends_on],
                ac=task.acceptance,
                proof_bundle=task.proof_bundle,
            )
            created_ids[key] = created.id
            created_task_ids.append(created.id)

        aggregate = engine.create_task(
            manifest.aggregate.title,
            body=_aggregate_body(document),
            tags=list(dict.fromkeys([*manifest.aggregate.tags, import_tag, "spec-aggregate"])),
            priority=manifest.aggregate.priority,
            status="collect",
            depends_on=[created_ids[key] for key in ordered_keys],
            ac=manifest.aggregate.acceptance,
            proof_bundle="critical",
        )
        created_task_ids.append(aggregate.id)
        for task_id in created_ids.values():
            engine.edit_task(str(task_id), parent=aggregate.id, source="spec-import")
    except Exception:
        _rollback_created_tasks(engine, created_task_ids)
        raise

    return {
        "feature": manifest.feature,
        "import_tag": import_tag,
        "aggregate_id": aggregate.id,
        "task_ids": created_ids,
    }


def _rollback_created_tasks(engine: KanbanEngine, task_ids: list[int]) -> None:
    for task_id in reversed(task_ids):
        for path in engine.tasks_dir.glob(f"{task_id}-*.md"):
            path.unlink()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks_file", type=Path, help="Spec Kit tasks.md with OwlBear manifest")
    parser.add_argument(
        "--kanban-dir",
        type=Path,
        default=Path(".owlbear/kanban"),
        help="OwlBear Kanban directory (default: .owlbear/kanban)",
    )
    parser.add_argument("--apply", action="store_true", help="Create tasks; default is dry-run JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for dry-run and explicit task import."""
    args = _build_parser().parse_args(argv)
    try:
        document = load_import_document(args.tasks_file)
        result = apply_import(document, args.kanban_dir) if args.apply else build_import_preview(document)
    except Exception as exc:  # noqa: BLE001
        json.dump({"ok": False, "error": str(exc)}, sys.stderr)
        sys.stderr.write("\n")
        return 1
    json.dump({"ok": True, "applied": bool(args.apply), "result": result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

