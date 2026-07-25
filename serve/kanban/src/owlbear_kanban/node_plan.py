"""Contained isolated storage for delivery-node plans."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import stat
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from ruamel.yaml.error import YAMLError

from owlbear_kanban.change import ChangeRevision, DeliveryNode
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    TransactionConflictError,
    TransactionParticipant,
    TransactionPathError,
)
from owlbear_kanban.yaml_rt import make_yaml

_NODE_ID_RE = re.compile(r"^DN-[0-9]{3}$")
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


@dataclass(frozen=True)
class StoredNodePlan:
    """One parsed node plan and its observed-content token."""

    node_id: str
    plan: Mapping[str, object]
    token: str


class NodePlanStore:
    """Prepare OCC-guarded participants for isolated node-plan records."""

    def __init__(self, revision: ChangeRevision) -> None:
        self._revision = revision

    def read(self, node_id: str) -> StoredNodePlan | None:
        """Read one plan and return its current content token when present."""
        self._validate_node(node_id)
        with self._root() as root_fd:
            current = self._read(root_fd, node_id)
        if current is None:
            return None
        content, plan = current
        return StoredNodePlan(node_id=node_id, plan=plan, token=hashlib.sha256(content).hexdigest())

    def prepare(
        self,
        node_id: str,
        plan: Mapping[str, object],
        expected_token: str | None = None,
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Prepare one contained create or token-guarded replacement participant."""
        self._validate_node(node_id)
        replacement = _serialize_plan(plan)
        with self._root() as root_fd:
            current = self._read(root_fd, node_id)
        relative_path = Path("plans") / f"{node_id}.yaml"
        if current is None:
            if expected_token is not None:
                raise TransactionConflictError
            return TransactionParticipant(self._revision.source_dir, relative_path, replacement)
        current_content, _current_plan = current
        current_token = hashlib.sha256(current_content).hexdigest()
        if current_content != replacement and expected_token != current_token:
            raise TransactionConflictError
        return ReplacementTransactionParticipant(
            self._revision.source_dir,
            relative_path,
            current_content,
            replacement,
        )

    def _validate_node(self, node_id: str) -> None:
        if not _NODE_ID_RE.fullmatch(node_id):
            raise TransactionPathError
        try:
            node = self._revision.resolve(node_id)
        except KeyError as exc:
            raise TransactionPathError from exc
        if not isinstance(node, DeliveryNode):
            raise TransactionPathError

    @contextlib.contextmanager
    def _root(self) -> Iterator[int]:
        try:
            root_fd = os.open(self._revision.source_dir, _DIRECTORY_OPEN_FLAGS)
        except OSError as exc:
            raise TransactionPathError from exc
        try:
            current = os.fstat(root_fd)
            if (current.st_dev, current.st_ino) != self._revision.source_identity:
                raise TransactionPathError
            yield root_fd
        finally:
            os.close(root_fd)

    @staticmethod
    def _read(root_fd: int, node_id: str) -> tuple[bytes, Mapping[str, object]] | None:
        try:
            plans_fd = os.open("plans", _DIRECTORY_OPEN_FLAGS, dir_fd=root_fd)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise TransactionPathError from exc
        try:
            try:
                plan_fd = os.open(f"{node_id}.yaml", _FILE_OPEN_FLAGS, dir_fd=plans_fd)
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise TransactionPathError from exc
            try:
                if not stat.S_ISREG(os.fstat(plan_fd).st_mode):
                    raise TransactionPathError
                with os.fdopen(plan_fd, "rb") as handle:
                    plan_fd = -1
                    content = handle.read()
            finally:
                if plan_fd >= 0:
                    os.close(plan_fd)
        finally:
            os.close(plans_fd)
        try:
            value = make_yaml().load(content.decode("utf-8"))
        except (UnicodeDecodeError, YAMLError) as exc:
            message = "node plan is not valid UTF-8 YAML"
            raise ValueError(message) from exc
        if not isinstance(value, Mapping):
            message = "node plan must be a YAML mapping"
            raise TypeError(message)
        return content, _json_mapping(value)


def _json_mapping(value: Mapping[object, object]) -> dict[str, object]:
    normalized = _json_value(value)
    if not isinstance(normalized, dict):
        raise TypeError
    json.dumps(normalized, allow_nan=False)
    return normalized


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            message = "node plan mapping keys must be strings"
            raise TypeError(message)
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    message = f"node plan value is not JSON-shaped: {type(value).__name__}"
    raise TypeError(message)


def _serialize_plan(plan: Mapping[str, object]) -> bytes:
    stream = StringIO()
    make_yaml(explicit_start=True).dump(_json_mapping(plan), stream)
    return stream.getvalue().encode("utf-8")


__all__ = ["NodePlanStore", "StoredNodePlan"]
