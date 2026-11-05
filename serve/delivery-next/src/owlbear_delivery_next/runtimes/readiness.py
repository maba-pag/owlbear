"""Readiness: the facts a clone needs before Delivery can run and publish, each ok or with one concrete fix (DR2)."""

from __future__ import annotations

import json
import shlex
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import truststore

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github import account
from owlbear_delivery_next.github.account import AccountMissing
from owlbear_delivery_next.impeccable import pack_update
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.git_files import probe_in
from owlbear_delivery_next.runtimes import copilot_cli
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import github_writer, prefs_import, profile_share
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.github.account import Writer
    from owlbear_delivery_next.local_system.git_files import Probe
    from owlbear_delivery_next.state_store.store import Store

SHAPER = "owlbear-shaper.agent.md"
PUSH = frozenset({"WRITE", "MAINTAIN", "ADMIN"})
REPO_FIELDS = "nameWithOwner,viewerPermission,isEmpty,defaultBranchRef"
CONFIG_FIX = "Repair the git configuration as git's error says, then run setup again"
SIGN_IN = "Sign that account in with `gh auth login --hostname {host}`, or name another as the GitHub account"


@dataclass(frozen=True)
class Check:
    """One readiness fact: ok, or one concrete fix."""

    name: str
    ok: bool
    detail: str
    fix: str = ""


def reach(host: str, timeout: float = 10) -> str | None:
    """None when ``https://<host>`` answers through the configured proxy and the system trust store, else the error."""
    https = urllib.request.HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
    request = urllib.request.Request(f"https://{host}/", method="HEAD")
    try:
        urllib.request.build_opener(https).open(request, timeout=timeout).close()
    except urllib.error.HTTPError:
        return None
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)  # a URLError's reason: the error itself, or its text
        return failure(reason if isinstance(reason, BaseException) else exc)
    return None


def _network(host: str, error: str | None) -> Check:
    if error is None:
        return Check("network", ok=True, detail=f"https://{host} answers")
    fix = "Connect to the network or set HTTPS_PROXY, then run setup again"
    if "certificate" in error.lower():
        fix = "A proxy intercepts TLS: set SSL_CERT_FILE to your company's CA bundle, then run setup again"
    return Check("network", ok=False, detail=f"https://{host}: {error}", fix=fix)


def _github(host: str, probe: Probe, writer: Writer) -> list[Check]:
    """The GitHub CLI, the account the project's writes are made by (TD-402), its push permission and first commits."""
    code, text = probe(["gh", "--version"])
    if code:
        return [Check("github cli", ok=False, detail=text, fix="Install the GitHub CLI: https://cli.github.com")]
    out = [Check("github cli", ok=True, detail=text.splitlines()[0])]
    try:
        access = writer.access()
    except AccountMissing as exc:
        return [*out, Check("github sign-in", ok=False, detail=str(exc), fix=SIGN_IN.format(host=host))]
    except StoreError as exc:  # the settings that name the account can't be read
        fix = "Repair the settings file the error names, then run setup again"
        return [*out, Check("github sign-in", ok=False, detail=str(exc), fix=fix)]
    rule = "; the GitHub account setting is unset, so TD-402's rule picked it" if writer.unset else ""
    out.append(Check("github sign-in", ok=True, detail=f"writes as {access.login or '-'} ({access.why}){rule}"))
    code, text = probe(["gh", "repo", "view", "--json", REPO_FIELDS], access.environment())
    try:
        repo = json.loads(text) if code == 0 else {}
    except ValueError:
        repo = {}
    detail = f"{repo.get('nameWithOwner')}: {repo.get('viewerPermission')}" if repo else text
    fix = "Point `origin` at a GitHub repository you can push to (check with `gh repo view`)"
    out.append(Check("repository", ok=repo.get("viewerPermission") in PUSH, detail=detail, fix=fix))
    return [*out, _first_commit(repo, probe)] if repo else out


def _first_commit(repo: dict[str, object], probe: Probe) -> Check:
    """Whether GitHub and this clone both hold commits; for each that holds none, the git commands that end it."""
    name, ref = repo.get("nameWithOwner"), repo.get("defaultBranchRef")
    branch = ref.get("name") if isinstance(ref, dict) else ""
    remote = repo.get("isEmpty") is not True
    code, said = probe(["git", "rev-parse", "--verify", "--quiet", "HEAD"])
    if code not in {0, 1}:  # git failed; exit 1 alone means a clone without commits
        return Check(
            "first commit", ok=False, detail=said, fix="Repair the clone as git's error says, then run setup again"
        )
    local = code == 0
    if remote and local:
        return Check("first commit", ok=True, detail=f"default branch {branch}")
    if remote:
        detail = f"{name} has commits on {branch}, but this clone has none"
        command = f"git pull --set-upstream origin {shlex.quote(branch)}"  # a branch name may hold $ or ;
    elif local:
        detail, command = f"{name} has no commits yet, but this clone has", "git push -u origin HEAD"
    else:
        detail = f"{name} has no commits yet, and neither has this clone"
        command = 'git add <file> && git commit -m "First commit" && git push -u origin HEAD'
    return Check("first commit", ok=False, detail=detail, fix=f"Run `{command}`, then run setup again")


def _ssh(key: str, probe: Probe) -> Check:
    """An SSH signing key: a literal key or a key file, which must be a readable OpenSSH public key in the agent."""
    path = None if key.startswith(("ssh-", "key::")) else Path(key).expanduser()
    pub_path = path if path is None or path.suffix == ".pub" else path.with_name(path.name + ".pub")
    setting = "Set `git config user.signingkey` to your OpenSSH public key file, e.g. ~/.ssh/id_ed25519.pub"
    try:
        pub = pub_path.read_text() if pub_path else key.removeprefix("key::")
    except (OSError, UnicodeDecodeError) as exc:
        return Check("commit signing", ok=False, detail=f"ssh key {pub_path}: {failure(exc)}", fix=setting)
    words = pub.split()
    if len(words) < 2 or not words[0].startswith(("ssh-", "ecdsa-", "sk-")):  # noqa: PLR2004 - type and key
        return Check(
            "commit signing", ok=False, detail=f"ssh key {pub_path or key[:40]}: not a public key", fix=setting
        )
    code, said = probe(["ssh-add", "-L"])
    if code not in {0, 1}:  # 1: the agent holds no identities
        return Check(
            "commit signing",
            ok=False,
            detail=f"ssh-agent not reachable: {said}",
            fix="Start ssh-agent and point SSH_AUTH_SOCK at it, then run `ssh-add <key>`",
        )
    ok = words[1] in said
    private = pub_path.with_suffix("") if pub_path else "<your private key>"
    return Check(
        "commit signing", ok=ok, detail=f"ssh key {'in' if ok else 'not in'} the agent", fix=f"Run `ssh-add {private}`"
    )


class _UnreadSettingError(Exception):
    """Git could not read a setting; the message is its whole failure."""


def _config(probe: Probe, *key: str) -> str:
    """A git setting's value; an unset one, which git answers with exit 1, is empty; any other failure is raised."""
    code, text = probe(["git", "config", *key])
    if code not in {0, 1}:
        raise _UnreadSettingError(text)
    return "" if code else text.strip()


def signing(probe: Probe) -> Check:
    """Whether commits can be signed as Git requires; a locked or missing key is the failure."""
    try:
        return _signed(probe)
    except _UnreadSettingError as exc:
        return Check("commit signing", ok=False, detail=str(exc), fix=CONFIG_FIX)


def _signed(probe: Probe) -> Check:
    if _config(probe, "--bool", "commit.gpgsign") != "true":
        return Check("commit signing", ok=True, detail="not required")
    fmt = _config(probe, "gpg.format") or "openpgp"
    key = _config(probe, "user.signingkey")
    if not key:
        return Check(
            "commit signing", ok=False, detail=f"{fmt} required, no key", fix="Set `git config user.signingkey`"
        )
    if fmt == "ssh":
        return _ssh(key, probe)
    if fmt != "openpgp":
        return Check("commit signing", ok=True, detail=f"{fmt}: not verified by setup")
    sign = [
        "gpg",
        "--batch",
        "--yes",
        "--pinentry-mode",
        "error",
        "-u",
        key,
        "--clearsign",
        "-o",
        "/dev/null",
        "/dev/null",
    ]
    code, said = probe(sign)
    fix = "Unlock your GPG key (`echo test | gpg --clearsign`), then run setup again"
    detail = f"gpg key {key} unlocked" if code == 0 else f"gpg key {key} locked or missing: {said}"
    return Check("commit signing", ok=code == 0, detail=detail, fix=fix)


def publishing(host: str, probe: Probe, network: str | None, writer: Writer) -> list[Check]:
    """The readiness facts publishing needs: the network, the GitHub CLI, the writing account and its permission."""
    return [_network(host, network), *_github(host, probe, writer)]


def readiness(host: str, probe: Probe, network: str | None, copilot: str | None, writer: Writer) -> list[Check]:
    """Every readiness fact, in the order a fix should be applied."""
    out = publishing(host, probe, network, writer)
    code, text = probe([copilot, "--version"]) if copilot else (127, copilot_cli.missing())
    said = text if code or not text else text.splitlines()[0]  # a failure whole; a version, its first line
    detail = f"{copilot}: {said}" if copilot else said
    out.append(Check("copilot cli", ok=code == 0, detail=detail, fix=copilot_cli.FIX))
    return [*out, identity(probe), signing(probe)]


def identity(probe: Probe) -> Check:
    """Whether Git has an author name and email."""
    fix = 'Run `git config --global user.name "Your Name"` and `git config --global user.email you@example.com`'
    try:
        name, email = _config(probe, "user.name"), _config(probe, "user.email")
    except _UnreadSettingError as exc:
        return Check("git identity", ok=False, detail=str(exc), fix=CONFIG_FIX)
    ok = bool(name and email)
    return Check("git identity", ok=ok, detail=f"{name} <{email}>" if ok else "not set", fix=fix)


def ready(store: Store, repo: Path, *, carry: bool = False) -> list[Check]:
    """The readiness check at a host start, after a shared profile's facts were detected in this clone (TD-147).

    With *carry* (a host start) the legacy preference import runs after that detection and its failure is a check.
    A detection that cannot publish is a failed check too, and the legacy import waits for a detection that succeeded.
    """
    try:
        prof = profile_share.checked(store, repo)
    except StoreError as exc:
        fix = "Restore the shared profile repository's write access, then restart Delivery"
        failed = Check("profile detection", ok=False, detail=failure(exc), fix=fix)
        return [failed, *_host_checks(store, repo)]
    carried = _carried(store) if carry else []
    return [*carried, *check(repo, prof, github_writer.of(store, repo, detecting=True))]


def _host_checks(store: Store, repo: Path) -> list[Check]:
    """The host checks after a failed detection: the known profile's host, else none while the profile is unreadable.

    A missing profile is a fresh clone, whose checks use the default host; an unreadable one has no host to check, so
    its host-specific checks wait for the next start rather than run against a public host by default.
    """
    try:
        prof = store.read_profile()
    except StoreError:
        return []
    return check(repo, prof, github_writer.of(store, repo, detecting=True))


def _carried(store: Store) -> list[Check]:
    """The one-time legacy preference import at a host start: a review or unpublished step is reported, not hidden.

    A lock that cannot be taken or a local flag that cannot be written is reported the same way and tried again at the
    next start; the import's state is left as it is.
    """
    try:
        prefs_import.run(store)
    except StoreError as exc:
        fix = "review the Merge and cleanup preferences on the Settings page, or fix the repository and restart"
        return [Check("legacy preferences", ok=False, detail=str(exc), fix=fix)]
    except (data_repo.DataRepoError, OSError) as exc:
        fix = "Restore the shared profile repository's access and local write access, then restart Delivery"
        return [Check("legacy preferences", ok=False, detail=failure(exc), fix=fix)]
    return []


def check(repo: Path, prof: Profile | None, writer: Writer) -> list[Check]:
    """The readiness check of this clone (DR2), run by setup and at every host start; *writer* makes its GitHub writes.

    The host is the profile's, else the one the origin names, so a first run on an enterprise host checks that host.
    """
    host = profile.value(prof or Profile(), profile.HOST, "") or account.host_of(repo)
    try:
        copilot: str | None = copilot_cli.cli_path()
    except FileNotFoundError:
        copilot = None
    updates = Check("Impeccable updates", ok=True, detail=pack_update.said(pack_update.notice(refresh=True)))
    return [*readiness(host, probe_in(repo), reach(host), copilot, writer), updates]


def shaper_path(home: Path) -> Path:
    """The shaping chat's agent file, in the one user folder the window's agent host lists agents from (TD-93)."""
    return home / ".copilot" / "agents" / SHAPER
