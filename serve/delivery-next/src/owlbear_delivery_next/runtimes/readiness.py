"""Readiness: the facts a clone needs before Delivery can run and publish, each ok or with one concrete fix (DR2)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import truststore

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.design_packs import pack_update
from owlbear_delivery_next.local_system.git_files import probe_in
from owlbear_delivery_next.runtimes import copilot_cli
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.git_files import Probe
    from owlbear_delivery_next.state_store.store import Store

SHAPER = "owlbear-shaper.agent.md"
PUSH = frozenset({"WRITE", "MAINTAIN", "ADMIN"})


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
        return str(getattr(exc, "reason", exc))
    return None


def _network(host: str, error: str | None) -> Check:
    if error is None:
        return Check("network", ok=True, detail=f"https://{host} answers")
    fix = "Connect to the network or set HTTPS_PROXY, then run setup again"
    if "certificate" in error.lower():
        fix = "A proxy intercepts TLS: set SSL_CERT_FILE to your company's CA bundle, then run setup again"
    return Check("network", ok=False, detail=f"https://{host}: {error}"[:200], fix=fix)


def _sign_in_failure(host: str, text: str) -> Check:
    """The failed account's lines of ``gh auth status``, not the last account it lists; a bad GH_TOKEN is named."""
    lines = [ln.strip() for ln in text.splitlines()]
    start = next((i for i, ln in enumerate(lines) if ln.startswith("X ")), len(lines))
    end = next((i for i in range(start, len(lines)) if not lines[i]), len(lines))
    detail = " ".join(lines[start:end]) or " ".join(lines)[-160:]
    fix = f"Run `gh auth login --hostname {host}`"
    if "GH_TOKEN" in detail:
        fix = f"Unset GH_TOKEN or set a valid token, then restart Delivery; or run `gh auth login --hostname {host}`"
    return Check("github sign-in", ok=False, detail=detail[:200], fix=fix)


def _github(host: str, probe: Probe) -> list[Check]:
    code, text = probe(["gh", "--version"])
    if code:
        return [Check("github cli", ok=False, detail=text[:120], fix="Install the GitHub CLI: https://cli.github.com")]
    out = [Check("github cli", ok=True, detail=text.splitlines()[0])]
    code, text = probe(["gh", "auth", "status", "--hostname", host])
    if code:
        return [*out, _sign_in_failure(host, text)]
    out.append(Check("github sign-in", ok=True, detail=f"signed in to {host}"))
    code, text = probe(["gh", "repo", "view", "--json", "nameWithOwner,viewerPermission"])
    try:
        repo = json.loads(text) if code == 0 else {}
    except ValueError:
        repo = {}
    detail = f"{repo.get('nameWithOwner')}: {repo.get('viewerPermission')}" if repo else text[-160:]
    fix = "Point `origin` at a GitHub repository you can push to (check with `gh repo view`)"
    return [*out, Check("repository", ok=repo.get("viewerPermission") in PUSH, detail=detail, fix=fix)]


def _ssh(key: str, probe: Probe) -> Check:
    """An SSH signing key: a literal key or a key file, which must be a readable OpenSSH public key in the agent."""
    path = None if key.startswith(("ssh-", "key::")) else Path(key).expanduser()
    pub_path = path if path is None or path.suffix == ".pub" else path.with_name(path.name + ".pub")
    setting = "Set `git config user.signingkey` to your OpenSSH public key file, e.g. ~/.ssh/id_ed25519.pub"
    try:
        pub = pub_path.read_text() if pub_path else key.removeprefix("key::")
    except (OSError, UnicodeDecodeError) as exc:
        return Check("commit signing", ok=False, detail=f"ssh key {pub_path}: {exc}"[:200], fix=setting)
    words = pub.split()
    if len(words) < 2 or not words[0].startswith(("ssh-", "ecdsa-", "sk-")):  # noqa: PLR2004 - type and key
        return Check(
            "commit signing", ok=False, detail=f"ssh key {pub_path or key[:40]}: not a public key", fix=setting
        )
    ok = words[1] in probe(["ssh-add", "-L"])[1]
    private = pub_path.with_suffix("") if pub_path else "<your private key>"
    return Check(
        "commit signing", ok=ok, detail=f"ssh key {'in' if ok else 'not in'} the agent", fix=f"Run `ssh-add {private}`"
    )


def _signing(probe: Probe) -> Check:
    if probe(["git", "config", "--bool", "commit.gpgsign"])[1].strip() != "true":
        return Check("commit signing", ok=True, detail="not required")
    fmt = probe(["git", "config", "gpg.format"])[1].strip() or "openpgp"
    key = probe(["git", "config", "user.signingkey"])[1].strip()
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
    ok = probe(sign)[0] == 0
    fix = "Unlock your GPG key (`echo test | gpg --clearsign`), then run setup again"
    return Check("commit signing", ok=ok, detail=f"gpg key {key} {'unlocked' if ok else 'locked or missing'}", fix=fix)


def publishing(host: str, probe: Probe, network: str | None) -> list[Check]:
    """The readiness facts publishing needs: the network, the GitHub CLI, sign-in and push permission."""
    return [_network(host, network), *_github(host, probe)]


def readiness(host: str, probe: Probe, network: str | None, copilot: str | None) -> list[Check]:
    """Every readiness fact, in the order a fix should be applied."""
    out = publishing(host, probe, network)
    code, text = probe([copilot, "--version"]) if copilot else (127, copilot_cli.missing())
    line = text.splitlines()[0] if text else ""
    detail = f"{copilot}: {line}" if copilot else line
    out.append(Check("copilot cli", ok=code == 0, detail=detail, fix=copilot_cli.FIX))
    name, email = probe(["git", "config", "user.name"]), probe(["git", "config", "user.email"])
    ok = name[0] == email[0] == 0 and bool(name[1] and email[1])
    fix = 'Run `git config --global user.name "Your Name"` and `git config --global user.email you@example.com`'
    out.append(Check("git identity", ok=ok, detail=f"{name[1]} <{email[1]}>" if ok else "not set", fix=fix))
    return [*out, _signing(probe)]


def ready(store: Store, repo: Path, *, carry: bool = False) -> list[Check]:
    """The readiness check at a host start, after a shared profile's facts were detected in this clone (TD-147).

    With *carry* (a host start) the legacy preference import runs after that detection and its failure is a check.
    """
    prof = profile_share.checked(store, repo)
    carried = _carried(store) if carry else []
    return [*carried, *check(repo, prof)]


def _carried(store: Store) -> list[Check]:
    """The one-time legacy preference import at a host start: a review or unpublished step is reported, not hidden."""
    try:
        prefs_import.run(store)
    except StoreError as exc:
        fix = "review the Merge and cleanup preferences on the Settings page, or fix the repository and restart"
        return [Check("legacy preferences", ok=False, detail=str(exc), fix=fix)]
    return []


def check(repo: Path, prof: Profile | None) -> list[Check]:
    """The readiness check of this clone (DR2), run by setup and at every host start."""
    host = profile.value(prof or Profile(), profile.HOST, "github.com")
    try:
        copilot: str | None = copilot_cli.cli_path()
    except FileNotFoundError:
        copilot = None
    updates = Check("design pack updates", ok=True, detail=pack_update.said(pack_update.notice(refresh=True)))
    return [*readiness(host, probe_in(repo), reach(host), copilot), updates]


def shaper_path(home: Path) -> Path:
    """The shaping chat's agent file, in the one user folder the window's agent host lists agents from (TD-93)."""
    return home / ".copilot" / "agents" / SHAPER
