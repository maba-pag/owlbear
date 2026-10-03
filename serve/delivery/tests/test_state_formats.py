"""N02-A: persisted-format registry, capability gate, controller lock and strict frontier reads."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import pkgutil
import shutil
import subprocess
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Literal, get_args

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import owlbear_delivery
from owlbear_delivery import state_formats
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    DeliveryStateVersionError,
    close_delivery_application,
    load_delivery_application,
)
from owlbear_delivery.delivery_runtime import DeliveryFrontier, parse_delivery_frontier
from owlbear_delivery.delivery_state import parse_delivery_state_snapshot
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.state_formats import (
    FAMILIES,
    NESTED_MODELS,
    NON_PERSISTED_MODELS,
    RECORD_KINDS,
    RecordKind,
    classify_kind,
    record_tree_digest,
    scan_capability,
)
from owlbear_delivery.storage_io import ControllerFencedError, acquire_controller_lock

_GIT = resolve_git_executable()
_FIXTURES = Path(__file__).with_name("fixtures")
_GOLDEN = _FIXTURES / "state_formats" / "golden"
_FINGERPRINTS = _FIXTURES / "state_formats.json"
_ACCEPTED = frozenset({"current", "readable-legacy"})
_HOLDER = """
import sys
from pathlib import Path
from owlbear_delivery.storage_io import acquire_controller_lock
lock = acquire_controller_lock(Path(sys.argv[1]), exclusive=True)
print("held", flush=True)
sys.stdin.read()
"""


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        (_GIT, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _portfolio(tmp_path: Path) -> tuple[Path, DeliveryStartupConfig]:
    """Create a disposable primary checkout whose GitHub remote resolves to a local bare repository."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "State Formats Test")
    _git(repository, "config", "user.email", "state-formats@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    _git(repository, "fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    config_path = repository / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(), encoding="utf-8")
    return repository, config


def _write(root: Path, locator: str, payload: object) -> None:
    path = root / ".owlbear/delivery" / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _tree_listing(repository: Path) -> list[str]:
    root = repository / ".owlbear/delivery"
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


def _exclusive_available(repository: Path) -> bool:
    try:
        lock = acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True)
    except ControllerFencedError:
        return False
    lock.release()
    return True


# ---------------------------------------------------------------------------
# Registry hygiene and schema fingerprints (I2)
# ---------------------------------------------------------------------------


def _owner(owner: str) -> type[BaseModel]:
    module, name = owner.split(":")
    return getattr(importlib.import_module(module), name)


def _versioned_models(modules: list[types.ModuleType]) -> dict[str, type[BaseModel]]:
    models = {}
    for module in modules:
        for name, value in vars(module).items():
            if (
                isinstance(value, type)
                and issubclass(value, BaseModel)
                and value.__module__ == module.__name__
                and "schema_version" in value.model_fields
            ):
                models[f"{module.__name__}:{name}"] = value
    return models


def _delivery_modules() -> list[types.ModuleType]:
    return [
        importlib.import_module(f"owlbear_delivery.{info.name}")
        for info in pkgutil.iter_modules(owlbear_delivery.__path__)
    ]


def _unregistered(models: dict[str, type[BaseModel]]) -> list[str]:
    owners = {owner for kind in RECORD_KINDS for owner in kind.owners}
    return sorted(set(models) - owners - set(NESTED_MODELS) - NON_PERSISTED_MODELS)


def _reachable(model: type[BaseModel]) -> set[type[BaseModel]]:
    seen: set[type[BaseModel]] = set()
    pending: list[object] = [model]
    while pending:
        item = pending.pop()
        if isinstance(item, type) and issubclass(item, BaseModel):
            if item in seen:
                continue
            seen.add(item)
            pending.extend(field.annotation for field in item.model_fields.values())
        else:
            pending.extend(get_args(item))
    return seen


def test_every_versioned_delivery_model_is_registered_nested_or_non_persisted() -> None:
    models = _versioned_models(_delivery_modules())

    assert _unregistered(models) == []
    assert sorted((set(NESTED_MODELS) | NON_PERSISTED_MODELS) - set(models)) == []


def test_hygiene_rejects_an_unregistered_versioned_model() -> None:
    module = types.ModuleType("owlbear_delivery.synthetic_records")

    class SyntheticRecord(BaseModel):
        schema_version: Literal[1] = 1

    SyntheticRecord.__module__ = module.__name__
    module.SyntheticRecord = SyntheticRecord  # type: ignore[attr-defined]

    assert _unregistered(_versioned_models([module])) == ["owlbear_delivery.synthetic_records:SyntheticRecord"]


def test_nested_models_are_persisted_inside_their_family_and_non_persisted_models_are_not() -> None:
    reachable_by_family: dict[str, set[type[BaseModel]]] = {}
    for kind in RECORD_KINDS:
        for owner in kind.owners:
            reachable_by_family.setdefault(kind.family_id, set()).update(_reachable(_owner(owner)))
    every_reachable = set().union(*reachable_by_family.values())

    misplaced = [
        nested
        for nested, family_id in NESTED_MODELS.items()
        if not any(
            model is _owner(nested) or issubclass(model, _owner(nested))
            for model in reachable_by_family.get(family_id, set())
        )
    ]
    persisted = sorted(name for name in NON_PERSISTED_MODELS if _owner(name) in every_reachable)

    assert misplaced == []
    assert persisted == []


def test_registry_versions_match_owner_models() -> None:
    mismatches = []
    for kind in RECORD_KINDS:
        for owner in kind.owners:
            field = _owner(owner).model_fields.get("schema_version")
            declared = None if field is None else max(get_args(field.annotation))
            if declared != kind.current:
                mismatches.append((kind.kind_id, owner, declared, kind.current))

    assert mismatches == []
    assert set(FAMILIES) >= {"config", "frontier", "coordination", "snapshot", "claim_issuer", "locks"}


def _strip_documentation(value: object, *, names: bool = False) -> object:
    if isinstance(value, dict):
        return {
            key: _strip_documentation(item, names=key in {"properties", "$defs"} and not names)
            for key, item in value.items()
            if names or key not in {"title", "description"} or not isinstance(item, str)
        }
    if isinstance(value, list):
        return [_strip_documentation(item) for item in value]
    return value


def _schema_fingerprint(model: type[BaseModel]) -> str:
    schema = {
        "validation": model.model_json_schema(mode="validation"),
        "serialization": model.model_json_schema(mode="serialization"),
    }
    encoded = json.dumps(_strip_documentation(schema), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _kind_fingerprints(kind: RecordKind, models: dict[str, type[BaseModel]] | None = None) -> dict[str, str]:
    resolve = models.__getitem__ if models is not None else _owner
    return {owner: _schema_fingerprint(resolve(owner)) for owner in kind.owners}


def _fingerprint_drift(kind: RecordKind, fingerprints: dict[str, str], recorded: dict[str, object]) -> list[str]:
    """Return why a recorded schema no longer matches, naming the required version/upcast work."""
    drift = []
    recorded_version = recorded.get("version")
    if recorded_version != kind.current:
        legacy = {version for version, _owner in (*kind.read_upcasts, *kind.rewrites)}
        if recorded_version not in legacy:
            drift.append(
                f"{kind.kind_id}: version {recorded_version} -> {kind.current} without a registered "
                "read-upcast or rewrite of the recorded version"
            )
    elif recorded.get("fingerprints") != fingerprints:
        drift.append(f"{kind.kind_id}: owner schema changed without a schema_version bump")
    return drift


def test_registered_owner_schemas_match_their_versioned_fingerprints() -> None:
    recorded = json.loads(_FINGERPRINTS.read_text(encoding="utf-8"))
    drift = [
        message
        for kind in RECORD_KINDS
        if kind.owners
        for message in _fingerprint_drift(kind, _kind_fingerprints(kind), recorded.get(kind.kind_id, {}))
    ]

    assert sorted(recorded) == sorted(kind.kind_id for kind in RECORD_KINDS if kind.owners)
    assert drift == [], (
        "A persisted owner model changed. Bump its schema_version, register a read-upcast or fenced "
        "rewrite for the previous version, then update tests/fixtures/state_formats.json."
    )


def test_fingerprint_detects_an_unversioned_schema_change_and_an_unregistered_bump() -> None:
    class SyntheticV1(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        schema_version: Literal[1] = 1
        value: str

    class SyntheticChanged(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        schema_version: Literal[1] = 1
        value: int

    kind = RecordKind("synthetic", "synthetic", r"synthetic\.json", ("m:Synthetic",), "M", 1)
    recorded = {"version": 1, "fingerprints": _kind_fingerprints(kind, {"m:Synthetic": SyntheticV1})}
    bumped = RecordKind("synthetic", "synthetic", r"synthetic\.json", ("m:Synthetic",), "M", 2)
    upcast = RecordKind(
        "synthetic", "synthetic", r"synthetic\.json", ("m:Synthetic",), "M", 2, read_upcasts=((1, "m:up"),)
    )

    assert _fingerprint_drift(kind, _kind_fingerprints(kind, {"m:Synthetic": SyntheticV1}), recorded) == []
    assert _fingerprint_drift(kind, _kind_fingerprints(kind, {"m:Synthetic": SyntheticChanged}), recorded) == [
        "synthetic: owner schema changed without a schema_version bump"
    ]
    assert _fingerprint_drift(bumped, {}, recorded) == [
        "synthetic: version 1 -> 2 without a registered read-upcast or rewrite of the recorded version"
    ]
    assert _fingerprint_drift(upcast, {}, recorded) == []


def test_state_formats_is_a_stdlib_leaf() -> None:
    tree = ast.parse(Path(state_formats.__file__).read_text(encoding="utf-8"))
    imported = {
        module.split(".", 1)[0]
        for node in ast.walk(tree)
        for module in (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module]
            if isinstance(node, ast.ImportFrom) and node.module is not None
            else []
        )
    }

    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


# ---------------------------------------------------------------------------
# Golden D03 records (I2) and gate classification
# ---------------------------------------------------------------------------


def _golden_records() -> list[tuple[str, Path]]:
    return sorted((path.relative_to(_GOLDEN).as_posix(), path) for path in _GOLDEN.rglob("*") if path.is_file())


def _canonical(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


# Product writers per record kind; every other kind is written as sorted compact JSON plus newline.
_WRITER_FORMATS: dict[str, tuple[str, ...]] = {
    "action_receipt": ("canonical", "compact"),
    "claim_issuer": ("compact",),
    "recovery_invocation": ("compact",),
    "recovery_record": ("compact",),
    "retry_ledger": ("compact",),
    "retry_attempt": ("compact",),
    "retry_outcome": ("compact",),
    "retry_owner_result": ("compact",),
    "retry_repair_binding": ("compact",),
    **{kind.kind_id: ("indented",) for kind in RECORD_KINDS if kind.family_id.startswith("pull_request_")},
}
_SERIALIZERS = {
    "canonical": _canonical,
    "compact": lambda model: (model.model_dump_json() + "\n").encode(),
    "indented": lambda model: (model.model_dump_json(indent=2) + "\n").encode(),
}


def _owner_round_trip(kind: RecordKind, raw: bytes) -> bytes:
    if kind.kind_id == "frontier":
        return parse_delivery_frontier(raw)[1]
    if kind.kind_id == "snapshot":
        return parse_delivery_state_snapshot(raw).canonical_bytes()
    if kind.kind_id == "package_manifest":
        return _owner(kind.owners[0]).model_validate_json(raw, strict=True).canonical_bytes()
    if kind.envelope is not None:
        envelope = json.loads(raw)
        model = _owner(kind.owners[0]).model_validate_json(json.dumps(envelope[kind.envelope]), strict=True)
        rebuilt = {**envelope, kind.envelope: model.model_dump(mode="json")}
        return (json.dumps(rebuilt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    errors = []
    for owner in kind.owners:
        try:
            model = _owner(owner).model_validate_json(raw, strict=True)
        except ValidationError as exc:
            errors.append(exc)
            continue
        written = [_SERIALIZERS[name](model) for name in _WRITER_FORMATS.get(kind.kind_id, ("canonical",))]
        return raw if raw in written else written[0]
    raise errors[0]


def test_golden_d03_records_cover_every_readable_owner_kind() -> None:
    covered = {classify_kind(locator).kind_id for locator, _path in _golden_records()}  # type: ignore[union-attr]
    expected = {kind.kind_id for kind in RECORD_KINDS if kind.read and kind.owners}

    assert sorted(expected - covered) == sorted(_UNCOVERED_GOLDEN_KINDS)


@pytest.mark.parametrize(("locator", "path"), _golden_records(), ids=[locator for locator, _ in _golden_records()])
def test_golden_d03_record_round_trips_byte_identically_through_its_strict_owner(locator: str, path: Path) -> None:
    kind = classify_kind(locator)
    assert kind is not None
    raw = path.read_bytes()

    assert _owner_round_trip(kind, raw) == raw


def test_gate_classifies_every_golden_family_as_supported_without_writing(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(_GOLDEN, workspace / ".owlbear/delivery")
    digests = record_tree_digest(workspace)
    listing = _tree_listing(workspace)

    report = scan_capability(workspace)

    assert {record.status for record in report.records} <= _ACCEPTED
    assert {record.kind_id for record in report.records} == {
        classify_kind(locator).kind_id  # type: ignore[union-attr]
        for locator, _path in _golden_records()
    }
    assert report.refusals == ()
    assert record_tree_digest(workspace) == digests
    assert _tree_listing(workspace) == listing


def _golden_frontier() -> tuple[str, bytes]:
    return next(
        (locator, path.read_bytes()) for locator, path in _golden_records() if locator.endswith("/frontier.json")
    )


def test_schema_17_frontier_is_readable_legacy_and_reads_through_the_one_parser(tmp_path: Path) -> None:
    locator, raw = _golden_frontier()
    legacy = json.loads(raw)
    legacy["schema_version"] = 17
    for binding in legacy["bindings"]:
        binding.pop("retry_count", None)
        binding.pop("retry_fingerprint", None)
    legacy_raw = json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()
    _write(tmp_path, locator, legacy)

    report = scan_capability(tmp_path)
    frontier, canonical = parse_delivery_frontier(legacy_raw)

    assert [(record.status, record.version) for record in report.records] == [("readable-legacy", 17)]
    assert frontier.schema_version == 18
    assert all(binding.retry_count == 0 for binding in frontier.bindings)
    assert parse_delivery_frontier(canonical)[1] == canonical


def test_frontier_string_for_integer_is_rejected_by_the_strict_parser() -> None:
    _locator, raw = _golden_frontier()
    payload = json.loads(raw)
    payload["bindings"][0]["retry_count"] = str(payload["bindings"][0]["retry_count"])
    content = json.dumps(payload).encode()

    assert DeliveryFrontier.model_validate_json(content, strict=False) == parse_delivery_frontier(raw)[0]
    with pytest.raises(ValidationError, match="retry_count"):
        parse_delivery_frontier(content)


def test_frontier_number_for_datetime_is_rejected_by_the_strict_parser() -> None:
    _locator, raw = _golden_frontier()
    original = parse_delivery_frontier(raw)[0]
    lax_only = []
    for path in _datetime_paths(json.loads(raw)):
        payload = json.loads(raw)
        stamp = datetime.fromisoformat(_get_path(payload, path)).timestamp()
        _set_path(payload, path, int(stamp) if stamp.is_integer() else stamp)
        content = json.dumps(payload).encode()
        try:
            accepted = DeliveryFrontier.model_validate_json(content, strict=False) == original
        except ValidationError:
            accepted = False
        if accepted:
            lax_only.append(content)

    assert lax_only, "golden frontier must contain a persisted datetime field"
    for content in lax_only:
        with pytest.raises(ValidationError):
            parse_delivery_frontier(content)


def test_frontier_arrays_for_tuple_fields_are_accepted_by_strict_json_mode() -> None:
    _locator, raw = _golden_frontier()

    with pytest.raises(ValidationError):
        DeliveryFrontier.model_validate(json.loads(raw), strict=True)
    assert parse_delivery_frontier(raw)[1] == raw


def _datetime_paths(value: object, path: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    if isinstance(value, dict):
        return [found for key, item in sorted(value.items()) for found in _datetime_paths(item, (*path, key))]
    if isinstance(value, list):
        return [found for index, item in enumerate(value) for found in _datetime_paths(item, (*path, index))]
    if isinstance(value, str) and len(value) >= 20 and value[4] == "-" and value[10] == "T":
        return [path]
    return []


def _get_path(value: object, path: tuple[object, ...]) -> str:
    for key in path:
        value = value[key]  # type: ignore[index]
    return value  # type: ignore[return-value]


def _set_path(value: object, path: tuple[object, ...], replacement: object) -> None:
    for key in path[:-1]:
        value = value[key]  # type: ignore[index]
    value[path[-1]] = replacement  # type: ignore[index]


# ---------------------------------------------------------------------------
# Default loader gate (I1) and controller lock (I5)
# ---------------------------------------------------------------------------


_NEWER_STATE = {
    "frontier-19": ("runtime/changes/demo/frontier.json", {"schema_version": 19, "bindings": []}),
    "coordination-2": ("runtime/coordination/changes/demo.json", {"schema_version": 2, "change_id": "demo"}),
    "config-3": (
        "config.json",
        {
            "schema_version": 3,
            "remote": "origin",
            "target_branch": "main",
            "github_repository": "example/project",
        },
    ),
    "claim-issuer-2": ("runtime/changes/demo/claim-issuers/attempt-1.json", {"schema_version": 2, "window": None}),
    "format-1": ("runtime/format.json", {"format": 1}),
}


@pytest.mark.parametrize("case", sorted(_NEWER_STATE))
def test_loader_refuses_newer_state_before_remote_bootstrap(tmp_path: Path, case: str) -> None:
    repository, config = _portfolio(tmp_path)
    _git(
        repository, "config", f"url.{tmp_path / 'unreachable.git'}.insteadOf", "https://github.com/example/project.git"
    )
    locator, payload = _NEWER_STATE[case]
    _write(repository, locator, payload)
    digests = record_tree_digest(repository)

    with pytest.raises(DeliveryStateVersionError) as refusal:
        load_delivery_application(config, workspace_root=repository)

    assert refusal.value.code == "state-newer-than-controller"
    assert refusal.value.field == "state_version"
    assert refusal.value.locator == locator
    assert record_tree_digest(repository) == digests
    assert _exclusive_available(repository)


def test_loader_gate_runs_before_git_configuration_validation(tmp_path: Path) -> None:
    repository, config = _portfolio(tmp_path)
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")
    _write(repository, "runtime/changes/demo/frontier.json", {"schema_version": 19, "bindings": []})

    with pytest.raises(DeliveryStateVersionError) as refusal:
        load_delivery_application(config, workspace_root=repository)
    _write(repository, "runtime/changes/demo/frontier.json", {"schema_version": 18, "bindings": []})
    with pytest.raises(DeliveryApplicationLoadError) as git_failure:
        load_delivery_application(config, workspace_root=repository)

    assert refusal.value.code == "state-newer-than-controller"
    assert git_failure.value.field == "target_branch"
    assert not isinstance(git_failure.value, DeliveryStateVersionError)


@pytest.mark.parametrize(
    ("locator", "payload", "code"),
    [
        ("runtime/changes/demo/frontier.json", {"schema_version": 16, "bindings": []}, "state-version-unknown"),
        ("runtime/host.json", {"schema_version": 0}, "state-version-unknown"),
        ("runtime/migrations/proposal-1/journal.json", {"state": "applying"}, "state-migration-incomplete"),
        ("runtime/format.json", {"format": "one"}, "state-version-unknown"),
    ],
    ids=["frontier-16", "host-0", "migration-journal", "malformed-format-marker"],
)
def test_loader_refuses_unknown_versions_and_migration_journals(
    tmp_path: Path, locator: str, payload: object, code: str
) -> None:
    repository, config = _portfolio(tmp_path)
    _write(repository, locator, payload)
    digests = record_tree_digest(repository)

    with pytest.raises(DeliveryStateVersionError) as refusal:
        load_delivery_application(config, workspace_root=repository)

    assert refusal.value.code == code
    assert record_tree_digest(repository) == digests


def test_exclusive_holder_fences_the_default_loader_without_reading_or_writing(tmp_path: Path) -> None:
    repository, config = _portfolio(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    runtime_root.mkdir(parents=True)
    holder = subprocess.Popen(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _HOLDER, str(runtime_root)),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline() == "held\n"
        _write(repository, "runtime/changes/demo/frontier.json", {"schema_version": 19, "bindings": []})
        digests = record_tree_digest(repository)
        listing = _tree_listing(repository)

        with pytest.raises(DeliveryApplicationLoadError) as fenced:
            load_delivery_application(config, workspace_root=repository)

        assert fenced.value.code == "controller-fenced"
        assert not isinstance(fenced.value, DeliveryStateVersionError)
        assert record_tree_digest(repository) == digests
        assert _tree_listing(repository) == listing
    finally:
        assert holder.stdin is not None
        holder.stdin.close()
        holder.wait(timeout=10)


def test_running_controllers_share_the_lock_and_fence_exclusive_acquisition(tmp_path: Path) -> None:
    repository, config = _portfolio(tmp_path)

    first = load_delivery_application(config, workspace_root=repository)
    second = load_delivery_application(config, workspace_root=repository)
    probe = subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _HOLDER, str(repository / ".owlbear/delivery/runtime")),
        input="",
        capture_output=True,
        text=True,
        check=False,
    )

    assert probe.returncode != 0
    assert "ControllerFencedError" in probe.stderr
    assert not _exclusive_available(repository)
    close_delivery_application(first)
    assert not _exclusive_available(repository)
    close_delivery_application(second)
    assert _exclusive_available(repository)


def test_refused_load_releases_the_controller_lock(tmp_path: Path) -> None:
    repository, config = _portfolio(tmp_path)
    _write(repository, "runtime/coordination/changes/demo.json", {"schema_version": 2, "change_id": "demo"})

    with pytest.raises(DeliveryStateVersionError):
        load_delivery_application(config, workspace_root=repository)

    assert _exclusive_available(repository)
    assert (repository / ".owlbear/delivery/runtime/controller.lock").is_file()


def test_controller_lock_is_not_a_record_and_shared_mode_is_reentrant(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".owlbear/delivery/runtime"
    shared = acquire_controller_lock(runtime_root)
    other_shared = acquire_controller_lock(runtime_root)

    with pytest.raises(ControllerFencedError):
        acquire_controller_lock(runtime_root, exclusive=True)
    shared.release()
    other_shared.release()
    exclusive = acquire_controller_lock(runtime_root, exclusive=True)
    with pytest.raises(ControllerFencedError):
        acquire_controller_lock(runtime_root)
    exclusive.release()

    assert classify_kind("runtime/controller.lock").mutability == "L"  # type: ignore[union-attr]
    assert record_tree_digest(tmp_path) == {}
    assert scan_capability(tmp_path).refusals == ()


def test_gate_reports_unrecognized_and_unreadable_records_without_refusing(tmp_path: Path) -> None:
    _write(tmp_path, "runtime/unexpected/thing.json", {"schema_version": 99})
    path = tmp_path / ".owlbear/delivery/runtime/changes/demo/frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"{not json")
    path.with_name("admission.json").symlink_to(path)

    report = scan_capability(tmp_path)

    assert {(record.kind_id, record.status) for record in report.records} == {
        (None, "unrecognized"),
        ("frontier", "unreadable"),
        ("admission", "unreadable"),
    }
    assert report.refusals == ()


# Hand-authored tracked configuration has no product writer to round-trip; the remote-only snapshot family is
# covered by the read-upcast and newer-version tests in test_delivery_state.
_UNCOVERED_GOLDEN_KINDS: frozenset[str] = frozenset({"config", "host", "host_local", "snapshot"})
