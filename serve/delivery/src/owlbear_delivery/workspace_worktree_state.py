"""No-follow worktree reads, managed-index validation and private restoration staging."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import secrets
import stat
from contextlib import suppress
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery.recovery import (
    digest,
)
from owlbear_delivery.runtime_transaction import (
    contained_directory,
    read_contained,
)
from owlbear_delivery.workspace_models import (
    _ASCII_DIGIT_MAX,
    _ASCII_DIGIT_MIN,
    _CACHE_TREE_COUNT_FIELDS,
    _GIT_MODE_GITLINK,
    _GIT_MODE_SYMLINK,
    _GIT_MODE_TREE,
    _INDEX_OBJECT_ID_LENGTHS,
    _INDEX_PATH_LENGTH_MASK,
    _INDEX_RECORD_FIELD_COUNT,
    _MAX_PRESERVED_FILE_BYTES,
    _MAX_PRESERVED_TOTAL_BYTES,
    _MAX_RESTORATION_STAGING_ATTEMPTS,
    _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH,
    _PRESERVATION_FILE_IDENTITY_FIELDS,
    _PRIVATE_PATH_MARKERS,
    _RESTORATION_RECORD_TEMPORARY_MODE,
    _RESTORATION_RECORD_TEMPORARY_PATTERN,
    _RESTORATION_STAGE_PATTERN,
    ChangeCoordination,
    PreservationFenceError,
    PreservationRejectedError,
    WorktreePreservationReceipt,
    _contains_private_index_metadata,
    _directory_identity_tuple,
    _ManagedIndexIdentity,
    _open_worktree_parent,
    _path_is_contained,
    _preservation_file_identity,
    _preservation_temporary_name,
    _PreservedPathState,
    _reject_symlink_ancestors,
    _same_preservation_identity,
    _same_staging_identity,
    _validate_relative_preservation_path,
    _WorktreeRestorationContext,
    _WorktreeRestorationStage,
    _WorktreeRestorationStageCandidate,
)

if TYPE_CHECKING:
    import subprocess


class _WorktreeStateMixin:
    """No-follow worktree reads, managed-index validation and private restoration staging."""

    def _preservation_git(
        self,
        *arguments: str,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        return self._run_git(
            "--no-optional-locks",
            *arguments,
            cwd=cwd,
            check=check,
            environment=environment,
        )

    def _resolve_managed_index(self, worktree: Path) -> _ManagedIndexIdentity:
        self._require_preservation_environment()
        index = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "index",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        administration = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--absolute-git-dir",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        common = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        repository_common = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                cwd=self._repository,
            )
            .stdout.decode()
            .strip()
        )
        if (
            not index.is_absolute()
            or not administration.is_absolute()
            or not common.is_absolute()
            or not repository_common.is_absolute()
            or index.parent != administration
            or common != common.resolve()
            or administration != administration.resolve()
            or index != index.resolve()
            or repository_common != repository_common.resolve()
            or common != repository_common
            or not _path_is_contained(common, administration)
        ):
            msg = "Git resolved an unexpected worktree administration path"
            raise PreservationRejectedError(msg)
        _reject_symlink_ancestors(index)
        _reject_symlink_ancestors(administration)
        _reject_symlink_ancestors(common)
        lock = index.with_name(f"{index.name}.lock")
        try:
            lock.lstat()
        except FileNotFoundError:
            pass
        else:
            msg = "managed Git index is locked"
            raise PreservationRejectedError(msg)
        try:
            metadata = index.lstat()
        except FileNotFoundError as exc:
            msg = "managed Git index is missing"
            raise PreservationRejectedError(msg) from exc
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            msg = "managed Git index is not a single regular file"
            raise PreservationRejectedError(msg)
        return _ManagedIndexIdentity(
            path=index,
            administration=administration,
            common_directory=common,
            device=metadata.st_dev,
            inode=metadata.st_ino,
            mode=stat.S_IMODE(metadata.st_mode),
            link_count=metadata.st_nlink,
        )

    @staticmethod
    def _read_managed_index(identity: _ManagedIndexIdentity) -> bytes:
        descriptor = os.open(identity.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or (before.st_dev, before.st_ino) != (identity.device, identity.inode)
                or before.st_size > _MAX_PRESERVED_TOTAL_BYTES
            ):
                msg = "managed Git index metadata changed"
                raise PreservationRejectedError(msg)
            content = os.read(descriptor, before.st_size + 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if len(content) != before.st_size or (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            msg = "managed Git index changed while it was read"
            raise PreservationFenceError(msg)
        return content

    def _verify_index_metadata(
        self,
        identity: _ManagedIndexIdentity,
        expected_digest: str,
        metadata: tuple[int, int, int, int],
    ) -> bytes:
        if (identity.mode, identity.device, identity.inode, identity.link_count) != metadata:
            msg = "managed Git index identity changed"
            raise PreservationFenceError(msg)
        content = self._read_managed_index(identity)
        if hashlib.sha256(content).hexdigest() != expected_digest:
            msg = "managed Git index digest changed"
            raise PreservationFenceError(msg)
        return content

    def _index_entries(self, worktree: Path) -> tuple[tuple[str, int, int], ...]:
        return tuple((path, mode, stage) for path, mode, stage, _object_id in self._index_entry_records(worktree))

    def _index_entry_records(self, worktree: Path) -> tuple[tuple[str, int, int, str], ...]:
        output = self._preservation_git("ls-files", "--sparse", "--stage", "-z", cwd=worktree).stdout
        result: list[tuple[str, int, int, str]] = []
        for record in output.split(b"\0"):
            if not record:
                continue
            header, separator, raw_path = record.partition(b"\t")
            fields = header.split()
            if (
                not separator
                or len(fields) != _INDEX_RECORD_FIELD_COUNT
                or len(fields[1]) not in _INDEX_OBJECT_ID_LENGTHS
            ):
                msg = "managed index inventory is malformed"
                raise PreservationRejectedError(msg)
            try:
                mode = int(fields[0], 8)
                stage = int(fields[2])
                object_id = fields[1].decode("ascii")
                path = os.fsdecode(raw_path)
            except (UnicodeError, ValueError) as exc:
                msg = "managed index inventory is not canonical"
                raise PreservationRejectedError(msg) from exc
            if any(character not in "0123456789abcdef" for character in object_id):
                raise PreservationRejectedError("managed index inventory is not canonical")  # noqa: EM101, TRY003
            result.append((path, mode, stage, object_id))
        return tuple(result)

    def _head_entries(self, worktree: Path, head: str) -> tuple[tuple[str, int, str], ...]:
        output = self._preservation_git("ls-tree", "-r", "-z", "--full-tree", head, cwd=worktree).stdout
        result: list[tuple[str, int, str]] = []
        for record in output.split(b"\0"):
            if not record:
                continue
            header, separator, raw_path = record.partition(b"\t")
            fields = header.split()
            if (
                not separator
                or len(fields) != _INDEX_RECORD_FIELD_COUNT
                or len(fields[2]) not in _INDEX_OBJECT_ID_LENGTHS
            ):
                raise PreservationRejectedError("reviewed HEAD inventory is malformed")  # noqa: EM101, TRY003
            try:
                mode = int(fields[0], 8)
                object_id = fields[2].decode("ascii")
                path = os.fsdecode(raw_path)
            except (UnicodeError, ValueError) as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "reviewed HEAD inventory is not canonical"  # noqa: EM101
                ) from exc
            if fields[1] not in {b"blob", b"commit"} or any(
                character not in "0123456789abcdef" for character in object_id
            ):
                raise PreservationRejectedError("reviewed HEAD inventory is not canonical")  # noqa: EM101, TRY003
            result.append((path, mode, object_id))
        return tuple(result)

    @staticmethod
    def _validate_index_entries(entries: tuple[tuple[str, int, int], ...]) -> None:
        for path, mode, stage in entries:
            if stage != 0:
                msg = "unmerged index entries require containment"
                raise PreservationRejectedError(msg)
            if mode in {_GIT_MODE_GITLINK, _GIT_MODE_TREE}:
                msg = "submodule or sparse-index entries require containment"
                raise PreservationRejectedError(msg)
            if mode not in {0o100644, 0o100755, 0o120000}:
                msg = "unsupported managed index entry type"
                raise PreservationRejectedError(msg)
            _validate_relative_preservation_path(path)

    @staticmethod
    def _skip_legacy_index_entries(content: bytes, entry_count: int, checksum_start: int) -> int:
        cursor = 12
        for _index in range(entry_count):
            if cursor + 62 > checksum_start:
                msg = "managed index entry table is truncated"
                raise PreservationRejectedError(msg)
            entry_start = cursor
            flags = int.from_bytes(content[cursor + 60 : cursor + 62], "big")
            cursor += 62
            if flags & _INDEX_PATH_LENGTH_MASK < _INDEX_PATH_LENGTH_MASK:
                path_end = cursor + (flags & _INDEX_PATH_LENGTH_MASK)
                if path_end >= checksum_start or content[path_end] != 0:
                    msg = "managed index entry path is malformed"
                    raise PreservationRejectedError(msg)
                cursor = path_end + 1
            else:
                try:
                    path_end = content.index(b"\0", cursor, checksum_start)
                except ValueError as exc:
                    msg = "managed index entry path is unterminated"
                    raise PreservationRejectedError(msg) from exc
                cursor = path_end + 1
            cursor = entry_start + ((cursor - entry_start + 7) & ~7)
        return cursor

    @staticmethod
    def _validate_legacy_index_extension_table(content: bytes, cursor: int, checksum_start: int) -> None:
        known = {b"TREE", b"REUC", b"EOIE", b"IEOT"}
        while cursor < checksum_start:
            if cursor + 8 > checksum_start:
                msg = "managed index extension header is truncated"
                raise PreservationRejectedError(msg)
            extension = content[cursor : cursor + 4]
            size = int.from_bytes(content[cursor + 4 : cursor + 8], "big")
            cursor += 8
            if extension not in known or cursor + size > checksum_start:
                msg = "managed index extension requires containment"
                raise PreservationRejectedError(msg)
            extension_content = content[cursor : cursor + size]
            if _contains_private_index_metadata(extension_content):
                msg = "managed index extension contains private metadata"
                raise PreservationRejectedError(msg)
            cursor += size
        if cursor != checksum_start:
            msg = "managed index extension table is malformed"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_index_tree_extension(  # noqa: C901 - parse each cache-tree record and subtree boundary explicitly.
        content: bytes,
    ) -> tuple[str, ...]:
        """Validate cache-tree records instead of treating extension bytes as trusted paths."""
        if not content:
            raise PreservationRejectedError("managed Git cache-tree extension is empty")  # noqa: EM101, TRY003
        cursor = 0
        paths: list[str] = []
        pending_nodes = [1]
        while pending_nodes:
            if pending_nodes[-1] == 0:
                pending_nodes.pop()
                continue
            pending_nodes[-1] -= 1
            try:
                path_end = content.index(b"\0", cursor)
            except ValueError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree path is unterminated"  # noqa: EM101
                ) from exc
            raw_path = content[cursor:path_end]
            cursor = path_end + 1
            try:
                path = os.fsdecode(raw_path)
            except UnicodeError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree path is not canonical"  # noqa: EM101
                ) from exc
            if path:
                _validate_relative_preservation_path(path)
                paths.append(path)
            try:
                line_end = content.index(b"\n", cursor)
            except ValueError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree record is unterminated"  # noqa: EM101
                ) from exc
            counts = content[cursor:line_end].split(b" ")
            if len(counts) != _CACHE_TREE_COUNT_FIELDS or any(
                not item
                or (item.startswith(b"-") and len(item) == 1)
                or any(byte < _ASCII_DIGIT_MIN or byte > _ASCII_DIGIT_MAX for byte in item.removeprefix(b"-"))
                for item in counts
            ):
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree counts are malformed"  # noqa: EM101
                )
            entry_count = int(counts[0])
            subtree_count = int(counts[1])
            if entry_count < -1 or subtree_count < 0:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree counts are malformed"  # noqa: EM101
                )
            cursor = line_end + 1
            if entry_count >= 0:
                if cursor + 20 > len(content):
                    raise PreservationRejectedError(  # noqa: TRY003
                        "managed Git cache-tree object is truncated"  # noqa: EM101
                    )
                cursor += 20
            pending_nodes.append(subtree_count)
        if cursor != len(content):
            raise PreservationRejectedError(  # noqa: TRY003
                "managed Git cache-tree subtree count is malformed"  # noqa: EM101
            )
        return tuple(paths)

    @staticmethod
    def _validate_index_path_names(paths: tuple[str, ...]) -> None:
        """Apply conservative index-name screening only after the exact index boundary is trusted."""
        for path in paths:
            _validate_relative_preservation_path(path)
            components = {component.casefold() for component in PurePosixPath(path).parts}
            if any(
                component in _PRIVATE_PATH_MARKERS
                or component.startswith(
                    (
                        ".env.",
                        "id_rsa.",
                        "id_ed25519.",
                        "id_ecdsa.",
                        "credential.",
                        "credentials.",
                        "password.",
                        "passwd.",
                        "private.",
                        "secret.",
                        "secrets.",
                        "token.",
                    )
                )
                for component in components
            ):
                raise PreservationRejectedError(  # noqa: TRY003
                    "private or secret-like index path requires containment"  # noqa: EM101
                )

    @staticmethod
    def _preservation_status_paths(status: bytes) -> tuple[str, ...]:
        if status and not status.endswith(b"\0"):
            msg = "Git returned an unterminated worktree status"
            raise PreservationRejectedError(msg)
        paths: set[str] = set()
        records = status.split(b"\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                msg = "Git returned a malformed worktree status"
                raise PreservationRejectedError(msg)
            code = record[:2].decode("ascii", errors="strict")
            if code == "!!":
                msg = "ignored worktree content requires containment"
                raise PreservationRejectedError(msg)
                continue
            paths.add(os.fsdecode(record[3:]))
            if "R" in code or "C" in code:
                if index >= len(records) or not records[index]:
                    msg = "Git returned an incomplete rename status"
                    raise PreservationRejectedError(msg)
                paths.add(os.fsdecode(records[index]))
                index += 1
        return tuple(sorted(paths))

    @staticmethod
    def _ignored_inventory_paths(status: bytes) -> frozenset[str]:
        """Return Git's collapsed ignored paths; ignored directories keep their trailing slash."""
        if status and not status.endswith(b"\0"):
            msg = "Git returned an unterminated worktree status"
            raise PreservationRejectedError(msg)
        records = status.split(b"\0")
        index = 0
        ignored: set[str] = set()
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                msg = "Git returned a malformed worktree status"
                raise PreservationRejectedError(msg)
            code = record[:2].decode("ascii", errors="strict")
            if code == "!!":
                ignored.add(os.fsdecode(record[3:]))
                continue
            if "R" in code or "C" in code:
                if index >= len(records) or not records[index]:
                    msg = "Git returned an incomplete rename status"
                    raise PreservationRejectedError(msg)
                index += 1
        return frozenset(ignored)

    @staticmethod
    def _validate_private_paths(paths: tuple[str, ...]) -> None:
        for path in paths:
            _validate_relative_preservation_path(path)
            components = {component.casefold() for component in PurePosixPath(path).parts}
            if any(
                component in _PRIVATE_PATH_MARKERS
                or component.startswith(
                    (
                        "private.",
                        "private-",
                        "private_",
                        ".env.",
                        "id_rsa.",
                        "id_ed25519.",
                        "id_ecdsa.",
                    )
                )
                or any(marker in component for marker in ("credential", "password", "secret", "token"))
                for component in components
            ):
                msg = "private or secret-like path requires containment"
                raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_private_content(content: bytes) -> None:
        """Reject high-confidence credential material before private storage."""
        lowered = content.lower()
        markers = (
            b"-----begin ",
            b"private key-----",
            b"aws_secret_access_key=",
            b"aws_access_key_id=",
            b"github_pat_",
            b"ghp_",
            b"xoxb-",
            b"xoxp-",
        )
        if any(marker in lowered for marker in markers):
            msg = "private or secret-like content requires containment"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_preservation_path(worktree: Path, path: str) -> None:
        _validate_relative_preservation_path(path)
        candidate = worktree / PurePosixPath(path)
        current = worktree
        for component in PurePosixPath(path).parts[:-1]:
            current = current / component
            try:
                metadata = current.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    msg = "external symlink traversal is not permitted"
                    raise PreservationRejectedError(msg)
                if not stat.S_ISDIR(metadata.st_mode):
                    msg = "worktree path ancestor is not a directory"
                    raise PreservationRejectedError(msg)
            except FileNotFoundError:
                break
        if candidate.is_dir() and not candidate.is_symlink():
            msg = "directory paths require bounded file inventory"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _verify_worktree_ancestors(
        ancestors: tuple[tuple[Path, tuple[int, int, int]], ...],
        path: str,
    ) -> None:
        message = f"worktree ancestor changed while reading: {path}"
        for ancestor, expected in ancestors:
            try:
                current = ancestor.lstat()
            except FileNotFoundError as exc:
                raise PreservationFenceError(message) from exc
            if (
                stat.S_ISLNK(current.st_mode)
                or not stat.S_ISDIR(current.st_mode)
                or _directory_identity_tuple(current) != expected
            ):
                raise PreservationFenceError(message)

    @staticmethod
    def _read_worktree_leaf(
        parent_fd: int,
        name: str,
        path: str,
        metadata: os.stat_result,
        expected_staging_identity: tuple[int, int, int, int, int, int, int, int] | None,
    ) -> _PreservedPathState:
        changed_message = f"worktree path changed while it was read: {path}"
        identity = _preservation_file_identity(metadata)
        mode = stat.S_IMODE(metadata.st_mode)
        containment_message = "special or multiply-linked worktree path requires containment"
        size_message = "worktree path exceeds the per-file preservation limit"
        if stat.S_ISLNK(metadata.st_mode):
            content = os.fsencode(os.readlink(name, dir_fd=parent_fd))
            after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not _same_preservation_identity(_preservation_file_identity(after), identity):
                raise PreservationFenceError(changed_message)
            return _PreservedPathState("symlink", content, 0o777, identity)
        if not stat.S_ISREG(metadata.st_mode):
            raise PreservationRejectedError(containment_message)
        if metadata.st_nlink != 1 and (
            expected_staging_identity is None or not _same_staging_identity(expected_staging_identity, identity)
        ):
            raise PreservationRejectedError(containment_message)
        if metadata.st_size > _MAX_PRESERVED_FILE_BYTES:
            raise PreservationRejectedError(size_message)
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent_fd,
            )
        except FileNotFoundError as exc:
            raise PreservationFenceError(changed_message) from exc
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise PreservationFenceError(changed_message) from exc
            raise
        try:
            content = os.read(descriptor, metadata.st_size + 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if len(content) != metadata.st_size or not _same_preservation_identity(
            _preservation_file_identity(after), identity
        ):
            raise PreservationFenceError(changed_message)
        return _PreservedPathState("regular", content, mode, identity)

    def _read_head_state(self, worktree: Path, head: str, path: str) -> _PreservedPathState:
        output = self._preservation_git("ls-tree", "-z", head, "--", path, cwd=worktree).stdout
        if not output:
            return _PreservedPathState("absent", None, None)
        record = output.rstrip(b"\0")
        header, separator, raw_path = record.partition(b"\t")
        fields = header.split()
        if not separator or len(fields) != _INDEX_RECORD_FIELD_COUNT or os.fsdecode(raw_path) != path:
            msg = "HEAD path inventory is malformed"
            raise PreservationRejectedError(msg)
        try:
            mode = int(fields[0], 8)
            object_id = fields[2].decode("ascii")
        except (UnicodeError, ValueError) as exc:
            msg = "HEAD path inventory is malformed"
            raise PreservationRejectedError(msg) from exc
        if mode == _GIT_MODE_GITLINK:
            msg = "submodule path requires containment"
            raise PreservationRejectedError(msg)
        if mode not in {0o100644, 0o100755, 0o120000}:
            msg = "HEAD path has an unsupported type"
            raise PreservationRejectedError(msg)
        content = self._preservation_git("cat-file", "blob", object_id, cwd=worktree).stdout
        if mode == _GIT_MODE_SYMLINK:
            return _PreservedPathState("symlink", content, 0o777)
        return _PreservedPathState("regular", content, stat.S_IMODE(mode))

    @staticmethod
    def _state_digest(state: _PreservedPathState) -> str | None:
        return None if state.content is None else hashlib.sha256(state.content).hexdigest()

    @staticmethod
    def _read_private_staging_state(
        root_fd: int,
        relative: Path | None,
    ) -> _PreservedPathState | None:
        """Read an owner-private stage without following links or trusting its name."""
        if relative is None:
            return None
        with contained_directory(root_fd, relative.parent) as parent_fd:
            try:
                metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return None
            identity = _preservation_file_identity(metadata)
            if stat.S_ISLNK(metadata.st_mode):
                content = os.fsencode(os.readlink(relative.name, dir_fd=parent_fd))
                after = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
                if not _same_staging_identity(_preservation_file_identity(after), identity):
                    msg = "private restoration staging changed while it was read"
                    raise PreservationFenceError(msg)
                return _PreservedPathState("symlink", content, 0o777, identity)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink < 1:
                msg = "private restoration staging is not a regular file"
                raise PreservationRejectedError(msg)
            descriptor = os.open(
                relative.name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent_fd,
            )
            try:
                observed = os.fstat(descriptor)
                if not _same_staging_identity(_preservation_file_identity(observed), identity):
                    msg = "private restoration staging changed while it was opened"
                    raise PreservationFenceError(msg)
                with os.fdopen(descriptor, "rb", closefd=False) as handle:
                    content = handle.read(_MAX_PRESERVED_FILE_BYTES + 1)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            if len(content) > _MAX_PRESERVED_FILE_BYTES:
                msg = "private restoration staging exceeds its bound"
                raise PreservationRejectedError(msg)
            if not _same_staging_identity(_preservation_file_identity(after), identity):
                msg = "private restoration staging changed while it was read"
                raise PreservationFenceError(msg)
            return _PreservedPathState("regular", content, stat.S_IMODE(metadata.st_mode), identity)

    @staticmethod
    def _private_staging_artifact_size(entry: os.DirEntry[str], parent_fd: int) -> int:
        is_stage = _RESTORATION_STAGE_PATTERN.fullmatch(entry.name) is not None
        is_temporary = _RESTORATION_RECORD_TEMPORARY_PATTERN.fullmatch(entry.name) is not None
        if not is_stage and not is_temporary:
            msg = "private restoration staging inventory is malformed"
            raise PreservationFenceError(msg)
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as exc:
            msg = "private restoration staging inventory is unavailable"
            raise PreservationFenceError(msg) from exc
        if is_temporary and (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != _RESTORATION_RECORD_TEMPORARY_MODE
        ):
            msg = "private restoration staging temporary is not an owner-private regular file"
            raise PreservationFenceError(msg)
        if is_stage and (
            not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)) or metadata.st_nlink < 1
        ):
            msg = "private restoration staging artifact is not a file"
            raise PreservationFenceError(msg)
        size = metadata.st_size
        if stat.S_ISLNK(metadata.st_mode):
            try:
                size = len(os.fsencode(os.readlink(entry.name, dir_fd=parent_fd)))
            except OSError as exc:
                msg = "private restoration staging link is unreadable"
                raise PreservationFenceError(msg) from exc
        if size < 0 or size > _MAX_PRESERVED_FILE_BYTES:
            msg = "private restoration staging artifact exceeds its bound"
            raise PreservationFenceError(msg)
        return size

    def _create_private_staging(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
        state: _PreservedPathState,
    ) -> tuple[str, _PreservedPathState]:
        """Create a private stage before exposing any artifact to the worktree."""
        if state.kind == "absent" or state.content is None:
            msg = "private restoration staging content is missing"
            raise PreservationRejectedError(msg)
        relative = Path(operation_id) / "paths" / digest(path.encode())
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(
                root_fd,
                Path(receipt.storage_ref) / "restoration" / relative,
                create=True,
            ) as parent_fd:
                self._validate_private_staging_inventory(parent_fd, len(state.content))
                for _attempt in range(_MAX_RESTORATION_STAGING_ATTEMPTS):
                    source = f"stage-{secrets.token_hex(16)}"
                    created = False
                    staged: _PreservedPathState | None = None
                    try:
                        if state.kind == "symlink":
                            os.symlink(os.fsdecode(state.content), source, dir_fd=parent_fd)
                            created = True
                            os.fsync(parent_fd)
                        else:
                            descriptor = os.open(
                                source,
                                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600,
                                dir_fd=parent_fd,
                            )
                            created = True
                            try:
                                with os.fdopen(descriptor, "wb", closefd=False) as handle:
                                    handle.write(state.content)
                                    handle.flush()
                                os.fchmod(descriptor, state.mode or 0o644)
                                os.fsync(descriptor)
                            finally:
                                os.close(descriptor)
                            os.fsync(parent_fd)
                        staged = self._read_private_staging_state(
                            root_fd,
                            Path(receipt.storage_ref) / "restoration" / relative / source,
                        )
                        self._require_private_staging_readback(staged, state)
                    except FileExistsError:
                        continue
                    except BaseException:
                        if created and staged is not None and staged.identity is not None:
                            with suppress(OSError):
                                current = self._read_private_staging_state(
                                    root_fd,
                                    Path(receipt.storage_ref) / "restoration" / relative / source,
                                )
                                if (
                                    current is not None
                                    and current.identity is not None
                                    and _same_staging_identity(staged.identity, current.identity)
                                ):
                                    os.unlink(source, dir_fd=parent_fd)
                                    os.fsync(parent_fd)
                        raise
                    else:
                        return source, staged
                msg = "private restoration staging name allocation exhausted"
                raise PreservationFenceError(msg)
        finally:
            os.close(root_fd)

    def _read_restoration_staging_record(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
    ) -> tuple[str, tuple[int, int, int, int, int, int, int, int]] | None:
        record_relative = (
            Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / "staging.json"
        )
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            content = read_contained(root_fd, record_relative, limit=_MAX_PRESERVED_TOTAL_BYTES)
        finally:
            os.close(root_fd)
        if content is None:
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            msg = "restoration staging identity is malformed"
            raise PreservationFenceError(msg) from exc
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "schema_version",
                "preservation_receipt_id",
                "operation_id",
                "path",
                "source",
                "identity",
            }
            or payload.get("schema_version") != 1
            or payload.get("preservation_receipt_id") != receipt.receipt_id
            or payload.get("operation_id") != operation_id
            or payload.get("path") != path
        ):
            msg = "restoration staging identity is invalid"
            raise PreservationFenceError(msg)
        source = payload.get("source")
        identity = payload.get("identity")
        if (
            not isinstance(source, str)
            or not _RESTORATION_STAGE_PATTERN.fullmatch(source)
            or not isinstance(identity, list)
            or len(identity) != _PRESERVATION_FILE_IDENTITY_FIELDS
            or any(type(value) is not int or value < 0 for value in identity)
        ):
            msg = "restoration staging identity is malformed"
            raise PreservationFenceError(msg)
        return source, tuple(identity)

    def _remove_private_staging(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
        source: str,
        identity: tuple[int, int, int, int, int, int, int, int],
    ) -> None:
        if not _RESTORATION_STAGE_PATTERN.fullmatch(source):
            msg = "restoration staging source is malformed"
            raise PreservationFenceError(msg)
        relative = Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / source
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative.parent) as parent_fd:
                staged = self._read_private_staging_state(root_fd, relative)
                if staged is None:
                    return
                if staged.identity is None or not _same_staging_identity(identity, staged.identity):
                    msg = "restoration staging owner identity changed"
                    raise PreservationFenceError(msg)
                os.unlink(source, dir_fd=parent_fd)
                os.fsync(parent_fd)
        finally:
            os.close(root_fd)

    def _cleanup_restoration_staging_source(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
    ) -> None:
        record = self._read_restoration_staging_record(receipt, operation_id, path)
        if record is not None:
            source, identity = record
            self._remove_private_staging(receipt, operation_id, path, source, identity)

    @staticmethod
    def _same_state(left: _PreservedPathState, right: _PreservedPathState) -> bool:
        return (
            left.kind == right.kind
            and left.content == right.content
            and left.mode == right.mode
            and (
                left.identity is None
                or right.identity is None
                or _same_preservation_identity(left.identity, right.identity)
            )
        )

    def _write_worktree_state(
        self,
        path: str,
        state: _PreservedPathState,
        restoration: _WorktreeRestorationContext,
    ) -> None:
        worktree = restoration.worktree
        self._validate_preservation_path(worktree, path)
        relative = PurePosixPath(path)
        name = relative.name
        if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
            msg = f"path identity changed before restoration: {path}"
            raise PreservationFenceError(msg)
        parent_fd = _open_worktree_parent(worktree, relative.parts[:-1])
        try:
            if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
                msg = f"path identity changed before restoration: {path}"
                raise PreservationFenceError(msg)
            if state.kind == "absent":
                try:
                    os.unlink(name, dir_fd=parent_fd)
                except FileNotFoundError:
                    return
                os.fsync(parent_fd)
                return
            stage = self._prepare_worktree_restoration_stage(worktree, path, state, parent_fd, restoration)
            if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
                msg = f"path identity changed before restoration: {path}"
                raise PreservationFenceError(msg)
            os.replace(stage.temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
            if stage.source is not None and stage.identity is not None:
                self._remove_private_staging(
                    restoration.receipt,
                    restoration.operation_id,
                    path,
                    stage.source,
                    stage.identity,
                )
        finally:
            os.close(parent_fd)

    def _prepare_worktree_restoration_stage(
        self,
        worktree: Path,
        path: str,
        state: _PreservedPathState,
        parent_fd: int,
        restoration: _WorktreeRestorationContext,
    ) -> _WorktreeRestorationStage:
        receipt = restoration.receipt
        operation_id = restoration.operation_id
        if receipt.runtime_device != receipt.worktree_device:
            msg = "private restoration staging requires one filesystem"
            raise PreservationFenceError(msg)
        temporary = _preservation_temporary_name(operation_id, path)
        temporary_relative = str(PurePosixPath(path).parent / temporary)
        staging_record = self._read_restoration_staging_record(receipt, operation_id, path)
        candidate = _WorktreeRestorationStageCandidate(
            temporary,
            temporary_relative,
            staging_record,
            staging_record[0] if staging_record is not None else None,
            staging_record[1] if staging_record is not None else None,
        )
        try:
            (worktree / PurePosixPath(temporary_relative)).lstat()
        except FileNotFoundError:
            return self._create_worktree_restoration_stage(path, state, parent_fd, restoration, candidate)
        if candidate.identity is None:
            msg = f"restoration staging identity is missing: {path}"
            raise PreservationFenceError(msg)
        temporary_state = self._read_worktree_state(
            worktree,
            temporary_relative,
            expected_staging_identity=candidate.identity,
        )
        if temporary_state.identity is None or not _same_staging_identity(candidate.identity, temporary_state.identity):
            msg = f"restoration staging owner identity changed: {path}"
            raise PreservationFenceError(msg)
        if not self._same_state(temporary_state, state):
            msg = f"owned restoration staging changed before replay: {path}"
            raise PreservationFenceError(msg)
        return _WorktreeRestorationStage(
            candidate.temporary, candidate.temporary_relative, candidate.source, candidate.identity
        )

    def _create_worktree_restoration_stage(
        self,
        path: str,
        state: _PreservedPathState,
        parent_fd: int,
        restoration: _WorktreeRestorationContext,
        candidate: _WorktreeRestorationStageCandidate,
    ) -> _WorktreeRestorationStage:
        source_relative, staging_source, staging_identity = self._private_restoration_staging_source(
            path,
            state,
            restoration,
            candidate,
        )
        self._link_private_restoration_stage(source_relative, candidate.temporary, parent_fd)
        temporary_state = self._read_worktree_state(
            restoration.worktree,
            candidate.temporary_relative,
            expected_staging_identity=staging_identity,
        )
        if (
            temporary_state.identity is None
            or staging_identity is None
            or not _same_staging_identity(staging_identity, temporary_state.identity)
        ):
            msg = f"restoration staging owner identity changed: {path}"
            raise PreservationFenceError(msg)
        if not self._same_state(temporary_state, state):
            msg = f"owned restoration staging changed before replay: {path}"
            raise PreservationFenceError(msg)
        return _WorktreeRestorationStage(
            candidate.temporary, candidate.temporary_relative, staging_source, staging_identity
        )

    def _private_restoration_staging_source(
        self,
        path: str,
        state: _PreservedPathState,
        restoration: _WorktreeRestorationContext,
        candidate: _WorktreeRestorationStageCandidate,
    ) -> tuple[Path, str, tuple[int, int, int, int, int, int, int, int]]:
        receipt = restoration.receipt
        operation_id = restoration.operation_id
        source_state: _PreservedPathState | None = None
        if candidate.source is not None:
            source_relative = (
                Path(receipt.storage_ref)
                / "restoration"
                / operation_id
                / "paths"
                / digest(path.encode())
                / candidate.source
            )
            root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                source_state = self._read_private_staging_state(root_fd, source_relative)
            finally:
                os.close(root_fd)
            if source_state is not None:
                if source_state.identity is None or candidate.identity is None:
                    msg = f"restoration staging identity is missing: {path}"
                    raise PreservationFenceError(msg)
                if not _same_staging_identity(candidate.identity, source_state.identity):
                    msg = f"restoration staging owner identity changed: {path}"
                    raise PreservationFenceError(msg)
                if not self._same_state(source_state, state):
                    msg = f"owned restoration staging changed before replay: {path}"
                    raise PreservationFenceError(msg)
        staging_source = candidate.source
        staging_identity = candidate.identity
        if source_state is None:
            if candidate.staging_record is not None:
                msg = f"restoration staging source is missing: {path}"
                raise PreservationFenceError(msg)
            staging_source, source_state = self._create_private_staging(
                receipt,
                operation_id,
                path,
                state,
            )
            if source_state.identity is None:
                msg = f"private restoration staging identity is unavailable: {path}"
                raise PreservationFenceError(msg)
            staging_identity = source_state.identity
            record_name = f"paths/{digest(path.encode())}"
            self._write_restoration_record(
                receipt,
                operation_id,
                f"{record_name}/staging.json",
                {
                    "preservation_receipt_id": receipt.receipt_id,
                    "operation_id": operation_id,
                    "path": path,
                    "source": staging_source,
                    "identity": list(staging_identity),
                },
            )
        return (
            Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / staging_source,
            staging_source,
            staging_identity,
        )

    def _link_private_restoration_stage(self, source_relative: Path, temporary: str, parent_fd: int) -> None:
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, source_relative.parent) as source_parent_fd:
                os.link(
                    source_relative.name,
                    temporary,
                    src_dir_fd=source_parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                os.fsync(source_parent_fd)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                msg = "private restoration staging cannot cross filesystems"
                raise PreservationFenceError(msg) from exc
            raise
        finally:
            os.close(root_fd)
        os.fsync(parent_fd)

    def _captured_finalization_guard(
        self,
        coordination: ChangeCoordination,
        head: str,
        promoted_commits: tuple[str, ...],
    ) -> str | None:
        self._require_preservation_environment()
        if coordination.writer is not None or coordination.publication_lease is not None:
            return "active-custody"
        if any(
            (
                coordination.external_head_adoption_intent,
                coordination.worktree_cleanup_intent,
                coordination.worktree_cleanup,
                coordination.dirty_worktree_quarantine,
            )
        ):
            return "workspace-preflight-failed"
        ancestors = (coordination.last_reviewed_commit, *promoted_commits)
        if any(not self._is_ancestor(commit, head, cwd=self._repository) for commit in ancestors):
            return "workspace-preflight-failed"
        if not self._promoted_chain_is_linear(promoted_commits):
            return "workspace-preflight-failed"
        return None

    def _promoted_chain_is_linear(self, promoted_commits: tuple[str, ...]) -> bool:
        # Frontier bindings list results per outcome, not in build order.
        depths = {commit: int(self._git("rev-list", "--count", commit)) for commit in promoted_commits}
        chain = sorted(depths, key=depths.__getitem__)
        return all(
            self._is_ancestor(predecessor, successor, cwd=self._repository)
            for predecessor, successor in pairwise(chain)
        )
