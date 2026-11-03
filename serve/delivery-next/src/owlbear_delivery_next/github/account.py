"""The GitHub account a repository's writes are made by (TD-402): a project's setting, else the repository owner's.

The setting names a login, or ``repository-owner``: the account ``gh`` holds for the repository's owner, else
``maba-pag`` (D-01M5DW3X00RAVF1FZF19GBJ7KX). The account's token is read from ``gh`` without switching its active
account, and goes only into the launches that write (``git.access``, D-01M6G9YYZHNDM3J6F0TYM9TWDK).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit

from owlbear_delivery_next.git.access import TOKENS, Access, is_local
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.github.provider import FailureCode, ProviderError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

REPOSITORY_OWNER = "repository-owner"
FALLBACK = "maba-pag"
LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,38}")  # GitHub's logins; enterprise-managed ones hold an underscore
TIMEOUT = 30.0  # each gh call, when no deadline bounds the resolution
_SCP = re.compile(r"^(?:[^@/]+@)?([^/:]+):(.+)$")
_PATH = re.compile(r"^/*([^/]+)/([^/]+?)(?:\.git)?/*$")


class AccountMissing(ProviderError):  # noqa: N818 - it names the owner's question, as the other provider errors do
    """The account a write needs is not one ``gh`` holds, or the repository's origin names no GitHub repository."""

    def __init__(self, detail: str) -> None:
        super().__init__(FailureCode.AUTHENTICATION_REQUIRED, "github account", detail, retry_safe=False)
        self.detail = detail


@dataclass(frozen=True)
class Origin:
    """The repository a remote names: ``LOCAL`` for a path or ``file://`` remote, which needs no account."""

    host: str
    owner: str
    name: str

    LOCAL: ClassVar[Origin]

    @classmethod
    def url(cls, url: str) -> Origin:
        """The repository *url* names; one that is neither local nor a repository URL raises ``AccountMissing``."""
        if is_local(url):
            return cls.LOCAL
        if "://" in url:
            parts = urlsplit(url)
            host, path = (parts.hostname or ""), parts.path
        elif scp := _SCP.match(url):
            host, path = scp.group(1), scp.group(2)
        else:
            host, path = "", ""
        found = _PATH.match(path)
        if not host or found is None:
            msg = f"the remote URL {url} names no GitHub repository (https://<host>/<owner>/<name>)"
            raise AccountMissing(msg)
        return cls(host.lower(), found.group(1), found.group(2))

    @classmethod
    def of(cls, repository: Path, remote: str = "origin", *, timeout: float = TIMEOUT) -> Origin:
        """The repository *remote*'s configured URL names, as written: a URL the tests rewrite still names GitHub."""
        environment = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
        command = (resolve_git_executable(), "-C", str(repository), "config", "--get", f"remote.{remote}.url")
        try:
            done = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector
                command, capture_output=True, env=environment, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"the URL of {repository}'s remote {remote} could not be read in {timeout:g} s"
            raise AccountMissing(msg) from exc
        if done.returncode:
            said = done.stderr.decode(errors="replace").strip() or "it is not set"
            msg = f"{repository} has no URL for the remote {remote}, so no account can be chosen for it: {said}"
            raise AccountMissing(msg)
        return cls.url(done.stdout.decode(errors="replace").strip())

    def __str__(self) -> str:
        return f"{self.host}/{self.owner}/{self.name}" if self.host else "a local repository"


Origin.LOCAL = Origin("", "", "")


def host_of(repository: Path) -> str:
    """The host *repository*'s origin names, else ``github.com``; it never raises, a bad origin fails at its launch."""
    try:
        return Origin.of(repository).host or "github.com"
    except AccountMissing:
        return "github.com"


class _Clock:
    """What remains of one resolution's deadline; none left raises ``AccountMissing`` before another call."""

    def __init__(self, until: float | None) -> None:
        self.until = until

    def left(self, doing: str) -> float:
        if self.until is None:
            return TIMEOUT
        left = self.until - time.monotonic()
        if left <= 0:
            msg = f"no time was left to {doing}"
            raise AccountMissing(msg)
        return min(left, TIMEOUT)


def _gh(gh: str, args: tuple[str, ...], clock: _Clock, doing: str) -> subprocess.CompletedProcess[bytes]:
    environment = {k: v for k, v in os.environ.items() if k not in TOKENS}  # gh's stored accounts, not a token
    timeout = clock.left(doing)
    try:
        return subprocess.run(  # noqa: S603 - the resolved gh executable and code-owned argument vectors
            (gh, *args), capture_output=True, env=environment, timeout=timeout, check=False, stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"gh did not answer in {timeout:g} s while it was asked to {doing}"
        raise AccountMissing(msg) from exc


def _token(gh: str, host: str, login: str, clock: _Clock) -> str | None:
    """*login*'s token as ``gh`` stores it for *host*, or ``None`` when ``gh`` holds no such account."""
    done = _gh(gh, ("auth", "token", "--hostname", host, "--user", login), clock, f"read {login}'s token on {host}")
    said = done.stderr.decode(errors="replace").strip()
    if done.returncode:
        if "no oauth token found" in said:
            return None
        msg = f"gh could not read {login}'s token on {host} (exit {done.returncode}): {said or 'no message'}"
        raise AccountMissing(msg)
    return done.stdout.decode(errors="replace").strip() or None


def _logins(gh: str, host: str, clock: _Clock) -> list[str]:
    """Every login ``gh`` holds for *host*, whatever its validation state."""
    done = _gh(gh, ("auth", "status", "--hostname", host, "--json", "hosts"), clock, f"list its accounts on {host}")
    try:
        hosts = json.loads(done.stdout)["hosts"]
        return [entry["login"] for entry in hosts.get(host, [])]
    except (ValueError, KeyError, TypeError) as exc:
        said = done.stderr.decode(errors="replace").strip() or done.stdout.decode(errors="replace").strip()
        msg = f"gh's accounts on {host} could not be read (exit {done.returncode}): {said or 'no message'}"
        raise AccountMissing(msg) from exc


def resolve(setting: str, origin: Origin, *, until: float | None = None) -> Access:
    """The access *setting* gives on *origin*'s host; ``until`` (monotonic) bounds every ``gh`` call it makes."""
    if origin == Origin.LOCAL:
        return Access.LOCAL
    gh = shutil.which("gh")
    if gh is None:
        msg = f"gh is not installed, so no account can write to {origin}; install the GitHub CLI and sign in"
        raise AccountMissing(msg)
    clock, listed = _Clock(until), []

    def find(login: str) -> tuple[str, str] | None:
        if token := _token(gh, origin.host, login, clock):
            return login, token
        if not listed:
            listed.extend(_logins(gh, origin.host, clock) or [""])
        spelled = next((x for x in listed if x and x.casefold() == login.casefold() and x != login), None)
        if spelled and (token := _token(gh, origin.host, spelled, clock)):
            return spelled, token
        return None

    if setting != REPOSITORY_OWNER:
        tried = [(setting, "the setting names it")]
    else:
        tried = [(origin.owner, "the repository owner"), (FALLBACK, f"gh has no account for the owner {origin.owner}")]
    for login, why in tried:
        if found := find(login):
            return Access(found[0], why, origin.host, found[1], gh)
    held = ", ".join(x for x in listed if x) or "none"
    wanted = " or ".join(login for login, _ in tried)
    chose = "the setting names it" if setting != REPOSITORY_OWNER else "TD-402's rule: the owner's, else maba-pag"
    msg = (
        f"gh holds no account {wanted} on {origin.host}, needed to write to {origin} ({chose}); "
        f"gh's accounts there: {held}. Sign it in with: gh auth login --hostname {origin.host}, "
        "or name another account in the project's GitHub account setting"
    )
    raise AccountMissing(msg)


class Writer:
    """The account one repository's writes are made by, resolved at the first launch that needs it and kept."""

    def __init__(self, setting: str | Callable[[], str], origin: Origin | Path) -> None:
        self._setting, self._origin = setting, origin
        self._access: Access | None = None
        self.unset = False  # set by a setting that was unset and stood in for by TD-402's rule

    @classmethod
    def rule(cls, origin: Origin | Path) -> Writer:
        """TD-402's rule on *origin*: the repository owner's account when ``gh`` has it, else ``maba-pag``."""
        return cls(REPOSITORY_OWNER, origin)

    def access(self, until: float | None = None) -> Access:
        """The access, resolved now if no launch has needed it yet; *until* bounds that resolution."""
        if self._access is None:
            setting = self._setting() if callable(self._setting) else self._setting
            origin = self._origin if isinstance(self._origin, Origin) else Origin.of(self._origin)
            self._access = resolve(setting, origin, until=until)
        return self._access
