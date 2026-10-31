"""PDS's pin: the npm release whose skills Delivery vendors in ``pds/`` and whose loader and stylesheet it serves.

``pds.json`` names the version, npm's integrity of its tarball and the SHA-256 of every vendored and served file, by
its path in the package folder.
A candidate comes only from a tarball whose sha512 matches npm's integrity, checked before anything is extracted
(D-01M5DW3X00NFB5CXS5DPG7FTY9: the pages load PDS only from its CDN; these files are the skills and two entry points).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import posixpath
import re
import tarfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.impeccable import pack_files

if TYPE_CHECKING:
    from collections.abc import Callable

NAME = "@porsche-design-system/components-js"
REGISTRY = "https://registry.npmjs.org/@porsche-design-system/components-js"
TARBALLS = "https://registry.npmjs.org/@porsche-design-system/components-js/-/"
PREFIX = "serve/delivery-next/src/owlbear_delivery_next/"  # the package folder, from the repository's root
PIN, TREE, WEB = "pds.json", "pds", "web/pds"
VERSION = re.compile(r"\d+\.\d+\.\d+")
SEEDS = (  # every candidate vendors these; their markdown links add the rest (D-01M69E9EKZ9RC3G25HZXMPXJET)
    "package.json", "LICENSE.md", "OSS_NOTICE", "CHANGELOG.md", "skills/pds-knowledge-js",
    "skills/pds-audit-deprecations-js", "meta", "tokens", "scss", "tailwindcss",
)  # fmt: skip
SERVED = {  # each served file: npm's file and the header line before its bytes
    "load.mjs": ("esm/index.mjs", "Loads the components from the PDS CDN."),
    "index.css": ("stylesheets/index.css", "Fonts load from the PDS CDN under the PDS Assets License."),
}
LICENCE = "Apache-2.0, (c) 2022 Dr. Ing. h.c. F. Porsche AG."
LINK = re.compile(r"\]\(([^)\s]+)")
SECONDS = 60.0


class PinError(Exception):
    """A release that can't be pinned: unreachable, tampered, unsafe or incomplete; the message says which."""


class Pin(BaseModel):
    """``pds.json``: the version, npm's integrity and every pinned file's SHA-256 by its path in the package folder."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    integrity: str
    files: dict[str, str]


@dataclass(frozen=True)
class Release:
    """One verified release: the vendored closure by package path and the two served files."""

    version: str
    integrity: str
    tree: dict[str, bytes]
    served: dict[str, bytes]

    def pin(self) -> Pin:
        """Its ``pds.json``: version, integrity and the SHA-256 of every vendored and served file."""
        sums = {p: hashlib.sha256(b).hexdigest() for p, b in sorted(self.mapped().items())}
        return Pin(version=self.version, integrity=self.integrity, files=sums)

    def mapped(self) -> dict[str, bytes]:
        """Every pinned file's bytes by its path in the package folder."""
        return {f"{TREE}/{p}": b for p, b in self.tree.items()} | {f"{WEB}/{n}": b for n, b in self.served.items()}

    def files(self, old: Pin | None = None) -> dict[str, bytes | None]:
        """Every file to commit by repository path, ``pds.json`` included; ``None`` deletes one only the old pin had."""
        new = self.mapped()
        gone: dict[str, bytes | None] = {p: None for p in (old.files if old else {}) if p not in new}
        out = {**dict(sorted(new.items())), **gone, PIN: render(self.pin())}
        return {f"{PREFIX}{p}": b for p, b in out.items()}


def render(pin: Pin) -> bytes:
    """``pds.json``'s bytes: the digests grouped by folder, so every line stays within the repository's width."""
    folders: dict[str, dict[str, str]] = {}
    for path, digest in sorted(pin.files.items()):
        folder, _, name = path.rpartition("/")
        folders.setdefault(folder, {})[name] = digest
    body = {"version": pin.version, "integrity": pin.integrity, "files": folders}
    return (json.dumps(body, indent=2) + "\n").encode()


def package() -> Path:
    """The installed package folder, whose ``pds.json`` and ``pds/`` this checkout serves."""
    return Path(str(files("owlbear_delivery_next")))


def read(root: Path | None = None) -> Pin:
    """The pin of the package folder ``root`` (the installed one by default)."""
    body = json.loads(((root or package()) / PIN).read_bytes())
    if isinstance(body, dict) and isinstance(folders := body.get("files"), dict):
        body["files"] = {f"{f}/{n}": d for f, names in folders.items() for n, d in (names or {}).items()}
    return Pin.model_validate(body)


def verify(root: Path | None = None) -> list[str]:
    """What differs between the package folder and its pin: each missing or changed file, by its path there."""
    root = root or package()
    pin, out = read(root), []
    for path, digest in pin.files.items():
        at = root / path
        if not at.is_file():
            out.append(f"{path} is missing")
        elif hashlib.sha256(at.read_bytes()).hexdigest() != digest:
            out.append(f"{path} differs from the pin")
    return out


def release(version: str, fetch: Callable[[str, float], bytes] | None = None) -> Release:
    """Download, verify and pick release ``version``: npm's metadata, then its tarball, checked before extraction.

    Raises:
        PinError: npm was not reached or answered unusably, the tarball's sha512 differs, or it is unsafe or incomplete.
    """
    if not VERSION.fullmatch(version):
        msg = f"{version!r} is not a release version"
        raise PinError(msg)
    get = fetch or pack_files.fetch
    try:
        meta = json.loads(get(f"{REGISTRY}/{version}", SECONDS))
        url, integrity = meta["dist"]["tarball"], meta["dist"]["integrity"]
    except OSError as exc:
        msg = f"npm was not reached for {NAME} {version}: {exc}"
        raise PinError(msg) from exc
    except (ValueError, KeyError, TypeError) as exc:
        msg = f"npm's metadata for {NAME} {version} names no tarball and integrity"
        raise PinError(msg) from exc
    if not (isinstance(url, str) and url.startswith(TARBALLS) and isinstance(integrity, str)):
        msg = f"npm's tarball for {NAME} {version} is not on the registry: {str(url)[:120]}"
        raise PinError(msg)
    try:
        data = get(url, SECONDS)
    except OSError as exc:
        msg = f"the tarball {url} was not downloaded: {exc}"
        raise PinError(msg) from exc
    return unpack(version, integrity, data)


def unpack(version: str, integrity: str, data: bytes) -> Release:
    """Check ``data`` against ``integrity`` first, then extract it safely and pick the closure and served files."""
    algorithm, _, expected = integrity.partition("-")
    if algorithm != "sha512" or base64.b64encode(hashlib.sha512(data).digest()).decode() != expected:
        msg = f"the tarball of {NAME} {version} does not match npm's integrity {integrity[:30]}…; nothing was extracted"
        raise PinError(msg)
    tree = extract(data)
    served = {name: _served(tree, version, name) for name in SERVED}
    return Release(version, integrity, closure(tree), served)


def extract(data: bytes) -> dict[str, bytes]:
    """The tarball's regular files by package path; an absolute, ``..``, link or device entry refuses it whole."""
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            parts = name.split("/")
            if name.startswith("/") or ".." in parts or parts[0] != "package":
                msg = f"the tarball holds an unsafe path {name!r}; nothing was extracted"
                raise PinError(msg)
            if member.isdir():
                continue
            if not member.isfile():
                msg = f"the tarball holds {name!r}, which is not a regular file; nothing was extracted"
                raise PinError(msg)
            body = tar.extractfile(member)
            out["/".join(parts[1:])] = body.read() if body else b""
    return out


def closure(tree: dict[str, bytes]) -> dict[str, bytes]:
    """The seeds, then every file their markdown links reach, recursively, by package path.

    A link resolves against its file's folder, else against its skill's folder (the skills write reference paths from
    their root); site-root (``/…``), anchor-only and scheme links are documentation and skipped.

    Raises:
        PinError: A seed is missing, or a link leaves the package or names no file.
    """
    todo: list[str] = []
    for seed in SEEDS:
        found = [p for p in tree if p == seed or p.startswith(f"{seed}/")]
        if not found:
            msg = f"the release has no {seed}, which every PDS update vendors"
            raise PinError(msg)
        todo += found
    seen: set[str] = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        if path.endswith(".md"):
            todo += [_target(tree, path, link) for link in _links(tree[path])]
    return {p: tree[p] for p in sorted(seen)}


def _links(body: bytes) -> list[str]:
    out = []
    for raw in LINK.findall(body.decode("utf-8", errors="replace")):
        link = raw.split("#", 1)[0]
        if link and not link.startswith("/") and not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link):
            out.append(link)
    return out


def _target(tree: dict[str, bytes], path: str, link: str) -> str:
    parts = path.split("/")
    skill = "/".join(parts[:2]) if parts[0] == "skills" and len(parts) > 2 else ""  # noqa: PLR2004
    for base in (posixpath.dirname(path), *([skill] if skill else [])):
        target = posixpath.normpath(posixpath.join(base, link))
        if target == ".." or target.startswith("../"):
            msg = f"{path} links {link!r} outside the package"
            raise PinError(msg)
        if target in tree:
            return target
    msg = f"{path} links {link!r}, which names no file in the release"
    raise PinError(msg)


def _served(tree: dict[str, bytes], version: str, name: str) -> bytes:
    source, said = SERVED[name]
    if source not in tree:
        msg = f"the release has no {source}, which Delivery serves as {name}"
        raise PinError(msg)
    body = tree[source] if tree[source].endswith(b"\n") else tree[source] + b"\n"
    return f"/* {NAME} {version} {source}; {LICENCE} {said} */\n".encode() + body
