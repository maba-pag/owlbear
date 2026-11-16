"""Attribute a read-only batch's Git ref writes without mistaking another process's fetched tags for its own."""

from __future__ import annotations

import shlex
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system.git_files import git_common_dir

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class RefWatchError(RuntimeError):
    """Git ref attribution could not be prepared or inspected."""


@dataclass(frozen=True)
class Watch:
    """The batch's shell initialization and prepared source-ref transactions, outside the agent's worktree."""

    script: Path
    record: Path


_active: ContextVar[Watch | None] = ContextVar("read_only_refs", default=None)


def prepare(source: Path, folder: Path) -> Watch:
    """Prepare an additive, process-inherited hook; refuse unsupported or disabled registration before a session."""
    folder.mkdir(parents=True, exist_ok=True)
    hook, script, record = (folder / f"read-only-refs{suffix}" for suffix in ("-hook.sh", ".sh", ".log"))
    name = f"owlbear-read-only-{uuid.uuid4().hex}"
    settings = (
        (f"hook.{name}.event", "reference-transaction"),
        (f"hook.{name}.command", f"/bin/sh {shlex.quote(str(hook))}"),
    )
    args = [arg for key, value in settings for arg in ("-c", f"{key}={value}")]
    listed = worktree.git(source, *args, "hook", "list", "reference-transaction")
    if name not in listed.splitlines():
        msg = f"Git did not enable the read-only reference-transaction hook in {source}:\n{listed}"
        raise RefWatchError(msg)
    hook.write_text(
        '#!/bin/sh\n[ "$1" = prepared ] || exit 0\n'
        f"common=$({shlex.quote(worktree.GIT)} rev-parse --path-format=absolute --git-common-dir) || exit\n"
        'common=$(CDPATH= cd "$common" && pwd -P) || exit\n'
        f'[ "$common" = {shlex.quote(str(git_common_dir(source)))} ] || exit 0\n'
        f"cat >> {shlex.quote(str(record))}\n",
        encoding="utf-8",
    )
    lines = ["owlbear_ref_config_count=${GIT_CONFIG_COUNT:-0}"]
    for key, value in settings:
        lines += [
            f'export "GIT_CONFIG_KEY_$owlbear_ref_config_count={key}"',
            f'export "GIT_CONFIG_VALUE_$owlbear_ref_config_count="{shlex.quote(value)}',
            "owlbear_ref_config_count=$((owlbear_ref_config_count + 1))",
        ]
    lines += ['export GIT_CONFIG_COUNT="$owlbear_ref_config_count"', "unset owlbear_ref_config_count"]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    record.write_text("", encoding="utf-8")
    return Watch(script, record)


@contextmanager
def watching(watch: Watch | None) -> Iterator[None]:
    """Keep the batch's attribution scoped through its SDK sessions and settlement."""
    token = _active.set(watch)
    try:
        yield
    finally:
        _active.reset(token)


def script() -> Path | None:
    """The active batch's additional shell-init script, if any."""
    watch = _active.get()
    return watch.script if watch else None


def refs(watch: Watch | None) -> set[str]:
    """Heads and tags in the batch's prepared transactions; an unreadable record is not a clean inspection."""
    if watch is None:
        return set()
    try:
        found = set()
        for line in watch.record.read_text(encoding="utf-8").splitlines():
            old, new, ref = line.split()
            if old != new and ref.startswith(("refs/heads/", "refs/tags/")):
                found.add(ref)
    except (OSError, ValueError) as exc:
        msg = f"{watch.record}: {failure(exc)}"
        raise RefWatchError(msg) from exc
    return found
