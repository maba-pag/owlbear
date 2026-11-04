"""The credentials one launch writes to GitHub with (TD-402, D-01M6G9YYZHNDM3J6F0TYM9TWDK).

The chosen account's token goes only into the child's environment; Git's credential helpers are reset for the launch
and replaced by ``gh``'s, which answers with that token. The active ``gh`` account is never switched.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.git.remote_git import RemoteGitError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

TOKENS = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://")
_SCP = re.compile(r"^[^/]*:")  # Git's scp-like form: a colon before any slash


def is_local(url: str) -> bool:
    """Whether Git reaches *url* on this machine: ``file://``, or a path that is neither ``scheme://`` nor scp-like."""
    if scheme := _SCHEME.match(url):
        return scheme.group(1).lower() == "file"
    return not _SCP.match(url)


@dataclass(frozen=True)
class Access:
    """The account a launch writes as; ``LOCAL`` (no login) leaves the launch exactly as it was."""

    login: str
    why: str
    host: str
    token: str = field(repr=False)
    gh: str

    LOCAL: ClassVar[Access]

    def environment(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        """*base* (the process's by default) with this account's token as the only GitHub token."""
        environment = dict(os.environ if base is None else base)
        if not self.login:
            return environment
        for name in TOKENS:
            environment.pop(name, None)
        cloud = self.host == "github.com" or self.host.endswith(".ghe.com")  # gh's rule: others are Enterprise Server
        environment["GH_TOKEN" if cloud else "GH_ENTERPRISE_TOKEN"] = self.token
        return environment

    def options(self) -> tuple[str, ...]:
        """Git options that reset its credential helpers and use ``gh``'s, which answers from the environment."""
        if not self.login:
            return ()
        return ("-c", "credential.helper=", "-c", f"credential.helper=!{shlex.quote(self.gh)} auth git-credential")

    def destinations(self, repository: Path, remote: str, timeout: float) -> list[str]:
        """Every URL a push to *remote* goes to; one that would push as another account raises ``PushRefused``.

        That is a URL that is neither HTTPS nor local (SSH, the key's account), one carrying its own password or token,
        an HTTPS one on another host than the account was chosen on, and any non-local one when no account was chosen
        because the remote's fetch URL is local.
        """
        environment = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
        command = (resolve_git_executable(), "-C", str(repository), "remote", "get-url", "--push", "--all", remote)
        try:
            done = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector
                command, capture_output=True, env=environment, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"the push URLs of {remote} in {repository} could not be read in {timeout:g} s"
            error = RemoteGitError(msg, retry_safe=True)
            error.add_note(failure(exc))
            raise error from exc
        if done.returncode:
            said = done.stderr.decode(errors="replace").strip() or f"exit {done.returncode}"
            msg = f"the push URLs of {remote} in {repository} could not be read: {said}"
            raise RemoteGitError(msg, retry_safe=False)
        urls = done.stdout.decode(errors="replace").split()
        who = f"instead of {self.login}" if self.login else "instead of the account the setting names"
        fix = f"git -C {repository} remote set-url --push {remote} https://<host>/<owner>/<name>.git"
        for url in urls:
            if is_local(url):
                continue
            parts = urlsplit(url) if "://" in url else None
            if parts is not None and parts.password is not None:  # the URL itself is never shown: it holds a secret
                msg = (
                    f"{repository}'s remote {remote} has a push URL with a password or token in it, which Git would "
                    f"push with {who}. Give it one without: {fix}"
                )
                raise PushRefused(msg)
            if parts is None or parts.scheme.lower() != "https":
                msg = (
                    f"{repository}'s remote {remote} pushes to {url}, over SSH, where the SSH key's account would push "
                    f"{who}. Give it an HTTPS push URL: {fix}"
                )
                raise PushRefused(msg)
            if not self.login:
                msg = (
                    f"{repository}'s remote {remote} pushes to {url} although its URL is local, so no account was "
                    f"chosen for it. Give it a local push URL, or an HTTPS URL to push as the setting's account: "
                    f"git -C {repository} remote set-url {remote} https://<host>/<owner>/<name>.git"
                )
                raise PushRefused(msg)
            if parts.hostname != self.host:
                msg = (
                    f"{repository}'s remote {remote} pushes to {url}, on {parts.hostname}, not {self.host}, where "
                    f"{self.login} was chosen from its URL. Give it a push URL on {self.host}: {fix}"
                )
                raise PushRefused(msg)
        return urls


Access.LOCAL = Access("", "a local remote", "", "", "")


class PushRefused(RemoteGitError):  # noqa: N818 - named for the owner's question, as RemoteGitFailed is
    """A push would leave as another account than the chosen one: over SSH, with its URL's own token, or unchosen."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, retry_safe=False)
