"""Synchronize the pinned Archify release into the local development cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, NoReturn

SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parents[2]
LOCK_PATH = SCRIPT_DIR / "archify.lock.json"
CACHE_ROOT = REPOSITORY_ROOT / ".owlbear/cache/archify"
REPOSITORY = "tt-a1i/archify"
ASSET = "archify.zip"
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_EXTRACTED_BYTES = 32 * 1024 * 1024
MAX_FILE_COUNT = 1000
REQUIRED_FILES = (
    "archify/bin/archify.mjs",
    "archify/assets/template.html",
    "archify/renderers/architecture/render-architecture.mjs",
    "archify/schemas/architecture.schema.json",
)


class SyncError(RuntimeError):
    """Report a pinned Archify synchronization failure."""


def _fail(message: str, cause: BaseException | None = None) -> NoReturn:
    """Raise one synchronization error with an optional source exception."""
    if cause is None:
        raise SyncError(message)
    raise SyncError(message) from cause


def _read_lock(path: Path) -> dict[str, str]:
    """Read and validate one Archify lock document."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"Could not read Archify lock {path}: {error}", error)
    if not isinstance(document, dict):
        _fail("Archify lock must be a JSON object.")
    if document.get("schema_version") != 1:
        _fail("Archify lock schema_version must be 1.")
    if document.get("repository") != REPOSITORY or document.get("asset") != ASSET:
        _fail(f"Archify lock must target {REPOSITORY} release asset {ASSET}.")
    version = document.get("version")
    digest = document.get("sha256")
    if not isinstance(version, str) or VERSION_PATTERN.fullmatch(version) is None:
        _fail("Archify lock version must be a three-part semantic version.")
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        _fail("Archify lock sha256 must be a lowercase SHA-256 digest.")
    return {"repository": REPOSITORY, "asset": ASSET, "version": version, "sha256": digest}


def _release_url(version: str) -> str:
    """Build the fixed GitHub release URL for one validated version."""
    return f"https://github.com/{REPOSITORY}/releases/download/{version}/{ASSET}"


def _open_url(request: urllib.request.Request) -> BinaryIO:
    """Open the fixed release request."""
    return urllib.request.urlopen(request, timeout=60)  # noqa: S310


def _download(url: str, destination: Path) -> None:
    """Download one bounded release asset to a temporary path."""
    request = urllib.request.Request(url, headers={"User-Agent": "owlbear-archify-sync"})  # noqa: S310
    try:
        with _open_url(request) as response, destination.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ARCHIVE_BYTES:
                    _fail(f"Archify release exceeds the {MAX_ARCHIVE_BYTES} byte limit.")
                output.write(chunk)
    except SyncError:
        raise
    except (OSError, urllib.error.URLError) as error:
        _fail(f"Could not download Archify release: {error}", error)


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_member_path(name: str) -> tuple[str, ...]:
    """Validate and normalize one release ZIP member path."""
    if not name or "\x00" in name or "\\" in name:
        _fail(f"Archify release contains an unsafe ZIP path: {name!r}.")
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts or not member.parts or member.parts[0] != "archify":
        _fail(f"Archify release contains an unsafe ZIP path: {name!r}.")
    return member.parts


def _extract_archive(archive: Path, destination: Path) -> None:
    """Extract a validated Archify release without following unsafe entries."""
    try:
        archive_file = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile) as error:
        _fail(f"Archify release is not a readable ZIP: {error}", error)

    extracted_bytes = 0
    file_count = 0
    seen: set[tuple[str, ...]] = set()
    with archive_file:
        for member in archive_file.infolist():
            parts = _validated_member_path(member.filename)
            if parts in seen:
                _fail(f"Archify release contains duplicate ZIP path: {member.filename!r}.")
            seen.add(parts)
            mode = (member.external_attr >> 16) & 0o170000
            if stat.S_ISLNK(mode):
                _fail(f"Archify release contains a symbolic link: {member.filename!r}.")
            if member.is_dir():
                continue
            file_count += 1
            extracted_bytes += member.file_size
            if file_count > MAX_FILE_COUNT or extracted_bytes > MAX_EXTRACTED_BYTES:
                _fail("Archify release exceeds the extraction limits.")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive_file.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            permissions = (member.external_attr >> 16) & 0o777
            target.chmod(permissions or 0o644)

    missing = [relative for relative in REQUIRED_FILES if not (destination / relative).is_file()]
    if missing:
        _fail(f"Archify release is missing required files: {', '.join(missing)}.")


def _cache_directory(lock: dict[str, str], cache_root: Path) -> Path:
    """Return the version-specific cache directory."""
    return cache_root / lock["version"]


def _cache_is_valid(lock: dict[str, str], cache_root: Path) -> bool:
    """Return whether the cache contains the exact pinned release."""
    directory = _cache_directory(lock, cache_root)
    marker_path = directory / ".complete.json"
    try:
        marker: Any = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(marker, dict):
        return False
    if marker.get("schema_version") != 1 or marker.get("version") != lock["version"]:
        return False
    if marker.get("sha256") != lock["sha256"]:
        return False
    return all((directory / relative).is_file() for relative in REQUIRED_FILES)


def _write_marker(directory: Path, lock: dict[str, str]) -> None:
    """Write the cache completion marker."""
    marker = {"schema_version": 1, "version": lock["version"], "sha256": lock["sha256"], "asset": lock["asset"]}
    (directory / ".complete.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")


def _install_archive(archive: Path, lock: dict[str, str], cache_root: Path) -> Path:
    """Install one verified archive atomically into the version cache."""
    cache_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".archify-", dir=cache_root.parent))
    target = _cache_directory(lock, cache_root)
    try:
        _extract_archive(archive, staging)
        _write_marker(staging, lock)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        staging.replace(target)
        return target / "archify"
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def ensure_archify(
    lock_path: Path = LOCK_PATH,
    cache_root: Path = CACHE_ROOT,
    *,
    offline: bool = False,
) -> Path:
    """Ensure the locked Archify package exists and return its root."""
    lock = _read_lock(lock_path)
    if _cache_is_valid(lock, cache_root):
        return _cache_directory(lock, cache_root) / "archify"
    if offline:
        _fail(f"Archify {lock['version']} is not present in the offline cache.")
    cache_root.parent.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=".archify-", suffix=".zip", dir=cache_root.parent, delete=False
    ) as temporary:
        archive = Path(temporary.name)
    try:
        _download(_release_url(lock["version"]), archive)
        actual_digest = _sha256(archive)
        if actual_digest != lock["sha256"]:
            _fail(f"Archify release digest mismatch: expected {lock['sha256']}, got {actual_digest}.")
        return _install_archive(archive, lock, cache_root)
    finally:
        archive.unlink(missing_ok=True)


def _write_lock(path: Path, lock: dict[str, str]) -> None:
    """Replace a lock file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(json.dumps({"schema_version": 1, **lock}, indent=2) + "\n")
        candidate = Path(temporary.name)
    try:
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)


def update_pin(
    version: str,
    lock_path: Path = LOCK_PATH,
    cache_root: Path = CACHE_ROOT,
) -> Path:
    """Download, verify, cache, and record one Archify release version."""
    if VERSION_PATTERN.fullmatch(version) is None:
        _fail("Archify version must be a v-prefixed three-part semantic version.")
    cache_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=".archify-update-", suffix=".zip", dir=cache_root.parent, delete=False
    ) as temporary:
        archive = Path(temporary.name)
    try:
        _download(_release_url(version), archive)
        lock = {"repository": REPOSITORY, "asset": ASSET, "version": version, "sha256": _sha256(archive)}
        root = _install_archive(archive, lock, cache_root)
        _write_lock(lock_path, lock)
        return root
    finally:
        archive.unlink(missing_ok=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the synchronizer command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="fail instead of downloading a missing cache")
    parser.add_argument("--print-root", action="store_true", help="print only the resolved Archify root")
    parser.add_argument("--update-pin", metavar="VERSION", help="download and record a new release version")
    arguments = parser.parse_args(argv)
    if arguments.offline and arguments.update_pin:
        parser.error("--offline and --update-pin cannot be combined")
    return arguments


def main(argv: list[str] | None = None) -> int:
    """Run the Archify cache synchronizer."""
    arguments = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        root = update_pin(arguments.update_pin) if arguments.update_pin else ensure_archify(offline=arguments.offline)
    except SyncError as error:
        print(f"Archify sync failed: {error}", file=sys.stderr)
        return 1
    if arguments.print_root:
        print(root)
    else:
        print(f"Archify ready: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
