"""The design pack (TD-76): Impeccable's detector, pinned together with the design skills extracted from it.

Delivery downloads the engine and the in-page detector once, unmodified, checks each against the pack's digest and
keeps them outside every project, in ``<OWLBEAR_HOME>/design-pack/<pack>/``. The pack changes only as a whole.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import ssl
import tempfile
import urllib.request
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import truststore

from owlbear_delivery_next import preload

if TYPE_CHECKING:
    from collections.abc import Callable

ENGINE, BUNDLE = "impeccable", "detect-antipatterns-browser.js"
RELEASE = "https://github.com/{repository}/releases/download/engine-v{engine}/impeccable-{platform}"
RAW = "https://raw.githubusercontent.com/{repository}/{commit}/{path}"
SECONDS = 120.0  # one download


class PackError(RuntimeError):
    """The pack cannot be installed: an unsupported platform, a failed download or a digest mismatch."""


@dataclass(frozen=True)
class Installed:
    """The pack's verified files on this machine: the engine to run, and the in-page detector's verified text."""

    engine: Path
    engine_sha256: str
    bundle: str

    def verified_engine(self) -> Path:
        """The engine, checked against its digest just before it runs."""
        if _sha256(self.engine) != self.engine_sha256:
            msg = f"{self.engine} no longer matches the design pack's digest; run `owlbear-next design-pack --install`"
            raise PackError(msg)
        return self.engine


def manifest() -> dict[str, Any]:
    """The pack's pins: upstream tag and commit, the engine's digest per platform, the in-page detector's digest."""
    return json.loads(files("owlbear_delivery_next").joinpath("design_pack.json").read_text(encoding="utf-8"))


def identity(pins_text: str | None = None) -> str:
    """What a review records as the pack it used: its version and a hash over its pins, adapter and skills.

    *pins_text* is a candidate pack's ``design_pack.json``; by default the installed one's.
    """
    package = files("owlbear_delivery_next")
    text = package.joinpath("design_pack.json").read_bytes() if pins_text is None else pins_text.encode()
    digest = hashlib.sha256(text)
    digest.update(package.joinpath("detector.py").read_bytes())
    pins = json.loads(text)
    for name in pins["skills"]:
        digest.update(preload.text(name).encode())
    return f"{pins['pack']}+{digest.hexdigest()[:12]}"


def platform_name() -> str:
    """This machine as the engine's release names it, such as ``darwin-arm64``."""
    system = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}.get(platform.machine())
    if system is None or machine is None:
        msg = f"the design detector has no engine for {platform.system()} {platform.machine()}"
        raise PackError(msg)
    return f"{system}-{machine}"


def folder(pins: dict[str, Any] | None = None) -> Path:
    """Where this machine keeps the pack's downloads, outside every project; *pins* name a candidate pack."""
    home = Path(os.environ.get("OWLBEAR_HOME") or Path.home() / ".owlbear")
    return home / "design-pack" / (pins or manifest())["pack"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wanted(pins: dict[str, Any] | None = None) -> dict[str, tuple[str, str]]:
    pins = pins or manifest()
    up, name = pins["upstream"], platform_name()
    engine = RELEASE.format(repository=up["repository"], engine=up["engine"], platform=name)
    bundle = RAW.format(repository=up["repository"], commit=up["commit"], path=pins["bundle"]["path"])
    return {ENGINE: (engine, pins["engine"][name]), BUNDLE: (bundle, pins["bundle"]["sha256"])}


def _private(target: Path) -> bool:
    """Whether *target* is a real folder only this user can change: no link, no other writer."""
    try:
        info = target.lstat()
    except OSError:
        return False
    return not target.is_symlink() and info.st_uid == os.getuid() and not info.st_mode & 0o022


def installed(pins: dict[str, Any] | None = None) -> Installed | None:
    """The pack's files when both are present in a private folder and match their digests; otherwise none."""
    try:
        wanted, target = _wanted(pins), folder(pins)
        if not (_private(target) and _private(target.parent)) or any(
            _sha256(target / n) != d for n, (_u, d) in wanted.items()
        ):
            return None
        bundle = (target / BUNDLE).read_bytes()
    except OSError, KeyError, PackError:
        return None
    if hashlib.sha256(bundle).hexdigest() != wanted[BUNDLE][1]:  # the text kept is the text verified
        return None
    return Installed(target / ENGINE, wanted[ENGINE][1], bundle.decode("utf-8"))


def fetch(url: str, seconds: float = SECONDS) -> bytes:
    """One HTTPS download through the system's trust store, bounded in time."""
    https = urllib.request.HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
    with urllib.request.build_opener(https).open(url, timeout=seconds) as response:
        return response.read()


def _keep(target: Path, name: str, data: bytes) -> None:
    """Write *data* as *name* through a unique temporary file and an atomic rename; nothing half-written stays."""
    fd, tmp = tempfile.mkstemp(dir=target, prefix=f".{name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        Path(tmp).chmod(0o755 if name == ENGINE else 0o644)
        Path(tmp).replace(target / name)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def install(download: Callable[[str], bytes] | None = None, pins: dict[str, Any] | None = None) -> Installed:
    """Download what is missing or changed, refuse any file that does not match its digest, and keep the rest."""
    download = download or fetch
    target = folder(pins)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.mkdir(mode=0o700, exist_ok=True)
    if not (_private(target) and _private(target.parent)):
        msg = f"{target} is a link or others can write to it; the design pack is kept only in a private folder"
        raise PackError(msg)
    for name, (url, digest) in _wanted(pins).items():
        path = target / name
        if path.exists() and _sha256(path) == digest:
            continue
        try:
            data = download(url)
        except OSError as exc:
            msg = f"cannot download {url}: {exc}"
            raise PackError(msg) from exc
        if hashlib.sha256(data).hexdigest() != digest:
            msg = f"{url} does not match the design pack's digest; nothing was installed from it"
            raise PackError(msg)
        _keep(target, name, data)
    found = installed(pins)
    if found is None:
        msg = f"the design pack in {target} does not verify after installing"
        raise PackError(msg)
    return found


def status() -> str:
    """One line for setup and the CLI: whether the design detector is ready on this machine."""
    pack = manifest()["pack"]
    try:
        platform_name()
    except PackError as exc:
        return f"design pack {pack}: {exc}"
    if installed() is None:
        return f"design pack {pack}: not installed; run `owlbear-next design-pack --install`"
    return f"design pack {pack}: installed in {folder()}"
