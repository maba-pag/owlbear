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
        environment["GH_TOKEN" if self.host == "github.com" else "GH_ENTERPRISE_TOKEN"] = self.token
        return environment

    def options(self) -> tuple[str, ...]:
        """Git options that reset its credential helpers and use ``gh``'s, which answers from the environment."""
        if not self.login:
            return ()
        return ("-c", "credential.helper=", "-c", f"credential.helper=!{shlex.quote(self.gh)} auth git-credential")

    def destinations(self, repository: Path, remote: str, timeout: float) -> list[str]:
        """Every URL a push to *remote* goes to; one that is neither HTTPS nor local raises ``PushRefused``."""
        environment = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
        command = (resolve_git_executable(), "-C", str(repository), "remote", "get-url", "--push", "--all", remote)
        try:
            done = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector
                command, capture_output=True, env=environment, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"the push URLs of {remote} in {repository} could not be read in {timeout:g} s"
            raise RemoteGitError(msg, retry_safe=True) from exc
        if done.returncode:
            said = done.stderr.decode(errors="replace").strip() or f"exit {done.returncode}"
            msg = f"the push URLs of {remote} in {repository} could not be read: {said}"
            raise RemoteGitError(msg, retry_safe=False)
        urls = done.stdout.decode(errors="replace").split()
        for url in urls:
            if not url.lower().startswith("https://") and not is_local(url):
                who = f"instead of {self.login}" if self.login else "instead of the account the setting names"
                msg = (
                    f"{repository}'s remote {remote} pushes to {url}, over SSH, where the SSH key's account would push "
                    f"{who}. Give it an HTTPS push URL: git -C {repository} remote set-url --push {remote} "
                    "https://<host>/<owner>/<name>.git"
                )
                raise PushRefused(msg)
        return urls


Access.LOCAL = Access("", "a local remote", "", "", "")


class PushRefused(RemoteGitError):  # noqa: N818 - named for the owner's question, as RemoteGitFailed is
    """A push would leave over SSH, where the key's account pushes instead of the chosen one."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, retry_safe=False)
